"""Integration tests for LLM Client Service with real vLLM.

This module tests the LLMClientService with a real vLLM server
without mocking.


Date: 2025-10-18
"""

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_vllm_service_availability(check_vllm):
    """Test vLLM service is accessible.

    Integration Test: Verifies vLLM server is running and responding
    Prerequisites: vLLM running on localhost:8000
    Expected: Service returns 200 OK
    """
    import requests

    response = requests.get("http://localhost:8000/v1/models", timeout=5)
    assert response.status_code == 200

    models_data = response.json()
    assert "data" in models_data
    assert len(models_data["data"]) > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_llm_client_real_generation(check_vllm):
    """Test LLM client generates text with real vLLM server.

    Integration Test: Verifies text generation works with real model
    Prerequisites: vLLM running with Qwen3-0.6B
    Expected: Returns non-empty generated text
    """
    from app.services.llm_client import LLMClientService

    client = LLMClientService(
        base_url="http://localhost:8000/v1",
        model="Qwen/Qwen3-0.6B"
    )

    response = await client.generate(
        prompt="What is 2+2? Answer in one word.",
        temperature=0.0,
        max_tokens=10
    )

    assert response is not None
    assert len(response) > 0
    assert isinstance(response, str)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_llm_client_with_system_message(check_vllm):
    """Test LLM client with system message.

    Integration Test: Verifies system prompts influence generation
    Prerequisites: vLLM running
    Expected: Response follows system instructions
    """
    from app.services.llm_client import LLMClientService

    client = LLMClientService(
        base_url="http://localhost:8000/v1",
        model="Qwen/Qwen3-0.6B"
    )

    response = await client.generate(
        prompt="What is Python?",
        system_message="You are a helpful programming teacher. Answer concisely.",
        temperature=0.7,
        max_tokens=100
    )

    assert response is not None
    assert len(response) > 10
    assert "python" in response.lower() or "programming" in response.lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_llm_client_temperature_variations(check_vllm):
    """Test LLM client with different temperature settings.

    Integration Test: Verifies temperature parameter affects generation
    Prerequisites: vLLM running
    Expected: Different temperatures produce valid responses
    """
    from app.services.llm_client import LLMClientService

    client = LLMClientService(
        base_url="http://localhost:8000/v1",
        model="Qwen/Qwen3-0.6B"
    )

    prompt = "Describe the color blue in 5 words."

    # Test low temperature (deterministic)
    response_low = await client.generate(prompt=prompt, temperature=0.0, max_tokens=20)
    assert response_low is not None

    # Test medium temperature (balanced)
    response_med = await client.generate(prompt=prompt, temperature=0.7, max_tokens=20)
    assert response_med is not None

    # Test high temperature (creative)
    response_high = await client.generate(prompt=prompt, temperature=1.5, max_tokens=20)
    assert response_high is not None

    # All should be strings
    assert all(isinstance(r, str)
               for r in [response_low, response_med, response_high])


@pytest.mark.integration
@pytest.mark.asyncio
async def test_llm_client_max_tokens_limit(check_vllm):
    """Test LLM client respects max_tokens parameter.

    Integration Test: Verifies max_tokens limits response length
    Prerequisites: vLLM running
    Expected: Response respects token limit
    """
    from app.services.llm_client import LLMClientService

    client = LLMClientService(
        base_url="http://localhost:8000/v1",
        model="Qwen/Qwen3-0.6B"
    )

    # Request very short response
    short_response = await client.generate(
        prompt="Write a story about a dog.",
        temperature=0.7,
        max_tokens=10
    )

    # Request longer response
    long_response = await client.generate(
        prompt="Write a story about a dog.",
        temperature=0.7,
        max_tokens=100
    )

    assert len(short_response) < len(long_response)
    assert len(short_response) > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_llm_client_concurrent_requests(check_vllm):
    """Test LLM client handles concurrent requests.

    Integration Test: Verifies concurrent generation requests work
    Prerequisites: vLLM running with concurrent batching
    Expected: All requests complete successfully
    """
    from app.services.llm_client import LLMClientService
    import asyncio

    client = LLMClientService(
        base_url="http://localhost:8000/v1",
        model="Qwen/Qwen3-0.6B"
    )

    prompts = [
        "What is 1+1?",
        "What is 2+2?",
        "What is 3+3?",
        "What is 4+4?",
        "What is 5+5?"
    ]

    # Execute concurrently
    tasks = [
        client.generate(prompt=p, temperature=0.0, max_tokens=10)
        for p in prompts
    ]

    responses = await asyncio.gather(*tasks)

    assert len(responses) == len(prompts)
    assert all(isinstance(r, str) and len(r) > 0 for r in responses)
