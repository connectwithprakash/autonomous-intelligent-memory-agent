"""API routes module."""

from memory_agent.infrastructure.api.routes.agent import router as agent_router
from memory_agent.infrastructure.api.routes.evaluation import router as evaluation_router
from memory_agent.infrastructure.api.routes.health import router as health_router
from memory_agent.infrastructure.api.routes.llm import router as llm_router
from memory_agent.infrastructure.api.routes.memory import router as memory_router
from memory_agent.infrastructure.api.routes.session import router as session_router

__all__ = [
    "agent_router",
    "evaluation_router",
    "health_router",
    "llm_router",
    "memory_router",
    "session_router",
]