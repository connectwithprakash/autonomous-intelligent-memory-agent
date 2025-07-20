"""LLM service for managing providers."""

from typing import Dict, List, Optional

from structlog import get_logger

from memory_agent.core.entities import Message
from memory_agent.core.interfaces import (
    CompletionOptions,
    CompletionResponse,
    ILLMProvider,
    LLMProviderType,
    ModelInfo,
)
from memory_agent.infrastructure.config.settings import settings
from memory_agent.infrastructure.llm.factory import LLMProviderFactory

logger = get_logger(__name__)


class LLMService:
    """Service for managing LLM providers."""
    
    def __init__(self):
        """Initialize LLM service."""
        self._providers: Dict[LLMProviderType, ILLMProvider] = {}
        self._current_provider: Optional[ILLMProvider] = None
        self._current_provider_type: Optional[LLMProviderType] = None
    
    async def initialize(self) -> None:
        """Initialize the service with default provider."""
        provider_type = self._get_provider_type_from_string(settings.llm_provider)
        await self.set_provider(provider_type)
    
    def _get_provider_type_from_string(self, provider_str: str) -> LLMProviderType:
        """Convert provider string to enum."""
        try:
            return LLMProviderType[provider_str.upper()]
        except KeyError:
            logger.warning(
                f"Unknown provider '{provider_str}', defaulting to Ollama",
                provider=provider_str,
            )
            return LLMProviderType.OLLAMA
    
    def _get_provider_config(self, provider_type: LLMProviderType) -> Dict:
        """Get provider configuration from settings."""
        base_config = {
            "temperature": settings.llm_temperature,
            "max_tokens": settings.llm_max_tokens,
        }
        
        if provider_type == LLMProviderType.OLLAMA:
            return {
                **base_config,
                "base_url": settings.ollama_base_url,
            }
        elif provider_type == LLMProviderType.OPENAI:
            return {
                **base_config,
                "api_key": settings.openai_api_key,
                "organization": settings.openai_organization,
                "base_url": settings.openai_base_url,
            }
        elif provider_type == LLMProviderType.ANTHROPIC:
            return {
                **base_config,
                "api_key": settings.anthropic_api_key,
                "base_url": settings.anthropic_base_url,
            }
        
        return base_config
    
    async def set_provider(
        self,
        provider_type: LLMProviderType,
        config: Optional[Dict] = None,
    ) -> None:
        """Set the active LLM provider.
        
        Args:
            provider_type: Type of provider to use
            config: Optional provider configuration
        """
        # Check if we already have this provider
        if provider_type not in self._providers:
            # Create new provider
            provider_config = config or self._get_provider_config(provider_type)
            provider = LLMProviderFactory.create(provider_type, provider_config)
            await provider.initialize()
            self._providers[provider_type] = provider
        
        # Set as current provider
        self._current_provider = self._providers[provider_type]
        self._current_provider_type = provider_type
        
        logger.info(
            "Set LLM provider",
            provider=provider_type.value,
            models=len(await self._current_provider.get_available_models()),
        )
    
    async def get_current_provider(self) -> ILLMProvider:
        """Get the current LLM provider.
        
        Returns:
            Current LLM provider
            
        Raises:
            RuntimeError: If no provider is set
        """
        if not self._current_provider:
            await self.initialize()
        
        if not self._current_provider:
            raise RuntimeError("No LLM provider is set")
        
        return self._current_provider
    
    async def complete(
        self,
        messages: List[Message],
        options: Optional[CompletionOptions] = None,
        provider_type: Optional[LLMProviderType] = None,
    ) -> CompletionResponse:
        """Generate a completion.
        
        Args:
            messages: List of messages
            options: Completion options
            provider_type: Optional provider to use (uses current if not specified)
            
        Returns:
            Completion response
        """
        # Switch provider if specified
        if provider_type and provider_type != self._current_provider_type:
            await self.set_provider(provider_type)
        
        provider = await self.get_current_provider()
        
        # Set default model if not specified
        if options and not options.model:
            # Get provider default model
            if self._current_provider_type == LLMProviderType.OLLAMA:
                options.model = settings.llm_model or "llama3.2"
            elif self._current_provider_type == LLMProviderType.OPENAI:
                options.model = settings.llm_model or "gpt-4o-mini"
            elif self._current_provider_type == LLMProviderType.ANTHROPIC:
                options.model = settings.llm_model or "claude-3-5-sonnet-20241022"
        
        return await provider.complete(messages, options)
    
    async def get_available_providers(self) -> List[LLMProviderType]:
        """Get list of available providers."""
        return list(LLMProviderType)
    
    async def get_available_models(
        self,
        provider_type: Optional[LLMProviderType] = None,
    ) -> List[ModelInfo]:
        """Get available models for a provider.
        
        Args:
            provider_type: Provider to query (uses current if not specified)
            
        Returns:
            List of available models
        """
        if provider_type and provider_type != self._current_provider_type:
            # Temporarily create provider to get models
            config = self._get_provider_config(provider_type)
            provider = LLMProviderFactory.create(provider_type, config)
            await provider.initialize()
            models = await provider.get_available_models()
            await provider.shutdown()
            return models
        
        provider = await self.get_current_provider()
        return await provider.get_available_models()
    
    async def validate_model(
        self,
        model_id: str,
        provider_type: Optional[LLMProviderType] = None,
    ) -> bool:
        """Validate if a model is available.
        
        Args:
            model_id: Model ID to validate
            provider_type: Provider to check (uses current if not specified)
            
        Returns:
            True if model is available
        """
        models = await self.get_available_models(provider_type)
        return any(m.id == model_id for m in models)
    
    async def get_provider_info(self) -> Dict:
        """Get information about the current provider.
        
        Returns:
            Provider information
        """
        provider = await self.get_current_provider()
        models = await provider.get_available_models()
        
        return {
            "provider": self._current_provider_type.value,
            "models": [
                {
                    "id": m.id,
                    "name": m.name,
                    "context_window": m.context_window,
                    "max_tokens": m.max_tokens,
                    "supports_streaming": m.supports_streaming,
                    "supports_functions": m.supports_functions,
                }
                for m in models
            ],
            "default_model": settings.llm_model,
            "temperature": settings.llm_temperature,
            "max_tokens": settings.llm_max_tokens,
        }
    
    async def shutdown(self) -> None:
        """Shutdown all providers."""
        for provider in self._providers.values():
            await provider.shutdown()
        self._providers.clear()
        self._current_provider = None
        self._current_provider_type = None


# Global LLM service instance
llm_service = LLMService()