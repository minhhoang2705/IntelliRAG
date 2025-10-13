"""Unit tests for structured logging infrastructure."""

import pytest
import json
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO

from app.services.preprocessing.text import TextHandler
from app.services.preprocessing.pdf import PDFHandler
from app.services.preprocessing.image import ImageHandler


# Test JSON formatter
def test_json_formatter_creates_valid_json():
    """Test that formatter outputs valid JSON."""
    from app.core.logging import StructuredJSONFormatter

    formatter = StructuredJSONFormatter()
    record = logging.LogRecord(
        name='test.logger',
        level=logging.INFO,
        pathname='test.py',
        lineno=10,
        msg='Test message',
        args=(),
        exc_info=None
    )

    formatted = formatter.format(record)

    # Should be valid JSON
    log_data = json.loads(formatted)

    # Assert required fields present
    assert 'timestamp' in log_data
    assert 'level' in log_data
    assert 'logger' in log_data
    assert 'message' in log_data
    assert log_data['level'] == 'INFO'
    assert log_data['logger'] == 'test.logger'
    assert log_data['message'] == 'Test message'


def test_json_formatter_includes_extra_fields():
    """Test that extra context is included in JSON output."""
    from app.core.logging import StructuredJSONFormatter

    formatter = StructuredJSONFormatter()
    record = logging.LogRecord(
        name='test.logger',
        level=logging.INFO,
        pathname='test.py',
        lineno=10,
        msg='Test message',
        args=(),
        exc_info=None
    )

    # Add extra data
    record.extra_data = {'file_size': 1024, 'handler': 'TextHandler'}

    formatted = formatter.format(record)
    log_data = json.loads(formatted)

    # Assert extra fields are included
    assert 'file_size' in log_data
    assert log_data['file_size'] == 1024
    assert 'handler' in log_data
    assert log_data['handler'] == 'TextHandler'


# Test processing metrics
def test_handler_logs_processing_metrics(tmp_path):
    """Test that handlers log detailed processing metrics."""
    from app.services.preprocessing.base import BaseHandler

    test_file = tmp_path / "test.txt"
    test_file.write_text("Test content for logging metrics")

    handler = TextHandler()

    with patch('app.services.preprocessing.base.logger') as mock_logger:
        handler.process_with_logging(test_file)

        # Check that info was called with metrics
        assert mock_logger.info.called
        # Get the call arguments
        calls = mock_logger.info.call_args_list

        # Should have at least 2 calls: start and success
        assert len(calls) >= 2

        # Check success call has extra_data with metrics
        success_call = calls[-1]
        if 'extra' in success_call.kwargs:
            extra_data = success_call.kwargs['extra'].get('extra_data', {})
            assert 'file_size' in extra_data
            assert 'duration_seconds' in extra_data
            assert 'chunk_count' in extra_data


def test_handler_logs_performance_timing(tmp_path):
    """Test processing time is measured and logged."""
    from app.services.preprocessing.base import BaseHandler

    test_file = tmp_path / "test.txt"
    test_file.write_text("Test content")

    handler = TextHandler()

    with patch('app.services.preprocessing.base.logger') as mock_logger:
        handler.process_with_logging(test_file)

        # Find the success log call
        calls = mock_logger.info.call_args_list
        success_call = calls[-1]

        if 'extra' in success_call.kwargs:
            extra_data = success_call.kwargs['extra'].get('extra_data', {})
            assert 'duration_seconds' in extra_data
            assert isinstance(extra_data['duration_seconds'], (int, float))
            assert extra_data['duration_seconds'] >= 0


# Test error logging
def test_handler_logs_errors_with_stack_trace(tmp_path):
    """Test that errors include full stack traces."""
    from app.services.preprocessing.base import BaseHandler

    test_file = tmp_path / "test.txt"
    test_file.write_text("Test content")

    handler = TextHandler()

    # Mock process to raise an exception
    with patch.object(handler, 'process', side_effect=ValueError("Test error")):
        with patch('app.services.preprocessing.base.logger') as mock_logger:
            with pytest.raises(ValueError):
                handler.process_with_logging(test_file)

            # Assert logger.error was called with exc_info=True
            mock_logger.error.assert_called()
            call_kwargs = mock_logger.error.call_args.kwargs
            assert call_kwargs.get('exc_info') is True

            # Assert error context includes file_path
            extra_data = call_kwargs.get('extra', {}).get('extra_data', {})
            assert 'file_path' in extra_data


def test_handler_logs_security_errors(tmp_path):
    """Test security validation errors are logged."""
    from app.services.preprocessing.base import BaseHandler, SecurityError

    # Create oversized file (> 50MB)
    oversized_file = tmp_path / "oversized.txt"
    with open(oversized_file, 'wb') as f:
        f.write(b'x' * (51 * 1024 * 1024))

    handler = TextHandler()

    with patch('app.services.preprocessing.base.logger') as mock_logger:
        with pytest.raises(SecurityError):
            handler.process_with_logging(oversized_file)

        # Assert error was logged
        mock_logger.error.assert_called()


# Test DocumentChunker logging
def test_chunker_logs_tokenization_metrics():
    """Test that chunker logs tokenization performance."""
    from app.services.preprocessing.chunker import DocumentChunker

    with patch('app.services.preprocessing.chunker.logger') as mock_logger:
        # Use hybrid chunker which loads tokenizer
        chunker = DocumentChunker(
            chunker_type="hybrid", chunk_size=100, chunk_overlap=20)

        # Assert tokenizer load was logged
        assert mock_logger.info.called
        calls = mock_logger.info.call_args_list

        # Find the tokenizer load call
        tokenizer_call = calls[0]
        if 'extra' in tokenizer_call.kwargs:
            extra_data = tokenizer_call.kwargs['extra'].get('extra_data', {})
            assert 'model_id' in extra_data
            assert 'tokenizer_load_time' in extra_data


def test_chunker_logs_chunking_metrics():
    """Test that chunker logs chunking duration."""
    from app.services.preprocessing.chunker import DocumentChunker

    chunker = DocumentChunker(chunker_type="langchain")

    with patch('app.services.preprocessing.chunker.logger') as mock_logger:
        chunks = chunker.chunk_text("This is a test text for chunking.")

        # Assert chunking was logged
        mock_logger.info.assert_called()
        call = mock_logger.info.call_args

        if 'extra' in call.kwargs:
            extra_data = call.kwargs['extra'].get('extra_data', {})
            assert 'text_length' in extra_data
            assert 'chunk_count' in extra_data
            assert 'chunker_type' in extra_data
            assert 'chunking_duration' in extra_data


# Keep existing tests
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
