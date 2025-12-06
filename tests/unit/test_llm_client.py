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
    from unittest.mock import Mock
    import time

    client = LLMClientService()

    # Create properly structured mock response with actual int tokens
    mock_response = Mock()
    mock_message = Mock()
    mock_message.content = "Python is a programming language"
    mock_choice = Mock()
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]

    # CRITICAL: Actual integers, not Mocks
    mock_usage = Mock()
    mock_usage.total_tokens = 100
    mock_usage.prompt_tokens = 20
    mock_usage.completion_tokens = 80
    mock_response.usage = mock_usage

    mock_response.model = "Qwen/Qwen3-0.6B"
    mock_response.created = int(time.time())
    mock_response.id = f"chatcmpl-{int(time.time())}"

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
