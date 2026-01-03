"""Custom exceptions for IntelliRAG application.
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


class LoaderError(IntelliRAGError):
    """Document loader service error."""
    pass


class S3LoaderError(LoaderError):
    """S3 document loading failed."""
    pass


class GCSLoaderError(LoaderError):
    """GCS document loading failed."""
    pass
