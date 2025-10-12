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
        # Prevent access to sensitive system files
        resolved_path = file_path.resolve()
        path_str = str(resolved_path)

        # Block access to common sensitive directories
        sensitive_paths = ['/etc/', '/sys/', '/proc/', '/root/']
        for sensitive in sensitive_paths:
            if path_str.startswith(sensitive):
                raise SecurityError("Path traversal detected")

        # Check file size
        file_size = file_path.stat().st_size
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

    def chunk_text(
        self,
        text: str,
        chunk_size: int = 1000,
        overlap: int = 100
    ) -> List[str]:
        """
        Split text into overlapping chunks.

        Args:
            text: Text to chunk
            chunk_size: Maximum size of each chunk in characters
            overlap: Number of characters to overlap between chunks

        Returns:
            List of text chunks
        """
        if not text:
            return []

        chunks = []
        start = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk = text[start:end]
            chunks.append(chunk)

            # Move to the next chunk with overlap
            start = end - overlap if end < len(text) else end

        return chunks

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