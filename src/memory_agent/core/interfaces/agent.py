"""Main agent interface definitions."""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional, Protocol, runtime_checkable

from pydantic import BaseModel

from .evaluator import EvaluationContext, RelevanceScore
from .llm import CompletionOptions, ILLMProvider
from .message import IMessage, IMessageChain
from .storage import IStorageManager
from .tool import IToolRegistry


class AgentConfig(BaseModel):
    """Configuration for the agent."""

    relevance_threshold: float = 0.7
    max_corrections_per_turn: int = 3
    enable_streaming: bool = True
    max_context_tokens: int = 4096
    auto_compress_after_messages: int = 100
    debug_mode: bool = False


class AgentResponse(BaseModel):
    """Response from the agent."""

    content: str
    corrections_made: int = 0
    tokens_used: int = 0
    execution_time_ms: float
    metadata: Dict[str, Any] = {}


@runtime_checkable
class IMemoryAgent(Protocol):
    """Protocol for the main memory agent."""

    async def initialize(self) -> bool:
        """Initialize the agent and its components.
        
        Returns:
            True if successful
        """
        ...

    async def process_message(
        self,
        user_message: str,
        session_id: str,
        options: Optional[CompletionOptions] = None,
    ) -> AgentResponse:
        """Process a user message and generate response.
        
        Args:
            user_message: User's input message
            session_id: Session identifier
            options: Completion options
            
        Returns:
            Agent's response
        """
        ...

    async def stream_response(
        self,
        user_message: str,
        session_id: str,
        options: Optional[CompletionOptions] = None,
    ) -> AsyncIterator[str]:
        """Stream response for a user message.
        
        Args:
            user_message: User's input message
            session_id: Session identifier
            options: Completion options
            
        Yields:
            Response chunks
        """
        ...

    async def get_conversation_history(
        self, session_id: str, limit: Optional[int] = None
    ) -> List[IMessage]:
        """Get conversation history for a session.
        
        Args:
            session_id: Session identifier
            limit: Maximum messages to return
            
        Returns:
            List of messages
        """
        ...

    async def clear_session(self, session_id: str) -> bool:
        """Clear all data for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if successful
        """
        ...

    async def get_memory_stats(self) -> Dict:
        """Get memory usage statistics.
        
        Returns:
            Memory statistics
        """
        ...


@runtime_checkable
class IAgentOrchestrator(Protocol):
    """Protocol for orchestrating agent components."""

    @property
    def llm_provider(self) -> ILLMProvider:
        """LLM provider instance."""
        ...

    @property
    def message_chain(self) -> IMessageChain:
        """Message chain manager."""
        ...

    @property
    def storage_manager(self) -> IStorageManager:
        """Storage manager."""
        ...

    @property
    def tool_registry(self) -> IToolRegistry:
        """Tool registry."""
        ...

    async def run_self_correction_loop(
        self,
        message_chain: List[IMessage],
        context: EvaluationContext,
    ) -> List[IMessage]:
        """Run the self-correction loop.
        
        Args:
            message_chain: Current message chain
            context: Evaluation context
            
        Returns:
            Corrected message chain
        """
        ...

    async def evaluate_and_store(
        self,
        message: IMessage,
        context: EvaluationContext,
    ) -> RelevanceScore:
        """Evaluate a message and store based on relevance.
        
        Args:
            message: Message to evaluate
            context: Evaluation context
            
        Returns:
            Relevance score
        """
        ...