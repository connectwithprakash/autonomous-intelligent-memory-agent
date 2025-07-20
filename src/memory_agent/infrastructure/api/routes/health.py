"""Health check routes."""

from datetime import datetime
from typing import Dict

from fastapi import APIRouter, status
from pydantic import BaseModel

from memory_agent.infrastructure.api.websocket import connection_manager
from memory_agent.infrastructure.config.settings import settings

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str
    timestamp: datetime
    version: str
    services: Dict[str, bool]
    stats: Dict[str, int]


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
)
async def health_check() -> HealthResponse:
    """Check application health."""
    # Check service availability
    services = {
        "api": True,
        "websocket": True,
        "redis": False,  # TODO: Check Redis connection
        "postgres": False,  # TODO: Check PostgreSQL connection
    }
    
    # Get connection stats
    stats = connection_manager.get_connection_stats()
    
    return HealthResponse(
        status="healthy" if all(services.values()) else "degraded",
        timestamp=datetime.utcnow(),
        version=settings.app_version,
        services=services,
        stats=stats,
    )


@router.get("/health/live", status_code=status.HTTP_200_OK)
async def liveness_probe() -> Dict[str, str]:
    """Kubernetes liveness probe."""
    return {"status": "alive"}


@router.get("/health/ready", status_code=status.HTTP_200_OK)
async def readiness_probe() -> Dict[str, str]:
    """Kubernetes readiness probe."""
    # TODO: Check if all services are ready
    return {"status": "ready"}