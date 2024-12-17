import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Type

from app.settings import AppSettings
from common.search.azure_ai_search import AzureRAGSearchClient
from langchain.callbacks.manager import AsyncCallbackManagerForToolRun, CallbackManagerForToolRun
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from typing import ClassVar
from openai import AzureOpenAI

logger = logging.getLogger(__name__)


class CustomAzureSearchRetriever(BaseRetriever):
    app_settings: ClassVar[AppSettings] = AppSettings()
    indexes: List
    fields_to_select: str
    vector_query_fields: str = ""
    generate_vector_query_embeddings: bool = False
    search_fields: str = ""
    filter: str = ""
    id_field: Optional[str] = None
    topK: int = 10
    max_results: int = 10
    semantic_config: Optional[str] = None
    answers: str = ""
    captions: str = ""
    highlightPreTag: str = ""
    highlightPostTag: str = ""
    reranker_threshold: Optional[int] = None
    vector_query_weight: Optional[int] = None

    search_client: ClassVar[AzureRAGSearchClient] = AzureRAGSearchClient(
        api_key=app_settings.environment_config.azure_search_key.get_secret_value(),
        api_version=app_settings.environment_config.azure_search_api_version,
        search_endpoint=app_settings.environment_config.azure_search_endpoint,
    )

    def generate_embeddings(self, query: str):
        client = AzureOpenAI(
            api_key=self.app_settings.environment_config.openai_api_key.get_secret_value(),
            api_version=self.app_settings.environment_config.openai_api_version,
            azure_endpoint=self.app_settings.environment_config.openai_endpoint,
        )
        model = self.app_settings.environment_config.openai_embedding_deployment_name
        return client.embeddings.create(input=[query], model=model).data[0].embedding

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        query_embeddings = None
        top_docs = []
        if self.generate_vector_query_embeddings:
            query_embeddings = self.generate_embeddings(query)
        ordered_results = self.search_client.search(
            query,
            self.indexes,
            k=self.topK,
            fields_to_select=self.fields_to_select,
            search_fields=self.search_fields,
            id_field=self.id_field,
            vector_query_fields=self.vector_query_fields,
            vector_query_embeddings=query_embeddings,
            filter=self.filter,
            semantic_config=self.semantic_config,
            answers=self.answers,
            captions=self.captions,
            highlightPreTag=self.highlightPreTag,
            highlightPostTag=self.highlightPostTag,
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
    indexes: List[str] = []
    args_schema: Type[BaseModel] = AzureAISearchInput
    semantic_config: str = ""
    search_fields: str = ""
    id_field: str = ""
    vector_query_fields: str = ""
    generate_vector_query_embeddings: bool = False
    filter: str = ""
    reranker_th: int = None
    vector_query_weight: int = None
    max_results: int = 3
    strict: bool = True

    def _run(self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        retriever = CustomAzureSearchRetriever(
            indexes=self.indexes,
            fields_to_select=self.fields_to_select,
            vector_query_fields=self.vector_query_fields,
            generate_vector_query_embeddings=self.generate_vector_query_embeddings,
            search_fields=self.search_fields,
            id_field=self.id_field,
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
            generate_vector_query_embeddings=self.generate_vector_query_embeddings,
            search_fields=self.search_fields,
            id_field=self.id_field,
            topK=self.k,
            filter=self.filter,
            semantic_config=self.semantic_config,
            reranker_threshold=self.reranker_th,
            vector_query_weight=self.vector_query_weight,
            callback_manager=self.callbacks,
            max_results=self.max_results,
        )
        # Please note below that running a non-async function like run_agent
        # in a separate thread won't make it truly asynchronous.
        # It allows the function to be called without blocking the event loop,
        # but it may still have synchronous behavior internally.
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(ThreadPoolExecutor(), retriever.invoke, query)
        return results


class AzureAIFilterableSearchInput(BaseModel):
    query: str = Field(description="should be a search query")
    filter_expression: str = Field(
        description="should be filter expression represented as a string", default_factory=lambda: ""
    )


class AzureAIFilterableSearch_Tool(BaseTool):
    name: str
    k: int
    description: str
    fields_to_select: str
    indexes: List[str] = []
    args_schema: Type[BaseModel] = AzureAIFilterableSearchInput
    vector_query_fields: str = ""
    generate_vector_query_embeddings: bool = False
    search_fields: str = ""
    id_field: str = ""
    semantic_config: str = ""
    reranker_th: int = None
    vector_query_weight: int = None
    max_results: int = 3

    def _run(
        self, query: str, filter_expression: str = "", run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Use the tool synchronously."""
        retriever = CustomAzureSearchRetriever(
            indexes=self.indexes,
            fields_to_select=self.fields_to_select,
            vector_query_fields=self.vector_query_fields,
            generate_vector_query_embeddings=self.generate_vector_query_embeddings,
            search_fields=self.search_fields,
            id_field=self.id_field,
            topK=self.k,
            filter=filter_expression,
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
        filter_expression: str = "",
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        """Use the tool asynchronously."""
        retriever = CustomAzureSearchRetriever(
            indexes=self.indexes,
            fields_to_select=self.fields_to_select,
            vector_query_fields=self.vector_query_fields,
            generate_vector_query_embeddings=self.generate_vector_query_embeddings,
            search_fields=self.search_fields,
            topK=self.k,
            filter=filter_expression,
            semantic_config=self.semantic_config,
            reranker_threshold=self.reranker_th,
            vector_query_weight=self.vector_query_weight,
            callback_manager=self.callbacks,
            max_results=self.max_results,
        )
        # Please note below that running a non-async function like run_agent in
        # a separate thread won't make it truly asynchronous.
        # It allows the function to be called without blocking the event loop,
        # but it may still have synchronous behavior internally.
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(ThreadPoolExecutor(), retriever.invoke, query)
        return results
