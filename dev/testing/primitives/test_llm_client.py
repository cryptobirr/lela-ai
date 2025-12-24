"""
TDD Red-Phase Tests for LLMClient Primitive

Issue: #5 - [Sprint 1, Day 2] Primitive: LLMClient
Status: RED PHASE - All tests should FAIL (no implementation yet)

Test coverage: 6 tests mapping 1:1 to 6 acceptance criteria
"""

import pytest
from unittest.mock import Mock, patch
import time


class TestLLMClient:
    """Test suite for LLMClient primitive - Red Phase"""

    def test_call_invokes_llm_api_and_returns_response_text(self, mocker):
        """
        AC1: call() successfully invokes LLM API and returns response text

        Verifies LLMClient makes successful API call and returns response text
        """
        # Setup: Mock successful Anthropic API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"text": "Hello, world!"}]
        }

        mock_post = mocker.patch("httpx.post", return_value=mock_response)

        # Action: Call LLM API
        from src.primitives.llm_client import LLMClient
        client = LLMClient()
        result = client.call(
            prompt="Say hello",
            config={
                "provider": "anthropic",
                "model": "claude-sonnet-4",
                "api_key": "test-key"
            }
        )

        # Expected: Returns response text
        assert result == "Hello, world!"
        # Verify API was called exactly once
        assert mock_post.call_count == 1

    def test_call_raises_rate_limit_error_on_429_status(self, mocker):
        """
        AC2: call() raises RateLimitError when API returns 429 status

        Verifies LLMClient detects rate limit errors and raises appropriate exception
        """
        # Setup: Mock 429 rate limit response
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {
            "error": {"type": "rate_limit_error", "message": "Too many requests"}
        }

        mocker.patch("httpx.post", return_value=mock_response)

        # Action & Expected: Should raise RateLimitError
        from src.primitives.llm_client import LLMClient, RateLimitError
        client = LLMClient()

        with pytest.raises(RateLimitError) as exc_info:
            client.call(
                prompt="Test",
                config={"provider": "anthropic", "api_key": "test-key"}
            )

        # Error message should mention rate limit or 429
        error_message = str(exc_info.value).lower()
        assert "rate limit" in error_message or "429" in error_message

    def test_call_with_retry_uses_exponential_backoff_on_rate_limits(self, mocker):
        """
        AC3: call_with_retry() retries with exponential backoff on rate limits (3 attempts)

        Verifies retry logic: 2 failures (429) + 1 success with exponential backoff delays
        """
        # Setup: Mock responses - 429, 429, 200 (success on 3rd attempt)
        mock_responses = [
            Mock(status_code=429, json=lambda: {"error": {"type": "rate_limit_error"}}),
            Mock(status_code=429, json=lambda: {"error": {"type": "rate_limit_error"}}),
            Mock(status_code=200, json=lambda: {"content": [{"text": "Success!"}]})
        ]

        mock_post = mocker.patch("httpx.post", side_effect=mock_responses)
        mock_sleep = mocker.patch("time.sleep")  # Mock sleep to speed up test

        # Action: Call with retry
        from src.primitives.llm_client import LLMClient
        client = LLMClient()
        result = client.call_with_retry(
            prompt="Test",
            config={"provider": "anthropic", "api_key": "test-key"},
            retries=3
        )

        # Expected: Makes 3 API calls (2 failures + 1 success)
        assert mock_post.call_count == 3

        # Expected: Returns successful response from 3rd attempt
        assert result == "Success!"

        # Expected: Sleep called twice (after 1st and 2nd failures) with exponential backoff
        assert mock_sleep.call_count == 2
        # First sleep: ~1 second (2^0 = 1)
        first_sleep = mock_sleep.call_args_list[0][0][0]
        assert 0.8 <= first_sleep <= 1.2  # Allow some jitter

        # Second sleep: ~2 seconds (2^1 = 2)
        second_sleep = mock_sleep.call_args_list[1][0][0]
        assert 1.8 <= second_sleep <= 2.4  # Allow some jitter

    def test_call_raises_timeout_error_when_request_exceeds_threshold(self, mocker):
        """
        AC4: call() raises TimeoutError when API request exceeds timeout threshold

        Verifies LLMClient handles slow API responses with timeout
        """
        # Setup: Mock slow API response (raises timeout exception)
        import httpx

        def slow_response(*args, **kwargs):
            raise httpx.TimeoutException("Request timed out")

        mocker.patch("httpx.post", side_effect=slow_response)

        # Action & Expected: Should raise TimeoutError
        from src.primitives.llm_client import LLMClient, TimeoutError
        client = LLMClient()

        with pytest.raises(TimeoutError) as exc_info:
            client.call(
                prompt="Test",
                config={
                    "provider": "anthropic",
                    "api_key": "test-key",
                    "timeout": 2  # 2 second timeout
                }
            )

        # Error message should mention timeout
        error_message = str(exc_info.value).lower()
        assert "timeout" in error_message

    def test_supports_provider_identifies_valid_providers(self):
        """
        AC5: supports_provider() correctly identifies supported providers

        Verifies supports_provider() returns True for valid providers, False otherwise
        """
        # Setup: Create LLMClient instance
        from src.primitives.llm_client import LLMClient
        client = LLMClient()

        # Action & Expected: Check each supported provider
        assert client.supports_provider("anthropic") is True
        assert client.supports_provider("google") is True
        assert client.supports_provider("openai") is True
        assert client.supports_provider("ollama") is True

        # Action & Expected: Invalid provider returns False
        assert client.supports_provider("invalid-provider") is False
        assert client.supports_provider("") is False
        assert client.supports_provider("ANTHROPIC") is False  # Case-sensitive

    def test_call_raises_descriptive_exceptions_on_api_failures(self, mocker):
        """
        AC6: call() raises descriptive exceptions with error details on API failures

        Verifies LLMClient raises specific, descriptive exceptions (not generic errors)
        """
        # Setup: Mock 500 server error with detailed error message
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {
            "error": {
                "type": "internal_error",
                "message": "Model overloaded"
            }
        }

        mocker.patch("httpx.post", return_value=mock_response)

        # Action & Expected: Should raise LLMAPIError with specific details
        from src.primitives.llm_client import LLMClient, LLMAPIError
        client = LLMClient()

        with pytest.raises(LLMAPIError) as exc_info:
            client.call(
                prompt="Test",
                config={"provider": "anthropic", "api_key": "test-key"}
            )

        # Error message should contain specific details (not generic)
        error_message = str(exc_info.value).lower()

        # Should include error type
        assert "internal_error" in error_message or "internal" in error_message

        # Should include error message
        assert "overloaded" in error_message or "model overloaded" in error_message

        # Should include status code
        assert "500" in error_message

        # Should NOT be generic message
        assert error_message != "api failed"
        assert error_message != "error occurred"
