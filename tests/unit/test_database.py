"""Unit tests for DatabaseService.

Author: IntelliRAG Team
Date: 2025-10-20
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestDatabaseService:
    """Test suite for DatabaseService."""

    @pytest.mark.asyncio
    async def test_database_service_initialization(self):
        """Test that DatabaseService can be initialized with database URL."""
        from app.services.database import DatabaseService

        db_service = DatabaseService(database_url="postgresql+asyncpg://test:pass@localhost:5432/testdb")

        assert db_service is not None
        assert db_service.database_url == "postgresql+asyncpg://test:pass@localhost:5432/testdb"

    @pytest.mark.asyncio
    async def test_database_service_connect(self):
        """Test that DatabaseService can establish database connection."""
        from app.services.database import DatabaseService

        # Mock asyncpg.create_pool
        mock_pool = MagicMock()
        with patch('app.services.database.asyncpg.create_pool', new_callable=AsyncMock, return_value=mock_pool):
            db_service = DatabaseService(database_url="postgresql+asyncpg://test:pass@localhost:5432/testdb")
            
            # Should be able to connect
            await db_service.connect()
            
            # Should have a pool after connecting
            assert db_service.pool is not None
            assert db_service.pool == mock_pool

    @pytest.mark.asyncio
    async def test_database_service_disconnect(self):
        """Test that DatabaseService can disconnect from database."""
        from app.services.database import DatabaseService

        # Mock asyncpg.create_pool
        mock_pool = MagicMock()
        mock_pool.close = AsyncMock()
        
        with patch('app.services.database.asyncpg.create_pool', new_callable=AsyncMock, return_value=mock_pool):
            db_service = DatabaseService(database_url="postgresql+asyncpg://test:pass@localhost:5432/testdb")
            
            # Connect first
            await db_service.connect()
            assert db_service.pool is not None
            
            # Now disconnect
            await db_service.disconnect()
            
            # Pool should be closed
            mock_pool.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_service_health_check(self):
        """Test that DatabaseService can perform health check."""
        from app.services.database import DatabaseService

        # Mock asyncpg.create_pool and pool methods
        mock_pool = MagicMock()
        mock_pool.fetch = AsyncMock(return_value=[(1,)])  # SELECT 1 returns 1
        
        with patch('app.services.database.asyncpg.create_pool', new_callable=AsyncMock, return_value=mock_pool):
            db_service = DatabaseService(database_url="postgresql+asyncpg://test:pass@localhost:5432/testdb")
            
            # Connect first
            await db_service.connect()
            
            # Health check should return True when connection is healthy
            is_healthy = await db_service.health_check()
            
            assert is_healthy is True
            mock_pool.fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_service_create_collection(self):
        """Test that DatabaseService can create a collection."""
        from app.services.database import DatabaseService

        # Mock asyncpg.create_pool and pool methods
        mock_pool = MagicMock()
        mock_pool.fetchrow = AsyncMock(return_value={
            'collection_id': '123e4567-e89b-12d3-a456-426614174000',
            'collection_name': 'test-collection',
            'description': 'Test collection',
            'created_at': '2025-10-20T10:00:00Z',
            'updated_at': '2025-10-20T10:00:00Z',
            'document_count': 0,
            'total_chunks': 0
        })

        with patch('app.services.database.asyncpg.create_pool', new_callable=AsyncMock, return_value=mock_pool):
            db_service = DatabaseService(database_url="postgresql+asyncpg://test:pass@localhost:5432/testdb")

            # Connect first
            await db_service.connect()

            # Create collection
            collection = await db_service.create_collection(
                collection_name='test-collection',
                description='Test collection'
            )

            # Verify collection was created
            assert collection is not None
            assert collection['collection_name'] == 'test-collection'
            assert collection['description'] == 'Test collection'
            assert collection['document_count'] == 0
            mock_pool.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_service_get_collection(self):
        """Test that DatabaseService can retrieve a collection by name."""
        from app.services.database import DatabaseService

        # Mock asyncpg.create_pool and pool methods
        mock_pool = MagicMock()
        mock_pool.fetchrow = AsyncMock(return_value={
            'collection_id': '123e4567-e89b-12d3-a456-426614174000',
            'collection_name': 'test-collection',
            'description': 'Test collection',
            'created_at': '2025-10-20T10:00:00Z',
            'updated_at': '2025-10-20T10:00:00Z',
            'document_count': 5,
            'total_chunks': 150
        })

        with patch('app.services.database.asyncpg.create_pool', new_callable=AsyncMock, return_value=mock_pool):
            db_service = DatabaseService(database_url="postgresql+asyncpg://test:pass@localhost:5432/testdb")

            # Connect first
            await db_service.connect()

            # Get collection
            collection = await db_service.get_collection('test-collection')

            # Verify collection was retrieved
            assert collection is not None
            assert collection['collection_name'] == 'test-collection'
            assert collection['document_count'] == 5
            assert collection['total_chunks'] == 150
            mock_pool.fetchrow.assert_called_once()
