import json
import logging

from app.settings import AppSettings
from fastapi import Request
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

logger = logging.getLogger(__name__)


class Anonymizer:
    async def set_body(self, request: Request):
        try:
            receive_ = await request._receive()
            # Decode body to JSON
            body = json.loads(receive_["body"].decode("utf-8"))
            # Check if 'input' and 'question' fields are present
            if "input" in body and "question" in body["input"]:
                # Extract and log the 'question' field
                question = body["input"].get("question")
                # Update the 'question' field to a new value
                anonymized_question = self.anonymize_text(question)
                # Modify request body if anonymized items is not empty
                if len(anonymized_question.items) > 0:
                    body["input"]["question"] = anonymized_question.text
                    # Optionally log the modified body
                    logger.info(f"Replaced Question With: {anonymized_question}")

                async def receive():
                    receive_["body"] = json.dumps(body).encode("utf-8")
                    return receive_

                request._receive = receive

            else:
                # Log that the input/question field is missing
                logger.info(
                    "Input or question field is missing in the request body so no anonymization attempted"
                )

        except Exception as e:
            # Log the exception
            logger.error(f"Failed to process the request body: {str(e)}")

    def redacted_text_replacement(self, x):
        return str("redacted_value")

    def __init__(self, app_settings: AppSettings):
        configuration = {
            "nlp_engine_name": "spacy",
            "models": [
                {"lang_code": "en", "model_name": "en_core_web_sm"},
            ],
        }
        provider = NlpEngineProvider(nlp_configuration=configuration)
        self.pii_analyzer = AnalyzerEngine(nlp_engine=provider.create_engine())
        self.pii_anonymizer = AnonymizerEngine()
        self.pii_entities = app_settings.anonymizer_entities

    def custom_operators(self):
        config = {}
        for entity in self.pii_entities:
            config[entity] = OperatorConfig(
                "custom", {"lambda": self.redacted_text_replacement}
            )
        return config

    def anonymize_text(self, text):
        analyzed_text = self.pii_analyzer.analyze(
            text, entities=self.pii_entities, language="en"
        )
        anonymized_text = self.pii_anonymizer.anonymize(
            text, analyzed_text, operators=self.custom_operators()
        )
        return anonymized_text
