"""Unit tests for URL/Web document loader service.

Tests for loading web pages using LangChain's WebBaseLoader.
This service provides async loading capabilities for web content.

Date: 2025-10-24
"""

import pytest
from unittest.mock import patch
from langchain_core.documents import Document


class TestURLLoaderService:
    """Test suite for URL/Web document loader service."""

    @pytest.mark.asyncio
    async def test_load_single_url(self, mocker):
        """Test loading content from a single URL.

        RED Phase: Will fail because URLLoaderService doesn't exist.
        """
        from app.services.url_loader import URLLoaderService

        # Mock LangChain's WebBaseLoader
        mock_document = Document(
            page_content="Sample web page content",
            metadata={"source": "https://example.com", "title": "Example Page"}
        )

        mock_loader = mocker.Mock()
        mock_loader.load.return_value = [mock_document]

        with patch('app.services.url_loader.WebBaseLoader', return_value=mock_loader):
            service = URLLoaderService()

            # Test loading a single URL
            documents = await service.load_url(url="https://example.com")

            assert documents is not None
            assert len(documents) == 1
            assert documents[0].page_content == "Sample web page content"
            assert documents[0].metadata["source"] == "https://example.com"

    @pytest.mark.asyncio
    async def test_load_multiple_urls(self, mocker):
        """Test loading content from multiple URLs concurrently.

        RED Phase: Will test multi-URL loading capability.
        """
        from app.services.url_loader import URLLoaderService

        # Mock documents from multiple URLs
        mock_documents = [
            Document(
                page_content="Content from first URL",
                metadata={"source": "https://example.com", "title": "Example"}
            ),
            Document(
                page_content="Content from second URL",
                metadata={"source": "https://google.com", "title": "Google"}
            )
        ]

        mock_loader = mocker.Mock()
        mock_loader.load.return_value = mock_documents

        with patch('app.services.url_loader.WebBaseLoader', return_value=mock_loader):
            service = URLLoaderService()

            # Test loading multiple URLs
            documents = await service.load_urls(
                urls=["https://example.com", "https://google.com"]
            )

            assert documents is not None
            assert len(documents) == 2
            assert documents[0].page_content == "Content from first URL"
            assert documents[1].page_content == "Content from second URL"
