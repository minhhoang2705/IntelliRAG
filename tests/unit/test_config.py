"""Unit tests for configuration management.

Author: IntelliRAG Team
Date: 2025-10-20
"""

import pytest
import os
from unittest.mock import patch


class TestSettings:
    """Test suite for Settings configuration class."""

    def test_settings_loads_app_name_from_environment(self):
        """Test that settings loads app name from environment variables."""
        with patch.dict(os.environ, {
            "APP_NAME": "TestApp",
            "POSTGRES_PASSWORD": "testpass",
            "MINIO_ACCESS_KEY": "testkey",
            "MINIO_SECRET_KEY": "testsecret"
        }):
            from app.config import Settings
            test_settings = Settings()

            assert test_settings.app_name == "TestApp"

    def test_postgres_configuration(self):
        """Test PostgreSQL configuration loading."""
        with patch.dict(os.environ, {
            "POSTGRES_HOST": "dbhost",
            "POSTGRES_PORT": "5433",
            "POSTGRES_DB": "mydb",
            "POSTGRES_USER": "myuser",
            "POSTGRES_PASSWORD": "mypass",
            "MINIO_ACCESS_KEY": "key",
            "MINIO_SECRET_KEY": "secret"
        }, clear=True):
            from app.config import Settings
            test_settings = Settings()

            assert test_settings.postgres_host == "dbhost"
            assert test_settings.postgres_port == 5433
            assert test_settings.postgres_db == "mydb"
            assert test_settings.postgres_user == "myuser"
            assert test_settings.postgres_password == "mypass"

    def test_database_url_construction(self):
        """Test database URL is properly constructed."""
        with patch.dict(os.environ, {
            "POSTGRES_HOST": "dbhost",
            "POSTGRES_PORT": "5433",
            "POSTGRES_DB": "mydb",
            "POSTGRES_USER": "myuser",
            "POSTGRES_PASSWORD": "mypass",
            "MINIO_ACCESS_KEY": "key",
            "MINIO_SECRET_KEY": "secret"
        }, clear=True):
            from app.config import Settings
            test_settings = Settings()

            expected = "postgresql+asyncpg://myuser:mypass@dbhost:5433/mydb"
            assert test_settings.database_url == expected

    def test_database_pool_configuration(self):
        """Test database pool settings."""
        with patch.dict(os.environ, {
            "DB_POOL_MIN_SIZE": "10",
            "DB_POOL_MAX_SIZE": "50",
            "DB_POOL_TIMEOUT": "60",
            "POSTGRES_PASSWORD": "pass",
            "MINIO_ACCESS_KEY": "key",
            "MINIO_SECRET_KEY": "secret"
        }, clear=True):
            from app.config import Settings
            test_settings = Settings()

            assert test_settings.db_pool_min_size == 10
            assert test_settings.db_pool_max_size == 50
            assert test_settings.db_pool_timeout == 60

    def test_minio_configuration(self):
        """Test MinIO configuration loading."""
        with patch.dict(os.environ, {
            "MINIO_ENDPOINT": "minio:9000",
            "MINIO_ACCESS_KEY": "admin",
            "MINIO_SECRET_KEY": "password",
            "MINIO_SECURE": "true",
            "MINIO_REGION": "us-west-1",
            "POSTGRES_PASSWORD": "pass"
        }, clear=True):
            from app.config import Settings
            test_settings = Settings()

            assert test_settings.minio_endpoint == "minio:9000"
            assert test_settings.minio_access_key == "admin"
            assert test_settings.minio_secret_key == "password"
            assert test_settings.minio_secure is True
            assert test_settings.minio_region == "us-west-1"

    def test_minio_buckets_configuration(self):
        """Test MinIO bucket names configuration."""
        with patch.dict(os.environ, {
            "RAW_DOCUMENTS_BUCKET": "test-raw",
            "PROCESSED_DOCUMENTS_BUCKET": "test-processed",
            "DOCUMENT_CHUNKS_BUCKET": "test-chunks",
            "POSTGRES_PASSWORD": "pass",
            "MINIO_ACCESS_KEY": "key",
            "MINIO_SECRET_KEY": "secret"
        }, clear=True):
            from app.config import Settings
            test_settings = Settings()

            assert test_settings.raw_documents_bucket == "test-raw"
            assert test_settings.processed_documents_bucket == "test-processed"
            assert test_settings.document_chunks_bucket == "test-chunks"

    def test_qdrant_configuration(self):
        """Test Qdrant configuration loading."""
        with patch.dict(os.environ, {
            "QDRANT_URL": "http://qdrant:6333",
            "QDRANT_COLLECTION_NAME": "my_collection",
            "POSTGRES_PASSWORD": "pass",
            "MINIO_ACCESS_KEY": "key",
            "MINIO_SECRET_KEY": "secret"
        }, clear=True):
            from app.config import Settings
            test_settings = Settings()

            assert test_settings.qdrant_url == "http://qdrant:6333"
            assert test_settings.qdrant_collection_name == "my_collection"

    def test_vllm_configuration(self):
        """Test vLLM configuration loading."""
        with patch.dict(os.environ, {
            "VLLM_BASE_URL": "http://vllm:8000/v1",
            "VLLM_MODEL": "Qwen/Qwen2.5-7B",
            "POSTGRES_PASSWORD": "pass",
            "MINIO_ACCESS_KEY": "key",
            "MINIO_SECRET_KEY": "secret"
        }, clear=True):
            from app.config import Settings
            test_settings = Settings()

            assert test_settings.vllm_base_url == "http://vllm:8000/v1"
            assert test_settings.vllm_model == "Qwen/Qwen2.5-7B"

    def test_embedding_configuration(self):
        """Test embedding model configuration."""
        with patch.dict(os.environ, {
            "EMBEDDING_MODEL": "sentence-transformers/custom-model",
            "EMBEDDING_DEVICE": "cuda",
            "EMBEDDING_BATCH_SIZE": "64",
            "POSTGRES_PASSWORD": "pass",
            "MINIO_ACCESS_KEY": "key",
            "MINIO_SECRET_KEY": "secret"
        }, clear=True):
            from app.config import Settings
            test_settings = Settings()

            assert test_settings.embedding_model == "sentence-transformers/custom-model"
            assert test_settings.embedding_device == "cuda"
            assert test_settings.embedding_batch_size == 64

    def test_document_processing_configuration(self):
        """Test document processing configuration."""
        with patch.dict(os.environ, {
            "MAX_FILE_SIZE_MB": "100",
            "CHUNK_SIZE": "1024",
            "CHUNK_OVERLAP": "128",
            "POSTGRES_PASSWORD": "pass",
            "MINIO_ACCESS_KEY": "key",
            "MINIO_SECRET_KEY": "secret"
        }, clear=True):
            from app.config import Settings
            test_settings = Settings()

            assert test_settings.max_file_size_mb == 100
            assert test_settings.chunk_size == 1024
            assert test_settings.chunk_overlap == 128

    def test_allowed_file_types_parsing(self):
        """Test that allowed file types are parsed correctly."""
        with patch.dict(os.environ, {
            "ALLOWED_FILE_TYPES": "pdf,docx,txt,csv",
            "POSTGRES_PASSWORD": "pass",
            "MINIO_ACCESS_KEY": "key",
            "MINIO_SECRET_KEY": "secret"
        }, clear=True):
            from app.config import Settings
            test_settings = Settings()

            assert test_settings.allowed_file_types == "pdf,docx,txt,csv"
            assert test_settings.allowed_file_types_list == ["pdf", "docx", "txt", "csv"]

    def test_rag_configuration(self):
        """Test RAG configuration parameters."""
        with patch.dict(os.environ, {
            "RAG_TOP_K": "10",
            "RAG_TEMPERATURE": "0.5",
            "RAG_MAX_TOKENS": "1024",
            "POSTGRES_PASSWORD": "pass",
            "MINIO_ACCESS_KEY": "key",
            "MINIO_SECRET_KEY": "secret"
        }, clear=True):
            from app.config import Settings
            test_settings = Settings()

            assert test_settings.rag_top_k == 10
            assert test_settings.rag_temperature == 0.5
            assert test_settings.rag_max_tokens == 1024

    def test_default_values(self):
        """Test that appropriate default values are set."""
        with patch.dict(os.environ, {
            "POSTGRES_PASSWORD": "pass",
            "MINIO_ACCESS_KEY": "key",
            "MINIO_SECRET_KEY": "secret"
        }, clear=True):
            from app.config import Settings
            test_settings = Settings()

            # Defaults
            assert test_settings.app_name == "IntelliRAG"
            assert test_settings.app_version == "0.2.0"
            assert test_settings.debug is False
            assert test_settings.postgres_host == "localhost"
            assert test_settings.postgres_port == 5432
            assert test_settings.minio_secure is False
            assert test_settings.chunk_size == 512
            assert test_settings.chunk_overlap == 50

    def test_required_fields_validation(self):
        """Test that required fields raise validation errors when missing."""
        from pydantic import ValidationError
        
        with patch.dict(os.environ, {}, clear=True):
            from app.config import Settings
            
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            
            error_str = str(exc_info.value).lower()
            assert "postgres_password" in error_str or "minio_access_key" in error_str

    def test_settings_singleton(self):
        """Test that settings module exports a singleton instance."""
        with patch.dict(os.environ, {
            "POSTGRES_PASSWORD": "pass",
            "MINIO_ACCESS_KEY": "key",
            "MINIO_SECRET_KEY": "secret"
        }, clear=True):
            from app.config import settings

            assert settings is not None
            assert hasattr(settings, 'app_name')
            assert hasattr(settings, 'postgres_host')
            assert hasattr(settings, 'minio_endpoint')
            assert hasattr(settings, 'database_url')
