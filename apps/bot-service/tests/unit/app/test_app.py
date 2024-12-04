import os
import unittest

from app.settings import AppSettings, EnvironmentConfig
from fastapi.testclient import TestClient
from langchain_core.runnables import Runnable, RunnableLambda

os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["AZURE_OPENAI_API_VERSION"] = "2024-06-01"
os.environ["OPENAI_API_VERSION"] = "2024-06-01"
os.environ["AZURE_COSMOSDB_ENDPOINT"] = "https://localhost:8081"
os.environ["AZURE_COSMOSDB_NAME"] = "database"
os.environ["AZURE_COSMOSDB_CONTAINER_NAME"] = "container"
os.environ["AZURE_COSMOSDB_CONNECTION_STRING"] = "connection_string"
os.environ["AZURE_SEARCH_ENDPOINT"] = "https://localhost:8081"
os.environ["AZURE_SEARCH_KEY"] = "key"
os.environ["AZURE_SEARCH_API_VERSION"] = "api_version"
os.environ["AZURE_SEARCH_INDEX_NAME"] = "index_name"
os.environ["AZURE_SEARCH_INDEX_NAME_NO_OPTIONS"] = "index_name"
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://localhost:8081"
os.environ["AZURE_OPENAI_API_KEY"] = "key"
os.environ["AZURE_OPENAI_MODEL_NAME"] = "model_name"
os.environ["AZURE_OPENAI_CLASSIFIER_MODEL_NAME"] = "model_name"
os.environ["CONTENT_SAFETY_ENDPOINT"] = "DEBUG"
os.environ["CONTENT_SAFETY_KEY"] = "key"

from api.server import AppFactory

class MockRunnableFactory:
    def get_runnable(self) -> Runnable:
        simple_runnable = RunnableLambda(
            lambda question_input: {
                "question": question_input,
                "history": [],
                "output": question_input,
                "intermediate_steps": [],
            }
        )
        return simple_runnable


environment_config = EnvironmentConfig(anonymize_input=True, anonymizer_mode="CUSTOM")
app_settings = AppSettings(environment_config=environment_config)
runnable_factory = MockRunnableFactory()
app = AppFactory(app_settings=app_settings, runnable_factory=runnable_factory).app


class TestApp(unittest.TestCase):
    def test_anonymizer_is_called(self):
        client = TestClient(app)
        config = {"configurable": {"session_id": "session_id", "user_id": "user_id"}}
        payload = {"input": {"question": "hello there my phone number is 512-111-1111"}, "config": config}

        response = client.post("/agent/invoke", json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertIn("hello there my phone number is redacted_value", response.text)


if __name__ == "__main__":
    unittest.main()
