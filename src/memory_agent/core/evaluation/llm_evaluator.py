"""LLM-based relevance evaluator."""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np
from structlog import get_logger

from memory_agent.core.entities import ConversationBlock, Message
from memory_agent.core.evaluation.base import BaseRelevanceEvaluator
from memory_agent.core.interfaces import CompletionOptions, MessageRole
from memory_agent.infrastructure.llm.service import llm_service

logger = get_logger(__name__)


class LLMRelevanceEvaluator(BaseRelevanceEvaluator):
    """Relevance evaluator using LLM for sophisticated analysis."""
    
    def __init__(
        self,
        semantic_weight: float = 0.3,
        temporal_weight: float = 0.2,
        goal_weight: float = 0.25,
        information_weight: float = 0.15,
        factual_weight: float = 0.1,
        use_embeddings: bool = True,
    ):
        """Initialize LLM relevance evaluator.
        
        Args:
            semantic_weight: Weight for semantic alignment
            temporal_weight: Weight for temporal relevance
            goal_weight: Weight for goal contribution
            information_weight: Weight for information quality
            factual_weight: Weight for factual consistency
            use_embeddings: Whether to use embeddings for semantic similarity
        """
        super().__init__(
            semantic_weight,
            temporal_weight,
            goal_weight,
            information_weight,
            factual_weight,
        )
        self.use_embeddings = use_embeddings
        self._embedding_cache: Dict[str, np.ndarray] = {}
    
    async def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for text.
        
        For now, we'll use a simple implementation. In production,
        you'd use an embedding model like text-embedding-ada-002.
        """
        # Check cache
        if text in self._embedding_cache:
            return self._embedding_cache[text]
        
        # For demonstration, create a simple hash-based embedding
        # In production, use actual embedding models
        import hashlib
        
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()
        
        # Convert to normalized vector
        embedding = np.frombuffer(hash_bytes, dtype=np.uint8).astype(np.float32)
        embedding = embedding[:128]  # Use first 128 dimensions
        embedding = embedding / np.linalg.norm(embedding)
        
        self._embedding_cache[text] = embedding
        return embedding
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
    
    async def _evaluate_semantic_alignment(
        self,
        block: ConversationBlock,
        context: List[ConversationBlock],
    ) -> float:
        """Evaluate semantic alignment with context."""
        if not context:
            return 0.8  # Default score for first block
        
        # Get block content
        block_content = " ".join([msg.content for msg in block.messages])
        
        if self.use_embeddings:
            # Use embeddings for semantic similarity
            block_embedding = await self._get_embedding(block_content)
            
            # Calculate similarity with recent context
            similarities = []
            for ctx_block in context[-3:]:  # Last 3 blocks
                ctx_content = " ".join([msg.content for msg in ctx_block.messages])
                ctx_embedding = await self._get_embedding(ctx_content)
                similarity = self._cosine_similarity(block_embedding, ctx_embedding)
                similarities.append(similarity)
            
            # Average similarity, but not too high (we want some diversity)
            avg_similarity = np.mean(similarities) if similarities else 0.5
            
            # Score is high if similarity is moderate (0.3-0.8)
            if avg_similarity < 0.3:
                return 0.3  # Too different
            elif avg_similarity > 0.9:
                return 0.5  # Too similar (redundant)
            else:
                return 0.8  # Good alignment
        
        else:
            # Use LLM for evaluation
            context_summary = self._summarize_context(context[-3:])
            
            prompt = f"""Evaluate the semantic alignment of this message with the conversation context.

Context Summary:
{context_summary}

Current Message:
{block_content}

Rate the semantic alignment from 0 to 1, where:
- 0 = Completely unrelated to the conversation
- 0.5 = Somewhat related but tangential
- 1 = Perfectly aligned with the conversation flow

Respond with just a number between 0 and 1."""

            try:
                response = await self._query_llm(prompt, temperature=0.1)
                score = float(response.strip())
                return max(0, min(1, score))
            except:
                return 0.7  # Default score on error
    
    async def _evaluate_temporal_relevance(
        self,
        block: ConversationBlock,
        context: List[ConversationBlock],
    ) -> float:
        """Evaluate temporal relevance."""
        # Get block age
        block_age = datetime.utcnow() - block.created_at
        
        # Score based on age
        if block_age < timedelta(minutes=5):
            age_score = 1.0
        elif block_age < timedelta(hours=1):
            age_score = 0.9
        elif block_age < timedelta(hours=6):
            age_score = 0.7
        elif block_age < timedelta(days=1):
            age_score = 0.5
        elif block_age < timedelta(days=7):
            age_score = 0.3
        else:
            age_score = 0.1
        
        # Check if block references recent events
        block_content = " ".join([msg.content for msg in block.messages])
        
        # Look for temporal markers
        temporal_markers = [
            "today", "yesterday", "tomorrow", "now", "currently",
            "this week", "last week", "next week", "recently",
        ]
        
        has_temporal_reference = any(
            marker in block_content.lower() 
            for marker in temporal_markers
        )
        
        if has_temporal_reference:
            # Block discusses time-sensitive information
            return min(1.0, age_score * 1.2)
        
        # Consider access frequency
        access_score = min(1.0, block.access_count / 10)
        
        return (age_score * 0.7) + (access_score * 0.3)
    
    async def _evaluate_goal_contribution(
        self,
        block: ConversationBlock,
        context: List[ConversationBlock],
        goal: Optional[str] = None,
    ) -> float:
        """Evaluate contribution to conversation goal."""
        block_content = " ".join([msg.content for msg in block.messages])
        
        # If no explicit goal, try to infer from context
        if not goal and context:
            # Look for question/task in recent context
            for ctx_block in reversed(context[-5:]):
                for msg in ctx_block.messages:
                    if msg.role == MessageRole.USER and "?" in msg.content:
                        goal = f"Answer: {msg.content}"
                        break
                if goal:
                    break
        
        if not goal:
            # No clear goal, use general relevance
            return 0.7
        
        # Use LLM to evaluate goal contribution
        prompt = f"""Evaluate how well this message contributes to the conversation goal.

