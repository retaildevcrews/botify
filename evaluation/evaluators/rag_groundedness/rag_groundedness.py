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
import json


class RAGGroundednessEvaluator:

    def __init__(self, model_config: AzureOpenAIModelConfiguration):
        prompty_model_config = {"configuration": model_config}
        (
            prompty_model_config.update({"parameters": {"extra_headers": {"x-ms-user-agent": USER_AGENT}}})
            if USER_AGENT and isinstance(model_config, AzureOpenAIModelConfiguration)
            else None
        )
        current_dir = os.path.dirname(__file__)
        prompty_path = os.path.join(current_dir, "rag_groundedness.prompty")
        self._flow = load_flow(source=prompty_path, model=prompty_model_config)

    def __call__(self, *, answer: str, context: str, **kwargs):
        try:
            # Run the evaluation flow
            llm_output = self._flow(answer=answer, context=context)
            output = json.loads(llm_output)
            score = output["score"]
            reason = output["explanation"]
        except Exception as e:
            score = -1
            reason = f"Error in RAGGroundednessEvaluator: {e}"
        return {"score": score, "reason": reason}
