"""
Storage module for cloud-agnostic object storage.

This module provides abstract interfaces and implementations for different
cloud storage providers (GCS, S3, etc.).
"""

from app.services.storage.base import ObjectStorageProtocol

__all__ = ["ObjectStorageProtocol"]
