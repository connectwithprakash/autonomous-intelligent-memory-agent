"""WebSocket event types and payloads for real-time updates."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from memory_agent.core.interfaces import (
    Decision,
    MessageRole,
    MessageType,
    RelevanceScore,
    StorageTier,
)


class EventType(str, Enum):
    """Types of WebSocket events."""
    
    # Connection events
    CONNECTION_ESTABLISHED = "connection.established"
    CONNECTION_CLOSED = "connection.closed"
    
    # Message events
    MESSAGE_ADDED = "message.added"
    MESSAGE_REMOVED = "message.removed"
    MESSAGE_UPDATED = "message.updated"
    
    # Evaluation events
    RELEVANCE_EVALUATED = "relevance.evaluated"
    CORRECTION_TRIGGERED = "correction.triggered"
    CORRECTION_COMPLETED = "correction.completed"
    
    # Memory events
    MEMORY_TIER_CHANGED = "memory.tier_changed"
    MEMORY_STATS_UPDATED = "memory.stats_updated"
    BLOCK_COMPRESSED = "block.compressed"
    BLOCK_ARCHIVED = "block.archived"
    
    # Tool events
    TOOL_CALLED = "tool.called"
    TOOL_COMPLETED = "tool.completed"
    TOOL_FAILED = "tool.failed"
    
    # Agent events
    AGENT_THINKING = "agent.thinking"
    AGENT_RESPONDING = "agent.responding"
    AGENT_ERROR = "agent.error"


class BaseEvent(BaseModel):
    """Base class for all WebSocket events."""
    
    event_id: str = Field(default_factory=lambda: str(datetime.utcnow().timestamp()))
    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MessageEvent(BaseEvent):
    """Event for message-related updates."""
    
    message_id: str
    role: MessageRole
    content: str
    message_type: MessageType
    sequence_number: Optional[int] = None
    tool_name: Optional[str] = None
    parent_message_id: Optional[str] = None


class EvaluationEvent(BaseEvent):
    """Event for relevance evaluation updates."""
    
    block_id: str
    message_id: str
    relevance_score: float
    decision: Decision
    confidence: float
    reasoning: str
    dimensions: Dict[str, float] = Field(
        description="Individual dimension scores"
    )


class CorrectionEvent(BaseEvent):
    """Event for self-correction updates."""
    
    original_message_id: str
    corrected_message_id: Optional[str] = None
    reason: str
    action: str  # "remove", "replace", "rollback"
    affected_messages: List[str] = Field(default_factory=list)


class MemoryEvent(BaseEvent):
    """Event for memory management updates."""
    
    block_id: str
    action: str  # "tier_change", "compress", "archive", "delete"
    from_tier: Optional[StorageTier] = None
    to_tier: Optional[StorageTier] = None
    size_before: Optional[int] = None
    size_after: Optional[int] = None
    retention_score: Optional[float] = None


class ToolEvent(BaseEvent):
    """Event for tool execution updates."""
    
    tool_name: str
    tool_id: str
    status: str  # "started", "completed", "failed"
    parameters: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None


class MemoryStatsEvent(BaseEvent):
    """Event for memory statistics updates."""
    
    event_type: EventType = EventType.MEMORY_STATS_UPDATED
    
    total_blocks: int
    tier_stats: Dict[str, Dict[str, Any]] = Field(
        description="Statistics per storage tier"
    )
    total_size_bytes: int
    active_sessions: int
    compression_ratio: float
    
    # Performance metrics
    avg_relevance_score: float
    total_corrections: int
    cache_hit_rate: float


class AgentStateEvent(BaseEvent):
    """Event for agent state updates."""
    
    state: str  # "idle", "thinking", "calling_tool", "evaluating", "responding"
    progress: Optional[float] = None  # 0.0 to 1.0
    current_action: Optional[str] = None
    estimated_time_remaining_ms: Optional[float] = None


class ErrorEvent(BaseEvent):
    """Event for error notifications."""
    
    event_type: EventType = EventType.AGENT_ERROR
    error_code: str
    error_message: str
    error_details: Optional[Dict[str, Any]] = None
    recoverable: bool = True


class EventBatch(BaseModel):
    """Batch of events for efficient transmission."""
    
    batch_id: str = Field(default_factory=lambda: str(datetime.utcnow().timestamp()))
    events: List[BaseEvent]
    batch_size: int = Field(default=0)
    
    def __init__(self, **data):
        """Initialize and set batch size."""
        super().__init__(**data)
        self.batch_size = len(self.events)


# Helper functions for creating events

def create_message_event(
    event_type: EventType,
    message_id: str,
    role: MessageRole,
    content: str,
    session_id: str,
    **kwargs
) -> MessageEvent:
    """Create a message event."""
    # Extract message_type from kwargs to avoid duplicate
    message_type = kwargs.pop("message_type", MessageType.TEXT)
    
    return MessageEvent(
        event_type=event_type,
        message_id=message_id,
        role=role,
        content=content,
        session_id=session_id,
        message_type=message_type,
        **kwargs
    )


def create_evaluation_event(
    block_id: str,
    message_id: str,
    score: RelevanceScore,
    session_id: str
) -> EvaluationEvent:
    """Create an evaluation event from a relevance score."""
    return EvaluationEvent(
        event_type=EventType.RELEVANCE_EVALUATED,
        block_id=block_id,
        message_id=message_id,
        relevance_score=score.overall_score,
        decision=score.decision,
        confidence=score.confidence,
        reasoning=score.reasoning,
        session_id=session_id,
        dimensions={
            "semantic_alignment": score.semantic_alignment,
            "temporal_relevance": score.temporal_relevance,
            "goal_contribution": score.goal_contribution,
            "information_quality": score.information_quality,
            "factual_consistency": score.factual_consistency,
        }
    )


def create_correction_event(
    original_id: str,
    reason: str,
    action: str,
    session_id: str,
    **kwargs
) -> CorrectionEvent:
    """Create a correction event."""
    return CorrectionEvent(
        event_type=EventType.CORRECTION_TRIGGERED,
        original_message_id=original_id,
        reason=reason,
        action=action,
        session_id=session_id,
        **kwargs
    )