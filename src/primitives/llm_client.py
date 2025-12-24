"""
LLMClient Primitive - Generic LLM API client (provider-agnostic)

Issue: #5 - [Sprint 1, Day 2] Primitive: LLMClient
Status: GREEN PHASE - Minimum implementation to pass tests
"""

import time
from typing import Any


# Exception hierarchy
class LLMError(Exception):
    """Base exception for LLM client errors"""

    pass


class RateLimitError(LLMError):
    """Raised when API returns 429 rate limit"""

    pass


class TimeoutError(LLMError):
    """Raised when request exceeds timeout threshold"""

    pass


class LLMAPIError(LLMError):
    """Raised for general API failures (5xx, 4xx except 429)"""

    pass


class LLMClient:
    """Generic LLM API client with multi-provider support"""

    SUPPORTED_PROVIDERS = {"anthropic", "google", "openai", "ollama"}

    def supports_provider(self, provider: str) -> bool:
        """Check if provider is supported

        Args:
            provider: Provider name (case-sensitive)

        Returns:
            True if provider supported, False otherwise
        """
        return provider in self.SUPPORTED_PROVIDERS

    def call(self, prompt: str, config: dict[str, Any]) -> str:
        """Make LLM API call and return response text

        Args:
            prompt: Input prompt text
            config: Configuration dict with keys:
                - provider: Provider name (anthropic|google|openai|ollama)
                - model: Model name
                - api_key: API key (optional)
                - timeout: Timeout in seconds (optional, default 30)

        Returns:
            Response text from LLM

        Raises:
            RateLimitError: When API returns 429 status
            TimeoutError: When request exceeds timeout threshold
            LLMAPIError: For other API failures
        """
        import httpx

        provider = config.get("provider")
        timeout = config.get("timeout", 30)

        try:
            # Make API call (simplified - only handles Anthropic for now)
            response = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": config.get("api_key", ""),
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": config.get("model", "claude-sonnet-4"),
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1024,
                },
                timeout=timeout,
            )
        except httpx.TimeoutException as e:
            raise TimeoutError(f"Request timeout after {timeout}s: {str(e)}") from e

        # Handle error status codes
        if response.status_code == 429:
            error_data = response.json().get("error", {})
            raise RateLimitError(
                f"Rate limit exceeded (429): {error_data.get('message', 'Too many requests')}"
            )

        if response.status_code >= 400:
            error_data = response.json().get("error", {})
            error_type = error_data.get("type", "unknown")
            error_message = error_data.get("message", "Unknown error")
            raise LLMAPIError(
                f"API error ({response.status_code}): {error_type} - {error_message}"
            )

        # Extract response text
        response_data = response.json()
        content = response_data.get("content", [])
        if content and isinstance(content, list):
            return content[0].get("text", "")

        return ""

    def call_with_retry(
        self, prompt: str, config: dict[str, Any], retries: int = 3
    ) -> str:
        """Make LLM API call with retry logic (exponential backoff)

        Args:
            prompt: Input prompt text
            config: Configuration dict (same as call())
            retries: Maximum number of attempts (default 3)

        Returns:
            Response text from LLM

        Raises:
            RateLimitError: When all retries exhausted
            TimeoutError: When request exceeds timeout threshold
            LLMAPIError: For other API failures
        """
        attempt = 0
        while attempt < retries:
            try:
                return self.call(prompt, config)
            except RateLimitError:
                attempt += 1
                if attempt >= retries:
                    raise  # Re-raise on last attempt

                # Exponential backoff: 2^(attempt-1) seconds
                backoff_delay = 2 ** (attempt - 1)
                time.sleep(backoff_delay)

        # Should never reach here
        raise RateLimitError("All retry attempts exhausted")
