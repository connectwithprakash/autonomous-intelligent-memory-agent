"""Main FastAPI application."""

from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from structlog import get_logger

from memory_agent.infrastructure.api.routes import (
    agent_router,
    evaluation_router,
    health_router,
    llm_router,
    memory_router,
    session_router,
)
from memory_agent.infrastructure.api.websocket import websocket_handler
from memory_agent.infrastructure.config.settings import settings

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info(
        "Starting Memory Agent API",
        version=settings.app_version,
        debug=settings.debug,
    )
    
    # Initialize components
    from memory_agent.infrastructure.llm.service import llm_service
    from memory_agent.core.evaluation.service import relevance_service
    from memory_agent.core.agent_service import agent_service
    
    await llm_service.initialize()
    await relevance_service.initialize()
    await agent_service.initialize()
    
    yield
    
    # Shutdown
    logger.info("Shutting down Memory Agent API")
    
    # Cleanup
    await websocket_handler.manager.close_all_connections()
    from memory_agent.infrastructure.llm.service import llm_service
    from memory_agent.core.agent_service import agent_service
    await llm_service.shutdown()
    await agent_service.shutdown()


def create_app() -> FastAPI:
    """Create the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Handle all unhandled exceptions."""
        logger.error(
            "Unhandled exception",
            exc_info=exc,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal server error",
                "type": "internal_error",
            },
        )
    
    # Add routes
    app.include_router(health_router, tags=["health"])
    app.include_router(
        agent_router,
        prefix=f"{settings.api_prefix}/agent",
        tags=["agent"],
    )
    app.include_router(
        session_router,
        prefix=f"{settings.api_prefix}/sessions",
        tags=["sessions"],
    )
    app.include_router(
        memory_router,
        prefix=f"{settings.api_prefix}/memory",
        tags=["memory"],
    )
    app.include_router(
        llm_router,
        prefix=f"{settings.api_prefix}/llm",
        tags=["llm"],
    )
    app.include_router(
        evaluation_router,
        prefix=f"{settings.api_prefix}/evaluation",
        tags=["evaluation"],
    )
    
    # Add WebSocket endpoint
    @app.websocket("/ws/{client_id}")
    async def websocket_endpoint(websocket, client_id: str):
        """WebSocket endpoint for real-time updates."""
        await websocket_handler.handle_connection(
            websocket=websocket,
            client_id=client_id,
        )
    
    # Root endpoint
    @app.get("/")
    async def root() -> Dict[str, Any]:
        """Root endpoint."""
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "status": "running",
            "docs": "/docs",
            "health": "/health",
            "api": settings.api_prefix,
            "websocket": "/ws/{client_id}",
        }
    
    return app


# Create the app instance
app = create_app()