#!/usr/bin/env python

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, TypedDict

import _additional_version_info
import pydantic
import toml
from api.anonymize_decorator import anonymize
from api.models import Payload
from api.utils import invoke_wrapper as invoke_runnable
from app.settings import AppSettings
from botify_langchain.runnable_factory import RunnableFactory
from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.websockets import WebSocketDisconnect
from opentelemetry import trace

# Configure logging
logger = logging.getLogger(__name__)

tracer = trace.get_tracer(__name__)


class Config:
    arbitrary_types_allowed = True


# Define Input and Output Schemas


class Input(TypedDict):
    question: str


@pydantic.dataclasses.dataclass(config=Config)
class Output:
    output: Any


class AppFactory:
    def __init__(self, app_settings: AppSettings, runnable_factory: RunnableFactory):
        self.app_settings = app_settings
        self.runnable_factory = runnable_factory
        self.app = FastAPI(
            title="Botify API",
            version=self.get_version(),
            description="""An API server utilizing LangChain's Runnable
            interfaces to create a chatbot that uses an
            index as grounding material for answering questions.""",
        )
        self.setup_middleware()
        self.setup_routes()
        self.setup_realtime_routes()  # Add WebSocket endpoints
        logging.getLogger().setLevel(self.app_settings.environment_config.log_level)

    def get_source_ip(self, request: Request) -> str:
        x_forward = request.headers.get("X-Forwarded-For")
        x_real_ip = request.headers.get("X-Real-IP")
        x_azure = request.headers.get("X-Azure-ClientIP")
        x_origin_ip = request.headers.get("X-Origin-IP")
        http_client_ip = request.headers.get("HTTP_CLIENT_IP")
        return ",".join(
            filter(None, [x_forward, x_real_ip, x_azure, x_origin_ip, http_client_ip, request.client.host])
        )

    def get_version(self) -> str:
        # Load the pyproject.toml file
        current_file_path = Path(__file__).resolve()
        pyproject_file_path = current_file_path.parent.parent / "pyproject.toml"
        pyproject = toml.load(pyproject_file_path)

        version = pyproject.get("tool", {}).get("poetry", {}).get("version", "Version not found")
        if _additional_version_info.__short_sha__ and _additional_version_info.__build_timestamp__:
            version += f"-{_additional_version_info.__short_sha__}-{
                _additional_version_info.__build_timestamp__}"
        return version

    def setup_middleware(self):
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["*"],
        )

    def setup_routes(self):
        @self.app.get("/version")
        def get_version():
            config_hash = self.app_settings.get_config_hash()
            return {"version": self.app.version, "config_hash": config_hash}

        @self.app.get("/")
        async def redirect_root_to_docs() -> RedirectResponse:
            """Redirect to the API documentation."""
            return RedirectResponse("/docs")

        @self.app.get(
            "/realtime-info",
            summary="Get information about the realtime WebSocket endpoint",
            description="Provides details on how to use the WebSocket endpoint for realtime voice interactions.",
            responses={
                200: {
                    "description": "Information about the realtime WebSocket endpoint",
                    "content": {
                        "application/json": {
                            "example": {
                                "websocket_endpoint": "/realtime",
                                "protocol": "WebSocket",
                                "description": "Endpoint for realtime voice interactions",
                                "message_format": {"type": "input_audio_buffer.append", "data": "base64 encoded audio data"},
                                "required_env_vars": [
                                    "AZURE_OPENAI_API_KEY",
                                    "AZURE_OPENAI_ENDPOINT",
                                    "AZURE_OPENAI_REALTIME_DEPLOYMENT",
                                ],
                                "available_voice_options": ["alloy", "echo", "fable", "onyx", "nova", "shimmer", "coral"],
                            }
                        }
                    },
                }
            },
        )
        def get_realtime_info():
            """Provides documentation about the realtime WebSocket endpoint."""
            return {
                "websocket_endpoint": "/realtime",
                "protocol": "WebSocket",
                "description": "Endpoint for realtime voice interactions with the Azure OpenAI Realtime API",
                "message_format": {"type": "input_audio_buffer.append", "data": "base64 encoded audio data"},
                "response_format": {
                    "transcription": "The transcribed text from the user's audio",
                    "assistant_response": "The assistant's response based on the knowledge base",
                    "audio_response": "Base64 encoded audio response from the assistant",
                },
                "required_env_vars": [
                    "AZURE_OPENAI_API_KEY",
                    "AZURE_OPENAI_ENDPOINT",
                    "AZURE_OPENAI_REALTIME_DEPLOYMENT",
                ],
                "available_voice_options": ["alloy", "echo", "fable", "onyx", "nova", "shimmer", "coral"],
                "current_voice": os.getenv("AZURE_OPENAI_REALTIME_VOICE_CHOICE", "coral"),
                "speech_engine": os.getenv("SPEECH_ENGINE", "openai"),
                "test_client_path": "/test/realtime/index.html",
                "documentation": "See the README at /test/realtime/README.md for detailed usage instructions",
            }

        if self.app_settings.add_memory:
            # Add API route for the agent
            self.runnable_factory.get_runnable().with_types(input_type=Input, output_type=Output)
        else:
            self.runnable_factory.get_runnable(include_history=False).with_types(
                input_type=Input, output_type=Output
            )

        @self.app.post(
            "/invoke",
            response_model=Dict[str, Any],
            summary="Invoke the runnable",
            description="This endpoint invokes the runnable with the provided input and configuration.",
            responses={
                200: {
                    "description": "Successful invocation",
                    "content": {"application/json": {"example": {"result": "The result of the runnable"}}},
                },
                401: {
                    "description": "Unauthorized",
                    "content": {
                        "application/json": {
                            "example": {"detail": "Please provide authorization header as: 'Bearer <token>'"}
                        }
                    },
                },
                500: {
                    "description": "Internal Server Error",
                    "content": {
                        "application/json": {
                            "example": {"detail": "Error while decoding token: <error_message>"}
                        }
                    },
                },
            },
        )
        @anonymize
        async def invoke(request: Request, payload: Payload):
            with tracer.start_as_current_span("".join(request.url.path)) as request_span:
                request_span.set_attribute("source_ip", self.get_source_ip(request))
                body = await request.body()
                body = json.loads(body)
                input_data = body.get("input")
                config_data = body.get("config")
                result = await invoke_runnable(input_data, config_data, self.runnable_factory)
                logger.error(f"Result: {result}")
                return result

        @self.app.post(
            "/stream_events",
            response_model=Output,
            summary="Invoke the runnable using add_routes",
            description="This endpoint invokes the runnable with provided input and config via add_routes.",
            responses={
                200: {
                    "description": "Successful invocation",
                    "content": {"application/json": {"example": {"result": "The result of the runnable"}}},
                },
            },
        )
        @anonymize
        async def stream_events(request: Request, payload: Payload):
            async def event_stream():
                body = await request.body()
                body = json.loads(body)
                input_data = body.get("input")
                config_data = body.get("config")
                async for event in self.runnable_factory.get_runnable().astream_events(
                    input_data, config_data, version="v2", include_types="chat_model"
                ):
                    # Unpack AIMessageChunk if present
                    event_type = event.get("event")
                    logger.debug("Event: %s", str(event))
                    data = event.get("data", {})
                    metadata = event.get("metadata")
                    logger.debug("Metadata: %s", str(metadata))
                    if metadata:
                        node = metadata.get("langgraph_node")
                        logger.debug("langgraph_node: %s", node)
                    chunk = data.get("chunk")

                    if chunk:
                        content = chunk.content
                        if event_type == "on_chat_model_stream" and content and node and node == "agent":
                            logger.debug(f"Event that chunk came from: {event}")
                            yield content

            return StreamingResponse(event_stream(), media_type="text/event-stream")

    def setup_realtime_routes(self):
        """Add WebSocket endpoint for realtime voice interactions."""
        from api.realtime import BotifyRealtime
        import os

        @self.app.get("/realtime-status")
        async def realtime_status():
            """
            Get the status of the realtime voice API configuration.

            This endpoint provides information about the configuration status
            of the realtime voice API, including:
            - Whether the required environment variables are set
            - The current turn detection type configuration
            - The WebSocket library availability

            Returns:
                dict: Status information about the realtime voice API
            """
            # Check required environment variables
            required_vars = ["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_REALTIME_DEPLOYMENT"]
            missing_vars = [var for var in required_vars if not os.getenv(var)]

            # Check turn detection type
            turn_detection_type = os.getenv("AZURE_SPEECH_SERVICES_TURN_DETECTION_TYPE", "server_vad")

            # Check WebSocket library availability
            websocket_libraries = []
            try:
                import websockets

                websocket_libraries.append("websockets")
            except ImportError:
                pass

            try:
                import wsproto

                websocket_libraries.append("wsproto")
            except ImportError:
                pass

            return {
                "status": "ok" if not missing_vars and websocket_libraries else "error",
                "environment_config": {
                    "missing_vars": missing_vars,
                    "all_required_vars_set": len(missing_vars) == 0,
                    "turn_detection_type": turn_detection_type,
                    "end_of_utterance_supported": turn_detection_type == "cascaded",
                },
                "websocket_support": {
                    "libraries_available": websocket_libraries,
                    "has_websocket_support": len(websocket_libraries) > 0,
                },
                "version": self.app.version,
            }

        @self.app.get("/realtime-info")
        async def realtime_info():
            """
            Get information about how to use the realtime WebSocket API.

            This endpoint provides documentation about the WebSocket endpoint,
            including how to connect, the message format, and configuration options.

            Returns:
                dict: Documentation about the realtime WebSocket API
            """
            return {
                "websocket_endpoint": "/realtime",
                "description": "WebSocket endpoint for real-time voice interactions",
                "connection": {"url": "ws://hostname:port/realtime", "protocols": ["websocket"]},
                "client_messages": [
                    {"type": "input_audio_buffer.append", "data": "base64-encoded audio data"}
                ],
                "server_messages": [
                    {"type": "conversation.item.input_audio_transcription.completed", "transcript": "transcribed user speech"},
                    {"type": "response.audio_transcript.delta", "delta": "partial response text"},
                    {"type": "response.audio_transcript.done", "timestamp": "timestamp when response is complete"},
                ],
                "configuration": {
                    "turn_detection_types": {
                        "server_vad": "Basic voice activity detection (default)",
                        "cascaded": "Advanced detection with end-of-utterance support",
                    },
                    "environment_variables": {
                        "AZURE_SPEECH_SERVICES_TURN_DETECTION_TYPE": "Turn detection type (server_vad or cascaded)",
                        "AZURE_OPENAI_REALTIME_VOICE_CHOICE": "Voice to use for responses (e.g., 'coral')",
                    },
                },
                "test_client": "/workspaces/botify/apps/bot-service/test/realtime/index.html",
            }

        @self.app.websocket("/realtime")
        async def realtime_endpoint(websocket: WebSocket):
            """
            WebSocket endpoint for real-time voice interactions with the Azure OpenAI Realtime API.

            This endpoint allows for bidirectional audio streaming with Azure OpenAI's Realtime API.
            The client can send audio data to the server, which will be transcribed and processed,
            and receive responses both as text and synthesized audio.

            Args:
                websocket (WebSocket): Client WebSocket connection.

            Protocol:
                - Client connects via WebSocket to /realtime
                - Client sends audio data in base64 format with message type 'input_audio_buffer.append'
                - Server transcribes audio and processes it using the knowledge base
                - Server streams responses back to the client
            """
            with tracer.start_as_current_span("realtime_endpoint") as span:
                await websocket.accept()
                logger.info("WebSocket connection established")
                rtmt = None
                try:
                    # Validate required environment variables for real-time
                    required_vars = [
                        "AZURE_OPENAI_API_KEY",
                        "AZURE_OPENAI_ENDPOINT",
                        "AZURE_OPENAI_REALTIME_DEPLOYMENT",
                    ]
                    missing_vars = [var for var in required_vars if not os.getenv(var)]
                    if missing_vars:
                        error_msg = f"Missing environment variables for real-time: {', '.join(missing_vars)}"
                        logger.error(error_msg)
                        await websocket.close(code=1002, reason=error_msg[:100])  # Truncate to 100 chars
                        return

                    engine = os.getenv("SPEECH_ENGINE", "openai")
                    if engine == "openai":
                        api_key = os.getenv("AZURE_OPENAI_API_KEY")
                        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
                    elif engine == "azure":
                        api_key = os.getenv("AZURE_SPEECH_SERVICES_KEY")
                        endpoint = os.getenv("AZURE_SPEECH_SERVICES_ENDPOINT")
                    else:
                        error_msg = "SPEECH_ENGINE env must be: openai or azure"
                        logger.error(error_msg)
                        await websocket.close(code=1002, reason=error_msg)
                        return

                    logger.info(f"Speech engine selected: {engine}")
                    span.set_attribute("speech_engine", engine)

                    # Initialize BotifyRealtime with the existing search tool
                    rtmt = BotifyRealtime(
                        engine=engine,
                        api_key=api_key,
                        endpoint=endpoint,
                        deployment=os.getenv("AZURE_OPENAI_REALTIME_DEPLOYMENT"),
                        voice_choice=os.getenv("AZURE_OPENAI_REALTIME_VOICE_CHOICE", "coral"),
                    )
                    await rtmt._forward_messages(websocket)

                except WebSocketDisconnect:
                    logger.info("WebSocket disconnected by client")
                except Exception as e:
                    error_msg = f"WebSocket error: {str(e)}"[:100]  # Truncate to fit WebSocket limit
                    logger.error(error_msg)
                    if not websocket.client_state == 2:  # Check if WebSocket is not already closed (2 = DISCONNECTED)
                        await websocket.close(code=1011, reason=error_msg)
                finally:
                    if rtmt:
                        await rtmt.cleanup()
                        logger.info("Cleaned up BotifyRealtime resources")


# Instantiate the settings and factory
app_settings = AppSettings()
runnable_factory = RunnableFactory()
app_factory = AppFactory(app_settings, runnable_factory)
app = app_factory.app

# Run the server
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
