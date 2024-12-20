import argparse
import csv
import logging
import os
import time

import pandas as pd
from evaluation_utils.evaluator_config import EvaluatorConfigList
from evaluation_utils.formatting_utils import string_to_dict
from evaluation_utils.runnable_caller import RunnableCaller
from evaluators import (
    CoherenceEvaluator,
    FluencyEvaluator,
    RAGGroundednessEvaluator,
    RelevanceOptionalContextEvaluator,
)
from promptflow.core import AzureOpenAIModelConfiguration
from promptflow.evals.evaluate import evaluate
from run_evaluations.utils import run_evaluation

logger = logging.getLogger(__name__)


def call_full_flow(*, question, session_id, user_id, sbux_global_id, chat_history, **kwargs):
    runnable_caller = RunnableCaller()
    query_list = []
    called_tools = []
    # Call the full flow - this is the system under test
    # Call the full flow - this is the system under test
    logger.debug(
        f"Calling full flow with question: {question} and session_id: {
                 session_id} and user_id: {user_id} and chat_history: {chat_history}"
    )
    result = runnable_caller.call_full_flow(question, session_id, user_id, sbux_global_id, chat_history)
    # Capture parts of result that will be fed into the evaluation framework for
    # either reporting purposes or inputs to the evaluators
    chat_history = chat_history
    answer = result["answer"]
    config = result["app_config"]
    config_hash = result["app_config_hash"]
    documents_list = result["search_documents"]
    called_tools_list = result["called_tools"]
    for tool in called_tools_list:
        called_tools.append(tool["name"])
        query = tool["args"]["query"]
        query_list.append(query)

    # query_list = [i['query'] for i in tool_action_dict]
    # called_tools = [i['tool'] for i in tool_action_dict]
    prompt_tokens = result["prompt_tokens"]
    completion_tokens = result["completion_tokens"]
    total_tokens = result["total_tokens"]
    start_time = result["start_time"]
    end_time = result["end_time"]
    ellapsed_time = result["ellapsed_time"]
    # Return dictionary with all the necessary information for reporting or
    # evaluation purposes
    return {
        "question": question,
        "answer": answer,
        "query_list": query_list,
        "search_results": documents_list,
        "called_tools": called_tools,
        "app_config": config,
        "app_config_hash": config_hash,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "start_time": start_time,
        "end_time": end_time,
        "ellapsed_time": ellapsed_time,
    }


def get_evaluator_configs(config: AzureOpenAIModelConfiguration):
    """
    This function returns an EvaluatorConfigList object that contains all the evaluator configurations
    parameters: config: AzureOpenAIModelConfiguration object
    """
    evaluator_configs = EvaluatorConfigList()
    evaluator_configs.append_config(
        "response_groundedness",
        RAGGroundednessEvaluator(config),
        {"question": "${data.question}", "answer": "${target.answer}", "context": "${target.search_results}"},
    )
    evaluator_configs.append_config(
        "response_fluency",
        FluencyEvaluator(config),
        {"question": "${data.question}", "answer": "${target.answer}"},
    )
    evaluator_configs.append_config(
        "response_coherence",
        CoherenceEvaluator(config),
        {"question": "${data.question}", "answer": "${target.answer}"},
    )
    evaluator_configs.append_config(
        "response_relevance",
        RelevanceOptionalContextEvaluator(config),
        {"question": "${data.question}", "answer": "${target.answer}", "context": "${target.search_results}"},
    )
    return evaluator_configs


def evaluate_full_flow(dataset_path, model_config, evaluate_function=evaluate, **kwargs):
    evaluator_configs = get_evaluator_configs(model_config)
    result = run_evaluation(
        name="Botify Full Flow Evaluation",
        dataset_path=dataset_path,
        evaluator_config_list=evaluator_configs,
        target_function=call_full_flow,
        evaluate_function=evaluate_function,
        **kwargs,
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--evaluation_name",
        help="evaluation name used to log the evaluation to AI Studio",
        default="full_flow_eval",
        type=str,
    )
    parser.add_argument(
        "--dataset_path",
        help="Test dataset to use with evaluation",
        default="/workspaces/genai-pcc-search/evaluation/data_files/golden_dataset.jsonl",
        type=str,
    )

    parser.add_argument("--json_schema_path", help="Json schema to use with evaluation", type=str)

    args = parser.parse_args()

    model_config = AzureOpenAIModelConfiguration(
        azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT_EVAL"),
        api_key=os.environ.get("AZURE_OPENAI_API_KEY_EVAL"),
        azure_deployment=os.environ.get("AZURE_OPENAI_MODEL_NAME_EVAL"),
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION"),
    )

    result = evaluate_full_flow(dataset_path=args.dataset_path, model_config=model_config)
