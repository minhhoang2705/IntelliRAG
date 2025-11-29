"""Unit tests for configuration management.


Date: 2025-10-20
"""

import os
from unittest.mock import patch


class TestSettings:
    """Test suite for Settings configuration class."""

    def test_settings_loads_app_name_from_environment(self):
        """Test that settings loads app name from environment variables."""
        with patch.dict(os.environ, {
            "APP_NAME": "TestApp",
        }):
            from app.config import Settings
            test_settings = Settings()

            assert test_settings.app_name == "TestApp"

    def test_qdrant_configuration(self):
        """Test Qdrant configuration loading."""
        with patch.dict(os.environ, {
            "QDRANT_URL": "http://qdrant:6333",
            "QDRANT_COLLECTION_NAME": "my_collection",
        }, clear=True):
            from app.config import Settings
            test_settings = Settings()

            assert test_settings.qdrant_url == "http://qdrant:6333"
            assert test_settings.qdrant_collection_name == "my_collection"

    def test_vllm_configuration(self):
        """Test vLLM configuration loading."""
        with patch.dict(os.environ, {
            "VLLM_BASE_URL": "http://vllm:8000/v1",
            "VLLM_MODEL": "Qwen/Qwen3-0.6B",
        }, clear=True):
            from app.config import Settings
            test_settings = Settings()

            assert test_settings.vllm_base_url == "http://vllm:8000/v1"
            assert test_settings.vllm_model == "Qwen/Qwen3-0.6B"

    def test_embedding_configuration(self):
        """Test embedding model configuration."""
        with patch.dict(os.environ, {
            "EMBEDDING_MODEL": "sentence-transformers/custom-model",
            "EMBEDDING_DEVICE": "cuda",
            "EMBEDDING_BATCH_SIZE": "64",
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
        }, clear=True):
            from app.config import Settings
            test_settings = Settings()

            assert test_settings.allowed_file_types == "pdf,docx,txt,csv"
            assert test_settings.allowed_file_types_list == [
                "pdf", "docx", "txt", "csv"]

    def test_rag_configuration(self):
        """Test RAG configuration parameters."""
        with patch.dict(os.environ, {
            "RAG_TOP_K": "10",
            "RAG_TEMPERATURE": "0.5",
            "RAG_MAX_TOKENS": "1024",
        }, clear=True):
            from app.config import Settings
            test_settings = Settings()

            assert test_settings.rag_top_k == 10
            assert test_settings.rag_temperature == 0.5
            assert test_settings.rag_max_tokens == 1024

    def test_default_values(self):
        """Test that appropriate default values are set."""
        with patch.dict(os.environ, {
        }, clear=True):
            from app.config import Settings
            test_settings = Settings()

            # Defaults
            assert test_settings.app_name == "IntelliRAG"
            assert test_settings.app_version == "0.2.0"
            assert test_settings.debug is False
            assert test_settings.chunk_size == 512
            assert test_settings.chunk_overlap == 50

    def test_settings_singleton(self):
        """Test that settings module exports a singleton instance."""
        with patch.dict(os.environ, {
        }, clear=True):
            from app.config import settings

            assert settings is not None
            assert hasattr(settings, 'app_name')

    def test_gcs_project_id_configuration(self):
        """Test GCS project ID configuration loading."""
        with patch.dict(os.environ, {
            "GCS_PROJECT_ID": "my-gcp-project"
        }, clear=True):
            from app.config import Settings
            test_settings = Settings()

            assert test_settings.gcs_project_id == "my-gcp-project"

    def test_gcs_bucket_name_configuration(self):
        """Test GCS bucket name configuration loading."""
        with patch.dict(os.environ, {
            "GCS_BUCKET_NAME": "my-custom-bucket"
        }, clear=True):
            from app.config import Settings
            test_settings = Settings()

            assert test_settings.gcs_bucket_name == "my-custom-bucket"

    def test_gcs_credentials_path_configuration(self):
        """Test GCS credentials path configuration."""
        with patch.dict(os.environ, {
            "GCS_CREDENTIALS_PATH": "/path/to/creds.json"
        }, clear=True):
            from app.config import Settings
            test_settings = Settings()

            assert test_settings.gcs_credentials_path == "/path/to/creds.json"

    def test_gcs_use_default_credentials_configuration(self):
        """Test GCS use default credentials flag."""
        with patch.dict(os.environ, {
            "GCS_USE_DEFAULT_CREDENTIALS": "false"
        }, clear=True):
            from app.config import Settings
            test_settings = Settings()

            assert test_settings.gcs_use_default_credentials is False

    def test_gcs_timeout_configuration(self):
        """Test GCS upload and download timeout configuration."""
        with patch.dict(os.environ, {
            "GCS_UPLOAD_TIMEOUT": "600",
            "GCS_DOWNLOAD_TIMEOUT": "600"
        }, clear=True):
            from app.config import Settings
            test_settings = Settings()

            assert test_settings.gcs_upload_timeout == 600
            assert test_settings.gcs_download_timeout == 600

    def test_gcs_max_retries_configuration(self):
        """Test GCS max retries configuration."""
        with patch.dict(os.environ, {
            "GCS_MAX_RETRIES": "5"
        }, clear=True):
            from app.config import Settings
            test_settings = Settings()

            assert test_settings.gcs_max_retries == 5

    def test_gcs_configuration_defaults(self):
        """Test GCS configuration default values."""
        with patch.dict(os.environ, {}, clear=True):
            from app.config import Settings
            test_settings = Settings()

            assert test_settings.gcs_project_id == "intellirag-project"
            assert test_settings.gcs_bucket_name == "intellirag-raw-documents"
            assert test_settings.gcs_credentials_path == ""
            assert test_settings.gcs_use_default_credentials is True
            assert test_settings.gcs_upload_timeout == 300
            assert test_settings.gcs_download_timeout == 300
            assert test_settings.gcs_max_retries == 3
