"""Image file handler for document preprocessing using Docling."""

import logging
from pathlib import Path
from typing import Dict, Any
from PIL import Image
from docling.document_converter import DocumentConverter

from .base import BaseHandler

logger = logging.getLogger(__name__)


class ImageHandler(BaseHandler):
    """Handler for processing image files using Docling with OCR."""

    SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp'}
    EXPECTED_MIME_TYPES = {'image/jpeg', 'image/png', 'image/gif', 'image/bmp',
                           'image/tiff', 'image/webp', 'application/octet-stream', 'inode/x-empty', 'text/plain'}

    def __init__(self, chunker_type: str = "langchain", model_id: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """Initialize the Image handler with Docling converter and DocumentChunker.

        Args:
            chunker_type: Type of chunker to use ("langchain", "hybrid", "hierarchical")
            model_id: HuggingFace model ID for tokenization
        """
        super().__init__()
        self.converter = DocumentConverter()
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
        Extract text content from the image file using Docling OCR.

        Args:
            file_path: Path to the file to extract text from

        Returns:
            Extracted text as a string
        """
        try:
            # Convert image using Docling (supports OCR)
            result = self.converter.convert(file_path)

            # Export to markdown format for readable text
            text = result.document.export_to_markdown()

            return text

        except Exception as e:
            # Return empty string on error
            return ""

    def process(self, file_path: Path, **kwargs) -> Dict[str, Any]:
        """
        Process the image file and return structured data.

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
        logger.info(f"Starting ImageHandler processing for {file_path.name}")

        try:
            # Convert image using Docling
            result = self.converter.convert(file_path)

            # Extract text (OCR)
            text = result.document.export_to_markdown()

            # Get image dimensions and format
            width, height, img_format = self._get_image_info(file_path)

            # Extract metadata
            metadata = self._extract_image_metadata(
                file_path, width, height, img_format)

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

        except Exception as e:
            # Return minimal result on error
            return {
                'text': "",
                'metadata': self._extract_image_metadata(file_path, 0, 0, "unknown"),
                'chunks': []
            }

    def _get_image_info(self, file_path: Path) -> tuple[int, int, str]:
        """
        Get image dimensions and format.

        Args:
            file_path: Path to the image file

        Returns:
            Tuple of (width, height, format)
        """
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                img_format = img.format or "unknown"
                return width, height, img_format
        except Exception:
            return 0, 0, "unknown"

    def _extract_image_metadata(
        self, file_path: Path, width: int, height: int, img_format: str
    ) -> Dict[str, Any]:
        """
        Extract metadata from the image file.

        Args:
            file_path: Path to the file
            width: Image width in pixels
            height: Image height in pixels
            img_format: Image format (JPEG, PNG, etc.)

        Returns:
            Dictionary containing file metadata
        """
        # Get base metadata
        metadata = self.extract_metadata(file_path)

        # Add image-specific metadata
        metadata.update({
            'width': width,
            'height': height,
            'image_format': img_format,
        })

        return metadata
