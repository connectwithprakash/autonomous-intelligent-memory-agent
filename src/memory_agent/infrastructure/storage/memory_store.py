"""In-memory storage implementation with tiered management."""

import asyncio
import gzip
import json
from collections import OrderedDict, defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from structlog import get_logger

from memory_agent.core.entities import ConversationBlock, Message
from memory_agent.core.interfaces import IStorage, StorageTier

logger = get_logger(__name__)


class InMemoryStore(IStorage):
    """In-memory storage with tier management."""
    
    def __init__(
        self,
        hot_capacity: int = 100,
        warm_capacity: int = 500,
        cold_capacity: int = 2000,
        compression_threshold: int = 1024,  # bytes
    ):
        """Initialize in-memory store.
        
        Args:
            hot_capacity: Max blocks in hot tier
            warm_capacity: Max blocks in warm tier
            cold_capacity: Max blocks in cold tier
            compression_threshold: Min size for compression
        """
        self.hot_capacity = hot_capacity
        self.warm_capacity = warm_capacity
        self.cold_capacity = cold_capacity
        self.compression_threshold = compression_threshold
        
        # Storage tiers - using OrderedDict for LRU behavior
        self._hot_store: OrderedDict[str, ConversationBlock] = OrderedDict()
        self._warm_store: OrderedDict[str, Tuple[bytes, Dict]] = OrderedDict()  # compressed data + metadata
        self._cold_store: OrderedDict[str, Dict] = OrderedDict()  # summaries only
        
        # Indexes for fast lookup
        self._session_index: Dict[str, Set[str]] = defaultdict(set)
        self._tier_index: Dict[str, StorageTier] = {}
        
        # Statistics
        self._stats = {
            "total_stored": 0,
            "total_retrieved": 0,
            "total_compressed": 0,
            "total_evicted": 0,
            "bytes_saved": 0,
        }
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def initialize(self) -> None:
        """Initialize the storage."""
        self._running = True
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        logger.info(
            "Initialized in-memory store",
            hot_capacity=self.hot_capacity,
            warm_capacity=self.warm_capacity,
            cold_capacity=self.cold_capacity,
        )
    
    async def store(
        self,
        key: str,
        value: ConversationBlock,
        tier: StorageTier = StorageTier.HOT,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Store a conversation block."""
        metadata = metadata or {}
        session_id = metadata.get("session_id", "default")
        
        # Add to appropriate tier
        if tier == StorageTier.HOT:
            await self._store_hot(key, value, session_id)
        elif tier == StorageTier.WARM:
            await self._store_warm(key, value, session_id)
        else:  # COLD
            await self._store_cold(key, value, session_id)
        
        # Update indexes
        self._session_index[session_id].add(key)
        self._tier_index[key] = tier
        self._stats["total_stored"] += 1
    
    async def _store_hot(self, key: str, value: ConversationBlock, session_id: str) -> None:
        """Store in hot tier."""
        # Check capacity
        if len(self._hot_store) >= self.hot_capacity:
            # Evict oldest to warm tier
            oldest_key, oldest_value = self._hot_store.popitem(last=False)
            await self._store_warm(oldest_key, oldest_value, session_id)
            logger.debug(
                "Evicted from hot to warm tier",
                key=oldest_key,
                current_size=len(self._hot_store),
            )
        
        self._hot_store[key] = value
        self._hot_store.move_to_end(key)  # Mark as recently used
    
    async def _store_warm(self, key: str, value: ConversationBlock, session_id: str) -> None:
        """Store in warm tier with compression."""
        # Check capacity
        if len(self._warm_store) >= self.warm_capacity:
            # Evict oldest to cold tier
            oldest_key, (compressed_data, metadata) = self._warm_store.popitem(last=False)
            
            # Decompress and create summary for cold storage
            decompressed = gzip.decompress(compressed_data)
            block_data = json.loads(decompressed.decode('utf-8'))
            
            # Create summary
            summary = self._create_summary(block_data)
            await self._store_cold(oldest_key, summary, session_id)
            
            logger.debug(
                "Evicted from warm to cold tier",
                key=oldest_key,
                current_size=len(self._warm_store),
            )
        
        # Compress the block
        block_data = self._serialize_block(value)
        serialized = json.dumps(block_data).encode('utf-8')
        
        if len(serialized) > self.compression_threshold:
            compressed = gzip.compress(serialized, compresslevel=6)
            self._stats["bytes_saved"] += len(serialized) - len(compressed)
            self._stats["total_compressed"] += 1
        else:
            compressed = serialized
        
        metadata = {
            "original_size": len(serialized),
            "compressed_size": len(compressed),
            "compression_ratio": len(serialized) / len(compressed) if compressed else 1,
            "created_at": value.created_at.isoformat(),
            "access_count": value.access_count,
        }
        
        self._warm_store[key] = (compressed, metadata)
        self._warm_store.move_to_end(key)
        self._tier_index[key] = StorageTier.WARM
    
    async def _store_cold(self, key: str, value: Any, session_id: str) -> None:
        """Store in cold tier as summary."""
        # Check capacity
        if len(self._cold_store) >= self.cold_capacity:
            # Evict oldest completely
            oldest_key = next(iter(self._cold_store))
            self._cold_store.pop(oldest_key)
            self._tier_index.pop(oldest_key, None)
            self._stats["total_evicted"] += 1
            
            logger.debug(
                "Evicted from cold tier (permanent)",
                key=oldest_key,
                current_size=len(self._cold_store),
            )
        
        # Store summary
        if isinstance(value, ConversationBlock):
            summary = self._create_summary(self._serialize_block(value))
        else:
            summary = value
        
        self._cold_store[key] = summary
        self._cold_store.move_to_end(key)
        self._tier_index[key] = StorageTier.COLD
    
    async def retrieve(
        self,
        key: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[ConversationBlock]:
        """Retrieve a conversation block."""
        self._stats["total_retrieved"] += 1
        
        # Check which tier the key is in
        tier = self._tier_index.get(key)
        if not tier:
            return None
        
        if tier == StorageTier.HOT:
            # Direct retrieval
            block = self._hot_store.get(key)
            if block:
                # Update access time and count
                block.last_accessed = datetime.utcnow()
                block.access_count += 1
                self._hot_store.move_to_end(key)  # Mark as recently used
            return block
            
        elif tier == StorageTier.WARM:
            # Decompress and deserialize
            data = self._warm_store.get(key)
            if not data:
                return None
            
            compressed, metadata = data
            decompressed = gzip.decompress(compressed) if len(compressed) < len(str(compressed)) else compressed
            block_data = json.loads(decompressed.decode('utf-8'))
            
            # Recreate block
            block = self._deserialize_block(block_data)
            
            # Promote to hot tier if frequently accessed
            if block.access_count > 5:
                session_id = metadata.get("session_id", "default")
                await self._store_hot(key, block, session_id)
                self._warm_store.pop(key, None)
                logger.debug(
                    "Promoted from warm to hot tier",
                    key=key,
                    access_count=block.access_count,
                )
            
            return block
            
        else:  # COLD
            # Only summary available
            summary = self._cold_store.get(key)
            if not summary:
                return None
            
            # Create a minimal block from summary
            block = ConversationBlock(
                block_id=key,
                messages=[
                    Message(
                        role=MessageRole.SYSTEM,
                        content=f"[Summary] {summary.get('summary', 'Historical conversation')}",
                    )
                ],
                relevance_score=summary.get('relevance_score', 0.5),
            )
            
            # Don't promote summaries back to hot tier
            return block
    
    async def delete(self, key: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Delete a conversation block."""
        tier = self._tier_index.get(key)
        if not tier:
            return False
        
        # Remove from appropriate tier
        if tier == StorageTier.HOT:
            self._hot_store.pop(key, None)
        elif tier == StorageTier.WARM:
            self._warm_store.pop(key, None)
        else:  # COLD
            self._cold_store.pop(key, None)
        
        # Update indexes
        self._tier_index.pop(key, None)
        
        # Remove from session index
        session_id = metadata.get("session_id", "default") if metadata else "default"
        self._session_index[session_id].discard(key)
        
        return True
    
    async def list_keys(
        self,
        prefix: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """List all keys."""
        all_keys = list(self._tier_index.keys())
        
        if prefix:
            all_keys = [k for k in all_keys if k.startswith(prefix)]
        
        if metadata and "session_id" in metadata:
            session_keys = self._session_index.get(metadata["session_id"], set())
            all_keys = [k for k in all_keys if k in session_keys]
        
        return all_keys
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        return {
            **self._stats,
            "tier_distribution": {
                StorageTier.HOT.value: len(self._hot_store),
                StorageTier.WARM.value: len(self._warm_store),
                StorageTier.COLD.value: len(self._cold_store),
            },
            "total_blocks": len(self._tier_index),
            "sessions": len(self._session_index),
            "memory_usage": {
                "hot_bytes": sum(self._estimate_block_size(b) for b in self._hot_store.values()),
                "warm_bytes": sum(len(data[0]) for data in self._warm_store.values()),
                "cold_bytes": sum(len(json.dumps(s)) for s in self._cold_store.values()),
            },
        }
    
    def _serialize_block(self, block: ConversationBlock) -> Dict:
        """Serialize a conversation block."""
        return {
            "block_id": block.block_id,
            "messages": [
                {
                    "role": msg.role.value,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
                    "metadata": msg.metadata,
                }
                for msg in block.messages
            ],
            "relevance_score": block.relevance_score,
            "created_at": block.created_at.isoformat(),
            "last_accessed": block.last_accessed.isoformat(),
            "access_count": block.access_count,
        }
    
    def _deserialize_block(self, data: Dict) -> ConversationBlock:
        """Deserialize a conversation block."""
        messages = [
            Message(
                role=MessageRole[msg["role"].upper()],
                content=msg["content"],
                timestamp=datetime.fromisoformat(msg["timestamp"]) if msg.get("timestamp") else None,
                metadata=msg.get("metadata"),
            )
            for msg in data["messages"]
        ]
        
        block = ConversationBlock(
            block_id=data["block_id"],
            messages=messages,
            relevance_score=data.get("relevance_score", 1.0),
        )
        
        # Restore timestamps
        if "created_at" in data:
            block.created_at = datetime.fromisoformat(data["created_at"])
        if "last_accessed" in data:
            block.last_accessed = datetime.fromisoformat(data["last_accessed"])
        if "access_count" in data:
            block.access_count = data["access_count"]
        
        return block
    
    def _create_summary(self, block_data: Dict) -> Dict:
        """Create a summary of a conversation block."""
        messages = block_data.get("messages", [])
        
        # Extract key information
        roles = [msg.get("role", "unknown") for msg in messages]
        total_length = sum(len(msg.get("content", "")) for msg in messages)
        
        # Create brief summary
        if messages:
            first_msg = messages[0].get("content", "")[:100]
            last_msg = messages[-1].get("content", "")[:100]
            summary = f"{roles[0]}: {first_msg}... → {roles[-1]}: {last_msg}..."
        else:
            summary = "Empty conversation block"
        
        return {
            "summary": summary,
            "message_count": len(messages),
            "total_length": total_length,
            "roles": list(set(roles)),
            "relevance_score": block_data.get("relevance_score", 0.5),
            "created_at": block_data.get("created_at"),
        }
    
    def _estimate_block_size(self, block: ConversationBlock) -> int:
        """Estimate memory size of a block."""
        # Rough estimation
        size = 0
        for msg in block.messages:
            size += len(msg.content)
            size += len(str(msg.metadata)) if msg.metadata else 0
        return size
    
    async def _periodic_cleanup(self) -> None:
        """Periodic cleanup task."""
        while self._running:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                
                # Clean up old blocks in cold tier
                now = datetime.utcnow()
                to_remove = []
                
                for key, summary in self._cold_store.items():
                    created_at_str = summary.get("created_at")
                    if created_at_str:
                        created_at = datetime.fromisoformat(created_at_str)
                        if now - created_at > timedelta(days=7):
                            to_remove.append(key)
                
                for key in to_remove:
                    await self.delete(key)
                
                if to_remove:
                    logger.info(
                        "Cleaned up old blocks",
                        removed_count=len(to_remove),
                    )
                    
            except Exception as e:
                logger.error("Error in periodic cleanup", error=str(e))
    
    async def shutdown(self) -> None:
        """Shutdown the storage."""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info(
            "Shutdown in-memory store",
            final_stats=await self.get_stats(),
        )