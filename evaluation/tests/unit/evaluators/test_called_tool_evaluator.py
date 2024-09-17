import unittest

from evaluators.called_tool_evaluator import CalledToolEvaluator


class TestCalledToolEvaluator(unittest.TestCase):

    def test_notools(self):
        evaluator = CalledToolEvaluator()
        result = evaluator([], [])
        self.assertEqual(result["score"], 1.0)
        self.assertEqual(result["called not expected"], [])
        self.assertEqual(result["expected not called"], [])

    def test_correct_tools(self):
        evaluator = CalledToolEvaluator()
        result = evaluator(["tool"], ["tool"])
        self.assertEqual(result["score"], 1.0)
        self.assertEqual(result["called not expected"], [])
        self.assertEqual(result["expected not called"], [])

    def test_expected_tool_not_called(self):
        evaluator = CalledToolEvaluator()
        result = evaluator(["tool"], [])
        self.assertEqual(result["score"], 0.0)
        self.assertEqual(result["called not expected"], [])
        self.assertEqual(result["expected not called"], ["tool"])

    def test_no_expected_tool_but_tool_called(self):
        evaluator = CalledToolEvaluator()
        result = evaluator([], ["tool"])
        self.assertEqual(result["score"], 0.0)
        self.assertEqual(result["called not expected"], ["tool"])
        self.assertEqual(result["expected not called"], [])

    def test_multiple_tools(self):
        evaluator = CalledToolEvaluator()
        result = evaluator(["tool1", "tool2"], ["tool1", "tool2"])
        self.assertEqual(result["score"], 1.0)
        self.assertEqual(result["called not expected"], [])
        self.assertEqual(result["expected not called"], [])

    def test_multiple_tools_one_missing(self):
        evaluator = CalledToolEvaluator()
        result = evaluator(["tool1", "tool2"], ["tool1"])
        self.assertEqual(result["score"], 0.5)
        self.assertEqual(result["called not expected"], [])
        self.assertEqual(result["expected not called"], ["tool2"])

    def test_multiple_tools_one_extra(self):
        evaluator = CalledToolEvaluator()
        result = evaluator(["tool1", "tool2"], ["tool1", "tool2", "tool3"])
        self.assertEqual(result["score"], 0.5)
        self.assertEqual(result["called not expected"], ["tool3"])
        self.assertEqual(result["expected not called"], [])


if __name__ == "__main__":
    unittest.main()
