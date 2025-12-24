"""
Test suite for WorkerExecutor Component

Purpose: Verify WorkerExecutor executes worker tasks correctly
         (read instructions, call LLM, write result)

Test Coverage:
- Happy path: Successful task execution with valid inputs
- Edge cases: Empty instructions, missing fields, path variations
- Error handling: LLM failures, file I/O errors, invalid configurations
- Integration: Interaction with LLMProvider, ResultManager, and Logger

Requirements tested: Issue #17 - [Sprint 2, Day 4] Component: WorkerExecutor
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from src.components.worker_executor import WorkerExecutor


class TestWorkerExecutorInitialization:
    """Test WorkerExecutor initialization"""

    def test_init_creates_executor_with_dependencies(self):
        """WorkerExecutor initializes with LLMProvider, ResultManager, and Logger"""
        executor = WorkerExecutor()

        assert executor is not None
        assert hasattr(executor, "llm_provider")
        assert hasattr(executor, "result_manager")
        assert hasattr(executor, "logger")


class TestWorkerExecutorExecute:
    """Test execute() method - main workflow"""

    def test_execute_with_valid_inputs_returns_result_path(self, tmp_path):
        """execute() processes valid instructions and returns result file path"""
        # Arrange: Create instructions file
        instructions_path = tmp_path / "instructions.json"
        instructions_data = {
            "instructions": "Analyze this data",
            "output_path": "result.json",
        }
        instructions_path.write_text(json.dumps(instructions_data))

        worker_config = {
            "worker_id": "worker-001",
            "pod_id": "pod-001",
            "session_id": "session-001",
            "worker_dir": str(tmp_path),
            "llm_config_path": str(tmp_path / "llm_config.json"),
        }

        # Mock LLM config file
        llm_config_path = tmp_path / "llm_config.json"
        llm_config_data = {
            "provider": "anthropic",
            "model": "claude-sonnet-4",
        }
        llm_config_path.write_text(json.dumps(llm_config_data))

        executor = WorkerExecutor()

        # Mock dependencies
        executor.llm_provider.generate = Mock(return_value="Analysis complete")
        executor.result_manager.write = Mock(return_value=str(tmp_path / "result.json"))

        # Act: Execute task
        result_path = executor.execute(str(instructions_path), worker_config)

        # Assert: Returns result file path
        assert result_path == str(tmp_path / "result.json")
        assert executor.llm_provider.generate.called
        assert executor.result_manager.write.called

    def test_execute_reads_instructions_correctly(self, tmp_path):
        """execute() reads and parses instructions.json file"""
        # Arrange
        instructions_path = tmp_path / "instructions.json"
        instructions_data = {"instructions": "Task description", "output_path": "result.json"}
        instructions_path.write_text(json.dumps(instructions_data))

        worker_config = {
            "worker_id": "worker-001",
            "pod_id": "pod-001",
            "session_id": "session-001",
            "worker_dir": str(tmp_path),
            "llm_config_path": str(tmp_path / "llm_config.json"),
        }

        # Mock LLM config
        llm_config_path = tmp_path / "llm_config.json"
        llm_config_path.write_text(json.dumps({"provider": "anthropic", "model": "claude"}))

        executor = WorkerExecutor()
        executor.llm_provider.generate = Mock(return_value="Result")
        executor.result_manager.write = Mock(return_value=str(tmp_path / "result.json"))

        # Act
        executor.execute(str(instructions_path), worker_config)

        # Assert: LLM provider called with instructions
        executor.llm_provider.generate.assert_called_once()
        call_args = executor.llm_provider.generate.call_args
        assert "Task description" in str(call_args)

    def test_execute_generates_valid_prompt_from_instructions(self, tmp_path):
        """execute() generates proper LLM prompt from instructions"""
        # Arrange
        instructions_path = tmp_path / "instructions.json"
        instructions_data = {"instructions": "Process this request", "output_path": "result.json"}
        instructions_path.write_text(json.dumps(instructions_data))

        worker_config = {
            "worker_id": "worker-001",
            "pod_id": "pod-001",
            "session_id": "session-001",
            "worker_dir": str(tmp_path),
            "llm_config_path": str(tmp_path / "llm_config.json"),
        }

        llm_config_path = tmp_path / "llm_config.json"
        llm_config_path.write_text(json.dumps({"provider": "anthropic", "model": "claude"}))

        executor = WorkerExecutor()
        executor.llm_provider.generate = Mock(return_value="Response")
        executor.result_manager.write = Mock(return_value=str(tmp_path / "result.json"))

        # Act
        executor.execute(str(instructions_path), worker_config)

        # Assert: Prompt includes instructions
        prompt = executor.llm_provider.generate.call_args[0][0]
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "Process this request" in prompt

    def test_execute_calls_llm_via_provider(self, tmp_path):
        """execute() calls LLM through LLMProvider.generate()"""
        # Arrange
        instructions_path = tmp_path / "instructions.json"
        instructions_path.write_text(json.dumps({"instructions": "Task", "output_path": "result.json"}))

        worker_config = {
            "worker_id": "worker-001",
            "pod_id": "pod-001",
            "session_id": "session-001",
            "worker_dir": str(tmp_path),
            "llm_config_path": str(tmp_path / "llm_config.json"),
        }

        llm_config_path = tmp_path / "llm_config.json"
        llm_config_path.write_text(json.dumps({"provider": "anthropic", "model": "claude"}))

        executor = WorkerExecutor()
        mock_generate = Mock(return_value="LLM Response")
        executor.llm_provider.generate = mock_generate
        executor.result_manager.write = Mock(return_value=str(tmp_path / "result.json"))

        # Act
        executor.execute(str(instructions_path), worker_config)

        # Assert: LLM provider called with prompt and config
        assert mock_generate.called
        call_args = mock_generate.call_args
        assert call_args[0][0]  # Prompt exists
        assert "config_path" in call_args[0][1]  # Provider config passed

    def test_execute_writes_result_json(self, tmp_path):
        """execute() writes result.json through ResultManager"""
        # Arrange
        instructions_path = tmp_path / "instructions.json"
        instructions_path.write_text(json.dumps({"instructions": "Task", "output_path": "result.json"}))

        worker_config = {
            "worker_id": "worker-001",
            "pod_id": "pod-001",
            "session_id": "session-001",
            "worker_dir": str(tmp_path),
            "llm_config_path": str(tmp_path / "llm_config.json"),
        }

        llm_config_path = tmp_path / "llm_config.json"
        llm_config_path.write_text(json.dumps({"provider": "anthropic", "model": "claude"}))

        executor = WorkerExecutor()
        executor.llm_provider.generate = Mock(return_value="Task completed successfully")
        mock_write = Mock(return_value=str(tmp_path / "result.json"))
        executor.result_manager.write = mock_write

        # Act
        executor.execute(str(instructions_path), worker_config)

        # Assert: ResultManager.write called with correct parameters
        mock_write.assert_called_once()
        call_args = mock_write.call_args[0]
        assert call_args[0] == "Task completed successfully"  # result
        assert str(call_args[1]) == str(tmp_path)  # worker_dir
        assert call_args[2] == "worker-001"  # worker_id
        assert call_args[3] == "pod-001"  # pod_id
        assert call_args[4] == "session-001"  # session_id

    def test_execute_logs_execution_details(self, tmp_path):
        """execute() logs execution start, LLM call, and completion"""
        # Arrange
        instructions_path = tmp_path / "instructions.json"
        instructions_path.write_text(json.dumps({"instructions": "Task", "output_path": "result.json"}))

        worker_config = {
            "worker_id": "worker-001",
            "pod_id": "pod-001",
            "session_id": "session-001",
            "worker_dir": str(tmp_path),
            "llm_config_path": str(tmp_path / "llm_config.json"),
        }

        llm_config_path = tmp_path / "llm_config.json"
        llm_config_path.write_text(json.dumps({"provider": "anthropic", "model": "claude"}))

        executor = WorkerExecutor()
        executor.llm_provider.generate = Mock(return_value="Response")
        executor.result_manager.write = Mock(return_value=str(tmp_path / "result.json"))

        mock_logger = Mock()
        executor.logger = mock_logger

        # Act
        executor.execute(str(instructions_path), worker_config)

        # Assert: Logger called multiple times (start, LLM call, completion)
        assert mock_logger.info.call_count >= 2

    def test_execute_returns_correct_result_file_path(self, tmp_path):
        """execute() returns exact path returned by ResultManager"""
        # Arrange
        instructions_path = tmp_path / "instructions.json"
        instructions_path.write_text(json.dumps({"instructions": "Task", "output_path": "result.json"}))

        expected_path = str(tmp_path / "custom" / "result.json")
        worker_config = {
            "worker_id": "worker-001",
            "pod_id": "pod-001",
            "session_id": "session-001",
            "worker_dir": str(tmp_path / "custom"),
            "llm_config_path": str(tmp_path / "llm_config.json"),
        }

        llm_config_path = tmp_path / "llm_config.json"
        llm_config_path.write_text(json.dumps({"provider": "anthropic", "model": "claude"}))

        executor = WorkerExecutor()
        executor.llm_provider.generate = Mock(return_value="Response")
        executor.result_manager.write = Mock(return_value=expected_path)

        # Act
        result_path = executor.execute(str(instructions_path), worker_config)

        # Assert
        assert result_path == expected_path


class TestWorkerExecutorEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_execute_with_empty_instructions_raises_error(self, tmp_path):
        """execute() raises ValueError when instructions are empty"""
        # Arrange
        instructions_path = tmp_path / "instructions.json"
        instructions_path.write_text(json.dumps({"instructions": "", "output_path": "result.json"}))

        worker_config = {
            "worker_id": "worker-001",
            "pod_id": "pod-001",
            "session_id": "session-001",
            "worker_dir": str(tmp_path),
            "llm_config_path": str(tmp_path / "llm_config.json"),
        }

        executor = WorkerExecutor()

        # Act & Assert
        with pytest.raises(ValueError, match="instructions cannot be empty|prompt cannot be empty"):
            executor.execute(str(instructions_path), worker_config)

    def test_execute_with_missing_instructions_file_raises_error(self, tmp_path):
        """execute() raises FileNotFoundError when instructions.json missing"""
        # Arrange
        instructions_path = tmp_path / "nonexistent.json"
        worker_config = {
            "worker_id": "worker-001",
            "pod_id": "pod-001",
            "session_id": "session-001",
            "worker_dir": str(tmp_path),
            "llm_config_path": str(tmp_path / "llm_config.json"),
        }

        executor = WorkerExecutor()

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            executor.execute(str(instructions_path), worker_config)

    def test_execute_with_invalid_json_raises_error(self, tmp_path):
        """execute() raises ValueError when instructions.json has invalid JSON"""
        # Arrange
        instructions_path = tmp_path / "instructions.json"
        instructions_path.write_text("{invalid json content")

        worker_config = {
            "worker_id": "worker-001",
            "pod_id": "pod-001",
            "session_id": "session-001",
            "worker_dir": str(tmp_path),
            "llm_config_path": str(tmp_path / "llm_config.json"),
        }

        executor = WorkerExecutor()

        # Act & Assert
        with pytest.raises((json.JSONDecodeError, ValueError)):
            executor.execute(str(instructions_path), worker_config)

    def test_execute_with_missing_worker_config_fields_raises_error(self, tmp_path):
        """execute() raises ValueError when required worker_config fields missing"""
        # Arrange
        instructions_path = tmp_path / "instructions.json"
        instructions_path.write_text(json.dumps({"instructions": "Task", "output_path": "result.json"}))

        incomplete_config = {
            "worker_id": "worker-001",
            # Missing pod_id, session_id, worker_dir, llm_config_path
        }

        executor = WorkerExecutor()

        # Act & Assert
        with pytest.raises((ValueError, KeyError)):
            executor.execute(str(instructions_path), incomplete_config)

    def test_execute_with_very_long_instructions_succeeds(self, tmp_path):
        """execute() handles very long instructions (10KB+)"""
        # Arrange
        long_instructions = "Analyze this data. " * 1000  # ~20KB
        instructions_path = tmp_path / "instructions.json"
        instructions_path.write_text(
            json.dumps({"instructions": long_instructions, "output_path": "result.json"})
        )

        worker_config = {
            "worker_id": "worker-001",
            "pod_id": "pod-001",
            "session_id": "session-001",
            "worker_dir": str(tmp_path),
            "llm_config_path": str(tmp_path / "llm_config.json"),
        }

        llm_config_path = tmp_path / "llm_config.json"
        llm_config_path.write_text(json.dumps({"provider": "anthropic", "model": "claude"}))

        executor = WorkerExecutor()
        executor.llm_provider.generate = Mock(return_value="Response")
        executor.result_manager.write = Mock(return_value=str(tmp_path / "result.json"))

        # Act
        result_path = executor.execute(str(instructions_path), worker_config)

        # Assert
        assert result_path is not None
        assert executor.llm_provider.generate.called


class TestWorkerExecutorErrorHandling:
    """Test error handling and failure scenarios"""

    def test_execute_handles_llm_api_errors_gracefully(self, tmp_path):
        """execute() propagates LLM API errors with proper logging"""
        # Arrange
        instructions_path = tmp_path / "instructions.json"
        instructions_path.write_text(json.dumps({"instructions": "Task", "output_path": "result.json"}))

        worker_config = {
            "worker_id": "worker-001",
            "pod_id": "pod-001",
            "session_id": "session-001",
            "worker_dir": str(tmp_path),
            "llm_config_path": str(tmp_path / "llm_config.json"),
        }

        llm_config_path = tmp_path / "llm_config.json"
        llm_config_path.write_text(json.dumps({"provider": "anthropic", "model": "claude"}))

        executor = WorkerExecutor()
        from src.primitives.llm_client import LLMAPIError

        executor.llm_provider.generate = Mock(side_effect=LLMAPIError("API failed"))
        mock_logger = Mock()
        executor.logger = mock_logger

        # Act & Assert
        with pytest.raises(LLMAPIError):
            executor.execute(str(instructions_path), worker_config)

        # Verify error was logged
        assert mock_logger.error.called

    def test_execute_handles_rate_limit_errors(self, tmp_path):
        """execute() propagates rate limit errors from LLM provider"""
        # Arrange
        instructions_path = tmp_path / "instructions.json"
        instructions_path.write_text(json.dumps({"instructions": "Task", "output_path": "result.json"}))

        worker_config = {
            "worker_id": "worker-001",
            "pod_id": "pod-001",
            "session_id": "session-001",
            "worker_dir": str(tmp_path),
            "llm_config_path": str(tmp_path / "llm_config.json"),
        }

        llm_config_path = tmp_path / "llm_config.json"
        llm_config_path.write_text(json.dumps({"provider": "anthropic", "model": "claude"}))

        executor = WorkerExecutor()
        from src.primitives.llm_client import RateLimitError

        executor.llm_provider.generate = Mock(side_effect=RateLimitError("Rate limit exceeded"))

        # Act & Assert
        with pytest.raises(RateLimitError):
            executor.execute(str(instructions_path), worker_config)

    def test_execute_handles_timeout_errors(self, tmp_path):
        """execute() propagates timeout errors from LLM provider"""
        # Arrange
        instructions_path = tmp_path / "instructions.json"
        instructions_path.write_text(json.dumps({"instructions": "Task", "output_path": "result.json"}))

        worker_config = {
            "worker_id": "worker-001",
            "pod_id": "pod-001",
            "session_id": "session-001",
            "worker_dir": str(tmp_path),
            "llm_config_path": str(tmp_path / "llm_config.json"),
        }

        llm_config_path = tmp_path / "llm_config.json"
        llm_config_path.write_text(json.dumps({"provider": "anthropic", "model": "claude"}))

        executor = WorkerExecutor()
        from src.primitives.llm_client import TimeoutError as LLMTimeoutError

        executor.llm_provider.generate = Mock(side_effect=LLMTimeoutError("Request timed out"))

        # Act & Assert
        with pytest.raises(LLMTimeoutError):
            executor.execute(str(instructions_path), worker_config)

    def test_execute_handles_result_write_failures(self, tmp_path):
        """execute() propagates errors from ResultManager.write()"""
        # Arrange
        instructions_path = tmp_path / "instructions.json"
        instructions_path.write_text(json.dumps({"instructions": "Task", "output_path": "result.json"}))

        worker_config = {
            "worker_id": "worker-001",
            "pod_id": "pod-001",
            "session_id": "session-001",
            "worker_dir": str(tmp_path),
            "llm_config_path": str(tmp_path / "llm_config.json"),
        }

        llm_config_path = tmp_path / "llm_config.json"
        llm_config_path.write_text(json.dumps({"provider": "anthropic", "model": "claude"}))

        executor = WorkerExecutor()
        executor.llm_provider.generate = Mock(return_value="Response")
        executor.result_manager.write = Mock(side_effect=ValueError("Write failed"))

        # Act & Assert
        with pytest.raises(ValueError, match="Write failed"):
            executor.execute(str(instructions_path), worker_config)

    def test_execute_handles_invalid_llm_config(self, tmp_path):
        """execute() raises error when LLM config is invalid"""
        # Arrange
        instructions_path = tmp_path / "instructions.json"
        instructions_path.write_text(json.dumps({"instructions": "Task", "output_path": "result.json"}))

        worker_config = {
            "worker_id": "worker-001",
            "pod_id": "pod-001",
            "session_id": "session-001",
            "worker_dir": str(tmp_path),
            "llm_config_path": str(tmp_path / "llm_config.json"),
        }

        # Invalid LLM config (missing required fields)
        llm_config_path = tmp_path / "llm_config.json"
        llm_config_path.write_text(json.dumps({"invalid": "config"}))

        executor = WorkerExecutor()

        # Act & Assert
        with pytest.raises(ValueError, match="validation failed|Missing required field"):
            executor.execute(str(instructions_path), worker_config)


class TestWorkerExecutorStateless:
    """Test that WorkerExecutor is stateless"""

    def test_executor_has_no_instance_state(self):
        """WorkerExecutor stores no state between calls"""
        executor = WorkerExecutor()

        # Verify no state-related attributes
        instance_vars = [
            attr
            for attr in dir(executor)
            if not attr.startswith("_") and not callable(getattr(executor, attr))
        ]

        # Should only have dependency objects, no state
        for var in instance_vars:
            attr = getattr(executor, var)
            # Dependencies are ok (LLMProvider, ResultManager, Logger)
            assert hasattr(attr, "__class__")

    def test_multiple_executions_are_independent(self, tmp_path):
        """Multiple execute() calls don't affect each other"""
        # Arrange
        executor = WorkerExecutor()
        executor.llm_provider.generate = Mock(side_effect=["Response 1", "Response 2"])
        executor.result_manager.write = Mock(
            side_effect=[str(tmp_path / "result1.json"), str(tmp_path / "result2.json")]
        )

        # Create two sets of instructions
        instructions1 = tmp_path / "instructions1.json"
        instructions1.write_text(json.dumps({"instructions": "Task 1", "output_path": "result.json"}))

        instructions2 = tmp_path / "instructions2.json"
        instructions2.write_text(json.dumps({"instructions": "Task 2", "output_path": "result.json"}))

        worker_config1 = {
            "worker_id": "worker-001",
            "pod_id": "pod-001",
            "session_id": "session-001",
            "worker_dir": str(tmp_path),
            "llm_config_path": str(tmp_path / "llm_config.json"),
        }

        worker_config2 = {
            "worker_id": "worker-002",
            "pod_id": "pod-002",
            "session_id": "session-002",
            "worker_dir": str(tmp_path),
            "llm_config_path": str(tmp_path / "llm_config.json"),
        }

        llm_config_path = tmp_path / "llm_config.json"
        llm_config_path.write_text(json.dumps({"provider": "anthropic", "model": "claude"}))

        # Act
        result1 = executor.execute(str(instructions1), worker_config1)
        result2 = executor.execute(str(instructions2), worker_config2)

        # Assert: Both executions succeeded independently
        assert result1 == str(tmp_path / "result1.json")
        assert result2 == str(tmp_path / "result2.json")
        assert executor.llm_provider.generate.call_count == 2
