"""Base relevance evaluation implementation."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from structlog import get_logger

from memory_agent.core.entities import ConversationBlock, Message
from memory_agent.core.interfaces import (
    Decision,
    IRelevanceEvaluator,
    RelevanceFactors,
    RelevanceScore,
)

logger = get_logger(__name__)


class BaseRelevanceEvaluator(IRelevanceEvaluator, ABC):
    """Base implementation for relevance evaluators."""
    
    def __init__(
        self,
        semantic_weight: float = 0.3,
        temporal_weight: float = 0.2,
        goal_weight: float = 0.25,
        information_weight: float = 0.15,
        factual_weight: float = 0.1,
    ):
        """Initialize base relevance evaluator.
        
        Args:
            semantic_weight: Weight for semantic alignment (0-1)
            temporal_weight: Weight for temporal relevance (0-1)
            goal_weight: Weight for goal contribution (0-1)
            information_weight: Weight for information quality (0-1)
            factual_weight: Weight for factual consistency (0-1)
        """
        # Normalize weights
        total_weight = (
            semantic_weight + 
            temporal_weight + 
            goal_weight + 
            information_weight + 
            factual_weight
        )
        
        self.weights = {
            "semantic_alignment": semantic_weight / total_weight,
            "temporal_relevance": temporal_weight / total_weight,
            "goal_contribution": goal_weight / total_weight,
            "information_quality": information_weight / total_weight,
            "factual_consistency": factual_weight / total_weight,
        }
        
        logger.info(
            "Initialized relevance evaluator",
            weights=self.weights,
        )
    
    @abstractmethod
    async def _evaluate_semantic_alignment(
        self,
        block: ConversationBlock,
        context: List[ConversationBlock],
    ) -> float:
        """Evaluate semantic alignment with context.
        
        Args:
            block: Block to evaluate
            context: Surrounding conversation blocks
            
        Returns:
            Score between 0 and 1
        """
        pass
    
    @abstractmethod
    async def _evaluate_temporal_relevance(
        self,
        block: ConversationBlock,
        context: List[ConversationBlock],
    ) -> float:
        """Evaluate temporal relevance.
        
        Args:
            block: Block to evaluate
            context: Surrounding conversation blocks
            
        Returns:
            Score between 0 and 1
        """
        pass
    
    @abstractmethod
    async def _evaluate_goal_contribution(
        self,
        block: ConversationBlock,
        context: List[ConversationBlock],
        goal: Optional[str] = None,
    ) -> float:
        """Evaluate contribution to conversation goal.
        
        Args:
            block: Block to evaluate
            context: Surrounding conversation blocks
            goal: Explicit goal if available
            
        Returns:
            Score between 0 and 1
        """
        pass
    
    @abstractmethod
    async def _evaluate_information_quality(
        self,
        block: ConversationBlock,
    ) -> float:
        """Evaluate information quality and uniqueness.
        
        Args:
            block: Block to evaluate
            
        Returns:
            Score between 0 and 1
        """
        pass
    
    @abstractmethod
    async def _evaluate_factual_consistency(
        self,
        block: ConversationBlock,
        context: List[ConversationBlock],
    ) -> float:
        """Evaluate factual consistency.
        
        Args:
            block: Block to evaluate
            context: Surrounding conversation blocks
            
        Returns:
            Score between 0 and 1
        """
        pass
    
    async def evaluate(
        self,
        block: ConversationBlock,
        context: List[ConversationBlock],
        metadata: Optional[Dict] = None,
    ) -> RelevanceScore:
        """Evaluate relevance of a conversation block."""
        metadata = metadata or {}
        
        # Evaluate each factor
        factors = RelevanceFactors(
            semantic_alignment=await self._evaluate_semantic_alignment(block, context),
            temporal_relevance=await self._evaluate_temporal_relevance(block, context),
            goal_contribution=await self._evaluate_goal_contribution(
                block, context, metadata.get("goal")
            ),
            information_quality=await self._evaluate_information_quality(block),
            factual_consistency=await self._evaluate_factual_consistency(block, context),
        )
        
        # Calculate weighted overall score
        overall_score = sum(
            getattr(factors, factor) * weight
            for factor, weight in self.weights.items()
        )
        
        # Determine decision
        decision = self._make_decision(overall_score, factors, metadata)
        
        # Create relevance score
        score = RelevanceScore(
            overall_score=overall_score,
            factors=factors,
            decision=decision,
            explanation=self._generate_explanation(overall_score, factors, decision),
        )
        
        logger.debug(
            "Evaluated block relevance",
            block_id=block.block_id,
            score=overall_score,
            decision=decision.value,
        )
        
        return score
    
    def _make_decision(
        self,
        overall_score: float,
        factors: RelevanceFactors,
        metadata: Dict,
    ) -> Decision:
        """Make decision based on scores.
        
        Args:
            overall_score: Overall relevance score
            factors: Individual factor scores
            metadata: Additional metadata
            
        Returns:
            Decision for the block
        """
        # Get thresholds from metadata or use defaults
        keep_threshold = metadata.get("keep_threshold", 0.7)
        review_threshold = metadata.get("review_threshold", 0.4)
        
        # Check for critical factors
        if factors.factual_consistency < 0.3:
            return Decision.REMOVE
        
        if factors.semantic_alignment < 0.2:
            return Decision.REMOVE
        
        # Make decision based on overall score
        if overall_score >= keep_threshold:
            return Decision.KEEP
        elif overall_score >= review_threshold:
            return Decision.REVIEW
        else:
            return Decision.REMOVE
    
    def _generate_explanation(
        self,
        overall_score: float,
        factors: RelevanceFactors,
        decision: Decision,
    ) -> str:
        """Generate explanation for the decision.
        
        Args:
            overall_score: Overall relevance score
            factors: Individual factor scores
            decision: Decision made
            
        Returns:
            Human-readable explanation
        """
        # Find weakest factors
        factor_scores = {
            "semantic alignment": factors.semantic_alignment,
            "temporal relevance": factors.temporal_relevance,
            "goal contribution": factors.goal_contribution,
            "information quality": factors.information_quality,
            "factual consistency": factors.factual_consistency,
        }
        
        sorted_factors = sorted(factor_scores.items(), key=lambda x: x[1])
        weakest = sorted_factors[0]
        strongest = sorted_factors[-1]
        
        if decision == Decision.KEEP:
            return (
                f"Block is relevant with score {overall_score:.2f}. "
                f"Strongest factor: {strongest[0]} ({strongest[1]:.2f})"
            )
        elif decision == Decision.REVIEW:
            return (
                f"Block needs review with score {overall_score:.2f}. "
                f"Weakest factor: {weakest[0]} ({weakest[1]:.2f})"
            )
        else:
            return (
                f"Block should be removed with score {overall_score:.2f}. "
                f"Critical weakness: {weakest[0]} ({weakest[1]:.2f})"
            )
    
    async def batch_evaluate(
        self,
        blocks: List[ConversationBlock],
        metadata: Optional[Dict] = None,
    ) -> List[RelevanceScore]:
        """Evaluate multiple blocks."""
        scores = []
        
        for i, block in enumerate(blocks):
            # Use surrounding blocks as context
            context = blocks[max(0, i-5):i] + blocks[i+1:min(len(blocks), i+6)]
            score = await self.evaluate(block, context, metadata)
            scores.append(score)
        
        return scores
    
    async def evaluate_correction(
        self,
        original_block: ConversationBlock,
        corrected_block: ConversationBlock,
        context: List[ConversationBlock],
    ) -> float:
        """Evaluate improvement from correction."""
        # Evaluate both blocks
        original_score = await self.evaluate(original_block, context)
        corrected_score = await self.evaluate(corrected_block, context)
        
        # Calculate improvement
        improvement = corrected_score.overall_score - original_score.overall_score
        
        logger.info(
            "Evaluated correction",
            original_score=original_score.overall_score,
            corrected_score=corrected_score.overall_score,
            improvement=improvement,
        )
        
        return improvement