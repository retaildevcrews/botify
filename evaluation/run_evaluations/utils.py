import logging
import pathlib

from app.app_settings import AppSettings
from evaluation_utils.evaluator_config import EvaluatorConfigList
from promptflow.evals.evaluate import evaluate

logger = logging.getLogger(__name__)


def run_evaluation(name, dataset_path, evaluator_config_list: EvaluatorConfigList, target_function, evaluate_function=evaluate, **kwargs):
    # load app settings to highlight issues with environment setup
    try:
        skip_environment_validation = kwargs.get(
            'ignore_environment_validation')

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
    except EnvironmentError as e:
        logger.error(
            f"Error loading app settings - please ensure your environment variables are set: {e}")
        result = None

    return result
