#!/usr/bin/env python

import asyncio
import json
import logging

import aiohttp
from app.settings import AppSettings
from botify_langchain.runnable_factory import RunnableFactory
from common.schemas import ResponseSchema
from fastapi import WebSocket, WebSocketDisconnect
from opentelemetry import trace
from prompts.prompt_gen import PromptGen

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class BotifyRealtime:
    def __init__(self):
        self.runnable_factory = RunnableFactory()
        self.app_settings = AppSettings()
        self.promptgen = PromptGen()

        self.api_key = self.app_settings.environment_config.openai_api_key.get_secret_value()
        self.endpoint = self.app_settings.environment_config.openai_endpoint.rstrip("/")
        self.deployment = self.app_settings.environment_config.openai_realtime_deployment_name
        self.voice_choice = self.app_settings.environment_config.openai_realtime_voice_choice

        self.session = None
        self.ws_openai = None
        self.client_connected = True
        self.search_tool = self.runnable_factory.azure_ai_search_tool

    async def connect_to_realtime_api(self):
        headers = {"api-key": self.api_key}
        base_url = self.endpoint.replace("https://", "wss://")
        url = f"{base_url}/openai/realtime?api-version=2024-10-01-preview&deployment={self.deployment}"

        try:
            self.session = aiohttp.ClientSession()
            self.ws_openai = await self.session.ws_connect(url, headers=headers, timeout=30)
            await self.send_session_config()
        except Exception as e:
            logger.error("Failed to connect to Azure OpenAI: %s", str(e))
            if self.session and not self.session.closed:
                await self.session.close()
            raise ConnectionError(f"Cannot connect to Azure OpenAI Realtime API: {str(e)}")

    async def send_session_config(self):
        # Simple prompt without JSON filtering
        prompt_text = self.promptgen.generate_prompt(
            self.app_settings.prompt_template_paths, schema=ResponseSchema().get_response_schema()
        )

        # Basic realtime instructions
        enhanced_prompt = (
            "Use the search-tool for any information requests. "
            "Provide conversational responses with source links as markdown. " + prompt_text
        )

        # Simple session configuration
        config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": enhanced_prompt,
                "voice": self.voice_choice,
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {"model": "whisper-1"},
                "turn_detection": {"type": "server_vad", "threshold": 0.2, "silence_duration_ms": 500},
                "tools": (
                    [
                        {
                            "type": "function",
                            "name": "search-tool",
                            "description": "Search the knowledge base for information",
                            "parameters": {
                                "type": "object",
                                "properties": {"query": {"type": "string", "description": "Search query"}},
                                "required": ["query"],
                            },
                        }
                    ]
                    if self.search_tool
                    else []
                ),
                "tool_choice": "auto",
            },
        }

        await self.ws_openai.send_json(config)

    async def _forward_messages(self, websocket: WebSocket):
        with tracer.start_as_current_span("realtime_forward_messages"):
            try:
                logger.info("Starting realtime session")
                await self.connect_to_realtime_api()

                # Start forwarding tasks
                client_task = asyncio.create_task(self._from_client_to_openai(websocket))
                openai_task = asyncio.create_task(self._from_openai_to_client(websocket))

                # Wait for either task to complete
                done, pending = await asyncio.wait(
                    [client_task, openai_task], return_when=asyncio.FIRST_EXCEPTION
                )

                # Cancel pending tasks
                for task in pending:
                    task.cancel()

                # Check for exceptions
                for task in done:
                    if task.exception():
                        raise task.exception()

            except WebSocketDisconnect:
                self.client_connected = False
            except Exception as e:
                logger.error("Error in message forwarding: %s", str(e))
                self.client_connected = False
                try:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "error": {"message": f"Server error: {str(e)}", "code": "internal_error"},
                        }
                    )
                except Exception:
                    pass
            finally:
                await self.cleanup()

    async def _from_client_to_openai(self, websocket: WebSocket):
        with tracer.start_as_current_span("realtime_client_to_openai"):
            while self.client_connected:
                try:
                    message = await websocket.receive_text()
                    message_data = json.loads(message)

                    # Simple audio format handling
                    if message_data.get("type") == "input_audio_buffer.append":
                        if "data" in message_data and "audio" not in message_data:
                            message_data["audio"] = message_data.pop("data")

                    await self.ws_openai.send_json(message_data)
                except WebSocketDisconnect:
                    self.client_connected = False
                    break
                except Exception as e:
                    logger.error("Error forwarding client message: %s", str(e))
                    break

    async def _from_openai_to_client(self, websocket: WebSocket):
        with tracer.start_as_current_span("realtime_openai_to_client"):
            if not self.ws_openai or self.ws_openai.closed:
                logger.error("OpenAI WebSocket not ready")
                return

            try:
                async for msg in self.ws_openai:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        try:
                            message = json.loads(msg.data)

                            # Handle errors
                            if message.get("type") == "error":
                                await self._handle_error(message, websocket)
                                continue

                            # Handle function calls
                            if (
                                message.get("type") == "response.output_item.done"
                                and message.get("item", {}).get("type") == "function_call"
                            ):
                                await self._handle_function_call(message["item"])
                                continue  # Don't forward function call messages

                            # Forward all other messages
                            await websocket.send_text(msg.data)

                        except json.JSONDecodeError:
                            logger.error("Failed to parse JSON from OpenAI")
                        except Exception as e:
                            logger.error("Error processing OpenAI message: %s", str(e))
            except Exception as e:
                logger.error("Error in OpenAI-to-client forwarding: %s", str(e))
                raise

    async def _handle_error(self, message, websocket):
        """Simple error handling"""
        error_details = message.get("error", {})
        error_message = (
            error_details.get("message", "Unknown error")
            if isinstance(error_details, dict)
            else str(error_details)
        )

        logger.error("OpenAI API error: %s", error_message)

        await websocket.send_json(
            {
                "type": "error",
                "error": {"message": f"API Error: {error_message}", "code": "api_error"},
            }
        )

    async def _handle_function_call(self, function_call):
        """Simple function call handling"""
        tool_name = function_call["name"]
        arguments = json.loads(function_call["arguments"])
        tool_call_id = function_call["call_id"]

        if tool_name == "search-tool" and self.search_tool:
            try:
                query = arguments.get("query", "")
                result = await self.search_tool._arun(query)

                # Simple result serialization
                result_json = json.dumps(result) if isinstance(result, (dict, list)) else str(result)

                tool_result = {
                    "type": "conversation.item.create",
                    "item": {
                        "type": "function_call_output",
                        "call_id": tool_call_id,
                        "output": result_json,
                    },
                }

                await self.ws_openai.send_json(tool_result)

                # Continue response
                continue_response = {
                    "type": "response.create",
                    "response": {"modalities": ["text", "audio"]},
                }
                await self.ws_openai.send_json(continue_response)

            except Exception as e:
                logger.error("Tool execution error: %s", str(e))
                error_result = {
                    "type": "conversation.item.create",
                    "item": {
                        "type": "function_call_output",
                        "call_id": tool_call_id,
                        "output": json.dumps({"error": str(e)}),
                    },
                }
                await self.ws_openai.send_json(error_result)

    async def cleanup(self):
        if self.ws_openai and not self.ws_openai.closed:
            await self.ws_openai.close()
        if self.session and not self.session.closed:
            await self.session.close()
