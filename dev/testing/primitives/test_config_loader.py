"""
TDD Red-Phase Tests for ConfigLoader Primitive

Issue: #6 - [Sprint 1, Day 3] Primitive: ConfigLoader
Status: RED PHASE - All tests should FAIL (no implementation yet)

Test coverage: 5 tests mapping 1:1 to 5 acceptance criteria
"""

import json
import os
import pytest
from pathlib import Path


class TestConfigLoader:
    """Test suite for ConfigLoader primitive - Red Phase"""

    def test_load_returns_dict_from_valid_config(self, tmp_path):
        """
        AC1: Loads valid config files

        Verifies ConfigLoader reads valid JSON config and returns dict
        """
        # Setup: Create valid config file
        config_file = tmp_path / "valid_config.json"
        config_data = {
            "model": "claude-3-opus-20240229",
            "max_tokens": 1000,
            "temperature": 0.7
        }
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        # Action: Load the config
        from src.primitives.config_loader import ConfigLoader
        loader = ConfigLoader()
        result = loader.load(str(config_file))

        # Expected: Returns dict matching exact structure
        assert isinstance(result, dict)
        assert result["model"] == "claude-3-opus-20240229"
        assert result["max_tokens"] == 1000
        assert result["temperature"] == 0.7

    def test_validate_rejects_invalid_config_structure(self, tmp_path):
        """
        AC2: Validates config structure

        Verifies ConfigLoader validates required fields and raises error on invalid structure
        """
        # Setup: Create config with missing required field
        config_file = tmp_path / "invalid_config.json"
        invalid_data = {
            "max_tokens": 1000
            # Missing "model" field
        }
        config_file.write_text(json.dumps(invalid_data), encoding="utf-8")

        # Setup: Define schema requiring "model" field
        schema = {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "max_tokens": {"type": "integer"}
            },
            "required": ["model"]
        }

        # Action & Expected: Should raise ValueError with validation error
        from src.primitives.config_loader import ConfigLoader
        loader = ConfigLoader()

        with pytest.raises(ValueError) as exc_info:
            loader.load(str(config_file), schema=schema)

        # Error message should indicate missing "model" field
        error_msg = str(exc_info.value)
        assert "model" in error_msg.lower() or "required" in error_msg.lower()

    def test_substitutes_environment_variables(self, tmp_path, monkeypatch):
        """
        AC3: Substitutes environment variables

        Verifies ConfigLoader replaces environment variable placeholders with actual values
        """
        # Setup: Set environment variables
        monkeypatch.setenv("TEST_MODEL", "claude-3-sonnet-20240229")
        monkeypatch.setenv("TEST_API_KEY", "test-key-12345")

        # Setup: Create config file with env var placeholders
        config_file = tmp_path / "env_config.json"
        config_data = {
            "model": "${TEST_MODEL}",
            "api_key": "${TEST_API_KEY}"
        }
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        # Action: Load the config
        from src.primitives.config_loader import ConfigLoader
        loader = ConfigLoader()
        result = loader.load(str(config_file))

        # Expected: Returns dict with substituted values
        assert result["model"] == "claude-3-sonnet-20240229"
        assert result["api_key"] == "test-key-12345"
        # Ensure no placeholder strings remain
        assert "${" not in str(result)

    def test_raises_clear_error_on_malformed_json(self, tmp_path):
        """
        AC4: Raises clear errors on invalid config

        Verifies ConfigLoader provides helpful error messages for malformed JSON
        """
        # Setup: Create config file with malformed JSON
        config_file = tmp_path / "malformed_config.json"
        config_file.write_text('{"model": "claude", "missing_close"', encoding="utf-8")

        # Action & Expected: Should raise exception with clear error
        from src.primitives.config_loader import ConfigLoader
        loader = ConfigLoader()

        with pytest.raises((json.JSONDecodeError, ValueError)) as exc_info:
            loader.load(str(config_file))

        # Error message should indicate JSON parsing failure
        error_msg = str(exc_info.value)
        assert "JSON" in error_msg or "Expecting" in error_msg or "malformed" in error_msg.lower()

    def test_handles_missing_config_file(self):
        """
        AC5: Handles missing config files

        Verifies ConfigLoader raises clear error when config file doesn't exist
        """
        # Setup: Non-existent config path
        non_existent_path = "/tmp/missing_config_12345.json"

        # Action & Expected: Should raise FileNotFoundError
        from src.primitives.config_loader import ConfigLoader
        loader = ConfigLoader()

        with pytest.raises(FileNotFoundError) as exc_info:
            loader.load(non_existent_path)

        # Error message should include the file path
        assert non_existent_path in str(exc_info.value)


