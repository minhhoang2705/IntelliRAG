"""Tests for the CSVHandler class."""

import pytest
from pathlib import Path
import tempfile
import os


def test_csv_handler_inherits_base_handler():
    """Test that CSVHandler inherits from BaseHandler."""
    from app.services.preprocessing.csv_handler import CSVHandler
    from app.services.preprocessing.base import BaseHandler

    assert issubclass(CSVHandler, BaseHandler)


def test_csv_handler_can_be_instantiated():
    """Test that CSVHandler can be instantiated."""
    from app.services.preprocessing.csv_handler import CSVHandler

    handler = CSVHandler()
    assert handler is not None


def test_csv_handler_validate_accepts_csv_files():
    """Test that CSVHandler validates .csv files correctly."""
    from app.services.preprocessing.csv_handler import CSVHandler

    handler = CSVHandler()

    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp:
        tmp.write(b"Name,Age\nJohn,30")
        tmp_path = Path(tmp.name)

    try:
        assert handler.validate(tmp_path) is True
    finally:
        os.unlink(tmp_path)


def test_csv_handler_validate_rejects_non_csv_files():
    """Test that CSVHandler rejects non-.csv files."""
    from app.services.preprocessing.csv_handler import CSVHandler

    handler = CSVHandler()

    test_files = [
        ('.txt', b'Plain text'),
        ('.pdf', b'PDF content'),
        ('.xlsx', b'Excel content')
    ]

    for suffix, content in test_files:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            assert handler.validate(tmp_path) is False
        finally:
            os.unlink(tmp_path)


def test_csv_handler_validate_checks_file_exists():
    """Test that CSVHandler validates file existence."""
    from app.services.preprocessing.csv_handler import CSVHandler

    handler = CSVHandler()
    non_existent_path = Path("/non/existent/file.csv")

    assert handler.validate(non_existent_path) is False


def test_csv_handler_extract_text_basic():
    """Test that CSVHandler extracts and formats CSV data as text."""
    from app.services.preprocessing.csv_handler import CSVHandler

    handler = CSVHandler()
    csv_content = """Name,Age,City
John Doe,30,New York
Jane Smith,25,Los Angeles"""

    with tempfile.NamedTemporaryFile(
        suffix='.csv', mode='w', encoding='utf-8', delete=False
    ) as tmp:
        tmp.write(csv_content)
        tmp_path = Path(tmp.name)

    try:
        extracted = handler.extract_text(tmp_path)

        # Should contain the data in readable format
        assert isinstance(extracted, str)
        assert len(extracted) > 0
        assert 'Name' in extracted or 'John Doe' in extracted

    finally:
        os.unlink(tmp_path)


def test_csv_handler_extract_text_different_delimiters():
    """Test that CSVHandler handles different delimiters."""
    from app.services.preprocessing.csv_handler import CSVHandler

    handler = CSVHandler()

    # Test with semicolon delimiter
    csv_content = """Name;Age;City
John Doe;30;New York
Jane Smith;25;Los Angeles"""

    with tempfile.NamedTemporaryFile(
        suffix='.csv', mode='w', encoding='utf-8', delete=False
    ) as tmp:
        tmp.write(csv_content)
        tmp_path = Path(tmp.name)

    try:
        extracted = handler.extract_text(tmp_path)
        assert isinstance(extracted, str)
        assert len(extracted) > 0

    finally:
        os.unlink(tmp_path)


def test_csv_handler_process_returns_structured_data():
    """Test that CSVHandler.process returns properly structured data."""
    from app.services.preprocessing.csv_handler import CSVHandler

    handler = CSVHandler()
    csv_content = """Name,Age,City
John Doe,30,New York
Jane Smith,25,Los Angeles"""

    with tempfile.NamedTemporaryFile(
        suffix='.csv', mode='w', encoding='utf-8', delete=False
    ) as tmp:
        tmp.write(csv_content)
        tmp_path = Path(tmp.name)

    try:
        result = handler.process(tmp_path)

        # Check structure
        assert isinstance(result, dict)
        assert 'text' in result
        assert 'metadata' in result
        assert 'chunks' in result
        assert 'structured_data' in result

        # Check metadata
        metadata = result['metadata']
        assert 'filename' in metadata
        assert 'row_count' in metadata
        assert 'column_count' in metadata
        assert 'columns' in metadata

        assert metadata['row_count'] == 2  # Excluding header
        assert metadata['column_count'] == 3
        assert metadata['columns'] == ['Name', 'Age', 'City']

        # Check structured data
        structured = result['structured_data']
        assert isinstance(structured, list)
        assert len(structured) == 2

    finally:
        os.unlink(tmp_path)


def test_csv_handler_process_with_chunking():
    """Test that CSVHandler processes with chunking."""
    from app.services.preprocessing.csv_handler import CSVHandler

    handler = CSVHandler()

    # Create CSV with multiple rows
    rows = ["Name,Value"]
    rows.extend([f"Row{i},{i}" for i in range(100)])
    csv_content = "\n".join(rows)

    with tempfile.NamedTemporaryFile(
        suffix='.csv', mode='w', encoding='utf-8', delete=False
    ) as tmp:
        tmp.write(csv_content)
        tmp_path = Path(tmp.name)

    try:
        result = handler.process(tmp_path, chunk_size=200, overlap=20)

        assert 'chunks' in result
        chunks = result['chunks']
        assert len(chunks) > 1  # Should be chunked

    finally:
        os.unlink(tmp_path)


def test_csv_handler_handles_empty_csv():
    """Test that CSVHandler handles empty CSV files gracefully."""
    from app.services.preprocessing.csv_handler import CSVHandler

    handler = CSVHandler()

    with tempfile.NamedTemporaryFile(
        suffix='.csv', mode='w', encoding='utf-8', delete=False
    ) as tmp:
        tmp.write("")
        tmp_path = Path(tmp.name)

    try:
        result = handler.process(tmp_path)

        assert result['text'] == ""
        assert result['metadata']['row_count'] == 0
        assert result['chunks'] == []

    finally:
        os.unlink(tmp_path)


def test_csv_handler_handles_csv_with_only_header():
    """Test that CSVHandler handles CSV with only header row."""
    from app.services.preprocessing.csv_handler import CSVHandler

    handler = CSVHandler()

    with tempfile.NamedTemporaryFile(
        suffix='.csv', mode='w', encoding='utf-8', delete=False
    ) as tmp:
        tmp.write("Name,Age,City\n")
        tmp_path = Path(tmp.name)

    try:
        result = handler.process(tmp_path)

        assert result['metadata']['row_count'] == 0  # No data rows
        assert result['metadata']['column_count'] == 3
        assert result['metadata']['columns'] == ['Name', 'Age', 'City']

    finally:
        os.unlink(tmp_path)


def test_csv_handler_handles_malformed_csv():
    """Test that CSVHandler handles malformed CSV gracefully."""
    from app.services.preprocessing.csv_handler import CSVHandler

    handler = CSVHandler()

    # CSV with inconsistent columns
    csv_content = """Name,Age,City
John Doe,30
Jane Smith,25,Los Angeles,Extra"""

    with tempfile.NamedTemporaryFile(
        suffix='.csv', mode='w', encoding='utf-8', delete=False
    ) as tmp:
        tmp.write(csv_content)
        tmp_path = Path(tmp.name)

    try:
        result = handler.process(tmp_path)

        # Should still process, even if malformed
        assert isinstance(result, dict)
        assert 'text' in result
        assert 'metadata' in result

    finally:
        os.unlink(tmp_path)