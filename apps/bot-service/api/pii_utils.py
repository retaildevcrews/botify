import functools
import json
import logging
from http import HTTPStatus
from typing import Callable

from app.exceptions import InputTooLongError, MaxTurnsExceededError
from app.messages import (
    CHARACTER_LIMIT_ERROR_MESSAGE_JSON,
    GENERIC_ERROR_MESSAGE_JSON,
    MAX_TURNS_EXCEEDED_ERROR_MESSAGE_JSON,
)
from app.settings import AppSettings
from botify_langchain.runnable_factory import RunnableFactory
from common.presidio.anonymizer import Anonymizer as PresidioAnonymizer
from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def anonymize(app_settings: AppSettings):
    async def error_response(code: int, message: str) -> dict:
        logger.exception(message)
        return JSONResponse(content=message, status_code=code)

    def decorator(func: Callable):
        @functools.wraps(func)
        async def anonymize_wrap(request: Request, *args, **kws):
            try:
                anonymizer = Anonymizer(app_settings)
                await anonymizer.set_body(request)

            except Exception as e:
                return await error_response(
                    code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
                    message=f"Error while anonymizing request: {str(e)}",
                )
            return await func(request, *args, **kws)

        return anonymize_wrap

    return decorator


class Anonymizer:
    def __init__(self, app_settings: AppSettings):
        self._app_settings = app_settings

    async def set_body(self, request: Request):
        app_settings = self._app_settings
        pii_entities = app_settings.anonymizer_entities
        mode = app_settings.environment_config.anonymizer_mode
        anonymizer_key = app_settings.environment_config.anonymizer_crypto_key
        logger.debug(f"Anonymizing PII entities: {pii_entities}")
        logger.debug(f"Anonymizer mode: {mode}")
        logger.debug(f"Anonymizer encryption key: {anonymizer_key}")
        anonymizer = PresidioAnonymizer(pii_entities, mode, anonymizer_key)
        try:
            logger.debug("Anonymizing request")

            # Decode body to JSON
            body = await request.body()
            body = json.loads(body)

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
                    question_in_body = body["input"]["question"]
                    logger.info(
                        f"Question that has been replaced in body: {
                                question_in_body}"
                    )
                    request._body = json.dumps(body).encode("utf-8")
                    logger.info(f"Body after anonymization: {request._body}")
            else:
                # Log that the input/question field is missing
                logger.info(
                    "Input or question field is missing in the request body so no anonymization attempted"
                )

        except Exception as e:
            # Log the exception
            logger.error(f"Failed to process the request body: {str(e)}")


retries_limit = AppSettings().invoke_retry_count


async def invoke(input_data, config_data, runnable_factory: RunnableFactory, retry_count=0):
    error_response = {"output": GENERIC_ERROR_MESSAGE_JSON}
    try:
        invoke_runnable_factory = runnable_factory
        runnable = invoke_runnable_factory.get_runnable()
        result = await runnable.ainvoke(input_data, config_data)
        return result
    except Exception as e:
        logging.error(f"Error invoking runnable: {e}")
        if isinstance(e, InputTooLongError):
            return {"output": CHARACTER_LIMIT_ERROR_MESSAGE_JSON}
        if isinstance(e, MaxTurnsExceededError):
            return {"output": MAX_TURNS_EXCEEDED_ERROR_MESSAGE_JSON}
        if not isinstance(e, ValueError):
            result = (
                await invoke(input_data, config_data, invoke_runnable_factory, retry_count + 1)
                if retry_count < retries_limit
                else error_response
            )
            return result
        return error_response
