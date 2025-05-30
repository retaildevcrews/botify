#!/usr/bin/env python

import asyncio
import json
import logging
import os
import uuid

import aiohttp
from app.settings import AppSettings
from botify_langchain.runnable_factory import RunnableFactory
from common.schemas import ResponseSchema
from fastapi import WebSocket, WebSocketDisconnect
from langchain_core.documents import Document
from opentelemetry import trace
from prompts.prompt_gen import PromptGen

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# Constants for debounce and throttling
DEBOUNCE_DELAY = float(os.getenv("DEBOUNCE_DELAY", 1.5))
THROTTLE_MIN_INTERVAL = int(os.getenv("THROTTLE_MIN_INTERVAL", 4))

# Session config
REALTIME_SESSION_CONFIG = {
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
        "tool_choice": "auto",
    },
}


class BotifyRealtime:
    def __init__(self):
        # Initialize runnable factory to use the same data source as the rest of the application
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
        self.session_id = str(uuid.uuid4())
        self.current_turn_id = None
        self.pending_tasks = set()

        # Get the search tool from the runnable factory
        self.search_tool = self.runnable_factory.azure_ai_search_tool
        logger.debug(
            "Initialized search tool: %s with name: %s",
            type(self.search_tool),
            self.search_tool.name if hasattr(self.search_tool, "name") else "Unknown",
        )

        # Set up tools
        self.tools = {"search-tool": self.search_tool}
        logger.debug("Available tools: %s", list(self.tools.keys()))

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
        url = f"{base_url}/openai/realtime?api-version=2024-10-01-preview&deployment={self.deployment}"
        logger.debug("Connecting to Realtime API at: %s", url)

        try:
            self.session = aiohttp.ClientSession()
            self.ws_openai = await self.session.ws_connect(url, headers=headers, timeout=30)
            await self.send_session_config()
            logger.debug("Successfully connected to Realtime API")
        except aiohttp.ClientConnectorError as e:
            logger.error("Failed to connect to %s: %s", url, str(e))
            if self.session and not self.session.closed:
                await self.session.close()
            raise ConnectionError(f"Cannot connect to Azure OpenAI Realtime API: {str(e)}")
        except aiohttp.ClientResponseError as e:
            logger.error("API error when connecting to %s: %s %s", url, e.status, e.message)
            if self.session and not self.session.closed:
                await self.session.close()
            raise ConnectionError(f"API error: {e.status} {e.message}")
        except asyncio.TimeoutError:
            logger.error("Connection timeout when connecting to %s", url)
            if self.session and not self.session.closed:
                await self.session.close()
            raise ConnectionError("Connection timeout to Azure OpenAI Realtime API")
        except Exception as e:
            logger.error("Unexpected error connecting to %s: %s", url, str(e))
            if self.session and not self.session.closed:
                await self.session.close()
            raise

    async def send_session_config(self):
        """
        Send session configuration to the Realtime API.
        """
        config = REALTIME_SESSION_CONFIG.copy()

        # Get the current turn detection type
        turn_detection_type = os.getenv("AZURE_SPEECH_SERVICES_TURN_DETECTION_TYPE", "server_vad")
        logger.debug("Using %s pipeline for turn detection", turn_detection_type)

        # Customize configuration based on turn detection type
        if turn_detection_type == "azure_semantic_vad":
            # For azure_semantic_vad, only include the parameters it supports
            config["session"]["turn_detection"] = {
                "type": turn_detection_type,
                "threshold": float(os.getenv("AZURE_SPEECH_SERVICES_VAD_THRESHOLD", 0.2)),
                "silence_duration_ms": int(os.getenv("AZURE_SPEECH_SERVICES_VAD_SILENCE_DURATION_MS", 500)),
            }
            # Make sure Azure-specific noise reduction is included since we're using azure_semantic_vad
            if "input_audio_noise_reduction" not in config["session"]:
                config["session"]["input_audio_noise_reduction"] = {"type": "azure_deep_noise_suppression"}
            logger.debug("Using simplified configuration for azure_semantic_vad")
        elif turn_detection_type == "server_vad":
            # For server_vad, ensure we don't have end-of-utterance detection
            if "end_of_utterance_detection" in config["session"]["turn_detection"]:
                del config["session"]["turn_detection"]["end_of_utterance_detection"]
            logger.debug("Using standard configuration for server_vad")

        # Generate the base prompt using the configured template paths
        prompt_text = self.promptgen.generate_prompt(
            self.app_settings.prompt_template_paths, schema=ResponseSchema().get_response_schema()
        )

        # Override the JSON format requirement for realtime conversations
        # Extract the base content without JSON schema instructions
        base_prompt_lines = prompt_text.split("\n")
        filtered_lines = []
        skip_json_section = False

        for line in base_prompt_lines:
            if "JSON schema" in line or "json" in line.lower() and "schema" in line.lower():
                skip_json_section = True
                continue
            elif skip_json_section and line.strip() and not line.startswith(" "):
                skip_json_section = False

            if not skip_json_section:
                filtered_lines.append(line)

        filtered_prompt = "\n".join(filtered_lines)

        # Add explicit realtime-specific instructions
        enhanced_prompt = (
            """CRITICAL TOOL USAGE: You MUST use the search-tool for any information request or question.
            When users ask "how to" questions, factual questions, or request any information, you MUST call
            the search-tool first before responding.

REALTIME RESPONSE FORMAT OVERRIDE:
- This is a realtime voice conversation - DO NOT use JSON format
- Provide your response as a complete, natural conversational answer
- When you use search results, ALWAYS include source links directly in your response text
- Format links as markdown: [descriptive text](URL)
- Example: "For more details, you can check the full guide [here](https://example.com/clean-windows)"
- Make your response helpful and conversational while ensuring source links are included inline

"""
            + filtered_prompt
        )

        config["session"]["instructions"] = enhanced_prompt

        # Log a sample of the prompt for debugging (first 200 chars)
        logger.info("🎯 REALTIME PROMPT PREVIEW: ...%s...", enhanced_prompt[:200])
        config["session"]["voice"] = self.voice_choice

        # Configure tools
        tool_configs = []
        if self.search_tool:
            tool_config = {
                "type": "function",
                "name": "search-tool",
                "description": (
                    "Use this tool to search the knowledge base for any information requests, "
                    "questions, or how-to guides. This includes questions about procedures, "
                    "instructions, tutorials, or any topic that might be documented. Always use "
                    "this tool when users ask questions like 'how to do something', request "
                    "information, or need help with any topic."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": (
                                "Search query for information - include the user's complete "
                                "question or key terms from their request"
                            ),
                        },
                    },
                    "required": ["query"],
                },
            }
            tool_configs.append(tool_config)
            logger.debug("Added tool configuration: %s", tool_config)
            logger.info("🔧 SEARCH-TOOL REGISTERED for realtime session - Tool available for function calls")
        else:
            logger.warning("Search tool is None, no tools will be available")

        config["session"]["tools"] = tool_configs

        # Set tool_choice to auto but with very explicit instructions to use tools
        # This allows the model to choose when to use tools appropriately
        if tool_configs:
            config["session"]["tool_choice"] = "auto"
            logger.info(
                "🔧 Set tool_choice to 'auto' with explicit tool usage instructions for realtime endpoint"
            )

        # Log the configuration for debugging
        debug_config = config.copy()
        if "session" in debug_config and "instructions" in debug_config["session"]:
            debug_config["session"][
                "instructions"
            ] = "[INSTRUCTIONS TRUNCATED]"  # Don't log the full instructions
        logger.debug("Sending session configuration: %s", json.dumps(debug_config))

        try:
            await self.ws_openai.send_json(config)
            logger.debug("Sent session configuration to Azure Voice Agent Realtime API")
        except Exception as e:
            logger.error("Error sending session configuration: %s", str(e))
            raise

    async def _forward_messages(self, websocket: WebSocket):
        with tracer.start_as_current_span("realtime_forward_messages"):
            try:
                # Log client information
                client_info = "Client IP: %s:%s" % (websocket.client.host, websocket.client.port)
                logger.debug("Starting realtime session. %s", client_info)
                logger.info("📡 REALTIME SESSION STARTING - Beginning message forwarding for %s", client_info)

                # Connect to Azure OpenAI Realtime API
                logger.info("🔗 Connecting to Azure OpenAI Realtime API...")
                await self.connect_to_realtime_api()
                logger.info("✅ Azure OpenAI connection established successfully")

                await asyncio.sleep(1)  # Brief pause to ensure connection is established
                logger.info("🚀 Starting message forwarding tasks...")

                # Start forwarding tasks
                client_task = asyncio.create_task(self._from_client_to_openai(websocket))
                openai_task = asyncio.create_task(self._from_openai_to_client(websocket))
                logger.info("📨 Both forwarding tasks created - client_to_openai and openai_to_client")

                try:
                    # Wait for either task to complete or fail
                    logger.info("⏳ Waiting for message forwarding tasks to start processing...")
                    done, pending = await asyncio.wait(
                        [client_task, openai_task], return_when=asyncio.FIRST_EXCEPTION
                    )
                    logger.info("⚠️ One or more tasks completed/failed - checking results...")

                    # Cancel any pending tasks
                    for task in pending:
                        logger.info(f"🛑 Cancelling pending task: {task.get_name()}")
                        task.cancel()

                    # Check for exceptions
                    for task in done:
                        if task.exception() is not None:
                            exc = task.exception()
                            logger.error(
                                "❌ Task %s failed with exception: %s",
                                task.get_name(),
                                str(exc),
                            )
                            logger.exception("Full traceback for %s:", task.get_name())
                            raise exc
                        else:
                            logger.info("✅ Task %s completed normally", task.get_name())
                except WebSocketDisconnect:
                    logger.info("Client WebSocket disconnected")
                    self.client_connected = False
                except asyncio.CancelledError:
                    logger.info("Tasks cancelled")
                    self.client_connected = False
                except Exception as e:
                    logger.error("Error in message forwarding: %s", str(e))
                    self.client_connected = False
                    # Try to send an error message to the client if still connected
                    if websocket.client_state.name != "DISCONNECTED":
                        try:
                            await websocket.send_json(
                                {
                                    "type": "error",
                                    "error": {
                                        "message": "Server error: %s" % str(e),
                                        "code": "internal_error",
                                    },
                                }
                            )
                        except Exception:
                            pass  # If we can't send the error, just continue to cleanup
            except ConnectionError as e:
                # Handle connection errors to Azure OpenAI
                logger.error(f"Connection error: {str(e)}")
                if websocket.client_state.name != "DISCONNECTED":
                    try:
                        await websocket.send_json(
                            {
                                "type": "error",
                                "error": {
                                    "message": f"Azure OpenAI connection error: {str(e)}",
                                    "code": "azure_connection_error",
                                },
                            }
                        )
                    except Exception:
                        pass  # If we can't send the error, just continue to cleanup
            except Exception as e:
                # Handle unexpected errors
                logger.error(f"Unexpected error in _forward_messages: {str(e)}")
                if websocket.client_state.name != "DISCONNECTED":
                    try:
                        await websocket.send_json(
                            {
                                "type": "error",
                                "error": {"message": "Internal server error", "code": "internal_error"},
                            }
                        )
                    except Exception:
                        pass  # If we can't send the error, just continue to cleanup
            finally:
                # Clean up any pending tasks and connections
                if self.pending_tasks:
                    logger.debug(f"Waiting for {len(self.pending_tasks)} pending tasks to complete")
                    try:
                        await asyncio.wait_for(asyncio.gather(*self.pending_tasks), timeout=10)
                    except asyncio.TimeoutError:
                        logger.warning("Timeout waiting for pending tasks")
                        for task in self.pending_tasks:
                            task.cancel()
                await self.cleanup()
                logger.debug("Realtime session ended. %s", client_info)

    async def _from_client_to_openai(self, websocket: WebSocket):
        with tracer.start_as_current_span("realtime_client_to_openai"):
            # logger.info(f"📥 CLIENT-TO-OPENAI task started - listening for client messages")
            while self.client_connected:
                try:
                    logger.debug("Waiting for client message...")
                    message = await websocket.receive_text()
                    # logger.info(f"📥 Received client message of length: {len(message)}")
                    message_data = json.loads(message)

                    # Log the message type
                    message_type = message_data.get("type", "unknown")
                    # logger.info(f"📥 Client message type: {message_type}")

                    # Set a new turn ID when receiving audio data
                    if message_type == "input_audio_buffer.append":
                        self.current_turn_id = str(uuid.uuid4())
                        logger.debug("Created new turn ID: %s", self.current_turn_id)

                        # Check if audio exists directly in the message (new format)
                        if "audio" in message_data:
                            audio_length = len(message_data.get("audio", ""))
                            logger.debug("Audio data present in root, length: %d", audio_length)
                        # For backward compatibility, also check in data field (old format)
                        elif "data" in message_data:
                            data_field = message_data.get("data")
                            logger.debug("Data field found, type: %s", type(data_field))

                            # Validate the audio data format
                            if isinstance(data_field, str):
                                # Old format with string data, move to root level
                                logger.debug("Converting string data in 'data' field to root 'audio' field")
                                message_data["audio"] = data_field
                                del message_data["data"]
                            elif isinstance(data_field, dict) and "audio" in data_field:
                                # Old format with nested audio, move to root level
                                logger.debug("Moving audio from nested data object to root level")
                                message_data["audio"] = data_field["audio"]
                                del message_data["data"]
                            else:
                                logger.error("Invalid data format: %s", type(data_field))
                                await websocket.send_json(
                                    {
                                        "type": "error",
                                        "error": {
                                            "message": (
                                                "Invalid data format. Expected 'audio' field at root level "
                                                "or in 'data' object."
                                            ),
                                            "code": "client_error",
                                        },
                                    }
                                )
                                continue
                        else:
                            logger.error("Missing 'audio' field in message")
                            await websocket.send_json(
                                {
                                    "type": "error",
                                    "error": {
                                        "message": "Invalid message format: missing 'audio' field",
                                        "code": "client_error",
                                    },
                                }
                            )
                            continue

                        # Log what we're sending to OpenAI
                        if "audio" in message_data:
                            audio_length = len(message_data["audio"])
                            logger.debug("Sending audio data to OpenAI, length: %d", audio_length)
                        else:
                            logger.error("No audio data found after processing")
                            continue
                    # Send the message to OpenAI
                    logger.debug("Forwarding message to OpenAI")
                    await self.ws_openai.send_json(message_data)
                except WebSocketDisconnect:
                    self.client_connected = False
                    logger.info("Client disconnected during message send")
                    break
                except Exception as e:
                    logger.error(f"Error forwarding client message to OpenAI: {str(e)}")
                    break

    async def _handle_error_message(self, message, websocket):
        """Handle error messages from OpenAI Realtime API"""
        error_details = message.get("error", "Unknown error details")
        logger.error(f"OpenAI Realtime API error: {error_details}")

        # Extract a user-friendly error message and log more details
        error_message = "Unknown error occurred"
        if isinstance(error_details, dict):
            error_message = error_details.get("message", "Unknown error occurred")
            error_type = error_details.get("type", "unknown_error")
            error_code = error_details.get("code", "unknown_code")
            error_param = error_details.get("param", "none")
            error_id = error_details.get("event_id", "none")
            logger.error(
                "Error details - Type: %s, Code: %s, Param: %s, Event ID: %s",
                error_type,
                error_code,
                error_param,
                error_id,
            )

            # Log additional details for internal server errors which may be configuration-related
            if error_code == "internal_error" or error_type == "server_error":
                logger.error("Internal server error detected - this might be due to configuration issues")
                logger.info(
                    "Current turn detection type: %s",
                    os.getenv("AZURE_SPEECH_SERVICES_TURN_DETECTION_TYPE", "server_vad"),
                )

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
                                "silence_duration_ms": 500,
                            }
                        },
                    }
                    await self.ws_openai.send_json(simplified_config)
                    logger.info("Sent simplified configuration after error")
                except Exception as e:
                    logger.error(f"Failed to send recovery configuration: {str(e)}")
        elif isinstance(error_details, str):
            error_message = error_details

        # Send the error to the client
        await websocket.send_json(
            {
                "type": "error",
                "error": {
                    "message": f"API Error: {error_message}",
                    "details": error_details,
                    "code": "api_error",
                },
            }
        )

        # If it's an invalid_request_error, provide more helpful details about how to fix it
        if isinstance(error_details, dict) and error_details.get("type") == "invalid_request_error":
            error_param = error_details.get("param")
            if "End of utterance detection is only supported for cascaded pipelines" in error_message:
                fix_message = (
                    "The Azure OpenAI Realtime API doesn't support end-of-utterance detection "
                    "with the current turn detection type. Restarting the server to disable "
                    "end-of-utterance detection."
                )
                logger.debug(fix_message)
                await websocket.send_json(
                    {
                        "type": "error",
                        "error": {"message": fix_message, "code": "configuration_error"},
                    }
                )

                # We need to restart our connection without end-of-utterance detection
                await websocket.close(code=1012, reason="Restarting connection with updated configuration")
                return

    async def _from_openai_to_client(self, websocket: WebSocket):
        with tracer.start_as_current_span("realtime_openai_to_client"):
            # logger.info(f"📤 OPENAI-TO-CLIENT task started - listening for OpenAI messages")

            # Check if OpenAI WebSocket is ready
            if not self.ws_openai:
                logger.error("❌ OpenAI WebSocket is None - cannot start message forwarding")
                return
            if self.ws_openai.closed:
                logger.error("❌ OpenAI WebSocket is closed - cannot start message forwarding")
                return

            logger.info(f"✅ OpenAI WebSocket is ready, state: {self.ws_openai.closed}")
            transcript_buffer = ""
            tool_name = None
            # logger.info(f"📤 Starting to iterate over OpenAI WebSocket messages...")

            try:
                async for msg in self.ws_openai:
                    # logger.info(f"📤 Got message from OpenAI WebSocket, type: {msg.type}")
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        try:
                            message = json.loads(msg.data)
                            # logger.info(f"📤 Received message from OpenAI: {message['type']}")

                            if message.get("type") == "conversation.item.created" and "item" in message:
                                self.current_turn_id = message["item"]["id"]
                                logger.debug(
                                    "Updated turn_id to %s for conversation item %s",
                                    self.current_turn_id,
                                    message["item"]["id"],
                                )

                            if message.get("type") == "error":
                                await self._handle_error_message(message, websocket)
                                continue  # Skip further processing for error messages

                            turn_id = self.current_turn_id

                            if message.get("type") == "conversation.item.input_audio_transcription.completed":
                                transcribed_text = message.get("transcript", "")
                                if transcribed_text and turn_id:
                                    logger.debug(
                                        "Received user transcription for turn_id=%s: %s",
                                        turn_id,
                                        transcribed_text,
                                    )
                                    self.conversation_history.append(
                                        {"role": "user", "content": transcribed_text}
                                    )

                            if message.get("type") == "response.audio_transcript.delta":
                                transcript_buffer += message["delta"]
                                logger.debug(
                                    "Appending to transcript for turn_id=%s: %s", turn_id, message["delta"]
                                )

                            # Track function call events from the model
                            if message.get("type") == "response.function_call_arguments.delta":
                                logger.info(
                                    "🔍 FUNCTION-CALL-ARGS-DELTA received - Model is invoking a function"
                                )

                            if message.get("type") == "response.function_call_arguments.done":
                                logger.info(
                                    "🔍 FUNCTION-CALL-ARGS-DONE received - Function arguments complete"
                                )

                            # Track when function call items are added to the response
                            if message.get("type") == "response.output_item.added":
                                item = message.get("item", {})
                                item_type = item.get("type")
                                logger.info(f"🔍 OUTPUT-ITEM-ADDED: type='{item_type}', item={item}")
                                if item_type == "function_call":
                                    logger.info(f"🔍 FUNCTION-CALL-ITEM detected: {item}")

                            if message.get("type") == "response.output_item.done":
                                item = message.get("item", {})
                                item_type = item.get("type")
                                if item_type == "function_call":
                                    logger.info(f"🔍 FUNCTION-CALL-ITEM-DONE: {item}")

                            if (
                                message.get("type") == "response.audio_transcript.done"
                                and transcript_buffer
                                and turn_id
                            ):
                                logger.debug(
                                    f"Completed transcript for turn_id={turn_id}: {transcript_buffer}"
                                )
                                assistant_message = {
                                    "role": "assistant",
                                    "content": transcript_buffer,
                                    "additional_kwargs": {"tool_results": self.all_tool_results.copy()},
                                }
                                self.conversation_history.append(assistant_message)
                                transcript_buffer = ""

                            if (
                                message.get("type") == "response.output_item.done"
                                and "item" in message
                                and message["item"].get("type") == "function_call"
                            ):
                                logger.debug("Received function_call from OpenAI Realtime API")
                                function_call = message["item"]
                                tool_name = function_call["name"]
                                arguments = json.loads(function_call["arguments"])
                                tool_call_id = function_call["call_id"]

                                logger.debug(
                                    "Function call details - tool_name: %s, call_id: %s, arguments: %s",
                                    tool_name,
                                    tool_call_id,
                                    arguments,
                                )

                                if tool_name in self.tools:
                                    tool = self.tools[tool_name]
                                    try:
                                        # Extract the query parameter from arguments
                                        query = arguments.get("query", "")
                                        logger.debug(f"Calling tool {tool_name} with query: {query}")

                                        # Add info logging for search-tool specifically
                                        if tool_name == "search-tool":
                                            logger.info(
                                                """🔍 SEARCH-TOOL INVOKED via realtime
                                                endpoint - Query: '%s' (call_id: %s)""",
                                                query,
                                                tool_call_id,
                                            )

                                        if not query:
                                            logger.warning("Empty query provided to tool %s", tool_name)

                                        result = await tool._arun(query)
                                        logger.debug(
                                            f"""Tool {tool_name} returned result of type: {type(result)}
                                            with length: {len(str(result))}"""
                                        )

                                        # Add info logging for successful search-tool completion
                                        if tool_name == "search-tool":
                                            result_length = len(str(result)) if result else 0
                                            logger.info(
                                                """✅ SEARCH-TOOL COMPLETED successfully -
                                                Result length: %s chars (call_id: %s)""",
                                                result_length,
                                                tool_call_id,
                                            )

                                        # Handle Document objects in search results
                                        if (
                                            isinstance(result, list)
                                            and result
                                            and isinstance(result[0], Document)
                                        ):
                                            # Convert Document objects to dict format for JSON serialization
                                            serializable_result = [
                                                {
                                                    "page_content": doc.page_content,
                                                    "metadata": (
                                                        doc.metadata if hasattr(doc, "metadata") else {}
                                                    ),
                                                }
                                                for doc in result
                                            ]
                                            result_json = json.dumps(serializable_result)
                                        elif isinstance(result, (dict, list)):
                                            result_json = json.dumps(result)
                                        else:
                                            result_json = str(result)

                                        tool_result = {
                                            "type": "conversation.item.create",
                                            "item": {
                                                "type": "function_call_output",
                                                "call_id": tool_call_id,
                                                "output": result_json,
                                            },
                                        }

                                        self.all_tool_results.append(
                                            {
                                                "tool_name": tool_name,
                                                "tool_call_id": tool_call_id,
                                                "arguments": arguments,
                                                "result": result,
                                            }
                                        )

                                        # Send tool result back to Azure OpenAI with error handling
                                        try:
                                            await self.ws_openai.send_json(tool_result)
                                            logger.info(
                                                "✅ TOOL RESULT SENT to Azure OpenAI for call_id: %s",
                                                tool_call_id,
                                            )

                                            # After sending the tool result, explicitly continue the response
                                            # This tells Azure OpenAI to generate its response based on
                                            # the tool result
                                            continue_response = {
                                                "type": "response.create",
                                                "response": {
                                                    "modalities": ["text", "audio"],
                                                    "instructions": (
                                                        "Based on the search results "
                                                        "provided by the tool, "
                                                        "give a comprehensive and helpful "
                                                        "answer to the user's question."
                                                    ),
                                                },
                                            }
                                            await self.ws_openai.send_json(continue_response)
                                            logger.info(
                                                """RESPONSE CONTINUATION TRIGGERED after
                                                tool result for call_id: %s""",
                                                tool_call_id,
                                            )

                                        except Exception as send_error:
                                            logger.error(
                                                "❌ FAILED to send tool result to OpenAI: %s", send_error
                                            )
                                            raise send_error
                                    except Exception as e:
                                        # Add info logging for search-tool errors
                                        if tool_name == "search-tool":
                                            logger.info(
                                                "❌ SEARCH-TOOL FAILED - Query: '%s', Error: %s (call_id: %s)",
                                                query,
                                                str(e),
                                                tool_call_id,
                                            )

                                        logger.error(
                                            f"Error invoking tool {tool_name} with query '{query}': {str(e)}"
                                        )
                                        logger.exception("Full traceback:")
                                        error_message = {
                                            "type": "conversation.item.create",
                                            "item": {
                                                "type": "function_call_output",
                                                "call_id": tool_call_id,
                                                "output": json.dumps({"error": str(e)}),
                                            },
                                        }
                                        await self.ws_openai.send_json(error_message)
                                else:
                                    # Add specific info logging for search-tool not found
                                    if tool_name == "search-tool":
                                        logger.info(
                                            """⚠️ SEARCH-TOOL NOT FOUND - Tool '%s' not available in
                                            registered tools: %s (call_id: %s)""",
                                            tool_name,
                                            list(self.tools.keys()),
                                            tool_call_id,
                                        )

                                    logger.error(
                                        "Tool %s not found in available tools: %s",
                                        tool_name,
                                        list(self.tools.keys()),
                                    )

                                # DO NOT forward function_call completion messages to the client
                                # Azure OpenAI will send the actual response after processing the tool result
                                logger.debug(
                                    f"""Skipping function_call completion message (call_id:
                                    {tool_call_id}) - waiting for AI response"""
                                )
                                continue  # Skip forwarding this message to the client

                            # Forward the message to the client - check connection state first
                            try:
                                # Check if WebSocket is still connected before sending
                                if (
                                    hasattr(websocket, "client_state")
                                    and websocket.client_state.name == "CONNECTED"
                                ):
                                    await websocket.send_text(msg.data)
                                elif not hasattr(websocket, "client_state"):
                                    # Fallback: try to send and catch the exception
                                    await websocket.send_text(msg.data)
                                else:
                                    logger.info("Client disconnected during message send")
                                    break  # Exit the message processing loop if client disconnected
                            except Exception as send_error:
                                logger.info(f"Client disconnected during message send: {send_error}")
                                break  # Exit the message processing loop

                        except json.JSONDecodeError:
                            logger.error(f"Failed to parse JSON from message: {msg.data}")
                        except Exception as e:
                            logger.error(f"Error processing message from OpenAI: {str(e)}")
                            import traceback

                            logger.error(
                                f"Full exception traceback: {traceback.format_exc()}"
                            )  # Add full traceback to debug the exact issue
            except Exception as e:
                logger.error(f"❌ Error in OpenAI-to-client message forwarding: {str(e)}")
                logger.exception("Full traceback for OpenAI-to-client error:")
                raise

    async def cleanup(self):
        if self.ws_openai and not self.ws_openai.closed:
            await self.ws_openai.close()
        if self.session and not self.session.closed:
            await self.session.close()
        logger.debug("WebSocket connections and session cleaned up")
