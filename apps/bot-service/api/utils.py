import logging

from api.models import Output
from app.messages import GENERIC_ERROR_MESSAGE
from app.settings import AppSettings
from botify_langchain.runnable_factory import RunnableFactory
from botify_langchain.utils.response_parser import parse_response

logger = logging.getLogger(__name__)

retries_limit = AppSettings().invoke_retry_count


async def invoke_wrapper(input_data, config_data, runnable_factory: RunnableFactory, retry_count=0):
    error_response = Output(
        question=input_data["messages"][0]["content"], answer=GENERIC_ERROR_MESSAGE
    ).model_dump()
    try:
        runnable = runnable_factory.get_runnable()
        result = await runnable.ainvoke(input_data, config_data)
        return result
    except Exception as e:
        logger.exception(f"Error invoking runnable: {e}")
        if not isinstance(e, ValueError):
            result = (
                await invoke_wrapper(input_data, config_data, runnable_factory, retry_count + 1)
                if retry_count < retries_limit
                else error_response
            )
            return result
        return error_response
