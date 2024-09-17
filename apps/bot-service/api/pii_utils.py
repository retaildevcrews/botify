import json
import logging

from app.settings import AppSettings
from common.presidio.anonymizer import Anonymizer as PresidioAnonymizer
from fastapi import Request

logger = logging.getLogger(__name__)


class Anonymizer:
    async def set_body(self, request: Request):
        app_settings = AppSettings()
        pii_entities = app_settings.anonymizer_entities
        mode = app_settings.environment_config.anonymizer_mode
        anonymizer_key = app_settings.environment_config.anonymizer_crypto_key
        logger.debug(f"Anonymizing PII entities: {pii_entities}")
        logger.debug(f"Anonymizer mode: {mode}")
        logger.debug(f"Anonymizer encryption key: {anonymizer_key}")
        anonymizer = PresidioAnonymizer(pii_entities, mode, anonymizer_key)
        try:
            receive_ = await request._receive()
            # Decode body to JSON
            body = json.loads(receive_["body"].decode("utf-8"))
            # Check if 'input' and 'question' fields are present
            if "input" in body and "question" in body["input"]:
                # Extract and log the 'question' field
                question = body["input"].get("question")
                # Update the 'question' field to a new value
                anonymized_question = anonymizer.anonymize_text(question)
                # Modify request body if anonymized items is not empty
                if len(anonymized_question.items) > 0:
                    body["input"]["question"] = anonymized_question.text
                    # Optionally log the modified body
                    logger.info(
                        f"Replaced Question With: {
                                anonymized_question}"
                    )

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
