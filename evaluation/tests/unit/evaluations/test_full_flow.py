import unittest

from evaluators import (
    CalledToolEvaluator,
    CoherenceEvaluator,
    FluencyEvaluator,
    JsonSchemaValidationEvaluator,
    RAGGroundednessEvaluator,
    RelevanceOptionalContextEvaluator,
)
from run_evaluations.evaluate_full_flow import evaluate_full_flow
from tests.test_utils.evalutation_test_utils import validate_evaluator, validate_evaluator_config


class TestEvalFullFlow(unittest.TestCase):

    class Config:
        def __init__(self, api_version):
            self.api_version = api_version

    def setUp(self):
        # Set up any necessary objects or state before each test
        self.model_config = self.Config(api_version="1.0")
        self.maxDiff = None

    # mock the evaluate function

    def evaluate_tester(self, target, evaluation_name, data, evaluators, evaluator_config):
        return {
            "target": target,
            "evaluation_name": evaluation_name,
            "data": data,
            "evaluators": evaluators,
            "evaluator_config": evaluator_config,
        }

    def test_evaluators(self):

        result = evaluate_full_flow(
            dataset_path="path",
            model_config=self.model_config,
            evaluate_function=self.evaluate_tester,
            ignore_environment_validation=True,
        )

        evaluators = result["evaluators"]

        expected_evaluator_count = 8
        self.assertEqual(len(evaluators), expected_evaluator_count)

        validate_evaluator(self, evaluators, "json_schema_validation", JsonSchemaValidationEvaluator)
        validate_evaluator(self, evaluators, "voice_summary_groundedness", RAGGroundednessEvaluator)
        validate_evaluator(self, evaluators, "display_response_groundedness", RAGGroundednessEvaluator)
        validate_evaluator(self, evaluators, "display_response_fluency", FluencyEvaluator)
        validate_evaluator(self, evaluators, "display_response_coherence", CoherenceEvaluator)
        validate_evaluator(self, evaluators, "voice_summary_fluency", FluencyEvaluator)
        validate_evaluator(self, evaluators, "voice_summary_coherence", CoherenceEvaluator)
        validate_evaluator(self, evaluators, "relevance", RelevanceOptionalContextEvaluator)

        evaluator_config = result["evaluator_config"]

        expected_evaluator_config_count = 8
        self.assertEqual(len(evaluator_config), expected_evaluator_config_count)

        validate_evaluator_config(
            self, evaluator_config, "json_schema_validation", "content", "${target.bot_response}"
        )

        validate_evaluator_config(
            self, evaluator_config, "display_response_groundedness", "question", "${data.question}"
        )
        validate_evaluator_config(
            self, evaluator_config, "display_response_groundedness", "answer", "${target.display_response}"
        )
        validate_evaluator_config(
            self, evaluator_config, "display_response_groundedness", "context", "${target.search_results}"
        )

        validate_evaluator_config(
            self, evaluator_config, "voice_summary_groundedness", "question", "${data.question}"
        )
        validate_evaluator_config(
            self, evaluator_config, "voice_summary_groundedness", "answer", "${target.voice_summary}"
        )
        validate_evaluator_config(
            self, evaluator_config, "voice_summary_groundedness", "context", "${target.search_results}"
        )

        validate_evaluator_config(
            self, evaluator_config, "display_response_fluency", "question", "${data.question}"
        )
        validate_evaluator_config(
            self, evaluator_config, "display_response_fluency", "answer", "${target.display_response}"
        )

        validate_evaluator_config(
            self, evaluator_config, "display_response_coherence", "question", "${data.question}"
        )
        validate_evaluator_config(
            self, evaluator_config, "display_response_coherence", "answer", "${target.display_response}"
        )

        validate_evaluator_config(
            self, evaluator_config, "voice_summary_fluency", "question", "${data.question}"
        )
        validate_evaluator_config(
            self, evaluator_config, "voice_summary_fluency", "answer", "${target.voice_summary}"
        )

        validate_evaluator_config(
            self, evaluator_config, "voice_summary_coherence", "question", "${data.question}"
        )
        validate_evaluator_config(
            self, evaluator_config, "voice_summary_coherence", "answer", "${target.voice_summary}"
        )

        validate_evaluator_config(self, evaluator_config, "relevance", "question", "${data.question}")
        validate_evaluator_config(self, evaluator_config, "relevance", "answer", "${target.bot_response}")
        validate_evaluator_config(self, evaluator_config, "relevance", "context", "${target.context}")

    def tearDown(self):
        # Clean up any necessary objects or state after each test
        pass


if __name__ == "__main__":
    unittest.main()
