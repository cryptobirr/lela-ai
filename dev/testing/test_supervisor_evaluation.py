"""
Test suite for SupervisorEvaluation Feature

Purpose: Verify complete supervisor evaluation logic (binary PASS/FAIL)

Test Coverage:
- Happy path: Successful evaluation (PASS case)
- Happy path: Failed evaluation (FAIL case with gaps)
- Edge cases: Empty results, malformed instructions, missing files
- Error handling: File I/O errors, validation failures
- State tracking: Attempt count, evaluation history

Requirements tested: Issue #19 - Feature: SupervisorEvaluation
Composition: RequirementComparator (#16), FeedbackManager (#14)
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from src.features.supervisor_evaluation import SupervisorEvaluation


class TestSupervisorEvaluationPassCase:
    """Test successful evaluation (PASS) scenarios."""

    def test_evaluate_pass_writes_pass_feedback(self, tmp_path):
        """
        When result meets requirements exactly, write PASS feedback.

        Acceptance: Evaluates correctly (PASS when requirements met)
        """
        # Arrange
        pod_dir = tmp_path / "pod-001"
        pod_dir.mkdir()

        # Create instructions.json
        instructions_file = pod_dir / "instructions.json"
        instructions_data = {
            "instructions": "Calculate 2+2 and return PASS if correct",
            "output_path": "result.json",
        }
        instructions_file.write_text(json.dumps(instructions_data))

        # Create result.json with PASS
        result_file = pod_dir / "result.json"
        result_data = {"result": "PASS"}
        result_file.write_text(json.dumps(result_data))

        supervisor = SupervisorEvaluation()

        # Act
        status = supervisor.evaluate(pod_dir, pod_id="pod-001")

        # Assert
        assert status == "PASS"

        # Verify feedback.json was written with PASS
        feedback_file = pod_dir / "feedback.json"
        assert feedback_file.exists()

        feedback_data = json.loads(feedback_file.read_text())
        assert feedback_data["status"] == "PASS"
        assert feedback_data["result"] == "PASS"
        assert feedback_data["attempts"] == 1
        assert feedback_data["pod_id"] == "pod-001"
        assert "timestamp" in feedback_data

    def test_evaluate_pass_increments_attempt_count_after_retries(self, tmp_path):
        """
        When evaluation passes after multiple attempts, attempt count reflects total tries.

        Acceptance: Tracks attempt count correctly
        """
        # Arrange
        pod_dir = tmp_path / "pod-001"
        pod_dir.mkdir()

        instructions_file = pod_dir / "instructions.json"
        instructions_data = {"instructions": "Do something", "output_path": "result.json"}
        instructions_file.write_text(json.dumps(instructions_data))

        result_file = pod_dir / "result.json"
        result_data = {"result": "PASS"}
        result_file.write_text(json.dumps(result_data))

        # Simulate previous failed attempt by setting current_attempt=2
        supervisor = SupervisorEvaluation(current_attempt=2)

        # Act
        status = supervisor.evaluate(pod_dir, pod_id="pod-001")

        # Assert
        assert status == "PASS"

        feedback_file = pod_dir / "feedback.json"
        feedback_data = json.loads(feedback_file.read_text())
        assert feedback_data["attempts"] == 2  # Reflects all attempts

    def test_evaluate_pass_logs_evaluation_details(self, tmp_path):
        """
        When evaluation passes, log evaluation details for debugging.

        Acceptance: Logs evaluation details
        """
        # Arrange
        pod_dir = tmp_path / "pod-001"
        pod_dir.mkdir()

        instructions_file = pod_dir / "instructions.json"
        instructions_data = {"instructions": "Test task", "output_path": "result.json"}
        instructions_file.write_text(json.dumps(instructions_data))

        result_file = pod_dir / "result.json"
        result_data = {"result": "PASS"}
        result_file.write_text(json.dumps(result_data))

        supervisor = SupervisorEvaluation()

        # Act & Assert - verify logging happens
        with patch("src.features.supervisor_evaluation.Logger") as mock_logger_class:
            mock_logger = Mock()
            mock_logger_class.return_value = mock_logger

            supervisor_with_mock = SupervisorEvaluation()
            supervisor_with_mock.logger = mock_logger

            status = supervisor_with_mock.evaluate(pod_dir, pod_id="pod-001")

            # Verify logger.info was called with evaluation details
            mock_logger.info.assert_called()
            call_args = mock_logger.info.call_args
            assert "PASS" in str(call_args)


class TestSupervisorEvaluationFailCase:
    """Test failed evaluation (FAIL) scenarios."""

    def test_evaluate_fail_writes_fail_feedback_with_gaps(self, tmp_path):
        """
        When result doesn't meet requirements, write FAIL feedback with specific gaps.

        Acceptance: Evaluates correctly (FAIL when requirements missing)
        """
        # Arrange
        pod_dir = tmp_path / "pod-001"
        pod_dir.mkdir()

        instructions_file = pod_dir / "instructions.json"
        instructions_data = {
            "instructions": "Calculate 2+2 and return PASS if correct",
            "output_path": "result.json",
        }
        instructions_file.write_text(json.dumps(instructions_data))

        # Result is wrong (not PASS)
        result_file = pod_dir / "result.json"
        result_data = {"result": "5"}
        result_file.write_text(json.dumps(result_data))

        supervisor = SupervisorEvaluation()

        # Act
        status = supervisor.evaluate(pod_dir, pod_id="pod-001")

        # Assert
        assert status == "FAIL"

        # Verify feedback.json was written with FAIL and gaps
        feedback_file = pod_dir / "feedback.json"
        assert feedback_file.exists()

        feedback_data = json.loads(feedback_file.read_text())
        assert feedback_data["status"] == "FAIL"
        assert "gaps" in feedback_data
        assert len(feedback_data["gaps"]) > 0
        assert feedback_data["attempt"] == 1
        assert feedback_data["pod_id"] == "pod-001"

    def test_evaluate_fail_increments_attempt_count(self, tmp_path):
        """
        When evaluation fails, increment attempt count for retry.

        Acceptance: Tracks attempt count correctly
        """
        # Arrange
        pod_dir = tmp_path / "pod-001"
        pod_dir.mkdir()

        instructions_file = pod_dir / "instructions.json"
        instructions_data = {"instructions": "Do task", "output_path": "result.json"}
        instructions_file.write_text(json.dumps(instructions_data))

        result_file = pod_dir / "result.json"
        result_data = {"result": "wrong"}
        result_file.write_text(json.dumps(result_data))

        supervisor = SupervisorEvaluation(current_attempt=1)

        # Act
        status = supervisor.evaluate(pod_dir, pod_id="pod-001")

        # Assert
        assert status == "FAIL"

        feedback_file = pod_dir / "feedback.json"
        feedback_data = json.loads(feedback_file.read_text())
        assert feedback_data["attempt"] == 2  # Incremented from 1 to 2

    def test_evaluate_fail_includes_specific_gaps(self, tmp_path):
        """
        FAIL feedback must include specific, actionable gap descriptions.

        Acceptance: Writes correct feedback files with specific gaps
        """
        # Arrange
        pod_dir = tmp_path / "pod-001"
        pod_dir.mkdir()

        instructions_file = pod_dir / "instructions.json"
        instructions_data = {
            "instructions": "Return JSON with fields: name, age, email",
            "output_path": "result.json",
        }
        instructions_file.write_text(json.dumps(instructions_data))

        # Result missing required fields
        result_file = pod_dir / "result.json"
        result_data = {"result": '{"name": "Alice"}'}
        result_file.write_text(json.dumps(result_data))

        supervisor = SupervisorEvaluation()

        # Act
        status = supervisor.evaluate(pod_dir, pod_id="pod-001")

        # Assert
        assert status == "FAIL"

        feedback_file = pod_dir / "feedback.json"
        feedback_data = json.loads(feedback_file.read_text())
        assert "gaps" in feedback_data
        # Gaps should mention missing fields
        gaps_str = " ".join(feedback_data["gaps"])
        assert any(
            keyword in gaps_str.lower() for keyword in ["missing", "incomplete", "incorrect"]
        )


class TestSupervisorEvaluationEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_evaluate_empty_result_returns_fail(self, tmp_path):
        """
        When result is empty string, evaluation fails with appropriate gap.

        Acceptance: Handles edge cases (empty result)
        """
        # Arrange
        pod_dir = tmp_path / "pod-001"
        pod_dir.mkdir()

        instructions_file = pod_dir / "instructions.json"
        instructions_data = {"instructions": "Complete task", "output_path": "result.json"}
        instructions_file.write_text(json.dumps(instructions_data))

        result_file = pod_dir / "result.json"
        result_data = {"result": ""}
        result_file.write_text(json.dumps(result_data))

        supervisor = SupervisorEvaluation()

        # Act
        status = supervisor.evaluate(pod_dir, pod_id="pod-001")

        # Assert
        assert status == "FAIL"

        feedback_file = pod_dir / "feedback.json"
        feedback_data = json.loads(feedback_file.read_text())
        assert "No result provided" in str(feedback_data["gaps"])

    def test_evaluate_malformed_instructions_raises_error(self, tmp_path):
        """
        When instructions.json is malformed, raise clear error.

        Acceptance: Handles edge cases (malformed instructions)
        """
        # Arrange
        pod_dir = tmp_path / "pod-001"
        pod_dir.mkdir()

        # Write invalid JSON
        instructions_file = pod_dir / "instructions.json"
        instructions_file.write_text("{invalid json")

        supervisor = SupervisorEvaluation()

        # Act & Assert
        with pytest.raises((ValueError, json.JSONDecodeError)):
            supervisor.evaluate(pod_dir, pod_id="pod-001")

    def test_evaluate_missing_result_file_returns_fail(self, tmp_path):
        """
        When result.json doesn't exist, evaluation fails gracefully.

        Acceptance: Handles edge cases (missing files)
        """
        # Arrange
        pod_dir = tmp_path / "pod-001"
        pod_dir.mkdir()

        instructions_file = pod_dir / "instructions.json"
        instructions_data = {"instructions": "Do task", "output_path": "result.json"}
        instructions_file.write_text(json.dumps(instructions_data))

        # No result.json file created

        supervisor = SupervisorEvaluation()

        # Act
        status = supervisor.evaluate(pod_dir, pod_id="pod-001")

        # Assert
        assert status == "FAIL"

        feedback_file = pod_dir / "feedback.json"
        feedback_data = json.loads(feedback_file.read_text())
        assert "No result provided" in str(feedback_data["gaps"])

    def test_evaluate_missing_instructions_file_raises_error(self, tmp_path):
        """
        When instructions.json doesn't exist, raise clear error.

        Acceptance: Handles edge cases (missing files)
        """
        # Arrange
        pod_dir = tmp_path / "pod-001"
        pod_dir.mkdir()

        # No instructions.json file

        supervisor = SupervisorEvaluation()

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            supervisor.evaluate(pod_dir, pod_id="pod-001")


class TestSupervisorEvaluationStateTracking:
    """Test evaluation state and history tracking."""

    def test_evaluation_history_tracks_all_evaluations(self, tmp_path):
        """
        Supervisor maintains history of all evaluations for debugging.

        Acceptance: Maintains evaluation history (for debugging)
        """
        # Arrange
        pod_dir = tmp_path / "pod-001"
        pod_dir.mkdir()

        instructions_file = pod_dir / "instructions.json"
        instructions_data = {"instructions": "Task", "output_path": "result.json"}
        instructions_file.write_text(json.dumps(instructions_data))

        result_file = pod_dir / "result.json"
        result_data = {"result": "PASS"}
        result_file.write_text(json.dumps(result_data))

        supervisor = SupervisorEvaluation()

        # Act
        supervisor.evaluate(pod_dir, pod_id="pod-001")

        # Assert - supervisor should maintain history
        assert hasattr(supervisor, "evaluation_history")
        assert len(supervisor.evaluation_history) == 1

        history_entry = supervisor.evaluation_history[0]
        assert history_entry["status"] == "PASS"
        assert history_entry["pod_id"] == "pod-001"
        assert "timestamp" in history_entry

    def test_multiple_evaluations_append_to_history(self, tmp_path):
        """
        Multiple evaluations accumulate in history for audit trail.

        Acceptance: Maintains evaluation history (for debugging)
        """
        # Arrange
        supervisor = SupervisorEvaluation()

        # First evaluation (FAIL)
        pod_dir_1 = tmp_path / "pod-001"
        pod_dir_1.mkdir()
        instructions_file_1 = pod_dir_1 / "instructions.json"
        instructions_file_1.write_text(json.dumps({"instructions": "Task 1", "output_path": "result.json"}))
        result_file_1 = pod_dir_1 / "result.json"
        result_file_1.write_text(json.dumps({"result": "wrong"}))

        supervisor.evaluate(pod_dir_1, pod_id="pod-001")

        # Second evaluation (PASS)
        pod_dir_2 = tmp_path / "pod-002"
        pod_dir_2.mkdir()
        instructions_file_2 = pod_dir_2 / "instructions.json"
        instructions_file_2.write_text(json.dumps({"instructions": "Task 2", "output_path": "result.json"}))
        result_file_2 = pod_dir_2 / "result.json"
        result_file_2.write_text(json.dumps({"result": "PASS"}))

        supervisor.evaluate(pod_dir_2, pod_id="pod-002")

        # Assert
        assert len(supervisor.evaluation_history) == 2
        assert supervisor.evaluation_history[0]["status"] == "FAIL"
        assert supervisor.evaluation_history[1]["status"] == "PASS"

    def test_get_current_attempt_returns_correct_count(self, tmp_path):
        """
        Current attempt count accessible for reporting and monitoring.

        Acceptance: Tracks attempt count correctly
        """
        # Arrange
        supervisor = SupervisorEvaluation(current_attempt=5)

        # Act
        attempt = supervisor.get_current_attempt()

        # Assert
        assert attempt == 5


class TestSupervisorEvaluationIntegration:
    """Integration tests with RequirementComparator and FeedbackManager."""

    def test_supervisor_uses_comparator_for_evaluation(self, tmp_path):
        """
        SupervisorEvaluation delegates comparison to RequirementComparator.

        Acceptance: Integrates RequirementComparator correctly
        """
        # Arrange
        pod_dir = tmp_path / "pod-001"
        pod_dir.mkdir()

        instructions_file = pod_dir / "instructions.json"
        instructions_data = {"instructions": "Test", "output_path": "result.json"}
        instructions_file.write_text(json.dumps(instructions_data))

        result_file = pod_dir / "result.json"
        result_data = {"result": "PASS"}
        result_file.write_text(json.dumps(result_data))

        supervisor = SupervisorEvaluation()

        # Act
        with patch("src.features.supervisor_evaluation.RequirementComparator") as MockComparator:
            mock_comp = Mock()
            mock_comp.evaluate.return_value = ("PASS", [])
            MockComparator.return_value = mock_comp

            supervisor_with_mock = SupervisorEvaluation()
            supervisor_with_mock.comparator = mock_comp

            status = supervisor_with_mock.evaluate(pod_dir, pod_id="pod-001")

            # Assert comparator was called
            mock_comp.evaluate.assert_called_once()

    def test_supervisor_uses_feedback_manager_for_writing(self, tmp_path):
        """
        SupervisorEvaluation delegates feedback writing to FeedbackManager.

        Acceptance: Integrates FeedbackManager correctly
        """
        # Arrange
        pod_dir = tmp_path / "pod-001"
        pod_dir.mkdir()

        instructions_file = pod_dir / "instructions.json"
        instructions_data = {"instructions": "Test", "output_path": "result.json"}
        instructions_file.write_text(json.dumps(instructions_data))

        result_file = pod_dir / "result.json"
        result_data = {"result": "PASS"}
        result_file.write_text(json.dumps(result_data))

        supervisor = SupervisorEvaluation()

        # Act
        with patch("src.features.supervisor_evaluation.FeedbackManager") as MockFeedback:
            mock_feedback = Mock()
            mock_feedback.write_pass.return_value = str(pod_dir / "feedback.json")
            MockFeedback.return_value = mock_feedback

            supervisor_with_mock = SupervisorEvaluation()
            supervisor_with_mock.feedback_manager = mock_feedback
            supervisor_with_mock.comparator = Mock()
            supervisor_with_mock.comparator.evaluate.return_value = ("PASS", [])

            status = supervisor_with_mock.evaluate(pod_dir, pod_id="pod-001")

            # Assert feedback manager was called
            mock_feedback.write_pass.assert_called_once()
