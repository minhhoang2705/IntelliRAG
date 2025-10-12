"""Base handler abstract class for document preprocessing."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, List, Optional


class SecurityError(Exception):
    """Raised when security validation fails."""
    pass


class BaseHandler(ABC):
    """Abstract base class for all document handlers."""

    # Security constants
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB default

    @abstractmethod
    def validate(self, file_path: Path) -> bool:
        """
        Validate if the file can be processed by this handler.

        Args:
            file_path: Path to the file to validate

        Returns:
            True if the file can be processed, False otherwise
        """
        pass

    @abstractmethod
    def process(self, file_path: Path, **kwargs) -> Dict[str, Any]:
        """
        Process the document and return structured data.

        Args:
            file_path: Path to the file to process
            **kwargs: Additional processing options

        Returns:
            Dictionary containing processed data including text and metadata
        """
        pass

    @abstractmethod
    def extract_text(self, file_path: Path) -> str:
        """
        Extract text content from the document.

        Args:
            file_path: Path to the file to extract text from

        Returns:
            Extracted text as a string
        """
        pass

    def secure_validate(self, file_path: Path) -> bool:
        """Perform security validations on file."""
        try:
            # Prevent access to sensitive system files
            resolved_path = file_path.resolve(strict=True)
        except (OSError, RuntimeError) as e:
            raise SecurityError(f"Failed to resolve path: {str(e)}")

        path_str = str(resolved_path)

        # Block access to common sensitive directories
        import os
        import platform

        sensitive_paths = ['/etc/', '/sys/', '/proc/', '/root/']
        if platform.system() == 'Windows':
            sensitive_paths.extend(['C:\\Windows\\', 'C:\\Program Files\\'])

        # Also check if trying to escape allowed directory
        # Define allowed base directory (e.g., upload directory)
        # allowed_base = Path('/path/to/allowed/uploads').resolve()
        # if not resolved_path.is_relative_to(allowed_base):
        #     raise SecurityError("Path outside allowed directory")

        for sensitive in sensitive_paths:
            if path_str.startswith(sensitive):
                raise SecurityError("Path traversal detected")

        # Check file size (use resolved_path to avoid TOCTOU)
        try:
            file_size = resolved_path.stat().st_size
        except (OSError, FileNotFoundError) as e:
            raise SecurityError(f"Failed to access file: {str(e)}")

        if file_size > self.MAX_FILE_SIZE:
            raise SecurityError(f"File size exceeds {self.MAX_FILE_SIZE} bytes")

        # Validate magic bytes if EXPECTED_MIME_TYPES is defined
        if hasattr(self, 'EXPECTED_MIME_TYPES'):
            import magic
            try:
                mime_type = magic.from_file(str(file_path), mime=True)
                if mime_type not in self.EXPECTED_MIME_TYPES:
                    raise SecurityError(f"Invalid file type: {mime_type}")
            except Exception as e:
                # If magic fails, raise security error
                raise SecurityError(f"Failed to validate file type: {str(e)}")

        return True

    def extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """
        Extract metadata from the file.

        Args:
            file_path: Path to the file

        Returns:
            Dictionary containing file metadata
        """
        return {
            "filename": file_path.name,
            "file_path": str(file_path),
            "file_extension": file_path.suffix.lower(),
        }
