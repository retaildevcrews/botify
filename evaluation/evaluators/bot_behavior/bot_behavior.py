# ---------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# ---------------------------------------------------------

import os

import numpy as np
from promptflow._utils.async_utils import async_run_allowing_running_loop
from promptflow.core import AsyncPrompty, AzureOpenAIModelConfiguration

try:
    from promptflow.evals._user_agent import USER_AGENT
except ImportError:
    USER_AGENT = None


class _AsyncBotBehaviorEvaluator:
    PROMPTY_FILE = "bot_behavior.prompty"
    LLM_CALL_TIMEOUT = 600

    def __init__(self, model_config: AzureOpenAIModelConfiguration):
        if model_config.api_version is None:
            model_config.api_version = "2024-02-15-preview"

        prompty_model_config = {"configuration": model_config, "parameters": {"extra_headers": {}}}

        # Handle "RuntimeError: Event loop is closed" from httpx AsyncClient
        # https://github.com/encode/httpx/discussions/2959
        prompty_model_config["parameters"]["extra_headers"].update({"Connection": "close"})

        if USER_AGENT and isinstance(model_config, AzureOpenAIModelConfiguration):
            prompty_model_config["parameters"]["extra_headers"].update({"x-ms-useragent": USER_AGENT})

        current_dir = os.path.dirname(__file__)
        prompty_path = os.path.join(current_dir, self.PROMPTY_FILE)
        self._flow = AsyncPrompty.load(source=prompty_path, model=prompty_model_config)

    async def __call__(self, *, question: str, answer: str, expected_behavior: str, **kwargs):
        try:
            # Run the evaluation flow
            llm_output = await self._flow(
                question=question,
                answer=answer,
                expected_behavior=expected_behavior,
                timeout=self.LLM_CALL_TIMEOUT,
                **kwargs,
            )
            score = llm_output["score"]
            reason = llm_output["reason"]
        except Exception as e:
            score = np.NaN
            reason = f"Error when running evaluator: {
                e} LLM Response is: {llm_output}"
        return {"score": score, "reason": reason}


class BotBehaviorEvaluator:

    def __init__(self, model_config: AzureOpenAIModelConfiguration):
        self._async_evaluator = _AsyncBotBehaviorEvaluator(model_config)

    def __call__(self, *, question: str, answer: str, expected_behavior: str, **kwargs):
        """
        Evaluate the behavior of the bot based on the question and expected behavior provided.
        """
        return async_run_allowing_running_loop(
            self._async_evaluator,
            question=question,
            answer=answer,
            expected_behavior=expected_behavior,
            **kwargs,
        )

    def _to_async(self):
        return self._async_evaluator
