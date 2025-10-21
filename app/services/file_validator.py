"""File validation service for secure file upload handling.

Author: IntelliRAG Team
Date: 2025-10-21
"""

import logging
from app.exceptions import InvalidFileError

logger = logging.getLogger(__name__)


class FileValidator:
    """Validates files before processing to prevent security vulnerabilities."""

    def __init__(self, max_file_size_mb: int = 50):
        """Initialize FileValidator.
        
        Args:
            max_file_size_mb: Maximum allowed file size in megabytes (default: 50 MB)
        """
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024

    def validate_file_size(self, file_size_bytes: int) -> int:
        """Validate file size is within acceptable limits.
        
        Args:
            file_size_bytes: File size in bytes
            
        Returns:
            The validated file size in bytes
            
        Raises:
            InvalidFileError: If file size is invalid (negative, zero, or too large)
        """
        if file_size_bytes <= 0:
            raise InvalidFileError("File size must be positive")

        if file_size_bytes > self.max_file_size_bytes:
            max_mb = self.max_file_size_bytes / (1024 * 1024)
            actual_mb = file_size_bytes / (1024 * 1024)
            raise InvalidFileError(
                f"File too large: {actual_mb:.2f} MB (max: {max_mb:.0f} MB)"
            )

        return file_size_bytes

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent path traversal attacks.
        
        Args:
            filename: Original filename (may contain path components)
            
        Returns:
            Sanitized filename with path components and dangerous characters removed
            
        Raises:
            InvalidFileError: If filename becomes empty after sanitization
        """
        import re

        # Normalize path separators (handle both Unix and Windows paths)
        # Replace backslashes with forward slashes
        filename = filename.replace('\\', '/')

        # Extract only the basename (last component after /)
        if '/' in filename:
            filename = filename.split('/')[-1]

        # Remove drive letters (C:, D:, etc.)
        filename = re.sub(r'^[A-Z]:', '', filename)

        # Remove any remaining dangerous characters (keep only alphanumeric, spaces, dots, hyphens, underscores)
        filename = re.sub(r'[^\w\s.-]', '', filename)

        # Remove leading/trailing whitespace and dots
        filename = filename.strip('. ')

        if not filename:
            raise InvalidFileError("Invalid filename: empty after sanitization")

        if len(filename) > 255:
            raise InvalidFileError(f"Filename too long: {len(filename)} characters (max: 255)")

        return filename

    # Whitelist of allowed MIME types
    ALLOWED_MIME_TYPES = {
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # .docx
        'text/plain',
        'text/csv',
        'image/jpeg',
        'image/png'
    }

    def validate_mime_type(self, mime_type: str) -> str:
        """Validate MIME type against whitelist.
        
        Args:
            mime_type: MIME type to validate
            
        Returns:
            The validated MIME type
            
        Raises:
            InvalidFileError: If MIME type is not in whitelist
        """
        if not mime_type:
            raise InvalidFileError("MIME type cannot be empty")

        mime_type = mime_type.lower().strip()

        if mime_type not in self.ALLOWED_MIME_TYPES:
            raise InvalidFileError(
                f"MIME type not allowed: {mime_type}. "
                f"Allowed types: {', '.join(sorted(self.ALLOWED_MIME_TYPES))}"
            )

        return mime_type

    def validate_sha256_hash(self, hash_value: str) -> str:
        """Validate SHA-256 hash format.
        
        Args:
            hash_value: SHA-256 hash string to validate
            
        Returns:
            The validated hash in lowercase
            
        Raises:
            InvalidFileError: If hash format is invalid
        """
        import re

        if not hash_value:
            raise InvalidFileError("Hash value cannot be empty")

        hash_value = hash_value.strip().lower()

        # SHA-256 hash must be exactly 64 hexadecimal characters
        if not re.match(r'^[a-f0-9]{64}$', hash_value):
            raise InvalidFileError(
                f"Invalid SHA-256 hash format. Expected 64 hexadecimal characters, got: {len(hash_value)}"
            )

        return hash_value
