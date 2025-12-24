"""
LLMProvider Component - Unified interface for all LLM providers

Issue: #15 - [Sprint 2, Day 2] Component: LLMProvider
Status: GREEN PHASE - Implementing minimal code to make tests pass

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

    def __init__(self):
        """Initialize LLMProvider (stateless, no instance state)"""
        self.llm_client = LLMClient()
        self.config_loader = ConfigLoader()
        self.logger = logger.Logger()

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
        if not prompt or (isinstance(prompt, str) and len(prompt.strip()) == 0):
            raise ValueError("Prompt cannot be empty")

        # Load config from file
        config_path = provider_config.get("config_path")
        if not config_path:
            raise ValueError("Missing required parameter: 'config_path'")

        config = self.config_loader.load(config_path)

        # Validate config before calling LLM
        is_valid, errors = self.validate_config(config)
        if not is_valid:
            error_msg = f"Config validation failed: {'; '.join(errors)}"
            self.logger.error(error_msg, context={"errors": errors, "config_path": config_path})
            raise ValueError(error_msg)

        # Resolve API key from environment variable
        api_key = None
        if "api_key_env" in config:
            api_key_env = config["api_key_env"]
            api_key = os.environ.get(api_key_env)
            if not api_key:
                raise ValueError(f"Environment variable '{api_key_env}' is not defined")

        # Build LLMClient config
        llm_config = {
            "provider": config["provider"],
            "model": config["model"],
            "api_key": api_key,
            "timeout": config.get("timeout", 30),
        }

        # Log the LLM call before making it
        self.logger.info(
            "Making LLM call",
            context={
                "prompt": prompt,
                "provider": config["provider"],
                "model": config["model"],
            },
        )

        # Call LLM
        try:
            response = self.llm_client.call(prompt, config=llm_config)

            # Log successful response
            self.logger.info(
                "LLM call successful",
                context={
                    "prompt": prompt,
                    "response": response,
                    "provider": config["provider"],
                    "model": config["model"],
                },
            )

            return response

        except (LLMAPIError, RateLimitError, TimeoutError) as e:
            # Log error
            self.logger.error(
                "LLM call failed",
                context={
                    "prompt": prompt,
                    "provider": config["provider"],
                    "model": config["model"],
                    "error": str(e),
                },
            )
            # Re-raise exception (no silent failures)
            raise
