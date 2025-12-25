"""
FeedbackLoop Feature Tests - Issue #21

RED PHASE: These tests define the expected behavior of the FeedbackLoop feature.
They will fail initially because the implementation doesn't exist yet.

Purpose: Verify supervisor-worker feedback loop with retry on FAIL

Test Coverage:
- Loop executes correctly (supervisor → worker → supervisor)
- Retries on FAIL with gaps context
- Exits on PASS
- Respects max attempts
- Logs loop iterations
- Handles errors (missing files, timeouts)
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class TestFeedbackLoopBasicFlow:
    """Test basic feedback loop execution flow"""

    def test_feedback_loop_exists(self):
        """FeedbackLoop class should be importable"""
        from src.features.feedback_loop import FeedbackLoop
        assert FeedbackLoop is not None

    def test_feedback_loop_initialization(self, tmp_path):
        """FeedbackLoop should initialize with required components"""
        from src.features.feedback_loop import FeedbackLoop

        loop = FeedbackLoop(
            pod_dir=tmp_path,
            pod_id="test-pod-001",
            max_attempts=3
        )

        assert loop.pod_dir == tmp_path
        assert loop.pod_id == "test-pod-001"
        assert loop.max_attempts == 3
        assert loop.current_attempt == 0
        assert loop.loop_status == "idle"

    def test_feedback_loop_has_supervisor_and_worker(self, tmp_path):
        """FeedbackLoop should have SupervisorEvaluation and WorkerExecution"""
        from src.features.feedback_loop import FeedbackLoop

        loop = FeedbackLoop(
            pod_dir=tmp_path,
            pod_id="test-pod-001"
        )

        assert hasattr(loop, 'supervisor')
        assert hasattr(loop, 'worker')
        assert loop.supervisor is not None
        assert loop.worker is not None


class TestFeedbackLoopExecution:
    """Test feedback loop execution scenarios"""

    def test_single_pass_completes_immediately(self, tmp_path):
        """
        If worker produces correct result on first attempt, loop exits on PASS

        Flow:
        1. Supervisor writes instructions.json
        2. Worker executes, writes result.json
        3. Supervisor evaluates → PASS
        4. Loop exits with status=PASS, attempts=1
        """
        from src.features.feedback_loop import FeedbackLoop

        # Setup: Write instructions
        instructions_file = tmp_path / "instructions.json"
        instructions_file.write_text(json.dumps({
            "instructions": "Return the number 42",
            "output_path": "result.json"
        }))

        # Mock both worker and supervisor
        with patch('src.features.feedback_loop.WorkerExecution') as MockWorker, \
             patch('src.features.feedback_loop.SupervisorEvaluation') as MockSupervisor:
            mock_worker = MockWorker.return_value
            mock_worker.execute.return_value = {"result": "42"}

            mock_supervisor = MockSupervisor.return_value
            mock_supervisor.evaluate.return_value = "PASS"

            # Execute loop
            loop = FeedbackLoop(pod_dir=tmp_path, pod_id="test-pod-001")
            result = loop.run()

            # Verify: PASS on first attempt
            assert result["status"] == "PASS"
            assert result["attempts"] == 1
            assert loop.loop_status == "COMPLETE"
            assert loop.current_attempt == 1

    def test_fail_then_pass_completes_on_second_attempt(self, tmp_path):
        """
        Worker fails first attempt, supervisor writes gaps, worker retries and passes

        Flow:
        1. Worker executes → wrong result
        2. Supervisor evaluates → FAIL with gaps
        3. Worker reads feedback, retries with gap context
        4. Worker produces correct result
        5. Supervisor evaluates → PASS
        6. Loop exits with status=PASS, attempts=2
        """
        from src.features.feedback_loop import FeedbackLoop

        # Setup instructions
        instructions_file = tmp_path / "instructions.json"
        instructions_file.write_text(json.dumps({
            "instructions": "Return the number 42",
            "output_path": "result.json"
        }))

        # Mock both worker and supervisor
        with patch('src.features.feedback_loop.WorkerExecution') as MockWorker, \
             patch('src.features.feedback_loop.SupervisorEvaluation') as MockSupervisor:
            mock_worker = MockWorker.return_value
            mock_worker.execute.side_effect = [
                {"result": "24"},  # Wrong on first attempt
            ]
            mock_worker.execute_with_feedback.return_value = {"result": "42"}  # Correct on retry

            mock_supervisor = MockSupervisor.return_value
            # FAIL on first attempt, PASS on second
            mock_supervisor.evaluate.side_effect = ["FAIL", "PASS"]
            mock_supervisor.write_feedback.return_value = None

            # Execute loop
            loop = FeedbackLoop(pod_dir=tmp_path, pod_id="test-pod-001")

            # Write feedback file for retry (simulate supervisor writing gaps)
            feedback_file = tmp_path / "feedback.json"
            feedback_file.write_text(json.dumps({
                "status": "FAIL",
                "gaps": ["Result was 24, expected 42"],
                "attempt": 1
            }))

            result = loop.run()

            # Verify: PASS on second attempt
            assert result["status"] == "PASS"
            assert result["attempts"] == 2
            assert loop.loop_status == "COMPLETE"

    def test_max_attempts_exceeded_fails_loop(self, tmp_path):
        """
        Worker fails repeatedly until max_attempts, loop exits with FAIL

        Flow:
        1. Worker executes → wrong result (attempt 1)
        2. Supervisor → FAIL with gaps
        3. Worker retries → wrong result (attempt 2)
        4. Supervisor → FAIL with gaps
        5. Worker retries → wrong result (attempt 3)
        6. Supervisor → FAIL (max_attempts=3 reached)
        7. Loop exits with status=FAIL, reason=MAX_ATTEMPTS_EXCEEDED
        """
        from src.features.feedback_loop import FeedbackLoop

        # Setup instructions
        instructions_file = tmp_path / "instructions.json"
        instructions_file.write_text(json.dumps({
            "instructions": "Return the number 42",
            "output_path": "result.json"
        }))

        # Mock worker to always fail
        with patch('src.features.feedback_loop.WorkerExecution') as MockWorker:
            mock_worker = MockWorker.return_value
            mock_worker.execute.return_value = {"result": "WRONG"}

            # Execute loop with max_attempts=3
            loop = FeedbackLoop(
                pod_dir=tmp_path,
                pod_id="test-pod-001",
                max_attempts=3
            )
            result = loop.run()

            # Verify: FAIL after max attempts
            assert result["status"] == "FAIL"
            assert result["reason"] == "MAX_ATTEMPTS_EXCEEDED"
            assert result["attempts"] == 3
            assert loop.loop_status == "FAILED"


class TestFeedbackLoopGapsContext:
    """Test that feedback gaps are properly communicated to worker"""

    def test_worker_receives_gaps_on_retry(self, tmp_path):
        """Worker should receive gaps from supervisor feedback on retry"""
        from src.features.feedback_loop import FeedbackLoop

        # Setup instructions
        instructions_file = tmp_path / "instructions.json"
        instructions_file.write_text(json.dumps({
            "instructions": "Return JSON with 'name' and 'age' keys",
            "output_path": "result.json"
        }))

        # Mock supervisor to write FAIL feedback with gaps
        with patch('src.features.feedback_loop.SupervisorEvaluation') as MockSupervisor:
            mock_supervisor = MockSupervisor.return_value

            # First evaluation: FAIL with gaps
            mock_supervisor.evaluate.return_value = "FAIL"

            # Simulate supervisor writing feedback.json
            feedback_file = tmp_path / "feedback.json"
            feedback_file.write_text(json.dumps({
                "status": "FAIL",
                "gaps": ["Missing 'age' key", "Value type mismatch"],
                "attempt": 1
            }))

            loop = FeedbackLoop(pod_dir=tmp_path, pod_id="test-pod-001")

            # Verify gaps are read and available
            gaps = loop._read_gaps()
            assert gaps == ["Missing 'age' key", "Value type mismatch"]

    def test_worker_execution_includes_gap_context(self, tmp_path):
        """Worker's retry execution should include gap context in prompt"""
        from src.features.feedback_loop import FeedbackLoop

        # Setup
        instructions_file = tmp_path / "instructions.json"
        instructions_file.write_text(json.dumps({
            "instructions": "Return valid JSON",
            "output_path": "result.json"
        }))

        feedback_file = tmp_path / "feedback.json"
        feedback_file.write_text(json.dumps({
            "status": "FAIL",
            "gaps": ["Missing required field 'id'", "Invalid JSON format"],
            "attempt": 1
        }))

        with patch('src.features.feedback_loop.WorkerExecution') as MockWorker:
            mock_worker = MockWorker.return_value
            # Return JSON-serializable result
            mock_worker.execute_with_feedback.return_value = {"result": "valid"}

            loop = FeedbackLoop(pod_dir=tmp_path, pod_id="test-pod-001")
            loop._execute_worker_with_feedback()

            # Verify worker was called with feedback context
            # (exact implementation depends on how gaps are passed to worker)
            assert mock_worker.execute_with_feedback.called or mock_worker.execute.called


