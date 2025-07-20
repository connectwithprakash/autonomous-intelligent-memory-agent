"""Anthropic Claude LLM provider."""

from typing import Any, AsyncIterator, Dict, List, Optional

from anthropic import AsyncAnthropic
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


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude LLM provider."""
    
    # Available Claude models with their specifications
    AVAILABLE_MODELS = [
        ModelInfo(
            id="claude-3-5-sonnet-20241022",
            name="Claude 3.5 Sonnet",
            context_window=200000,
            max_tokens=8192,
            supports_streaming=True,
            supports_functions=True,
        ),
        ModelInfo(
            id="claude-3-5-haiku-20241022",
            name="Claude 3.5 Haiku",
            context_window=200000,
            max_tokens=8192,
            supports_streaming=True,
            supports_functions=True,
        ),
        ModelInfo(
            id="claude-3-opus-20240229",
            name="Claude 3 Opus",
            context_window=200000,
            max_tokens=4096,
            supports_streaming=True,
            supports_functions=True,
        ),
        ModelInfo(
            id="claude-3-sonnet-20240229",
            name="Claude 3 Sonnet",
            context_window=200000,
            max_tokens=4096,
            supports_streaming=True,
            supports_functions=True,
        ),
        ModelInfo(
            id="claude-3-haiku-20240307",
            name="Claude 3 Haiku",
            context_window=200000,
            max_tokens=4096,
            supports_streaming=True,
            supports_functions=True,
        ),
    ]
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs: Any
    ):
        """Initialize Anthropic provider.
        
        Args:
            api_key: Anthropic API key
            base_url: Custom base URL
            **kwargs: Additional configuration
        """
        super().__init__(
            provider_type=LLMProviderType.ANTHROPIC,
            api_key=api_key,
            base_url=base_url,
            **kwargs
        )
        
        self.client = AsyncAnthropic(
            api_key=api_key,
            base_url=base_url,
        )
        self._available_models = self.AVAILABLE_MODELS.copy()
    
    def _convert_messages_for_anthropic(
        self,
        messages: List[Message],
        system_message: Optional[str] = None,
    ) -> tuple[Optional[str], List[Dict[str, Any]]]:
        """Convert messages to Anthropic format.
        
        Anthropic requires system messages to be separate and
        alternating user/assistant messages.
        
        Args:
            messages: List of messages
            system_message: Optional system message
            
        Returns:
            Tuple of (system_message, anthropic_messages)
        """
        anthropic_messages = []
        combined_system = system_message or ""
        
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                # Combine system messages
                if combined_system:
                    combined_system += "\n\n"
                combined_system += msg.content
            else:
                anthropic_messages.append({
                    "role": msg.role.value,
                    "content": msg.content,
                })
        
        # Ensure messages alternate between user and assistant
        # Anthropic requires the first message to be from the user
        if anthropic_messages and anthropic_messages[0]["role"] == "assistant":
            anthropic_messages.insert(0, {
                "role": "user",
                "content": "Continue the conversation.",
            })
        
        return combined_system or None, anthropic_messages
    
    async def complete(
        self,
        messages: List[Message],
        options: Optional[CompletionOptions] = None,
    ) -> CompletionResponse:
        """Generate a completion."""
        options = options or CompletionOptions()
        
        # Convert messages to Anthropic format
        system_message, anthropic_messages = self._convert_messages_for_anthropic(
            messages,
            options.system_message,
        )
        
        try:
            # Make request
            response = await self.client.messages.create(
                model=options.model or "claude-3-5-sonnet-20241022",
                messages=anthropic_messages,
                system=system_message,
                temperature=options.temperature,
                top_p=options.top_p,
                max_tokens=options.max_tokens or 4096,
                stop_sequences=options.stop_sequences,
                stream=False,
            )
            
            # Extract content
            content = ""
            for block in response.content:
                if block.type == "text":
                    content += block.text
            
            # Convert usage
            usage = TokenUsage(
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            )
            
            return CompletionResponse(
                content=content,
                model=response.model,
                usage=usage,
                finish_reason=response.stop_reason or "stop",
            )
            
        except Exception as e:
            logger.error(
                "Anthropic API error",
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
        
        # Convert messages to Anthropic format
        system_message, anthropic_messages = self._convert_messages_for_anthropic(
            messages,
            options.system_message,
        )
        
        try:
            # Make streaming request
            async with self.client.messages.stream(
                model=options.model or "claude-3-5-sonnet-20241022",
                messages=anthropic_messages,
                system=system_message,
                temperature=options.temperature,
                top_p=options.top_p,
                max_tokens=options.max_tokens or 4096,
                stop_sequences=options.stop_sequences,
            ) as stream:
                # Track accumulated content for usage estimation
                accumulated_content = ""
                
                async for event in stream:
                    if event.type == "content_block_delta":
                        # Text content chunk
                        if event.delta.type == "text_delta":
                            content = event.delta.text
                            accumulated_content += content
                            
                            yield StreamChunk(
                                content=content,
                                model=stream.response.model,
                                finish_reason=None,
                            )
                    
                    elif event.type == "message_stop":
                        # Final chunk with usage
                        usage = TokenUsage(
                            prompt_tokens=stream.response.usage.input_tokens,
                            completion_tokens=stream.response.usage.output_tokens,
                            total_tokens=(
                                stream.response.usage.input_tokens +
                                stream.response.usage.output_tokens
                            ),
                        )
                        
                        yield StreamChunk(
                            content="",
                            model=stream.response.model,
                            finish_reason=stream.response.stop_reason or "stop",
                            usage=usage,
                        )
                        
        except Exception as e:
            logger.error(
                "Anthropic streaming API error",
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