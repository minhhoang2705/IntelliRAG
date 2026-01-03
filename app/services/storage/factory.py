"""
Storage service factory for creating provider-specific storage instances.

This module provides a factory function to instantiate storage services
based on provider type (S3, GCS, etc.).
"""

from typing import Literal, Optional
from app.services.storage.base import ObjectStorageProtocol


# Type alias for supported storage providers
StorageProvider = Literal["s3", "gcs"]


def create_storage_service(
    provider: StorageProvider,
    bucket_name: str,
    **kwargs
) -> ObjectStorageProtocol:
    """Create a storage service instance based on provider type.

    Args:
        provider: Storage provider name ("s3" or "gcs")
        bucket_name: Name of the storage bucket
        **kwargs: Provider-specific configuration options:
            - For S3:
                - region: AWS region (default: "us-east-1")
                - endpoint_url: Optional endpoint URL for LocalStack
            - For GCS:
                - project_id: GCP project ID (required)
                - credentials_path: Path to service account JSON

    Returns:
        Storage service instance implementing ObjectStorageProtocol

    Raises:
        ValueError: If provider is not supported

    Examples:
        >>> # Create S3 storage
        >>> s3_storage = create_storage_service(
        ...     provider="s3",
        ...     bucket_name="my-bucket",
        ...     region="us-west-2"
        ... )

        >>> # Create GCS storage
        >>> gcs_storage = create_storage_service(
        ...     provider="gcs",
        ...     bucket_name="my-bucket",
        ...     project_id="my-project"
        ... )
    """
    if provider == "s3":
        from app.services.storage.s3_storage import S3StorageService
        return S3StorageService(
            bucket_name=bucket_name,
            region=kwargs.get("region", "us-east-1"),
            endpoint_url=kwargs.get("endpoint_url")
        )

    elif provider == "gcs":
        from app.services.storage.gcs_storage import GCSStorageService
        return GCSStorageService(
            project_id=kwargs.get("project_id", ""),
            bucket_name=bucket_name,
            credentials_path=kwargs.get("credentials_path")
        )

    else:
        raise ValueError(f"Unknown storage provider: {provider}")
