from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, List, Optional

from langchain_community.chat_message_histories import CosmosDBChatMessageHistory
from langchain_core.messages import (
    BaseMessage,
    messages_to_dict,
    messages_from_dict,
)

from datetime import datetime

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
        history_limit: Optional[int] = 5,
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

        self.history: List[BaseMessage] = []
        self.history_limit = history_limit
        self.session_start_timestamp = None

    def add_message(self, message: BaseMessage) -> None:
        self.history.append(message)
        super().add_message(message)
    
    def load_messages(self):
        """Retrieve the messages from Cosmos"""
        if not self._container:
            raise ValueError("Container not initialized")
        try:
            from azure.cosmos.exceptions import (  # pylint: disable=import-outside-toplevel
                CosmosHttpResponseError,
            )
        except ImportError as exc:
            raise ImportError(
                "You must install the azure-cosmos package to use the CosmosDBChatMessageHistory."  # noqa: E501
                "Please install it with `pip install azure-cosmos`."
            ) from exc
        try:
            item = self._container.read_item(
                item=self.session_id, partition_key=self.user_id
            )
        except CosmosHttpResponseError:
            logger.info("no session found")
            return
        if "messages" in item and len(item["messages"]) > 0:
            self.messages = messages_from_dict(item["messages"])
        if "session_start_ts" in item:
            self.session_start_timestamp = item["session_start_ts"]
        # Copy context messages to history if empty
        if not self.history and self.messages:
            self.history = self.messages.copy()
        # Trim context messages
        if len(self.messages) > self.history_limit and self.history_limit > 0:
            logger.debug(f"Limiting history to {self.history_limit} messages")
            self.messages = self.messages[(-1*self.history_limit):]

    def upsert_messages(self):
        """Update the cosmosdb item."""
        if not self._container:
            raise ValueError("Container not initialized")
        if not self.session_start_timestamp:
            self.session_start_timestamp = int(datetime.now().timestamp())
        self._container.upsert_item(
            body={
                "id": self.session_id,
                "user_id": self.user_id,
                "messages": messages_to_dict(self.history),
                "session_start_ts": self.session_start_timestamp
            }
        )
    
    def get_session_turn_count(self) -> int:
        message_count = len(self.history)
        session_turn_count = message_count/2
        return session_turn_count
