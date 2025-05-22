#!/usr/bin/env python

import asyncio
import aiohttp
import json
import logging
import uuid
import os
from fastapi import WebSocket, WebSocketDisconnect
from opentelemetry import trace
from prompts.prompts import AGENT_PROMPT_REALTIME
from langchain_openai import AzureChatOpenAI
from botify_langchain.runnable_factory import RunnableFactory
from app.settings import AppSettings

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# Constants for debounce and throttling
DEBOUNCE_DELAY = float(os.getenv("DEBOUNCE_DELAY", 1.5))
THROTTLE_MIN_INTERVAL = int(os.getenv("THROTTLE_MIN_INTERVAL", 4))

# Session configs
REALTIME_SESSION_CONFIG_AZURE = {
    "type": "session.update",
    "session": {
        "modalities": ["text", "audio"],
        "instructions": None,  # Will be set in __init__
        "voice": None,  # Will be set in __init__
        "input_audio_format": "pcm16",
        "output_audio_format": "pcm16",
        "input_audio_transcription": {"model": "whisper-1"},
        "input_audio_noise_reduction": {
            "type": "azure_deep_noise_suppression"
        },
        "input_audio_echo_cancellation": {
            "type": "server_echo_cancellation"
        },
        "turn_detection": {
            "type": os.getenv("AZURE_SPEECH_SERVICES_TURN_DETECTION_TYPE", "server_vad"),
            "threshold": float(os.getenv("AZURE_SPEECH_SERVICES_VAD_THRESHOLD", 0.2)),
            "silence_duration_ms": int(os.getenv("AZURE_SPEECH_SERVICES_VAD_SILENCE_DURATION_MS", 500)),
            # Remove other parameters that might not be compatible with azure_semantic_vad
        },
        "tools": [],  # Will be populated based on available tools
        "tool_choice": "auto"
    }
}

REALTIME_SESSION_CONFIG_OPENAI = {
    "type": "session.update",
    "session": {
        "modalities": ["text", "audio"],
        "instructions": None,  # Will be set in __init__
        "voice": None,  # Will be set in __init__
        "input_audio_format": "pcm16",
        "output_audio_format": "pcm16",
        "input_audio_transcription": {"model": "whisper-1"},
        "turn_detection": {
            "type": "server_vad",
            "threshold": float(os.getenv("AZURE_OPENAI_REALTIME_VAD_THRESHOLD", 0.2)),
            "silence_duration_ms": int(os.getenv("AZURE_OPENAI_REALTIME_VAD_SILENCE_DURATION_MS", 500)),
        },
        "tools": [],  # Will be populated based on available tools
        "tool_choice": "auto"
    }
}

