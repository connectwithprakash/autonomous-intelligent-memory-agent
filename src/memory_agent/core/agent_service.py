"""Memory agent service for managing agent instances."""

from typing import Dict, Optional

from structlog import get_logger

from memory_agent.core.agent import MemoryAgent
from memory_agent.core.interfaces import CompletionOptions
from memory_agent.infrastructure.config.settings import settings

logger = get_logger(__name__)


class MemoryAgentService:
    """Service for managing memory agent instances."""
    
    def __init__(self):
        """Initialize agent service."""
        self._agents: Dict[str, MemoryAgent] = {}
        self._default_agent: Optional[MemoryAgent] = None
    
    async def initialize(self) -> None:
        """Initialize the service with default agent."""
        # Create default agent
        self._default_agent = MemoryAgent(
            agent_id="default",
            enable_self_correction=getattr(settings, "enable_self_correction", True),
            correction_threshold=settings.relevance_threshold,
            hot_capacity=getattr(settings, "hot_memory_capacity", 100),
            warm_capacity=getattr(settings, "warm_memory_capacity", 500),
            cold_capacity=getattr(settings, "cold_memory_capacity", 2000),
        )
        
        await self._default_agent.initialize()
        self._agents["default"] = self._default_agent
        
        logger.info("Initialized memory agent service")
    
    async def get_agent(self, agent_id: str = "default") -> MemoryAgent:
        """Get or create an agent instance.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Memory agent instance
        """
        if agent_id not in self._agents:
            # Create new agent
            agent = MemoryAgent(
                agent_id=agent_id,
                enable_self_correction=getattr(settings, "enable_self_correction", True),
                correction_threshold=settings.relevance_threshold,
            )
            
            await agent.initialize()
            self._agents[agent_id] = agent
            
            logger.info(
                "Created new memory agent",
                agent_id=agent_id,
            )
        
        return self._agents[agent_id]
    
    async def process_message(
        self,
        content: str,
        session_id: str,
        agent_id: str = "default",
        options: Optional[CompletionOptions] = None,
    ) -> str:
        """Process a message using the specified agent.
        
        Args:
            content: User message content
            session_id: Session identifier
            agent_id: Agent to use
            options: Completion options
            
        Returns:
            Agent response
        """
        agent = await self.get_agent(agent_id)
        return await agent.process_message(content, session_id, options)
    
    async def get_conversation_history(
        self,
        session_id: str,
        agent_id: str = "default",
        limit: int = 50,
    ) -> list:
        """Get conversation history.
        
        Args:
            session_id: Session identifier
            agent_id: Agent to query
            limit: Max blocks to return
            
        Returns:
            List of conversation blocks
        """
        agent = await self.get_agent(agent_id)
        return await agent.get_conversation_history(session_id, limit)
    
    async def clear_session(
        self,
        session_id: str,
        agent_id: str = "default",
    ) -> None:
        """Clear session memory.
        
        Args:
            session_id: Session to clear
            agent_id: Agent to use
        """
        agent = await self.get_agent(agent_id)
        await agent.clear_session(session_id)
    
    async def optimize_memory(
        self,
        agent_id: str = "default",
    ) -> Dict[str, int]:
        """Optimize agent memory.
        
        Args:
            agent_id: Agent to optimize
            
        Returns:
            Optimization statistics
        """
        agent = await self.get_agent(agent_id)
        return await agent.optimize_memory()
    
    async def get_stats(self) -> Dict:
        """Get statistics for all agents.
        
        Returns:
            Combined statistics
        """
        stats = {
            "agent_count": len(self._agents),
            "agents": {},
        }
        
        for agent_id, agent in self._agents.items():
            stats["agents"][agent_id] = await agent.get_memory_stats()
        
        return stats
    
    async def shutdown(self) -> None:
        """Shutdown all agents."""
        for agent in self._agents.values():
            await agent.shutdown()
        
        self._agents.clear()
        self._default_agent = None
        
        logger.info("Shutdown memory agent service")


# Global agent service instance
agent_service = MemoryAgentService()