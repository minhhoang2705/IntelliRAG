"""Tests for the ImageHandler class."""

import pytest
from pathlib import Path
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock


def test_image_handler_inherits_base_handler():
    """Test that ImageHandler inherits from BaseHandler."""
    from app.services.preprocessing.image import ImageHandler
    from app.services.preprocessing.base import BaseHandler

    assert issubclass(ImageHandler, BaseHandler)


def test_image_handler_can_be_instantiated():
    """Test that ImageHandler can be instantiated."""
    from app.services.preprocessing.image import ImageHandler

    handler = ImageHandler()
    assert handler is not None


def test_image_handler_validate_accepts_image_files():
    """Test that ImageHandler validates image files correctly."""
    from app.services.preprocessing.image import ImageHandler

    handler = ImageHandler()

    image_extensions = ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp']

    for ext in image_extensions:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(b"\xFF\xD8\xFF")  # JPEG signature
            tmp_path = Path(tmp.name)

        try:
            assert handler.validate(tmp_path) is True
        finally:
            os.unlink(tmp_path)


def test_image_handler_validate_rejects_non_image_files():
    """Test that ImageHandler rejects non-image files."""
    from app.services.preprocessing.image import ImageHandler

    handler = ImageHandler()

    test_files = [
        ('.txt', b'Plain text'),
        ('.pdf', b'PDF content'),
        ('.docx', b'DOCX content')
    ]

    for suffix, content in test_files:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            assert handler.validate(tmp_path) is False
        finally:
            os.unlink(tmp_path)


def test_image_handler_validate_checks_file_exists():
    """Test that ImageHandler validates file existence."""
    from app.services.preprocessing.image import ImageHandler

    handler = ImageHandler()
    non_existent_path = Path("/non/existent/file.jpg")

    assert handler.validate(non_existent_path) is False


@patch('app.services.preprocessing.image.DocumentConverter')
def test_image_handler_extract_text(mock_converter_class):
    """Test that ImageHandler extracts text from images using Docling."""
    from app.services.preprocessing.image import ImageHandler

    # Mock the Docling DocumentConverter
    mock_converter = MagicMock()
    mock_converter_class.return_value = mock_converter

    # Mock the conversion result
    mock_result = MagicMock()
    mock_result.document.export_to_markdown.return_value = "Extracted text from image via OCR."
    mock_converter.convert.return_value = mock_result

    handler = ImageHandler()

    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        tmp.write(b"\xFF\xD8\xFF")
        tmp_path = Path(tmp.name)

    try:
        extracted = handler.extract_text(tmp_path)

        assert isinstance(extracted, str)
        assert len(extracted) > 0
        assert "Extracted text" in extracted or "OCR" in extracted

    finally:
        os.unlink(tmp_path)


@patch('app.services.preprocessing.image.DocumentConverter')
def test_image_handler_process_returns_structured_data(mock_converter_class):
    """Test that ImageHandler.process returns properly structured data."""
    from app.services.preprocessing.image import ImageHandler

    # Mock the Docling DocumentConverter
    mock_converter = MagicMock()
    mock_converter_class.return_value = mock_converter

    # Mock the conversion result
    mock_result = MagicMock()
    mock_result.document.export_to_markdown.return_value = "Text extracted from image."
    mock_converter.convert.return_value = mock_result

    handler = ImageHandler()

    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        tmp.write(b"\x89PNG\r\n\x1a\n")  # PNG signature
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
        assert 'image_format' in metadata

        assert metadata['filename'] == tmp_path.name
        assert metadata['file_extension'] == '.png'

    finally:
        os.unlink(tmp_path)


@patch('app.services.preprocessing.image.DocumentConverter')
def test_image_handler_process_with_chunking(mock_converter_class):
    """Test that ImageHandler processes with chunking."""
    from app.services.preprocessing.image import ImageHandler

    # Mock the Docling DocumentConverter
    mock_converter = MagicMock()
    mock_converter_class.return_value = mock_converter

    # Mock the conversion result with long text
    long_text = "A" * 100 + " " + "B" * 100
    mock_result = MagicMock()
    mock_result.document.export_to_markdown.return_value = long_text
    mock_converter.convert.return_value = mock_result

    handler = ImageHandler()

    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        tmp.write(b"\xFF\xD8\xFF")
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


@patch('app.services.preprocessing.image.DocumentConverter')
def test_image_handler_handles_empty_image(mock_converter_class):
    """Test that ImageHandler handles images with no text gracefully."""
    from app.services.preprocessing.image import ImageHandler

    # Mock the Docling DocumentConverter
    mock_converter = MagicMock()
    mock_converter_class.return_value = mock_converter

    # Mock empty result
    mock_result = MagicMock()
    mock_result.document.export_to_markdown.return_value = ""
    mock_converter.convert.return_value = mock_result

    handler = ImageHandler()

    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        tmp.write(b"\xFF\xD8\xFF")
        tmp_path = Path(tmp.name)

    try:
        result = handler.process(tmp_path)

        assert result['text'] == ""
        assert result['chunks'] == []

    finally:
        os.unlink(tmp_path)


@patch('app.services.preprocessing.image.Image')
@patch('app.services.preprocessing.image.DocumentConverter')
def test_image_handler_extracts_image_metadata(mock_converter_class, mock_image_class):
    """Test that ImageHandler extracts image dimensions."""
    from app.services.preprocessing.image import ImageHandler

    # Mock PIL Image
    mock_image = MagicMock()
    mock_image.size = (1920, 1080)
    mock_image.format = 'JPEG'
    mock_image_class.open.return_value.__enter__.return_value = mock_image

    # Mock the Docling DocumentConverter
    mock_converter = MagicMock()
    mock_converter_class.return_value = mock_converter

    mock_result = MagicMock()
    mock_result.document.export_to_markdown.return_value = "Test text"
    mock_converter.convert.return_value = mock_result

    handler = ImageHandler()

    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        tmp.write(b"\xFF\xD8\xFF")
        tmp_path = Path(tmp.name)

    try:
        result = handler.process(tmp_path)

        metadata = result['metadata']
        assert 'width' in metadata
        assert 'height' in metadata
        assert metadata['width'] == 1920
        assert metadata['height'] == 1080

    finally:
        os.unlink(tmp_path)


@patch('app.services.preprocessing.image.DocumentConverter')
def test_image_handler_handles_conversion_errors(mock_converter_class):
    """Test that ImageHandler handles conversion errors gracefully."""
    from app.services.preprocessing.image import ImageHandler

    # Mock the Docling DocumentConverter to raise an error
    mock_converter = MagicMock()
    mock_converter_class.return_value = mock_converter
    mock_converter.convert.side_effect = Exception("Conversion failed")

    handler = ImageHandler()

    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        tmp.write(b"\xFF\xD8\xFF")
        tmp_path = Path(tmp.name)

    try:
        # Should handle error gracefully
        result = handler.extract_text(tmp_path)
        assert result == ""  # Returns empty string on error

    finally:
        os.unlink(tmp_path)
