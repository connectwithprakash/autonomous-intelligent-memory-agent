"""Ollama LLM provider for local models."""

import json
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx
from structlog import get_logger

from memory_agent.core.entities import Message
from memory_agent.core.interfaces import (
    CompletionOptions,
    CompletionResponse,
    LLMProviderType,
    ModelInfo,
    StreamChunk,
)
from memory_agent.infrastructure.config.settings import settings
from memory_agent.infrastructure.llm.base import BaseLLMProvider

logger = get_logger(__name__)


class OllamaProvider(BaseLLMProvider):
    """Ollama provider for local LLM models."""
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        timeout: float = 120.0,
        **kwargs: Any
    ):
        """Initialize Ollama provider.
        
        Args:
            base_url: Ollama API base URL
            timeout: Request timeout in seconds
            **kwargs: Additional configuration
        """
        super().__init__(
            provider_type=LLMProviderType.OLLAMA,
            base_url=base_url,
            **kwargs
        )
        self.timeout = timeout
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
        )
    
    async def _load_available_models(self) -> None:
        """Load available models from Ollama."""
        try:
            response = await self.client.get("/api/tags")
            response.raise_for_status()
            
            data = response.json()
            self._available_models = [
                ModelInfo(
                    id=model["name"],
                    name=model["name"],
                    context_window=model.get("context_length", 4096),
                    capabilities=[],
                    metadata={}
                )
                for model in data.get("models", [])
            ]
            
            logger.info(
                "Loaded Ollama models",
                count=len(self._available_models),
                models=[m.id for m in self._available_models],
            )
        except Exception as e:
            logger.warning(
                "Failed to load Ollama models",
                error=str(e),
                hint="Make sure Ollama is running at " + self.base_url,
            )
            # Provide some default models even if we can't connect
            self._available_models = [
                ModelInfo(
                    id="llama3.2",
                    name="Llama 3.2",
                    context_window=8192,
                    capabilities=["chat", "streaming"],
                    metadata={"max_tokens": 4096}
                ),
                ModelInfo(
                    id="mistral",
                    name="Mistral",
                    context_window=8192,
                    capabilities=["chat", "streaming"],
                    metadata={"max_tokens": 4096}
                ),
                ModelInfo(
                    id="phi3",
                    name="Phi-3",
                    context_window=4096,
                    capabilities=["chat", "streaming"],
                    metadata={"max_tokens": 2048}
                ),
            ]
    
    async def complete(
        self,
        messages: List[Message],
        options: Optional[CompletionOptions] = None,
    ) -> CompletionResponse:
        """Generate a completion."""
        options = options or CompletionOptions()
        
        # Convert messages to Ollama format
        ollama_messages = self._messages_to_provider_format(messages)
        
        # Prepare request
        # Get model from config or settings
        model = self.config.get("model") or settings.llm_model or "llama3.2"
        
        request_data = {
            "model": model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": options.temperature,
                "top_p": options.top_p,
                "num_predict": options.max_tokens,
            },
        }
        
        if options.stop_sequences:
            request_data["options"]["stop"] = options.stop_sequences
        
        try:
            # Make request
            response = await self.client.post(
                "/api/chat",
                json=request_data,
            )
            response.raise_for_status()
            
            data = response.json()
            content = data["message"]["content"]
            
            # Calculate token usage
            usage = self._calculate_token_usage(
                messages,
                content,
                model,
            )
            
            # Update with actual token counts if available
            if "prompt_eval_count" in data:
                usage.prompt_tokens = data["prompt_eval_count"]
            if "eval_count" in data:
                usage.completion_tokens = data["eval_count"]
            usage.total_tokens = usage.prompt_tokens + usage.completion_tokens
            
            return CompletionResponse(
                content=content,
                model=data.get("model", model),
                usage={
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens,
                },
                finish_reason="stop",
            )
            
        except httpx.HTTPStatusError as e:
            logger.error(
                "Ollama API error",
                status_code=e.response.status_code,
                response=e.response.text,
            )
            raise
        except Exception as e:
            logger.error("Failed to complete with Ollama", error=str(e))
            raise
    
    async def stream_complete(
        self,
        messages: List[Message],
        options: Optional[CompletionOptions] = None,
    ) -> AsyncIterator[str]:
        """Generate a streaming completion."""
        options = options or CompletionOptions()
        
        # Convert messages to Ollama format
        ollama_messages = self._messages_to_provider_format(messages)
        
        # Get model from config or settings
        model = self.config.get("model") or settings.llm_model or "llama3.2"
        
        # Prepare request
        request_data = {
            "model": model,
            "messages": ollama_messages,
            "stream": True,
            "options": {
                "temperature": options.temperature,
                "top_p": options.top_p,
                "num_predict": options.max_tokens,
            },
        }
        
        if options.stop_sequences:
            request_data["options"]["stop"] = options.stop_sequences
        
        try:
            # Make streaming request
            async with self.client.stream(
                "POST",
                "/api/chat",
                json=request_data,
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    
                    try:
                        data = json.loads(line)
                        
                        # Extract content from the message
                        if "message" in data and "content" in data["message"]:
                            yield data["message"]["content"]
                        
                        # Check if done
                        if data.get("done", False):
                            break
                            
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse Ollama stream chunk", line=line)
                        continue
                        
        except httpx.HTTPStatusError as e:
            logger.error(
                "Ollama streaming API error",
                status_code=e.response.status_code,
                response=e.response.text,
            )
            raise
        except Exception as e:
            logger.error("Failed to stream with Ollama", error=str(e))
            raise
    
    async def get_available_models(self) -> List[ModelInfo]:
        """Get available models."""
        if not self._available_models:
            await self._load_available_models()
        return self._available_models
    
    async def validate_model(self, model_id: str) -> bool:
        """Validate if a model is available."""
        models = await self.get_available_models()
        return any(m.id == model_id for m in models)
    
    async def shutdown(self) -> None:
        """Shutdown the provider."""
        await self.client.aclose()