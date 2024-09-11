import unittest
import uuid
import os

import pandas as pd

from run_evaluations.evaluate_bot_behavior import evaluate_bot_behavior
from promptflow.core import AzureOpenAIModelConfiguration


class TestEvaluateBotBehavior(unittest.TestCase):

    def test(self):
        datafilepath = "/workspaces/botify/evaluation/data_files/bot_behavior.jsonl"
        model_config = AzureOpenAIModelConfiguration(
            azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT_EVAL"),
            api_key=os.environ.get("AZURE_OPENAI_API_KEY_EVAL"),
            azure_deployment=os.environ.get("AZURE_OPENAI_MODEL_NAME_EVAL"),
            api_version=os.environ.get("AZURE_OPENAI_API_VERSION"),
        )
        result = evaluate_bot_behavior(
            dataset_path=datafilepath,
            model_config=model_config
        )
        print(result)
        self.assertEqual(result["failed_record_count"], 0)


if __name__ == "__main__":
    unittest.main()
