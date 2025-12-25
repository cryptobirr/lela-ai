"""
Test suite for WorkerExecution Feature

Purpose: Verify complete worker execution logic (read, execute, write)

Test Coverage:
- Happy path: Normal execution flow with PASS feedback
- Edge cases: Multiple retries, different LLM providers, missing files
- Error handling: Invalid JSON, execution failures, feedback loops
- Integration: File-based communication (instructions.json, result.json, feedback.json)

Requirements tested: Issue #20 - Feature: WorkerExecution
Dependencies: WorkerExecutor (#17), ResultManager (#13)
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class TestWorkerExecutionReadInstructions:
    """Test reading instructions from disk."""

    def test_reads_instructions_from_json_file(self, tmp_path):
        """Worker reads instructions.json and parses content correctly."""
        # Arrange
        instructions_file = tmp_path / "instructions.json"
        instructions_data = {
            "instructions": "Analyze the data and provide summary",
            "output_path": "result.json"
        }
        instructions_file.write_text(json.dumps(instructions_data))

        # Act
        from src.features.worker_execution import WorkerExecution
        worker = WorkerExecution(working_dir=tmp_path)
        instructions = worker.read_instructions()

        # Assert
        assert instructions["instructions"] == "Analyze the data and provide summary"
        assert instructions["output_path"] == "result.json"

    def test_handles_missing_instructions_file(self, tmp_path):
        """Worker handles case when instructions.json doesn't exist."""
        # Arrange
        from src.features.worker_execution import WorkerExecution
        worker = WorkerExecution(working_dir=tmp_path)

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            worker.read_instructions()

    def test_handles_invalid_json_in_instructions(self, tmp_path):
        """Worker handles corrupted/invalid JSON in instructions.json."""
        # Arrange
        instructions_file = tmp_path / "instructions.json"
        instructions_file.write_text("{ invalid json content")

        from src.features.worker_execution import WorkerExecution
        worker = WorkerExecution(working_dir=tmp_path)

        # Act & Assert
        with pytest.raises(json.JSONDecodeError):
            worker.read_instructions()

    def test_validates_required_fields_in_instructions(self, tmp_path):
        """Worker validates that instructions.json has required fields."""
        # Arrange
        instructions_file = tmp_path / "instructions.json"
        instructions_data = {"output_path": "result.json"}  # Missing 'instructions'
        instructions_file.write_text(json.dumps(instructions_data))

        from src.features.worker_execution import WorkerExecution
        worker = WorkerExecution(working_dir=tmp_path)

        # Act & Assert
        with pytest.raises(ValueError, match="Missing required field: instructions"):
            worker.read_instructions()


