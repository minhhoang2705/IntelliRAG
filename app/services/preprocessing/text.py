"""Text file handler for document preprocessing."""

import logging
from pathlib import Path
from typing import Dict, Any
import chardet

from .base import BaseHandler

logger = logging.getLogger(__name__)


class TextHandler(BaseHandler):
    """Handler for processing plain text files."""

    SUPPORTED_EXTENSIONS = {'.txt'}
    EXPECTED_MIME_TYPES = {'text/plain', 'text/markdown',
                           'application/octet-stream', 'inode/x-empty'}

    def __init__(self, chunker_type: str = "langchain", model_id: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """Initialize TextHandler with DocumentChunker.

        Args:
            chunker_type: Type of chunker to use ("langchain", "hybrid", "hierarchical")
            model_id: HuggingFace model ID for tokenization
        """
        super().__init__()
        from .chunker import DocumentChunker
        self.chunker = DocumentChunker(
            chunker_type=chunker_type, model_id=model_id)

    def validate(self, file_path: Path) -> bool:
        """
        Validate if the file can be processed by this handler.

        Args:
            file_path: Path to the file to validate

        Returns:
            True if the file can be processed, False otherwise
        """
        # Check file exists
        if not file_path.exists():
            return False

        # Check file extension
        if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            return False

        return True

    def extract_text(self, file_path: Path) -> str:
        """
        Extract text content from the text file.

        Args:
            file_path: Path to the file to extract text from

        Returns:
            Extracted text as a string
        """
        # Try UTF-8 first
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # If UTF-8 fails, detect encoding
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                result = chardet.detect(raw_data)
                encoding = result['encoding'] or 'utf-8'

            # Read with detected encoding
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                return f.read()

    def process(self, file_path: Path, **kwargs) -> Dict[str, Any]:
        """
        Process the text file and return structured data.

        Args:
            file_path: Path to the file to process
            **kwargs: Additional processing options
                - chunk_size: Maximum size of each chunk in characters
                - overlap: Number of characters to overlap between chunks

        Returns:
            Dictionary containing processed data including text and metadata
        """
        # Security validation - must happen first
        self.secure_validate(file_path)

        # Log processing start
        logger.info(f"Starting TextHandler processing for {file_path.name}")

        # Extract text
        text = self.extract_text(file_path)

        # Extract metadata
        metadata = self._extract_text_metadata(file_path, text)

        # Chunk text using DocumentChunker with custom parameters from kwargs
        if text:
            # Get chunking parameters from kwargs or use defaults
            chunk_size = kwargs.get('chunk_size', 512)
            overlap = kwargs.get('overlap', 100)

            # Create DocumentChunker with requested parameters
            from .chunker import DocumentChunker
            chunker = DocumentChunker(
                chunk_size=chunk_size,
                chunk_overlap=overlap,
                chunker_type=self.chunker.chunker_type,
                model_id=self.chunker.model_id
            )

            metadata_for_chunks = metadata.copy()
            chunks = chunker.chunk_text(text, metadata=metadata_for_chunks)
        else:
            chunks = []

        return {
            'text': text,
            'metadata': metadata,
            'chunks': chunks
        }

    def _extract_text_metadata(self, file_path: Path, text: str) -> Dict[str, Any]:
        """
        Extract metadata from the text file.

        Args:
            file_path: Path to the file
            text: Extracted text content

        Returns:
            Dictionary containing file metadata
        """
        # Get base metadata
        metadata = self.extract_metadata(file_path)

        # Add text-specific metadata
        metadata.update({
            'encoding': 'utf-8',  # We normalize to utf-8
            'char_count': len(text),
            'line_count': len(text.splitlines()) if text else 0,
        })

        return metadata
