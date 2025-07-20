"""Main memory agent implementation."""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from structlog import get_logger

from memory_agent.core.correction.self_corrector import SelfCorrector
from memory_agent.core.entities import ConversationBlock, Message, MessageChain
from memory_agent.core.evaluation.service import relevance_service
from memory_agent.core.interfaces import (
    CompletionOptions,
    ILLMProvider,
    IMemoryAgent,
    MessageRole,
    StorageTier,
)
from memory_agent.infrastructure.api.websocket import websocket_handler
from memory_agent.infrastructure.llm.service import llm_service
from memory_agent.infrastructure.storage.manager import MemoryStorageManager

logger = get_logger(__name__)


class MemoryAgent(IMemoryAgent):
    """Autonomous AI agent with memory management and self-correction."""
    
    def __init__(
        self,
        agent_id: str = None,
        enable_self_correction: bool = True,
        correction_threshold: float = 0.4,
        hot_capacity: int = 100,
        warm_capacity: int = 500,
        cold_capacity: int = 2000,
    ):
        """Initialize memory agent.
        
        Args:
            agent_id: Unique agent identifier
            enable_self_correction: Enable autonomous correction
            correction_threshold: Relevance threshold for corrections
            hot_capacity: Max blocks in hot memory tier
            warm_capacity: Max blocks in warm memory tier
            cold_capacity: Max blocks in cold memory tier
        """
        self.agent_id = agent_id or str(uuid.uuid4())
        self.enable_self_correction = enable_self_correction
        
        # Initialize components
        self._message_chains: Dict[str, MessageChain] = {}
        self._storage_manager = MemoryStorageManager(
            hot_capacity=hot_capacity,
            warm_capacity=warm_capacity,
            cold_capacity=cold_capacity,
            relevance_threshold=correction_threshold,
        )
        
        self._self_corrector = SelfCorrector(
            storage_manager=self._storage_manager,
            correction_threshold=correction_threshold,
            enable_auto_correction=enable_self_correction,
        )
        
        self._active_sessions: Dict[str, Dict] = {}
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the agent."""
        if self._initialized:
            return
        
        # Initialize services
        await llm_service.initialize()
        await relevance_service.initialize()
        await self._storage_manager.initialize()
        
        # Start self-correction if enabled
        if self.enable_self_correction:
            await self._self_corrector.start()
        
        self._initialized = True
        logger.info(
            "Initialized memory agent",
            agent_id=self.agent_id,
            self_correction=self.enable_self_correction,
        )
    
    async def process_message(
        self,
        content: str,
        session_id: str,
        options: Optional[CompletionOptions] = None,
    ) -> str:
        """Process a user message and generate response."""
        if not self._initialized:
            await self.initialize()
        
        # Create user message
        user_message = Message(
            role=MessageRole.USER,
            content=content,
            timestamp=datetime.utcnow(),
        )
        
        # Get or create message chain
        if session_id not in self._message_chains:
            self._message_chains[session_id] = MessageChain()
        
        chain = self._message_chains[session_id]
        await chain.add_message(user_message, session_id)
        
        # Create conversation block
        sequence_num = len(await self._storage_manager.list_blocks(session_id=session_id))
        user_block = ConversationBlock(
            block_id=f"{session_id}_{uuid.uuid4().hex[:8]}",
            sequence_number=sequence_num,
            session_id=session_id,
            content=user_message.content,
            source="user",
            message_id=user_message.id,
            relevance_score=1.0,  # User messages always relevant
        )
        
        # Store in hot tier
        await self._storage_manager.store_block(
            user_block,
            StorageTier.HOT,
            session_id,
        )
        
        # Broadcast message event
        await websocket_handler.broadcast_message_added(
            message=user_message,
            session_id=session_id,
        )
        
        # Build context from memory
        context_messages = await self._build_context(session_id, chain)
        
        # Generate response
        response_content = await self._generate_response(
            context_messages,
            options,
        )
        
        # Create assistant message
        assistant_message = Message(
            role=MessageRole.ASSISTANT,
            content=response_content,
            timestamp=datetime.utcnow(),
        )
        
        await chain.add_message(assistant_message, session_id)
        
        # Create and store assistant block
        sequence_num = len(await self._storage_manager.list_blocks(session_id=session_id))
        assistant_block = ConversationBlock(
            block_id=f"{session_id}_{uuid.uuid4().hex[:8]}",
            sequence_number=sequence_num,
            session_id=session_id,
            content=assistant_message.content,
            source="agent",
            message_id=assistant_message.id,
            relevance_score=0.9,  # Assistant messages initially high relevance
        )
        
        await self._storage_manager.store_block(
            assistant_block,
            StorageTier.HOT,
            session_id,
        )
        
        # Broadcast response
        await websocket_handler.broadcast_message_added(
            message=assistant_message,
            session_id=session_id,
        )
        
        # Trigger self-correction check
        if self.enable_self_correction:
            asyncio.create_task(self._check_for_corrections(session_id))
        
        # Update session activity
        self._update_session_activity(session_id)
        
        return response_content
    
    async def _build_context(
        self,
        session_id: str,
        chain: MessageChain,
    ) -> List[Message]:
        """Build context from memory and message chain."""
        context_messages = []
        
        # Get recent blocks from storage
        block_ids = await self._storage_manager.list_blocks(
            tier=StorageTier.HOT,
            session_id=session_id,
        )
        
        # Retrieve recent relevant blocks
        recent_blocks = []
        for block_id in block_ids[-20:]:  # Last 20 blocks
            block = await self._storage_manager.retrieve_block(block_id, session_id)
            if block and block.relevance_score > 0.5:
                recent_blocks.append(block)
        
        # Extract messages from blocks and reconstruct
        for block in recent_blocks[-10:]:  # Use last 10 relevant blocks
            # Reconstruct message from block
            role = MessageRole.USER if block.source == "user" else MessageRole.ASSISTANT
            msg = Message(
                id=block.message_id,
                role=role,
                content=block.content,
                timestamp=block.timestamp,
            )
            context_messages.append(msg)
        
        # Add system message if needed
        if not any(msg.role == MessageRole.SYSTEM for msg in context_messages):
            system_msg = Message(
                role=MessageRole.SYSTEM,
                content="You are a helpful AI assistant with memory management capabilities. Provide accurate and relevant responses.",
            )
            context_messages.insert(0, system_msg)
        
        return context_messages
    
    async def _generate_response(
        self,
        messages: List[Message],
        options: Optional[CompletionOptions] = None,
    ) -> str:
        """Generate response using LLM."""
        try:
            response = await llm_service.complete(messages, options)
            return response.content
        except Exception as e:
            logger.error(
                "Failed to generate response",
                error=str(e),
            )
            return "I apologize, but I encountered an error generating a response. Please try again."
    
    async def _check_for_corrections(self, session_id: str) -> None:
        """Check if recent messages need correction."""
        try:
            # Brief delay to let messages settle
            await asyncio.sleep(2)
            
            # Analyze recent conversation
            problematic = await self._self_corrector.analyze_conversation(
                session_id,
                window_size=5,
            )
            
            if problematic:
                logger.info(
                    "Found issues in conversation",
                    session_id=session_id,
                    issue_count=len(problematic),
                )
                
                # Apply corrections
                corrections = await self._self_corrector.correct_conversation(
                    session_id,
                    problematic,
                )
                
                if corrections:
                    # Notify about corrections
                    await websocket_handler.broadcast_correction_event(
                        session_id=session_id,
                        correction_count=len(corrections),
                    )
                    
        except Exception as e:
            logger.error(
                "Error checking for corrections",
                session_id=session_id,
                error=str(e),
            )
    
    async def get_conversation_history(
        self,
        session_id: str,
        limit: int = 50,
    ) -> List[ConversationBlock]:
        """Get conversation history from memory."""
        blocks = []
        
        # Get all blocks for session
        block_ids = await self._storage_manager.list_blocks(session_id=session_id)
        
        # Retrieve blocks
        for block_id in block_ids[-limit:]:
            block = await self._storage_manager.retrieve_block(block_id, session_id)
            if block:
                blocks.append(block)
        
        return blocks
    
    async def clear_session(self, session_id: str) -> None:
        """Clear all memory for a session."""
        # Get all blocks
        block_ids = await self._storage_manager.list_blocks(session_id=session_id)
        
        # Delete each block
        for block_id in block_ids:
            await self._storage_manager.delete_block(block_id, session_id)
        
        # Clear message chain
        if session_id in self._message_chains:
            del self._message_chains[session_id]
        
        # Clear session data
        if session_id in self._active_sessions:
            del self._active_sessions[session_id]
        
        logger.info(
            "Cleared session memory",
            session_id=session_id,
            blocks_removed=len(block_ids),
        )
    
    async def optimize_memory(self) -> Dict[str, int]:
        """Optimize memory storage."""
        return await self._storage_manager.optimize_storage()
    
    async def get_memory_stats(self) -> Dict:
        """Get memory statistics."""
        storage_stats = await self._storage_manager.get_stats()
        
        return {
            "agent_id": self.agent_id,
            "active_sessions": len(self._active_sessions),
            "message_chains": len(self._message_chains),
            "self_correction_enabled": self.enable_self_correction,
            "correction_history": len(self._self_corrector.get_correction_history()),
            **storage_stats,
        }
    
    def _update_session_activity(self, session_id: str) -> None:
        """Update session activity tracking."""
        if session_id not in self._active_sessions:
            self._active_sessions[session_id] = {
                "created_at": datetime.utcnow(),
                "message_count": 0,
            }
        
        session = self._active_sessions[session_id]
        session["last_activity"] = datetime.utcnow()
        session["message_count"] += 1
    
    async def shutdown(self) -> None:
        """Shutdown the agent."""
        if self._initialized:
            await self._self_corrector.stop()
            await self._storage_manager.shutdown()
            self._initialized = False
            
            logger.info(
                "Shutdown memory agent",
                agent_id=self.agent_id,
            )