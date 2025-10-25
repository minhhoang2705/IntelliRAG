"""URL/Web document loader service using LangChain.

Date: 2025-10-24
"""

from typing import List
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.documents import Document
import asyncio
import logging

logger = logging.getLogger(__name__)


class URLLoaderService:
    """Service for loading web pages from URLs."""

    def __init__(self):
        """Initialize URL loader service."""
        logger.info("Initialized URLLoaderService")

    async def load_url(self, url: str) -> List[Document]:
        """Load content from a single URL.

        Args:
            url: Web page URL to load

        Returns:
            List of LangChain Document objects
        """
        logger.info(f"Loading URL: {url}")

        loader = WebBaseLoader(url)
        loop = asyncio.get_event_loop()
        documents = await loop.run_in_executor(None, loader.load)

        logger.info(f"Loaded {len(documents)} document(s) from {url}")
        return documents

    async def load_urls(self, urls: List[str]) -> List[Document]:
        """Load content from multiple URLs concurrently.

        Args:
            urls: List of web page URLs to load

        Returns:
            List of LangChain Document objects
        """
        logger.info(f"Loading {len(urls)} URLs concurrently")

        loader = WebBaseLoader(urls)
        loop = asyncio.get_event_loop()
        documents = await loop.run_in_executor(None, loader.load)

        logger.info(f"Loaded {len(documents)} document(s) from {len(urls)} URLs")
        return documents
