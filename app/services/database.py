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

    async def connect(
        self,
        min_size: int = 10,
        max_size: int = 20,
        command_timeout: float = 60.0,
        max_inactive_connection_lifetime: float = 300.0
    ):
        """Establish connection to PostgreSQL database with production-grade pool configuration.
        
        Args:
            min_size: Minimum number of connections in the pool (default: 10)
            max_size: Maximum number of connections in the pool (default: 20)
            command_timeout: Timeout in seconds for SQL commands (default: 60.0)
            max_inactive_connection_lifetime: Max seconds a connection can stay inactive (default: 300.0)
        """
        # Extract connection string (remove sqlalchemy prefix)
        url = self.database_url.replace("postgresql+asyncpg://", "postgresql://")
        
        self.pool = await asyncpg.create_pool(
            url,
            min_size=min_size,
            max_size=max_size,
            command_timeout=command_timeout,
            max_inactive_connection_lifetime=max_inactive_connection_lifetime
        )
        
        logger.info(
            f"Connected to PostgreSQL database with pool: "
            f"min_size={min_size}, max_size={max_size}, "
            f"command_timeout={command_timeout}s, "
            f"max_inactive_connection_lifetime={max_inactive_connection_lifetime}s"
        )

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
            
        Raises:
            DuplicateResourceError: If collection name already exists
            DatabaseServiceError: For other database errors
        """
        from asyncpg.exceptions import UniqueViolationError, PostgresError
        from app.exceptions import DuplicateResourceError, DatabaseServiceError
        
        try:
            query = """
                INSERT INTO collections (collection_name, description)
                VALUES ($1, $2)
                RETURNING *
            """
            return await self.pool.fetchrow(query, collection_name, description)
            
        except UniqueViolationError as e:
            logger.warning(f"Duplicate collection: {collection_name}")
            raise DuplicateResourceError(
                f"Collection '{collection_name}' already exists"
            ) from e
            
        except PostgresError as e:
            logger.error(f"Database error creating collection: {e}", exc_info=True)
            raise DatabaseServiceError(
                "Failed to create collection due to database error"
            ) from e
            
        except Exception as e:
            logger.exception(f"Unexpected error creating collection: {e}")
            raise DatabaseServiceError(
                "An unexpected error occurred"
            ) from e

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

    async def create_document(
        self,
        collection_id: str,
        filename: str,
        mime_type: str,
        file_size_bytes: int,
        file_hash: str,
        minio_bucket: str,
        minio_raw_path: str,
        custom_metadata: dict = None
    ):
        """Create a new document record.
        
        Args:
            collection_id: UUID of the collection
            filename: Original filename
            mime_type: MIME type of the document
            file_size_bytes: File size in bytes
            file_hash: SHA-256 hash for deduplication
            minio_bucket: MinIO bucket name
            minio_raw_path: Path to raw file in MinIO
            custom_metadata: Optional custom metadata (JSONB)
            
        Returns:
            Record of the created document
        """
        query = """
            INSERT INTO documents (
                collection_id, filename, mime_type, file_size_bytes,
                file_hash, minio_bucket, minio_raw_path, custom_metadata
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING *
        """
        return await self.pool.fetchrow(
            query,
            collection_id,
            filename,
            mime_type,
            file_size_bytes,
            file_hash,
            minio_bucket,
            minio_raw_path,
            custom_metadata or {}
        )

    async def check_duplicate_document(
        self,
        collection_id: str,
        file_hash: str
    ) -> str | None:
        """Check if a document with the same hash already exists in the collection.
        
        Uses SERIALIZABLE transaction isolation to prevent race conditions when
        multiple users upload the same file simultaneously.
        
        Args:
            collection_id: UUID of the collection
            file_hash: SHA-256 hash of the file
            
        Returns:
            document_id if duplicate found, None otherwise
        """
        query = """
            SELECT document_id FROM documents
            WHERE collection_id = $1 AND file_hash = $2
        """
        
        # Use SERIALIZABLE isolation to prevent race conditions
        async with self.pool.transaction(isolation='serializable') as transaction:
            result = await transaction.fetchrow(query, collection_id, file_hash)
            if result:
                return result['document_id']
            return None

    async def create_processing_job(
        self,
        document_id: str,
        collection_id: str
    ):
        """Create a processing job to track document pipeline progress.
        
        Args:
            document_id: UUID of the document
            collection_id: UUID of the collection
            
        Returns:
            Record of the created processing job
        """
        query = """
            INSERT INTO processing_jobs (document_id, collection_id, status)
            VALUES ($1, $2, 'pending')
            RETURNING *
        """
        return await self.pool.fetchrow(query, document_id, collection_id)

    async def update_job_status(
        self,
        job_id: str,
        status: str,
        error_message: str = None
    ):
        """Update the status of a processing job.
        
        Args:
            job_id: UUID of the processing job
            status: New status (pending, processing, completed, failed, retrying)
            error_message: Optional error message for failed jobs
        """
        query = """
            UPDATE processing_jobs
            SET status = $1, error_message = $2
            WHERE job_id = $3
        """
        await self.pool.execute(query, status, error_message, job_id)

    async def get_document(self, document_id: str):
        """Get a document by ID.
        
        Args:
            document_id: UUID of the document
            
        Returns:
            Document record or None if not found
        """
        query = """
            SELECT * FROM documents
            WHERE document_id = $1
        """
        return await self.pool.fetchrow(query, document_id)

    async def list_documents(
        self,
        collection_id: str,
        offset: int = 0,
        limit: int = 10
    ):
        """List documents in a collection with pagination.
        
        Args:
            collection_id: UUID of the collection
            offset: Number of documents to skip (default: 0)
            limit: Maximum number of documents to return (default: 10)
            
        Returns:
            List of document records
        """
        query = """
            SELECT * FROM documents
            WHERE collection_id = $1
            ORDER BY uploaded_at DESC
            OFFSET $2 LIMIT $3
        """
        return await self.pool.fetch(query, collection_id, offset, limit)
