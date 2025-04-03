import functools
import json
import logging
from http import HTTPStatus
from typing import Callable

from app.messages import GENERIC_ERROR_MESSAGE
from app.settings import AppSettings
from common import Singleton
from common.presidio.anonymizer import Anonymizer as PresidioAnonymizer
from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def anonymize(func: Callable):
    @functools.wraps(func)
    async def anonymize_wrap(request: Request, *args, **kws):
        body = await request.body()
        body = json.loads(body)
        logger.debug(f"Received body {body}")
        try:
            anonymizer = Anonymizer()
            question, anonymized_entities = await anonymizer.anonymize_input(body)
            if len(anonymized_entities) > 0:
                for item in anonymized_entities:
                    entity_type_detected = item.entity_type
                    logger.info(
                        f"PII data detected in input query: {
                            entity_type_detected}",
                        extra={"triggered_scanner": "input_anonymize", "pii_detected": entity_type_detected},
                    )
                response = GENERIC_ERROR_MESSAGE
                logger.info(
                    "Response logged",
                    extra={
                        "application_logs": {"output": response},
                        "sink": ["file"],
                    },
                )
                return JSONResponse(
                    status_code=HTTPStatus.OK.value,
                    content=response,
                )
        except Exception as e:
            logger.exception(f"Error occurred while anonymizing input: {e}")
            # question = body["input"].get("messages")[-1]["content"]
            return JSONResponse(
                status_code=HTTPStatus.OK.value,
                content=GENERIC_ERROR_MESSAGE,
            )
        return await func(request, *args, **kws)

    return anonymize_wrap


class Anonymizer(metaclass=Singleton):

    def __init__(self):
        app_settings = AppSettings()
        pii_entities = app_settings.anonymizer_entities
        mode = app_settings.environment_config.anonymizer_mode
        anonymizer_key = app_settings.environment_config.anonymizer_crypto_key
        logger.debug(f"Anonymizing PII entities: {pii_entities}")
        logger.debug(f"Anonymizer mode: {mode}")
        logger.debug(f"Anonymizer encryption key: {anonymizer_key}")
        self.anonymizer = PresidioAnonymizer(pii_entities, mode, anonymizer_key)

    async def anonymize_input(self, body: dict):
        """Example anonymized_question
        text: redacted_value and redacted_value thanks
        items:
        [
            {'start': 19, 'end': 33, 'entity_type': 'EMAIL_ADDRESS',
            'text': 'redacted_value', 'operator': 'custom'},
            {'start': 0, 'end': 14, 'entity_type': 'PHONE_NUMBER',
            'text': 'redacted_value', 'operator': 'custom'}
        ]"""
        logger.debug("Anonymizing request")
        # Check if 'input' and 'question' fields are present
        if "input" in body and "messages" in body["input"]:
            # Extract and log the 'question' field
            question = body["input"].get("messages")[-1]["content"]
            analyzed_text = self.anonymizer.analyze_text(question)
            return question, analyzed_text
        else:
            # Log that the input/question field is missing
            logger.info(
                "Input or question field is missing in the request body so no anonymization attempted"
            )
