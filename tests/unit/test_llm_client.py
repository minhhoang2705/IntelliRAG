"""Unit tests for LLM Client Service.

This module tests the LLMClientService which interfaces with vLLM
via OpenAI-compatible API.


Date: 2025-10-17
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_llm_client_initialization():
    """Test LLM client initializes with correct configuration."""
    from app.services.llm_client import LLMClientService

    client = LLMClientService(
        base_url="http://localhost:8000/v1",
        api_key="dummy-key",
        model="Qwen/Qwen3-0.6B-Instruct"
    )

    assert client.base_url == "http://localhost:8000/v1"
    assert client.model == "Qwen/Qwen3-0.6B-Instruct"
    assert client.client is not None


@pytest.mark.asyncio
async def test_llm_client_generate(mocker):
    """Test LLM client generates text completions."""
    from app.services.llm_client import LLMClientService

    client = LLMClientService()

    # Mock the OpenAI client response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Python is a programming language"

    # Use AsyncMock for async method
    mock_create = AsyncMock(return_value=mock_response)
    mocker.patch.object(
        client.client.chat.completions,
        'create',
        mock_create
    )

    response = await client.generate(
        prompt="What is Python?",
        temperature=0.7,
        max_tokens=100
    )

    assert response == "Python is a programming language"
    mock_create.assert_called_once()