class TestWorkerExecutionExecuteWithLLM:
    """Test execution using configured LLM."""

    def test_executes_with_configured_llm_provider(self, tmp_path):
        """Worker executes instructions using the configured LLM provider."""
        # Arrange
        instructions = {
            "instructions": "Summarize this text",
            "output_path": "result.json"
        }

        from src.features.worker_execution import WorkerExecution
        worker = WorkerExecution(working_dir=tmp_path, llm_provider="openai")

        # Act
        result = worker.execute(instructions)

        # Assert
        assert result is not None
        assert isinstance(result, dict)
        assert "result" in result

    def test_supports_multiple_llm_providers(self, tmp_path):
        """Worker supports different LLM providers (OpenAI, Anthropic, etc.)."""
        # Arrange
        instructions = {"instructions": "Test task", "output_path": "result.json"}

        from src.features.worker_execution import WorkerExecution

        # Act & Assert - OpenAI
        worker_openai = WorkerExecution(working_dir=tmp_path, llm_provider="openai")
        result_openai = worker_openai.execute(instructions)
        assert result_openai is not None

        # Act & Assert - Anthropic
        worker_anthropic = WorkerExecution(working_dir=tmp_path, llm_provider="anthropic")
        result_anthropic = worker_anthropic.execute(instructions)
        assert result_anthropic is not None

    def test_handles_llm_execution_failure(self, tmp_path):
        """Worker handles LLM execution failures gracefully."""
        # Arrange
        instructions = {"instructions": "Task", "output_path": "result.json"}

        from src.features.worker_execution import WorkerExecution
        worker = WorkerExecution(working_dir=tmp_path, llm_provider="mock")

        # Mock LLM failure
        with patch.object(worker, '_call_llm', side_effect=Exception("LLM API error")):
            # Act & Assert
            with pytest.raises(Exception, match="LLM API error"):
                worker.execute(instructions)

    def test_passes_instructions_to_llm_correctly(self, tmp_path):
        """Worker passes instruction text to LLM without modification."""
        # Arrange
        instructions = {
            "instructions": "Specific detailed instructions here",
            "output_path": "result.json"
        }

        from src.features.worker_execution import WorkerExecution
        worker = WorkerExecution(working_dir=tmp_path, llm_provider="mock")

        # Mock LLM call
        mock_llm = Mock(return_value={"result": "LLM response"})
        worker._call_llm = mock_llm

        # Act
        worker.execute(instructions)

        # Assert
        mock_llm.assert_called_once_with("Specific detailed instructions here")


class TestWorkerExecutionWriteResult:
    """Test writing result to disk."""

    def test_writes_result_to_json_file(self, tmp_path):
        """Worker writes execution result to result.json."""
        # Arrange
        result_data = {"result": "Analysis complete", "metadata": {"tokens": 150}}

        from src.features.worker_execution import WorkerExecution
        worker = WorkerExecution(working_dir=tmp_path)

        # Act
        worker.write_result(result_data, output_path="result.json")

        # Assert
        result_file = tmp_path / "result.json"
        assert result_file.exists()
        written_data = json.loads(result_file.read_text())
        assert written_data["result"] == "Analysis complete"
        assert written_data["metadata"]["tokens"] == 150

    def test_writes_to_custom_output_path(self, tmp_path):
        """Worker writes result to custom path specified in instructions."""
        # Arrange
        result_data = {"result": "Custom output"}

        from src.features.worker_execution import WorkerExecution
        worker = WorkerExecution(working_dir=tmp_path)

        # Act
        worker.write_result(result_data, output_path="custom/path/output.json")

        # Assert
        result_file = tmp_path / "custom" / "path" / "output.json"
        assert result_file.exists()
        written_data = json.loads(result_file.read_text())
        assert written_data["result"] == "Custom output"

    def test_creates_parent_directories_if_needed(self, tmp_path):
        """Worker creates parent directories when writing result."""
        # Arrange
        result_data = {"result": "Test"}

        from src.features.worker_execution import WorkerExecution
        worker = WorkerExecution(working_dir=tmp_path)

        # Act
        worker.write_result(result_data, output_path="deep/nested/path/result.json")

        # Assert
        assert (tmp_path / "deep" / "nested" / "path" / "result.json").exists()

    def test_handles_write_permission_errors(self, tmp_path):
        """Worker handles file write permission errors."""
        # Arrange
        result_data = {"result": "Test"}

        from src.features.worker_execution import WorkerExecution
        worker = WorkerExecution(working_dir=tmp_path)

        # Make directory read-only
        read_only_dir = tmp_path / "readonly"
        read_only_dir.mkdir()
        read_only_dir.chmod(0o444)

        # Act & Assert
        with pytest.raises(PermissionError):
            worker.write_result(result_data, output_path="readonly/result.json")


