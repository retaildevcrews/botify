import json
import logging
import os
import pathlib
import time

import pandas as pd
from app.settings import AppSettings
from evaluation_utils.evaluator_config import EvaluatorConfigList
from promptflow.evals.evaluate import evaluate

logger = logging.getLogger(__name__)


def split_search_json(input_search_result):
    try:
        parsed_list = json.loads(input_search_result)
        if not isinstance(parsed_list, list):
            raise ValueError("Input is not a valid JSON list")
        if not parsed_list:
            return "[]", "[]"
        mid_index = (len(parsed_list) // 2) + 1
        first_part = parsed_list[:mid_index]
        second_part = parsed_list[mid_index:]
        return json.dumps(first_part), json.dumps(second_part)
    except json.JSONDecodeError:
        return "(Error: Invalid JSON format)", "(Error: Invalid JSON format)"
    except Exception as e:
        return f"(Error: {str(e)})", f"(Error: {str(e)})"


# Apply `split_search_json` to the 'outputs.search_results' column
def split_search_result_col(doc):
    part1, part2 = split_search_json(doc)
    return pd.Series([part1, part2])


def split_search_result(df):

    # Get the position of 'search_results' column
    doc_list_index = df.columns.get_loc("outputs.search_results")

    # Split the search results and drop the original column
    df_split = df["outputs.search_results"].apply(split_search_result_col)
    df_split.columns = ["outputs.search_results_part_1", "outputs.search_results_part_2"]

    # Drop the 'search_results' column
    df.drop(columns=["outputs.search_results"], inplace=True)

    # Insert the new columns at the original index
    for i, col in enumerate(df_split.columns):
        df.insert(doc_list_index + i, col, df_split[col])

    return df


def run_evaluation(
    name,
    dataset_path,
    evaluator_config_list: EvaluatorConfigList,
    target_function,
    azure_ai_project=None,
    evaluate_function=evaluate,
    **kwargs,
):
    # load app settings to highlight issues with environment setup
    try:
        skip_environment_validation = kwargs.get("ignore_environment_validation")
        if skip_environment_validation == None or not skip_environment_validation:
            AppSettings()
        path = str(pathlib.Path.cwd() / dataset_path)
        result = evaluate_function(
            target=target_function,
            evaluation_name=name,
            data=path,
            evaluators=evaluator_config_list.get_evaluators_dict(),
            evaluator_config=evaluator_config_list.get_configs_dict(),
        )
        # Ensure the results directory exists
        results_dir = os.path.join(os.path.dirname(dataset_path), "results")
        save_evaluation_results(result, results_dir)
    except EnvironmentError as e:
        logger.error(f"Error loading app settings - please ensure your environment variables are set: {e}")
        result = None
    return result


def save_evaluation_results(result, output_path):
    if result:
        rows = result["rows"]
        # Split search_result column
        df = pd.DataFrame(rows)
        if "outputs.search_results" in df.columns:
            df = split_search_result(df)

        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        pathlib.Path(output_path).mkdir(parents=True, exist_ok=True)
        output_file = f"{output_path}/evaluation_results_{timestamp}.csv"
        df.to_csv(output_file, index=False)
        print(f"Results saved to {output_file}")
    else:
        logger.error("No results to save")
