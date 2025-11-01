"""Unit tests for Markdown document loader service.

Tests for loading Markdown files using LangChain's TextLoader.
This service provides async loading capabilities for .md files.

Date: 2025-10-24
"""

import pytest
from unittest.mock import patch
from langchain_core.documents import Document


class TestMarkdownLoaderService:
    """Test suite for Markdown document loader service."""

    @pytest.mark.asyncio
    async def test_load_single_markdown_file(self, mocker):
        """Test loading a single Markdown file.

        RED Phase: Will fail because MarkdownLoaderService doesn't exist.
        """
        from app.services.markdown_loader import MarkdownLoaderService

        # Mock LangChain's TextLoader
        mock_document = Document(
            page_content="# Sample Markdown\n\nThis is **bold** text.",
            metadata={"source": "/path/to/sample.md"}
        )

        mock_loader = mocker.Mock()
        mock_loader.load.return_value = [mock_document]

        with patch('app.services.markdown_loader.TextLoader', return_value=mock_loader):
            service = MarkdownLoaderService()

            # Test loading a single Markdown file
            documents = await service.load_file(file_path="/path/to/sample.md")

            assert documents is not None
            assert len(documents) == 1
            assert "# Sample Markdown" in documents[0].page_content
            assert "**bold**" in documents[0].page_content
            assert documents[0].metadata["source"] == "/path/to/sample.md"
