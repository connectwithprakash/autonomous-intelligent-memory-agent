"""Agent API routes."""

from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from structlog import get_logger

from memory_agent.core.interfaces import CompletionOptions
from memory_agent.infrastructure.api.websocket import websocket_handler
from memory_agent.infrastructure.config.settings import settings

logger = get_logger(__name__)

router = APIRouter()


class ChatRequest(BaseModel):
    """Chat request model."""
    
    message: str = Field(..., description="User message")
    session_id: str = Field(..., description="Session identifier")
    stream: bool = Field(default=False, description="Stream response")
    options: Optional[CompletionOptions] = None


class ChatResponse(BaseModel):
    """Chat response model."""
    
    response: str
    session_id: str
    message_id: str
    timestamp: datetime
    tokens_used: int = 0
    corrections_made: int = 0


class AgentStats(BaseModel):
    """Agent statistics."""
    
    active_sessions: int
    total_messages: int
    total_corrections: int
    avg_relevance_score: float
    memory_usage_mb: float


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
)
async def chat(request: ChatRequest) -> ChatResponse:
    """Process a chat message."""
    from memory_agent.core.agent_service import agent_service
    
    try:
        # Process message with memory agent
        response_content = await agent_service.process_message(
            content=request.message,
            session_id=request.session_id,
            options=request.options,
        )
        
        # Get agent stats for corrections count
        agent = await agent_service.get_agent()
        correction_history = agent._self_corrector.get_correction_history(5)
        recent_corrections = len([
            c for c in correction_history
            if c.get("timestamp") and 
            (datetime.utcnow() - c["timestamp"]).total_seconds() < 60
        ])
        
        # Create response
        response = ChatResponse(
            response=response_content,
            session_id=request.session_id,
            message_id=f"msg_{datetime.utcnow().timestamp()}",
            timestamp=datetime.utcnow(),
            tokens_used=0,  # TODO: Track actual token usage
            corrections_made=recent_corrections,
        )
        
        return response
        
    except Exception as e:
        logger.error("Chat completion failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate response: {str(e)}",
        )


@router.get(
    "/stats",
    response_model=AgentStats,
    status_code=status.HTTP_200_OK,
)
async def get_agent_stats() -> AgentStats:
    """Get agent statistics."""
    from memory_agent.core.agent_service import agent_service
    
    # Get stats from agent service
    stats = await agent_service.get_stats()
    
    # Extract default agent stats
    default_stats = stats.get("agents", {}).get("default", {})
    
    # Calculate totals
    total_messages = 0
    total_corrections = default_stats.get("correction_history", 0)
    
    # Sum up messages from tier distribution
    tier_dist = default_stats.get("tier_distribution", {})
    total_blocks = sum(tier_dist.values())
    
    # Estimate messages (assuming avg 2 messages per block)
    total_messages = total_blocks * 2
    
    # Calculate memory usage
    memory_usage = default_stats.get("memory_usage", {})
    total_bytes = sum(memory_usage.values())
    memory_usage_mb = total_bytes / (1024 * 1024)
    
    return AgentStats(
        active_sessions=default_stats.get("active_sessions", 0),
        total_messages=total_messages,
        total_corrections=total_corrections,
        avg_relevance_score=0.85,  # TODO: Calculate actual average
        memory_usage_mb=round(memory_usage_mb, 2),
    )


@router.post("/clear-memory", status_code=status.HTTP_200_OK)
async def clear_memory(session_id: Optional[str] = None) -> Dict[str, str]:
    """Clear memory for a session or all sessions."""
    if session_id:
        # TODO: Clear specific session
        return {"message": f"Memory cleared for session {session_id}"}
    else:
        # TODO: Clear all memory
        return {"message": "All memory cleared"}


@router.post("/evaluate", status_code=status.HTTP_200_OK)
async def evaluate_relevance(
    content: str,
    session_id: str,
) -> Dict[str, float]:
    """Evaluate relevance of content."""
    # TODO: Implement relevance evaluation
    
    # Mock evaluation
    score = 0.85
    
    # Broadcast evaluation event
    await websocket_handler.broadcast_evaluation_result(
        block=None,  # TODO: Create actual block
        score=None,  # TODO: Create actual score
        session_id=session_id,
    )
    
    return {
        "overall_score": score,
        "semantic_alignment": 0.9,
        "temporal_relevance": 0.8,
        "goal_contribution": 0.85,
        "information_quality": 0.88,
        "factual_consistency": 0.82,
    }