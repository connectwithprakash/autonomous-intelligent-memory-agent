"""WebSocket connection manager for handling multiple client connections."""

import asyncio
import json
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Set

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from structlog import get_logger

from .events import BaseEvent, EventBatch, EventType

logger = get_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and event broadcasting."""
    
    def __init__(self):
        """Initialize the connection manager."""
        # Active connections by client ID
        self._connections: Dict[str, WebSocket] = {}
        
        # Session subscriptions (session_id -> set of client_ids)
        self._session_subscriptions: Dict[str, Set[str]] = defaultdict(set)
        
        # Client metadata
        self._client_metadata: Dict[str, Dict] = {}
        
        # Event history buffer (for replay)
        self._event_buffer: List[BaseEvent] = []
        self._buffer_size = 1000
        
        # Statistics
        self._stats = {
            "total_connections": 0,
            "total_events_sent": 0,
            "total_events_received": 0,
            "connection_errors": 0,
        }
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
    
    async def connect(
        self,
        websocket: WebSocket,
        client_id: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        
        async with self._lock:
            self._connections[client_id] = websocket
            self._client_metadata[client_id] = metadata or {}
            self._client_metadata[client_id]["connected_at"] = datetime.utcnow()
            self._stats["total_connections"] += 1
        
        logger.info(
            "WebSocket connection established",
            client_id=client_id,
            metadata=metadata
        )
        
        # Send connection established event
        await self.send_personal_event(
            client_id,
            BaseEvent(
                event_type=EventType.CONNECTION_ESTABLISHED,
                metadata={"client_id": client_id}
            )
        )
    
    async def disconnect(self, client_id: str) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            if client_id in self._connections:
                # Remove from all session subscriptions
                for session_id in list(self._session_subscriptions.keys()):
                    self._session_subscriptions[session_id].discard(client_id)
                    if not self._session_subscriptions[session_id]:
                        del self._session_subscriptions[session_id]
                
                # Close and remove connection
                websocket = self._connections[client_id]
                del self._connections[client_id]
                del self._client_metadata[client_id]
                
                try:
                    await websocket.close()
                except Exception as e:
                    logger.warning(
                        "Error closing WebSocket",
                        client_id=client_id,
                        error=str(e)
                    )
        
        logger.info("WebSocket connection closed", client_id=client_id)
    
    async def subscribe_to_session(
        self,
        client_id: str,
        session_id: str
    ) -> bool:
        """Subscribe a client to session events."""
        async with self._lock:
            if client_id not in self._connections:
                return False
            
            self._session_subscriptions[session_id].add(client_id)
            
            # Update client metadata
            if "sessions" not in self._client_metadata[client_id]:
                self._client_metadata[client_id]["sessions"] = set()
            self._client_metadata[client_id]["sessions"].add(session_id)
        
        logger.info(
            "Client subscribed to session",
            client_id=client_id,
            session_id=session_id
        )
        return True
    
    async def unsubscribe_from_session(
        self,
        client_id: str,
        session_id: str
    ) -> bool:
        """Unsubscribe a client from session events."""
        async with self._lock:
            if session_id in self._session_subscriptions:
                self._session_subscriptions[session_id].discard(client_id)
                if not self._session_subscriptions[session_id]:
                    del self._session_subscriptions[session_id]
            
            # Update client metadata
            if (client_id in self._client_metadata and 
                "sessions" in self._client_metadata[client_id]):
                self._client_metadata[client_id]["sessions"].discard(session_id)
        
        logger.info(
            "Client unsubscribed from session",
            client_id=client_id,
            session_id=session_id
        )
        return True
    
    async def send_personal_event(
        self,
        client_id: str,
        event: BaseEvent
    ) -> bool:
        """Send an event to a specific client."""
        if client_id not in self._connections:
            return False
        
        websocket = self._connections[client_id]
        try:
            await websocket.send_json(event.model_dump(mode="json"))
            self._stats["total_events_sent"] += 1
            return True
        except Exception as e:
            logger.error(
                "Failed to send event to client",
                client_id=client_id,
                event_type=event.event_type,
                error=str(e)
            )
            self._stats["connection_errors"] += 1
            # Disconnect client on send error
            await self.disconnect(client_id)
            return False
    
    async def broadcast_event(
        self,
        event: BaseEvent,
        session_id: Optional[str] = None
    ) -> int:
        """Broadcast an event to all relevant clients."""
        # Add to event buffer
        async with self._lock:
            self._event_buffer.append(event)
            if len(self._event_buffer) > self._buffer_size:
                self._event_buffer.pop(0)
        
        # Determine target clients
        if session_id and session_id in self._session_subscriptions:
            client_ids = list(self._session_subscriptions[session_id])
        else:
            client_ids = list(self._connections.keys())
        
        # Send to all target clients
        send_count = 0
        for client_id in client_ids:
            if await self.send_personal_event(client_id, event):
                send_count += 1
        
        logger.debug(
            "Event broadcast",
            event_type=event.event_type,
            session_id=session_id,
            recipients=send_count
        )
        
        return send_count
    
    async def broadcast_batch(
        self,
        events: List[BaseEvent],
        session_id: Optional[str] = None
    ) -> int:
        """Broadcast a batch of events efficiently."""
        if not events:
            return 0
        
        batch = EventBatch(events=events)
        
        # Determine target clients
        if session_id and session_id in self._session_subscriptions:
            client_ids = list(self._session_subscriptions[session_id])
        else:
            client_ids = list(self._connections.keys())
        
        # Send batch to all target clients
        send_count = 0
        for client_id in client_ids:
            websocket = self._connections.get(client_id)
            if websocket:
                try:
                    await websocket.send_json(batch.model_dump(mode="json"))
                    send_count += 1
                    self._stats["total_events_sent"] += len(events)
                except Exception as e:
                    logger.error(
                        "Failed to send batch to client",
                        client_id=client_id,
                        batch_size=len(events),
                        error=str(e)
                    )
                    await self.disconnect(client_id)
        
        return send_count
    
    async def handle_client_message(
        self,
        client_id: str,
        message: Dict
    ) -> None:
        """Handle incoming message from a client."""
        self._stats["total_events_received"] += 1
        
        # Handle different message types
        message_type = message.get("type")
        
        if message_type == "subscribe":
            session_id = message.get("session_id")
            if session_id:
                await self.subscribe_to_session(client_id, session_id)
        
        elif message_type == "unsubscribe":
            session_id = message.get("session_id")
            if session_id:
                await self.unsubscribe_from_session(client_id, session_id)
        
        elif message_type == "ping":
            # Respond with pong
            await self.send_personal_event(
                client_id,
                BaseEvent(
                    event_type=EventType.CONNECTION_ESTABLISHED,
                    metadata={"type": "pong", "timestamp": datetime.utcnow()}
                )
            )
        
        elif message_type == "replay":
            # Send recent events from buffer
            count = min(message.get("count", 50), len(self._event_buffer))
            if count > 0:
                recent_events = self._event_buffer[-count:]
                await self.broadcast_batch(recent_events)
        
        else:
            logger.warning(
                "Unknown message type from client",
                client_id=client_id,
                message_type=message_type
            )
    
    def get_connection_stats(self) -> Dict:
        """Get connection statistics."""
        return {
            "active_connections": len(self._connections),
            "active_sessions": len(self._session_subscriptions),
            "buffered_events": len(self._event_buffer),
            **self._stats
        }
    
    def get_client_info(self, client_id: str) -> Optional[Dict]:
        """Get information about a specific client."""
        if client_id not in self._connections:
            return None
        
        metadata = self._client_metadata.get(client_id, {}).copy()
        metadata["is_connected"] = True
        metadata["subscribed_sessions"] = list(
            metadata.get("sessions", set())
        )
        
        return metadata
    
    async def close_all_connections(self) -> None:
        """Close all active connections."""
        client_ids = list(self._connections.keys())
        
        for client_id in client_ids:
            await self.disconnect(client_id)
        
        logger.info("All WebSocket connections closed")


# Global connection manager instance
connection_manager = ConnectionManager()