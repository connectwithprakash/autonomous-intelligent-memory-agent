"""Heuristic-based relevance evaluator for fast evaluation."""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

from structlog import get_logger

from memory_agent.core.entities import ConversationBlock
from memory_agent.core.evaluation.base import BaseRelevanceEvaluator
from memory_agent.core.interfaces import MessageRole

logger = get_logger(__name__)


class HeuristicRelevanceEvaluator(BaseRelevanceEvaluator):
    """Fast heuristic-based relevance evaluator."""
    
    def __init__(
        self,
        semantic_weight: float = 0.3,
        temporal_weight: float = 0.2,
        goal_weight: float = 0.25,
        information_weight: float = 0.15,
        factual_weight: float = 0.1,
    ):
        """Initialize heuristic relevance evaluator."""
        super().__init__(
            semantic_weight,
            temporal_weight,
            goal_weight,
            information_weight,
            factual_weight,
        )
        
        # Keywords indicating different aspects
        self.greeting_keywords = {
            "hello", "hi", "hey", "greetings", "good morning",
            "good afternoon", "good evening", "welcome",
        }
        
        self.closing_keywords = {
            "bye", "goodbye", "farewell", "see you", "take care",
            "have a nice day", "thank you", "thanks",
        }
        
        self.question_patterns = [
            r"\?", r"^(what|where|when|why|how|who|which)",
            r"(can|could|would|should|may|might) (you|i|we)",
        ]
        
        self.filler_phrases = {
            "i see", "okay", "alright", "sure", "got it",
            "understood", "makes sense", "right", "yeah", "yes",
        }
        
        self.error_keywords = {
            "error", "mistake", "wrong", "incorrect", "sorry",
            "apologize", "my bad", "oops", "fault",
        }
    
    async def _evaluate_semantic_alignment(
        self,
        block: ConversationBlock,
        context: List[ConversationBlock],
    ) -> float:
        """Evaluate semantic alignment using keyword overlap."""
        if not context:
            return 0.8
        
        # Extract keywords from block
        block_keywords = self._extract_keywords(block)
        
        # Extract keywords from recent context
        context_keywords: Set[str] = set()
        for ctx_block in context[-3:]:
            context_keywords.update(self._extract_keywords(ctx_block))
        
        if not block_keywords or not context_keywords:
            return 0.5
        
        # Calculate Jaccard similarity
        intersection = block_keywords.intersection(context_keywords)
        union = block_keywords.union(context_keywords)
        
        similarity = len(intersection) / len(union) if union else 0
        
        # Adjust score based on message type
        block_content = " ".join([msg.content.lower() for msg in block.messages])
        
        # Greetings/closings get lower alignment scores
        if any(kw in block_content for kw in self.greeting_keywords):
            similarity *= 0.7
        
        if any(kw in block_content for kw in self.closing_keywords):
            similarity *= 0.7
        
        # Error messages might have low keyword overlap but are relevant
        if any(kw in block_content for kw in self.error_keywords):
            similarity = max(similarity, 0.6)
        
        # Map similarity to score (0.3-0.9 range)
        return 0.3 + (similarity * 0.6)
    
    async def _evaluate_temporal_relevance(
        self,
        block: ConversationBlock,
        context: List[ConversationBlock],
    ) -> float:
        """Evaluate temporal relevance based on age and access patterns."""
        # Age-based scoring
        age = datetime.utcnow() - block.created_at
        
        if age < timedelta(minutes=5):
            age_score = 1.0
        elif age < timedelta(hours=1):
            age_score = 0.9
        elif age < timedelta(hours=6):
            age_score = 0.7
        elif age < timedelta(days=1):
            age_score = 0.5
        elif age < timedelta(days=7):
            age_score = 0.3
        else:
            age_score = 0.1
        
        # Access frequency scoring
        if block.access_count == 0:
            access_score = 0.5
        elif block.access_count < 3:
            access_score = 0.7
        elif block.access_count < 10:
            access_score = 0.9
        else:
            access_score = 1.0
        
        # Recent access bonus
        time_since_access = datetime.utcnow() - block.last_accessed
        if time_since_access < timedelta(minutes=30):
            recency_bonus = 0.2
        elif time_since_access < timedelta(hours=2):
            recency_bonus = 0.1
        else:
            recency_bonus = 0
        
        # Combine scores
        score = (age_score * 0.5) + (access_score * 0.3) + (recency_bonus * 0.2)
        
        # Boost score for messages with temporal references
        block_content = " ".join([msg.content.lower() for msg in block.messages])
        temporal_refs = [
            "today", "tomorrow", "yesterday", "now", "currently",
            "this week", "next", "last", "soon", "recently",
        ]
        
        if any(ref in block_content for ref in temporal_refs):
            score = min(1.0, score * 1.2)
        
        return score
    
    async def _evaluate_goal_contribution(
        self,
        block: ConversationBlock,
        context: List[ConversationBlock],
        goal: Optional[str] = None,
    ) -> float:
        """Evaluate goal contribution using pattern matching."""
        # Check if block contains a question
        block_content = " ".join([msg.content for msg in block.messages])
        is_question = any(
            re.search(pattern, block_content.lower())
            for pattern in self.question_patterns
        )
        
        # Check if block is an answer to a recent question
        is_answer = False
        recent_question = None
        
        for ctx_block in reversed(context[-5:]):
            ctx_content = " ".join([msg.content for msg in ctx_block.messages])
            if any(re.search(p, ctx_content.lower()) for p in self.question_patterns):
                recent_question = ctx_content
                break
        
        # If there was a recent question and this block follows it
        if recent_question and context and block.created_at > context[-1].created_at:
            # Check if this might be an answer
            if block.messages and block.messages[0].role == MessageRole.ASSISTANT:
                is_answer = True
        
        # Score based on role in conversation
        if is_question:
            return 0.9  # Questions drive conversation
        elif is_answer:
            return 0.95  # Answers are highly relevant
        elif goal and goal.lower() in block_content.lower():
            return 0.85  # Directly mentions goal
        else:
            # Check for task-oriented language
            task_keywords = [
                "need", "want", "help", "please", "could", "would",
                "should", "must", "have to", "try", "let's", "will",
            ]
            
            task_score = sum(
                1 for kw in task_keywords 
                if kw in block_content.lower()
            ) / len(task_keywords)
            
            return 0.5 + (task_score * 0.4)
    
    async def _evaluate_information_quality(
        self,
        block: ConversationBlock,
    ) -> float:
        """Evaluate information quality using heuristics."""
        block_content = " ".join([msg.content for msg in block.messages])
        
        # Length scoring
        word_count = len(block_content.split())
        
        if word_count < 3:
            length_score = 0.2
        elif word_count < 10:
            length_score = 0.5
        elif word_count < 50:
            length_score = 0.8
        elif word_count < 200:
            length_score = 1.0
        elif word_count < 500:
            length_score = 0.8
        else:
            length_score = 0.6
        
        # Check for filler content
        filler_count = sum(
            1 for phrase in self.filler_phrases
            if phrase in block_content.lower()
        )
        
        if filler_count >= 3:
            filler_penalty = 0.3
        elif filler_count >= 1:
            filler_penalty = 0.1
        else:
            filler_penalty = 0
        
        # Check for substantive content markers
        substance_markers = [
            # Explanatory
            "because", "therefore", "however", "although", "despite",
            # Specific
            "specifically", "particularly", "especially", "exactly",
            # Examples
            "for example", "such as", "like", "including",
            # Structured
            "first", "second", "finally", "step", "process",
        ]
        
        substance_score = sum(
            1 for marker in substance_markers
            if marker in block_content.lower()
        ) / len(substance_markers)
        
        # Check for code/technical content
        has_code = any(
            pattern in block_content
            for pattern in ["```", "def ", "class ", "function", "import", "return"]
        )
        
        technical_bonus = 0.2 if has_code else 0
        
        # Combine scores
        quality_score = (
            (length_score * 0.4) +
            (substance_score * 0.4) +
            (technical_bonus * 0.2) -
            filler_penalty
        )
        
        return max(0, min(1, quality_score))
    
    async def _evaluate_factual_consistency(
        self,
        block: ConversationBlock,
        context: List[ConversationBlock],
    ) -> float:
        """Evaluate factual consistency using simple checks."""
        if not context:
            return 0.9
        
        block_content = " ".join([msg.content.lower() for msg in block.messages])
        
        # Check for contradiction markers
        contradiction_markers = [
            "no, actually", "that's wrong", "incorrect",
            "not true", "false", "mistake", "error",
        ]
        
        has_contradiction = any(
            marker in block_content
            for marker in contradiction_markers
        )
        
        if has_contradiction:
            # Check if it's self-correction (good) or confusion (bad)
            if block.messages and block.messages[0].role == MessageRole.ASSISTANT:
                # Assistant correcting itself - this is good
                return 0.8
            else:
                # User correcting assistant - indicates inconsistency
                return 0.4
        
        # Check for error keywords
        if any(kw in block_content for kw in self.error_keywords):
            return 0.6
        
        # Check for confidence markers
        confidence_markers = [
            "definitely", "certainly", "absolutely", "clearly",
            "obviously", "without doubt", "for sure",
        ]
        
        uncertainty_markers = [
            "maybe", "perhaps", "possibly", "might be",
            "could be", "not sure", "uncertain", "unclear",
        ]
        
        confidence_count = sum(
            1 for marker in confidence_markers
            if marker in block_content
        )
        
        uncertainty_count = sum(
            1 for marker in uncertainty_markers
            if marker in block_content
        )
        
        # High uncertainty might indicate factual issues
        if uncertainty_count > confidence_count:
            return 0.7
        elif confidence_count > 0:
            return 0.95
        else:
            return 0.85
    
    def _extract_keywords(self, block: ConversationBlock) -> Set[str]:
        """Extract meaningful keywords from block."""
        content = " ".join([msg.content for msg in block.messages])
        
        # Simple tokenization and filtering
        words = re.findall(r'\b\w+\b', content.lower())
        
        # Filter out common words
        stopwords = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at",
            "to", "for", "of", "with", "by", "from", "is", "are",
            "was", "were", "be", "been", "being", "have", "has",
            "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "must", "shall", "can",
        }
        
        keywords = {
            word for word in words
            if len(word) > 2 and word not in stopwords
        }
        
        return keywords