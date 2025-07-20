"""LLM provider interface definitions."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional, Protocol, runtime_checkable

from pydantic import BaseModel

from .message import IMessage


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    MOCK = "mock"


# Alias for backward compatibility
LLMProviderType = LLMProvider


class ModelInfo(BaseModel):
    """Information about an available model."""
    
    id: str
    name: str
    description: Optional[str] = None
    context_window: Optional[int] = None
    capabilities: List[str] = []
    metadata: Dict[str, Any] = {}


class TokenUsage(BaseModel):
    """Token usage information."""
    
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    
    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
        )


class StreamChunk(BaseModel):
    """A chunk from streaming response."""
    
    content: str
    finish_reason: Optional[str] = None
    model: Optional[str] = None
    usage: Optional[TokenUsage] = None


class CompletionOptions(BaseModel):
    """Options for LLM completion requests."""

    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: float = 1.0
    stop_sequences: Optional[List[str]] = None
    stream: bool = False


class CompletionResponse(BaseModel):
    """Response from LLM completion."""

    content: str
    model: str
    usage: Dict[str, int]  # tokens used, etc.
    finish_reason: str
    metadata: Dict[str, Any] = {}


@runtime_checkable
class ILLMProvider(Protocol):
    """Protocol for LLM providers."""

    @property
    def name(self) -> str:
        """Name of the provider."""
        ...

    @property
    def model(self) -> str:
        """Model identifier."""
        ...

    async def complete(
        self,
        messages: List[IMessage],
        options: Optional[CompletionOptions] = None,
    ) -> CompletionResponse:
        """Generate a completion from messages.
        
        Args:
            messages: List of messages for context
            options: Completion options
            
        Returns:
            Completion response
        """
        ...

    async def stream_complete(
        self,
        messages: List[IMessage],
        options: Optional[CompletionOptions] = None,
    ) -> AsyncIterator[str]:
        """Stream a completion from messages.
        
        Args:
            messages: List of messages for context
            options: Completion options
            
        Yields:
            Chunks of the completion
        """
        ...

    async def embed(self, text: str) -> List[float]:
        """Generate embeddings for text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        ...

    async def count_tokens(self, text: str) -> int:
        """Count tokens in text.
        
        Args:
            text: Text to count
            
        Returns:
            Number of tokens
        """
        ...

    async def validate_connection(self) -> bool:
        """Validate the provider connection.
        
        Returns:
            True if connection is valid
        """
        ...