class TestWorkerExecutionFeedbackHandling:
    """Test handling feedback from supervisor."""

    def test_reads_feedback_json_file(self, tmp_path):
        """Worker reads feedback.json when available."""
        # Arrange
        feedback_file = tmp_path / "feedback.json"
        feedback_data = {
            "status": "FAIL",
            "gaps": ["Missing field X", "Invalid format for Y"],
            "attempt": 1
        }
        feedback_file.write_text(json.dumps(feedback_data))

        from src.features.worker_execution import WorkerExecution
        worker = WorkerExecution(working_dir=tmp_path)

        # Act
        feedback = worker.read_feedback()

        # Assert
        assert feedback["status"] == "FAIL"
        assert len(feedback["gaps"]) == 2
        assert feedback["attempt"] == 1

    def test_handles_missing_feedback_file(self, tmp_path):
        """Worker handles case when feedback.json doesn't exist yet."""
        # Arrange
        from src.features.worker_execution import WorkerExecution
        worker = WorkerExecution(working_dir=tmp_path)

        # Act
        feedback = worker.read_feedback()

        # Assert
        assert feedback is None

    def test_retries_on_fail_feedback(self, tmp_path):
        """Worker retries execution when receiving FAIL feedback."""
        # Arrange
        instructions_file = tmp_path / "instructions.json"
        instructions_data = {
            "instructions": "Original task",
            "output_path": "result.json"
        }
        instructions_file.write_text(json.dumps(instructions_data))

        feedback_file = tmp_path / "feedback.json"
        feedback_data = {
            "status": "FAIL",
            "gaps": ["Missing validation"],
            "attempt": 1
        }
        feedback_file.write_text(json.dumps(feedback_data))

        from src.features.worker_execution import WorkerExecution
        worker = WorkerExecution(working_dir=tmp_path)

        # Mock LLM
        mock_llm = Mock(return_value={"result": "Retry result"})
        worker._call_llm = mock_llm

        # Act - run() with existing FAIL feedback should retry
        worker.run()

        # Assert - Should call LLM once for retry (feedback already exists from previous attempt)
        assert mock_llm.call_count == 1  # Retry only (original execution already happened)

    def test_includes_gaps_in_retry_context(self, tmp_path):
        """Worker includes gap information when retrying after FAIL."""
        # Arrange
        feedback_data = {
            "status": "FAIL",
            "gaps": ["Missing error handling", "Invalid output format"],
            "attempt": 1
        }
        feedback_file = tmp_path / "feedback.json"
        feedback_file.write_text(json.dumps(feedback_data))

        instructions = {
            "instructions": "Process data",
            "output_path": "result.json"
        }

        from src.features.worker_execution import WorkerExecution
        worker = WorkerExecution(working_dir=tmp_path)

        # Mock LLM
        mock_llm = Mock(return_value={"result": "Fixed result"})
        worker._call_llm = mock_llm

        # Act
        worker.execute_with_feedback(instructions, feedback_data)

        # Assert - LLM call should include gap context
        call_args = mock_llm.call_args[0][0]
        assert "Missing error handling" in call_args
        assert "Invalid output format" in call_args

    def test_completes_on_pass_feedback(self, tmp_path):
        """Worker marks execution complete when receiving PASS feedback."""
        # Arrange
        feedback_file = tmp_path / "feedback.json"
        feedback_data = {
            "status": "PASS",
            "result": "Execution successful",
            "attempts": 2
        }
        feedback_file.write_text(json.dumps(feedback_data))

        from src.features.worker_execution import WorkerExecution
        worker = WorkerExecution(working_dir=tmp_path)

        # Act
        status = worker.check_completion()

        # Assert
        assert status == "COMPLETE"

    def test_limits_retry_attempts(self, tmp_path):
        """Worker limits number of retry attempts to prevent infinite loops."""
        # Arrange
        from src.features.worker_execution import WorkerExecution
        worker = WorkerExecution(working_dir=tmp_path, max_retries=3)

        # Simulate multiple FAIL feedbacks
        for attempt in range(5):
            feedback_data = {
                "status": "FAIL",
                "gaps": [f"Issue {attempt}"],
                "attempt": attempt
            }
            feedback_file = tmp_path / "feedback.json"
            feedback_file.write_text(json.dumps(feedback_data))

            # Act
            if attempt < 3:
                worker.should_retry()
            else:
                # Assert - Should stop retrying after max_retries
                assert not worker.should_retry()


