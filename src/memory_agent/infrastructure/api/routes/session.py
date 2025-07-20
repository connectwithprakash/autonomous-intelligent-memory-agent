"""Session management routes."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from memory_agent.core.entities import Message
from memory_agent.core.interfaces import MessageRole

router = APIRouter()


class SessionInfo(BaseModel):
    """Session information."""
    
    session_id: str
    created_at: datetime
    last_activity: datetime
    message_count: int
    memory_usage_bytes: int
    status: str = "active"  # active, idle, archived


class MessageHistory(BaseModel):
    """Message history response."""
    
    session_id: str
    messages: List[Dict]
    total_count: int
    page: int
    page_size: int


class CreateSessionRequest(BaseModel):
    """Create session request."""
    
    session_id: Optional[str] = Field(
        None,
        description="Session ID (auto-generated if not provided)"
    )
    metadata: Optional[Dict[str, Any]] = None


class CreateSessionResponse(BaseModel):
    """Create session response."""
    
    session_id: str
    created_at: datetime


# In-memory session storage for now
sessions: Dict[str, SessionInfo] = {}
session_messages: Dict[str, List[Message]] = {}


@router.post(
    "/",
    response_model=CreateSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session(request: CreateSessionRequest) -> CreateSessionResponse:
    """Create a new session."""
    import uuid
    
    session_id = request.session_id or str(uuid.uuid4())
    
    if session_id in sessions:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Session {session_id} already exists",
        )
    
    now = datetime.utcnow()
    sessions[session_id] = SessionInfo(
        session_id=session_id,
        created_at=now,
        last_activity=now,
        message_count=0,
        memory_usage_bytes=0,
        status="active",
    )
    session_messages[session_id] = []
    
    return CreateSessionResponse(
        session_id=session_id,
        created_at=now,
    )


@router.get(
    "/{session_id}",
    response_model=SessionInfo,
    status_code=status.HTTP_200_OK,
)
async def get_session(session_id: str) -> SessionInfo:
    """Get session information."""
    if session_id not in sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )
    
    return sessions[session_id]


@router.get(
    "/",
    response_model=List[SessionInfo],
    status_code=status.HTTP_200_OK,
)
async def list_sessions(
    active_only: bool = Query(False, description="Only show active sessions"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> List[SessionInfo]:
    """List all sessions."""
    all_sessions = list(sessions.values())
    
    if active_only:
        all_sessions = [s for s in all_sessions if s.status == "active"]
    
    # Apply pagination
    return all_sessions[offset:offset + limit]


@router.get(
    "/{session_id}/messages",
    response_model=MessageHistory,
    status_code=status.HTTP_200_OK,
)
async def get_message_history(
    session_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> MessageHistory:
    """Get message history for a session."""
    if session_id not in sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )
    
    messages = session_messages.get(session_id, [])
    total_count = len(messages)
    
    # Apply pagination
    start = (page - 1) * page_size
    end = start + page_size
    page_messages = messages[start:end]
    
    return MessageHistory(
        session_id=session_id,
        messages=[msg.to_dict() for msg in page_messages],
        total_count=total_count,
        page=page,
        page_size=page_size,
    )


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_session(session_id: str) -> None:
    """Delete a session."""
    if session_id not in sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )
    
    del sessions[session_id]
    if session_id in session_messages:
        del session_messages[session_id]


@router.post(
    "/{session_id}/archive",
    status_code=status.HTTP_200_OK,
)
async def archive_session(session_id: str) -> Dict[str, str]:
    """Archive a session."""
    if session_id not in sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )
    
    sessions[session_id].status = "archived"
    
    return {"message": f"Session {session_id} archived"}