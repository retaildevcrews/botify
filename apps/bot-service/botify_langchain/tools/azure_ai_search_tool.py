import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Type

import requests
from app.settings import AppSettings
from langchain.callbacks.manager import (AsyncCallbackManagerForToolRun,
                                         CallbackManagerForToolRun)
from langchain.pydantic_v1 import BaseModel, Field
from langchain.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

logger = logging.getLogger(__name__)


class SearchInput(BaseModel):
    query: str = Field(description="should be a search query")


def get_search_results(
    query: str,
    indexes: list,
    fields_to_select: str,
    vector_query_fields: str,
    max_results: int,
    k: int = 10,
    reranker_threshold: int = 1,
    vector_query_weight: int = 1,
    azure_search_key: str = "",
    azure_search_api_version: str = "",
    azure_search_endpoint: str = ""
) -> List[dict]:
    """Performs multi-index hybrid search and returns ordered dictionary with the combined results"""

    headers = {
        "Content-Type": "application/json",
        "api-key": azure_search_key,
    }
    params = {
        "api-version": azure_search_api_version,
    }

    agg_search_results = {}

    for index in indexes:
        search_payload = {
            "search": query,
            "select": fields_to_select,
            "queryType": "semantic",
            "vectorQueries": [
                {"text": query, "fields": vector_query_fields,
                    "kind": "text", "k": k, "weight": vector_query_weight}
            ],
            "semanticConfiguration": "my-semantic-config",
            "answers": f"extractive|count-1",
            "captions": "extractive",
            "count": "true",
            "top": k
        }

        resp = requests.post(
            f"{azure_search_endpoint}/indexes/{index}/docs/search",
            data=json.dumps(search_payload),
            headers=headers,
            params=params,
        )
        search_results = resp.json()
        agg_search_results[index] = search_results

    content = dict()

    if not any("value" in results for results in agg_search_results.values()):
        logger.warning("Invalid Search Response")
        return []

    for index, results in agg_search_results.items():
        logger.debug(f"found {len(results['value'])} results in index {index}")
        if "value" not in results:
            continue
        for result in results["value"]:
            # Get the unique id of the result
            result_id = result["id"]

            # Check if the rerankerScore meets the threshold
            if result["@search.rerankerScore"] > reranker_threshold:
                content[result_id] = result
    # Sort results by score in descending order
    sorted_results = sorted(
        content.values(), key=lambda item: item["@search.score"], reverse=True)

    # Return up to max_results
    return sorted_results[:max_results]


class CustomAzureSearchRetriever(BaseRetriever):
    app_settings = AppSettings()
    indexes: List
    fields_to_select: str
    vector_query_fields: str
    topK: int
    reranker_threshold: int
    vector_query_weight: int
    max_results: int

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        top_docs = []
        ordered_results = get_search_results(
            query,
            self.indexes,
            k=self.topK,
            fields_to_select=self.fields_to_select,
            vector_query_fields=self.vector_query_fields,
            reranker_threshold=self.reranker_threshold,
            vector_query_weight=self.vector_query_weight,
            azure_search_endpoint=self.app_settings.environment_config.azure_search_endpoint,
            azure_search_api_version=self.app_settings.environment_config.azure_search_api_version,
            azure_search_key=self.app_settings.environment_config.azure_search_key.get_secret_value(),
            max_results=self.max_results,
        )

        top_docs = [Document(page_content=str(result))
                    for result in ordered_results]
        return top_docs


class AzureAISearch_Tool(BaseTool):
    name: str
    k: int
    description: str
    fields_to_select: str
    vector_query_fields: str
    indexes: List[str] = []
    args_schema: Type[BaseModel] = SearchInput
    reranker_th: int = 1
    vector_query_weight: int = 1
    max_results: int = 3

    def _run(
        self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:

        retriever = CustomAzureSearchRetriever(
            indexes=self.indexes,
            fields_to_select=self.fields_to_select,
            vector_query_fields=self.vector_query_fields,
            topK=self.k,
            reranker_threshold=self.reranker_th,
            vector_query_weight=self.vector_query_weight,
            callback_manager=self.callbacks,
            max_results=self.max_results,
        )
        results = retriever.invoke(query)

        return results

    async def _arun(
        self, query: str, run_manager: Optional[AsyncCallbackManagerForToolRun] = None
    ) -> str:
        """Use the tool asynchronously."""

        retriever = CustomAzureSearchRetriever(
            indexes=self.indexes,
            fields_to_select=self.fields_to_select,
            vector_query_fields=self.vector_query_fields,
            topK=self.k,
            max_results=self.max_results,
            reranker_threshold=self.reranker_th,
            vector_query_weight=self.vector_query_weight,
            callback_manager=self.callbacks,
        )
        # Please note below that running a non-async function like run_agent in a separate thread won't make it truly asynchronous.
        # It allows the function to be called without blocking the event loop, but it may still have synchronous behavior internally.
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            ThreadPoolExecutor(), retriever.invoke, query
        )

        return results
