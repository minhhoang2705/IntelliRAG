"""Database service for PostgreSQL operations.

Author: IntelliRAG Team
Date: 2025-10-20
"""

import asyncpg
import logging

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for managing PostgreSQL database operations."""

    def __init__(self, database_url: str):
        """Initialize database service.

        Args:
            database_url: PostgreSQL connection URL
        """
        self.database_url = database_url
        self.pool = None

    async def connect(self):
        """Establish connection to PostgreSQL database."""
        # Extract connection string (remove sqlalchemy prefix)
        url = self.database_url.replace("postgresql+asyncpg://", "postgresql://")
        self.pool = await asyncpg.create_pool(url)
        logger.info(f"Connected to PostgreSQL database: {url}")

    async def disconnect(self):
        """Disconnect from PostgreSQL database."""
        if self.pool:
            await self.pool.close()

    async def health_check(self) -> bool:
        """Check if database connection is healthy."""
        if self.pool:
            await self.pool.fetch("SELECT 1")
            return True
        return False

    async def create_collection(self, collection_name: str, description: str = None):
        """Create a new collection.
        
        Args:
            collection_name: Name of the collection
            description: Optional description of the collection
            
        Returns:
            Record of the created collection
        """
        query = """
            INSERT INTO collections (collection_name, description)
            VALUES ($1, $2)
            RETURNING *
        """
        return await self.pool.fetchrow(query, collection_name, description)

    async def get_collection(self, collection_name: str):
        """Get a collection by name.
        
        Args:
            collection_name: Name of the collection to retrieve
            
        Returns:
            Collection record or None if not found
        """
        query = """
            SELECT * FROM collections
            WHERE collection_name = $1
        """
        return await self.pool.fetchrow(query, collection_name)
