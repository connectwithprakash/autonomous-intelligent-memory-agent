"""WebSocket infrastructure for real-time updates."""

from .connection_manager import ConnectionManager, connection_manager
from .events import (
    BaseEvent,
    EventBatch,
    EventType,
    MessageEvent,
    EvaluationEvent,
    CorrectionEvent,
    MemoryEvent,
    ToolEvent,
    AgentStateEvent,
    MemoryStatsEvent,
    ErrorEvent,
    create_message_event,
    create_evaluation_event,
    create_correction_event,
)
from .handlers import WebSocketHandler, websocket_handler

__all__ = [
    # Manager
    "ConnectionManager",
    "connection_manager",
    # Events
    "BaseEvent",
    "EventBatch",
    "EventType",
    "MessageEvent",
    "EvaluationEvent",
    "CorrectionEvent",
    "MemoryEvent",
    "ToolEvent",
    "AgentStateEvent",
    "MemoryStatsEvent",
    "ErrorEvent",
    "create_message_event",
    "create_evaluation_event",
    "create_correction_event",
    # Handler
    "WebSocketHandler",
    "websocket_handler",
]