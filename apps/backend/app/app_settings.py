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
    load_environment_config: bool = True
    anonymize_questions: bool = True
    anonymizer_entities: list[str] = field(
        default_factory=lambda: [
            "PHONE_NUMBER",
            "EMAIL_ADDRESS",
            "CREDIT_CARD",
            "LOCATION",
            "IP_ADDRESS",
            "NRP",
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

    environment_config: Optional[EnvironmentConfig] = field(default=None)

    prompt_template_path: str = "minified_json.txt"
    response_schema_name: str = "response_schema.json"
    model_config: ModelConfig = field(default_factory=ModelConfig)
    optimize_history: bool = True
    content_safety_enabled: bool = True
    banned_topics: list[str] = field(
        default_factory=lambda: [
            "legal",
            "financial",
            "politics",
            "medical",
        ]
    )
    disclaimer_topics: list[str] = field(
        default_factory=lambda: [
            "fire",
        ]
    )
    validate_json_output: bool = True
    search_tool_topk: int = 10
    search_similarity_field: str = "summary"
    search_tool_reranker_threshold: int = 1
    item_detail_reranker_threshold: int = 1

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
