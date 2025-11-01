"""File validation service for secure file processing.

This module provides FileValidatorService which handles all security validations:
- File size limits
- Path traversal protection
- MIME type validation
- Metadata extraction

Extracted from the old BaseHandler to support both old and new loaders.

Date: 2025-10-25
"""

import logging
import time
import platform
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Raised when security validation fails."""
    pass


class FileValidatorService:
    """Service for validating files before processing to prevent security vulnerabilities."""

    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB default

    def __init__(self, max_file_size: Optional[int] = None):
        """Initialize FileValidatorService.

        Args:
            max_file_size: Maximum allowed file size in bytes (default: 50MB)
        """
        self.max_file_size = max_file_size if max_file_size is not None else self.MAX_FILE_SIZE
        logger.info(f"Initialized FileValidatorService with max_file_size={self.max_file_size} bytes")

    def validate(
        self,
        file_path: Path,
        expected_mime_types: Optional[List[str]] = None
    ) -> bool:
        """Perform comprehensive security validation on file.

        Args:
            file_path: Path to the file to validate
            expected_mime_types: Optional list of expected MIME types (e.g., ["application/pdf"])

        Returns:
            True if validation passes

        Raises:
            SecurityError: If any security validation fails
        """
        # Resolve path to prevent symlink attacks
        try:
            resolved_path = file_path.resolve(strict=True)
        except (OSError, RuntimeError) as e:
            raise SecurityError(f"Failed to access file: {str(e)}")

        path_str = str(resolved_path)

        # Block access to sensitive directories
        sensitive_paths = ['/etc/', '/sys/', '/proc/', '/root/']
        if platform.system() == 'Windows':
            sensitive_paths.extend(['C:\\Windows\\', 'C:\\Program Files\\'])

        for sensitive in sensitive_paths:
            if path_str.startswith(sensitive):
                raise SecurityError("Path traversal detected")

        # Check file existence and type
        try:
            if not resolved_path.exists():
                raise SecurityError("Failed to access file")
            if not resolved_path.is_file():
                raise SecurityError("Path is not a file")
        except (OSError, FileNotFoundError) as e:
            raise SecurityError(f"Failed to access file: {str(e)}")

        # Check file size
        try:
            file_size = resolved_path.stat().st_size
        except (OSError, FileNotFoundError) as e:
            raise SecurityError(f"Failed to access file: {str(e)}")

        if file_size > self.max_file_size:
            raise SecurityError(
                f"File size exceeds {self.max_file_size} bytes")

        # Validate MIME type if expected types are specified
        if expected_mime_types is not None:
            try:
                import magic
            except ImportError:
                raise SecurityError(
                    "python-magic library required for MIME type validation. "
                    "Install with: pip install python-magic"
                )

            try:
                mime_type = magic.from_file(str(resolved_path), mime=True)
                if mime_type not in expected_mime_types:
                    raise SecurityError(f"Invalid file type: {mime_type}")
            except magic.MagicException as e:
                raise SecurityError(f"Failed to validate file type: {str(e)}")

        return True

    def extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from the file.

        Args:
            file_path: Path to the file

        Returns:
            Dictionary containing file metadata (filename, file_path, file_extension)
        """
        return {
            "filename": file_path.name,
            "file_path": str(file_path),
            "file_extension": file_path.suffix.lower(),
        }
