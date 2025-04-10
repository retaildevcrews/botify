import unittest

from evaluators import (
    CoherenceEvaluator,
    FluencyEvaluator,
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
            "rows": [],
        }

    def test_evaluators(self):

        result = evaluate_full_flow(
            dataset_path="path",
            model_config=self.model_config,
            evaluate_function=self.evaluate_tester,
            ignore_environment_validation=True,
            save_results=False,
        )

        evaluators = result["evaluators"]

        expected_evaluator_count = 4
        self.assertEqual(len(evaluators), expected_evaluator_count)

        validate_evaluator(self, evaluators, "response_groundedness", RAGGroundednessEvaluator)
        validate_evaluator(self, evaluators, "response_coherence", CoherenceEvaluator)
        validate_evaluator(self, evaluators, "response_fluency", FluencyEvaluator)
        validate_evaluator(self, evaluators, "response_relevance", RelevanceOptionalContextEvaluator)

        evaluator_config = result["evaluator_config"]

        expected_evaluator_config_count = 4
        self.assertEqual(len(evaluator_config), expected_evaluator_config_count)

        validate_evaluator_config(
            self, evaluator_config, "response_groundedness", "question", "${data.question}"
        )

        validate_evaluator_config(
            self, evaluator_config, "response_groundedness", "answer", "${target.answer}"
        )

        validate_evaluator_config(
            self, evaluator_config, "response_groundedness", "context", "${target.search_results}"
        )

        validate_evaluator_config(self, evaluator_config, "response_fluency", "question", "${data.question}")

        validate_evaluator_config(self, evaluator_config, "response_fluency", "answer", "${target.answer}")

        validate_evaluator_config(
            self, evaluator_config, "response_coherence", "question", "${data.question}"
        )
        validate_evaluator_config(self, evaluator_config, "response_coherence", "answer", "${target.answer}")

        validate_evaluator_config(
            self, evaluator_config, "response_relevance", "question", "${data.question}"
        )
        validate_evaluator_config(self, evaluator_config, "response_relevance", "answer", "${target.answer}")
        validate_evaluator_config(
            self, evaluator_config, "response_relevance", "context", "${target.search_results}"
        )

    def tearDown(self):
        # Clean up any necessary objects or state after each test
        pass


if __name__ == "__main__":
    unittest.main()
