"""Composite relevance evaluator combining multiple strategies."""

from typing import Dict, List, Optional

from structlog import get_logger

from memory_agent.core.entities import ConversationBlock
from memory_agent.core.evaluation.base import BaseRelevanceEvaluator
from memory_agent.core.evaluation.heuristic_evaluator import HeuristicRelevanceEvaluator
from memory_agent.core.evaluation.llm_evaluator import LLMRelevanceEvaluator
from memory_agent.core.interfaces import Decision, RelevanceFactors, RelevanceScore

logger = get_logger(__name__)


class CompositeRelevanceEvaluator(BaseRelevanceEvaluator):
    """Composite evaluator using multiple evaluation strategies."""
    
    def __init__(
        self,
        use_llm: bool = True,
        llm_weight: float = 0.7,
        heuristic_weight: float = 0.3,
        semantic_weight: float = 0.3,
        temporal_weight: float = 0.2,
        goal_weight: float = 0.25,
        information_weight: float = 0.15,
        factual_weight: float = 0.1,
    ):
        """Initialize composite relevance evaluator.
        
        Args:
            use_llm: Whether to use LLM evaluation
            llm_weight: Weight for LLM evaluation (0-1)
            heuristic_weight: Weight for heuristic evaluation (0-1)
            semantic_weight: Weight for semantic alignment
            temporal_weight: Weight for temporal relevance
            goal_weight: Weight for goal contribution
            information_weight: Weight for information quality
            factual_weight: Weight for factual consistency
        """
        super().__init__(
            semantic_weight,
            temporal_weight,
            goal_weight,
            information_weight,
            factual_weight,
        )
        
        self.use_llm = use_llm
        
        # Normalize weights
        total = llm_weight + heuristic_weight
        self.llm_weight = llm_weight / total
        self.heuristic_weight = heuristic_weight / total
        
        # Initialize evaluators
        self.heuristic_evaluator = HeuristicRelevanceEvaluator(
            semantic_weight,
            temporal_weight,
            goal_weight,
            information_weight,
            factual_weight,
        )
        
        if self.use_llm:
            self.llm_evaluator = LLMRelevanceEvaluator(
                semantic_weight,
                temporal_weight,
                goal_weight,
                information_weight,
                factual_weight,
            )
        else:
            self.llm_evaluator = None
        
        logger.info(
            "Initialized composite evaluator",
            use_llm=use_llm,
            llm_weight=self.llm_weight,
            heuristic_weight=self.heuristic_weight,
        )
    
    async def evaluate(
        self,
        block: ConversationBlock,
        context: List[ConversationBlock],
        metadata: Optional[Dict] = None,
    ) -> RelevanceScore:
        """Evaluate relevance using multiple strategies."""
        metadata = metadata or {}
        
        # Always get heuristic evaluation (fast)
        heuristic_score = await self.heuristic_evaluator.evaluate(
            block, context, metadata
        )
        
        # Optionally get LLM evaluation
        if self.use_llm and self.llm_evaluator:
            # Use LLM for critical decisions or when heuristic is uncertain
            if (
                heuristic_score.overall_score < 0.6 or
                heuristic_score.overall_score > 0.4 and heuristic_score.overall_score < 0.7 or
                metadata.get("force_llm", False)
            ):
                try:
                    llm_score = await self.llm_evaluator.evaluate(
                        block, context, metadata
                    )
                    
                    # Combine scores
                    return self._combine_scores(heuristic_score, llm_score)
                    
                except Exception as e:
                    logger.warning(
                        "LLM evaluation failed, using heuristic only",
                        error=str(e),
                    )
                    return heuristic_score
        
        return heuristic_score
    
    def _combine_scores(
        self,
        heuristic_score: RelevanceScore,
        llm_score: RelevanceScore,
    ) -> RelevanceScore:
        """Combine scores from multiple evaluators."""
        # Combine overall scores
        overall = (
            (heuristic_score.overall_score * self.heuristic_weight) +
            (llm_score.overall_score * self.llm_weight)
        )
        
        # Combine factors
        factors = RelevanceFactors(
            semantic_alignment=(
                (heuristic_score.factors.semantic_alignment * self.heuristic_weight) +
                (llm_score.factors.semantic_alignment * self.llm_weight)
            ),
            temporal_relevance=(
                (heuristic_score.factors.temporal_relevance * self.heuristic_weight) +
                (llm_score.factors.temporal_relevance * self.llm_weight)
            ),
            goal_contribution=(
                (heuristic_score.factors.goal_contribution * self.heuristic_weight) +
                (llm_score.factors.goal_contribution * self.llm_weight)
            ),
            information_quality=(
                (heuristic_score.factors.information_quality * self.heuristic_weight) +
                (llm_score.factors.information_quality * self.llm_weight)
            ),
            factual_consistency=(
                (heuristic_score.factors.factual_consistency * self.heuristic_weight) +
                (llm_score.factors.factual_consistency * self.llm_weight)
            ),
        )
        
        # Determine decision (prefer more conservative)
        if heuristic_score.decision == Decision.REMOVE or llm_score.decision == Decision.REMOVE:
            decision = Decision.REMOVE
        elif heuristic_score.decision == Decision.REVIEW or llm_score.decision == Decision.REVIEW:
            decision = Decision.REVIEW
        else:
            decision = Decision.KEEP
        
        # Combine explanations
        explanation = (
            f"Composite evaluation (H:{self.heuristic_weight:.1f}, L:{self.llm_weight:.1f}): "
            f"{heuristic_score.explanation} | LLM: {llm_score.explanation}"
        )
        
        return RelevanceScore(
            overall_score=overall,
            factors=factors,
            decision=decision,
            explanation=explanation,
        )
    
    async def _evaluate_semantic_alignment(
        self,
        block: ConversationBlock,
        context: List[ConversationBlock],
    ) -> float:
        """Semantic alignment is handled by sub-evaluators."""
        raise NotImplementedError("Use evaluate() method instead")
    
    async def _evaluate_temporal_relevance(
        self,
        block: ConversationBlock,
        context: List[ConversationBlock],
    ) -> float:
        """Temporal relevance is handled by sub-evaluators."""
        raise NotImplementedError("Use evaluate() method instead")
    
    async def _evaluate_goal_contribution(
        self,
        block: ConversationBlock,
        context: List[ConversationBlock],
        goal: Optional[str] = None,
    ) -> float:
        """Goal contribution is handled by sub-evaluators."""
        raise NotImplementedError("Use evaluate() method instead")
    
    async def _evaluate_information_quality(
        self,
        block: ConversationBlock,
    ) -> float:
        """Information quality is handled by sub-evaluators."""
        raise NotImplementedError("Use evaluate() method instead")
    
    async def _evaluate_factual_consistency(
        self,
        block: ConversationBlock,
        context: List[ConversationBlock],
    ) -> float:
        """Factual consistency is handled by sub-evaluators."""
        raise NotImplementedError("Use evaluate() method instead")