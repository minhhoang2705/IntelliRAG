"""Unit tests for TextLoaderService using LangChain.

Following TDD methodology - batch per service approach.

Date: 2025-10-25
"""

import pytest
from pathlib import Path
from langchain_core.documents import Document


class TestTextLoaderInitialization:
    """Test TextLoaderService initialization."""

    def test_loader_initializes_successfully(self):
        """Test that text loader initializes without errors."""
        from app.services.text_loader import TextLoaderService

        loader = TextLoaderService()
        assert loader is not None

    def test_loader_has_file_validator(self):
        """Test that loader has a file validator instance."""
        from app.services.text_loader import TextLoaderService

        loader = TextLoaderService()
        assert hasattr(loader, 'validator')


class TestTextLoading:
    """Test text document loading functionality."""

    @pytest.mark.asyncio
    async def test_load_text_returns_documents(self, tmp_path):
        """Test loading text file returns Document objects."""
        from app.services.text_loader import TextLoaderService

        text_file = tmp_path / "test.txt"
        text_file.write_text("This is a test document.\nWith multiple lines.")

        loader = TextLoaderService()
        documents = await loader.load_text(text_file)

        assert len(documents) > 0
        assert all(isinstance(doc, Document) for doc in documents)
        assert "test document" in documents[0].page_content

    @pytest.mark.asyncio
    async def test_load_text_validates_file_first(self, tmp_path):
        """Test that load_text validates file before loading."""
        from app.services.text_loader import TextLoaderService
        from app.services.file_validator import SecurityError

        oversized_text = tmp_path / "oversized.txt"
        with open(oversized_text, 'w') as f:
            f.write('x' * (51 * 1024 * 1024))

        loader = TextLoaderService()

        with pytest.raises(SecurityError):
            await loader.load_text(oversized_text)

    @pytest.mark.asyncio
    async def test_load_text_handles_unicode(self, tmp_path):
        """Test loading text with Unicode characters."""
        from app.services.text_loader import TextLoaderService

        text_file = tmp_path / "unicode.txt"
        text_file.write_text("Hello 世界 🌍", encoding='utf-8')

        loader = TextLoaderService()
        documents = await loader.load_text(text_file)

        assert len(documents) > 0
        assert "世界" in documents[0].page_content
        assert "🌍" in documents[0].page_content
