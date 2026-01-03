"""
Base protocol for object storage services.

This module defines the ObjectStorageProtocol that all storage service
implementations (GCS, S3, etc.) must conform to.
"""

from typing import Protocol, runtime_checkable, Optional


@runtime_checkable
class ObjectStorageProtocol(Protocol):
    """Protocol for object storage services (GCS, S3, etc.)."""

    bucket_name: str

    async def __aenter__(self) -> "ObjectStorageProtocol":
        """Async context manager entry."""
        ...

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        ...

    async def connect(self) -> None:
        """Initialize storage client connection."""
        ...

    async def disconnect(self) -> None:
        """Close storage client connection."""
        ...

    async def upload_file(
        self,
        file_data,
        object_path: str,
        content_type: str,
        metadata: Optional[dict] = None
    ) -> str:
        """Upload file and return cloud URI (gs:// or s3://).

        Args:
            file_data: File content as bytes or file-like object
            object_path: Path in bucket (e.g., "collection_1/doc_uuid.pdf")
            content_type: MIME type (e.g., "application/pdf")
            metadata: Optional custom metadata dict

        Returns:
            Cloud URI (e.g., "gs://bucket-name/object-path" or "s3://bucket-name/object-path")
        """
        ...

    async def download_file(self, object_path: str) -> bytes:
        """Download file and return bytes.

        Args:
            object_path: Path in bucket

        Returns:
            File content as bytes
        """
        ...
