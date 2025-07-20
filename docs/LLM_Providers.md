# LLM Provider Configuration

The Memory Agent supports multiple LLM providers, allowing you to use local models with Ollama or cloud-based models from OpenAI and Anthropic.

## Supported Providers

### 1. Ollama (Local Models) - Default

Ollama allows you to run LLMs locally on your machine. This is the default provider as it doesn't require API keys.

**Setup:**
1. Install Ollama: https://ollama.ai/download
2. Start Ollama service: `ollama serve`
3. Pull a model: `ollama pull llama3.2`

**Configuration:**
```bash
# .env
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2
OLLAMA_BASE_URL=http://localhost:11434
```

**Available Models:**
- `llama3.2` - Meta's Llama 3.2 (recommended)
- `mistral` - Mistral 7B
- `phi3` - Microsoft Phi-3
- `codellama` - Code-focused model
- Any model from https://ollama.ai/library

### 2. OpenAI

Use OpenAI's GPT models including GPT-4 and GPT-3.5.

**Setup:**
1. Get API key from https://platform.openai.com/api-keys
2. Set environment variable

**Configuration:**
```bash
# .env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...
OPENAI_ORG=org-...  # Optional
```

**Available Models:**
- `gpt-4o` - GPT-4 Optimized (best performance)
- `gpt-4o-mini` - GPT-4 Optimized Mini (recommended for cost/performance)
- `gpt-4-turbo` - GPT-4 Turbo
- `gpt-4` - GPT-4
- `gpt-3.5-turbo` - GPT-3.5 Turbo (fastest, cheapest)

### 3. Anthropic

Use Anthropic's Claude models.

**Setup:**
1. Get API key from https://console.anthropic.com/
2. Set environment variable

**Configuration:**
```bash
# .env
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=sk-ant-...
```

**Available Models:**
- `claude-3-5-sonnet-20241022` - Claude 3.5 Sonnet (best performance)
- `claude-3-5-haiku-20241022` - Claude 3.5 Haiku (faster, cheaper)
- `claude-3-opus-20240229` - Claude 3 Opus
- `claude-3-sonnet-20240229` - Claude 3 Sonnet
- `claude-3-haiku-20240307` - Claude 3 Haiku

## API Endpoints

The Memory Agent provides REST API endpoints to manage LLM providers:

### List Available Providers
```bash
GET /api/v1/llm/providers
```

### Get Current Provider Info
```bash
GET /api/v1/llm/current
```

### Change Provider
```bash
POST /api/v1/llm/provider
{
  "provider": "ollama",
  "config": {
    "base_url": "http://localhost:11434"
  }
}
```

### List Available Models
```bash
GET /api/v1/llm/models
GET /api/v1/llm/models?provider=openai
```

### Test Completion
```bash
POST /api/v1/llm/test
{
  "prompt": "Hello, how are you?",
  "model": "llama3.2",
  "temperature": 0.7,
  "max_tokens": 100
}
```

## Programmatic Usage

### Using the LLM Service

```python
from memory_agent.infrastructure.llm.service import llm_service
from memory_agent.core.entities import Message
from memory_agent.core.interfaces import MessageRole, CompletionOptions

# Initialize service
await llm_service.initialize()

# Create messages
messages = [
    Message(role=MessageRole.USER, content="Hello!")
]

# Generate completion
response = await llm_service.complete(
    messages,
    CompletionOptions(temperature=0.7, max_tokens=100)
)

print(response.content)
```

### Using Providers Directly

```python
from memory_agent.infrastructure.llm import LLMProviderFactory
from memory_agent.core.interfaces import LLMProviderType

# Create Ollama provider
provider = LLMProviderFactory.create(
    LLMProviderType.OLLAMA,
    {"base_url": "http://localhost:11434"}
)
await provider.initialize()

# List models
models = await provider.get_available_models()
for model in models:
    print(f"{model.id}: {model.name}")

# Generate completion
response = await provider.complete(messages, options)
```

## Switching Providers at Runtime

You can switch providers dynamically through:

1. **API Call:**
```bash
curl -X POST http://localhost:8000/api/v1/llm/provider \
  -H "Content-Type: application/json" \
  -d '{"provider": "openai"}'
```

2. **Environment Variable:**
```bash
export LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=your-key
# Restart the service
```

3. **Programmatically:**
```python
from memory_agent.core.interfaces import LLMProviderType
await llm_service.set_provider(LLMProviderType.OPENAI)
```

## Cost Considerations

- **Ollama**: Free (runs locally, uses your hardware)
- **OpenAI**: 
  - GPT-4o: ~$5/1M input tokens, ~$15/1M output tokens
  - GPT-4o-mini: ~$0.15/1M input tokens, ~$0.60/1M output tokens
  - GPT-3.5-turbo: ~$0.50/1M input tokens, ~$1.50/1M output tokens
- **Anthropic**:
  - Claude 3.5 Sonnet: ~$3/1M input tokens, ~$15/1M output tokens
  - Claude 3.5 Haiku: ~$0.25/1M input tokens, ~$1.25/1M output tokens

## Performance Tips

1. **For Development**: Use Ollama with smaller models (phi3, llama3.2)
2. **For Production**: Consider OpenAI's GPT-4o-mini or Anthropic's Claude 3.5 Haiku for balance
3. **For Best Quality**: Use GPT-4o or Claude 3.5 Sonnet
4. **For Speed**: Use GPT-3.5-turbo or local models with GPU acceleration

## Troubleshooting

### Ollama Issues
- Ensure Ollama is running: `curl http://localhost:11434/api/tags`
- Check if model is downloaded: `ollama list`
- Pull model if missing: `ollama pull llama3.2`

### API Key Issues
- Verify key is set: `echo $OPENAI_API_KEY`
- Check key validity in provider's console
- Ensure no extra spaces or quotes in .env file

### Connection Issues
- Check firewall settings for local Ollama
- Verify proxy settings if using corporate network
- Try direct API calls to validate connectivity