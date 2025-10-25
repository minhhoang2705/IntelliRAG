"""Unit tests for PDFLoaderService using Docling.

This module tests the PDFLoaderService which uses LangChain's DoclingLoader
for advanced PDF parsing with layout understanding.

Following TDD methodology - batch per service approach.

Date: 2025-10-25
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from langchain_core.documents import Document


class TestPDFLoaderInitialization:
    """Test PDFLoaderService initialization."""

    def test_loader_initializes_successfully(self):
        """Test that PDF loader initializes without errors."""
        from app.services.pdf_loader import PDFLoaderService

        loader = PDFLoaderService()
        assert loader is not None

    def test_loader_has_file_validator(self):
        """Test that loader has a file validator instance."""
        from app.services.pdf_loader import PDFLoaderService

        loader = PDFLoaderService()
        assert hasattr(loader, 'validator')
        assert loader.validator is not None


class TestPDFLoading:
    """Test PDF document loading functionality."""

    @pytest.mark.asyncio
    async def test_load_single_pdf_returns_documents(self, tmp_path):
        """Test loading a single PDF file returns Document objects."""
        from app.services.pdf_loader import PDFLoaderService

        # Create a minimal PDF file
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b'%PDF-1.4\n%\xE2\xE3\xCF\xD3\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n')

        loader = PDFLoaderService()

        # Mock the actual Docling loading to avoid complex PDF parsing in tests
        with patch('app.services.pdf_loader.DoclingLoader') as mock_docling:
            mock_docling_instance = MagicMock()
            mock_docling_instance.load.return_value = [
                Document(page_content="Test content", metadata={"source": str(pdf_file)})
            ]
            mock_docling.return_value = mock_docling_instance

            documents = await loader.load_pdf(pdf_file)

            assert len(documents) > 0
            assert all(isinstance(doc, Document) for doc in documents)

    @pytest.mark.asyncio
    async def test_load_pdf_validates_file_first(self, tmp_path):
        """Test that load_pdf validates file before loading."""
        from app.services.pdf_loader import PDFLoaderService
        from app.services.file_validator import SecurityError

        # Create oversized PDF (larger than 50MB)
        oversized_pdf = tmp_path / "oversized.pdf"
        with open(oversized_pdf, 'wb') as f:
            f.write(b'%PDF-1.4\n')
            f.write(b'x' * (51 * 1024 * 1024))  # 51MB

        loader = PDFLoaderService()

        with pytest.raises(SecurityError):
            await loader.load_pdf(oversized_pdf)

    @pytest.mark.asyncio
    async def test_load_pdf_validates_mime_type(self, tmp_path):
        """Test that load_pdf validates PDF MIME type."""
        from app.services.pdf_loader import PDFLoaderService
        from app.services.file_validator import SecurityError

        # Create fake PDF with wrong content
        fake_pdf = tmp_path / "fake.pdf"
        fake_pdf.write_text("This is not a real PDF")

        loader = PDFLoaderService()

        with pytest.raises(SecurityError, match="Invalid file type"):
            await loader.load_pdf(fake_pdf)

    @pytest.mark.asyncio
    async def test_load_pdf_with_docling_chunking(self, tmp_path):
        """Test loading PDF with Docling's built-in chunking."""
        from app.services.pdf_loader import PDFLoaderService

        pdf_file = tmp_path / "chunked.pdf"
        pdf_file.write_bytes(b'%PDF-1.4\n%\xE2\xE3\xCF\xD3\n')

        loader = PDFLoaderService()

        with patch('app.services.pdf_loader.DoclingLoader') as mock_docling:
            # Simulate multiple chunks returned by Docling
            mock_docling_instance = MagicMock()
            mock_docling_instance.load.return_value = [
                Document(page_content="Chunk 1", metadata={"source": str(pdf_file), "chunk_index": 0}),
                Document(page_content="Chunk 2", metadata={"source": str(pdf_file), "chunk_index": 1}),
            ]
            mock_docling.return_value = mock_docling_instance

            documents = await loader.load_pdf(pdf_file, use_chunking=True)

            assert len(documents) == 2
            assert documents[0].page_content == "Chunk 1"
            assert documents[1].page_content == "Chunk 2"


