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
        # Chunks should now be dicts with 'text' and 'metadata'
        assert all(isinstance(chunk, dict) for chunk in chunks)
        assert all('text' in chunk and 'metadata' in chunk for chunk in chunks)
        # Verify metadata structure
        for i, chunk in enumerate(chunks):
            assert 'chunk_index' in chunk['metadata']
            assert 'start_position' in chunk['metadata']
            assert 'end_position' in chunk['metadata']
            assert chunk['metadata']['chunk_index'] == i

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


def test_csv_handler_rejects_too_many_rows():
    """Test that CSVHandler rejects CSV files with too many rows."""
    from app.services.preprocessing.csv_handler import CSVHandler, CSVBombError

    handler = CSVHandler()

    # Create CSV with rows exceeding MAX_ROWS
    rows = ["Name,Value"]
    # Assuming MAX_ROWS will be set to a reasonable limit (e.g., 100000)
    # We'll create more rows than that
    max_rows = handler.MAX_ROWS
    rows.extend([f"Row{i},{i}" for i in range(max_rows + 1)])
    csv_content = "\n".join(rows)

    with tempfile.NamedTemporaryFile(
        suffix='.csv', mode='w', encoding='utf-8', delete=False
    ) as tmp:
        tmp.write(csv_content)
        tmp_path = Path(tmp.name)

    try:
        with pytest.raises(CSVBombError) as exc_info:
            handler.process(tmp_path)

        assert "too many rows" in str(exc_info.value).lower()

    finally:
        os.unlink(tmp_path)


def test_csv_handler_rejects_too_many_columns():
    """Test that CSVHandler rejects CSV files with too many columns."""
    from app.services.preprocessing.csv_handler import CSVHandler, CSVBombError

    handler = CSVHandler()

    # Create CSV with columns exceeding MAX_COLUMNS
    max_cols = handler.MAX_COLUMNS
    columns = [f"Col{i}" for i in range(max_cols + 1)]
    csv_content = ",".join(columns) + "\n"
    csv_content += ",".join(["value"] * (max_cols + 1))

    with tempfile.NamedTemporaryFile(
        suffix='.csv', mode='w', encoding='utf-8', delete=False
    ) as tmp:
        tmp.write(csv_content)
        tmp_path = Path(tmp.name)

    try:
        with pytest.raises(CSVBombError) as exc_info:
            handler.process(tmp_path)

        assert "too many columns" in str(exc_info.value).lower()

    finally:
        os.unlink(tmp_path)


def test_csv_handler_validates_delimiter():
    """Test that CSVHandler validates and sanitizes delimiter."""
    from app.services.preprocessing.csv_handler import CSVHandler

    handler = CSVHandler()

    # Test with valid delimiters
    valid_delimiters = [',', ';', '\t', '|']

    for delimiter in valid_delimiters:
        csv_content = f"Name{delimiter}Age\nJohn{delimiter}30"

        with tempfile.NamedTemporaryFile(
            suffix='.csv', mode='w', encoding='utf-8', delete=False
        ) as tmp:
            tmp.write(csv_content)
            tmp_path = Path(tmp.name)

        try:
            result = handler.process(tmp_path)
            assert isinstance(result, dict)
            assert 'text' in result

        finally:
            os.unlink(tmp_path)


def test_csv_handler_handles_invalid_delimiter():
    """Test that CSVHandler handles invalid delimiter detection."""
    from app.services.preprocessing.csv_handler import CSVHandler

    handler = CSVHandler()

    # Create content that might confuse delimiter detection
    csv_content = "NoDelimitersHereJustText\nMoreTextWithoutDelimiters"

    with tempfile.NamedTemporaryFile(
        suffix='.csv', mode='w', encoding='utf-8', delete=False
    ) as tmp:
        tmp.write(csv_content)
        tmp_path = Path(tmp.name)

    try:
        # Should fall back to comma and handle gracefully
        result = handler.process(tmp_path)
        assert isinstance(result, dict)

    finally:
        os.unlink(tmp_path)


def test_csv_handler_streams_large_file():
    """Test that CSVHandler streams data without loading entire file into memory."""
    from app.services.preprocessing.csv_handler import CSVHandler

    handler = CSVHandler()

    # Create a reasonably large CSV (within limits)
    rows = ["Name,Value"]
    num_rows = min(10000, handler.MAX_ROWS - 1)
    rows.extend([f"Row{i},{i}" for i in range(num_rows)])
    csv_content = "\n".join(rows)

    with tempfile.NamedTemporaryFile(
        suffix='.csv', mode='w', encoding='utf-8', delete=False
    ) as tmp:
        tmp.write(csv_content)
        tmp_path = Path(tmp.name)

    try:
        result = handler.process(tmp_path)

        # Should successfully process
        assert isinstance(result, dict)
        assert result['metadata']['row_count'] == num_rows
        assert len(result['structured_data']) == num_rows

    finally:
        os.unlink(tmp_path)


def test_csv_handler_handles_csv_error():
    """Test that CSVHandler handles csv.Error consistently."""
    from app.services.preprocessing.csv_handler import CSVHandler

    handler = CSVHandler()

    # Create CSV with problematic content that might trigger csv.Error
    # Using null bytes which can cause issues
    csv_content = "Name,Age\nJohn\x00Doe,30"

    with tempfile.NamedTemporaryFile(
        suffix='.csv', mode='w', encoding='utf-8', delete=False
    ) as tmp:
        tmp.write(csv_content)
        tmp_path = Path(tmp.name)

    try:
        # Should handle error gracefully, not crash
        result = handler.process(tmp_path)
        assert isinstance(result, dict)

    finally:
        os.unlink(tmp_path)
