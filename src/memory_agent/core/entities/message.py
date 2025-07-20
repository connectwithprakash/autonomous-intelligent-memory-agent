"""Message entity implementation."""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from ..interfaces.message import IMessage, MessageRole, MessageType


class Message(BaseModel):
    """Concrete implementation of a message in the conversation chain."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: MessageRole
    content: str
    type: MessageType = MessageType.TEXT
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Optional fields for tool interactions
    tool_name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_parameters: Optional[Dict[str, Any]] = None
    
    # For tracking corrections
    parent_message_id: Optional[str] = None
    correction_reason: Optional[str] = None
    
    class Config:
        """Pydantic configuration."""
        
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary format."""
        data = self.model_dump()
        # Ensure datetime is serialized
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create message from dictionary."""
        # Parse datetime if it's a string
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)

    def to_llm_format(self) -> Dict[str, str]:
        """Convert to format expected by LLM APIs."""
        base = {
            "role": self.role.value,
            "content": self.content,
        }
        
        # Add tool-specific fields if present
        if self.tool_name and self.role == MessageRole.ASSISTANT:
            base["tool_calls"] = [{
                "id": self.tool_call_id or self.id,
                "type": "function",
                "function": {
                    "name": self.tool_name,
                    "arguments": self.tool_parameters or {}
                }
            }]
        elif self.role == MessageRole.TOOL:
            base["tool_call_id"] = self.tool_call_id
            base["name"] = self.tool_name
            
        return base

    def is_correction(self) -> bool:
        """Check if this message is a correction."""
        return self.type == MessageType.CORRECTION or self.parent_message_id is not None

    def __str__(self) -> str:
        """String representation."""
        return f"[{self.role.value.upper()}] {self.content[:50]}..."

    def __repr__(self) -> str:
        """Developer representation."""
        return f"Message(id={self.id}, role={self.role}, type={self.type})"