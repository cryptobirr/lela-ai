"""
LLMProvider Component - Unified interface for all LLM providers

Issue: #15 - [Sprint 2, Day 2] Component: LLMProvider
Status: REFACTOR PHASE - Improving code quality while maintaining test coverage

Composition:
- LLMClient (primitive) - Makes LLM API calls
- ConfigLoader (primitive) - Loads config files
- Logger (primitive) - Logs all interactions

Interface:
- generate(prompt: str, provider_config: dict) -> str
- validate_config(config: dict) -> tuple[bool, list[str]]

State: Stateless (uses config per call)
"""

import os
from typing import Any

from src.primitives.config_loader import ConfigLoader
from src.primitives.llm_client import LLMClient, LLMAPIError, RateLimitError, TimeoutError
from src.primitives import logger


class LLMProvider:
    """Unified LLM provider interface with config loading, logging, and error handling"""

    DEFAULT_TIMEOUT = 30  # Default LLM call timeout in seconds

    def __init__(self):
        """Initialize LLMProvider (stateless, no instance state)"""
        self.llm_client = LLMClient()
        self.config_loader = ConfigLoader()
        self.logger = logger.Logger()

    def _validate_prompt(self, prompt: str) -> None:
        """
        Validate prompt is not empty

        Args:
            prompt: Input prompt text

        Raises:
            ValueError: If prompt is empty or whitespace-only
        """
        if not prompt or (isinstance(prompt, str) and len(prompt.strip()) == 0):
            raise ValueError("Prompt cannot be empty")

    def _load_and_validate_config(self, config_path: str) -> dict[str, Any]:
        """
        Load config from file and validate it

        Args:
            config_path: Path to configuration file

        Returns:
            Validated configuration dictionary

        Raises:
            ValueError: If config is invalid
        """
        config = self.config_loader.load(config_path)
        is_valid, errors = self.validate_config(config)
        if not is_valid:
            error_msg = f"Config validation failed: {'; '.join(errors)}"
            self.logger.error(error_msg, context={"errors": errors, "config_path": config_path})
            raise ValueError(error_msg)
        return config

    def _resolve_api_key(self, config: dict[str, Any]) -> str | None:
        """
        Resolve API key from environment variable

        Args:
            config: LLM configuration with optional 'api_key_env' field

        Returns:
            API key string or None if not configured

        Raises:
            ValueError: If api_key_env is specified but environment variable is not defined
        """
        if "api_key_env" not in config:
            return None

        api_key_env = config["api_key_env"]
        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise ValueError(f"Environment variable '{api_key_env}' is not defined")
        return api_key

    def _build_llm_config(self, config: dict[str, Any], api_key: str | None) -> dict[str, Any]:
        """
        Build LLMClient configuration dictionary

        Args:
            config: Validated LLM configuration
            api_key: Resolved API key (may be None)

        Returns:
            Configuration dictionary for LLMClient.call()
        """
        return {
            "provider": config["provider"],
            "model": config["model"],
            "api_key": api_key,
            "timeout": config.get("timeout", self.DEFAULT_TIMEOUT),
        }

    def _build_log_context(
        self, prompt: str, config: dict[str, Any], response: str | None = None, error: str | None = None
    ) -> dict[str, Any]:
        """
        Build logging context dictionary

        Args:
            prompt: The prompt text
            config: LLM configuration
            response: Optional response text
            error: Optional error message

        Returns:
            Dictionary with logging context
        """
        context = {
            "prompt": prompt,
            "provider": config["provider"],
            "model": config["model"],
        }
        if response is not None:
            context["response"] = response
        if error is not None:
            context["error"] = error
        return context

    def validate_config(self, config: dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Validate LLM configuration

        Args:
            config: Configuration dict with keys:
                - provider: Provider name (required)
                - model: Model name (required)
                - api_key_env: Environment variable name for API key (optional)
                - timeout: Timeout in seconds (optional)

        Returns:
            Tuple of (is_valid, error_messages)
            - is_valid: True if config is valid, False otherwise
            - error_messages: List of error messages (empty if valid)
        """
        errors = []

        # Check required fields
        if "provider" not in config:
            errors.append("Missing required field: 'provider'")

        if "model" not in config:
            errors.append("Missing required field: 'model'")

        # Validate provider is supported
        if "provider" in config:
            provider = config["provider"]
            if not self.llm_client.supports_provider(provider):
                errors.append(f"Unsupported provider: '{provider}'")

        return (len(errors) == 0, errors)

    def generate(self, prompt: str, provider_config: dict[str, Any]) -> str:
        """
        Generate LLM response

        Args:
            prompt: Input prompt text
            provider_config: Configuration dict with keys:
                - config_path: Path to config file (required)

        Returns:
            Response text from LLM

        Raises:
            ValueError: If config validation fails or prompt is empty
            LLMAPIError: For API failures
            RateLimitError: For rate limit errors
            TimeoutError: For timeout errors
        """
        # Validate prompt
        self._validate_prompt(prompt)

        # Extract and validate config_path
        config_path = provider_config.get("config_path")
        if not config_path:
            raise ValueError("Missing required parameter: 'config_path'")

        # Load and validate configuration
        config = self._load_and_validate_config(config_path)

        # Resolve API key from environment
        api_key = self._resolve_api_key(config)

        # Build LLMClient configuration
        llm_config = self._build_llm_config(config, api_key)

        # Log the LLM call before making it
        self.logger.info("Making LLM call", context=self._build_log_context(prompt, config))

        # Call LLM
        try:
            response = self.llm_client.call(prompt, config=llm_config)

            # Log successful response
            self.logger.info(
                "LLM call successful", context=self._build_log_context(prompt, config, response=response)
            )

            return response

        except (LLMAPIError, RateLimitError, TimeoutError) as e:
            # Log error
            self.logger.error(
                "LLM call failed", context=self._build_log_context(prompt, config, error=str(e))
            )
            # Re-raise exception (no silent failures)
            raise
