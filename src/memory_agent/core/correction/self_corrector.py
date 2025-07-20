"""Self-correction loop implementation."""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from structlog import get_logger

from memory_agent.core.entities import ConversationBlock, Message, MessageChain
from memory_agent.core.evaluation.service import relevance_service
from memory_agent.core.interfaces import (
    CompletionOptions,
    Decision,
    MessageRole,
    RelevanceScore,
)
from memory_agent.infrastructure.llm.service import llm_service
from memory_agent.infrastructure.storage.manager import MemoryStorageManager

logger = get_logger(__name__)


class SelfCorrector:
    """Implements autonomous self-correction for conversations."""
    
    def __init__(
        self,
        storage_manager: MemoryStorageManager,
        correction_threshold: float = 0.4,
        review_threshold: float = 0.6,
        max_corrections_per_cycle: int = 3,
        enable_auto_correction: bool = True,
    ):
        """Initialize self-corrector.
        
        Args:
            storage_manager: Memory storage manager
            correction_threshold: Score below which to correct
            review_threshold: Score below which to review
            max_corrections_per_cycle: Max corrections in one cycle
            enable_auto_correction: Whether to auto-correct
        """
        self.storage_manager = storage_manager
        self.correction_threshold = correction_threshold
        self.review_threshold = review_threshold
        self.max_corrections_per_cycle = max_corrections_per_cycle
        self.enable_auto_correction = enable_auto_correction
        
        # Track correction history
        self._correction_history: List[Dict] = []
        self._active = False
        self._correction_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start the self-correction loop."""
        self._active = True
        if self.enable_auto_correction:
            self._correction_task = asyncio.create_task(self._correction_loop())
        logger.info(
            "Started self-correction loop",
            auto_correction=self.enable_auto_correction,
            correction_threshold=self.correction_threshold,
        )
    
    async def stop(self) -> None:
        """Stop the self-correction loop."""
        self._active = False
        if self._correction_task:
            self._correction_task.cancel()
            try:
                await self._correction_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped self-correction loop")
    
    async def analyze_conversation(
        self,
        session_id: str,
        window_size: int = 10,
    ) -> List[Tuple[ConversationBlock, RelevanceScore]]:
        """Analyze recent conversation for issues.
        
        Args:
            session_id: Session to analyze
            window_size: Number of recent blocks to check
            
        Returns:
            List of (block, score) tuples for problematic blocks
        """
        # Get recent blocks
        block_ids = await self.storage_manager.list_blocks(session_id=session_id)
        recent_ids = block_ids[-window_size:] if len(block_ids) > window_size else block_ids
        
        # Retrieve blocks
        blocks = []
        for block_id in recent_ids:
            block = await self.storage_manager.retrieve_block(block_id, session_id)
            if block:
                blocks.append(block)
        
        # Evaluate relevance
        problematic = []
        if blocks:
            evaluated = await relevance_service.evaluate_conversation(blocks)
            
            for block, score in evaluated:
                if score.overall_score < self.review_threshold:
                    problematic.append((block, score))
        
        return problematic
    
    async def correct_conversation(
        self,
        session_id: str,
        problematic_blocks: List[Tuple[ConversationBlock, RelevanceScore]],
    ) -> List[Dict]:
        """Correct problematic parts of conversation.
        
        Args:
            session_id: Session to correct
            problematic_blocks: Blocks that need correction
            
        Returns:
            List of corrections made
        """
        corrections = []
        correction_count = 0
        
        for block, score in problematic_blocks:
            if correction_count >= self.max_corrections_per_cycle:
                break
            
            # Determine correction action
            if score.decision == Decision.REMOVE:
                # Remove the block
                success = await self.storage_manager.delete_block(
                    block.block_id,
                    session_id,
                )
                
                if success:
                    correction = {
                        "type": "removal",
                        "block_id": block.block_id,
                        "reason": score.explanation,
                        "timestamp": datetime.utcnow(),
                    }
                    corrections.append(correction)
                    correction_count += 1
                    
                    logger.info(
                        "Removed irrelevant block",
                        block_id=block.block_id,
                        score=score.overall_score,
                    )
            
            elif score.decision == Decision.REVIEW and self.enable_auto_correction:
                # Try to improve the block
                improved_block = await self._improve_block(block, score, session_id)
                
                if improved_block:
                    # Replace the original block
                    await self.storage_manager.delete_block(block.block_id, session_id)
                    await self.storage_manager.store_block(improved_block, session_id=session_id)
                    
                    correction = {
                        "type": "improvement",
                        "original_block_id": block.block_id,
                        "new_block_id": improved_block.block_id,
                        "reason": score.explanation,
                        "timestamp": datetime.utcnow(),
                    }
                    corrections.append(correction)
                    correction_count += 1
                    
                    logger.info(
                        "Improved block",
                        original_id=block.block_id,
                        new_id=improved_block.block_id,
                    )
        
        # Record corrections in history
        if corrections:
            self._correction_history.extend(corrections)
            
            # Trim history to last 100 corrections
            if len(self._correction_history) > 100:
                self._correction_history = self._correction_history[-100:]
        
        return corrections
    
    async def _improve_block(
        self,
        block: ConversationBlock,
        score: RelevanceScore,
        session_id: str,
    ) -> Optional[ConversationBlock]:
        """Improve a problematic block.
        
        Args:
            block: Block to improve
            score: Relevance score with issues
            session_id: Session ID
            
        Returns:
            Improved block or None if improvement failed
        """
        # Get context
        block_ids = await self.storage_manager.list_blocks(session_id=session_id)
        context_blocks = []
        
        # Get blocks before and after
        block_index = block_ids.index(block.block_id) if block.block_id in block_ids else -1
        if block_index >= 0:
            for i in range(max(0, block_index - 3), min(len(block_ids), block_index + 3)):
                if i != block_index:
                    ctx_block = await self.storage_manager.retrieve_block(block_ids[i], session_id)
                    if ctx_block:
                        context_blocks.append(ctx_block)
        
        # Identify the main issue
        weakest_factor = min(
            [
                ("semantic_alignment", score.factors.semantic_alignment),
                ("temporal_relevance", score.factors.temporal_relevance),
                ("goal_contribution", score.factors.goal_contribution),
                ("information_quality", score.factors.information_quality),
                ("factual_consistency", score.factors.factual_consistency),
            ],
            key=lambda x: x[1],
        )
        
        # Create improvement prompt
        improvement_prompt = self._create_improvement_prompt(
            block,
            context_blocks,
            weakest_factor[0],
            score.explanation,
        )
        
        # Get LLM to improve the response
        messages = [
            Message(
                role=MessageRole.SYSTEM,
                content="You are a conversation improver. Improve the given response to address the identified issues while maintaining the original intent.",
            ),
            Message(
                role=MessageRole.USER,
                content=improvement_prompt,
            ),
        ]
        
        try:
            response = await llm_service.complete(
                messages,
                CompletionOptions(
                    temperature=0.7,
                    max_tokens=500,
                ),
            )
            
            # Create improved block with new schema
            improved_block = ConversationBlock(
                block_id=f"{block.block_id}_improved",
                sequence_number=block.sequence_number,
                session_id=block.session_id,
                content=response.content,  # Use improved content
                source=block.source,
                message_id=f"{block.message_id}_improved",
                relevance_score=score.overall_score * 1.5,  # Assume improvement
                metadata={
                    "improved": True,
                    "original_content": block.content,
                    "improvement_reason": score.explanation,
                },
            )
            
            return improved_block
            
        except Exception as e:
            logger.error(
                "Failed to improve block",
                block_id=block.block_id,
                error=str(e),
            )
            return None
    
    def _create_improvement_prompt(
        self,
        block: ConversationBlock,
        context: List[ConversationBlock],
        weak_factor: str,
        explanation: str,
    ) -> str:
        """Create prompt for improving a block."""
        # Extract content from block
        block_content = f"{block.source.upper()}: {block.content}"
        
        context_summary = "\n".join([
            f"- {ctx.content[:100]}..." 
            for ctx in context[-3:]
        ]) if context else "No context available"
        
        # Factor-specific guidance
        guidance = {
            "semantic_alignment": "Make the response more relevant to the conversation topic and context.",
            "temporal_relevance": "Update any time-sensitive information and remove outdated references.",
            "goal_contribution": "Focus on addressing the user's actual question or goal.",
            "information_quality": "Provide more specific, detailed, and useful information.",
            "factual_consistency": "Correct any factual errors or inconsistencies.",
        }
        
        return f"""Improve this conversation response:

