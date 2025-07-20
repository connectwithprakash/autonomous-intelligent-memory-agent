#!/usr/bin/env python3
"""Example script to test LLM providers."""

import asyncio
import os
from typing import List

from memory_agent.core.entities import Message
from memory_agent.core.interfaces import (
    CompletionOptions,
    LLMProviderType,
    MessageRole,
)
from memory_agent.infrastructure.llm import LLMProviderFactory


async def test_provider(provider_type: LLMProviderType, model: str = None):
    """Test a specific LLM provider."""
    print(f"\n=== Testing {provider_type.value} ===")
    
    # Create provider config
    config = {}
    if provider_type == LLMProviderType.OLLAMA:
        config["base_url"] = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    elif provider_type == LLMProviderType.OPENAI:
        config["api_key"] = os.getenv("OPENAI_API_KEY")
        if not config["api_key"]:
            print("Skipping OpenAI - no API key set")
            return
    elif provider_type == LLMProviderType.ANTHROPIC:
        config["api_key"] = os.getenv("ANTHROPIC_API_KEY")
        if not config["api_key"]:
            print("Skipping Anthropic - no API key set")
            return
    
    try:
        # Create provider
        provider = LLMProviderFactory.create(provider_type, config)
        await provider.initialize()
        
        # List available models
        models = await provider.get_available_models()
        print(f"Available models: {[m.id for m in models]}")
        
        # Use first model if not specified
        if not model:
            if not models:
                print("No models available")
                return
            model = models[0].id
        
        print(f"Using model: {model}")
        
        # Create test messages
        messages = [
            Message(
                role=MessageRole.USER,
                content="Write a haiku about artificial intelligence.",
            )
        ]
        
        # Test non-streaming completion
        print("\n--- Non-streaming completion ---")
        options = CompletionOptions(
            model=model,
            temperature=0.7,
            max_tokens=100,
        )
        
        response = await provider.complete(messages, options)
        print(f"Response: {response.content}")
        print(f"Tokens: {response.usage.total_tokens} "
              f"(prompt: {response.usage.prompt_tokens}, "
              f"completion: {response.usage.completion_tokens})")
        
        # Test streaming completion
        print("\n--- Streaming completion ---")
        print("Response: ", end="", flush=True)
        
        total_content = ""
        async for chunk in provider.complete_stream(messages, options):
            if chunk.content:
                print(chunk.content, end="", flush=True)
                total_content += chunk.content
            if chunk.finish_reason:
                print()  # New line
                if chunk.usage:
                    print(f"Tokens: {chunk.usage.total_tokens}")
        
        # Cleanup
        await provider.shutdown()
        
    except Exception as e:
        print(f"Error: {e}")


async def main():
    """Test all available providers."""
    # Test Ollama (local)
    await test_provider(LLMProviderType.OLLAMA, "llama3.2")
    
    # Test OpenAI (if API key is set)
    await test_provider(LLMProviderType.OPENAI, "gpt-4o-mini")
    
    # Test Anthropic (if API key is set)
    await test_provider(LLMProviderType.ANTHROPIC, "claude-3-5-haiku-20241022")


if __name__ == "__main__":
    print("Testing LLM Providers")
    print("====================")
    print()
    print("Make sure you have:")
    print("1. Ollama running locally (ollama serve)")
    print("2. Environment variables set for API keys:")
    print("   - OPENAI_API_KEY")
    print("   - ANTHROPIC_API_KEY")
    
    asyncio.run(main())