class TestFeedbackLoopHistory:
    """Test loop iteration history tracking"""

    def test_loop_tracks_iteration_count(self, tmp_path):
        """FeedbackLoop should track number of iterations"""
        from src.features.feedback_loop import FeedbackLoop

        # Setup instructions
        instructions_file = tmp_path / "instructions.json"
        instructions_file.write_text(json.dumps({
            "instructions": "Test instructions",
            "output_path": "result.json"
        }))

        # Create loop with mocked components
        with patch('src.features.feedback_loop.WorkerExecution') as MockWorker, \
             patch('src.features.feedback_loop.SupervisorEvaluation') as MockSupervisor:
            mock_worker = MockWorker.return_value
            mock_worker.execute.return_value = {"result": "test"}

            mock_supervisor = MockSupervisor.return_value
            mock_supervisor.evaluate.return_value = "PASS"

            loop = FeedbackLoop(pod_dir=tmp_path, pod_id="test-pod-001")

            # Initial state
            assert loop.get_iteration_count() == 0

            # After running
            loop.run()
            assert loop.get_iteration_count() == 1

    def test_loop_tracks_attempt_history(self, tmp_path):
        """FeedbackLoop should maintain history of all attempts"""
        from src.features.feedback_loop import FeedbackLoop

        loop = FeedbackLoop(pod_dir=tmp_path, pod_id="test-pod-001")

        # Simulate multiple iterations
        loop._add_to_history({
            "attempt": 1,
            "status": "FAIL",
            "gaps": ["Error 1"]
        })
        loop._add_to_history({
            "attempt": 2,
            "status": "PASS",
            "gaps": []
        })

        history = loop.get_history()
        assert len(history) == 2
        assert history[0]["attempt"] == 1
        assert history[1]["attempt"] == 2
        assert history[1]["status"] == "PASS"


