"""Relevance evaluation service."""

from typing import Dict, List, Optional, Tuple

from structlog import get_logger

from memory_agent.core.entities import ConversationBlock
from memory_agent.core.evaluation import (
    CompositeRelevanceEvaluator,
    HeuristicRelevanceEvaluator,
    LLMRelevanceEvaluator,
)
from memory_agent.core.interfaces import (
    Decision,
    IRelevanceEvaluator,
    RelevanceScore,
)
from memory_agent.infrastructure.config.settings import settings

logger = get_logger(__name__)


class RelevanceEvaluationService:
    """Service for managing relevance evaluation."""
    
    def __init__(self):
        """Initialize relevance evaluation service."""
        self._evaluator: Optional[IRelevanceEvaluator] = None
        self._evaluation_cache: Dict[str, RelevanceScore] = {}
        self._cache_size = 1000
    
    async def initialize(self) -> None:
        """Initialize the service."""
        # Determine evaluation strategy based on settings
        evaluation_mode = getattr(settings, "evaluation_mode", "composite")
        
        if evaluation_mode == "heuristic":
            self._evaluator = HeuristicRelevanceEvaluator()
            logger.info("Using heuristic relevance evaluator")
            
        elif evaluation_mode == "llm":
            self._evaluator = LLMRelevanceEvaluator()
            logger.info("Using LLM relevance evaluator")
            
        else:  # composite
            use_llm = settings.llm_provider != "mock"
            self._evaluator = CompositeRelevanceEvaluator(use_llm=use_llm)
            logger.info(
                "Using composite relevance evaluator",
                use_llm=use_llm,
            )
    
    async def evaluate_block(
        self,
        block: ConversationBlock,
        context: List[ConversationBlock],
        metadata: Optional[Dict] = None,
        use_cache: bool = True,
    ) -> RelevanceScore:
        """Evaluate relevance of a single block.
        
        Args:
            block: Block to evaluate
            context: Surrounding conversation blocks
            metadata: Additional metadata for evaluation
            use_cache: Whether to use cached results
            
        Returns:
            Relevance score
        """
        if not self._evaluator:
            await self.initialize()
        
        # Check cache
        cache_key = f"{block.block_id}:{len(context)}"
        if use_cache and cache_key in self._evaluation_cache:
            logger.debug(
                "Using cached relevance score",
                block_id=block.block_id,
            )
            return self._evaluation_cache[cache_key]
        
        # Evaluate
        score = await self._evaluator.evaluate(block, context, metadata)
        
        # Cache result
        if use_cache:
            self._cache_evaluation(cache_key, score)
        
        # Log significant decisions
        if score.decision == Decision.REMOVE:
            logger.warning(
                "Block marked for removal",
                block_id=block.block_id,
                score=score.overall_score,
                reason=score.explanation,
            )
        elif score.decision == Decision.REVIEW:
            logger.info(
                "Block marked for review",
                block_id=block.block_id,
                score=score.overall_score,
                reason=score.explanation,
            )
        
        return score
    
    async def evaluate_conversation(
        self,
        blocks: List[ConversationBlock],
        metadata: Optional[Dict] = None,
    ) -> List[Tuple[ConversationBlock, RelevanceScore]]:
        """Evaluate all blocks in a conversation.
        
        Args:
            blocks: All conversation blocks
            metadata: Additional metadata for evaluation
            
        Returns:
            List of (block, score) tuples
        """
        if not self._evaluator:
            await self.initialize()
        
        results = []
        
        for i, block in enumerate(blocks):
            # Use surrounding blocks as context
            context = blocks[max(0, i-5):i] + blocks[i+1:min(len(blocks), i+6)]
            score = await self.evaluate_block(block, context, metadata)
            results.append((block, score))
        
        return results
    
    async def find_irrelevant_blocks(
        self,
        blocks: List[ConversationBlock],
        threshold: float = 0.4,
        metadata: Optional[Dict] = None,
    ) -> List[Tuple[ConversationBlock, RelevanceScore]]:
        """Find blocks that should be removed or reviewed.
        
        Args:
            blocks: Conversation blocks to evaluate
            threshold: Relevance threshold (blocks below this are irrelevant)
            metadata: Additional metadata for evaluation
            
        Returns:
            List of (block, score) tuples for irrelevant blocks
        """
        # Evaluate all blocks
        evaluated = await self.evaluate_conversation(blocks, metadata)
        
        # Filter irrelevant ones
        irrelevant = [
            (block, score)
            for block, score in evaluated
            if score.overall_score < threshold or score.decision == Decision.REMOVE
        ]
        
        logger.info(
            "Found irrelevant blocks",
            total_blocks=len(blocks),
            irrelevant_count=len(irrelevant),
            threshold=threshold,
        )
        
        return irrelevant
    
    async def suggest_corrections(
        self,
        blocks: List[ConversationBlock],
        metadata: Optional[Dict] = None,
    ) -> List[Dict]:
        """Suggest corrections for improving conversation relevance.
        
        Args:
            blocks: Conversation blocks
            metadata: Additional metadata
            
        Returns:
            List of correction suggestions
        """
        suggestions = []
        
        # Evaluate all blocks
        evaluated = await self.evaluate_conversation(blocks, metadata)
        
        for i, (block, score) in enumerate(evaluated):
            if score.decision == Decision.REMOVE:
                # Suggest removal
                suggestions.append({
                    "type": "remove",
                    "block_id": block.block_id,
                    "reason": score.explanation,
                    "score": score.overall_score,
                })
                
            elif score.decision == Decision.REVIEW:
                # Analyze what's wrong
                factors = score.factors
                
                # Find weakest factor
                weakest_factor = min(
                    [
                        ("semantic_alignment", factors.semantic_alignment),
                        ("temporal_relevance", factors.temporal_relevance),
                        ("goal_contribution", factors.goal_contribution),
                        ("information_quality", factors.information_quality),
                        ("factual_consistency", factors.factual_consistency),
                    ],
                    key=lambda x: x[1],
                )
                
                # Suggest improvement
                if weakest_factor[0] == "semantic_alignment":
                    suggestions.append({
                        "type": "rephrase",
                        "block_id": block.block_id,
                        "reason": "Poor semantic alignment with conversation",
                        "suggestion": "Rephrase to better connect with the conversation context",
                        "score": score.overall_score,
                    })
                    
                elif weakest_factor[0] == "information_quality":
                    suggestions.append({
                        "type": "expand",
                        "block_id": block.block_id,
                        "reason": "Low information quality",
                        "suggestion": "Add more specific details or examples",
                        "score": score.overall_score,
                    })
                    
                elif weakest_factor[0] == "factual_consistency":
                    suggestions.append({
                        "type": "verify",
                        "block_id": block.block_id,
                        "reason": "Potential factual inconsistency",
                        "suggestion": "Verify facts and correct any errors",
                        "score": score.overall_score,
                    })
        
        return suggestions
    
    def _cache_evaluation(self, key: str, score: RelevanceScore) -> None:
        """Cache evaluation result."""
        # Simple LRU-like behavior
        if len(self._evaluation_cache) >= self._cache_size:
            # Remove oldest entry
            oldest_key = next(iter(self._evaluation_cache))
            del self._evaluation_cache[oldest_key]
        
        self._evaluation_cache[key] = score
    
    def clear_cache(self) -> None:
        """Clear evaluation cache."""
        self._evaluation_cache.clear()
        logger.info("Cleared relevance evaluation cache")
    
    def get_evaluator(self) -> Optional[IRelevanceEvaluator]:
        """Get the current evaluator instance."""
        return self._evaluator
    
    async def set_evaluator(self, evaluator: IRelevanceEvaluator) -> None:
        """Set a custom evaluator.
        
        Args:
            evaluator: Evaluator instance to use
        """
        self._evaluator = evaluator
        self.clear_cache()
        logger.info(
            "Set custom evaluator",
            evaluator_type=type(evaluator).__name__,
        )


# Global relevance evaluation service
relevance_service = RelevanceEvaluationService()