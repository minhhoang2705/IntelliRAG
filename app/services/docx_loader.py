"""DOCX document loader service using LangChain.


"""

from typing import List
from langchain_community.document_loaders import Docx2txtLoader
from langchain_core.documents import Document
import asyncio
import logging

logger = logging.getLogger(__name__)


class DOCXLoaderService:
    """Service for loading Microsoft Word documents (.docx)."""

    def __init__(self):
        """Initialize DOCX loader service."""
        logger.info("Initialized DOCXLoaderService")

    async def load_file(self, file_path: str) -> List[Document]:
        """Load a single DOCX file.

        Args:
            file_path: Path to the DOCX file (local path or URL)

        Returns:
            List of LangChain Document objects
        """
        logger.info(f"Loading DOCX file: {file_path}")

        loader = Docx2txtLoader(file_path)
        loop = asyncio.get_event_loop()
        documents = await loop.run_in_executor(None, loader.load)

        logger.info(f"Loaded {len(documents)} document(s) from {file_path}")
        return documents
