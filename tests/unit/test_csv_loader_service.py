"""Unit tests for CSVLoaderService using LangChain.

Following TDD methodology - batch per service approach.

Date: 2025-10-25
"""

import pytest
from langchain_core.documents import Document


class TestCSVLoaderInitialization:
    """Test CSVLoaderService initialization."""

    def test_loader_initializes_successfully(self):
        """Test that CSV loader initializes without errors."""
        from app.services.csv_loader import CSVLoaderService

        loader = CSVLoaderService()
        assert loader is not None

    def test_loader_has_file_validator(self):
        """Test that loader has a file validator instance."""
        from app.services.csv_loader import CSVLoaderService

        loader = CSVLoaderService()
        assert hasattr(loader, 'validator')


class TestCSVLoading:
    """Test CSV document loading functionality."""

    @pytest.mark.asyncio
    async def test_load_csv_returns_documents(self, tmp_path):
        """Test loading CSV file returns Document objects."""
        from app.services.csv_loader import CSVLoaderService

        csv_file = tmp_path / "test.csv"
        csv_file.write_text("name,age,city\nAlice,30,NYC\nBob,25,LA")

        loader = CSVLoaderService()
        documents = await loader.load_csv(csv_file)

        assert len(documents) > 0
        assert all(isinstance(doc, Document) for doc in documents)

    @pytest.mark.asyncio
    async def test_load_csv_validates_file_first(self, tmp_path):
        """Test that load_csv validates file before loading."""
        from app.services.csv_loader import CSVLoaderService
        from app.services.file_validator import SecurityError

        oversized_csv = tmp_path / "oversized.csv"
        with open(oversized_csv, 'w') as f:
            f.write('x' * (51 * 1024 * 1024))

        loader = CSVLoaderService()

        with pytest.raises(SecurityError):
            await loader.load_csv(oversized_csv)

    @pytest.mark.asyncio
    async def test_load_csv_with_custom_delimiter(self, tmp_path):
        """Test loading CSV with custom delimiter."""
        from app.services.csv_loader import CSVLoaderService

        csv_file = tmp_path / "custom.csv"
        csv_file.write_text("name;age;city\nAlice;30;NYC")

        loader = CSVLoaderService()
        documents = await loader.load_csv(csv_file, delimiter=';')

        assert len(documents) > 0
