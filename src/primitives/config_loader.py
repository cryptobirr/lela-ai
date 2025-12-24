"""
ConfigLoader Primitive

Loads agent configuration from files with validation and environment variable substitution.
"""

import os
import re
from typing import Optional, Union

from src.primitives.file_reader import FileReader
from src.primitives.json_validator import JSONValidator


class ConfigLoader:
    """Loads and validates agent configuration files"""

    # Environment variable pattern: ${VAR_NAME}
    ENV_VAR_PATTERN = r"\$\{([^}]+)\}"

    def __init__(self):
        self.file_reader = FileReader()
        self.validator = JSONValidator()

    def load(self, config_path: str, schema: Optional[dict] = None) -> dict:
        """
        Load configuration file with optional validation and env var substitution

        Args:
            config_path: Path to the JSON config file
            schema: Optional JSON schema for validation

        Returns:
            dict: Loaded and processed configuration

        Raises:
            FileNotFoundError: If config file doesn't exist
            json.JSONDecodeError: If JSON is malformed
            ValueError: If config fails validation or env var is undefined
        """
        # Read the config file
        config = self.file_reader.read(config_path)

        # Substitute environment variables
        config = self._substitute_env_vars(config)

        # Validate against schema if provided
        if schema:
            is_valid, error_messages = self.validator.validate(config, schema)
            if not is_valid:
                # Report first validation error for clarity
                raise ValueError(f"Config validation failed: {error_messages[0]}")

        return config

    def _substitute_env_vars(
        self, data: Union[dict, list, str, int, float, bool, None]
    ) -> Union[dict, list, str, int, float, bool, None]:
        """
        Recursively substitute environment variables in config data

        Supports ${VAR_NAME} syntax for environment variable substitution

        Args:
            data: Configuration data (dict, list, str, or primitive)

        Returns:
            Data with environment variables substituted

        Raises:
            ValueError: If environment variable is not defined
        """
        if isinstance(data, dict):
            return {key: self._substitute_env_vars(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._substitute_env_vars(item) for item in data]
        elif isinstance(data, str):
            # Match ${VAR_NAME} pattern
            matches = re.findall(self.ENV_VAR_PATTERN, data)

            for var_name in matches:
                if var_name not in os.environ:
                    raise ValueError(f"Environment variable '{var_name}' is not defined")
                data = data.replace(f"${{{var_name}}}", os.environ[var_name])

            return data
        else:
            return data

    def load_supervisor_config(self, pod_id: str) -> dict:
        """
        Load supervisor configuration using standard path convention

        Args:
            pod_id: Pod identifier

        Returns:
            dict: Supervisor configuration

        Raises:
            FileNotFoundError: If config file doesn't exist
        """
        config_path = f"configs/supervisor_{pod_id}.json"
        return self.load(config_path)

    def load_worker_config(self, pod_id: str, worker_id: str) -> dict:
        """
        Load worker configuration using standard path convention

        Args:
            pod_id: Pod identifier
            worker_id: Worker identifier

        Returns:
            dict: Worker configuration

        Raises:
            FileNotFoundError: If config file doesn't exist
        """
        config_path = f"configs/worker_{pod_id}_{worker_id}.json"
        return self.load(config_path)
