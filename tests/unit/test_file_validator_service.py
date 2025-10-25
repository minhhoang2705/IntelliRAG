"""Unit tests for FileValidatorService.

This module tests the FileValidatorService which encapsulates all security
validations extracted from the old BaseHandler:
- File size validation
- Path traversal protection
- MIME type validation

Following TDD methodology - batch per service approach.

Date: 2025-10-25
"""

import pytest
from pathlib import Path


class TestFileValidatorInitialization:
    """Test FileValidatorService initialization."""

    def test_validator_initializes_with_defaults(self):
        """Test that validator initializes with default max file size."""
        from app.services.file_validator import FileValidatorService

        validator = FileValidatorService()
        assert validator.max_file_size == 50 * 1024 * 1024  # 50MB default

    def test_validator_initializes_with_custom_size(self):
        """Test that validator can be initialized with custom max file size."""
        from app.services.file_validator import FileValidatorService

        custom_size = 100 * 1024 * 1024  # 100MB
        validator = FileValidatorService(max_file_size=custom_size)
        assert validator.max_file_size == custom_size


class TestFileSizeValidation:
    """Test file size limit enforcement."""

    def test_rejects_oversized_files(self, tmp_path):
        """Test that validator rejects files exceeding size limit."""
        from app.services.file_validator import FileValidatorService, SecurityError

        oversized_file = tmp_path / "large_file.txt"
        size_mb = 51
        with open(oversized_file, 'wb') as f:
            f.write(b'x' * (size_mb * 1024 * 1024))

        validator = FileValidatorService()

        with pytest.raises(SecurityError, match="File size exceeds"):
            validator.validate(oversized_file)

    def test_accepts_files_within_limit(self, tmp_path):
        """Test that validator accepts files within size limit."""
        from app.services.file_validator import FileValidatorService

        valid_file = tmp_path / "valid_file.txt"
        with open(valid_file, 'wb') as f:
            f.write(b'x' * (1 * 1024 * 1024))

        validator = FileValidatorService()
        assert validator.validate(valid_file) is True

    def test_accepts_empty_files(self, tmp_path):
        """Test that validator accepts empty files."""
        from app.services.file_validator import FileValidatorService

        empty_file = tmp_path / "empty.txt"
        empty_file.touch()

        validator = FileValidatorService()
        assert validator.validate(empty_file) is True


class TestPathTraversalProtection:
    """Test protection against path traversal attacks."""

    def test_prevents_access_to_etc_directory(self, tmp_path):
        """Test rejection of paths in /etc/ directory."""
        from app.services.file_validator import FileValidatorService, SecurityError

        validator = FileValidatorService()
        system_file = Path("/etc/passwd")

        if not system_file.exists():
            pytest.skip("System file /etc/passwd not available")

        with pytest.raises(SecurityError, match="Path traversal detected"):
            validator.validate(system_file)

    def test_handles_symlink_path_resolution(self, tmp_path):
        """Test that validator resolves symlinks correctly."""
        from app.services.file_validator import FileValidatorService

        real_file = tmp_path / "real_file.txt"
        real_file.write_text("content")

        symlink = tmp_path / "link_to_file.txt"
        symlink.symlink_to(real_file)

        validator = FileValidatorService()
        assert validator.validate(symlink) is True


class TestMIMETypeValidation:
    """Test file type validation using MIME types."""

    def test_validates_pdf_mime_type_when_specified(self, tmp_path):
        """Test that validator checks MIME type for PDF files."""
        from app.services.file_validator import FileValidatorService, SecurityError

        validator = FileValidatorService()

        fake_pdf = tmp_path / "fake.pdf"
        fake_pdf.write_text("This is not a real PDF file")

        with pytest.raises(SecurityError, match="Invalid file type"):
            validator.validate(fake_pdf, expected_mime_types=["application/pdf"])

    def test_accepts_valid_pdf_mime_type(self, tmp_path):
        """Test that validator accepts files with correct MIME type."""
        from app.services.file_validator import FileValidatorService

        validator = FileValidatorService()

        real_pdf = tmp_path / "real.pdf"
        real_pdf.write_bytes(b'%PDF-1.4\n%\xE2\xE3\xCF\xD3\n')

        assert validator.validate(real_pdf, expected_mime_types=["application/pdf"]) is True

    def test_skips_mime_validation_when_not_specified(self, tmp_path):
        """Test that MIME validation is skipped when expected_mime_types is None."""
        from app.services.file_validator import FileValidatorService

        validator = FileValidatorService()

        any_file = tmp_path / "any.xyz"
        any_file.write_text("content")

        assert validator.validate(any_file, expected_mime_types=None) is True


class TestFileExistence:
    """Test file existence validation."""

    def test_raises_error_for_nonexistent_file(self):
        """Test that validator raises error for files that don't exist."""
        from app.services.file_validator import FileValidatorService, SecurityError

        validator = FileValidatorService()
        nonexistent = Path("/tmp/this_file_definitely_does_not_exist_12345.txt")

        with pytest.raises(SecurityError, match="Failed to access file"):
            validator.validate(nonexistent)


class TestMetadataExtraction:
    """Test metadata extraction functionality."""

    def test_extract_metadata_returns_correct_info(self, tmp_path):
        """Test that extract_metadata returns filename, path, and extension."""
        from app.services.file_validator import FileValidatorService

        validator = FileValidatorService()

        test_file = tmp_path / "document.pdf"
        test_file.write_bytes(b'%PDF-1.4\n')

        metadata = validator.extract_metadata(test_file)

        assert metadata["filename"] == "document.pdf"
        assert metadata["file_path"] == str(test_file)
        assert metadata["file_extension"] == ".pdf"

    def test_extract_metadata_handles_files_without_extension(self, tmp_path):
        """Test metadata extraction for files without extension."""
        from app.services.file_validator import FileValidatorService

        validator = FileValidatorService()

        test_file = tmp_path / "README"
        test_file.write_text("content")

        metadata = validator.extract_metadata(test_file)

        assert metadata["filename"] == "README"
        assert metadata["file_extension"] == ""