class TestWorkerExecutionPolling:
    """Test polling for instructions."""

    def test_polls_for_instructions_json(self, tmp_path):
        """Worker polls working directory for instructions.json."""
        # Arrange
        from src.features.worker_execution import WorkerExecution
        worker = WorkerExecution(working_dir=tmp_path, poll_interval=0.1)

        # Act
        has_instructions = worker.check_for_instructions()

        # Assert
        assert has_instructions is False

        # Create instructions file
        instructions_file = tmp_path / "instructions.json"
        instructions_file.write_text(json.dumps({
            "instructions": "Task",
            "output_path": "result.json"
        }))

        # Act again
        has_instructions = worker.check_for_instructions()

        # Assert
        assert has_instructions is True

    def test_waits_when_no_instructions_available(self, tmp_path):
        """Worker waits when instructions.json is not available yet."""
        # Arrange
        from src.features.worker_execution import WorkerExecution
        worker = WorkerExecution(working_dir=tmp_path, poll_interval=0.1)

        # Mock sleep to avoid actual waiting
        with patch('time.sleep') as mock_sleep:
            # Act
            worker.wait_for_instructions(timeout=1.0)

            # Assert
            assert mock_sleep.called


class TestWorkerExecutionState:
    """Test execution state management."""

    def test_tracks_current_execution_status(self, tmp_path):
        """Worker tracks current execution status (idle, running, complete)."""
        # Arrange
        from src.features.worker_execution import WorkerExecution
        worker = WorkerExecution(working_dir=tmp_path)

        # Act & Assert - Initial state
        assert worker.get_status() == "idle"

        # Start execution
        worker.set_status("running")
        assert worker.get_status() == "running"

        # Complete execution
        worker.set_status("complete")
        assert worker.get_status() == "complete"

    def test_maintains_execution_history(self, tmp_path):
        """Worker maintains history of execution attempts."""
        # Arrange
        from src.features.worker_execution import WorkerExecution
        worker = WorkerExecution(working_dir=tmp_path)

        # Act
        worker.add_to_history({
            "attempt": 1,
            "status": "FAIL",
            "timestamp": "2025-12-24T16:00:00Z"
        })
        worker.add_to_history({
            "attempt": 2,
            "status": "PASS",
            "timestamp": "2025-12-24T16:05:00Z"
        })

        # Assert
        history = worker.get_history()
        assert len(history) == 2
        assert history[0]["status"] == "FAIL"
        assert history[1]["status"] == "PASS"

    def test_clears_state_on_new_instructions(self, tmp_path):
        """Worker clears previous execution state when new instructions arrive."""
        # Arrange
        from src.features.worker_execution import WorkerExecution
        worker = WorkerExecution(working_dir=tmp_path)

        # Set up previous state
        worker.set_status("complete")
        worker.add_to_history({"attempt": 1, "status": "PASS"})

        # Act
        worker.reset()

        # Assert
        assert worker.get_status() == "idle"
        assert len(worker.get_history()) == 0


