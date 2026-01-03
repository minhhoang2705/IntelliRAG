"""Application configuration management.
"""

from typing import List, Literal
from pydantic import ConfigDict, Field, computed_field
from pydantic_settings import BaseSettings


# Type alias for supported storage providers
StorageProviderType = Literal["gcs", "s3"]


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra='ignore'  # Allow undefined env vars for service-specific configs
    )

    # Note: Some environment variables (API_KEY, DEVICE, MAX_BATCH_SIZE, HF_TOKEN)
    # are used by specific services and intentionally not declared here.
    # These are loaded directly by their respective services.

    # Application
    app_name: str = "IntelliRAG"
    app_version: str = "0.2.0"
    debug: bool = False
    environment: str = "development"

    # Storage Provider Configuration
    storage_provider: StorageProviderType = Field(
        default="gcs",
        description="Storage provider: 'gcs' or 's3'"
    )

    # Google Cloud Storage (GCS) Configuration
    gcs_project_id: str = "intellirag-project"
    gcs_bucket_name: str = "intellirag-raw-documents"
    gcs_credentials_path: str = Field(
        default="", description="Path to GCS service account JSON file")
    gcs_use_default_credentials: bool = Field(
        default=True, description="Use default GCP credentials")

    # GCS Storage Settings
    gcs_upload_timeout: int = Field(
        default=300, description="Upload timeout in seconds")
    gcs_download_timeout: int = Field(
        default=300, description="Download timeout in seconds")
    gcs_max_retries: int = Field(
        default=3, description="Maximum retry attempts for GCS operations")

    # AWS S3 Configuration
    s3_bucket_name: str = Field(
        default="intellirag-raw-documents",
        description="S3 bucket name for document storage"
    )
    s3_region: str = Field(
        default="us-east-1",
        description="AWS region for S3 bucket"
    )
    s3_endpoint_url: str = Field(
        default="",
        description="Optional S3 endpoint URL (for LocalStack testing)"
    )

    # S3 Storage Settings
    s3_upload_timeout: int = Field(
        default=300, description="Upload timeout in seconds")
    s3_download_timeout: int = Field(
        default=300, description="Download timeout in seconds")
    s3_max_retries: int = Field(
        default=3, description="Maximum retry attempts for S3 operations")

    # PostgreSQL Configuration (REMOVED - Replaced by Qdrant Payloads)
    # All metadata now stored in Qdrant payloads. See app/models/schemas.py

    # MinIO Configuration (REMOVED - Replaced by Google Cloud Storage)
    # All document storage now uses GCS. See GCS Configuration section above.

    # Qdrant Configuration
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_name: str = "default"

    # vLLM Configuration
    vllm_base_url: str = "http://localhost:8000/v1"
    vllm_model: str = "Qwen/Qwen3-0.6B"

    # Embedding Service Configuration
    embedding_service_url: str = "http://localhost:8001"
    embedding_use_remote: bool = True  # Use remote embedding service by default

    # Embedding Model Configuration (for local mode fallback)
    embedding_model: str = "BAAI/bge-m3"
    embedding_dimension: int = 1024  # Note: Auto-discovered in remote mode
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
    def allowed_file_types_list(self) -> List[str]:
        """Parse allowed file types into a list."""
        return [ft.strip() for ft in self.allowed_file_types.split(",")]


# Global settings instance
settings = Settings()
