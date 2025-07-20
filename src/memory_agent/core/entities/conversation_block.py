"""ConversationBlock entity implementation."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..interfaces.evaluator import Decision, RelevanceScore
from ..interfaces.storage import StorageTier


class ProcessingStatus(str, Enum):
    """Status of block processing."""

    PENDING = "pending"
    EVALUATED = "evaluated"
    RETAINED = "retained"
    DISCARDED = "discarded"
    COMPRESSED = "compressed"
    ARCHIVED = "archived"


class ConversationBlock(BaseModel):
    """A unit of conversation with metadata for memory management."""

    # Core Identity
    block_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sequence_number: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_id: str
    
    # Content & Source
    content: str
    content_type: str = "text"  # text, json, html, markdown
    source: str  # agent, tool, user, system
    message_id: str  # Reference to the original message
    
    # Tool-specific fields
    tool_name: Optional[str] = None
    tool_parameters: Optional[Dict[str, Any]] = None
    tool_result: Optional[Dict[str, Any]] = None
    
    # Relevance & Quality
    relevance_score: Optional[float] = None
    confidence_score: Optional[float] = None
    quality_metrics: Dict[str, float] = Field(default_factory=dict)
    relevance_tags: List[str] = Field(default_factory=list)
    evaluation_result: Optional[RelevanceScore] = None
    
    # Memory Management
    memory_tier: StorageTier = StorageTier.HOT
    access_count: int = 0
    last_accessed: datetime = Field(default_factory=datetime.utcnow)
    retention_priority: float = 1.0
    compressed_size: Optional[int] = None
    
    # Relationships & Context
    parent_blocks: List[str] = Field(default_factory=list)
    child_blocks: List[str] = Field(default_factory=list)
    conversation_thread: Optional[str] = None
    context_window: List[str] = Field(default_factory=list)
    
    # Processing Status
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    evaluation_reason: Optional[str] = None
    correction_history: List[Dict[str, Any]] = Field(default_factory=list)
    
    class Config:
        """Pydantic configuration."""
        
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

    def update_access(self) -> None:
        """Update access count and timestamp."""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()

    def add_correction(self, reason: str, action: str) -> None:
        """Add a correction to history."""
        self.correction_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "reason": reason,
            "action": action,
        })

    def calculate_retention_score(self) -> float:
        """Calculate dynamic retention score based on multiple factors."""
        base_score = self.relevance_score or 0.5
        
        # Boost for recent access
        time_since_access = (datetime.utcnow() - self.last_accessed).total_seconds()
        recency_boost = max(0, 1 - (time_since_access / 86400))  # Decay over 24h
        
        # Boost for frequent access
        access_boost = min(1, self.access_count / 10)
        
        # Combine factors
        retention_score = (
            base_score * 0.6 +
            recency_boost * 0.2 +
            access_boost * 0.2
        )
        
        return min(1.0, retention_score * self.retention_priority)

    def should_compress(self, age_threshold_hours: int = 6) -> bool:
        """Check if block should be compressed."""
        if self.memory_tier != StorageTier.HOT:
            return False
            
        age_hours = (datetime.utcnow() - self.timestamp).total_seconds() / 3600
        return (
            age_hours > age_threshold_hours and
            self.access_count < 3 and
            self.calculate_retention_score() < 0.8
        )

    def should_archive(self, age_threshold_hours: int = 24) -> bool:
        """Check if block should be archived."""
        if self.memory_tier == StorageTier.COLD:
            return False
            
        age_hours = (datetime.utcnow() - self.timestamp).total_seconds() / 3600
        return (
            age_hours > age_threshold_hours and
            self.access_count == 0 and
            self.calculate_retention_score() < 0.5
        )

    def to_summary(self) -> str:
        """Generate a summary of the block."""
        summary_parts = [
            f"Block {self.block_id[:8]}",
            f"Seq: {self.sequence_number}",
            f"Source: {self.source}",
            f"Score: {self.relevance_score:.2f}" if self.relevance_score else "Unscored",
            f"Tier: {self.memory_tier.value}",
        ]
        return " | ".join(summary_parts)

    def __str__(self) -> str:
        """String representation."""
        return f"[{self.source.upper()}] {self.content[:50]}... (Score: {self.relevance_score})"

    def __repr__(self) -> str:
        """Developer representation."""
        return (
            f"ConversationBlock(id={self.block_id[:8]}, "
            f"seq={self.sequence_number}, "
            f"tier={self.memory_tier.value})"
        )