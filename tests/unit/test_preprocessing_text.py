"""Tests for the TextHandler class."""

import pytest
from pathlib import Path
import tempfile
import os


def test_text_handler_inherits_base_handler():
    """Test that TextHandler inherits from BaseHandler."""
    from app.services.preprocessing.text import TextHandler
    from app.services.preprocessing.base import BaseHandler

    assert issubclass(TextHandler, BaseHandler)


def test_text_handler_can_be_instantiated():
    """Test that TextHandler can be instantiated."""
    from app.services.preprocessing.text import TextHandler

    handler = TextHandler()
    assert handler is not None


def test_text_handler_validate_accepts_txt_files():
    """Test that TextHandler validates .txt files correctly."""
    from app.services.preprocessing.text import TextHandler

    handler = TextHandler()

    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp:
        tmp.write(b"Test content")
        tmp_path = Path(tmp.name)

    try:
        assert handler.validate(tmp_path) is True
    finally:
        os.unlink(tmp_path)


def test_text_handler_validate_rejects_non_txt_files():
    """Test that TextHandler rejects non-.txt files."""
    from app.services.preprocessing.text import TextHandler

    handler = TextHandler()

    # Test with different file extensions
    test_files = [
        ('.pdf', b'PDF content'),
        ('.docx', b'DOCX content'),
        ('.jpg', b'Image content')
    ]

    for suffix, content in test_files:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            assert handler.validate(tmp_path) is False
        finally:
            os.unlink(tmp_path)


def test_text_handler_validate_checks_file_exists():
    """Test that TextHandler validates file existence."""
    from app.services.preprocessing.text import TextHandler

    handler = TextHandler()
    non_existent_path = Path("/non/existent/file.txt")

    assert handler.validate(non_existent_path) is False


def test_text_handler_extract_text_utf8():
    """Test that TextHandler extracts text from UTF-8 files."""
    from app.services.preprocessing.text import TextHandler

    handler = TextHandler()
    test_content = "Hello, World! 你好世界 🌍"

    with tempfile.NamedTemporaryFile(
        suffix='.txt', mode='w', encoding='utf-8', delete=False
    ) as tmp:
        tmp.write(test_content)
        tmp_path = Path(tmp.name)

    try:
        extracted = handler.extract_text(tmp_path)
        assert extracted == test_content
    finally:
        os.unlink(tmp_path)


def test_text_handler_extract_text_different_encodings():
    """Test that TextHandler handles different encodings gracefully."""
    from app.services.preprocessing.text import TextHandler

    handler = TextHandler()

    # Test with latin-1 encoding
    test_content = "Héllo Wörld"

    with tempfile.NamedTemporaryFile(
        suffix='.txt', mode='w', encoding='latin-1', delete=False
    ) as tmp:
        tmp.write(test_content)
        tmp_path = Path(tmp.name)

    try:
        extracted = handler.extract_text(tmp_path)
        # Should handle encoding gracefully
        assert isinstance(extracted, str)
        assert len(extracted) > 0
    finally:
        os.unlink(tmp_path)


def test_text_handler_process_returns_structured_data():
    """Test that TextHandler.process returns properly structured data."""
    from app.services.preprocessing.text import TextHandler

    handler = TextHandler()
    test_content = "This is test content.\nWith multiple lines.\n"

    with tempfile.NamedTemporaryFile(
        suffix='.txt', mode='w', encoding='utf-8', delete=False
    ) as tmp:
        tmp.write(test_content)
        tmp_path = Path(tmp.name)

    try:
        result = handler.process(tmp_path)

        # Check structure
        assert isinstance(result, dict)
        assert 'text' in result
        assert 'metadata' in result
        assert 'chunks' in result

        # Check content
        assert result['text'] == test_content

        # Check metadata
        metadata = result['metadata']
        assert 'filename' in metadata
        assert 'file_path' in metadata
        assert 'file_extension' in metadata
        assert 'encoding' in metadata
        assert 'char_count' in metadata
        assert 'line_count' in metadata

        assert metadata['filename'] == tmp_path.name
        assert metadata['file_extension'] == '.txt'
        assert metadata['char_count'] == len(test_content)
        assert metadata['line_count'] == 2  # Two lines of text

    finally:
        os.unlink(tmp_path)


def test_text_handler_process_with_chunking():
    """Test that TextHandler processes with chunking."""
    from app.services.preprocessing.text import TextHandler

    handler = TextHandler()

    # Create text that will require chunking
    test_content = "A" * 100 + " " + "B" * 100

    with tempfile.NamedTemporaryFile(
        suffix='.txt', mode='w', encoding='utf-8', delete=False
    ) as tmp:
        tmp.write(test_content)
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


def test_text_handler_handles_empty_file():
    """Test that TextHandler handles empty files gracefully."""
    from app.services.preprocessing.text import TextHandler

    handler = TextHandler()

    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        result = handler.process(tmp_path)

        assert result['text'] == ""
        assert result['metadata']['char_count'] == 0
        assert result['metadata']['line_count'] == 0
        assert result['chunks'] == []

    finally:
        os.unlink(tmp_path)


def test_text_handler_handles_large_file():
    """Test that TextHandler handles large files efficiently."""
    from app.services.preprocessing.text import TextHandler

    handler = TextHandler()

    # Create a "large" file (1MB of text)
    test_content = "Lorem ipsum dolor sit amet. " * 10000

    with tempfile.NamedTemporaryFile(
        suffix='.txt', mode='w', encoding='utf-8', delete=False
    ) as tmp:
        tmp.write(test_content)
        tmp_path = Path(tmp.name)

    try:
        result = handler.process(tmp_path, chunk_size=1000)

        assert result['text'] == test_content
        # Chunks are now dicts with metadata
        assert len(result['chunks']) > 100  # Should create many chunks
        assert all(isinstance(chunk, dict) for chunk in result['chunks'])
        assert result['metadata']['char_count'] == len(test_content)

    finally:
        os.unlink(tmp_path)
