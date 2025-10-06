"""Shared fixtures for testing."""

import pytest
from pathlib import Path


@pytest.fixture
def fixtures_dir():
    """Return the path to the fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_text_content():
    """Provide sample text content for testing."""
    return "This is a sample text document for testing purposes."


@pytest.fixture
def sample_csv_content():
    """Provide sample CSV content for testing."""
    return """Name,Age,City
John Doe,30,New York
Jane Smith,25,Los Angeles
Bob Johnson,35,Chicago"""