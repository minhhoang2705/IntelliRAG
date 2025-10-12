"""
Unit tests for security validations in document handlers.

This module tests security features including:
- File size validation
- Path traversal protection
- Magic bytes validation
- Filename sanitization

Following TDD methodology - adding one test at a time.
"""

import pytest
from pathlib import Path

from app.services.preprocessing.base import BaseHandler, SecurityError
from app.services.preprocessing.text import TextHandler


class TestFileSizeValidation:
    """Test file size limit enforcement."""

    def test_base_handler_rejects_oversized_files(self, tmp_path):
        """Test that handlers reject files exceeding size limit."""
        # Create a file larger than 50MB
        oversized_file = tmp_path / "large_file.txt"

        # Write 51MB of data (50MB limit + 1MB)
        size_mb = 51
        with open(oversized_file, 'wb') as f:
            f.write(b'x' * (size_mb * 1024 * 1024))

        handler = TextHandler()

        # Should raise SecurityError for oversized file
        with pytest.raises(SecurityError, match="File size exceeds"):
            handler.secure_validate(oversized_file)

    def test_base_handler_accepts_files_within_limit(self, tmp_path):
        """Test that handlers accept files within size limit."""
        # Create a file smaller than 50MB
        valid_file = tmp_path / "valid_file.txt"

        # Write 1MB of data
        with open(valid_file, 'wb') as f:
            f.write(b'x' * (1 * 1024 * 1024))

        handler = TextHandler()

        # Should not raise any exception
        assert handler.secure_validate(valid_file) is True


class TestPathTraversalProtection:
    """Test protection against path traversal attacks."""

    def test_base_handler_prevents_absolute_paths_outside_project(self, tmp_path):
        """Test rejection of absolute paths outside the project directory."""
        handler = TextHandler()

        # Try to access a system file
        system_file = Path("/etc/passwd")

        # Skip if file doesn't exist (Windows or restricted system)
        if not system_file.exists():
            pytest.skip("System file /etc/passwd not available")

        # Should raise SecurityError for path outside project
        with pytest.raises(SecurityError, match="Path traversal detected"):
            handler.secure_validate(system_file)


class TestMagicBytesValidation:
    """Test file type validation using magic bytes."""

    def test_pdf_handler_validates_pdf_magic_bytes(self, tmp_path):
        """Test that PDF handler rejects files without PDF magic bytes."""
        from app.services.preprocessing.pdf import PDFHandler

        handler = PDFHandler()

        # Create a fake PDF file without proper magic bytes
        fake_pdf = tmp_path / "fake.pdf"
        fake_pdf.write_text("This is not a real PDF file")

        # Should raise SecurityError if magic byte validation is enabled
        with pytest.raises(SecurityError, match="Invalid file type"):
            handler.secure_validate(fake_pdf)



class TestSecurityIntegration:
    """Integration tests - verify security is enforced in process() methods."""

    def test_handler_process_rejects_oversized_files(self, tmp_path):
        """Test that handler.process() automatically enforces file size limits."""
        oversized_file = tmp_path / "oversized.txt"
        with open(oversized_file, 'wb') as f:
            f.write(b'x' * (51 * 1024 * 1024))  # 51MB

        handler = TextHandler()

        with pytest.raises(SecurityError, match="File size exceeds"):
            handler.process(oversized_file)
