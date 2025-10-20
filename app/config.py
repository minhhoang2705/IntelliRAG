"""Application configuration management.

Author: IntelliRAG Team
Date: 2025-10-20
"""

from typing import List
from pydantic import ConfigDict, Field, computed_field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Application
    app_name: str = "IntelliRAG"
    app_version: str = "0.2.0"
    debug: bool = False
    environment: str = "development"

    # PostgreSQL Configuration
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "intellirag"
    postgres_user: str = "intellirag_user"
    postgres_password: str

    # Database Pool Settings
    db_pool_min_size: int = 5
    db_pool_max_size: int = 20
    db_pool_timeout: int = 30

    # MinIO Configuration
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str
    minio_secret_key: str
    minio_secure: bool = False
    minio_region: str = "us-east-1"

    # MinIO Buckets
    raw_documents_bucket: str = "raw-documents"
    processed_documents_bucket: str = "processed-documents"
    document_chunks_bucket: str = "document-chunks"

    # Qdrant Configuration
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_name: str = "default"

    # vLLM Configuration
    vllm_base_url: str = "http://localhost:8000/v1"
    vllm_model: str = "Qwen/Qwen3-0.6B"

    # Embedding Model Configuration
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_device: str = "cpu"
    embedding_batch_size: int = 32

    # Document Processing Configuration
    max_file_size_mb: int = 50
    allowed_file_types: str = "pdf,docx,txt,csv"
    chunk_size: int = 512
    chunk_overlap: int = 50

    # RAG Configuration
    rag_top_k: int = 5
    rag_temperature: float = 0.7
    rag_max_tokens: int = 512

    @computed_field
    @property
    def database_url(self) -> str:
        """Construct PostgreSQL database URL."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field
    @property
    def allowed_file_types_list(self) -> List[str]:
        """Parse allowed file types into a list."""
        return [ft.strip() for ft in self.allowed_file_types.split(",")]


# Global settings instance
settings = Settings()
