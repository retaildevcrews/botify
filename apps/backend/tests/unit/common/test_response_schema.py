import unittest

from app.app_settings import AppSettings, EnvironmentConfig
from common.schemas import ResponseSchema


class TestStringMethods(unittest.TestCase):

    def test_get_response_schema_min_string(self):
        environment_config = EnvironmentConfig(unit_test_mode=True)
        app_settings = AppSettings(
            environment_config=environment_config,
            response_schema_name="response_schema.json",
        )
        schema = ResponseSchema().get_response_schema_as_string()
        expected_schema = """{"$schema":"http://json-schema.org/draft-07/schema#","title":" Rag Example Recommendation Response","type":"object","required":["voiceSummary","displayResponse"],"properties":{"voiceSummary":{"type":"string","description":"A brief summary of the response, intended for voice output."},"displayResponse":{"type":"string","description":"A more detailed message intended for display on screen, this can contain formatted text, this will be used in the chat interface."}}}"""
        self.assertEqual(expected_schema, schema)


if __name__ == "__main__":
    unittest.main()
