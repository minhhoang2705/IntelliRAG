"""Unit tests for LLM token metrics instrumentation.

This module tests that LLMClientService tracks token usage via Prometheus metrics.
Following TDD: Write ONE test, see it FAIL, implement, then proceed.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from prometheus_client import REGISTRY


def get_metric_value(metric_name: str, labels: dict = None) -> float:
    """Helper to extract metric value from Prometheus registry.

    Args:
        metric_name: Name of the Prometheus metric
        labels: Dictionary of label key-value pairs to match

    Returns:
        Metric value or 0 if not found
    """
    for collector in REGISTRY.collect():
        for sample in collector.samples:
            if sample.name == metric_name:
                if labels is None:
                    return sample.value
                # Check if all labels match
                if all(sample.labels.get(k) == v for k, v in labels.items()):
                    return sample.value
    return 0


@pytest.mark.asyncio
async def test_llm_client_tracks_input_tokens(mocker):
    """Test that LLM client tracks input token count.

    This test will FAIL until we add token tracking to LLMClientService.
    Expected failure: llm_token_count metric not incremented.
    """
    from app.services.llm_client import LLMClientService

    client = LLMClientService(model="Qwen/Qwen3-0.6B")

    # Mock OpenAI response with usage data
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Test response"
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 50  # Input tokens
    mock_response.usage.completion_tokens = 30  # Output tokens
    mock_response.usage.total_tokens = 80

    mock_create = AsyncMock(return_value=mock_response)
    mocker.patch.object(
        client.client.chat.completions,
        'create',
        mock_create
    )

    # Get initial token count
    initial_input_tokens = get_metric_value(
        'llm_token_count_total',
        labels={'model': 'Qwen/Qwen3-0.6B', 'type': 'input'}
    )

    # Generate response
    response = await client.generate(
        prompt="What is Python?",
        temperature=0.7,
        max_tokens=100
    )

    assert response == "Test response"

    # Verify input token metric incremented by 50
    final_input_tokens = get_metric_value(
        'llm_token_count_total',
        labels={'model': 'Qwen/Qwen3-0.6B', 'type': 'input'}
    )

    assert final_input_tokens == initial_input_tokens + 50, \
        f"Expected llm_token_count (input) to increment by 50, got {final_input_tokens - initial_input_tokens}"


@pytest.mark.asyncio
async def test_llm_client_tracks_output_tokens(mocker):
    """Test that LLM client tracks output token count.

    This test will FAIL until we add output token tracking to LLMClientService.
    """
    from app.services.llm_client import LLMClientService

    client = LLMClientService(model="Qwen/Qwen3-0.6B")

    # Mock OpenAI response with usage data
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Test response"
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 50  # Input tokens
    mock_response.usage.completion_tokens = 30  # Output tokens
    mock_response.usage.total_tokens = 80

    mock_create = AsyncMock(return_value=mock_response)
    mocker.patch.object(
        client.client.chat.completions,
        'create',
        mock_create
    )

    # Get initial output token count
    initial_output_tokens = get_metric_value(
        'llm_token_count_total',
        labels={'model': 'Qwen/Qwen3-0.6B', 'type': 'output'}
    )

    # Generate response
    response = await client.generate(
        prompt="What is Python?",
        temperature=0.7,
        max_tokens=100
    )

    assert response == "Test response"

    # Verify output token metric incremented by 30
    final_output_tokens = get_metric_value(
        'llm_token_count_total',
        labels={'model': 'Qwen/Qwen3-0.6B', 'type': 'output'}
    )

    assert final_output_tokens == initial_output_tokens + 30, \
        f"Expected llm_token_count (output) to increment by 30, got {final_output_tokens - initial_output_tokens}"
