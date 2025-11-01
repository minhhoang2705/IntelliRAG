"""Markdown document loader service using LangChain.

Date: 2025-10-24
"""

from typing import List
from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
import asyncio
import logging

logger = logging.getLogger(__name__)


class MarkdownLoaderService:
    """Service for loading Markdown documents (.md files)."""

    def __init__(self):
        """Initialize Markdown loader service."""
        logger.info("Initialized MarkdownLoaderService")

    async def load_file(self, file_path: str) -> List[Document]:
        """Load a single Markdown file.

        Args:
            file_path: Path to the Markdown file

        Returns:
            List of LangChain Document objects
        """
        logger.info(f"Loading Markdown file: {file_path}")

        loader = TextLoader(file_path)
        loop = asyncio.get_event_loop()
        documents = await loop.run_in_executor(None, loader.load)

        logger.info(f"Loaded {len(documents)} document(s) from {file_path}")
        return documents
