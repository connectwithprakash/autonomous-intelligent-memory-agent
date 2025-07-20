"""LLM provider factory."""

import os
from typing import Any, Dict, Optional

from structlog import get_logger

from memory_agent.core.interfaces import ILLMProvider, LLMProviderType
from memory_agent.infrastructure.llm.anthropic import AnthropicProvider
from memory_agent.infrastructure.llm.ollama import OllamaProvider
from memory_agent.infrastructure.llm.openai import OpenAIProvider

logger = get_logger(__name__)


class LLMProviderFactory:
    """Factory for creating LLM providers."""
    
    # Provider implementations
    _providers = {
        LLMProviderType.OLLAMA: OllamaProvider,
        LLMProviderType.OPENAI: OpenAIProvider,
        LLMProviderType.ANTHROPIC: AnthropicProvider,
    }
    
    @classmethod
    def create(
        cls,
        provider_type: LLMProviderType,
        config: Optional[Dict[str, Any]] = None,
    ) -> ILLMProvider:
        """Create an LLM provider instance.
        
        Args:
            provider_type: Type of provider to create
            config: Provider-specific configuration
            
        Returns:
            LLM provider instance
            
        Raises:
            ValueError: If provider type is not supported
        """
        if provider_type not in cls._providers:
            raise ValueError(f"Unsupported provider type: {provider_type}")
        
        config = config or {}
        provider_class = cls._providers[provider_type]
        
        # Add API keys from environment if not in config
        if provider_type == LLMProviderType.OPENAI and "api_key" not in config:
            config["api_key"] = os.getenv("OPENAI_API_KEY")
        elif provider_type == LLMProviderType.ANTHROPIC and "api_key" not in config:
            config["api_key"] = os.getenv("ANTHROPIC_API_KEY")
        
        logger.info(
            "Creating LLM provider",
            provider_type=provider_type.value,
            has_api_key=bool(config.get("api_key")),
        )
        
        return provider_class(**config)
    
    @classmethod
    def create_from_config(cls, config: Dict[str, Any]) -> ILLMProvider:
        """Create an LLM provider from configuration.
        
        Args:
            config: Configuration dictionary with at least:
                - provider: Provider type (ollama, openai, anthropic)
                - Additional provider-specific settings
                
        Returns:
            LLM provider instance
        """
        provider_str = config.pop("provider", "ollama").upper()
        
        try:
            provider_type = LLMProviderType[provider_str]
        except KeyError:
            raise ValueError(f"Unknown provider: {provider_str}")
        
        return cls.create(provider_type, config)
    
    @classmethod
    def get_default_config(cls, provider_type: LLMProviderType) -> Dict[str, Any]:
        """Get default configuration for a provider type.
        
        Args:
            provider_type: Provider type
            
        Returns:
            Default configuration dictionary
        """
        configs = {
            LLMProviderType.OLLAMA: {
                "base_url": "http://localhost:11434",
                "timeout": 120.0,
                "model": "llama3.2",
            },
            LLMProviderType.OPENAI: {
                "model": "gpt-4o-mini",
                "temperature": 0.7,
                "max_tokens": 2048,
            },
            LLMProviderType.ANTHROPIC: {
                "model": "claude-3-5-sonnet-20241022",
                "temperature": 0.7,
                "max_tokens": 4096,
            },
        }
        
        return configs.get(provider_type, {})