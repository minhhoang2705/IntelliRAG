"""Unit tests for DOCX document loader service.

Tests for loading Microsoft Word documents using LangChain's Docx2txtLoader.
This service provides async loading capabilities for .docx files.

Date: 2025-10-24
"""

import pytest
from unittest.mock import patch
from langchain_core.documents import Document


class TestDOCXLoaderService:
    """Test suite for DOCX document loader service."""

    @pytest.mark.asyncio
    async def test_load_single_docx_file(self, mocker):
        """Test loading a single DOCX file.

        RED Phase: Will fail because DOCXLoaderService doesn't exist.
        """
        from app.services.docx_loader import DOCXLoaderService

        # Mock LangChain's Docx2txtLoader
        mock_document = Document(
            page_content="Sample content from DOCX file",
            metadata={"source": "/path/to/sample.docx"}
        )

        mock_loader = mocker.Mock()
        mock_loader.load.return_value = [mock_document]

        with patch('app.services.docx_loader.Docx2txtLoader', return_value=mock_loader):
            service = DOCXLoaderService()

            # Test loading a single DOCX file
            documents = await service.load_file(file_path="/path/to/sample.docx")

            assert documents is not None
            assert len(documents) == 1
            assert documents[0].page_content == "Sample content from DOCX file"
            assert documents[0].metadata["source"] == "/path/to/sample.docx"

    @pytest.mark.asyncio
    async def test_load_docx_from_url(self, mocker):
        """Test loading DOCX file from remote URL.

        RED Phase: Will test URL loading capability.
        """
        from app.services.docx_loader import DOCXLoaderService

        # Mock document loaded from URL
        mock_document = Document(
            page_content="Content from remote DOCX",
            metadata={"source": "https://example.com/document.docx"}
        )

        mock_loader = mocker.Mock()
        mock_loader.load.return_value = [mock_document]

        with patch('app.services.docx_loader.Docx2txtLoader', return_value=mock_loader):
            service = DOCXLoaderService()

            # Test loading from URL
            documents = await service.load_file(
                file_path="https://example.com/document.docx"
            )

            assert documents is not None
            assert len(documents) == 1
            assert documents[0].page_content == "Content from remote DOCX"
            assert "https://example.com/document.docx" in documents[0].metadata["source"]