class BotifyRealtime:
    def __init__(self, engine: str, api_key: str, endpoint: str, deployment: str, voice_choice: str):
        self.engine = engine
        self.api_key = api_key
        self.endpoint = endpoint.rstrip('/')
        self.deployment = deployment
        self.voice_choice = voice_choice
        self.session = None
        self.ws_openai = None
        self.client_connected = True
        self.session_id = str(uuid.uuid4())
        self.current_turn_id = None
        self.pending_tasks = set()

        # Initialize runnable factory to use the same data source as the rest of the application
        self.runnable_factory = RunnableFactory()
        self.app_settings = AppSettings()

        # Get the search tool from the runnable factory
        self.search_tool = self.runnable_factory.azure_ai_search_tool

        # Set up tools
        self.tools = {"SearchTool": self.search_tool}

        # Set up conversation history
        self.conversation_history = []
        self.all_tool_results = []
        self.debounce_task = None
        self.last_json_update = 0
        self.DEBOUNCE_DELAY = DEBOUNCE_DELAY
        self.THROTTLE_MIN_INTERVAL = THROTTLE_MIN_INTERVAL

    async def connect_to_realtime_api(self):
        headers = {"api-key": self.api_key}
        base_url = self.endpoint.replace("https://", "wss://")

        if self.engine == "azure":
            url = f"{base_url}/voice-agent/realtime?api-version=2025-05-01-preview&deployment={self.deployment}"
        elif self.engine == "openai":
            url = f"{base_url}/openai/realtime?api-version=2024-10-01-preview&deployment={self.deployment}"
        else:
            logger.error(f"Invalid engine: {self.engine}. Must be 'openai' or 'azure'")
            raise ValueError("Invalid engine specified")

        logger.info(f"Connecting to Realtime API at: {url}")

        try:
            self.session = aiohttp.ClientSession()
            self.ws_openai = await self.session.ws_connect(url, headers=headers, timeout=30)
            await self.send_session_config(self.engine)
            logger.info(f"Successfully connected to Realtime API")
        except aiohttp.ClientConnectorError as e:
            logger.error(f"Failed to connect to {url}: {str(e)}")
            if self.session and not self.session.closed:
                await self.session.close()
            raise ConnectionError(f"Cannot connect to Azure OpenAI Realtime API: {str(e)}")
        except aiohttp.ClientResponseError as e:
            logger.error(f"API error when connecting to {url}: {e.status} {e.message}")
            if self.session and not self.session.closed:
                await self.session.close()
            raise ConnectionError(f"API error: {e.status} {e.message}")
        except asyncio.TimeoutError:
            logger.error(f"Connection timeout when connecting to {url}")
            if self.session and not self.session.closed:
                await self.session.close()
            raise ConnectionError("Connection timeout to Azure OpenAI Realtime API")
        except Exception as e:
            logger.error(f"Unexpected error connecting to {url}: {str(e)}")
            if self.session and not self.session.closed:
                await self.session.close()
            raise

    async def send_session_config(self, engine: str):
        """
        Send session configuration to the Realtime API.
        """
        if engine == "azure":
            config = REALTIME_SESSION_CONFIG_AZURE.copy()

            # Get the current turn detection type
            turn_detection_type = os.getenv("AZURE_SPEECH_SERVICES_TURN_DETECTION_TYPE", "server_vad")
            logger.info(f"Using {turn_detection_type} pipeline for turn detection")

            # Customize configuration based on turn detection type
            if turn_detection_type == "azure_semantic_vad":
                # For azure_semantic_vad, only include the parameters it supports
                config["session"]["turn_detection"] = {
                    "type": turn_detection_type,
                    "threshold": float(os.getenv("AZURE_SPEECH_SERVICES_VAD_THRESHOLD", 0.2)),
                    "silence_duration_ms": int(os.getenv("AZURE_SPEECH_SERVICES_VAD_SILENCE_DURATION_MS", 500))
                }
                # Make sure Azure-specific noise reduction is included since we're using azure_semantic_vad
                if "input_audio_noise_reduction" not in config["session"]:
                    config["session"]["input_audio_noise_reduction"] = {
                        "type": "azure_deep_noise_suppression"
                    }
                logger.info("Using simplified configuration for azure_semantic_vad")
            elif turn_detection_type == "server_vad":
                # For server_vad, ensure we don't have end-of-utterance detection
                if "end_of_utterance_detection" in config["session"]["turn_detection"]:
                    del config["session"]["turn_detection"]["end_of_utterance_detection"]
                logger.info("Using standard configuration for server_vad")
        else:
            config = REALTIME_SESSION_CONFIG_OPENAI.copy()

        # Get prompt from the prompt generator if available, otherwise use default
        try:
            from prompts.prompts import AGENT_PROMPT_REALTIME
            config["session"]["instructions"] = AGENT_PROMPT_REALTIME
        except (ImportError, AttributeError):
            # Use a basic prompt if AGENT_PROMPT_REALTIME is not available
            config["session"]["instructions"] = (
                "You are a helpful assistant. Answer questions based on the provided information. "
                "When you don't know the answer, say so rather than making things up."
            )

        config["session"]["voice"] = self.voice_choice

        # Configure tools
        tool_configs = []
        if self.search_tool:
            tool_configs.append({
                "type": "function",
                "name": "SearchTool",
                "description": "Useful to search for information in the knowledge base.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query for information"},
                    },
                    "required": ["query"]
                }
            })

        config["session"]["tools"] = tool_configs

        # Log the configuration for debugging
        debug_config = config.copy()
        if "session" in debug_config and "instructions" in debug_config["session"]:
            debug_config["session"]["instructions"] = "[INSTRUCTIONS TRUNCATED]"  # Don't log the full instructions
        logger.info(f"Sending session configuration: {json.dumps(debug_config)}")

        try:
            await self.ws_openai.send_json(config)
            logger.info(f"Sent session configuration to Realtime API for engine {engine}")
        except Exception as e:
            logger.error(f"Error sending session configuration: {str(e)}")
            raise

    async def _forward_messages(self, websocket: WebSocket):
        with tracer.start_as_current_span("realtime_forward_messages"):
            try:
                # Log client information
                client_info = f"Client IP: {websocket.client.host}:{websocket.client.port}"
                logger.info(f"Starting realtime session. {client_info}")

                # Connect to Azure OpenAI Realtime API
                await self.connect_to_realtime_api()
                await asyncio.sleep(1)  # Brief pause to ensure connection is established

                # Start forwarding tasks
                client_task = asyncio.create_task(self._from_client_to_openai(websocket))
                openai_task = asyncio.create_task(self._from_openai_to_client(websocket))

                try:
                    # Wait for either task to complete or fail
                    done, pending = await asyncio.wait(
                        [client_task, openai_task],
                        return_when=asyncio.FIRST_EXCEPTION
                    )

                    # Cancel any pending tasks
                    for task in pending:
                        task.cancel()

                    # Check for exceptions
                    for task in done:
                        if task.exception() is not None:
                            exc = task.exception()
                            logger.error(f"Task failed with exception: {str(exc)}")
                            raise exc
                except WebSocketDisconnect:
                    logger.info("Client WebSocket disconnected")
                    self.client_connected = False
                except asyncio.CancelledError:
                    logger.info("Tasks cancelled")
                    self.client_connected = False
                except Exception as e:
                    logger.error(f"Error in message forwarding: {str(e)}")
                    self.client_connected = False
                    # Try to send an error message to the client if still connected
                    if websocket.client_state.name != "DISCONNECTED":
                        try:
                            await websocket.send_json({
                                "type": "error",
                                "error": {
                                    "message": f"Server error: {str(e)}",
                                    "code": "internal_error"
                                }
                            })
                        except Exception:
                            pass  # If we can't send the error, just continue to cleanup
            except ConnectionError as e:
                # Handle connection errors to Azure OpenAI
                logger.error(f"Connection error: {str(e)}")
                if websocket.client_state.name != "DISCONNECTED":
                    try:
                        await websocket.send_json({
                            "type": "error",
                            "error": {
                                "message": f"Azure OpenAI connection error: {str(e)}",
                                "code": "azure_connection_error"
                            }
                        })
                    except Exception:
                        pass  # If we can't send the error, just continue to cleanup
            except Exception as e:
                # Handle unexpected errors
                logger.error(f"Unexpected error in _forward_messages: {str(e)}")
                if websocket.client_state.name != "DISCONNECTED":
                    try:
                        await websocket.send_json({
                            "type": "error",
                            "error": {
                                "message": "Internal server error",
                                "code": "internal_error"
                            }
                        })
                    except Exception:
                        pass  # If we can't send the error, just continue to cleanup
            finally:
                # Clean up any pending tasks and connections
                if self.pending_tasks:
                    logger.info(f"Waiting for {len(self.pending_tasks)} pending tasks to complete")
                    try:
                        await asyncio.wait_for(asyncio.gather(*self.pending_tasks), timeout=10)
                    except asyncio.TimeoutError:
                        logger.warning("Timeout waiting for pending tasks")
                        for task in self.pending_tasks:
                            task.cancel()
                await self.cleanup()
                logger.info(f"Realtime session ended. {client_info}")

    async def _from_client_to_openai(self, websocket: WebSocket):
        with tracer.start_as_current_span("realtime_client_to_openai"):
            while self.client_connected:
                try:
                    message = await websocket.receive_text()
                    logger.info(f"Received message of length: {len(message)}")
                    message_data = json.loads(message)

                    # Log the message type
                    message_type = message_data.get("type", "unknown")
                    logger.info(f"Received message type: {message_type}")

                    # Set a new turn ID when receiving audio data
                    if message_type == "input_audio_buffer.append":
                        self.current_turn_id = str(uuid.uuid4())
                        logger.info(f"Created new turn ID: {self.current_turn_id}")

                        # Check if audio exists directly in the message (new format)
                        if "audio" in message_data:
                            audio_length = len(message_data.get("audio", ""))
                            logger.info(f"Audio data present in root, length: {audio_length}")
                        # For backward compatibility, also check in data field (old format)
                        elif "data" in message_data:
                            data_field = message_data.get("data")
                            logger.info(f"Data field found, type: {type(data_field)}")

                            # Validate the audio data format
                            if isinstance(data_field, str):
                                # Old format with string data, move to root level
                                logger.info("Converting string data in 'data' field to root 'audio' field")
                                message_data["audio"] = data_field
                                del message_data["data"]
                            elif isinstance(data_field, dict) and "audio" in data_field:
                                # Old format with nested audio, move to root level
                                logger.info("Moving audio from nested data object to root level")
                                message_data["audio"] = data_field["audio"]
                                del message_data["data"]
                            else:
                                logger.error(f"Invalid data format: {type(data_field)}")
                                await websocket.send_json({
                                    "type": "error",
                                    "error": {
                                        "message": f"Invalid data format. Expected 'audio' field at root level or in 'data' object.",
                                        "code": "client_error"
                                    }
                                })
                                continue
                        else:
                            logger.error("Missing 'audio' field in message")
                            await websocket.send_json({
                                "type": "error",
                                "error": {
                                    "message": "Invalid message format: missing 'audio' field",
                                    "code": "client_error"
                                }
                            })
                            continue

                        # Log what we're sending to OpenAI
                        if "audio" in message_data:
                            audio_length = len(message_data["audio"])
                            logger.info(f"Sending audio data to OpenAI, length: {audio_length}")
                        else:
                            logger.error("No audio data found after processing")
                            continue
                    # Send the message to OpenAI
                    logger.info("Forwarding message to OpenAI")
                    await self.ws_openai.send_json(message_data)
                except WebSocketDisconnect:
                    self.client_connected = False
                    logger.info("Client disconnected during message send")
                    break
                except Exception as e:
                    logger.error(f"Error forwarding client message to OpenAI: {str(e)}")
                    break

    async def _from_openai_to_client(self, websocket: WebSocket):
        with tracer.start_as_current_span("realtime_openai_to_client"):
            transcript_buffer = ""
            tool_name = None
            async for msg in self.ws_openai:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        message = json.loads(msg.data)
                        logger.info(f"Received message from OpenAI: {message['type']}")

                        if message.get("type") == "conversation.item.created" and "item" in message:
                            self.current_turn_id = message["item"]["id"]
                            logger.info(f"Updated turn_id to {self.current_turn_id} for conversation item {message['item']['id']}")

                        if message.get("type") == "error":
                            error_details = message.get('error', 'Unknown error details')
                            logger.error(f"OpenAI Realtime API error: {error_details}")

                            # Extract a user-friendly error message and log more details
                            error_message = "Unknown error occurred"
                            if isinstance(error_details, dict):
                                error_message = error_details.get('message', 'Unknown error occurred')
                                error_type = error_details.get('type', 'unknown_error')
                                error_code = error_details.get('code', 'unknown_code')
                                error_param = error_details.get('param', 'none')
                                error_id = error_details.get('event_id', 'none')
                                logger.error(f"Error details - Type: {error_type}, Code: {error_code}, Param: {error_param}, Event ID: {error_id}")

                                # Log additional details for internal server errors which may be configuration-related
                                if error_code == "internal_error" or error_type == "server_error":
                                    logger.error("Internal server error detected - this might be due to configuration issues")
                                    logger.info(f"Current turn detection type: {os.getenv('AZURE_SPEECH_SERVICES_TURN_DETECTION_TYPE', 'server_vad')}")

                                    # Try to recover by sending new configuration
                                    try:
                                        logger.info("Attempting to recover from internal server error by updating session config")
                                        # Simplify the configuration to most basic form
                                        simplified_config = {
                                            "type": "session.update",
                                            "session": {
                                                "turn_detection": {
                                                    "type": "server_vad",
                                                    "threshold": 0.2,
                                                    "silence_duration_ms": 500
                                                }
                                            }
                                        }
                                        await self.ws_openai.send_json(simplified_config)
                                        logger.info("Sent simplified configuration after error")
                                    except Exception as e:
                                        logger.error(f"Failed to send recovery configuration: {str(e)}")
                            elif isinstance(error_details, str):
                                error_message = error_details

                            # Send the error to the client
                            await websocket.send_json({
                                "type": "error",
                                "error": {
                                    "message": f"API Error: {error_message}",
                                    "details": error_details,
                                    "code": "api_error"
                                }
                            })

                            # If it's an invalid_request_error, provide more helpful details about how to fix it
                            if isinstance(error_details, dict) and error_details.get("type") == "invalid_request_error":
                                error_param = error_details.get("param")
                                if "End of utterance detection is only supported for cascaded pipelines" in error_message:
                                    fix_message = "The Azure OpenAI Realtime API doesn't support end-of-utterance detection with the current turn detection type. Restarting the server to disable end-of-utterance detection."
                                    logger.info(fix_message)
                                    await websocket.send_json({
                                        "type": "error",
                                        "error": {
                                            "message": fix_message,
                                            "code": "configuration_error"
                                        }
                                    })

                                    # We need to restart our connection without end-of-utterance detection
                                    await websocket.close(code=1012, reason="Restarting connection with updated configuration")
                                    return

                            continue  # Skip further processing for error messages

                        turn_id = self.current_turn_id

                        if message.get("type") == "conversation.item.input_audio_transcription.completed":
                            transcribed_text = message.get("transcript", "")
                            if transcribed_text and turn_id:
                                logger.info(f"Received user transcription for turn_id={turn_id}: {transcribed_text}")
                                self.conversation_history.append({"role": "user", "content": transcribed_text})

                        if message.get("type") == "response.audio_transcript.delta":
                            transcript_buffer += message["delta"]
                            logger.info(f"Appending to transcript for turn_id={turn_id}: {message['delta']}")

                        if message.get("type") == "response.audio_transcript.done" and transcript_buffer and turn_id:
                            logger.info(f"Completed transcript for turn_id={turn_id}: {transcript_buffer}")
                            assistant_message = {
                                "role": "assistant",
                                "content": transcript_buffer,
                                "additional_kwargs": {
                                    "tool_results": self.all_tool_results.copy()
                                }
                            }
                            self.conversation_history.append(assistant_message)
                            transcript_buffer = ""

                        if message.get("type") == "response.output_item.done" and "item" in message and message["item"].get("type") == "function_call":
                            function_call = message["item"]
                            tool_name = function_call["name"]
                            arguments = json.loads(function_call["arguments"])
                            tool_call_id = function_call["call_id"]

                            if tool_name in self.tools:
                                tool = self.tools[tool_name]
                                try:
                                    result = await tool.ainvoke(arguments)
                                    logger.info(f"Tool {tool_name} returned result of type: {type(result)}")

                                    tool_result = {
                                        "type": "tool_result.update",
                                        "call_id": tool_call_id,
                                        "result": json.dumps(result)
                                    }

                                    self.all_tool_results.append({
                                        "tool_name": tool_name,
                                        "tool_call_id": tool_call_id,
                                        "arguments": arguments,
                                        "result": result
                                    })

                                    await self.ws_openai.send_json(tool_result)
                                    logger.info(f"Sent tool result to OpenAI: {tool_result}")
                                except Exception as e:
                                    logger.error(f"Error invoking tool {tool_name}: {str(e)}")
                                    error_message = {
                                        "type": "tool_result.update",
                                        "call_id": tool_call_id,
                                        "result": json.dumps({"error": str(e)})
                                    }
                                    await self.ws_openai.send_json(error_message)

                        # Forward the message to the client
                        await websocket.send_text(msg.data)

                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse JSON from message: {msg.data}")
                    except Exception as e:
                        logger.error(f"Error processing message from OpenAI: {str(e)}")

    async def cleanup(self):
        if self.ws_openai and not self.ws_openai.closed:
            await self.ws_openai.close()
        if self.session and not self.session.closed:
            await self.session.close()
        logger.info("WebSocket connections and session cleaned up")
