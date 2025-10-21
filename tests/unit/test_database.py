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
        """Test that DatabaseService can establish database connection with pool configuration."""
        from app.services.database import DatabaseService

        # Mock asyncpg.create_pool
        mock_pool = MagicMock()
        mock_create_pool = AsyncMock(return_value=mock_pool)

        with patch('app.services.database.asyncpg.create_pool', mock_create_pool):
            db_service = DatabaseService(database_url="postgresql+asyncpg://test:pass@localhost:5432/testdb")

            # Should be able to connect with pool configuration
            await db_service.connect(
                min_size=10,
                max_size=20,
                command_timeout=60.0,
                max_inactive_connection_lifetime=300.0
            )

            # Should have a pool after connecting
            assert db_service.pool is not None
            assert db_service.pool == mock_pool

            # Verify create_pool was called with correct parameters
            mock_create_pool.assert_called_once()
            call_args = mock_create_pool.call_args
            # Check that URL was passed (asyncpg may mask passwords for security)
            assert 'localhost:5432/testdb' in str(call_args[0][0])
            # Verify pool configuration parameters
            assert call_args[1]['min_size'] == 10
            assert call_args[1]['max_size'] == 20
            assert call_args[1]['command_timeout'] == 60.0
            assert call_args[1]['max_inactive_connection_lifetime'] == 300.0

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

    @pytest.mark.asyncio
    async def test_database_service_create_document(self):
        """Test that DatabaseService can create a document record."""
        from app.services.database import DatabaseService

        # Mock asyncpg.create_pool and pool methods
        mock_pool = MagicMock()
        mock_pool.fetchrow = AsyncMock(return_value={
            'document_id': '456e7890-e89b-12d3-a456-426614174001',
            'collection_id': '123e4567-e89b-12d3-a456-426614174000',
            'filename': 'test-document.pdf',
            'mime_type': 'application/pdf',
            'file_size_bytes': 1024000,
            'file_hash': 'a' * 64,  # SHA-256 hash (64 hex chars)
            'minio_bucket': 'raw-documents',
            'minio_raw_path': 'collection-test/test-document.pdf',
            'custom_metadata': {},
            'uploaded_at': '2025-10-21T10:00:00Z'
        })

        with patch('app.services.database.asyncpg.create_pool', new_callable=AsyncMock, return_value=mock_pool):
            db_service = DatabaseService(database_url="postgresql+asyncpg://test:pass@localhost:5432/testdb")

            # Connect first
            await db_service.connect()

            # Create document
            document = await db_service.create_document(
                collection_id='123e4567-e89b-12d3-a456-426614174000',
                filename='test-document.pdf',
                mime_type='application/pdf',
                file_size_bytes=1024000,
                file_hash='a' * 64,
                minio_bucket='raw-documents',
                minio_raw_path='collection-test/test-document.pdf'
            )

            # Verify document was created
            assert document is not None
            assert document['filename'] == 'test-document.pdf'
            assert document['mime_type'] == 'application/pdf'
            assert document['file_size_bytes'] == 1024000
            assert document['file_hash'] == 'a' * 64
            assert document['minio_bucket'] == 'raw-documents'
            mock_pool.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_service_check_duplicate_document(self):
        """Test that DatabaseService can check for duplicate documents by hash."""
        from app.services.database import DatabaseService

        # Mock asyncpg.create_pool and pool methods
        mock_pool = MagicMock()

        # Mock transaction context manager
        mock_transaction = MagicMock()
        mock_transaction.__aenter__ = AsyncMock(return_value=mock_transaction)
        mock_transaction.__aexit__ = AsyncMock(return_value=None)
        mock_transaction.fetchrow = AsyncMock(return_value={
            'document_id': '456e7890-e89b-12d3-a456-426614174001'
        })

        mock_pool.transaction = MagicMock(return_value=mock_transaction)

        with patch('app.services.database.asyncpg.create_pool', new_callable=AsyncMock, return_value=mock_pool):
            db_service = DatabaseService(database_url="postgresql+asyncpg://test:pass@localhost:5432/testdb")

            # Connect first
            await db_service.connect()

            # Check for duplicate (should find one)
            duplicate_id = await db_service.check_duplicate_document(
                collection_id='123e4567-e89b-12d3-a456-426614174000',
                file_hash='a' * 64
            )

            # Verify duplicate was found
            assert duplicate_id == '456e7890-e89b-12d3-a456-426614174001'

            # Verify transaction was created with SERIALIZABLE isolation
            mock_pool.transaction.assert_called_once_with(isolation='serializable')
            mock_transaction.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_service_create_processing_job(self):
        """Test that DatabaseService can create a processing job."""
        from app.services.database import DatabaseService

        # Mock asyncpg.create_pool and pool methods
        mock_pool = MagicMock()
        mock_pool.fetchrow = AsyncMock(return_value={
            'job_id': '789e0123-e89b-12d3-a456-426614174002',
            'document_id': '456e7890-e89b-12d3-a456-426614174001',
            'collection_id': '123e4567-e89b-12d3-a456-426614174000',
            'status': 'pending',
            'progress': {
                'upload': 'completed',
                'parsing': 'pending',
                'chunking': 'pending',
                'embedding': 'pending',
                'indexing': 'pending'
            },
            'retry_count': 0,
            'max_retries': 3,
            'created_at': '2025-10-21T10:00:00Z'
        })

        with patch('app.services.database.asyncpg.create_pool', new_callable=AsyncMock, return_value=mock_pool):
            db_service = DatabaseService(database_url="postgresql+asyncpg://test:pass@localhost:5432/testdb")

            # Connect first
            await db_service.connect()

            # Create processing job
            job = await db_service.create_processing_job(
                document_id='456e7890-e89b-12d3-a456-426614174001',
                collection_id='123e4567-e89b-12d3-a456-426614174000'
            )

            # Verify job was created
            assert job is not None
            assert job['status'] == 'pending'
            assert job['document_id'] == '456e7890-e89b-12d3-a456-426614174001'
            assert job['collection_id'] == '123e4567-e89b-12d3-a456-426614174000'
            assert job['retry_count'] == 0
            assert job['max_retries'] == 3
            mock_pool.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_service_update_job_status(self):
        """Test that DatabaseService can update job status."""
        from app.services.database import DatabaseService

        # Mock asyncpg.create_pool and pool methods
        mock_pool = MagicMock()
        mock_pool.execute = AsyncMock(return_value="UPDATE 1")

        with patch('app.services.database.asyncpg.create_pool', new_callable=AsyncMock, return_value=mock_pool):
            db_service = DatabaseService(database_url="postgresql+asyncpg://test:pass@localhost:5432/testdb")

            # Connect first
            await db_service.connect()

            # Update job status to failed with error message
            await db_service.update_job_status(
                job_id='789e0123-e89b-12d3-a456-426614174002',
                status='failed',
                error_message='File parsing failed: corrupted PDF'
            )

            # Verify execute was called
            mock_pool.execute.assert_called_once()
            call_args = mock_pool.execute.call_args[0][0]
            # Check that UPDATE query was executed
            assert 'UPDATE processing_jobs' in call_args
            assert 'status' in call_args

    @pytest.mark.asyncio
    async def test_database_service_get_document(self):
        """Test that DatabaseService can retrieve a document by ID."""
        from app.services.database import DatabaseService

        # Mock asyncpg.create_pool and pool methods
        mock_pool = MagicMock()
        mock_pool.fetchrow = AsyncMock(return_value={
            'document_id': '456e7890-e89b-12d3-a456-426614174001',
            'collection_id': '123e4567-e89b-12d3-a456-426614174000',
            'filename': 'report.pdf',
            'mime_type': 'application/pdf',
            'file_size_bytes': 2048000,
            'file_hash': 'b' * 64,
            'minio_bucket': 'raw-documents',
            'minio_raw_path': 'collection-test/report.pdf',
            'uploaded_at': '2025-10-21T10:00:00Z'
        })

        with patch('app.services.database.asyncpg.create_pool', new_callable=AsyncMock, return_value=mock_pool):
            db_service = DatabaseService(database_url="postgresql+asyncpg://test:pass@localhost:5432/testdb")

            # Connect first
            await db_service.connect()

            # Get document by ID
            document = await db_service.get_document('456e7890-e89b-12d3-a456-426614174001')

            # Verify document was retrieved
            assert document is not None
            assert document['document_id'] == '456e7890-e89b-12d3-a456-426614174001'
            assert document['filename'] == 'report.pdf'
            assert document['file_size_bytes'] == 2048000
            mock_pool.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_service_list_documents(self):
        """Test that DatabaseService can list documents with pagination."""
        from app.services.database import DatabaseService

        # Mock asyncpg.create_pool and pool methods
        mock_pool = MagicMock()
        mock_pool.fetch = AsyncMock(return_value=[
            {
                'document_id': '456e7890-e89b-12d3-a456-426614174001',
                'filename': 'doc1.pdf',
                'uploaded_at': '2025-10-21T10:00:00Z'
            },
            {
                'document_id': '456e7890-e89b-12d3-a456-426614174002',
                'filename': 'doc2.pdf',
                'uploaded_at': '2025-10-21T11:00:00Z'
            }
        ])

        with patch('app.services.database.asyncpg.create_pool', new_callable=AsyncMock, return_value=mock_pool):
            db_service = DatabaseService(database_url="postgresql+asyncpg://test:pass@localhost:5432/testdb")

            # Connect first
            await db_service.connect()

            # List documents with pagination
            documents = await db_service.list_documents(
                collection_id='123e4567-e89b-12d3-a456-426614174000',
                offset=0,
                limit=10
            )

            # Verify documents were retrieved
            assert documents is not None
            assert len(documents) == 2
            assert documents[0]['filename'] == 'doc1.pdf'
            assert documents[1]['filename'] == 'doc2.pdf'
            mock_pool.fetch.assert_called_once()
