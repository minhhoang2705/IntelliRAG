"""Tests for utility functions."""

import pytest


def test_extract_file_extension_with_extension():
    """Test extracting extension from file with extension."""
    from app.utils import extract_file_extension
    
    assert extract_file_extension("document.pdf") == "pdf"
    assert extract_file_extension("data.csv") == "csv"
    assert extract_file_extension("gs://bucket/file.txt") == "txt"


def test_extract_file_extension_uppercase():
    """Test extension normalization to lowercase."""
    from app.utils import extract_file_extension
    
    assert extract_file_extension("Document.PDF") == "pdf"
    assert extract_file_extension("FILE.TXT") == "txt"


def test_extract_file_extension_gcs_path():
    """Test extracting extension from GCS URI."""
    from app.utils import extract_file_extension
    
    assert extract_file_extension("gs://bucket/folder/document.pdf") == "pdf"
    assert extract_file_extension("gs://test-bucket/data.csv") == "csv"


def test_extract_file_extension_no_extension():
    """Test file path without extension returns 'unknown'."""
    from app.utils import extract_file_extension
    
    assert extract_file_extension("no_extension") == "unknown"
    assert extract_file_extension("gs://bucket/file") == "unknown"


def test_extract_file_extension_multiple_dots():
    """Test file with multiple dots returns last segment."""
    from app.utils import extract_file_extension
    
    assert extract_file_extension("archive.tar.gz") == "gz"
    assert extract_file_extension("backup.2024.pdf") == "pdf"
