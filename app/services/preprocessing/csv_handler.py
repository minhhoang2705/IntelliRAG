"""CSV file handler for document preprocessing."""

from pathlib import Path
from typing import Dict, Any, List
import csv
import io

from .base import BaseHandler


class CSVHandler(BaseHandler):
    """Handler for processing CSV files."""

    SUPPORTED_EXTENSIONS = {'.csv'}

    def validate(self, file_path: Path) -> bool:
        """
        Validate if the file can be processed by this handler.

        Args:
            file_path: Path to the file to validate

        Returns:
            True if the file can be processed, False otherwise
        """
        # Check file exists
        if not file_path.exists():
            return False

        # Check file extension
        if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            return False

        return True

    def extract_text(self, file_path: Path) -> str:
        """
        Extract text content from the CSV file.

        Args:
            file_path: Path to the file to extract text from

        Returns:
            Extracted text as a formatted string
        """
        try:
            with open(file_path, 'r', encoding='utf-8', newline='') as f:
                # Read CSV content
                content = f.read()

                if not content.strip():
                    return ""

                # Detect delimiter
                sniffer = csv.Sniffer()
                try:
                    dialect = sniffer.sniff(content[:1024])
                    delimiter = dialect.delimiter
                except csv.Error:
                    delimiter = ','

                # Parse CSV
                f.seek(0)
                reader = csv.reader(f, delimiter=delimiter)
                rows = list(reader)

                if not rows:
                    return ""

                # Format as readable text
                text_lines = []
                for row in rows:
                    text_lines.append(" | ".join(row))

                return "\n".join(text_lines)

        except Exception as e:
            # Return empty string on error
            return ""

    def process(self, file_path: Path, **kwargs) -> Dict[str, Any]:
        """
        Process the CSV file and return structured data.

        Args:
            file_path: Path to the file to process
            **kwargs: Additional processing options
                - chunk_size: Maximum size of each chunk in characters
                - overlap: Number of characters to overlap between chunks

        Returns:
            Dictionary containing processed data including text, metadata, and structured data
        """
        # Extract text
        text = self.extract_text(file_path)

        # Parse structured data
        structured_data, columns, row_count = self._parse_csv_data(file_path)

        # Extract metadata
        metadata = self._extract_csv_metadata(
            file_path, row_count, len(columns), columns
        )

        # Chunk text if requested
        chunk_size = kwargs.get('chunk_size', 1000)
        overlap = kwargs.get('overlap', 100)

        if text:
            chunks = self.chunk_text(text, chunk_size=chunk_size, overlap=overlap)
        else:
            chunks = []

        return {
            'text': text,
            'metadata': metadata,
            'chunks': chunks,
            'structured_data': structured_data
        }

    def _parse_csv_data(self, file_path: Path) -> tuple[List[Dict[str, Any]], List[str], int]:
        """
        Parse CSV file and return structured data.

        Args:
            file_path: Path to the CSV file

        Returns:
            Tuple of (structured_data, columns, row_count)
        """
        try:
            with open(file_path, 'r', encoding='utf-8', newline='') as f:
                content = f.read()

                if not content.strip():
                    return [], [], 0

                # Detect delimiter
                sniffer = csv.Sniffer()
                try:
                    dialect = sniffer.sniff(content[:1024])
                    delimiter = dialect.delimiter
                except csv.Error:
                    delimiter = ','

                # Parse CSV with DictReader
                f.seek(0)
                reader = csv.DictReader(f, delimiter=delimiter)

                columns = reader.fieldnames or []
                rows = list(reader)

                return rows, columns, len(rows)

        except Exception:
            return [], [], 0

    def _extract_csv_metadata(
        self, file_path: Path, row_count: int, column_count: int, columns: List[str]
    ) -> Dict[str, Any]:
        """
        Extract metadata from the CSV file.

        Args:
            file_path: Path to the file
            row_count: Number of data rows (excluding header)
            column_count: Number of columns
            columns: List of column names

        Returns:
            Dictionary containing file metadata
        """
        # Get base metadata
        metadata = self.extract_metadata(file_path)

        # Add CSV-specific metadata
        metadata.update({
            'row_count': row_count,
            'column_count': column_count,
            'columns': columns,
        })

        return metadata
