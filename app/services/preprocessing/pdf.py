"""PDF file handler for document preprocessing using Docling with PyMuPDF flattening."""

import logging
from pathlib import Path
from typing import Dict, Any
import tempfile
import fitz  # PyMuPDF
from docling.document_converter import DocumentConverter

from .base import BaseHandler

logger = logging.getLogger(__name__)


class PDFHandler(BaseHandler):
    """Handler for processing PDF files using Docling."""

    SUPPORTED_EXTENSIONS = {'.pdf'}
    EXPECTED_MIME_TYPES = {'application/pdf'}

    def __init__(self, chunker_type: str = "langchain", model_id: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """Initialize the PDF handler with Docling converter and DocumentChunker.

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

    def _flatten_pdf(self, file_path: Path) -> Path:
        """
        Flatten PDF using PyMuPDF to improve Docling processing.

        Args:
            file_path: Path to the original PDF file

        Returns:
            Path to the flattened PDF file (temporary file)
        """
        try:
            # Open PDF with PyMuPDF
            doc = fitz.open(file_path)

            # Create temporary file for flattened PDF
            temp_file = tempfile.NamedTemporaryFile(
                suffix='.pdf', delete=False)
            temp_path = Path(temp_file.name)
            temp_file.close()

            # Save flattened version
            doc.save(temp_path, deflate=True, garbage=4, clean=True)
            doc.close()

            return temp_path

        except Exception:
            # If flattening fails, return original path
            return file_path

    def extract_text(self, file_path: Path) -> str:
        """
        Extract text content from the PDF file using PyMuPDF flattening + Docling.

        Args:
            file_path: Path to the file to extract text from

        Returns:
            Extracted text as a string
        """
        flattened_path = None
        try:
            # Flatten PDF first
            flattened_path = self._flatten_pdf(file_path)

            # Convert PDF using Docling
            result = self.converter.convert(flattened_path)

            # Export to markdown format for readable text
            text = result.document.export_to_markdown()

            return text

        except Exception as e:
            # Return empty string on error
            return ""
        finally:
            # Clean up temporary flattened file if created
            if flattened_path and flattened_path != file_path:
                try:
                    flattened_path.unlink()
                except Exception:
                    pass

    def process(self, file_path: Path, **kwargs) -> Dict[str, Any]:
        """
        Process the PDF file and return structured data.

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
        logger.info(f"Starting PDFHandler processing for {file_path.name}")

        flattened_path = None
        try:
            # Flatten PDF first
            flattened_path = self._flatten_pdf(file_path)

            # Convert PDF using Docling
            result = self.converter.convert(flattened_path)

            # Extract text
            text = result.document.export_to_markdown()

            # Get page count
            page_count = len(result.pages) if hasattr(result, 'pages') else 0

            # Extract metadata
            metadata = self._extract_pdf_metadata(file_path, page_count)

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
                'metadata': self._extract_pdf_metadata(file_path, 0),
                'chunks': []
            }
        finally:
            # Clean up temporary flattened file if created
            if flattened_path and flattened_path != file_path:
                try:
                    flattened_path.unlink()
                except Exception:
                    pass

    def _extract_pdf_metadata(self, file_path: Path, page_count: int) -> Dict[str, Any]:
        """
        Extract metadata from the PDF file.

        Args:
            file_path: Path to the file
            page_count: Number of pages in the PDF

        Returns:
            Dictionary containing file metadata
        """
        # Get base metadata
        metadata = self.extract_metadata(file_path)

        # Add PDF-specific metadata
        metadata.update({
            'page_count': page_count,
        })

        return metadata
