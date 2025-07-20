"""WebSocket request handlers for the FastAPI application."""

import json
import uuid
from typing import Dict, List, Optional

from fastapi import WebSocket, WebSocketDisconnect, Query
from structlog import get_logger

from memory_agent.core.entities import ConversationBlock, Message
from memory_agent.core.interfaces import MessageRole, RelevanceScore, Decision

from .connection_manager import connection_manager
from .events import (
    EventType,
    create_correction_event,
    create_evaluation_event,
    create_message_event,
    MemoryEvent,
    ToolEvent,
    AgentStateEvent,
    MemoryStatsEvent,
)

logger = get_logger(__name__)


class WebSocketHandler:
    """Handles WebSocket connections for real-time updates."""
    
    def __init__(self):
        """Initialize the handler."""
        self.manager = connection_manager
    
    async def handle_connection(
        self,
        websocket: WebSocket,
        client_id: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """Handle a WebSocket connection lifecycle."""
        # Generate client ID if not provided
        if not client_id:
            client_id = str(uuid.uuid4())
        
        # Accept connection
        await self.manager.connect(
            websocket,
            client_id,
            metadata={"initial_session": session_id}
        )
        
        # Auto-subscribe to session if provided
        if session_id:
            await self.manager.subscribe_to_session(client_id, session_id)
        
        try:
            # Handle incoming messages
            while True:
                # Receive message
                data = await websocket.receive_text()
                
                try:
                    message = json.loads(data)
                    await self.manager.handle_client_message(client_id, message)
                except json.JSONDecodeError:
                    logger.warning(
                        "Invalid JSON from client",
                        client_id=client_id,
                        data=data[:100]
                    )
                except Exception as e:
                    logger.error(
                        "Error handling client message",
                        client_id=client_id,
                        error=str(e)
                    )
        
        except WebSocketDisconnect:
            logger.info("Client disconnected", client_id=client_id)
        except Exception as e:
            logger.error(
                "WebSocket error",
                client_id=client_id,
                error=str(e)
            )
        finally:
            # Clean up connection
            await self.manager.disconnect(client_id)
    
    # Event broadcasting methods
    
    async def broadcast_message_added(
        self,
        message: Message,
        session_id: str,
        sequence_number: Optional[int] = None
    ):
        """Broadcast when a message is added to the chain."""
        event = create_message_event(
            EventType.MESSAGE_ADDED,
            message_id=message.id,
            role=message.role,
            content=message.content,
            session_id=session_id,
            message_type=message.type,
            tool_name=message.tool_name,
            parent_message_id=message.parent_message_id,
            sequence_number=sequence_number,
        )
        
        await self.manager.broadcast_event(event, session_id)
    
    async def broadcast_message_removed(
        self,
        message_id: str,
        session_id: str,
        reason: Optional[str] = None
    ):
        """Broadcast when a message is removed from the chain."""
        event = create_message_event(
            EventType.MESSAGE_REMOVED,
            message_id=message_id,
            role=MessageRole.SYSTEM,
            content=f"Message removed: {reason or 'No reason provided'}",
            session_id=session_id,
        )
        
        await self.manager.broadcast_event(event, session_id)
    
    async def broadcast_evaluation_result(
        self,
        block: ConversationBlock,
        score: RelevanceScore,
        session_id: str
    ):
        """Broadcast relevance evaluation results."""
        event = create_evaluation_event(
            block_id=block.block_id,
            message_id=block.message_id,
            score=score,
            session_id=session_id
        )
        
        await self.manager.broadcast_event(event, session_id)
    
    async def broadcast_correction(
        self,
        original_message_id: str,
        reason: str,
        action: str,
        session_id: str,
        corrected_message_id: Optional[str] = None,
        affected_messages: Optional[List[str]] = None
    ):
        """Broadcast self-correction events."""
        event = create_correction_event(
            original_id=original_message_id,
            reason=reason,
            action=action,
            session_id=session_id,
            corrected_message_id=corrected_message_id,
            affected_messages=affected_messages or []
        )
        
        await self.manager.broadcast_event(event, session_id)
    
    async def broadcast_memory_event(
        self,
        block: ConversationBlock,
        action: str,
        session_id: str,
        **kwargs
    ):
        """Broadcast memory management events."""
        event = MemoryEvent(
            event_type=EventType.MEMORY_TIER_CHANGED,
            block_id=block.block_id,
            action=action,
            session_id=session_id,
            from_tier=kwargs.get("from_tier"),
            to_tier=kwargs.get("to_tier", block.memory_tier),
            retention_score=block.calculate_retention_score(),
            **kwargs
        )
        
        await self.manager.broadcast_event(event, session_id)
    
    async def broadcast_tool_event(
        self,
        tool_name: str,
        tool_id: str,
        status: str,
        session_id: str,
        **kwargs
    ):
        """Broadcast tool execution events."""
        event_type_map = {
            "started": EventType.TOOL_CALLED,
            "completed": EventType.TOOL_COMPLETED,
            "failed": EventType.TOOL_FAILED,
        }
        
        event = ToolEvent(
            event_type=event_type_map.get(status, EventType.TOOL_CALLED),
            tool_name=tool_name,
            tool_id=tool_id,
            status=status,
            session_id=session_id,
            **kwargs
        )
        
        await self.manager.broadcast_event(event, session_id)
    
    async def broadcast_agent_state(
        self,
        state: str,
        session_id: str,
        progress: Optional[float] = None,
        current_action: Optional[str] = None
    ):
        """Broadcast agent state updates."""
        event_type_map = {
            "thinking": EventType.AGENT_THINKING,
            "responding": EventType.AGENT_RESPONDING,
            "error": EventType.AGENT_ERROR,
        }
        
        event = AgentStateEvent(
            event_type=event_type_map.get(state, EventType.AGENT_THINKING),
            state=state,
            session_id=session_id,
            progress=progress,
            current_action=current_action
        )
        
        await self.manager.broadcast_event(event, session_id)
    
    async def broadcast_memory_stats(
        self,
        stats: Dict,
        session_id: Optional[str] = None
    ):
        """Broadcast memory statistics update."""
        event = MemoryStatsEvent(
            total_blocks=stats.get("total_blocks", 0),
            tier_stats=stats.get("tier_stats", {}),
            total_size_bytes=stats.get("total_size_bytes", 0),
            active_sessions=stats.get("active_sessions", 0),
            compression_ratio=stats.get("compression_ratio", 1.0),
            avg_relevance_score=stats.get("avg_relevance_score", 0.0),
            total_corrections=stats.get("total_corrections", 0),
            cache_hit_rate=stats.get("cache_hit_rate", 0.0),
            session_id=session_id
        )
        
        await self.manager.broadcast_event(event, session_id)


# Global WebSocket handler instance
websocket_handler = WebSocketHandler()