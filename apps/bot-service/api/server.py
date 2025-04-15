#!/usr/bin/env python

import json
import logging
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
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
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


# Instantiate the settings and factory
app_settings = AppSettings()
runnable_factory = RunnableFactory()
app_factory = AppFactory(app_settings, runnable_factory)
app = app_factory.app

# Run the server
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
