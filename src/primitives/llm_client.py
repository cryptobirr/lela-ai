"""
LLMClient Primitive - Generic LLM API client (provider-agnostic)

Issue: #5 - [Sprint 1, Day 2] Primitive: LLMClient
Status: REFACTOR PHASE - Improving code quality while maintaining test coverage
"""

import time
from typing import Any

import httpx


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

    def _parse_error_details(self, response: httpx.Response) -> tuple[str, str]:
        """Extract error type and message from API response

        Args:
            response: HTTP response object

        Returns:
            Tuple of (error_type, error_message)
        """
        error_data = response.json().get("error", {})
        error_type = error_data.get("type", "unknown")
        error_message = error_data.get("message", "Unknown error")
        return error_type, error_message

    def _extract_response_text(self, response: httpx.Response) -> str:
        """Extract text content from successful API response

        Args:
            response: HTTP response object

        Returns:
            Response text from LLM
        """
        response_data = response.json()
        content = response_data.get("content", [])
        if content and isinstance(content, list):
            return content[0].get("text", "")
        return ""

    def _calculate_backoff_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay

        Args:
            attempt: Current attempt number (1-indexed)

        Returns:
            Delay in seconds (2^(attempt-1))
        """
        return 2 ** (attempt - 1)

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
            error_type, error_message = self._parse_error_details(response)
            raise RateLimitError(f"Rate limit exceeded (429): {error_message}")

        if response.status_code >= 400:
            error_type, error_message = self._parse_error_details(response)
            raise LLMAPIError(f"API error ({response.status_code}): {error_type} - {error_message}")

        # Extract and return response text
        return self._extract_response_text(response)

    def call_with_retry(self, prompt: str, config: dict[str, Any], retries: int = 3) -> str:
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

                # Exponential backoff
                backoff_delay = self._calculate_backoff_delay(attempt)
                time.sleep(backoff_delay)

        # Should never reach here
        raise RateLimitError("All retry attempts exhausted")
