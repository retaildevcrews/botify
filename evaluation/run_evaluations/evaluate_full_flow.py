import argparse
import json
import os

from common.schemas import ResponseSchema
from evaluation_utils.evaluator_config import EvaluatorConfigList
from evaluation_utils.formatting_utils import string_to_dict
from evaluation_utils.runnable_caller import RunnableCaller
from evaluators import (
    CoherenceEvaluator,
    FluencyEvaluator,
    JsonSchemaValidationEvaluator,
    RAGGroundednessEvaluator,
    RelevanceOptionalContextEvaluator,
)
from promptflow.core import AzureOpenAIModelConfiguration
from promptflow.evals.evaluate import evaluate
from run_evaluations.utils import run_evaluation


def call_full_flow(*, question, session_id, user_id, chat_history, **kwargs):
    runnable_caller = RunnableCaller()
    # Call the full flow - this is the system under test
    # Call the full flow - this is the system under test
    result = runnable_caller.call_full_flow(question, session_id, user_id, chat_history)
    # Capture parts of result that will be fed into the evaluation framework for
    # either reporting purposes or inputs to the evaluators
    consolidated_tool_actions = result["consolidated_tool_actions"]
    chat_history = result["history"]
    bot_response = result["bot_response"]
    display_response = result["display_response"]
    voice_summary = result["voice_summary"]
    config = result["app_config"]
    config_hash = result["app_config_hash"]
    search_results = []
    for action in consolidated_tool_actions:
        documents = action["documents"]
        for doc in documents:
            search_results.append(doc.page_content)
    query_list = [i["query"] for i in consolidated_tool_actions]
    called_tools = [i["tool"] for i in consolidated_tool_actions]
    context = {"history": chat_history, "search_results": search_results}
    prompt_tokens = result["prompt_tokens"]
    completion_tokens = result["completion_tokens"]
    total_tokens = result["total_tokens"]
    start_time = result["start_time"]
    end_time = result["end_time"]
    ellapsed_time = result["ellapsed_time"]
    # Return dictionary with all the necessary information for reporting or
    # evaluation purposes
    return {
        "bot_response": bot_response,
        "display_response": display_response,
        "voice_summary": voice_summary,
        "query_list": query_list,
        "search_results": search_results,
        "called_tools": called_tools,
        "context": context,
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
        "json_schema_validation",
        JsonSchemaValidationEvaluator(ResponseSchema().get_response_schema_as_string()),
        {"content": "${target.bot_response}"},
    )
    evaluator_configs.append_config(
        "display_response_groundedness",
        RAGGroundednessEvaluator(config),
        {
            "question": "${data.question}",
            "answer": "${target.display_response}",
            "context": "${target.search_results}",
        },
    )
    evaluator_configs.append_config(
        "voice_summary_groundedness",
        RAGGroundednessEvaluator(config),
        {
            "question": "${data.question}",
            "answer": "${target.voice_summary}",
            "context": "${target.search_results}",
        },
    )
    evaluator_configs.append_config(
        "display_response_fluency",
        FluencyEvaluator(config),
        {"question": "${data.question}", "answer": "${target.display_response}"},
    )
    evaluator_configs.append_config(
        "voice_summary_fluency",
        FluencyEvaluator(config),
        {"question": "${data.question}", "answer": "${target.voice_summary}"},
    )
    evaluator_configs.append_config(
        "display_response_coherence",
        CoherenceEvaluator(config),
        {"question": "${data.question}", "answer": "${target.display_response}"},
    )
    evaluator_configs.append_config(
        "voice_summary_coherence",
        CoherenceEvaluator(config),
        {"question": "${data.question}", "answer": "${target.voice_summary}"},
    )
    evaluator_configs.append_config(
        "relevance",
        RelevanceOptionalContextEvaluator(config),
        {"question": "${data.question}", "answer": "${target.bot_response}", "context": "${target.context}"},
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
        **kwargs
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
        default="/workspaces/botify/evaluation/data_files/chatbot_test.jsonl",
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
