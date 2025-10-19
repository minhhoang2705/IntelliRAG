"""LLM Client Service for vLLM integration.

This module provides the LLMClientService for interfacing with vLLM
via OpenAI-compatible API.

Author: IntelliRAG Team  
Date: 2025-10-17
"""

from typing import Optional
from openai import AsyncOpenAI
import logging

logger = logging.getLogger(__name__)


class LLMClientService:
    """Service for generating text completions using vLLM."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000/v1",
        api_key: str = "dummy-key",
        model: str = "Qwen/Qwen3-0.6B"
    ):
        """Initialize LLM client.

        Args:
            base_url: vLLM server base URL (default: http://localhost:8000/v1)
            api_key: API key (vLLM doesn't require real key, use dummy)
            model: Model name to use for generation
        """
        self.base_url = base_url
        self.model = model
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        logger.info(f"Initialized LLMClientService with model: {model}")

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 512,
        system_message: Optional[str] = None
    ) -> str:
        """Generate text completion using vLLM.

        Args:
            prompt: User prompt/query
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate
            system_message: Optional system message for instruction

        Returns:
            Generated text response
        """
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        return response.choices[0].message.content