class TestWorkerExecutionMultipleWorkers:
    """Test support for multiple workers per pod."""

    def test_supports_multiple_worker_instances(self, tmp_path):
        """Pod can run multiple worker instances simultaneously."""
        # Arrange
        from src.features.worker_execution import WorkerExecution

        # Create separate working directories for each worker
        worker1_dir = tmp_path / "worker1"
        worker2_dir = tmp_path / "worker2"
        worker1_dir.mkdir()
        worker2_dir.mkdir()

        # Act
        worker1 = WorkerExecution(working_dir=worker1_dir, worker_id="worker-1")
        worker2 = WorkerExecution(working_dir=worker2_dir, worker_id="worker-2")

        # Assert
        assert worker1.worker_id == "worker-1"
        assert worker2.worker_id == "worker-2"
        assert worker1.working_dir != worker2.working_dir

    def test_workers_operate_independently(self, tmp_path):
        """Multiple workers execute independently without interfering."""
        # Arrange
        from src.features.worker_execution import WorkerExecution

        worker1_dir = tmp_path / "worker1"
        worker2_dir = tmp_path / "worker2"
        worker1_dir.mkdir()
        worker2_dir.mkdir()

        # Create different instructions for each worker
        (worker1_dir / "instructions.json").write_text(json.dumps({
            "instructions": "Task 1",
            "output_path": "result.json"
        }))
        (worker2_dir / "instructions.json").write_text(json.dumps({
            "instructions": "Task 2",
            "output_path": "result.json"
        }))

        worker1 = WorkerExecution(working_dir=worker1_dir, worker_id="worker-1")
        worker2 = WorkerExecution(working_dir=worker2_dir, worker_id="worker-2")

        # Mock LLM
        mock_llm = Mock(return_value={"result": "Response"})
        worker1._call_llm = mock_llm
        worker2._call_llm = mock_llm

        # Act
        worker1.run()
        worker2.run()

        # Assert - Each worker processed its own instructions
        result1 = json.loads((worker1_dir / "result.json").read_text())
        result2 = json.loads((worker2_dir / "result.json").read_text())
        assert result1 is not None
        assert result2 is not None


class TestWorkerExecutionIntegration:
    """Integration tests for complete worker execution flow."""

    def test_complete_execution_flow_with_pass(self, tmp_path):
        """Test complete flow: read instructions → execute → write result → receive PASS."""
        # Arrange
        instructions_file = tmp_path / "instructions.json"
        instructions_file.write_text(json.dumps({
            "instructions": "Analyze data",
            "output_path": "result.json"
        }))

        from src.features.worker_execution import WorkerExecution
        worker = WorkerExecution(working_dir=tmp_path)

        # Mock LLM
        mock_llm = Mock(return_value={"result": "Analysis complete"})
        worker._call_llm = mock_llm

        # Act - Execute
        worker.run()

        # Simulate supervisor feedback
        feedback_file = tmp_path / "feedback.json"
        feedback_file.write_text(json.dumps({
            "status": "PASS",
            "result": "Good work",
            "attempts": 1
        }))

        # Assert
        result_file = tmp_path / "result.json"
        assert result_file.exists()
        status = worker.check_completion()
        assert status == "COMPLETE"

    def test_complete_execution_flow_with_retry(self, tmp_path):
        """Test complete flow with FAIL feedback and successful retry."""
        # Arrange
        instructions_file = tmp_path / "instructions.json"
        instructions_file.write_text(json.dumps({
            "instructions": "Process request",
            "output_path": "result.json"
        }))

        from src.features.worker_execution import WorkerExecution
        worker = WorkerExecution(working_dir=tmp_path)

        # Mock LLM - first call fails, second succeeds
        mock_responses = [
            {"result": "Incomplete result"},
            {"result": "Complete result with all fields"}
        ]
        mock_llm = Mock(side_effect=mock_responses)
        worker._call_llm = mock_llm

        # Act - First execution
        worker.run()

        # Simulate FAIL feedback
        feedback_file = tmp_path / "feedback.json"
        feedback_file.write_text(json.dumps({
            "status": "FAIL",
            "gaps": ["Missing required fields"],
            "attempt": 1
        }))

        # Act - Retry
        worker.run()

        # Simulate PASS feedback
        feedback_file.write_text(json.dumps({
            "status": "PASS",
            "result": "All requirements met",
            "attempts": 2
        }))

        # Assert
        assert mock_llm.call_count == 2
        status = worker.check_completion()
        assert status == "COMPLETE"
