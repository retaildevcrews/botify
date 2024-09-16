import hashlib
from dataclasses import field
from typing import Dict, Optional

import pydantic
from app.environment_config import EnvironmentConfig
from pydantic import RootModel


class Config:
    arbitrary_types_allowed = True


@pydantic.dataclasses.dataclass(config=Config)
class ModelConfig:
    menu_search_tool_topk: int = 10
    max_tokens: int = 800
    temperature: float = 0.1
    top_p: float = 0.5
    logit_bias: Dict[int, int] = field(default_factory=dict)
    use_structured_output: bool = False
    use_json_format: bool = True


@pydantic.dataclasses.dataclass(config=Config)
class AppSettings:
    environment_config: Optional[EnvironmentConfig] = field(default=None) # Useful in unit tests
    prompt_template_path: str = "minified_json.txt"
    response_schema_name: str = "response_schema.json"
    model_config: ModelConfig = field(default_factory=ModelConfig) #Default model configuration can be seen in the ModelConfig class
    optimize_history: bool = True # When this is set to true, the agent will attempt to store only the display message and not entire bot response
    search_tool_topk: int = 10
    search_similarity_field: str = "summary"
    search_tool_reranker_threshold: int = 1
    item_detail_reranker_threshold: int = 1
    add_memory: bool = True # Adds memory to the agent so that it can engage in multi-turn conversations
    load_environment_config: bool = True
    # Use this section to turn anonymization on or off
    # there is an environment variable ANONYMIZER_MODE and ANONYMIZER_CRYPTO_KEY
    # that can be used to control how the anonymization will be done
    anonymize_questions: bool = True
    anonymizer_entities: list[str] = field(
        default_factory=lambda: [
            "PHONE_NUMBER",
            "EMAIL_ADDRESS",
            "CREDIT_CARD",
            "LOCATION",
            "IP_ADDRESS",
            "US_SSN",
            "URL",
            "IBAN_CODE",
            "US_SSN",
            "US_DRIVER_LICENSE",
            "US_PASSPORT",
            "US_BANK_NUMBER",
            "US_ITIN",
        ]
    )

    content_safety_enabled: bool = True #Used to turn on or off content safety checks - config is in environment_config
    # Use this section to turn on or off banned topic checks,
    # this is a custom tool that uses LLM to classify the topic of the question
    banned_topics: list[str] = field(
        default_factory=lambda: [
            "legal",
            "financial",
            "politics",
            "medical",
        ]
    )
    # Use this section to turn on or off annotation of disclaimers in responses,
    # this is a custom tool that uses LLM to classify the topic of the question
    disclaimer_topics: list[str] = field(
        default_factory=lambda: [
            "fire",
        ]
    )
    validate_json_output: bool = True

    def __post_init__(self):
        if self.load_environment_config and self.environment_config is None:
            self.environment_config = EnvironmentConfig()

    def get_config(self):
        json = RootModel[AppSettings](self).model_dump_json()
        return json

    def get_config_hash(self):
        hash_value = hashlib.sha224(
            self.get_config().encode("utf-16")).hexdigest()
        return hash_value
