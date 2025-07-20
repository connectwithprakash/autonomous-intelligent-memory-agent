"""Base LLM provider implementation."""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional

from structlog import get_logger

from memory_agent.core.entities import Message
from memory_agent.core.interfaces import (
    CompletionOptions,
    CompletionResponse,
    ILLMProvider,
    LLMProviderType,
    ModelInfo,
    StreamChunk,
    TokenUsage,
)

logger = get_logger(__name__)


class BaseLLMProvider(ILLMProvider, ABC):
    """Base implementation for LLM providers."""
    
    def __init__(
        self,
        provider_type: LLMProviderType,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs: Any
    ):
        """Initialize base LLM provider.
        
        Args:
            provider_type: Type of the LLM provider
            api_key: API key for authentication
            base_url: Base URL for API calls
            **kwargs: Additional provider-specific arguments
        """
        self.provider_type = provider_type
        self.api_key = api_key
        self.base_url = base_url
        self.config = kwargs
        self._available_models: List[ModelInfo] = []
    
    @property
    def name(self) -> str:
        """Name of the provider."""
        return self.provider_type.value
    
    @property
    def model(self) -> str:
        """Model identifier."""
        return self.config.get("model", "default")
    
    async def initialize(self) -> None:
        """Initialize the provider."""
        logger.info(
            "Initializing LLM provider",
            provider=self.provider_type.value,
            base_url=self.base_url,
        )
        await self._load_available_models()
    
    async def _load_available_models(self) -> None:
        """Load available models for this provider."""
        # To be implemented by subclasses
        pass
    
    def _messages_to_provider_format(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """Convert messages to provider-specific format.
        
        Args:
            messages: List of messages
            
        Returns:
            Provider-specific message format
        """
        return [
            {
                "role": msg.role.value,
                "content": msg.content,
            }
            for msg in messages
        ]
    
    def _calculate_token_usage(
        self,
        messages: List[Message],
        response: str,
        model: str,
    ) -> TokenUsage:
        """Calculate token usage for the request.
        
        Args:
            messages: Input messages
            response: Generated response
            model: Model used
            
        Returns:
            Token usage information
        """
        # Simple estimation - should be overridden by providers with actual counts
        prompt_tokens = sum(len(msg.content.split()) * 1.3 for msg in messages)
        completion_tokens = len(response.split()) * 1.3
        
        return TokenUsage(
            prompt_tokens=int(prompt_tokens),
            completion_tokens=int(completion_tokens),
            total_tokens=int(prompt_tokens + completion_tokens),
        )
    
    @abstractmethod
    async def complete(
        self,
        messages: List[Message],
        options: Optional[CompletionOptions] = None,
    ) -> CompletionResponse:
        """Generate a completion from messages."""
        ...
    
    @abstractmethod
    async def stream_complete(
        self,
        messages: List[Message],
        options: Optional[CompletionOptions] = None,
    ) -> AsyncIterator[str]:
        """Stream a completion from messages."""
        ...
    
    async def embed(self, text: str) -> List[float]:
        """Generate embeddings for text."""
        raise NotImplementedError(f"{self.name} does not support embeddings")
    
    async def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        # Simple estimation
        return int(len(text.split()) * 1.3)
    
    async def validate_connection(self) -> bool:
        """Validate the provider connection."""
        try:
            models = await self.get_available_models()
            return len(models) > 0
        except Exception:
            return False
    
    @abstractmethod
    async def get_available_models(self) -> List[ModelInfo]:
        """Get available models."""
        ...