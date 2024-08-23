class EvaluatorConfig:
    def __init__(self, evaluator_name: str, evaluator: callable, config: dict):
        """
        Initializes the EvaluatorConfig with a name, a callable evaluator, and a configuration.

        :param evaluator_name: Name of the evaluator (string)
        :param evaluator: Callable that performs evaluation
        :param config: Configuration dictionary with placeholders
        """
        self.evaluator_name = evaluator_name
        self.evaluator = evaluator
        self.config = config


class EvaluatorConfigList(list[EvaluatorConfig]):
    def append_config(self, evaluator_name: str, evaluator: callable, config: dict):
        """
        Appends a new EvaluatorConfig to the list.

        :param evaluator_name: Name of the evaluator (string)
        :param evaluator: Callable that performs evaluation
        :param config: Configuration dictionary with placeholders
        """
        new_config = EvaluatorConfig(evaluator_name, evaluator, config)
        self.append(new_config)

    def get_evaluators_dict(self) -> dict:
        """
        Returns a dictionary with evaluator names as keys and evaluators as values.

        :return: Dictionary with evaluator name as key and evaluator as value
        """
        return {config.evaluator_name: config.evaluator for config in self}

    def get_configs_dict(self) -> dict:
        """
        Returns a dictionary with evaluator names as keys and configs as values.

        :return: Dictionary with evaluator name as key and config as value
        """
        return {config.evaluator_name: config.config for config in self}
