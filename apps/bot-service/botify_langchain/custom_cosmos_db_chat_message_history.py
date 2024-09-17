from __future__ import annotations

import json
import logging
from typing import Any, Optional

from langchain_community.chat_message_histories import CosmosDBChatMessageHistory
from langchain_core.messages import BaseMessage

logger = logging.getLogger(__name__)


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
                logger.info(f"Failed to parse message content, so keeping original content. Error: {e}")
        super().add_message(message)
