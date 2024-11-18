import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Type

from app.settings import AppSettings
from common.search.azure_ai_search import AzureRAGSearchClient
from langchain.callbacks.manager import AsyncCallbackManagerForToolRun, CallbackManagerForToolRun
from langchain.pydantic_v1 import BaseModel, Field
from langchain.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

logger = logging.getLogger(__name__)


class CustomAzureSearchRetriever(BaseRetriever):
    app_settings = AppSettings()
    indexes: List
    fields_to_select: str
    vector_query_fields: str
    filter: str
    topK: int
    semantic_config: str
    reranker_threshold: int
    vector_query_weight: int
    max_results: int

    search_client = AzureRAGSearchClient(
        api_key=app_settings.environment_config.azure_search_key.get_secret_value(),
        api_version=app_settings.environment_config.azure_search_api_version,
        search_endpoint=app_settings.environment_config.azure_search_endpoint,
    )

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        top_docs = []
        ordered_results = self.search_client.search(
            query,
            self.indexes,
            k=self.topK,
            fields_to_select=self.fields_to_select,
            vector_query_fields=self.vector_query_fields,
            filter=self.filter,
            semantic_config=self.semantic_config,
            reranker_threshold=self.reranker_threshold,
            vector_query_weight=self.vector_query_weight,
            max_results=self.max_results,
        )

        top_docs = [Document(page_content=str(result)) for result in ordered_results]
        return top_docs


class AzureAISearchInput(BaseModel):
    query: str = Field(description="should be a search query")


class AzureAISearch_Tool(BaseTool):
    name: str
    k: int
    description: str
    fields_to_select: str
    vector_query_fields: str
    indexes: List[str] = []
    args_schema: Type[BaseModel] = AzureAISearchInput
    semantic_config: str = ""
    filter: str = ""
    reranker_th: int = 1
    vector_query_weight: int = 1
    max_results: int = 3

    def _run(self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        retriever = CustomAzureSearchRetriever(
            indexes=self.indexes,
            fields_to_select=self.fields_to_select,
            vector_query_fields=self.vector_query_fields,
            topK=self.k,
            filter=self.filter,
            semantic_config=self.semantic_config,
            reranker_threshold=self.reranker_th,
            vector_query_weight=self.vector_query_weight,
            callback_manager=self.callbacks,
            max_results=self.max_results,
        )
        results = retriever.invoke(query)

        return results

    async def _arun(self, query: str, run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        retriever = CustomAzureSearchRetriever(
            indexes=self.indexes,
            fields_to_select=self.fields_to_select,
            vector_query_fields=self.vector_query_fields,
            topK=self.k,
            filter=self.filter,
            semantic_config=self.semantic_config,
            reranker_threshold=self.reranker_th,
            vector_query_weight=self.vector_query_weight,
            callback_manager=self.callbacks,
            max_results=self.max_results,
        )
        results = await retriever.ainvoke(query)
        return results


class AzureAIFilterableSearchInput(BaseModel):
    query: str = Field(description="should be a search query")
    contains: list[str] = Field(
        description="should be a list of words that must appear in the search results",
        default_factory=lambda: [""],
    )
    does_not_contain: list[str] = Field(
        description="should be a list of words that do not appear in the search results",
        default_factory=lambda: [],
    )


class AzureAIFilterableSearch_Tool(BaseTool):
    name: str
    k: int
    description: str
    fields_to_select: str
    vector_query_fields: str
    indexes: List[str] = []
    args_schema: Type[BaseModel] = AzureAIFilterableSearchInput
    semantic_config: str
    reranker_th: int = 1
    vector_query_weight: int = 1
    max_results: int = 3

    def make_filter_expression(self, criteria):
        """
        Creates a filter expression for the Azure AI Search API based on provided criteria.
        :param criteria: A dictionary where keys are field names and values are lists of terms.
                        Example: {'contains': ['term1', 'term2'], 'not_contains': [
                            'term3'], 'field': 'summary'}
        :return: A string representing the filter expression.
        """
        filter_expressions = []

        # Handle contains criteria
        if "contains" in criteria and criteria["contains"]:
            contain_terms = ",".join(criteria["contains"])
            filter_expressions.append(
                f"search.ismatch('{contain_terms}', '{
                                      criteria.get('field', 'summary')}')"
            )

        # Handle does not contain criteria
        if "not_contains" in criteria and criteria["not_contains"]:
            not_contain_terms = ",".join(criteria["not_contains"])
            filter_expressions.append(
                f"not search.ismatch('{not_contain_terms}', '{
                                      criteria.get('field', 'summary')}')"
            )

        # Combine all filter expressions with ' and ' if there are any
        filter_expression = " and ".join(filter_expressions)

        # Log and return the filter expression
        logger.debug(f"filter_expression: {filter_expression}")
        return filter_expression

    def _run(
        self,
        query: str,
        contains: list[str] = [],
        does_not_contain: list[str] = [],
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Use the tool synchronously."""
        criteria = {"contains": contains, "not_contains": does_not_contain, "field": "summary"}
        filter = self.make_filter_expression(criteria)
        retriever = CustomAzureSearchRetriever(
            indexes=self.indexes,
            fields_to_select=self.fields_to_select,
            vector_query_fields=self.vector_query_fields,
            topK=self.k,
            filter=filter,
            semantic_config=self.semantic_config,
            reranker_threshold=self.reranker_th,
            vector_query_weight=self.vector_query_weight,
            callback_manager=self.callbacks,
            max_results=self.max_results,
        )
        results = retriever.invoke(query)

        return results

    async def _arun(
        self,
        query: str,
        contains: list[str] = [],
        does_not_contain: list[str] = [],
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        """Use the tool asynchronously."""
        criteria = {"contains": contains, "not_contains": does_not_contain, "field": "summary"}
        filter = self.make_filter_expression(criteria)
        retriever = CustomAzureSearchRetriever(
            indexes=self.indexes,
            fields_to_select=self.fields_to_select,
            vector_query_fields=self.vector_query_fields,
            topK=self.k,
            filter=filter,
            semantic_config=self.semantic_config,
            reranker_threshold=self.reranker_th,
            vector_query_weight=self.vector_query_weight,
            callback_manager=self.callbacks,
            max_results=self.max_results,
        )
        results = await retriever.ainvoke(query)
        return results
