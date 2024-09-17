from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine, DeanonymizeEngine
from presidio_anonymizer.entities import OperatorConfig, OperatorResult
from presidio_analyzer.nlp_engine import NlpEngineProvider
from pydantic import SecretStr
from fastapi import Request
import json
import logging
import traceback

logger = logging.getLogger(__name__)


class Anonymizer:

    def redacted_text_replacement(self, x):
        return str("redacted_value")

    def __init__(self, pii_entitities, mode: str = "CUSTOM", crypto_key: SecretStr = None):
        configuration = {
            "nlp_engine_name": "spacy",
            "models": [
                {"lang_code": "en", "model_name": "en_core_web_sm"},
            ],
        }
        provider = NlpEngineProvider(nlp_configuration=configuration)
        self.pii_analyzer = AnalyzerEngine(nlp_engine=provider.create_engine())
        self.pii_anonymizer = AnonymizerEngine()
        self.pii_entities = pii_entitities
        self.anonymizer_mode = mode
        self.anonymizer_crypto_key = crypto_key
        self.operators = self.configure_operators()

    def configure_operators(self):
        config = {}
        if self.anonymizer_mode.upper() == "ENCRYPT":
            operator_config = {
                "key": self.anonymizer_crypto_key.get_secret_value()}
        else:
            operator_config = {"lambda": self.redacted_text_replacement}
        for entity in self.pii_entities:
            config[entity] = OperatorConfig(
                self.anonymizer_mode.lower(), operator_config)
        logger.info(f"Configured operators: {config.keys()}")
        return config

    def anonymize_text(self, text):
        analyzed_text = self.pii_analyzer.analyze(
            text, entities=self.pii_entities, language="en")
        anonymized_text = self.pii_anonymizer.anonymize(
            text, analyzed_text, operators=self.operators)
        return anonymized_text


class Deanonymizer:
    def __init__(self, pii_entities, crypto_key: SecretStr = None):
        self.pii_deanonymizer = DeanonymizeEngine()
        self.pii_entities = pii_entities
        self.anonymizer_crypto_key = crypto_key
        self.operators = self.configure_operators()

    def configure_operators(self):
        config = {}
        for entity in self.pii_entities:
            config[entity] = OperatorConfig(
                "decrypt", {"key": self.anonymizer_crypto_key.get_secret_value()})
        return config

    def deanonymize_result(self, input_data):
        try:
            input_json = json.loads(input_data)
            text = input_json.get('text')
            entities = [OperatorResult(**item)
                        for item in input_json.get('items')]
            input_result = self.pii_deanonymizer.deanonymize(
                text, entities, operators=self.operators)
        except Exception:
            logger.debug(
                f"Input does not contain an anonymized result: {traceback.format_exc()}")
            return input_data

        return input_result.text
