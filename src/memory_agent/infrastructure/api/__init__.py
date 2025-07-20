"""API infrastructure module."""

from memory_agent.infrastructure.api.app import app, create_app

__all__ = [
    "app",
    "create_app",
]