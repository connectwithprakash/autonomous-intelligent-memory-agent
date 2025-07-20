"""Storage manager for coordinating memory tiers."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from structlog import get_logger

from memory_agent.core.entities import ConversationBlock
from memory_agent.core.evaluation.service import relevance_service
from memory_agent.core.interfaces import (
    Decision,
    IStorage,
    IStorageManager,
    StorageTier,
)
from memory_agent.infrastructure.storage.memory_store import InMemoryStore

logger = get_logger(__name__)


class MemoryStorageManager(IStorageManager):
    """Manager for tiered memory storage."""
    
    def __init__(
        self,
        hot_capacity: int = 100,
        warm_capacity: int = 500,
        cold_capacity: int = 2000,
        relevance_threshold: float = 0.4,
        promotion_threshold: float = 0.7,
    ):
        """Initialize memory storage manager.
        
        Args:
            hot_capacity: Max blocks in hot tier
            warm_capacity: Max blocks in warm tier  
            cold_capacity: Max blocks in cold tier
            relevance_threshold: Min relevance to keep in memory
            promotion_threshold: Min relevance to promote tier
        """
        self.relevance_threshold = relevance_threshold
        self.promotion_threshold = promotion_threshold
        
        # Single in-memory store handles all tiers
        self._store = InMemoryStore(
            hot_capacity=hot_capacity,
            warm_capacity=warm_capacity,
            cold_capacity=cold_capacity,
        )
        
        # Track tier assignments
        self._tier_assignments: Dict[str, StorageTier] = {}
        
        # Migration statistics
        self._migration_stats = {
            "promotions": 0,
            "demotions": 0,
            "evictions": 0,
        }
    
    async def initialize(self) -> None:
        """Initialize the storage manager."""
        await self._store.initialize()
        logger.info(
            "Initialized memory storage manager",
            relevance_threshold=self.relevance_threshold,
            promotion_threshold=self.promotion_threshold,
        )
    
    async def store_block(
        self,
        block: ConversationBlock,
        tier: Optional[StorageTier] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """Store a conversation block."""
        # Determine tier if not specified
        if not tier:
            tier = await self._determine_tier(block)
        
        # Store in the appropriate tier
        metadata = {"session_id": session_id or "default"}
        await self._store.store(block.block_id, block, tier, metadata)
        self._tier_assignments[block.block_id] = tier
        
        logger.debug(
            "Stored block",
            block_id=block.block_id,
            tier=tier.value,
            relevance=block.relevance_score,
        )
    
    async def retrieve_block(
        self,
        block_id: str,
        session_id: Optional[str] = None,
    ) -> Optional[ConversationBlock]:
        """Retrieve a conversation block."""
        metadata = {"session_id": session_id or "default"}
        block = await self._store.retrieve(block_id, metadata)
        
        if block:
            # Check if block should be promoted based on access
            current_tier = self._tier_assignments.get(block_id)
            if current_tier and current_tier != StorageTier.HOT:
                if block.access_count > 5 or block.relevance_score > self.promotion_threshold:
                    await self._promote_block(block, current_tier, session_id)
        
        return block
    
    async def delete_block(
        self,
        block_id: str,
        session_id: Optional[str] = None,
    ) -> bool:
        """Delete a conversation block."""
        metadata = {"session_id": session_id or "default"}
        success = await self._store.delete(block_id, metadata)
        
        if success:
            self._tier_assignments.pop(block_id, None)
            self._migration_stats["evictions"] += 1
        
        return success
    
    async def list_blocks(
        self,
        tier: Optional[StorageTier] = None,
        session_id: Optional[str] = None,
    ) -> List[str]:
        """List blocks in storage."""
        metadata = {"session_id": session_id} if session_id else None
        all_keys = await self._store.list_keys(metadata=metadata)
        
        if tier:
            # Filter by tier
            return [
                key for key in all_keys
                if self._tier_assignments.get(key) == tier
            ]
        
        return all_keys
    
    async def migrate_tier(
        self,
        block_id: str,
        to_tier: StorageTier,
        session_id: Optional[str] = None,
    ) -> bool:
        """Migrate a block to a different tier."""
        # Retrieve the block
        block = await self.retrieve_block(block_id, session_id)
        if not block:
            return False
        
        # Delete from current location
        await self.delete_block(block_id, session_id)
        
        # Store in new tier
        await self.store_block(block, to_tier, session_id)
        
        # Update stats
        current_tier = self._tier_assignments.get(block_id)
        if current_tier:
            if to_tier.value < current_tier.value:  # Promotion
                self._migration_stats["promotions"] += 1
            else:  # Demotion
                self._migration_stats["demotions"] += 1
        
        logger.info(
            "Migrated block between tiers",
            block_id=block_id,
            from_tier=current_tier.value if current_tier else None,
            to_tier=to_tier.value,
        )
        
        return True
    
    async def cleanup_irrelevant(
        self,
        session_id: Optional[str] = None,
        context_window: int = 10,
    ) -> List[str]:
        """Remove irrelevant blocks from memory."""
        removed = []
        
        # Get all blocks for the session
        block_ids = await self.list_blocks(session_id=session_id)
        
        # Retrieve and evaluate blocks in batches
        blocks: List[ConversationBlock] = []
        for block_id in block_ids:
            block = await self.retrieve_block(block_id, session_id)
            if block:
                blocks.append(block)
        
        # Evaluate relevance
        if blocks:
            irrelevant = await relevance_service.find_irrelevant_blocks(
                blocks,
                threshold=self.relevance_threshold,
            )
            
            # Remove irrelevant blocks
            for block, score in irrelevant:
                if score.decision == Decision.REMOVE:
                    success = await self.delete_block(block.block_id, session_id)
                    if success:
                        removed.append(block.block_id)
                        logger.info(
                            "Removed irrelevant block",
                            block_id=block.block_id,
                            score=score.overall_score,
                            reason=score.explanation,
                        )
        
        return removed
    
    async def optimize_storage(self) -> Dict[str, int]:
        """Optimize storage by migrating blocks between tiers."""
        migrations = {
            "promoted": 0,
            "demoted": 0,
            "removed": 0,
        }
        
        # Check all blocks
        all_blocks = []
        for block_id in await self.list_blocks():
            block = await self.retrieve_block(block_id)
            if block:
                all_blocks.append(block)
        
        # Evaluate and migrate based on access patterns and age
        now = datetime.utcnow()
        
        for block in all_blocks:
            current_tier = self._tier_assignments.get(block.block_id, StorageTier.HOT)
            age = now - block.created_at
            
            # Determine optimal tier
            if block.relevance_score < self.relevance_threshold:
                # Remove low relevance blocks
                await self.delete_block(block.block_id)
                migrations["removed"] += 1
                
            elif age > timedelta(hours=24) and current_tier == StorageTier.HOT:
                # Demote old blocks from hot tier
                await self.migrate_tier(block.block_id, StorageTier.WARM)
                migrations["demoted"] += 1
                
            elif age > timedelta(days=3) and current_tier == StorageTier.WARM:
                # Demote very old blocks to cold tier
                await self.migrate_tier(block.block_id, StorageTier.COLD)
                migrations["demoted"] += 1
                
            elif block.access_count > 10 and current_tier != StorageTier.HOT:
                # Promote frequently accessed blocks
                await self.migrate_tier(block.block_id, StorageTier.HOT)
                migrations["promoted"] += 1
        
        logger.info(
            "Optimized storage",
            **migrations,
        )
        
        return migrations
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        base_stats = await self._store.get_stats()
        
        return {
            **base_stats,
            "migration_stats": self._migration_stats,
            "tier_assignments": len(self._tier_assignments),
        }
    
    async def _determine_tier(self, block: ConversationBlock) -> StorageTier:
        """Determine appropriate storage tier for a block."""
        # New blocks with high relevance go to hot tier
        if block.relevance_score > self.promotion_threshold:
            return StorageTier.HOT
        
        # Medium relevance goes to warm tier
        elif block.relevance_score > self.relevance_threshold:
            return StorageTier.WARM
        
        # Low relevance goes to cold tier
        else:
            return StorageTier.COLD
    
    async def _promote_block(
        self,
        block: ConversationBlock,
        from_tier: StorageTier,
        session_id: Optional[str] = None,
    ) -> None:
        """Promote a block to a higher tier."""
        # Determine target tier
        if from_tier == StorageTier.COLD:
            to_tier = StorageTier.WARM
        else:  # WARM -> HOT
            to_tier = StorageTier.HOT
        
        await self.migrate_tier(block.block_id, to_tier, session_id)
    
    def get_storage(self, tier: StorageTier) -> IStorage:
        """Get storage for a specific tier."""
        # All tiers use the same in-memory store
        return self._store
    
    async def shutdown(self) -> None:
        """Shutdown the storage manager."""
        await self._store.shutdown()
        logger.info(
            "Shutdown memory storage manager",
            final_stats=self._migration_stats,
        )