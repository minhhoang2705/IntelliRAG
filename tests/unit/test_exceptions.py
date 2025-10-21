"""Unit tests for custom exceptions.

Author: IntelliRAG Team
Date: 2025-10-21
"""

import pytest


class TestExceptions:
    """Test suite for custom exception classes."""

    def test_database_service_error_can_be_raised(self):
        """Test that DatabaseServiceError can be raised and caught."""
        from app.exceptions import DatabaseServiceError

        with pytest.raises(DatabaseServiceError) as exc_info:
            raise DatabaseServiceError("Test error message")

        assert str(exc_info.value) == "Test error message"
