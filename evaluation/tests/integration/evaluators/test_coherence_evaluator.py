import os
import unittest

import pandas as pd
from evaluators.coherence import CoherenceEvaluator
from promptflow.core import AzureOpenAIModelConfiguration
from promptflow.evals.evaluate import evaluate
from run_evaluations.evaluate_full_flow import call_full_flow


class TestTopicDetection(unittest.TestCase):
    def get_evaluators(self, model_config):
        return {
            "display_response_coherence": CoherenceEvaluator(model_config),
        }

    def get_evaluator_config(self):
        return {
            "display_response_coherence": {
                "question": "${data.question}",
                "answer": "${target.display_response}",
            }
        }

    model_config = AzureOpenAIModelConfiguration(
        azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT_EVAL"),
        api_key=os.environ.get("AZURE_OPENAI_API_KEY_EVAL"),
        azure_deployment=os.environ.get("AZURE_OPENAI_MODEL_NAME_EVAL"),
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION"),
    )

    def test(self):
        datafilepath = "evaluation/data_files/end_to_end/single_turn/test_chatbot.jsonl"
        result = evaluate(
            target=call_full_flow,
            evaluation_name="Botify Full Flow Evaluation",
            data=datafilepath,
            evaluators=self.get_evaluators(self.model_config),
            evaluator_config=self.get_evaluator_config(),
        )
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
