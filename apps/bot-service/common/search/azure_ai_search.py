import json
import logging
from typing import List

import requests


logger = logging.getLogger(__name__)


class AzureRAGSearchClient:
    def __init__(self, api_key: str, api_version: str, search_endpoint: str):
        self.search_key = api_key
        self.api_version = api_version
        self.search_endpoint = search_endpoint

    def search(
        self,
        query: str,
        indexes: list,
        fields_to_select: str,
        max_results: int,
        id_field: str = "id",
        search_fields: str = "",
        vector_query_fields: str = "",
        vector_query_embeddings: List[float] = None,
        semantic_config: str = "",
        filter: str = "",
        k: int = 10,
        answers: str = "",
        captions: str = "",
        highlightPreTag: str = "",
        highlightPostTag: str = "",
        count: str = "true",
        reranker_threshold: int = None,
        vector_query_weight: int = None,
    ) -> List[dict]:
        print(f"query: {query}")
        """Performs multi-index hybrid search and returns ordered dictionary with the combined results"""
        headers = {
            "Content-Type": "application/json",
            "api-key": self.search_key,
        }
        params = {
            "api-version": self.api_version,
        }

        agg_search_results = {}
        for index in indexes:
            search_payload = {
                "select": fields_to_select,
                "count": count,
                "top": k
            }
            if search_fields != "":
                search_payload["search"] = query
                search_payload["searchFields"] = search_fields
            if vector_query_fields != "":
                search_payload["queryType"] = "semantic"
                if vector_query_embeddings:
                    search_payload["vectorQueries"] = [{
                        "vector": vector_query_embeddings, "fields": vector_query_fields, "kind": "vector", "k": k}]
                else:
                    search_payload["vectorQueries"] = [
                        {"text": query, "fields": vector_query_fields,
                            "kind": "text", "k": k, "weight": vector_query_weight}
                    ]
            if semantic_config:
                search_payload["semanticConfiguration"] = semantic_config
                # search_payload["searchMode"] = "any"
            if filter:
                search_payload["filter"] = filter
            if answers:
                search_payload["answers"] = answers
            if captions:
                search_payload["captions"] = captions
                if highlightPreTag:
                    search_payload["highlightPreTag"] = highlightPreTag
                if highlightPostTag:
                    search_payload["highlightPostTag"] = highlightPostTag

            print(f"search_payload: {search_payload}")
            resp = requests.post(
                f"{self.search_endpoint}/indexes/{index}/docs/search",
                data=json.dumps(search_payload),
                headers=headers,
                params=params,
            )
            search_results = resp.json()
            print(f"search_results: {search_results}")
            resp.raise_for_status()

            agg_search_results[index] = search_results

        content = dict()
        if not any("value" in results for results in agg_search_results.values()):
            logger.warning("No results returned")
            return []

        for index, results in agg_search_results.items():
            logger.debug(
                f"found {len(results['value'])} results in index {index}")
            if "value" not in results:
                continue
            for result in results["value"]:
                # Get the unique id of the result

                result_id = result[id_field] if id_field in result else str(
                    index)
                # Check if the rerankerScore meets the threshold
                if not reranker_threshold or result["@search.rerankerScore"] > reranker_threshold:
                    content[result_id] = result
                else:
                    logger.debug(f"Reranker Score below threshold for product number {
                        result[result_id]}, Skipping")
            # Sort results by score in descending order
            for item in content.values():
                if "@search.rerankerScore" not in item:
                    item["@search.rerankerScore"] = 0
            sorted_results = sorted(
                content.values(),
                key=lambda item: (
                    item["@search.rerankerScore"], item["@search.score"]),
                reverse=True
            )

        # Return up to max_results
        logger.debug(f"Returning {max_results} results")
        return sorted_results[:max_results]
