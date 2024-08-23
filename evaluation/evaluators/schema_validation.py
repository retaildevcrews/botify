# ---------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# ---------------------------------------------------------
import json

from jsonschema import ValidationError, validate

class JsonSchemaValidationEvaluator:
    def __init__(self, schema):
        self.name = "SchemaValidationEvaluator"
        self.schema = schema

    def __call__(self, content):
        try:
            schema = json.loads(self.schema)
            content = json.loads(content)
            validate(instance=content, schema=schema)

        except json.JSONDecodeError as e:
            print('JSONDecodeError:', e)
            return 0
        except ValidationError as e:
            print('ValidationError:', e)
            return 0
        return 1
