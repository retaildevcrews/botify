# ---------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# ---------------------------------------------------------

import os

from promptflow.client import load_flow
from promptflow.core import AzureOpenAIModelConfiguration

try:
    from promptflow.evals._user_agent import USER_AGENT
except ImportError:
    USER_AGENT = None


class PiiAnonymizerQualityEvaluator:
    def __init__(self, model_config: AzureOpenAIModelConfiguration):
        prompty_model_config = {"configuration": model_config}
        prompty_model_config.update({"parameters": {"extra_headers": {"x-ms-user-agent": USER_AGENT}}}) \
            if USER_AGENT and isinstance(model_config, AzureOpenAIModelConfiguration) else None
        current_dir = os.path.dirname(__file__)
        prompty_path = os.path.join(
            current_dir, "pii_anonymizer_quality.prompty")
        self._flow = load_flow(source=prompty_path, model=prompty_model_config)

    def __call__(self, *, question: str, anonymized_question: str, anonymizer_entities: str, **kwargs):
        """
        Evaluate PII redaction.

        :param question: The question with PII to be evaluated.
        :type question: str
        :param anonymized_question: The anonymized question to compare with question.
        :type anonymized_question: str
        :param anonymizer_entities: List of PII information to detect
        :type anonymizer_entities: list

        :return: The score of how well PII was redacted with reason for score
        :rtype: dict
        """
        try:
            # Run the evaluation flow
            llm_output = self._flow(
                question=question, anonymized_question=anonymized_question, anonymizer_entities=anonymizer_entities)
            score = llm_output['score']
            reason = llm_output['reason']
        except Exception as e:
            score = -1
            reason = f"Error in PiiAnonymizerQualityEvaluator: {
                e} LLM Response is: {llm_output}"
        return {"score": score, "reason": reason}