class TestPDFMetadata:
    """Test metadata extraction from PDF documents."""

    @pytest.mark.asyncio
    async def test_load_pdf_preserves_metadata(self, tmp_path):
        """Test that loaded documents preserve metadata."""
        from app.services.pdf_loader import PDFLoaderService

        pdf_file = tmp_path / "document.pdf"
        pdf_file.write_bytes(b'%PDF-1.4\n%\xE2\xE3\xCF\xD3\n')

        loader = PDFLoaderService()

        with patch('app.services.pdf_loader.DoclingLoader') as mock_docling:
            mock_docling_instance = MagicMock()
            mock_docling_instance.load.return_value = [
                Document(
                    page_content="Content",
                    metadata={
                        "source": str(pdf_file),
                        "page_count": 1,
                        "file_type": "pdf"
                    }
                )
            ]
            mock_docling.return_value = mock_docling_instance

            documents = await loader.load_pdf(pdf_file)

            assert "source" in documents[0].metadata
            assert "page_count" in documents[0].metadata
            assert documents[0].metadata["file_type"] == "pdf"


class TestErrorHandling:
    """Test error handling in PDF loading."""

    @pytest.mark.asyncio
    async def test_load_nonexistent_pdf_raises_error(self):
        """Test that loading nonexistent file raises appropriate error."""
        from app.services.pdf_loader import PDFLoaderService
        from app.services.file_validator import SecurityError

        loader = PDFLoaderService()
        nonexistent = Path("/tmp/nonexistent_file_123456789.pdf")

        with pytest.raises(SecurityError, match="Failed to access file"):
            await loader.load_pdf(nonexistent)

    @pytest.mark.asyncio
    async def test_load_directory_raises_error(self, tmp_path):
        """Test that loading a directory raises appropriate error."""
        from app.services.pdf_loader import PDFLoaderService
        from app.services.file_validator import SecurityError

        loader = PDFLoaderService()

        with pytest.raises(SecurityError):
            await loader.load_pdf(tmp_path)


class TestDoclingIntegration:
    """Test integration with Docling features."""

    @pytest.mark.asyncio
    async def test_supports_tables_extraction(self, tmp_path):
        """Test that loader can handle PDFs with tables (Docling feature)."""
        from app.services.pdf_loader import PDFLoaderService

        pdf_with_tables = tmp_path / "tables.pdf"
        pdf_with_tables.write_bytes(b'%PDF-1.4\n%\xE2\xE3\xCF\xD3\n')

        loader = PDFLoaderService()

        with patch('app.services.pdf_loader.DoclingLoader') as mock_docling:
            mock_docling_instance = MagicMock()
            mock_docling_instance.load.return_value = [
                Document(
                    page_content="| Header1 | Header2 |\n|---------|---------|",
                    metadata={"source": str(pdf_with_tables), "has_tables": True}
                )
            ]
            mock_docling.return_value = mock_docling_instance

            documents = await loader.load_pdf(pdf_with_tables)

            assert len(documents) > 0
            assert "has_tables" in documents[0].metadata

    @pytest.mark.asyncio
    async def test_supports_complex_layouts(self, tmp_path):
        """Test that loader can handle complex PDF layouts (Docling strength)."""
        from app.services.pdf_loader import PDFLoaderService

        complex_pdf = tmp_path / "complex.pdf"
        complex_pdf.write_bytes(b'%PDF-1.4\n%\xE2\xE3\xCF\xD3\n')

        loader = PDFLoaderService()

        with patch('app.services.pdf_loader.DoclingLoader') as mock_docling:
            mock_docling_instance = MagicMock()
            mock_docling_instance.load.return_value = [
                Document(
                    page_content="Extracted text from complex layout",
                    metadata={"source": str(complex_pdf), "layout_type": "multi_column"}
                )
            ]
            mock_docling.return_value = mock_docling_instance

            documents = await loader.load_pdf(complex_pdf)

            assert len(documents) > 0
            assert documents[0].page_content is not None
