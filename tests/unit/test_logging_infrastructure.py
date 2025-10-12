"""Unit tests for structured logging infrastructure."""

import pytest
from pathlib import Path
from unittest.mock import patch

from app.services.preprocessing.text import TextHandler
from app.services.preprocessing.pdf import PDFHandler
from app.services.preprocessing.image import ImageHandler


def test_handler_logs_processing_start(tmp_path):
    """Test that handlers log when processing starts."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Test content")

    handler = TextHandler()

    with patch('app.services.preprocessing.text.logger') as mock_logger:
        handler.process(test_file)
        mock_logger.info.assert_called()


def test_pdf_handler_logs_processing_start(tmp_path):
    """Test that PDFHandler logs when processing starts."""
    # Create a minimal valid PDF file
    test_pdf = tmp_path / "test.pdf"
    # PDF magic bytes + minimal structure
    test_pdf.write_bytes(b'%PDF-1.4\n%EOF')

    handler = PDFHandler()

    with patch('app.services.preprocessing.pdf.logger') as mock_logger:
        handler.process(test_pdf)
        # Verify info logging was called during processing
        mock_logger.info.assert_called()


def test_image_handler_logs_processing_start(tmp_path):
    """Test that ImageHandler logs when processing starts."""
    # Create a minimal PNG file (1x1 pixel)
    test_image = tmp_path / "test.png"
    # PNG magic bytes + minimal structure for 1x1 transparent pixel
    png_data = (
        b'\x89PNG\r\n\x1a\n'  # PNG signature
        b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
        b'\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
        b'\r\n-\xb4'
        b'\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    test_image.write_bytes(png_data)

    handler = ImageHandler()

    with patch('app.services.preprocessing.image.logger') as mock_logger:
        handler.process(test_image)
        # Verify info logging was called during processing
        mock_logger.info.assert_called()
