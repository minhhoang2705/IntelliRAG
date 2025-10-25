"""GCS document loader service using LangChain.

Date: 2025-10-24
"""

from typing import List, Optional, Callable
from langchain_community.document_loaders import GCSFileLoader, GCSDirectoryLoader
from langchain_core.documents import Document
from langchain_core.document_loaders.base import BaseLoader
import asyncio
import logging

logger = logging.getLogger(__name__)


class GCSLoaderService:
    """Service for loading documents from Google Cloud Storage."""

    def __init__(self, project_name: str, bucket: str):
        """Initialize GCS loader service.

        Args:
            project_name: GCP project ID
            bucket: GCS bucket name
        """
        self.project_name = project_name
        self.bucket = bucket
        logger.info(
            f"Initialized GCSLoaderService for project: {project_name}, "
            f"bucket: {bucket}"
        )

    async def load_file(self, blob: str) -> List[Document]:
        """Load a single file from GCS.

        Args:
            blob: Path to the file in the GCS bucket (e.g., "folder/file.txt")

        Returns:
            List of LangChain Document objects
        """
        logger.info(f"Loading file from GCS: gs://{self.bucket}/{blob}")

        loader = GCSFileLoader(
            project_name=self.project_name,
            bucket=self.bucket,
            blob=blob
        )
        loop = asyncio.get_event_loop()
        documents = await loop.run_in_executor(None, loader.load)

        logger.info(f"Loaded {len(documents)} document(s) from {blob}")
        return documents

    async def load_directory(
        self,
        prefix: str = "",
        loader_func: Optional[Callable[[str], BaseLoader]] = None,
        continue_on_failure: bool = False
    ) -> List[Document]:
        """Load all files from a GCS directory/prefix.

        Args:
            prefix: Directory prefix in GCS bucket (e.g., "documents/")
            loader_func: Optional custom loader function for specific file types
            continue_on_failure: Whether to continue loading if a file fails

        Returns:
            List of LangChain Document objects
        """
        logger.info(
            f"Loading directory from GCS: gs://{self.bucket}/{prefix}"
        )

        loader = GCSDirectoryLoader(
            project_name=self.project_name,
            bucket=self.bucket,
            prefix=prefix,
            loader_func=loader_func,
            continue_on_failure=continue_on_failure
        )
        loop = asyncio.get_event_loop()
        documents = await loop.run_in_executor(None, loader.load)

        logger.info(
            f"Loaded {len(documents)} document(s) from prefix '{prefix}'"
        )
        return documents