Current Response:
{block_content}

Recent Context:
{context_summary}

Issue Identified: {explanation}
Main Problem: Weak {weak_factor.replace('_', ' ')}

Improvement Needed: {guidance.get(weak_factor, 'Improve overall quality')}

Provide an improved version that addresses these issues while maintaining the helpful intent."""
    
    async def _correction_loop(self) -> None:
        """Background correction loop."""
        while self._active:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                # Get all active sessions
                all_blocks = await self.storage_manager.list_blocks()
                sessions = set()
                
                for block_id in all_blocks:
                    # Extract session from block ID pattern
                    if "_" in block_id:
                        session = block_id.split("_")[0]
                        sessions.add(session)
                
                # Analyze each session
                for session_id in sessions:
                    if not self._active:
                        break
                    
                    # Analyze conversation
                    problematic = await self.analyze_conversation(session_id)
                    
                    if problematic:
                        logger.info(
                            "Found problematic blocks",
                            session_id=session_id,
                            count=len(problematic),
                        )
                        
                        # Correct issues
                        corrections = await self.correct_conversation(
                            session_id,
                            problematic,
                        )
                        
                        if corrections:
                            logger.info(
                                "Applied corrections",
                                session_id=session_id,
                                correction_count=len(corrections),
                            )
                
            except Exception as e:
                logger.error(
                    "Error in correction loop",
                    error=str(e),
                )
                await asyncio.sleep(5)  # Brief pause on error
    
    def get_correction_history(self, limit: int = 10) -> List[Dict]:
        """Get recent correction history."""
        return self._correction_history[-limit:]
    
    async def force_correction(self, session_id: str) -> List[Dict]:
        """Force an immediate correction cycle for a session."""
        problematic = await self.analyze_conversation(session_id)
        
        if problematic:
            return await self.correct_conversation(session_id, problematic)
        
        return []