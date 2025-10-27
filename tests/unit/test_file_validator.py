"""Unit tests for FileValidator service.


Date: 2025-10-21
"""

import pytest


class TestFileValidator:
    """Test suite for FileValidator service."""

    def test_validate_file_size_within_limit(self):
        """Test that file size within limit is valid."""
        from app.services.file_validator import FileValidator

        validator = FileValidator()

        # 10 MB file (well within typical 50 MB limit)
        file_size = 10 * 1024 * 1024

        # Should not raise an exception
        validator.validate_file_size(file_size)

    def test_validate_file_size_exceeds_limit(self):
        """Test that file size exceeding limit raises InvalidFileError."""
        from app.services.file_validator import FileValidator
        from app.exceptions import InvalidFileError

        validator = FileValidator(max_file_size_mb=50)

        # 100 MB file (exceeds 50 MB limit)
        file_size = 100 * 1024 * 1024

        with pytest.raises(InvalidFileError) as exc_info:
            validator.validate_file_size(file_size)

        assert "too large" in str(exc_info.value).lower()
        assert "100" in str(exc_info.value)  # Should show actual size
        assert "50" in str(exc_info.value)   # Should show max size

    def test_validate_file_size_negative(self):
        """Test that negative file size raises InvalidFileError."""
        from app.services.file_validator import FileValidator
        from app.exceptions import InvalidFileError

        validator = FileValidator()

        with pytest.raises(InvalidFileError) as exc_info:
            validator.validate_file_size(-100)

        assert "must be positive" in str(exc_info.value).lower()

    def test_sanitize_filename_removes_path_traversal(self):
        """Test that path traversal attempts are sanitized."""
        from app.services.file_validator import FileValidator

        validator = FileValidator()

        # Path traversal attack attempts
        dangerous_filenames = [
            "../../etc/passwd",
            "../../../root/.ssh/id_rsa",
            "..\\..\\windows\\system32\\config\\sam",
            "/etc/passwd",
            "C:\\Windows\\System32\\config\\sam"
        ]

        for dangerous in dangerous_filenames:
            sanitized = validator.sanitize_filename(dangerous)

            # Should remove all path components
            assert "/" not in sanitized
            assert "\\" not in sanitized
            assert ".." not in sanitized

            # Should only contain the basename
            assert sanitized in ["passwd", "id_rsa", "sam"]

    def test_validate_mime_type_allowed(self):
        """Test that allowed MIME types pass validation."""
        from app.services.file_validator import FileValidator

        validator = FileValidator()

        allowed_types = [
            'application/pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain',
            'text/csv',
            'image/jpeg',
            'image/png'
        ]

        for mime_type in allowed_types:
            # Should not raise an exception
            result = validator.validate_mime_type(mime_type)
            assert result == mime_type

    def test_validate_sha256_hash_valid(self):
        """Test that valid SHA-256 hashes pass validation."""
        from app.services.file_validator import FileValidator

        validator = FileValidator()

        valid_hashes = [
            'a' * 64,  # All lowercase
            'A' * 64,  # All uppercase (should be normalized to lowercase)
            '0123456789abcdef' * 4,  # Mix of numbers and letters
        ]

        for hash_value in valid_hashes:
            result = validator.validate_sha256_hash(hash_value)
            # Should return lowercase version
            assert result == hash_value.lower()
            assert len(result) == 64
