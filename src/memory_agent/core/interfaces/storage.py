"""Storage interface definitions for memory management."""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Protocol, runtime_checkable

from pydantic import BaseModel


class StorageTier(str, Enum):
    """Storage tiers for memory management."""

    HOT = "hot"  # Active memory (Redis)
    WARM = "warm"  # Compressed recent (PostgreSQL)
    COLD = "cold"  # Archive (S3/MinIO)


class QueryFilter(BaseModel):
    """Filter criteria for storage queries."""

    session_id: Optional[str] = None
    min_relevance_score: Optional[float] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    tags: Optional[List[str]] = None
    limit: Optional[int] = None
    offset: Optional[int] = None


@runtime_checkable
class IStorage(Protocol):
    """Protocol for storage backends."""

    @property
    def tier(self) -> StorageTier:
        """Storage tier this backend represents."""
        ...

    async def store(self, key: str, data: Dict) -> bool:
        """Store data with a key.
        
        Args:
            key: Unique identifier
            data: Data to store
            
        Returns:
            True if successful
        """
        ...

    async def retrieve(self, key: str) -> Optional[Dict]:
        """Retrieve data by key.
        
        Args:
            key: Unique identifier
            
        Returns:
            Data if found, None otherwise
        """
        ...

    async def delete(self, key: str) -> bool:
        """Delete data by key.
        
        Args:
            key: Unique identifier
            
        Returns:
            True if deleted
        """
        ...

    async def query(self, filter: QueryFilter) -> List[Dict]:
        """Query storage with filters.
        
        Args:
            filter: Query filter criteria
            
        Returns:
            List of matching items
        """
        ...

    async def exists(self, key: str) -> bool:
        """Check if key exists.
        
        Args:
            key: Unique identifier
            
        Returns:
            True if exists
        """
        ...

    async def get_size(self) -> int:
        """Get total storage size in bytes.
        
        Returns:
            Size in bytes
        """
        ...

    async def clear(self) -> bool:
        """Clear all data in storage.
        
        Returns:
            True if successful
        """
        ...


@runtime_checkable
class IStorageManager(Protocol):
    """Protocol for managing multiple storage tiers."""

    async def store_block(
        self, block_id: str, block_data: Dict, tier: StorageTier
    ) -> bool:
        """Store a conversation block in specified tier.
        
        Args:
            block_id: Unique block identifier
            block_data: Block data to store
            tier: Target storage tier
            
        Returns:
            True if successful
        """
        ...

    async def retrieve_block(self, block_id: str) -> Optional[Dict]:
        """Retrieve a block from any tier.
        
        Args:
            block_id: Block identifier
            
        Returns:
            Block data if found
        """
        ...

    async def migrate_block(
        self, block_id: str, from_tier: StorageTier, to_tier: StorageTier
    ) -> bool:
        """Migrate a block between tiers.
        
        Args:
            block_id: Block identifier
            from_tier: Source tier
            to_tier: Destination tier
            
        Returns:
            True if successful
        """
        ...

    async def get_tier_stats(self) -> Dict[StorageTier, Dict]:
        """Get statistics for each storage tier.
        
        Returns:
            Stats per tier
        """
        ...