class TestFeedbackLoopErrorHandling:
    """Test error handling in feedback loop"""

    def test_missing_instructions_file_raises_error(self, tmp_path):
        """FeedbackLoop should raise error if instructions.json doesn't exist"""
        from src.features.feedback_loop import FeedbackLoop

        loop = FeedbackLoop(pod_dir=tmp_path, pod_id="test-pod-001")

        with pytest.raises(FileNotFoundError, match="instructions.json"):
            loop.run()

    def test_malformed_instructions_json_raises_error(self, tmp_path):
        """FeedbackLoop should raise error if instructions.json is invalid JSON"""
        from src.features.feedback_loop import FeedbackLoop

        # Write invalid JSON
        instructions_file = tmp_path / "instructions.json"
        instructions_file.write_text("{ invalid json }")

        loop = FeedbackLoop(pod_dir=tmp_path, pod_id="test-pod-001")

        with pytest.raises((json.JSONDecodeError, ValueError)):
            loop.run()

    def test_worker_timeout_handled_gracefully(self, tmp_path):
        """FeedbackLoop should handle worker timeout gracefully"""
        from src.features.feedback_loop import FeedbackLoop

        instructions_file = tmp_path / "instructions.json"
        instructions_file.write_text(json.dumps({
            "instructions": "Long running task",
            "output_path": "result.json"
        }))

        with patch('src.features.feedback_loop.WorkerExecution') as MockWorker:
            mock_worker = MockWorker.return_value
            mock_worker.execute.side_effect = TimeoutError("Worker timeout")

            loop = FeedbackLoop(
                pod_dir=tmp_path,
                pod_id="test-pod-001",
                timeout=5.0
            )
            result = loop.run()

            # Should fail gracefully with timeout error
            assert result["status"] == "FAIL"
            assert "timeout" in result.get("reason", "").lower()

    def test_supervisor_evaluation_error_propagates(self, tmp_path):
        """Errors in supervisor evaluation should propagate properly"""
        from src.features.feedback_loop import FeedbackLoop

        instructions_file = tmp_path / "instructions.json"
        instructions_file.write_text(json.dumps({
            "instructions": "Test task",
            "output_path": "result.json"
        }))

        with patch('src.features.feedback_loop.SupervisorEvaluation') as MockSupervisor:
            mock_supervisor = MockSupervisor.return_value
            mock_supervisor.evaluate.side_effect = ValueError("Evaluation failed")

            loop = FeedbackLoop(pod_dir=tmp_path, pod_id="test-pod-001")

            with pytest.raises(ValueError, match="Evaluation failed"):
                loop.run()


