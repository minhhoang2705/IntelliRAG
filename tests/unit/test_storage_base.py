"""
Unit tests for storage base protocol.

This module tests that the ObjectStorageProtocol is properly defined
and that concrete implementations conform to it.
"""

import pytest
from typing import Protocol, runtime_checkable


@runtime_checkable
class ObjectStorageProtocol(Protocol):
    """Protocol for object storage services (GCS, S3, etc.)."""

    bucket_name: str

    async def __aenter__(self) -> "ObjectStorageProtocol": ...
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None: ...
    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...

    async def upload_file(
        self,
        file_data,
        object_path: str,
        content_type: str,
        metadata: dict = None
    ) -> str:
        """Upload file and return cloud URI (gs:// or s3://)."""
        ...

    async def download_file(self, object_path: str) -> bytes:
        """Download file and return bytes."""
        ...


def test_protocol_defined():
    """Test that ObjectStorageProtocol is properly defined."""
    assert hasattr(ObjectStorageProtocol, '__protocol_attrs__')


def test_gcs_implements_protocol():
    """Test that GCSStorageService implements ObjectStorageProtocol."""
    from app.services.storage.gcs_storage import GCSStorageService

    service = GCSStorageService("test-project", "test-bucket")
    assert isinstance(service, ObjectStorageProtocol)


def test_s3_implements_protocol():
    """Test that S3StorageService implements ObjectStorageProtocol."""
    from app.services.storage.s3_storage import S3StorageService

    service = S3StorageService("test-bucket", "us-east-1")
    assert isinstance(service, ObjectStorageProtocol)
