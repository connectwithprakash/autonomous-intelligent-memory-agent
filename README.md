# Autonomous Intelligent Memory Agent

An AI agent system with self-correcting memory management capabilities. The agent monitors conversation flows, evaluates relevance, and automatically corrects mistakes by removing or improving irrelevant messages.

## Features

- **Autonomous Self-Correction**: Automatically detects and corrects irrelevant or problematic messages
- **Multi-Tier Memory Management**: Hot/Warm/Cold storage tiers with automatic migration
- **Multiple LLM Providers**: Support for Ollama (local), OpenAI, and Anthropic
- **Real-Time Monitoring**: WebSocket-based updates with React dashboard and Terminal UI
- **Relevance Evaluation**: Composite evaluation using both heuristic and LLM-based analysis
- **In-Memory Storage**: Efficient memory management with compression for older messages

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      User Interface Layer                     │
├──────────────────────┬────────────────┬────────────────────┤
│   React Dashboard    │   Terminal UI   │    REST API        │
├──────────────────────┴────────────────┴────────────────────┤
│                        WebSocket Layer                        │
├─────────────────────────────────────────────────────────────┤
│                      Memory Agent Core                        │
├─────────────┬────────────────┬─────────────┬───────────────┤
│ LLM Service │ Relevance Eval │  Storage    │ Self-Corrector│
├─────────────┴────────────────┴─────────────┴───────────────┤
│                    Infrastructure Layer                       │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.10+ (tested with 3.12)
- Node.js 18+
- UV package manager
- Ollama (for local LLM support)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd autonomous-intelligent-memory-agent
```

2. Install Python dependencies:
```bash
uv pip install -e .
```

3. Install dashboard dependencies:
```bash
cd dashboard/dashboard
npm install
cd ../..
```

### Running the System

1. Start the API server:
```bash
uv run uvicorn src.memory_agent.infrastructure.api.app:app --reload
```

2. Start the React dashboard (in a new terminal):
```bash
cd dashboard/dashboard
npm run dev
```

3. Start the Terminal UI (optional, in a new terminal):
```bash
uv run python -m memory_agent.cli
```

## Configuration

### Environment Variables

Create a `.env` file in the root directory:

```bash
# LLM Provider Settings
LLM_PROVIDER=ollama  # ollama, openai, or anthropic
LLM_MODEL=llama3.2   # Model to use

# API Keys (if using cloud providers)
OPENAI_API_KEY=your-api-key
ANTHROPIC_API_KEY=your-api-key

# Ollama Settings
OLLAMA_BASE_URL=http://localhost:11434

# Memory Settings
MEMORY_HOT_CAPACITY=100
MEMORY_WARM_CAPACITY=500
MEMORY_COLD_CAPACITY=2000

# Self-Correction Settings
CORRECTION_THRESHOLD=0.4
REVIEW_THRESHOLD=0.6
ENABLE_AUTO_CORRECTION=true
```

## Usage

### API Endpoints

- `POST /api/v1/agent/chat` - Send a message to the agent
- `GET /api/v1/agent/stats` - Get agent statistics
- `GET /api/v1/memory/stats` - Get memory usage statistics
- `GET /api/v1/llm/providers` - List available LLM providers
- `POST /api/v1/llm/providers/{provider}` - Switch LLM provider

### Dashboard Features

1. **Chat Interface**: Interactive chat with the memory agent
2. **Memory Visualization**: View memory tiers and block distribution
3. **Statistics**: Real-time performance metrics and usage stats
4. **Settings**: Configure LLM providers and models

### Self-Correction Process

The agent continuously monitors conversations and:

1. Evaluates message relevance using multiple factors:
   - Semantic alignment (30%)
   - Temporal relevance (20%)
   - Goal contribution (25%)
   - Information quality (15%)
   - Factual consistency (10%)

2. Takes corrective actions:
   - **Remove**: Deletes irrelevant messages (score < 0.4)
   - **Review**: Improves problematic messages (score < 0.6)
   - **Keep**: Maintains relevant messages (score ≥ 0.6)

## Development

### Project Structure

```
autonomous-intelligent-memory-agent/
├── src/memory_agent/
│   ├── core/              # Core business logic
│   │   ├── entities/      # Domain models
│   │   ├── interfaces/    # Protocol definitions
│   │   ├── evaluation/    # Relevance evaluation
│   │   └── correction/    # Self-correction logic
│   ├── infrastructure/    # External integrations
│   │   ├── api/          # FastAPI application
│   │   ├── llm/          # LLM providers
│   │   └── storage/      # Memory storage
│   └── cli.py            # Terminal UI
├── dashboard/            # React dashboard
├── tests/               # Test suite
└── docs/                # Documentation
```

### Testing

Run tests with:
```bash
uv run pytest
```

## Troubleshooting

### Common Issues

1. **Ollama Connection Error**
   - Ensure Ollama is running: `ollama serve`
   - Check the base URL in settings

2. **Dashboard Build Error**
   - Clear node_modules: `rm -rf node_modules && npm install`
   - Check Node.js version (18+ required)

3. **Memory Issues**
   - Adjust tier capacities in settings
   - Monitor memory usage in dashboard

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details.