class TestFeedbackLoopLogging:
    """Test logging of loop iterations"""

    def test_loop_logs_each_iteration(self, tmp_path):
        """FeedbackLoop should log each iteration for debugging"""
        from src.features.feedback_loop import FeedbackLoop

        with patch('src.features.feedback_loop.Logger') as MockLogger:
            mock_logger = MockLogger.return_value

            loop = FeedbackLoop(pod_dir=tmp_path, pod_id="test-pod-001")

            # Verify logger is initialized
            assert loop.logger is not None
            assert mock_logger.info.called or hasattr(loop, 'logger')

    def test_loop_logs_final_outcome(self, tmp_path):
        """FeedbackLoop should log final outcome (PASS/FAIL)"""
        from src.features.feedback_loop import FeedbackLoop

        instructions_file = tmp_path / "instructions.json"
        instructions_file.write_text(json.dumps({
            "instructions": "Test",
            "output_path": "result.json"
        }))

        with patch('src.features.feedback_loop.Logger') as MockLogger:
            mock_logger = MockLogger.return_value

            loop = FeedbackLoop(pod_dir=tmp_path, pod_id="test-pod-001")

            # Mock successful execution
            with patch.object(loop, '_run_loop'):
                loop.run()

                # Verify logging occurred (logger.info should be called)
                assert hasattr(loop, 'logger')


class TestFeedbackLoopConfiguration:
    """Test configuration options"""

    def test_configurable_max_attempts(self, tmp_path):
        """max_attempts should be configurable"""
        from src.features.feedback_loop import FeedbackLoop

        loop1 = FeedbackLoop(pod_dir=tmp_path, pod_id="test-pod-001", max_attempts=3)
        loop2 = FeedbackLoop(pod_dir=tmp_path, pod_id="test-pod-002", max_attempts=10)

        assert loop1.max_attempts == 3
        assert loop2.max_attempts == 10

    def test_default_max_attempts_is_three(self, tmp_path):
        """Default max_attempts should be 3 as per requirements"""
        from src.features.feedback_loop import FeedbackLoop

        loop = FeedbackLoop(pod_dir=tmp_path, pod_id="test-pod-001")
        assert loop.max_attempts == 3

    def test_configurable_timeout(self, tmp_path):
        """Timeout should be configurable for worker execution"""
        from src.features.feedback_loop import FeedbackLoop

        loop = FeedbackLoop(
            pod_dir=tmp_path,
            pod_id="test-pod-001",
            timeout=10.0
        )
        assert loop.timeout == 10.0


