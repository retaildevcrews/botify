import json
import os

from app.app_settings import AppSettings
from jsonschema import validate


class ResponseSchema:
    def __init__(self):
        app_settings = AppSettings(load_environment_config=False)
        self.schema_name = app_settings.response_schema_name

    def get_response_schema_as_string(self):
        current_path = os.path.dirname(__file__)
        schema_path = os.path.join(current_path, "json/" + self.schema_name)
        with open(schema_path, "r") as file:
            schema = json.load(file)
        minified_json = json.dumps(schema, separators=(",", ":"))
        return minified_json

    def validate_response(self, content):
        schema = json.loads(self.get_response_schema_as_string())
        content = json.loads(content)
        validate(instance=content, schema=schema)
