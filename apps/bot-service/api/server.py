#!/usr/bin/env python

import logging
from pathlib import Path
from typing import Any, List, TypedDict

import _additional_version_info
import pydantic
import toml
from app.settings import AppSettings
from botify_langchain.runnable_factory import RunnableFactory
from api.pii_utils import Anonymizer
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from langserve import add_routes

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
            description="An API server utilizing LangChain's Runnable interfaces to create a chatbot that uses an index as grounding material for answering questions."
        )
        self.setup_middleware()
        self.setup_routes()
        logging.getLogger().setLevel(self.app_settings.environment_config.log_level)

    def get_version(self) -> str:
        # Load the pyproject.toml file
        current_file_path = Path(__file__).resolve()
        pyproject_file_path = current_file_path.parent.parent / "pyproject.toml"
        pyproject = toml.load(pyproject_file_path)

        version = pyproject.get("tool", {}).get(
            "poetry", {}).get("version", "Version not found")
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
            anonymizer = Anonymizer(self.app_settings)
            dependencies.append(Depends(anonymizer.set_body))

        # Add API route for the agent
        add_routes(
            self.app,
            self.runnable_factory.get_runnable().with_types(
                input_type=Input, output_type=Output
            ),
            path="/agent",
            dependencies=dependencies,
            enabled_endpoints=["invoke", "stream_events", "playground"],
        )


# Instantiate the settings and factory
app_settings = AppSettings()
runnable_factory = RunnableFactory()
app_factory = AppFactory(app_settings, runnable_factory)
app = app_factory.app

# Run the server
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