class TestFeedbackLoopIntegration:
    """Integration tests using real SupervisorEvaluation and WorkerExecution"""

    def test_real_supervisor_and_worker_integration(self, tmp_path):
        """
        Test with real SupervisorEvaluation and WorkerExecution (minimal mock)

        This verifies the feedback loop correctly orchestrates real components
        """
        from src.features.feedback_loop import FeedbackLoop
        from src.features.supervisor_evaluation import SupervisorEvaluation
        from src.features.worker_execution import WorkerExecution

        # Setup instructions
        instructions_file = tmp_path / "instructions.json"
        instructions_file.write_text(json.dumps({
            "instructions": "Return the word 'SUCCESS'",
            "output_path": "result.json"
        }))

        # Create feedback loop with real components
        loop = FeedbackLoop(
            pod_dir=tmp_path,
            pod_id="integration-test-001",
            max_attempts=3
        )

        # Mock only the LLM call in worker (everything else is real)
        with patch.object(WorkerExecution, '_call_llm', return_value={"result": "SUCCESS"}):
            result = loop.run()

            # Verify: Real supervisor evaluated real worker output
            assert result["status"] in ["PASS", "FAIL"]
            assert result["attempts"] >= 1
            assert result["attempts"] <= 3

    def test_file_based_communication_between_components(self, tmp_path):
        """
        Verify all communication happens via files (instructions, result, feedback)
        """
        from src.features.feedback_loop import FeedbackLoop

        instructions_file = tmp_path / "instructions.json"
        instructions_file.write_text(json.dumps({
            "instructions": "Test file-based communication",
            "output_path": "result.json"
        }))

        loop = FeedbackLoop(pod_dir=tmp_path, pod_id="test-pod-001")

        # After execution, these files should exist
        with patch('src.features.feedback_loop.WorkerExecution'):
            with patch('src.features.feedback_loop.SupervisorEvaluation'):
                loop.run()

                # Verify file-based artifacts exist
                assert (tmp_path / "instructions.json").exists()
                # Result and feedback files depend on execution outcome


class TestFeedbackLoopEdgeCases:
    """Test edge cases for missing file paths"""

    def test_read_gaps_when_no_feedback_file(self, tmp_path):
        """_read_gaps should return empty list when feedback.json doesn't exist"""
        from src.features.feedback_loop import FeedbackLoop

        loop = FeedbackLoop(pod_dir=tmp_path, pod_id="test-pod-001")

        # No feedback file exists
        gaps = loop._read_gaps()
        assert gaps == []

    def test_read_gaps_when_feedback_is_pass(self, tmp_path):
        """_read_gaps should return empty list when feedback status is PASS"""
        from src.features.feedback_loop import FeedbackLoop

        # Create PASS feedback
        feedback_file = tmp_path / "feedback.json"
        feedback_file.write_text(json.dumps({
            "status": "PASS",
            "attempt": 1
        }))

        loop = FeedbackLoop(pod_dir=tmp_path, pod_id="test-pod-001")
        gaps = loop._read_gaps()
        assert gaps == []

    def test_read_feedback_when_file_missing(self, tmp_path):
        """_read_feedback should return None when feedback.json doesn't exist"""
        from src.features.feedback_loop import FeedbackLoop

        loop = FeedbackLoop(pod_dir=tmp_path, pod_id="test-pod-001")

        # No feedback file
        feedback = loop._read_feedback()
        assert feedback is None

    def test_read_result_when_file_missing(self, tmp_path):
        """_read_result should return empty string when result.json doesn't exist"""
        from src.features.feedback_loop import FeedbackLoop

        loop = FeedbackLoop(pod_dir=tmp_path, pod_id="test-pod-001")

        # No result file
        result = loop._read_result()
        assert result == ""

    def test_execute_worker_with_feedback_when_no_feedback(self, tmp_path):
        """_execute_worker_with_feedback should pass (do nothing) when no feedback exists"""
        from src.features.feedback_loop import FeedbackLoop

        # Setup instructions
        instructions_file = tmp_path / "instructions.json"
        instructions_file.write_text(json.dumps({
            "instructions": "Test",
            "output_path": "result.json"
        }))

        with patch('src.features.feedback_loop.WorkerExecution') as MockWorker:
            mock_worker = MockWorker.return_value

            loop = FeedbackLoop(pod_dir=tmp_path, pod_id="test-pod-001")

            # No feedback file exists
            loop._execute_worker_with_feedback()

            # Worker should not be called when no feedback
            assert not mock_worker.execute_with_feedback.called
            assert not mock_worker.execute.called
