"""Custom exceptions for IntelliRAG application.

Author: IntelliRAG Team
Date: 2025-10-21
"""


class IntelliRAGError(Exception):
    """Base exception for all IntelliRAG errors."""
    pass


class DatabaseServiceError(IntelliRAGError):
    """Base exception for database service errors."""
    pass


class DuplicateResourceError(DatabaseServiceError):
    """Resource already exists in the database."""
    pass


class ResourceNotFoundError(DatabaseServiceError):
    """Requested resource not found in the database."""
    pass


class DatabaseConnectionError(DatabaseServiceError):
    """Database connection failed or is unavailable."""
    pass


class ValidationError(IntelliRAGError):
    """Input validation failed."""
    pass


class InvalidFileError(ValidationError):
    """File validation failed (size, type, hash, etc.)."""
    pass


class StorageError(IntelliRAGError):
    """Storage service error (MinIO/S3)."""
    pass
