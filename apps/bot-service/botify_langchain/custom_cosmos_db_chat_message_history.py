from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, List, Optional

from langchain_community.chat_message_histories import \
    CosmosDBChatMessageHistory
from langchain_core.messages import BaseMessage

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from azure.cosmos import ContainerProxy


logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from azure.cosmos import ContainerProxy


class CustomCosmosDBChatMessageHistory(CosmosDBChatMessageHistory):
    """Chat message history backed by Azure CosmosDB."""

    def __init__(
        self,
        cosmos_endpoint: str,
        cosmos_database: str,
        cosmos_container: str,
        session_id: str,
        user_id: str,
        credential: Any = None,
        connection_string: Optional[str] = None,
        ttl: Optional[int] = None,
        cosmos_client_kwargs: Optional[dict] = None,
    ):
        super().__init__(
            cosmos_endpoint,
            cosmos_database,
            cosmos_container,
            session_id,
            user_id,
            credential,
            connection_string,
            ttl,
            cosmos_client_kwargs,
        )

    def add_message(self, message: BaseMessage) -> None:
        if message.type == "ai":
            try:
                content_object = json.loads(message.content)
                message.content = content_object["displayResponse"]
            except Exception as e:
                logger.info(
                    "Failed to parse message content, so keeping original content")
        super().add_message(message)
