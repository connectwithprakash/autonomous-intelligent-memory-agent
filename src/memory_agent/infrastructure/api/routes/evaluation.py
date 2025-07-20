"""Relevance evaluation routes."""

from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from structlog import get_logger

from memory_agent.core.entities import ConversationBlock, Message
from memory_agent.core.evaluation.service import relevance_service
from memory_agent.core.interfaces import MessageRole, RelevanceScore

logger = get_logger(__name__)
router = APIRouter()


class EvaluateBlockRequest(BaseModel):
    """Request to evaluate a conversation block."""
    
    block_id: str = Field(..., description="Block ID")
    messages: List[Dict[str, str]] = Field(..., description="Messages in the block")
    context_blocks: List[Dict] = Field(
        default_factory=list,
        description="Surrounding conversation blocks for context"
    )
    metadata: Optional[Dict] = Field(None, description="Additional metadata")


class EvaluateConversationRequest(BaseModel):
    """Request to evaluate an entire conversation."""
    
    session_id: str = Field(..., description="Session ID")
    blocks: List[Dict] = Field(..., description="Conversation blocks")
    threshold: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Relevance threshold"
    )


class EvaluationResponse(BaseModel):
    """Relevance evaluation response."""
    
    block_id: str
    overall_score: float
    decision: str
    explanation: str
    factors: Dict[str, float]


class ConversationEvaluationResponse(BaseModel):
    """Conversation evaluation response."""
    
    session_id: str
    total_blocks: int
    evaluations: List[EvaluationResponse]
    irrelevant_count: int
    suggestions: List[Dict]


@router.post(
    "/evaluate/block",
    response_model=EvaluationResponse,
    status_code=status.HTTP_200_OK,
)
async def evaluate_block(request: EvaluateBlockRequest) -> EvaluationResponse:
    """Evaluate relevance of a single conversation block."""
    try:
        # Create block from request
        messages = [
            Message(
                role=MessageRole[msg["role"].upper()],
                content=msg["content"],
            )
            for msg in request.messages
        ]
        
        block = ConversationBlock(
            block_id=request.block_id,
            messages=messages,
        )
        
        # Create context blocks
        context = []
        for ctx_data in request.context_blocks:
            ctx_messages = [
                Message(
                    role=MessageRole[msg["role"].upper()],
                    content=msg["content"],
                )
                for msg in ctx_data.get("messages", [])
            ]
            
            ctx_block = ConversationBlock(
                block_id=ctx_data.get("block_id", ""),
                messages=ctx_messages,
            )
            context.append(ctx_block)
        
        # Evaluate
        score = await relevance_service.evaluate_block(
            block,
            context,
            request.metadata,
        )
        
        return EvaluationResponse(
            block_id=block.block_id,
            overall_score=score.overall_score,
            decision=score.decision.value,
            explanation=score.explanation,
            factors={
                "semantic_alignment": score.factors.semantic_alignment,
                "temporal_relevance": score.factors.temporal_relevance,
                "goal_contribution": score.factors.goal_contribution,
                "information_quality": score.factors.information_quality,
                "factual_consistency": score.factors.factual_consistency,
            },
        )
        
    except Exception as e:
        logger.error("Failed to evaluate block", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation failed: {str(e)}",
        )


@router.post(
    "/evaluate/conversation",
    response_model=ConversationEvaluationResponse,
    status_code=status.HTTP_200_OK,
)
async def evaluate_conversation(
    request: EvaluateConversationRequest
) -> ConversationEvaluationResponse:
    """Evaluate relevance of an entire conversation."""
    try:
        # Create blocks from request
        blocks = []
        for block_data in request.blocks:
            messages = [
                Message(
                    role=MessageRole[msg["role"].upper()],
                    content=msg["content"],
                )
                for msg in block_data.get("messages", [])
            ]
            
            block = ConversationBlock(
                block_id=block_data.get("block_id", ""),
                messages=messages,
            )
            blocks.append(block)
        
        # Evaluate all blocks
        evaluated = await relevance_service.evaluate_conversation(blocks)
        
        # Find irrelevant blocks
        irrelevant = await relevance_service.find_irrelevant_blocks(
            blocks,
            threshold=request.threshold,
        )
        
        # Get suggestions
        suggestions = await relevance_service.suggest_corrections(blocks)
        
        # Build response
        evaluations = []
        for block, score in evaluated:
            evaluations.append(
                EvaluationResponse(
                    block_id=block.block_id,
                    overall_score=score.overall_score,
                    decision=score.decision.value,
                    explanation=score.explanation,
                    factors={
                        "semantic_alignment": score.factors.semantic_alignment,
                        "temporal_relevance": score.factors.temporal_relevance,
                        "goal_contribution": score.factors.goal_contribution,
                        "information_quality": score.factors.information_quality,
                        "factual_consistency": score.factors.factual_consistency,
                    },
                )
            )
        
        return ConversationEvaluationResponse(
            session_id=request.session_id,
            total_blocks=len(blocks),
            evaluations=evaluations,
            irrelevant_count=len(irrelevant),
            suggestions=suggestions,
        )
        
    except Exception as e:
        logger.error("Failed to evaluate conversation", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation failed: {str(e)}",
        )


@router.get(
    "/evaluate/stats",
    response_model=Dict,
    status_code=status.HTTP_200_OK,
)
async def get_evaluation_stats() -> Dict:
    """Get evaluation statistics."""
    evaluator = relevance_service.get_evaluator()
    
    if not evaluator:
        await relevance_service.initialize()
        evaluator = relevance_service.get_evaluator()
    
    return {
        "evaluator_type": type(evaluator).__name__ if evaluator else "None",
        "cache_size": len(relevance_service._evaluation_cache),
        "weights": evaluator.weights if evaluator else {},
    }


@router.post(
    "/evaluate/clear-cache",
    status_code=status.HTTP_200_OK,
)
async def clear_evaluation_cache() -> Dict[str, str]:
    """Clear the evaluation cache."""
    relevance_service.clear_cache()
    return {"message": "Evaluation cache cleared"}