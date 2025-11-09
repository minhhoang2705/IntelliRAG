"""LLM Client Service for vLLM integration.

This module provides the LLMClientService for interfacing with vLLM
via OpenAI-compatible API.
"""

from typing import Optional
from openai import AsyncOpenAI
import logging
from opentelemetry import trace
from app.api.middleware.metrics import llm_token_count

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
        tracer = trace.get_tracer(__name__)

        with tracer.start_as_current_span("llm.generate") as span:
            # Set span attributes
            span.set_attribute("llm.model", self.model)
            span.set_attribute("llm.temperature", temperature)
            span.set_attribute("llm.max_tokens", max_tokens)

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

            # Track input token usage
            if hasattr(response, 'usage') and response.usage:
                llm_token_count.labels(
                    model=self.model,
                    type='input'
                ).inc(response.usage.prompt_tokens)

                # Track output token usage
                llm_token_count.labels(
                    model=self.model,
                    type='output'
                ).inc(response.usage.completion_tokens)

            return response.choices[0].message.content
