"""
Test suite for LLMProvider Component

Purpose: Verify unified LLM provider interface with config loading, logging, and error handling

Test Coverage:
- Happy path: Successful LLM calls with all providers (5 tests)
- Edge cases: Empty responses, missing config keys, invalid providers (3 tests)
- Error handling: API failures, invalid configs, timeout scenarios (3 tests)

Requirements tested: Issue #15 - [Sprint 2, Day 2] Component: LLMProvider

Component: LLMProvider composes 3 primitives:
- LLMClient (#5)
- ConfigLoader (#6)
- Logger (#4)
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


class TestLLMProvider:
    """Test suite for LLMProvider component - Red Phase"""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary directory for test configs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            yield config_dir

    @pytest.fixture
    def valid_llm_config(self, temp_config_dir):
        """Create valid LLM configuration file."""
        config = {
            "provider": "anthropic",
            "model": "claude-sonnet-4",
            "api_key_env": "TEST_API_KEY",
            "timeout": 30,
        }
        config_path = temp_config_dir / "llm_config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        return config_path

    def test_generate_calls_llm_successfully_with_anthropic(self, valid_llm_config, mocker):
        """
        AC1: generate() calls LLM successfully with Anthropic provider

        Verifies LLMProvider loads config, calls Anthropic API via LLMClient,
        logs the interaction, and returns response text.
        """
        # Arrange
        from src.components.llm_provider import LLMProvider

        # Mock environment variable for API key
        mocker.patch.dict("os.environ", {"TEST_API_KEY": "test-anthropic-key"})

        # Mock LLMClient.call to return test response
        mock_llm_response = "This is a test response from Anthropic"
        mocker.patch(
            "src.primitives.llm_client.LLMClient.call", return_value=mock_llm_response
        )

        # Mock Logger to verify logging
        mock_logger = Mock()
        mocker.patch("src.primitives.logger.Logger", return_value=mock_logger)

        provider = LLMProvider()
        prompt = "What is the meaning of life?"

        # Act
        response = provider.generate(
            prompt=prompt, provider_config={"config_path": str(valid_llm_config)}
        )

        # Assert: Response matches LLM output
        assert response == mock_llm_response

        # Assert: Logger was called to log the interaction
        assert mock_logger.info.called, "LLMProvider should log LLM calls"

        # Verify log contains prompt, response, provider, and model
        log_calls = [call.kwargs for call in mock_logger.info.call_args_list]
        logged_context = {}
        for call in log_calls:
            if "context" in call:
                logged_context.update(call["context"])

        assert "prompt" in logged_context or any(
            "prompt" in str(call) for call in log_calls
        ), "Log should include prompt"
        assert "response" in logged_context or any(
            "response" in str(call) for call in log_calls
        ), "Log should include response"

    def test_generate_calls_llm_successfully_with_google(self, temp_config_dir, mocker):
        """
        AC1: generate() calls LLM successfully with Google provider

        Verifies LLMProvider supports Google/Gemini provider configuration.
        """
        # Arrange
        from src.components.llm_provider import LLMProvider

        # Create Google config
        google_config = {
            "provider": "google",
            "model": "gemini-pro",
            "api_key_env": "GOOGLE_API_KEY",
            "timeout": 30,
        }
        config_path = temp_config_dir / "google_config.json"
        config_path.write_text(json.dumps(google_config), encoding="utf-8")

        # Mock environment
        mocker.patch.dict("os.environ", {"GOOGLE_API_KEY": "test-google-key"})

        # Mock LLMClient
        mock_response = "Response from Google Gemini"
        mocker.patch("src.primitives.llm_client.LLMClient.call", return_value=mock_response)

        # Mock Logger
        mock_logger = Mock()
        mocker.patch("src.primitives.logger.Logger", return_value=mock_logger)

        provider = LLMProvider()

        # Act
        response = provider.generate(
            prompt="Test prompt", provider_config={"config_path": str(config_path)}
        )

        # Assert
        assert response == mock_response

    def test_generate_calls_llm_successfully_with_openai(self, temp_config_dir, mocker):
        """
        AC1: generate() calls LLM successfully with OpenAI provider

        Verifies LLMProvider supports OpenAI/GPT provider configuration.
        """
        # Arrange
        from src.components.llm_provider import LLMProvider

        # Create OpenAI config
        openai_config = {
            "provider": "openai",
            "model": "gpt-4",
            "api_key_env": "OPENAI_API_KEY",
            "timeout": 30,
        }
        config_path = temp_config_dir / "openai_config.json"
        config_path.write_text(json.dumps(openai_config), encoding="utf-8")

        # Mock environment
        mocker.patch.dict("os.environ", {"OPENAI_API_KEY": "test-openai-key"})

        # Mock LLMClient
        mock_response = "Response from OpenAI GPT-4"
        mocker.patch("src.primitives.llm_client.LLMClient.call", return_value=mock_response)

        # Mock Logger
        mock_logger = Mock()
        mocker.patch("src.primitives.logger.Logger", return_value=mock_logger)

        provider = LLMProvider()

        # Act
        response = provider.generate(
            prompt="Test prompt", provider_config={"config_path": str(config_path)}
        )

        # Assert
        assert response == mock_response

    def test_generate_calls_llm_successfully_with_ollama(self, temp_config_dir, mocker):
        """
        AC1: generate() calls LLM successfully with Ollama provider

        Verifies LLMProvider supports Ollama local model provider configuration.
        """
        # Arrange
        from src.components.llm_provider import LLMProvider

        # Create Ollama config (no API key needed for local)
        ollama_config = {
            "provider": "ollama",
            "model": "llama2",
            "timeout": 30,
        }
        config_path = temp_config_dir / "ollama_config.json"
        config_path.write_text(json.dumps(ollama_config), encoding="utf-8")

        # Mock LLMClient
        mock_response = "Response from Ollama local model"
        mocker.patch("src.primitives.llm_client.LLMClient.call", return_value=mock_response)

        # Mock Logger
        mock_logger = Mock()
        mocker.patch("src.primitives.logger.Logger", return_value=mock_logger)

        provider = LLMProvider()

        # Act
        response = provider.generate(
            prompt="Test prompt", provider_config={"config_path": str(config_path)}
        )

        # Assert
        assert response == mock_response

    def test_validate_config_returns_true_for_valid_configs(self, valid_llm_config):
        """
        AC5: validate_config() validates config before calling LLM

        Verifies validate_config() correctly identifies valid LLM configurations
        with all required fields present.
        """
        # Arrange
        from src.components.llm_provider import LLMProvider

        provider = LLMProvider()

        # Valid config with all required fields
        valid_config = {
            "provider": "anthropic",
            "model": "claude-sonnet-4",
            "api_key_env": "TEST_API_KEY",
            "timeout": 30,
        }

        # Act
        is_valid, errors = provider.validate_config(valid_config)

        # Assert
        assert is_valid is True, "Valid config should pass validation"
        assert len(errors) == 0, f"Valid config should have no errors, got: {errors}"

    def test_validate_config_returns_false_for_missing_provider(self):
        """
        AC5: validate_config() rejects config missing 'provider' field

        Verifies validate_config() detects missing required 'provider' field.
        """
        # Arrange
        from src.components.llm_provider import LLMProvider

        provider = LLMProvider()

        # Invalid config: missing 'provider'
        invalid_config = {
            "model": "claude-sonnet-4",
            "api_key_env": "TEST_API_KEY",
        }

        # Act
        is_valid, errors = provider.validate_config(invalid_config)

        # Assert
        assert is_valid is False, "Config missing 'provider' should fail validation"
        assert len(errors) > 0, "Should return error messages"
        assert any("provider" in error.lower() for error in errors), "Error should mention 'provider'"

    def test_validate_config_returns_false_for_missing_model(self):
        """
        AC5: validate_config() rejects config missing 'model' field

        Verifies validate_config() detects missing required 'model' field.
        """
        # Arrange
        from src.components.llm_provider import LLMProvider

        provider = LLMProvider()

        # Invalid config: missing 'model'
        invalid_config = {
            "provider": "anthropic",
            "api_key_env": "TEST_API_KEY",
        }

        # Act
        is_valid, errors = provider.validate_config(invalid_config)

        # Assert
        assert is_valid is False, "Config missing 'model' should fail validation"
        assert len(errors) > 0, "Should return error messages"
        assert any("model" in error.lower() for error in errors), "Error should mention 'model'"

    def test_validate_config_returns_false_for_unsupported_provider(self):
        """
        AC5: validate_config() rejects unsupported provider names

        Verifies validate_config() uses LLMClient.supports_provider() to validate provider.
        """
        # Arrange
        from src.components.llm_provider import LLMProvider

        provider = LLMProvider()

        # Invalid config: unsupported provider
        invalid_config = {
            "provider": "unsupported-provider",
            "model": "some-model",
            "api_key_env": "SOME_KEY",
        }

        # Act
        is_valid, errors = provider.validate_config(invalid_config)

        # Assert
        assert is_valid is False, "Unsupported provider should fail validation"
        assert len(errors) > 0, "Should return error messages"
        assert any(
            "unsupported" in error.lower() or "provider" in error.lower() for error in errors
        ), "Error should mention unsupported provider"

    def test_generate_loads_config_correctly(self, valid_llm_config, mocker):
        """
        AC2: generate() loads LLM config correctly via ConfigLoader

        Verifies LLMProvider uses ConfigLoader to load and parse config files,
        including environment variable substitution.
        """
        # Arrange
        from src.components.llm_provider import LLMProvider

        # Mock environment for API key substitution
        mocker.patch.dict("os.environ", {"TEST_API_KEY": "substituted-key-value"})

        # Mock LLMClient
        mock_response = "Test response"
        mock_llm_call = mocker.patch(
            "src.primitives.llm_client.LLMClient.call", return_value=mock_response
        )

        # Mock Logger
        mock_logger = Mock()
        mocker.patch("src.primitives.logger.Logger", return_value=mock_logger)

        provider = LLMProvider()

        # Act
        response = provider.generate(
            prompt="Test", provider_config={"config_path": str(valid_llm_config)}
        )

        # Assert: LLMClient.call was invoked with correct config
        assert mock_llm_call.called, "LLMClient.call should be invoked"
        call_config = mock_llm_call.call_args[1]["config"]

        # Verify config fields loaded from file
        assert call_config["provider"] == "anthropic"
        assert call_config["model"] == "claude-sonnet-4"
        assert call_config["timeout"] == 30

        # Verify environment variable was substituted
        assert "api_key" in call_config, "API key should be resolved from environment"

    def test_generate_logs_all_llm_calls(self, valid_llm_config, mocker):
        """
        AC3: generate() logs all LLM calls (prompt, response, provider, model)

        Verifies LLMProvider logs comprehensive details for every LLM interaction.
        """
        # Arrange
        from src.components.llm_provider import LLMProvider

        mocker.patch.dict("os.environ", {"TEST_API_KEY": "test-key"})

        # Mock LLMClient
        mock_response = "This is the LLM response"
        mocker.patch("src.primitives.llm_client.LLMClient.call", return_value=mock_response)

        # Mock Logger and capture calls
        mock_logger = Mock()
        mocker.patch("src.primitives.logger.Logger", return_value=mock_logger)

        provider = LLMProvider()
        prompt = "What is quantum computing?"

        # Act
        response = provider.generate(
            prompt=prompt, provider_config={"config_path": str(valid_llm_config)}
        )

        # Assert: Logger.info was called
        assert mock_logger.info.called, "Should log LLM call"

        # Collect all log calls
        log_calls = mock_logger.info.call_args_list

        # Assert: Log includes prompt
        logged_data = str(log_calls)
        assert "quantum computing" in logged_data or any(
            "prompt" in str(call) for call in log_calls
        ), "Log should include prompt text"

        # Assert: Log includes response
        assert "LLM response" in logged_data or any(
            "response" in str(call) for call in log_calls
        ), "Log should include response text"

        # Assert: Log includes provider
        assert "anthropic" in logged_data or any(
            "provider" in str(call) for call in log_calls
        ), "Log should include provider name"

        # Assert: Log includes model
        assert "claude-sonnet-4" in logged_data or any(
            "model" in str(call) for call in log_calls
        ), "Log should include model name"

    def test_generate_handles_api_errors_gracefully(self, valid_llm_config, mocker):
        """
        AC4: generate() handles API errors gracefully

        Verifies LLMProvider catches LLM API errors, logs them, and raises
        descriptive exceptions (not silent failures).
        """
        # Arrange
        from src.components.llm_provider import LLMProvider
        from src.primitives.llm_client import LLMAPIError

        mocker.patch.dict("os.environ", {"TEST_API_KEY": "test-key"})

        # Mock LLMClient to raise API error
        error_message = "API error (500): internal_error - Model overloaded"
        mocker.patch(
            "src.primitives.llm_client.LLMClient.call",
            side_effect=LLMAPIError(error_message),
        )

        # Mock Logger
        mock_logger = Mock()
        mocker.patch("src.primitives.logger.Logger", return_value=mock_logger)

        provider = LLMProvider()

        # Act & Assert: Should raise exception
        with pytest.raises(LLMAPIError) as exc_info:
            provider.generate(
                prompt="Test", provider_config={"config_path": str(valid_llm_config)}
            )

        # Assert: Exception message is descriptive
        assert "500" in str(exc_info.value) or "error" in str(exc_info.value).lower()

        # Assert: Error was logged
        assert (
            mock_logger.error.called or mock_logger.warning.called
        ), "API errors should be logged"

    def test_generate_handles_rate_limit_errors_gracefully(self, valid_llm_config, mocker):
        """
        AC4: generate() handles rate limit errors gracefully

        Verifies LLMProvider handles 429 rate limit errors with proper logging.
        """
        # Arrange
        from src.components.llm_provider import LLMProvider
        from src.primitives.llm_client import RateLimitError

        mocker.patch.dict("os.environ", {"TEST_API_KEY": "test-key"})

        # Mock LLMClient to raise rate limit error
        mocker.patch(
            "src.primitives.llm_client.LLMClient.call",
            side_effect=RateLimitError("Rate limit exceeded (429): Too many requests"),
        )

        # Mock Logger
        mock_logger = Mock()
        mocker.patch("src.primitives.logger.Logger", return_value=mock_logger)

        provider = LLMProvider()

        # Act & Assert: Should raise exception
        with pytest.raises(RateLimitError) as exc_info:
            provider.generate(
                prompt="Test", provider_config={"config_path": str(valid_llm_config)}
            )

        # Assert: Exception message mentions rate limit
        assert "rate limit" in str(exc_info.value).lower() or "429" in str(exc_info.value)

        # Assert: Error was logged
        assert (
            mock_logger.error.called or mock_logger.warning.called
        ), "Rate limit errors should be logged"

    def test_generate_handles_timeout_errors_gracefully(self, valid_llm_config, mocker):
        """
        AC4: generate() handles timeout errors gracefully

        Verifies LLMProvider handles timeout errors with proper logging.
        """
        # Arrange
        from src.components.llm_provider import LLMProvider
        from src.primitives.llm_client import TimeoutError

        mocker.patch.dict("os.environ", {"TEST_API_KEY": "test-key"})

        # Mock LLMClient to raise timeout error
        mocker.patch(
            "src.primitives.llm_client.LLMClient.call",
            side_effect=TimeoutError("Request timeout after 30s"),
        )

        # Mock Logger
        mock_logger = Mock()
        mocker.patch("src.primitives.logger.Logger", return_value=mock_logger)

        provider = LLMProvider()

        # Act & Assert: Should raise exception
        with pytest.raises(TimeoutError) as exc_info:
            provider.generate(
                prompt="Test", provider_config={"config_path": str(valid_llm_config)}
            )

        # Assert: Exception message mentions timeout
        assert "timeout" in str(exc_info.value).lower()

        # Assert: Error was logged
        assert (
            mock_logger.error.called or mock_logger.warning.called
        ), "Timeout errors should be logged"

    def test_generate_validates_config_before_calling_llm(self, temp_config_dir, mocker):
        """
        AC5: generate() validates config before calling LLM (prevents invalid API calls)

        Verifies LLMProvider validates configuration before making LLM calls,
        failing fast on invalid configs.
        """
        # Arrange
        from src.components.llm_provider import LLMProvider

        # Create invalid config (missing required 'model' field)
        invalid_config = {
            "provider": "anthropic",
            "api_key_env": "TEST_API_KEY",
            # Missing 'model'
        }
        config_path = temp_config_dir / "invalid_config.json"
        config_path.write_text(json.dumps(invalid_config), encoding="utf-8")

        mocker.patch.dict("os.environ", {"TEST_API_KEY": "test-key"})

        # Mock LLMClient (should NOT be called due to validation failure)
        mock_llm_call = mocker.patch("src.primitives.llm_client.LLMClient.call")

        # Mock Logger
        mock_logger = Mock()
        mocker.patch("src.primitives.logger.Logger", return_value=mock_logger)

        provider = LLMProvider()

        # Act & Assert: Should raise ValueError on validation failure
        with pytest.raises(ValueError, match="model|config|validation"):
            provider.generate(
                prompt="Test", provider_config={"config_path": str(config_path)}
            )

        # Assert: LLMClient.call was NOT invoked (failed validation before API call)
        assert (
            not mock_llm_call.called
        ), "LLMClient should not be called when config validation fails"

    def test_generate_returns_response_text_or_raises_exception(self, valid_llm_config, mocker):
        """
        AC6: generate() returns response text OR raises exception (no silent failures)

        Verifies LLMProvider always returns valid response or raises exception,
        never returning None or empty string silently.
        """
        # Arrange
        from src.components.llm_provider import LLMProvider

        mocker.patch.dict("os.environ", {"TEST_API_KEY": "test-key"})

        # Mock LLMClient to return valid response
        mock_response = "Valid LLM response text"
        mocker.patch("src.primitives.llm_client.LLMClient.call", return_value=mock_response)

        # Mock Logger
        mock_logger = Mock()
        mocker.patch("src.primitives.logger.Logger", return_value=mock_logger)

        provider = LLMProvider()

        # Act
        response = provider.generate(
            prompt="Test", provider_config={"config_path": str(valid_llm_config)}
        )

        # Assert: Returns actual response text (not None, not empty)
        assert response is not None, "Should not return None"
        assert isinstance(response, str), "Should return string"
        assert len(response) > 0, "Should not return empty string silently"
        assert response == mock_response, "Should return exact LLM response"

    def test_generate_is_stateless_no_instance_state(self, valid_llm_config, mocker):
        """
        Verify generate() is stateless (no instance state between calls)

        Tests that LLMProvider doesn't maintain state between generate() calls,
        consistent with component specification.
        """
        # Arrange
        from src.components.llm_provider import LLMProvider

        mocker.patch.dict("os.environ", {"TEST_API_KEY": "test-key"})

        # Mock LLMClient to return different responses
        mock_responses = ["First response", "Second response"]
        mock_llm_call = mocker.patch(
            "src.primitives.llm_client.LLMClient.call", side_effect=mock_responses
        )

        # Mock Logger
        mock_logger = Mock()
        mocker.patch("src.primitives.logger.Logger", return_value=mock_logger)

        provider = LLMProvider()

        # Act: Make two consecutive calls
        response1 = provider.generate(
            prompt="First prompt", provider_config={"config_path": str(valid_llm_config)}
        )
        response2 = provider.generate(
            prompt="Second prompt", provider_config={"config_path": str(valid_llm_config)}
        )

        # Assert: Each call independent (no state contamination)
        assert response1 == "First response"
        assert response2 == "Second response"
        assert mock_llm_call.call_count == 2

        # Verify each call received correct prompt (no state bleed)
        first_call_prompt = mock_llm_call.call_args_list[0][0][0]
        second_call_prompt = mock_llm_call.call_args_list[1][0][0]
        assert first_call_prompt == "First prompt"
        assert second_call_prompt == "Second prompt"

    def test_generate_handles_empty_prompt_gracefully(self, valid_llm_config, mocker):
        """
        Verify generate() handles empty prompt input

        Tests edge case of empty prompt string.
        """
        # Arrange
        from src.components.llm_provider import LLMProvider

        mocker.patch.dict("os.environ", {"TEST_API_KEY": "test-key"})

        # Mock LLMClient
        mocker.patch("src.primitives.llm_client.LLMClient.call", return_value="Response to empty")

        # Mock Logger
        mock_logger = Mock()
        mocker.patch("src.primitives.logger.Logger", return_value=mock_logger)

        provider = LLMProvider()

        # Act & Assert: Should either accept empty prompt or raise ValueError
        try:
            response = provider.generate(
                prompt="", provider_config={"config_path": str(valid_llm_config)}
            )
            # If it accepts empty prompt, should return valid response
            assert isinstance(response, str)
        except ValueError as e:
            # Or raise descriptive error
            assert "prompt" in str(e).lower() or "empty" in str(e).lower()

    def test_generate_resolves_api_key_from_environment(self, temp_config_dir, mocker):
        """
        Verify generate() resolves API key from environment variable

        Tests that api_key_env is correctly resolved via ConfigLoader's
        environment variable substitution.
        """
        # Arrange
        from src.components.llm_provider import LLMProvider

        # Create config with api_key_env reference
        config = {
            "provider": "anthropic",
            "model": "claude-sonnet-4",
            "api_key_env": "MY_SECRET_KEY",
        }
        config_path = temp_config_dir / "env_config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")

        # Set environment variable
        secret_key = "super-secret-api-key-12345"
        mocker.patch.dict("os.environ", {"MY_SECRET_KEY": secret_key})

        # Mock LLMClient and capture call
        mock_response = "Response"
        mock_llm_call = mocker.patch(
            "src.primitives.llm_client.LLMClient.call", return_value=mock_response
        )

        # Mock Logger
        mock_logger = Mock()
        mocker.patch("src.primitives.logger.Logger", return_value=mock_logger)

        provider = LLMProvider()

        # Act
        response = provider.generate(
            prompt="Test", provider_config={"config_path": str(config_path)}
        )

        # Assert: LLMClient was called with resolved API key
        assert mock_llm_call.called
        call_config = mock_llm_call.call_args[1]["config"]
        assert "api_key" in call_config, "API key should be resolved"
        # Note: exact key value may be transformed, but should be derived from environment

    def test_generate_raises_error_when_config_path_missing(self, mocker):
        """
        AC7: generate() raises ValueError when config_path is missing

        Covers line 94: Missing required parameter 'config_path' validation
        """
        from src.components.llm_provider import LLMProvider

        mock_logger = Mock()
        mocker.patch("src.primitives.logger.Logger", return_value=mock_logger)

        provider = LLMProvider()

        # Act & Assert: Should raise ValueError when config_path is not provided
        with pytest.raises(ValueError, match="config_path"):
            provider.generate(prompt="Test", provider_config={})

    def test_generate_raises_error_when_api_key_env_not_defined(self, temp_config_dir, mocker):
        """
        AC8: generate() raises ValueError when API key environment variable is not defined

        Covers line 111: Environment variable not defined validation
        """
        from src.components.llm_provider import LLMProvider

        config = {
            "provider": "anthropic",
            "model": "claude-sonnet-4",
            "api_key_env": "UNDEFINED_API_KEY_ENV_VAR",
        }
        config_path = temp_config_dir / "no_env_config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")

        # Clear environment to ensure UNDEFINED_API_KEY_ENV_VAR doesn't exist
        mocker.patch.dict("os.environ", {}, clear=True)

        mock_logger = Mock()
        mocker.patch("src.primitives.logger.Logger", return_value=mock_logger)

        provider = LLMProvider()

        # Act & Assert: Should raise ValueError when environment variable not defined
        with pytest.raises(ValueError, match="UNDEFINED_API_KEY_ENV_VAR"):
            provider.generate(prompt="Test", provider_config={"config_path": str(config_path)})
