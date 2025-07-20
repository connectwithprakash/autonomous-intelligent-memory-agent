"""Evaluator interface definitions for relevance assessment."""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from pydantic import BaseModel


class EvaluationDimension(str, Enum):
    """Dimensions for relevance evaluation."""

    SEMANTIC_ALIGNMENT = "semantic_alignment"
    TEMPORAL_RELEVANCE = "temporal_relevance"
    GOAL_CONTRIBUTION = "goal_contribution"
    INFORMATION_QUALITY = "information_quality"
    FACTUAL_CONSISTENCY = "factual_consistency"


class Decision(str, Enum):
    """Decisions based on evaluation."""

    RETAIN = "retain"  # Keep in active memory
    DISCARD = "discard"  # Remove from chain
    REEVALUATE = "reevaluate"  # Check again later
    COMPRESS = "compress"  # Move to compressed storage


class EvaluationContext(BaseModel):
    """Context for relevance evaluation."""

    user_query: str
    conversation_history: List[str] = []
    current_goal: Optional[str] = None
    session_id: str
    timestamp: datetime
    metadata: Dict[str, Any] = {}


class RelevanceFactors(BaseModel):
    """Individual relevance factors."""
    
    semantic_alignment: float
    temporal_relevance: float
    goal_contribution: float
    information_quality: float
    factual_consistency: float


class RelevanceScore(BaseModel):
    """Multi-dimensional relevance score."""

    # Overall score and factors
    overall_score: float
    factors: RelevanceFactors
    
    # Decision and reasoning
    decision: Decision
    explanation: str
    
    # Optional metadata
    confidence: Optional[float] = None
    evaluated_at: Optional[datetime] = None
    evaluator_version: str = "1.0"


@runtime_checkable
class IRelevanceEvaluator(Protocol):
    """Protocol for relevance evaluation."""

    async def evaluate(
        self,
        block_content: str,
        context: EvaluationContext,
    ) -> RelevanceScore:
        """Evaluate relevance of a conversation block.
        
        Args:
            block_content: Content to evaluate
            context: Evaluation context
            
        Returns:
            Relevance score with decision
        """
        ...

    async def batch_evaluate(
        self,
        blocks: List[str],
        context: EvaluationContext,
    ) -> List[RelevanceScore]:
        """Evaluate multiple blocks in batch.
        
        Args:
            blocks: List of block contents
            context: Evaluation context
            
        Returns:
            List of relevance scores
        """
        ...

    async def get_weights(self) -> Dict[EvaluationDimension, float]:
        """Get current dimension weights.
        
        Returns:
            Weight for each dimension
        """
        ...

    async def update_weights(
        self, weights: Dict[EvaluationDimension, float]
    ) -> bool:
        """Update dimension weights.
        
        Args:
            weights: New weights
            
        Returns:
            True if successful
        """
        ...


@runtime_checkable
class ISelfEvaluator(Protocol):
    """Protocol for self-evaluation and correction."""

    async def should_correct(
        self,
        message_chain: List[Dict],
        evaluation_scores: List[RelevanceScore],
    ) -> bool:
        """Determine if correction is needed.
        
        Args:
            message_chain: Current message chain
            evaluation_scores: Scores for each message
            
        Returns:
            True if correction needed
        """
        ...

    async def generate_correction_plan(
        self,
        message_chain: List[Dict],
        evaluation_scores: List[RelevanceScore],
    ) -> List[Dict]:
        """Generate a plan for correcting the chain.
        
        Args:
            message_chain: Current message chain
            evaluation_scores: Scores for each message
            
        Returns:
            List of correction actions
        """
        ...

    async def apply_corrections(
        self,
        message_chain: List[Dict],
        correction_plan: List[Dict],
    ) -> List[Dict]:
        """Apply corrections to the message chain.
        
        Args:
            message_chain: Current message chain
            correction_plan: Plan of corrections
            
        Returns:
            Corrected message chain
        """
        ...