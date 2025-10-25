"""Text document loader service using LangChain.

Date: 2025-10-25
"""

import logging
import asyncio
from pathlib import Path
from typing import List, Optional
from langchain_core.documents import Document
from langchain_community.document_loaders import TextLoader
from app.services.file_validator import FileValidatorService

logger = logging.getLogger(__name__)


class TextLoaderService:
    """Service for loading plain text documents using LangChain."""

    def __init__(self, max_file_size: Optional[int] = None):
        """Initialize text loader service.

        Args:
            max_file_size: Optional custom max file size for validation
        """
        self.validator = FileValidatorService(max_file_size=max_file_size)
        logger.info("Initialized TextLoaderService")

    async def load_text(
        self,
        file_path: Path
    ) -> List[Document]:
        """Load a plain text file.

        Args:
            file_path: Path to the text file

        Returns:
            List of LangChain Document objects

        Raises:
            SecurityError: If file validation fails
        """
        # Validate file security
        self.validator.validate(
            file_path,
            expected_mime_types=None  # Skip MIME validation for text files
        )

        logger.info(f"Loading text from: {file_path}")

        # Use LangChain TextLoader
        loader = TextLoader(
            file_path=str(file_path),
            encoding='utf-8',
            autodetect_encoding=True
        )

        # Run in executor since loader.load() is synchronous
        loop = asyncio.get_event_loop()
        documents = await loop.run_in_executor(None, loader.load)

        logger.info(f"Loaded {len(documents)} document(s) from {file_path}")

        return documents
