"""Core interfaces for the memory agent."""

from .agent import (
    AgentConfig,
    AgentResponse,
    IAgentOrchestrator,
    IMemoryAgent,
)
from .evaluator import (
    Decision,
    EvaluationContext,
    EvaluationDimension,
    IRelevanceEvaluator,
    ISelfEvaluator,
    RelevanceFactors,
    RelevanceScore,
)
from .llm import (
    CompletionOptions,
    CompletionResponse,
    ILLMProvider,
    LLMProvider,
    LLMProviderType,
    ModelInfo,
    StreamChunk,
    TokenUsage,
)
from .message import (
    IMessage,
    IMessageChain,
    MessageRole,
    MessageType,
)
from .storage import (
    IStorage,
    IStorageManager,
    QueryFilter,
    StorageTier,
)
from .tool import (
    IMCPClient,
    ITool,
    IToolRegistry,
    ToolParameter,
    ToolResult,
    ToolSpec,
    ToolType,
)

__all__ = [
    # Agent
    "AgentConfig",
    "AgentResponse",
    "IAgentOrchestrator",
    "IMemoryAgent",
    # Evaluator
    "Decision",
    "EvaluationContext",
    "EvaluationDimension",
    "IRelevanceEvaluator",
    "ISelfEvaluator",
    "RelevanceFactors",
    "RelevanceScore",
    # LLM
    "CompletionOptions",
    "CompletionResponse",
    "ILLMProvider",
    "LLMProvider",
    "LLMProviderType",
    "ModelInfo",
    "StreamChunk",
    "TokenUsage",
    # Message
    "IMessage",
    "IMessageChain",
    "MessageRole",
    "MessageType",
    # Storage
    "IStorage",
    "IStorageManager",
    "QueryFilter",
    "StorageTier",
    # Tool
    "IMCPClient",
    "ITool",
    "IToolRegistry",
    "ToolParameter",
    "ToolResult",
    "ToolSpec",
    "ToolType",
]