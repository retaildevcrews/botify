import json
import os
from logging import getLogger

from app.settings import AppSettings
from jsonschema import validate

logger = getLogger(__name__)


class ResponseSchema:
    def __init__(self):
        self.app_settings = AppSettings(load_environment_config=False)
        self.schema = None
        self.schema_name = self.app_settings.response_schema_name
        self.selected_format_config = self.app_settings.selected_format_config

    def get_response_schema_json(self):
        current_path = os.path.dirname(__file__)
        schema_path = os.path.join(current_path, "json/" + self.app_settings.json_validation_schema_name)
        try:
            with open(schema_path, "r") as file:
                # Load the JSON schema from the file
                schema = json.load(file)
                return schema
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading response schema: {e}")
            raise e

    def get_response_schema_json_as_string(self):
        try:
            return json.dumps(self.get_response_schema_json(), separators=(",", ":"))
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading response schema: {e}")
            return ""

    def validate_json_response(self, content):
        if isinstance(content, str):
            content = json.loads(content)
        schema = self.get_response_schema_json()
        validate(instance=content, schema=schema)

    def get_response_schema(self):
        if self.selected_format_config == "json" or self.selected_format_config == "json_schema":
            return self.get_response_schema_json_as_string()
