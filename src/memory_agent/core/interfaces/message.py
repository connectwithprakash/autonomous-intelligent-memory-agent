"""Message interface definitions for the memory agent."""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from pydantic import BaseModel


class MessageRole(str, Enum):
    """Roles for messages in the conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class MessageType(str, Enum):
    """Types of messages for categorization."""

    TEXT = "text"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    CORRECTION = "correction"


@runtime_checkable
class IMessage(Protocol):
    """Protocol for messages in the conversation chain."""

    @property
    def id(self) -> str:
        """Unique identifier for the message."""
        ...

    @property
    def role(self) -> MessageRole:
        """Role of the message sender."""
        ...

    @property
    def content(self) -> str:
        """Content of the message."""
        ...

    @property
    def timestamp(self) -> datetime:
        """When the message was created."""
        ...

    @property
    def metadata(self) -> Dict[str, Any]:
        """Additional metadata for the message."""
        ...


@runtime_checkable
class IMessageChain(Protocol):
    """Protocol for managing a chain of messages."""

    async def add_message(self, message: IMessage) -> str:
        """Add a message to the chain.
        
        Args:
            message: The message to add
            
        Returns:
            The ID of the added message
        """
        ...

    async def remove_message(self, message_id: str) -> bool:
        """Remove a message from the chain.
        
        Args:
            message_id: ID of the message to remove
            
        Returns:
            True if removed, False if not found
        """
        ...

    async def get_messages(self, session_id: str) -> List[IMessage]:
        """Get all messages in the chain for a session.
        
        Args:
            session_id: The session identifier
            
        Returns:
            List of messages in chronological order
        """
        ...

    async def rollback_to(self, message_id: str) -> bool:
        """Rollback the chain to a specific message.
        
        Args:
            message_id: ID of the message to rollback to
            
        Returns:
            True if successful, False otherwise
        """
        ...

    async def validate_chain(self) -> bool:
        """Validate the integrity of the message chain.
        
        Returns:
            True if chain is valid, False otherwise
        """
        ...

    async def get_context_window(
        self, max_tokens: int, session_id: str
    ) -> List[IMessage]:
        """Get messages that fit within a token limit.
        
        Args:
            max_tokens: Maximum number of tokens
            session_id: The session identifier
            
        Returns:
            List of messages within token limit
        """
        ...