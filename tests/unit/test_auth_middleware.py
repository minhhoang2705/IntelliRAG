"""
Unit tests for API authentication middleware.

Following TDD principles:
1. RED: Write ONE failing test first
2. GREEN: Implement minimal code to pass
3. REFACTOR: Improve code while keeping tests green
4. REPEAT: Add next test
"""

import pytest
from fastapi.security import HTTPAuthorizationCredentials
from unittest.mock import patch


class TestVerifyAPIKey:
    """Test suite for verify_api_key dependency."""

    @pytest.mark.asyncio
    async def test_verify_api_key_valid(self):
        """Test that valid API key is accepted."""
        from app.api.middleware.auth import verify_api_key

        # Mock credentials with valid key
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="test-api-key-123"
        )

        # Mock environment variable
        with patch("os.getenv", return_value="test-api-key-123"):
            result = await verify_api_key(credentials)

        assert result == "test-api-key-123"

    @pytest.mark.asyncio
    async def test_verify_api_key_invalid(self):
        """Test that invalid API key returns 401."""
        from fastapi import HTTPException
        from app.api.middleware.auth import verify_api_key

        # Mock credentials with wrong key
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="wrong-key"
        )

        # Mock environment variable with different key
        with patch("os.getenv", return_value="correct-key"):
            with pytest.raises(HTTPException) as exc_info:
                await verify_api_key(credentials)

        assert exc_info.value.status_code == 401
        assert "Invalid API key" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_verify_api_key_missing_header(self):
        """Test that missing Authorization header returns 401."""
        from fastapi import HTTPException
        from app.api.middleware.auth import verify_api_key

        # Mock environment variable (auth is enabled)
        with patch("os.getenv", return_value="test-api-key"):
            with pytest.raises(HTTPException) as exc_info:
                await verify_api_key(credentials=None)

        assert exc_info.value.status_code == 401
        assert "Missing API key" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_verify_api_key_dev_mode(self):
        """Test that no API_KEY env variable allows all requests (dev mode)."""
        from app.api.middleware.auth import verify_api_key

        # Mock no API key configured
        with patch("os.getenv", return_value=None):
            result = await verify_api_key(credentials=None)

        assert result == "dev-mode"
