import logging

from app.messages import GENERIC_ERROR_MESSAGE
from app.settings import AppSettings
from botify_langchain.runnable_factory import RunnableFactory

logger = logging.getLogger(__name__)

retries_limit = AppSettings().invoke_retry_count


async def invoke_wrapper(input_data, config_data, runnable_factory: RunnableFactory, retry_count=0):
    error_response = GENERIC_ERROR_MESSAGE
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
