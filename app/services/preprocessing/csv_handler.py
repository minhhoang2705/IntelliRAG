"""CSV file handler for document preprocessing."""

import logging
from pathlib import Path
from typing import Dict, Any, List
import csv
import io

from .base import BaseHandler

logger = logging.getLogger(__name__)


class CSVBombError(Exception):
    """Exception raised when CSV file exceeds security limits."""
    pass


class CSVHandler(BaseHandler):
    """Handler for processing CSV files."""

    SUPPORTED_EXTENSIONS = {'.csv'}
    EXPECTED_MIME_TYPES = {'text/csv', 'text/plain',
                           'application/csv', 'application/octet-stream',
                           'inode/x-empty'}

    # Security limits to prevent CSV-bomb DoS attacks
    MAX_ROWS = 100000  # Maximum number of data rows
    MAX_COLUMNS = 1000  # Maximum number of columns
    VALID_DELIMITERS = {',', ';', '\t', '|'}  # Valid CSV delimiters

    def __init__(self, chunker_type: str = "langchain", model_id: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """Initialize CSVHandler with DocumentChunker.

        Args:
            chunker_type: Type of chunker to use ("langchain", "hybrid", "hierarchical")
            model_id: HuggingFace model ID for tokenization
        """
        super().__init__()
        from .chunker import DocumentChunker
        self.chunker = DocumentChunker(
            chunker_type=chunker_type, model_id=model_id)

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

        # Check file size (e.g., max 100MB)
        max_size = 100 * 1024 * 1024  # 100MB
        if file_path.stat().st_size > max_size:
            return False

        return True

    def _detect_delimiter(self, sample: str) -> str:
        """
        Detect and validate the delimiter used in a CSV sample.

        Args:
            sample: Sample text from the CSV file

        Returns:
            Validated delimiter character
        """
        sniffer = csv.Sniffer()
        try:
            dialect = sniffer.sniff(sample)
            delimiter = dialect.delimiter

            # Validate delimiter is in the allowed set
            if delimiter not in self.VALID_DELIMITERS:
                logger.warning(
                    "Detected delimiter '%s' not in valid set, defaulting to comma",
                    delimiter
                )
                delimiter = ','

            return delimiter
        except csv.Error as e:
            logger.warning(
                "Failed to detect CSV delimiter (operation: delimiter_detection, sample_length: %d): %s. Defaulting to comma.",
                len(sample),
                str(e),
                exc_info=True
            )
            return ','

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
                delimiter = self._detect_delimiter(content[:1024])

                # Parse CSV with streaming to avoid loading entire file into memory
                f.seek(0)
                reader = csv.reader(f, delimiter=delimiter)

                # Get first row to check column count
                try:
                    first_row = next(reader)
                    if len(first_row) > self.MAX_COLUMNS:
                        raise CSVBombError(
                            f"CSV file has too many columns: {len(first_row)} exceeds limit of {self.MAX_COLUMNS}"
                        )

                    # Stream rows instead of loading all into memory
                    text_lines = [" | ".join(first_row)]
                    row_count = 1

                    for row in reader:
                        if row_count >= self.MAX_ROWS:
                            raise CSVBombError(
                                f"CSV file has too many rows: exceeds limit of {self.MAX_ROWS}"
                            )
                        text_lines.append(" | ".join(row))
                        row_count += 1

                    return "\n".join(text_lines)

                except StopIteration:
                    # Empty CSV
                    return ""

        except CSVBombError:
            # Re-raise CSV bomb errors
            raise
        except FileNotFoundError:
            logger.error(
                "File not found during text extraction (operation: extract_text, file_path: %s)",
                file_path,
                exc_info=True
            )
            return ""
        except PermissionError:
            logger.error(
                "Permission denied during text extraction (operation: extract_text, file_path: %s)",
                file_path,
                exc_info=True
            )
            return ""
        except UnicodeDecodeError as e:
            logger.error(
                "Encoding error during text extraction (operation: extract_text, file_path: %s, encoding: utf-8, position: %d): %s",
                file_path,
                e.start if hasattr(e, 'start') else 0,
                str(e),
                exc_info=True
            )
            return ""
        except csv.Error as e:
            logger.error(
                "CSV parsing error during text extraction (operation: extract_text, file_path: %s, row_count: %d): %s",
                file_path,
                row_count if 'row_count' in locals() else 0,
                str(e),
                exc_info=True
            )
            return ""
        except Exception as e:
            logger.exception(
                "Unexpected error during text extraction (operation: extract_text, file_path: %s): %s",
                file_path,
                str(e)
            )
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
        # Security validation - must happen first
        self.secure_validate(file_path)

        # Parse CSV once and get both structured data and text
        structured_data, columns, row_count, text = self._parse_csv_with_text(
            file_path)

        # Build metadata from row_count and columns
        metadata = self._extract_csv_metadata(
            file_path, row_count, len(columns), columns
        )

        # Chunk text using DocumentChunker with custom parameters from kwargs
        if text:
            # Get chunking parameters from kwargs or use defaults
            chunk_size = kwargs.get('chunk_size', 512)
            overlap = kwargs.get('overlap', 100)

            # Create DocumentChunker with requested parameters
            from .chunker import DocumentChunker
            chunker = DocumentChunker(
                chunk_size=chunk_size,
                chunk_overlap=overlap,
                chunker_type=self.chunker.chunker_type,
                model_id=self.chunker.model_id
            )

            metadata_for_chunks = metadata.copy()
            chunks = chunker.chunk_text(text, metadata=metadata_for_chunks)
        else:
            chunks = []

        return {
            'text': text,
            'metadata': metadata,
            'chunks': chunks,
            'structured_data': structured_data
        }

    def _parse_csv_with_text(self, file_path: Path) -> tuple[List[Dict[str, Any]], List[str], int, str]:
        """
        Parse CSV file once and return both structured data and text representation.

        Args:
            file_path: Path to the CSV file

        Returns:
            Tuple of (structured_data, columns, row_count, text)

        Raises:
            CSVBombError: If CSV exceeds security limits
        """
        try:
            with open(file_path, 'r', encoding='utf-8', newline='') as f:
                content = f.read()

                if not content.strip():
                    return [], [], 0, ""

                # Detect delimiter once
                delimiter = self._detect_delimiter(content[:1024])

                # Parse CSV with DictReader for structured data
                f.seek(0)
                reader = csv.DictReader(f, delimiter=delimiter)

                # Validate column count BEFORE reading any data
                columns = reader.fieldnames or []
                if len(columns) > self.MAX_COLUMNS:
                    raise CSVBombError(
                        f"CSV file has too many columns: {len(columns)} exceeds limit of {self.MAX_COLUMNS}"
                    )

                # Stream rows instead of loading all into memory
                rows = []
                text_lines = []

                # Add header to text representation
                if columns:
                    text_lines.append(" | ".join(columns))

                # Stream and process rows
                for i, row in enumerate(reader):
                    if i >= self.MAX_ROWS:
                        raise CSVBombError(
                            f"CSV file has too many rows: exceeds limit of {self.MAX_ROWS}"
                        )
                    rows.append(row)
                    # Generate text representation on the fly
                    if columns:
                        text_lines.append(" | ".join(
                            str(row.get(col, '')) for col in columns))

                row_count = len(rows)
                text = "\n".join(text_lines)

                return rows, columns, row_count, text

        except CSVBombError:
            # Re-raise CSV bomb errors
            raise
        except FileNotFoundError:
            logger.error(
                "File not found during CSV parsing with text (operation: parse_csv_with_text, file_path: %s)",
                file_path,
                exc_info=True
            )
            return [], [], 0, ""
        except PermissionError:
            logger.error(
                "Permission denied during CSV parsing with text (operation: parse_csv_with_text, file_path: %s)",
                file_path,
                exc_info=True
            )
            return [], [], 0, ""
        except UnicodeDecodeError as e:
            logger.error(
                "Encoding error during CSV parsing with text (operation: parse_csv_with_text, file_path: %s, encoding: utf-8, position: %d): %s",
                file_path,
                e.start if hasattr(e, 'start') else 0,
                str(e),
                exc_info=True
            )
            return [], [], 0, ""
        except csv.Error as e:
            logger.error(
                "CSV parsing error during parsing with text (operation: parse_csv_with_text, file_path: %s, row_count: %d): %s",
                file_path,
                len(rows) if 'rows' in locals() else 0,
                str(e),
                exc_info=True
            )
            return [], [], 0, ""
        except Exception as e:
            logger.exception(
                "Unexpected error during CSV parsing with text (operation: parse_csv_with_text, file_path: %s, row_count: %d, column_count: %d): %s",
                file_path,
                len(rows) if 'rows' in locals() else 0,
                len(columns) if 'columns' in locals() else 0,
                str(e)
            )
            return [], [], 0, ""

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
