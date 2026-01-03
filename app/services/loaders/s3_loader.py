"""
AWS S3 document loader service using LangChain.

This module provides S3LoaderService for loading documents from AWS S3.
"""

from typing import List, Optional, Callable
from langchain_community.document_loaders import S3FileLoader, S3DirectoryLoader
from langchain_core.documents import Document
from langchain_core.document_loaders.base import BaseLoader
from app.exceptions import S3LoaderError
import asyncio
import logging

logger = logging.getLogger(__name__)


class S3LoaderService:
    """Service for loading documents from AWS S3."""

    def __init__(
        self,
        bucket: str,
        region: str = "us-east-1",
        endpoint_url: Optional[str] = None
    ):
        """Initialize S3 loader service.

        Args:
            bucket: S3 bucket name
            region: AWS region (default: us-east-1)
            endpoint_url: Optional endpoint URL for LocalStack testing
        """
        self.bucket = bucket
        self.region = region
        self.endpoint_url = endpoint_url
        logger.info(
            f"Initialized S3LoaderService for bucket: {bucket}, "
            f"region: {region}"
        )

    async def load_file(self, key: str) -> List[Document]:
        """Load a single file from S3.

        Args:
            key: Path to the file in the S3 bucket (e.g., "folder/file.txt")

        Returns:
            List of LangChain Document objects

        Raises:
            S3LoaderError: If file loading fails
        """
        logger.info(f"Loading file from S3: s3://{self.bucket}/{key}")

        try:
            loader = S3FileLoader(
                bucket=self.bucket,
                key=key
            )
            loop = asyncio.get_event_loop()
            documents = await loop.run_in_executor(None, loader.load)

            logger.info(f"Loaded {len(documents)} document(s) from {key}")
            return documents

        except FileNotFoundError as e:
            logger.error(f"S3 file not found: s3://{self.bucket}/{key}")
            raise S3LoaderError(f"File not found: s3://{self.bucket}/{key}") from e

        except PermissionError as e:
            logger.error(f"S3 access denied: s3://{self.bucket}/{key}")
            raise S3LoaderError(f"Access denied: s3://{self.bucket}/{key}") from e

        except Exception as e:
            logger.error(
                f"Failed to load file from S3: s3://{self.bucket}/{key}. "
                f"Error: {type(e).__name__}: {e}"
            )
            raise S3LoaderError(
                f"Failed to load s3://{self.bucket}/{key}: {e}"
            ) from e

    async def load_directory(
        self,
        prefix: str = "",
        loader_func: Optional[Callable[[str], BaseLoader]] = None
    ) -> List[Document]:
        """Load all files from an S3 directory/prefix.

        Args:
            prefix: Directory prefix in S3 bucket (e.g., "documents/")
            loader_func: Optional custom loader function for specific file types

        Returns:
            List of LangChain Document objects

        Raises:
            S3LoaderError: If directory loading fails
        """
        logger.info(
            f"Loading directory from S3: s3://{self.bucket}/{prefix}"
        )

        try:
            loader = S3DirectoryLoader(
                bucket=self.bucket,
                prefix=prefix,
                loader_func=loader_func
            )
            loop = asyncio.get_event_loop()
            documents = await loop.run_in_executor(None, loader.load)

            logger.info(
                f"Loaded {len(documents)} document(s) from prefix '{prefix}'"
            )
            return documents

        except FileNotFoundError as e:
            logger.error(f"S3 prefix not found: s3://{self.bucket}/{prefix}")
            raise S3LoaderError(
                f"Prefix not found: s3://{self.bucket}/{prefix}"
            ) from e

        except PermissionError as e:
            logger.error(f"S3 access denied: s3://{self.bucket}/{prefix}")
            raise S3LoaderError(
                f"Access denied: s3://{self.bucket}/{prefix}"
            ) from e

        except Exception as e:
            logger.error(
                f"Failed to load directory from S3: s3://{self.bucket}/{prefix}. "
                f"Error: {type(e).__name__}: {e}"
            )
            raise S3LoaderError(
                f"Failed to load s3://{self.bucket}/{prefix}: {e}"
            ) from e
