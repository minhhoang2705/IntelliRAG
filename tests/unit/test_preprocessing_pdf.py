"""Tests for the PDFHandler class."""

import pytest
from pathlib import Path
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock


def test_pdf_handler_inherits_base_handler():
    """Test that PDFHandler inherits from BaseHandler."""
    from app.services.preprocessing.pdf import PDFHandler
    from app.services.preprocessing.base import BaseHandler

    assert issubclass(PDFHandler, BaseHandler)


def test_pdf_handler_can_be_instantiated():
    """Test that PDFHandler can be instantiated."""
    from app.services.preprocessing.pdf import PDFHandler

    handler = PDFHandler()
    assert handler is not None


def test_pdf_handler_validate_accepts_pdf_files():
    """Test that PDFHandler validates .pdf files correctly."""
    from app.services.preprocessing.pdf import PDFHandler

    handler = PDFHandler()

    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp.write(b"%PDF-1.4\ntest")
        tmp_path = Path(tmp.name)

    try:
        assert handler.validate(tmp_path) is True
    finally:
        os.unlink(tmp_path)


def test_pdf_handler_validate_rejects_non_pdf_files():
    """Test that PDFHandler rejects non-.pdf files."""
    from app.services.preprocessing.pdf import PDFHandler

    handler = PDFHandler()

    test_files = [
        ('.txt', b'Plain text'),
        ('.docx', b'DOCX content'),
        ('.csv', b'CSV content')
    ]

    for suffix, content in test_files:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            assert handler.validate(tmp_path) is False
        finally:
            os.unlink(tmp_path)


def test_pdf_handler_validate_checks_file_exists():
    """Test that PDFHandler validates file existence."""
    from app.services.preprocessing.pdf import PDFHandler

    handler = PDFHandler()
    non_existent_path = Path("/non/existent/file.pdf")

    assert handler.validate(non_existent_path) is False


@patch('app.services.preprocessing.pdf.DocumentConverter')
def test_pdf_handler_extract_text(mock_converter_class):
    """Test that PDFHandler extracts text from PDF using Docling."""
    from app.services.preprocessing.pdf import PDFHandler

    # Mock the Docling DocumentConverter
    mock_converter = MagicMock()
    mock_converter_class.return_value = mock_converter

    # Mock the conversion result
    mock_result = MagicMock()
    mock_result.document.export_to_markdown.return_value = "# Test PDF\n\nThis is test content from PDF."
    mock_converter.convert.return_value = mock_result

    handler = PDFHandler()

    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp.write(b"%PDF-1.4\ntest")
        tmp_path = Path(tmp.name)

    try:
        extracted = handler.extract_text(tmp_path)

        assert isinstance(extracted, str)
        assert len(extracted) > 0
        assert "Test PDF" in extracted or "test content" in extracted

    finally:
        os.unlink(tmp_path)


@patch('app.services.preprocessing.pdf.DocumentConverter')
def test_pdf_handler_process_returns_structured_data(mock_converter_class):
    """Test that PDFHandler.process returns properly structured data."""
    from app.services.preprocessing.pdf import PDFHandler

    # Mock the Docling DocumentConverter
    mock_converter = MagicMock()
    mock_converter_class.return_value = mock_converter

    # Mock the conversion result
    mock_result = MagicMock()
    mock_result.document.export_to_markdown.return_value = "# Test PDF\n\nPage 1 content.\n\nPage 2 content."
    mock_result.pages = [Mock(), Mock()]  # 2 pages
    mock_converter.convert.return_value = mock_result

    handler = PDFHandler()

    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp.write(b"%PDF-1.4\ntest")
        tmp_path = Path(tmp.name)

    try:
        result = handler.process(tmp_path)

        # Check structure
        assert isinstance(result, dict)
        assert 'text' in result
        assert 'metadata' in result
        assert 'chunks' in result

        # Check metadata
        metadata = result['metadata']
        assert 'filename' in metadata
        assert 'file_path' in metadata
        assert 'file_extension' in metadata
        assert 'page_count' in metadata

        assert metadata['filename'] == tmp_path.name
        assert metadata['file_extension'] == '.pdf'
        assert metadata['page_count'] == 2

    finally:
        os.unlink(tmp_path)


