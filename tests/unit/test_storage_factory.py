"""
Unit tests for storage factory.

This module tests the storage service factory function.
"""

import pytest
from app.services.storage.factory import create_storage_service, StorageProvider
from app.services.storage.s3_storage import S3StorageService
from app.services.storage.gcs_storage import GCSStorageService


def test_create_s3_storage():
    """Test creating S3 storage service."""
    service = create_storage_service(
        provider="s3",
        bucket_name="test-bucket",
        region="us-west-2"
    )

    assert isinstance(service, S3StorageService)
    assert service.bucket_name == "test-bucket"
    assert service.region == "us-west-2"


def test_create_gcs_storage():
    """Test creating GCS storage service."""
    service = create_storage_service(
        provider="gcs",
        bucket_name="test-bucket",
        project_id="test-project"
    )

    assert isinstance(service, GCSStorageService)
    assert service.bucket_name == "test-bucket"
    assert service.project_id == "test-project"


def test_create_storage_invalid_provider():
    """Test factory raises error for invalid provider."""
    with pytest.raises(ValueError, match="Unknown storage provider: invalid"):
        create_storage_service(
            provider="invalid",
            bucket_name="test-bucket"
        )


def test_create_s3_with_endpoint_url():
    """Test creating S3 storage with custom endpoint (LocalStack)."""
    service = create_storage_service(
        provider="s3",
        bucket_name="test-bucket",
        endpoint_url="http://localhost:4566"
    )

    assert isinstance(service, S3StorageService)
    assert service.endpoint_url == "http://localhost:4566"
