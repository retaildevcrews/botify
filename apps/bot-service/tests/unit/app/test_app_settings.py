import os
import unittest

from app.environment_config import EnvironmentConfig
from app.settings import AppSettings


class TestStringMethods(unittest.TestCase):
    def test_secrets_dont_print(self):
        environment_config = EnvironmentConfig(
            unit_test_mode=True,
            azure_search_key="1234567890",
            content_safety_key="1234567890",
            openai_api_key="1234567890",
            cosmos_connection_string="1234567890",
        )
        app_settings = AppSettings(environment_config=environment_config)
        self.assertEqual(str(app_settings.environment_config.azure_search_key), "**********")
        self.assertEqual(str(app_settings.environment_config.content_safety_key), "**********")
        self.assertEqual(str(app_settings.environment_config.openai_api_key), "**********")
        self.assertEqual(str(app_settings.environment_config.cosmos_connection_string), "**********")

    def test_app_settings_full(self):
        os.environ["LOG_LEVEL"] = "DEBUG"
        os.environ["AZURE_OPENAI_API_VERSION"] = "2024-04-01-preview"
        os.environ["OPENAI_API_VERSION"] = "2024-04-01-preview"
        os.environ["AZURE_COSMOSDB_ENDPOINT"] = "https://localhost:8081"
        os.environ["AZURE_COSMOSDB_NAME"] = "database"
        os.environ["AZURE_COSMOSDB_CONTAINER_NAME"] = "container"
        os.environ["AZURE_COSMOSDB_CONNECTION_STRING"] = "connection_string"
        os.environ["AZURE_SEARCH_ENDPOINT"] = "https://localhost:8081"
        os.environ["AZURE_SEARCH_KEY"] = "key"
        os.environ["AZURE_SEARCH_API_VERSION"] = "api_version"
        os.environ["AZURE_SEARCH_INDEX_NAME"] = "index_name"
        os.environ["AZURE_OPENAI_ENDPOINT"] = "https://localhost:8081"
        os.environ["AZURE_OPENAI_API_KEY"] = "key"
        os.environ["AZURE_OPENAI_CLASSIFIER_MODEL_NAME"] = "model_name"
        os.environ["AZURE_OPENAI_MODEL_NAME"] = "model_name"
        os.environ["CONTENT_SAFETY_ENDPOINT"] = "DEBUG"
        os.environ["CONTENT_SAFETY_KEY"] = "key"
        app_settings = AppSettings()
        self.assertEqual(app_settings.environment_config.log_level, "DEBUG")
        self.assertEqual(app_settings.environment_config.openai_api_version, "2024-04-01-preview")
        self.assertEqual(app_settings.environment_config.openai_endpoint, "https://localhost:8081")
        self.assertEqual(app_settings.environment_config.openai_api_key.get_secret_value(), "key")
        self.assertEqual(app_settings.environment_config.openai_deployment_name, "model_name")
        self.assertEqual(app_settings.environment_config.cosmos_endpoint, "https://localhost:8081")
        self.assertEqual(app_settings.environment_config.cosmos_database, "database")
        self.assertEqual(app_settings.environment_config.cosmos_container, "container")
        self.assertEqual(
            app_settings.environment_config.cosmos_connection_string.get_secret_value(), "connection_string"
        )
        self.assertEqual(app_settings.environment_config.azure_search_endpoint, "https://localhost:8081")
        self.assertEqual(app_settings.environment_config.azure_search_key.get_secret_value(), "key")
        self.assertEqual(app_settings.environment_config.azure_search_api_version, "api_version")
        self.assertEqual(app_settings.environment_config.doc_index, "index_name")
        self.assertEqual(app_settings.environment_config.content_safety_endpoint, "DEBUG")
        self.assertEqual(app_settings.environment_config.content_safety_key.get_secret_value(), "key")
        self.assertIsNotNone(app_settings)


if __name__ == "__main__":
    unittest.main()
