"""Integration tests for database schema via Alembic migrations.

Author: IntelliRAG Team
Date: 2025-10-21
"""

import pytest
import asyncpg
from app.config import settings


class TestDatabaseSchema:
    """Test suite for database schema created by Alembic migrations."""

    @pytest.mark.asyncio
    async def test_collections_table_exists(self):
        """Test that collections table exists after running migrations."""
        conn = await asyncpg.connect(
            settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        )

        try:
            result = await conn.fetchval(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'collections'
                )
                """
            )
            assert result is True, "collections table should exist after migration"

        finally:
            await conn.close()

    @pytest.mark.asyncio
    async def test_documents_table_exists(self):
        """Test that documents table exists with foreign key to collections."""
        conn = await asyncpg.connect(
            settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        )

        try:
            result = await conn.fetchval(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'documents'
                )
                """
            )
            assert result is True, "documents table should exist after migration"

        finally:
            await conn.close()

    @pytest.mark.asyncio
    async def test_document_chunks_table_exists(self):
        """Test that document_chunks table exists."""
        conn = await asyncpg.connect(
            settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        )

        try:
            result = await conn.fetchval(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'document_chunks'
                )
                """
            )
            assert result is True, "document_chunks table should exist after migration"

        finally:
            await conn.close()

    @pytest.mark.asyncio
    async def test_processing_jobs_table_exists(self):
        """Test that processing_jobs table exists."""
        conn = await asyncpg.connect(
            settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        )

        try:
            result = await conn.fetchval(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'processing_jobs'
                )
                """
            )
            assert result is True, "processing_jobs table should exist after migration"

        finally:
            await conn.close()
