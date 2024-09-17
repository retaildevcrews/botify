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
        vector_query_fields: str = "",
        semantic_config: str = "",
        filter: str = "",
        k: int = 10,
        answers: str = "",
        captions: str = "",
        count: str = "true",
        reranker_threshold: int = 1,
        vector_query_weight: int = 1,
    ) -> List[dict]:
        """Performs multi-index hybrid search and returns ordered dictionary with the combined results"""
        is_semantic = False
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
                "search": query,
                "select": fields_to_select,
                "queryType": "semantic",
                "vectorQueries": [
                    {
                        "text": query,
                        "fields": vector_query_fields,
                        "kind": "text",
                        "k": k,
                        "weight": vector_query_weight,
                    }
                ],
                "semanticConfiguration": semantic_config,
                "count": count,
                "top": k,
            }
            if vector_query_fields != "":
                is_semantic = True
                search_payload["queryType"] = "semantic"
                search_payload["vectorQueries"] = [
                    {
                        "text": query,
                        "fields": vector_query_fields,
                        "kind": "text",
                        "k": k,
                        "weight": vector_query_weight,
                    }
                ]
                search_payload["semanticConfiguration"] = semantic_config
                search_payload["searchMode"] = "any"
            else:
                search_payload["queryType"] = "full"
            if filter:
                search_payload["filter"] = filter
            if answers:
                search_payload["answers"] = answers
            if captions:
                search_payload["captions"] = captions

            resp = requests.post(
                f"{self.search_endpoint}/indexes/{index}/docs/search",
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
                if not is_semantic or result["@search.rerankerScore"] > reranker_threshold:
                    content[result_id] = result
                else:
                    logger.debug(
                        "Reranker Score below threshold for product number "
                        f"{result['id']}, Skipping"
                    )
        # Sort results by score in descending order
        sorted_results = sorted(content.values(), key=lambda item: item["@search.score"], reverse=True)

        # Return up to max_results
        return sorted_results[:max_results]
