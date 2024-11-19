import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import httpx
from app.settings import AppSettings
from langchain.callbacks.manager import AsyncCallbackManagerForToolRun, CallbackManagerForToolRun
from langchain.tools import BaseTool
from langchain_community.utilities.requests import JsonRequestsWrapper

logger = logging.getLogger(__name__)


class AzureContentSafety_Tool(BaseTool):
    app_settings = AppSettings()
    """Tool for performing Prompt Shields validation and Harmful Text validation for a query."""
    name = "Content Safety Validation"
    description = "Combines Prompt Shields validation and Harmful Text Analysis.\n"

    prompt_shield_endpoint = (
        app_settings.environment_config.content_safety_endpoint
        + "contentsafety/text:shieldPrompt?api-version="
        + app_settings.environment_config.content_safety_api_version
    )
    harmful_text_analysis_endpoint = (
        app_settings.environment_config.content_safety_endpoint
        + "contentsafety/text:analyze?api-version="
        + app_settings.environment_config.content_safety_api_version
    )

    headers = {
        "Ocp-Apim-Subscription-Key": app_settings.environment_config.content_safety_key.get_secret_value(),
        "Content-Type": "application/json",
    }

    def _run(self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None):
        payload_shield = {"userPrompt": query, "documents": None}
        payload_harmful = {"text": query}

        with ThreadPoolExecutor() as executor:
            shield_future = executor.submit(
                self._make_sync_request, self.prompt_shield_endpoint, payload_shield
            )
            harmful_future = executor.submit(
                self._make_sync_request,
                self.harmful_text_analysis_endpoint,
                payload_harmful,
            )

        shield_response = shield_future.result()
        harmful_response = harmful_future.result()

        return self._format_response(shield_response, harmful_response)

    async def _retry_async_request(self, func, *args, retries=3, **kwargs):
        for attempt in range(retries):
            try:
                return await func(*args, **kwargs)
            except aiohttp.ClientError as e:
                if attempt == retries - 1:
                    raise e

    async def _make_async_request(self, url, payload):
        jsonrequest = JsonRequestsWrapper(headers=self.headers)
        return await self._retry_async_request(jsonrequest.apost, url=url, data=payload)

    async def _arun(self, query: str, run_manager: Optional[AsyncCallbackManagerForToolRun] = None):
        payload_shield = {"userPrompt": query, "documents": None}
        payload_harmful = {"text": query}
        transport = httpx.AsyncHTTPTransport(retries=3)
        async with httpx.AsyncClient(transport=transport) as client:
            shield_response = await client.post(
                self.prompt_shield_endpoint, json=payload_shield, headers=self.headers
            )
            harmful_response = await client.post(
                self.harmful_text_analysis_endpoint, json=payload_harmful, headers=self.headers
            )

        return self._format_response(shield_response.json(), harmful_response.json())

    def _format_response(self, sheld_response, harmful_response):
        errors = []
        if "error" in sheld_response:
            errors.append(f"Shield Response Error: {sheld_response['error']}")
        if "error" in harmful_response:
            errors.append(
                f"Harmful Response Error: {
                          harmful_response['error']}"
            )

        if len(errors) > 0:
            raise RuntimeError(f"Errors in Content Safty Validation: {errors}")

        return {
            "prompt_shield_validation_response": sheld_response,
            "analyzed_harmful_text_response": harmful_response,
        }