@patch('app.services.preprocessing.pdf.DocumentConverter')
def test_pdf_handler_process_with_chunking(mock_converter_class):
    """Test that PDFHandler processes with chunking."""
    from app.services.preprocessing.pdf import PDFHandler

    # Mock the Docling DocumentConverter
    mock_converter = MagicMock()
    mock_converter_class.return_value = mock_converter

    # Mock the conversion result with long text
    long_text = "A" * 100 + " " + "B" * 100
    mock_result = MagicMock()
    mock_result.document.export_to_markdown.return_value = long_text
    mock_result.pages = [Mock()]
    mock_converter.convert.return_value = mock_result

    handler = PDFHandler()

    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp.write(b"%PDF-1.4\ntest")
        tmp_path = Path(tmp.name)

    try:
        result = handler.process(tmp_path, chunk_size=50, overlap=10)

        assert 'chunks' in result
        chunks = result['chunks']
        assert len(chunks) > 1  # Should be chunked
        # Chunks should now be dicts with 'text' and 'metadata'
        assert all(isinstance(chunk, dict) for chunk in chunks)
        assert all('text' in chunk and 'metadata' in chunk for chunk in chunks)
        # Allow some buffer for token-based chunking
        assert all(len(chunk['text']) <= 60 for chunk in chunks)
        # Verify metadata structure
        for i, chunk in enumerate(chunks):
            assert 'chunk_index' in chunk['metadata']
            assert 'start_position' in chunk['metadata']
            assert 'end_position' in chunk['metadata']
            assert chunk['metadata']['chunk_index'] == i

    finally:
        os.unlink(tmp_path)


@patch('app.services.preprocessing.pdf.DocumentConverter')
def test_pdf_handler_handles_empty_pdf(mock_converter_class):
    """Test that PDFHandler handles PDFs with no text gracefully."""
    from app.services.preprocessing.pdf import PDFHandler

    # Mock the Docling DocumentConverter
    mock_converter = MagicMock()
    mock_converter_class.return_value = mock_converter

    # Mock empty result
    mock_result = MagicMock()
    mock_result.document.export_to_markdown.return_value = ""
    mock_result.pages = []
    mock_converter.convert.return_value = mock_result

    handler = PDFHandler()

    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp.write(b"%PDF-1.4\ntest")
        tmp_path = Path(tmp.name)

    try:
        result = handler.process(tmp_path)

        assert result['text'] == ""
        assert result['metadata']['page_count'] == 0
        assert result['chunks'] == []

    finally:
        os.unlink(tmp_path)


@patch('app.services.preprocessing.pdf.DocumentConverter')
def test_pdf_handler_handles_multipage_pdf(mock_converter_class):
    """Test that PDFHandler handles multi-page PDFs."""
    from app.services.preprocessing.pdf import PDFHandler

    # Mock the Docling DocumentConverter
    mock_converter = MagicMock()
    mock_converter_class.return_value = mock_converter

    # Mock multi-page result
    mock_result = MagicMock()
    mock_result.document.export_to_markdown.return_value = "Page 1\nPage 2\nPage 3\nPage 4\nPage 5"
    mock_result.pages = [Mock() for _ in range(5)]  # 5 pages
    mock_converter.convert.return_value = mock_result

    handler = PDFHandler()

    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp.write(b"%PDF-1.4\ntest")
        tmp_path = Path(tmp.name)

    try:
        result = handler.process(tmp_path)

        assert result['metadata']['page_count'] == 5
        assert 'Page 1' in result['text']

    finally:
        os.unlink(tmp_path)


@patch('app.services.preprocessing.pdf.DocumentConverter')
def test_pdf_handler_handles_conversion_errors(mock_converter_class):
    """Test that PDFHandler handles conversion errors gracefully."""
    from app.services.preprocessing.pdf import PDFHandler

    # Mock the Docling DocumentConverter to raise an error
    mock_converter = MagicMock()
    mock_converter_class.return_value = mock_converter
    mock_converter.convert.side_effect = Exception("Conversion failed")

    handler = PDFHandler()

    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp.write(b"%PDF-1.4\ntest")
        tmp_path = Path(tmp.name)

    try:
        # Should handle error gracefully
        result = handler.extract_text(tmp_path)
        assert result == ""  # Returns empty string on error

    finally:
        os.unlink(tmp_path)