class TestConfigLoaderConvenienceMethods:
    """Test suite for ConfigLoader convenience methods - Red Phase"""

    def test_load_supervisor_config(self, tmp_path, monkeypatch):
        """
        Verify supervisor config loading with standard path convention

        Tests load_supervisor_config() method
        """
        # Setup: Create configs directory
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir()

        # Setup: Create supervisor config file
        pod_id = "pod-001"
        supervisor_config_file = configs_dir / f"supervisor_{pod_id}.json"
        supervisor_data = {
            "model": "claude-3-opus-20240229",
            "max_tokens": 2000
        }
        supervisor_config_file.write_text(json.dumps(supervisor_data), encoding="utf-8")

        # Setup: Change to tmp directory (so configs/ is relative)
        monkeypatch.chdir(tmp_path)

        # Action: Load supervisor config
        from src.primitives.config_loader import ConfigLoader
        loader = ConfigLoader()
        result = loader.load_supervisor_config(pod_id)

        # Expected: Loads from correct path and returns dict
        assert isinstance(result, dict)
        assert result["model"] == "claude-3-opus-20240229"
        assert result["max_tokens"] == 2000

    def test_load_worker_config(self, tmp_path, monkeypatch):
        """
        Verify worker config loading with standard path convention

        Tests load_worker_config() method
        """
        # Setup: Create configs directory
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir()

        # Setup: Create worker config file
        pod_id = "pod-001"
        worker_id = "worker-001"
        worker_config_file = configs_dir / f"worker_{pod_id}_{worker_id}.json"
        worker_data = {
            "model": "gpt-4-turbo-preview",
            "max_tokens": 1500,
            "temperature": 0.5
        }
        worker_config_file.write_text(json.dumps(worker_data), encoding="utf-8")

        # Setup: Change to tmp directory (so configs/ is relative)
        monkeypatch.chdir(tmp_path)

        # Action: Load worker config
        from src.primitives.config_loader import ConfigLoader
        loader = ConfigLoader()
        result = loader.load_worker_config(pod_id, worker_id)

        # Expected: Loads from correct path and returns dict
        assert isinstance(result, dict)
        assert result["model"] == "gpt-4-turbo-preview"
        assert result["max_tokens"] == 1500
        assert result["temperature"] == 0.5


class TestEnvironmentVariableSubstitution:
    """Additional tests for environment variable substitution edge cases"""

    def test_raises_error_for_undefined_env_var(self, tmp_path):
        """
        Verify ConfigLoader raises error when environment variable is not defined

        Edge case test for env var substitution
        """
        # Setup: Create config with undefined env var
        config_file = tmp_path / "undefined_env.json"
        config_data = {
            "model": "${UNDEFINED_VAR_12345}"
        }
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        # Action & Expected: Should raise ValueError
        from src.primitives.config_loader import ConfigLoader
        loader = ConfigLoader()

        with pytest.raises(ValueError) as exc_info:
            loader.load(str(config_file))

        # Error message should mention the undefined variable
        error_msg = str(exc_info.value)
        assert "UNDEFINED_VAR_12345" in error_msg or "environment" in error_msg.lower()

    def test_substitutes_nested_values(self, tmp_path, monkeypatch):
        """
        Verify ConfigLoader substitutes env vars in nested structures

        Tests env var substitution in nested JSON objects
        """
        # Setup: Set environment variables
        monkeypatch.setenv("NESTED_MODEL", "claude-3-sonnet-20240229")
        monkeypatch.setenv("NESTED_KEY", "nested-key-value")

        # Setup: Create config with nested env var placeholders
        config_file = tmp_path / "nested_env.json"
        config_data = {
            "outer": {
                "model": "${NESTED_MODEL}",
                "inner": {
                    "api_key": "${NESTED_KEY}"
                }
            }
        }
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        # Action: Load the config
        from src.primitives.config_loader import ConfigLoader
        loader = ConfigLoader()
        result = loader.load(str(config_file))

        # Expected: Nested env vars are substituted
        assert result["outer"]["model"] == "claude-3-sonnet-20240229"
        assert result["outer"]["inner"]["api_key"] == "nested-key-value"
        # Ensure no placeholder strings remain
        assert "${" not in json.dumps(result)

    def test_substitution_handles_primitive_types(self, tmp_path):
        """
        Verify ConfigLoader handles primitive types (int, float, bool, null) without modification

        Tests env var substitution preserves non-string primitive values
        """
        # Setup: Create config with primitive types (no env vars)
        config_file = tmp_path / "primitives.json"
        config_data = {
            "count": 42,
            "ratio": 3.14,
            "enabled": True,
            "disabled": False,
            "empty": None
        }
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        # Action: Load the config
        from src.primitives.config_loader import ConfigLoader
        loader = ConfigLoader()
        result = loader.load(str(config_file))

        # Expected: Primitive values preserved (not treated as strings)
        assert result["count"] == 42
        assert result["ratio"] == 3.14
        assert result["enabled"] is True
        assert result["disabled"] is False
        assert result["empty"] is None

    def test_substitution_handles_env_vars_in_arrays(self, tmp_path, monkeypatch):
        """
        Verify ConfigLoader substitutes env vars in array values

        Tests env var substitution in arrays
        """
        # Setup: Set environment variables
        monkeypatch.setenv("ARRAY_ITEM_1", "value1")
        monkeypatch.setenv("ARRAY_ITEM_2", "value2")

        # Setup: Create config with env vars in array
        config_file = tmp_path / "array_env.json"
        config_data = {
            "items": ["${ARRAY_ITEM_1}", "${ARRAY_ITEM_2}", "static_value"]
        }
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        # Action: Load the config
        from src.primitives.config_loader import ConfigLoader
        loader = ConfigLoader()
        result = loader.load(str(config_file))

        # Expected: Array env vars are substituted
        assert result["items"] == ["value1", "value2", "static_value"]
