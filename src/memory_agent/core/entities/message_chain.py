"""MessageChain entity implementation."""

import asyncio
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from ..interfaces.message import IMessage, IMessageChain
from .message import Message


class MessageChain(BaseModel):
    """Implementation of message chain management."""

    chains: Dict[str, List[Message]] = Field(default_factory=lambda: defaultdict(list))
    message_index: Dict[str, Message] = Field(default_factory=dict)
    
    class Config:
        """Pydantic configuration."""
        
        arbitrary_types_allowed = True
    
    def __init__(self, **data):
        """Initialize with a lock."""
        super().__init__(**data)
        self._lock = asyncio.Lock()

    async def add_message(self, message: IMessage, session_id: str) -> str:
        """Add a message to the chain."""
        async with self._lock:
            # Convert to Message if needed
            if not isinstance(message, Message):
                msg = Message(
                    id=message.id,
                    role=message.role,
                    content=message.content,
                    timestamp=message.timestamp,
                    metadata=message.metadata,
                )
            else:
                msg = message
            
            # Add to chain and index
            self.chains[session_id].append(msg)
            self.message_index[msg.id] = msg
            
            return msg.id

    async def remove_message(self, message_id: str) -> bool:
        """Remove a message from the chain."""
        async with self._lock:
            if message_id not in self.message_index:
                return False
            
            message = self.message_index[message_id]
            
            # Find and remove from appropriate chain
            for session_id, chain in self.chains.items():
                if message in chain:
                    chain.remove(message)
                    break
            
            # Remove from index
            del self.message_index[message_id]
            return True

    async def get_messages(self, session_id: str) -> List[IMessage]:
        """Get all messages in the chain for a session."""
        async with self._lock:
            return self.chains.get(session_id, []).copy()

    async def rollback_to(self, message_id: str, session_id: str) -> bool:
        """Rollback the chain to a specific message."""
        async with self._lock:
            if message_id not in self.message_index:
                return False
            
            target_message = self.message_index[message_id]
            chain = self.chains.get(session_id, [])
            
            if target_message not in chain:
                return False
            
            # Find index of target message
            target_index = chain.index(target_message)
            
            # Remove all messages after target
            removed_messages = chain[target_index + 1:]
            self.chains[session_id] = chain[:target_index + 1]
            
            # Remove from index
            for msg in removed_messages:
                if msg.id in self.message_index:
                    del self.message_index[msg.id]
            
            return True

    async def validate_chain(self, session_id: str) -> bool:
        """Validate the integrity of the message chain."""
        async with self._lock:
            chain = self.chains.get(session_id, [])
            
            if not chain:
                return True
            
            # Check for basic integrity
            prev_timestamp = None
            for i, msg in enumerate(chain):
                # Messages should be in chronological order
                if prev_timestamp and msg.timestamp < prev_timestamp:
                    return False
                prev_timestamp = msg.timestamp
                
                # Message should be in index
                if msg.id not in self.message_index:
                    return False
                
                # First message should be from user or system
                if i == 0 and msg.role.value not in ["user", "system"]:
                    return False
            
            return True

    async def get_context_window(
        self, max_tokens: int, session_id: str, token_counter=None
    ) -> List[IMessage]:
        """Get messages that fit within a token limit."""
        async with self._lock:
            chain = self.chains.get(session_id, [])
            if not chain:
                return []
            
            # Simple implementation - take most recent messages
            # In production, use actual token counting
            if token_counter:
                result = []
                total_tokens = 0
                
                # Work backwards from most recent
                for msg in reversed(chain):
                    msg_tokens = await token_counter(msg.content)
                    if total_tokens + msg_tokens > max_tokens:
                        break
                    result.insert(0, msg)
                    total_tokens += msg_tokens
                
                return result
            else:
                # Fallback: estimate ~4 chars per token
                char_limit = max_tokens * 4
                result = []
                total_chars = 0
                
                for msg in reversed(chain):
                    msg_chars = len(msg.content)
                    if total_chars + msg_chars > char_limit:
                        break
                    result.insert(0, msg)
                    total_chars += msg_chars
                
                return result

    async def insert_message_after(
        self, message_id: str, new_message: IMessage, session_id: str
    ) -> bool:
        """Insert a message after a specific message in the chain."""
        async with self._lock:
            if message_id not in self.message_index:
                return False
            
            chain = self.chains.get(session_id, [])
            target_message = self.message_index[message_id]
            
            if target_message not in chain:
                return False
            
            # Convert to Message if needed
            if not isinstance(new_message, Message):
                msg = Message(
                    id=new_message.id,
                    role=new_message.role,
                    content=new_message.content,
                    timestamp=new_message.timestamp,
                    metadata=new_message.metadata,
                )
            else:
                msg = new_message
            
            # Insert after target
            target_index = chain.index(target_message)
            chain.insert(target_index + 1, msg)
            self.message_index[msg.id] = msg
            
            return True

    async def replace_message(
        self, message_id: str, new_message: IMessage, session_id: str
    ) -> bool:
        """Replace a message in the chain."""
        async with self._lock:
            if message_id not in self.message_index:
                return False
            
            chain = self.chains.get(session_id, [])
            old_message = self.message_index[message_id]
            
            if old_message not in chain:
                return False
            
            # Convert to Message if needed
            if not isinstance(new_message, Message):
                msg = Message(
                    id=new_message.id,
                    role=new_message.role,
                    content=new_message.content,
                    timestamp=new_message.timestamp,
                    metadata=new_message.metadata,
                )
            else:
                msg = new_message
            
            # Replace in chain
            index = chain.index(old_message)
            chain[index] = msg
            
            # Update index
            del self.message_index[message_id]
            self.message_index[msg.id] = msg
            
            return True

    def get_chain_summary(self, session_id: str) -> Dict:
        """Get summary statistics for a chain."""
        chain = self.chains.get(session_id, [])
        
        if not chain:
            return {"total_messages": 0}
        
        role_counts = defaultdict(int)
        for msg in chain:
            role_counts[msg.role.value] += 1
        
        return {
            "total_messages": len(chain),
            "role_counts": dict(role_counts),
            "first_message": chain[0].timestamp.isoformat(),
            "last_message": chain[-1].timestamp.isoformat(),
            "duration_seconds": (chain[-1].timestamp - chain[0].timestamp).total_seconds(),
        }