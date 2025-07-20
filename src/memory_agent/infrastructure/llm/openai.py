"""OpenAI LLM provider."""

from typing import Any, AsyncIterator, Dict, List, Optional

from openai import AsyncOpenAI
from structlog import get_logger

from memory_agent.core.entities import Message
from memory_agent.core.interfaces import (
    CompletionOptions,
    CompletionResponse,
    LLMProviderType,
    MessageRole,
    ModelInfo,
    StreamChunk,
    TokenUsage,
)
from memory_agent.infrastructure.llm.base import BaseLLMProvider

logger = get_logger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI LLM provider."""
    
    # Available OpenAI models with their specifications
    AVAILABLE_MODELS = [
        ModelInfo(
            id="gpt-4o",
            name="GPT-4 Optimized",
            context_window=128000,
            max_tokens=16384,
            supports_streaming=True,
            supports_functions=True,
        ),
        ModelInfo(
            id="gpt-4o-mini",
            name="GPT-4 Optimized Mini",
            context_window=128000,
            max_tokens=16384,
            supports_streaming=True,
            supports_functions=True,
        ),
        ModelInfo(
            id="gpt-4-turbo",
            name="GPT-4 Turbo",
            context_window=128000,
            max_tokens=4096,
            supports_streaming=True,
            supports_functions=True,
        ),
        ModelInfo(
            id="gpt-4",
            name="GPT-4",
            context_window=8192,
            max_tokens=4096,
            supports_streaming=True,
            supports_functions=True,
        ),
        ModelInfo(
            id="gpt-3.5-turbo",
            name="GPT-3.5 Turbo",
            context_window=16385,
            max_tokens=4096,
            supports_streaming=True,
            supports_functions=True,
        ),
    ]
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        organization: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs: Any
    ):
        """Initialize OpenAI provider.
        
        Args:
            api_key: OpenAI API key
            organization: OpenAI organization ID
            base_url: Custom base URL (for Azure OpenAI or proxies)
            **kwargs: Additional configuration
        """
        super().__init__(
            provider_type=LLMProviderType.OPENAI,
            api_key=api_key,
            base_url=base_url,
            **kwargs
        )
        
        self.client = AsyncOpenAI(
            api_key=api_key,
            organization=organization,
            base_url=base_url,
        )
        self._available_models = self.AVAILABLE_MODELS.copy()
    
    async def complete(
        self,
        messages: List[Message],
        options: Optional[CompletionOptions] = None,
    ) -> CompletionResponse:
        """Generate a completion."""
        options = options or CompletionOptions()
        
        # Convert messages to OpenAI format
        openai_messages = [
            {
                "role": msg.role.value,
                "content": msg.content,
            }
            for msg in messages
        ]
        
        # Add system message if provided
        if options.system_message:
            openai_messages.insert(0, {
                "role": "system",
                "content": options.system_message,
            })
        
        try:
            # Make request
            response = await self.client.chat.completions.create(
                model=options.model or "gpt-4o-mini",
                messages=openai_messages,
                temperature=options.temperature,
                top_p=options.top_p,
                max_tokens=options.max_tokens,
                stop=options.stop_sequences,
                stream=False,
            )
            
            # Extract response
            choice = response.choices[0]
            content = choice.message.content or ""
            
            # Convert usage
            usage = TokenUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )
            
            return CompletionResponse(
                content=content,
                model=response.model,
                usage=usage,
                finish_reason=choice.finish_reason or "stop",
            )
            
        except Exception as e:
            logger.error(
                "OpenAI API error",
                error=str(e),
                model=options.model,
            )
            raise
    
    async def complete_stream(
        self,
        messages: List[Message],
        options: Optional[CompletionOptions] = None,
    ) -> AsyncIterator[StreamChunk]:
        """Generate a streaming completion."""
        options = options or CompletionOptions()
        
        # Convert messages to OpenAI format
        openai_messages = [
            {
                "role": msg.role.value,
                "content": msg.content,
            }
            for msg in messages
        ]
        
        # Add system message if provided
        if options.system_message:
            openai_messages.insert(0, {
                "role": "system",
                "content": options.system_message,
            })
        
        try:
            # Make streaming request
            stream = await self.client.chat.completions.create(
                model=options.model or "gpt-4o-mini",
                messages=openai_messages,
                temperature=options.temperature,
                top_p=options.top_p,
                max_tokens=options.max_tokens,
                stop=options.stop_sequences,
                stream=True,
            )
            
            # Stream chunks
            accumulated_content = ""
            async for chunk in stream:
                if not chunk.choices:
                    continue
                
                choice = chunk.choices[0]
                content = choice.delta.content or ""
                accumulated_content += content
                
                # Check if this is the last chunk
                if choice.finish_reason:
                    # Estimate usage for the final chunk
                    usage = self._calculate_token_usage(
                        messages,
                        accumulated_content,
                        chunk.model,
                    )
                    
                    yield StreamChunk(
                        content=content,
                        model=chunk.model,
                        finish_reason=choice.finish_reason,
                        usage=usage,
                    )
                else:
                    yield StreamChunk(
                        content=content,
                        model=chunk.model,
                        finish_reason=None,
                    )
                    
        except Exception as e:
            logger.error(
                "OpenAI streaming API error",
                error=str(e),
                model=options.model,
            )
            raise
    
    async def get_available_models(self) -> List[ModelInfo]:
        """Get available models."""
        return self._available_models
    
    async def validate_model(self, model_id: str) -> bool:
        """Validate if a model is available."""
        return any(m.id == model_id for m in self._available_models)
    
    async def shutdown(self) -> None:
        """Shutdown the provider."""
        await self.client.close()