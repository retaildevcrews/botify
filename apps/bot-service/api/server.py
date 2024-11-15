#!/usr/bin/env python

import logging
from pathlib import Path
from typing import Any, List, TypedDict

import _additional_version_info
import pydantic
import toml
from api.pii_utils import Anonymizer, anonymize, invoke as invoke_runnable
from app.settings import AppSettings
from botify_langchain.runnable_factory import RunnableFactory
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from langserve import add_routes
from fastapi import Request
from typing import Dict
from api.models import Payload
import json

# Configure logging
logger = logging.getLogger(__name__)


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
            description="An API server utilizing LangChain's Runnable interfaces to create a chatbot that uses an index as grounding material for answering questions.",
        )
        self.setup_middleware()
        self.setup_routes()
        logging.getLogger().setLevel(self.app_settings.environment_config.log_level)

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

        # Instantiate the anonymizer
        dependencies: List[Depends] = []
        if self.app_settings.environment_config.anonymize_input:
            anonymizer = Anonymizer()
            dependencies.append(Depends(anonymizer.set_body))

        if self.app_settings.add_memory:
            # Add API route for the agent
            runnable = self.runnable_factory.get_runnable().with_types(input_type=Input, output_type=Output)
        else:
            runnable = self.runnable_factory.get_runnable(include_history=False).with_types(
                input_type=Input, output_type=Output
            )
        
        @self.app.post(
            "/agent/invoke",
            response_model=Output,
            summary="Invoke the runnable",
            description="This endpoint invokes the runnable with the provided input and configuration.",
            responses={
                200: {
                    "description": "Successful invocation",
                    "content": {
                        "application/json": {
                            "example": {
                                "result": "The result of the runnable"
                            }
                        }
                    }
                },
            }
        )
        @anonymize(self.app_settings)
        async def invoke(request: Request, payload: Payload):
            with tracer.start_as_current_span("".join(request.url.path)) as request_span:
                request_span.set_attribute("source_ip", self.get_source_ip(request))
                body = await request.body()
                body = json.loads(body)
                input_data = body.get("input")
                config_data = body.get("config")
                if ("user_id" in config_data["configurable"]):
                    request_span.set_attribute("user_id", config_data["configurable"]["user_id"])
                if ("session_id" in config_data["configurable"]):
                    request_span.set_attribute("session_id", config_data["configurable"]["session_id"])
                logger.info(f"Received input: {input_data}")
                logger.info(f"Received config: {config_data}")
                return await invoke_runnable(input_data, config_data, self.runnable_factory, self.app_settings.invoke_retry_count)

# Instantiate the settings and factory
app_settings = AppSettings()
runnable_factory = RunnableFactory()
app_factory = AppFactory(app_settings, runnable_factory)
app = app_factory.app

# Run the server
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