Goal: {goal}

Message:
{block_content}

Rate the contribution from 0 to 1, where:
- 0 = Completely unrelated or counterproductive
- 0.5 = Somewhat helpful but indirect
- 1 = Directly addresses and advances the goal

Respond with just a number between 0 and 1."""

        try:
            response = await self._query_llm(prompt, temperature=0.1)
            score = float(response.strip())
            return max(0, min(1, score))
        except:
            return 0.6  # Default score on error
    
    async def _evaluate_information_quality(
        self,
        block: ConversationBlock,
    ) -> float:
        """Evaluate information quality and uniqueness."""
        block_content = " ".join([msg.content for msg in block.messages])
        
        # Basic quality checks
        word_count = len(block_content.split())
        
        # Too short or too long messages are lower quality
        if word_count < 3:
            length_score = 0.3
        elif word_count < 10:
            length_score = 0.7
        elif word_count < 200:
            length_score = 1.0
        elif word_count < 500:
            length_score = 0.8
        else:
            length_score = 0.6
        
        # Check for substantive content
        substantive_words = [
            "because", "therefore", "however", "specifically",
            "example", "means", "important", "explain",
        ]
        
        has_substance = any(
            word in block_content.lower() 
            for word in substantive_words
        )
        
        substance_score = 0.8 if has_substance else 0.5
        
        # Check for questions (information seeking)
        has_question = "?" in block_content
        question_score = 0.9 if has_question else 0.7
        
        # Combine scores
        return (length_score * 0.4) + (substance_score * 0.4) + (question_score * 0.2)
    
    async def _evaluate_factual_consistency(
        self,
        block: ConversationBlock,
        context: List[ConversationBlock],
    ) -> float:
        """Evaluate factual consistency."""
        if not context:
            return 0.9  # Can't verify consistency without context
        
        block_content = " ".join([msg.content for msg in block.messages])
        context_facts = self._extract_facts(context)
        
        if not context_facts:
            return 0.9  # No facts to check against
        
        # Use LLM to check consistency
        prompt = f"""Check if this message is factually consistent with the established facts in the conversation.

Established Facts:
{json.dumps(context_facts, indent=2)}

Current Message:
{block_content}

Rate the factual consistency from 0 to 1, where:
- 0 = Contains clear contradictions
- 0.5 = Some questionable claims
- 1 = Fully consistent with established facts

Respond with just a number between 0 and 1."""

        try:
            response = await self._query_llm(prompt, temperature=0.1)
            score = float(response.strip())
            return max(0, min(1, score))
        except:
            return 0.8  # Default score on error
    
    def _summarize_context(self, context: List[ConversationBlock]) -> str:
        """Create a summary of context blocks."""
        if not context:
            return "No prior context."
        
        summaries = []
        for block in context:
            role = block.messages[0].role.value if block.messages else "unknown"
            content = " ".join([msg.content for msg in block.messages])
            
            # Truncate long content
            if len(content) > 200:
                content = content[:200] + "..."
            
            summaries.append(f"{role}: {content}")
        
        return "\n".join(summaries)
    
    def _extract_facts(self, context: List[ConversationBlock]) -> List[str]:
        """Extract key facts from context."""
        facts = []
        
        for block in context:
            for msg in block.messages:
                content = msg.content.lower()
                
                # Look for factual statements
                if any(pattern in content for pattern in [
                    " is ", " are ", " was ", " were ",
                    " has ", " have ", " equals ", " means ",
                ]):
                    # Simple extraction - in production use NLP
                    sentences = content.split(".")
                    for sentence in sentences:
                        if len(sentence.split()) > 3 and len(sentence.split()) < 30:
                            facts.append(sentence.strip())
        
        # Limit to most recent facts
        return facts[-10:] if facts else []
    
    async def _query_llm(self, prompt: str, temperature: float = 0.7) -> str:
        """Query LLM for evaluation."""
        messages = [
            Message(
                role=MessageRole.SYSTEM,
                content="You are a relevance evaluator. Respond only with numeric scores as requested.",
            ),
            Message(
                role=MessageRole.USER,
                content=prompt,
            ),
        ]
        
        options = CompletionOptions(
            temperature=temperature,
            max_tokens=10,  # We only need a number
        )
        
        response = await llm_service.complete(messages, options)
        return response.content