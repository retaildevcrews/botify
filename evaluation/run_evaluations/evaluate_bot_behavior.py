import argparse
import os
import json
import uuid
import pandas as pd
import time

from common.schemas import ResponseSchema
from evaluators import (BotBehaviorEvaluator)
from promptflow.core import AzureOpenAIModelConfiguration
from promptflow.evals.evaluate import evaluate
from evaluation_utils.runnable_caller import RunnableCaller
from evaluation_utils.evaluator_config import EvaluatorConfigList
from evaluation_utils.formatting_utils import string_to_dict
from run_evaluations.utils import run_evaluation


def call_full_flow(*, question, **kwargs):
    runnable_caller = RunnableCaller()
    session_id = uuid.uuid4()
    user_id = "tdaley"
    bot_response = runnable_caller.call_full_flow(
        question, session_id, user_id, "")
    print(f'Bot Response: {bot_response}')
    answer = bot_response["answer"]
    config = bot_response["app_config"]
    config_hash = bot_response["app_config_hash"]
    prompt_tokens = bot_response["prompt_tokens"]
    completion_tokens = bot_response["completion_tokens"]
    total_tokens = bot_response["total_tokens"]
    start_time = bot_response["start_time"]
    end_time = bot_response["end_time"]
    ellapsed_time = bot_response["ellapsed_time"]

    # Return dictionary with all the necessary information for reporting or
    # evaluation purposes,
    result = {"question": question,
              "answer": answer,
              "app_config": config,
              "app_config_hash": config_hash, "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens, "total_tokens": total_tokens, "start_time": start_time, "end_time": end_time, "ellapsed_time": ellapsed_time}

    return result


def get_evaluator_configs(config: AzureOpenAIModelConfiguration):
    '''
    This function returns an EvaluatorConfigList object that contains all the evaluator configurations
    parameters: config: AzureOpenAIModelConfiguration object
    '''
    evaluator_configs = EvaluatorConfigList()
    evaluator_configs.append_config("bot_behavior", BotBehaviorEvaluator(config), {
        "question": "${data.question}", "answer": "${target.answer}", "expected_behavior": "${data.expected_behavior}"})
    return evaluator_configs
