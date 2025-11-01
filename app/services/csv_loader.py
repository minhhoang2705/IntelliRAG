"""CSV document loader service using LangChain.

Date: 2025-10-25
"""

import logging
import asyncio
from pathlib import Path
from typing import List, Optional
from langchain_core.documents import Document
from langchain_community.document_loaders.csv_loader import CSVLoader
from app.services.file_validator import FileValidatorService

logger = logging.getLogger(__name__)


class CSVLoaderService:
    """Service for loading CSV documents using LangChain."""

    def __init__(self, max_file_size: Optional[int] = None):
        """Initialize CSV loader service.

        Args:
            max_file_size: Optional custom max file size for validation
        """
        self.validator = FileValidatorService(max_file_size=max_file_size)
        logger.info("Initialized CSVLoaderService")

    async def load_csv(
        self,
        file_path: Path,
        delimiter: str = ','
    ) -> List[Document]:
        """Load a CSV file.

        Args:
            file_path: Path to the CSV file
            delimiter: CSV delimiter (default: ',')

        Returns:
            List of LangChain Document objects

        Raises:
            SecurityError: If file validation fails
        """
        # Validate file security
        self.validator.validate(
            file_path,
            expected_mime_types=None  # CSV has multiple possible MIME types
        )

        logger.info(f"Loading CSV from: {file_path}")

        # Use LangChain CSVLoader
        loader = CSVLoader(
            file_path=str(file_path),
            csv_args={'delimiter': delimiter}
        )

        # Run in executor since loader.load() is synchronous
        loop = asyncio.get_event_loop()
        documents = await loop.run_in_executor(None, loader.load)

        logger.info(f"Loaded {len(documents)} document(s) from {file_path}")

        return documents
