# ---------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# ---------------------------------------------------------
class CalledToolEvaluator:
    """
    This evaluator is used to evaluate whether the tools called in the flow are
    the tools that are expected to be called in the flow. The expected tools are provided
    as ground truth in the test data.

    The evaluator returns a score of 1 if the tools called in the flow are the same as the
    tools that are expected to be called in the flow. If the tools called in the flow are not
    the same as the tools that are expected to be called in the flow, the delta between the
    expected and actual tools is calculated and the score is calculated as 1 - (delta / num_expected_tools).
    Delta can be calculated as the number of tools that are expected to be called in the flow but are not
    + the number of tools that are called in the flow but are not expected.  The floor of the score is 0.
    """

    def __init__(self):
        self.name = "CalledToolEvaluator"

    def __call__(self, expected_called_tools, called_tools):
        """
        Performs the evaluation
        params:
        expected_called_tools: list of tools that are expected to be called in the flow
        called_tools: list of tools that are called in the flow
        """
        result = {}
        num_expected_called_tools = len(expected_called_tools)
        # Get tools called but not expected
        called_not_expected = list(set(called_tools) - set(expected_called_tools))
        # Get tools expected but not called
        expected_not_called = list(set(expected_called_tools) - set(called_tools))
        # Calculate number of incorrect tools
        num_incorrect_tools = len(called_not_expected) + len(expected_not_called)
        # Calculate score
        if num_expected_called_tools == 0:
            score = 0 if num_incorrect_tools > 0 else 1
        else:
            score = max(0, 1 - (num_incorrect_tools / num_expected_called_tools))
        # Output results
        result["score"] = score
        result["called not expected"] = called_not_expected
        result["expected not called"] = expected_not_called
        return result
