"""PDF document loader service using Docling.

This module provides PDFLoaderService which uses LangChain's DoclingLoader
for advanced PDF parsing with superior layout understanding.


"""

import logging
import asyncio
from pathlib import Path
from typing import List, Optional
from langchain_core.documents import Document
from langchain_docling import DoclingLoader
from app.services.file_validator import FileValidatorService

logger = logging.getLogger(__name__)


class PDFLoaderService:
    """Service for loading PDF documents using Docling."""

    def __init__(self, max_file_size: Optional[int] = None):
        """Initialize PDF loader service.

        Args:
            max_file_size: Optional custom max file size for validation
        """
        self.validator = FileValidatorService(max_file_size=max_file_size)
        logger.info("Initialized PDFLoaderService with Docling")

    async def load_pdf(
        self,
        file_path: Path,
        use_chunking: bool = False
    ) -> List[Document]:
        """Load a PDF file using Docling.

        Args:
            file_path: Path to the PDF file
            use_chunking: Whether to use Docling's built-in chunking

        Returns:
            List of LangChain Document objects

        Raises:
            SecurityError: If file validation fails
        """
        # Validate file security
        self.validator.validate(
            file_path,
            expected_mime_types=["application/pdf"]
        )

        logger.info(f"Loading PDF from: {file_path}")

        # Use DoclingLoader for PDF parsing
        loader = DoclingLoader(
            file_path=str(file_path)
        )

        # Run in executor since DoclingLoader.load() is synchronous
        loop = asyncio.get_event_loop()
        documents = await loop.run_in_executor(None, loader.load)

        logger.info(f"Loaded {len(documents)} document(s) from {file_path}")

        return documents
