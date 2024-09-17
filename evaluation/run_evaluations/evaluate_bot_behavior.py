import argparse
import json
import os
import time
import uuid

import pandas as pd
from common.schemas import ResponseSchema
from evaluation_utils.evaluator_config import EvaluatorConfigList
from evaluation_utils.formatting_utils import string_to_dict
from evaluation_utils.runnable_caller import RunnableCaller
from evaluators import BotBehaviorEvaluator
from promptflow.core import AzureOpenAIModelConfiguration
from promptflow.evals.evaluate import evaluate
from run_evaluations.utils import run_evaluation


def call_full_flow(*, question, **kwargs):
    runnable_caller = RunnableCaller()
    session_id = uuid.uuid4()
    user_id = f"user_{session_id}"
    bot_response = runnable_caller.call_full_flow(question, session_id, user_id, [])
    display_response = bot_response["display_response"]
    voice_summary = bot_response["voice_summary"]
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
    result = {
        "question": question,
        "answer": display_response,
        "voice_summary": voice_summary,
        "app_config": config,
        "app_config_hash": config_hash,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "start_time": start_time,
        "end_time": end_time,
        "ellapsed_time": ellapsed_time,
    }

    print(f"Result: {result}")

    return result


def get_evaluator_configs(config: AzureOpenAIModelConfiguration):
    """
    This function returns an EvaluatorConfigList object that contains all the evaluator configurations
    parameters: config: AzureOpenAIModelConfiguration object
    """
    evaluator_configs = EvaluatorConfigList()
    evaluator_configs.append_config(
        "bot_behavior_display",
        BotBehaviorEvaluator(config),
        {
            "question": "${data.question}",
            "answer": "${target.answer}",
            "expected_behavior": "${data.expected_behavior}",
        },
    )
    evaluator_configs.append_config(
        "bot_behavior_voice",
        BotBehaviorEvaluator(config),
        {
            "question": "${data.question}",
            "answer": "${target.voice_summary}",
            "expected_behavior": "${data.expected_behavior}",
        },
    )

    return evaluator_configs


def evaluate_full_flow(dataset_path, model_config, evaluate_function=evaluate, **kwargs):
    evaluator_configs = get_evaluator_configs(model_config)
    result = run_evaluation(
        name="Bot Behavior Evaluation",
        dataset_path=dataset_path,
        evaluator_config_list=evaluator_configs,
        target_function=call_full_flow,
        evaluate_function=evaluate_function,
        **kwargs,
    )
    return result


def generate_evaluation_result(df):
    total_rows = len(df)
    # Print every value in every row and column in the dataframe
    for index, row in df.iterrows():
        print(f"Row {index}:")
        for col in df.columns:
            print(f"  {col}: {row[col]}")

    mean_display_score = df["outputs.bot_behavior_display.score"].mean()
    mean_voice_score = df["outputs.bot_behavior_voice.score"].mean()
    # mean_prompt_tokens = df["outputs.prompt_tokens"].mean()
    # mean_completion_tokens = df["outputs.completion_tokens"].mean()
    # mean_total_tokens = df["outputs.total_tokens"].mean()
    # mean_ellapsed_time = df["outputs.ellapsed_time"].mean()

    output = {
        "total_rows": total_rows,
        "mean_display_score": mean_display_score,
        "mean_voice_score": mean_voice_score,
        # "mean_prompt_tokens": mean_prompt_tokens,
        # "mean_completion_tokens": mean_completion_tokens,
        # "mean_total_tokens": mean_total_tokens,
        # "mean_ellapsed_time": mean_ellapsed_time,
        "failing_records": [],
        "failed_record_count": 0,
    }

    # Filter for failing records
    failing_records = df[
        (df["outputs.bot_behavior_display.score"] < 4) | (df["outputs.bot_behavior_voice.score"] < 3)
    ][
        [
            "outputs.question",
            "outputs.answer",
            "outputs.bot_behavior_display.score",
            "outputs.bot_behavior_display.reason",
            "outputs.voice_summary",
            "outputs.bot_behavior_voice.score",
            "outputs.bot_behavior_voice.reason",
        ]
    ]
    output["failed_record_count"] = len(failing_records)

    # Add failing records to the output object
    for _, row in failing_records.iterrows():
        record = {
            "question": row["outputs.question"],
            "answer": row["outputs.answer"],
            "bot_behavior_display_score": row["outputs.bot_behavior_display.score"],
            "bot_behavior_display_reason": row["outputs.bot_behavior_display.reason"],
            "voice_summary": row["outputs.voice_summary"],
            "bot_behavior_voice_score": row["outputs.bot_behavior_voice.score"],
            "bot_behavior_voice_reason": row["outputs.bot_behavior_voice.reason"],
        }
        output["failing_records"].append(record)
    return output


def evaluate_bot_behavior(dataset_path, model_config):
    result = evaluate_full_flow(dataset_path=dataset_path, model_config=model_config)

    rows = result["rows"]
    df = pd.DataFrame(rows)

    return generate_evaluation_result(df)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--dataset_path",
        help="Test dataset to use with evaluation",
        default="/workspaces/botify/evaluation/data_files/bot_behavior.jsonl",
        type=str,
    )

    args = parser.parse_args()

    model_config = AzureOpenAIModelConfiguration(
        azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT_EVAL"),
        api_key=os.environ.get("AZURE_OPENAI_API_KEY_EVAL"),
        azure_deployment=os.environ.get("AZURE_OPENAI_MODEL_NAME_EVAL"),
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION"),
    )

    result = evaluate_bot_behavior(dataset_path=args.dataset_path, model_config=model_config)

    print(result)
