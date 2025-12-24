"""
Integration Test Suite for Sprint 2 Components (Issues #12-#17)

Purpose: Verify all 6 Sprint 2 components work together correctly

Test Coverage:
- Component integration: Components work together in workflows
- Data flow: Data passes correctly between components
- Error handling: Errors propagate correctly across components
- End-to-end: Complete supervisor-worker pod lifecycle

Requirements tested: Issue #18 - Integration tests + code review for all components
Dependencies: All 6 components (#12-#17) and primitives (#1-#10)
Stack: Python + pytest + pytest-mock
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

# Sprint 2 Components under integration test
from src.components.instruction_manager import InstructionManager
from src.components.result_manager import ResultManager
from src.components.feedback_manager import FeedbackManager
from src.components.llm_provider import LLMProvider
from src.components.requirement_comparator import RequirementComparator
from src.components.worker_executor import WorkerExecutor


class TestInstructionResultManagerIntegration:
    """Test InstructionManager + ResultManager integration."""

    def test_pod_workflow_instruction_creation_and_result_aggregation(self, tmp_path):
        """Complete workflow: Create instructions → Workers execute → Aggregate results.

        Tests: InstructionManager.create() integrates with ResultManager.aggregate_worker_results()
        """
        # Arrange: Create pod structure
        pod_dir = tmp_path / "pod-integration-test"
        pod_dir.mkdir()

        instruction_mgr = InstructionManager()
        result_mgr = ResultManager()

        # Act Phase 1: Supervisor creates instructions for pod
        instructions_file = instruction_mgr.create(
            instructions="Analyze dataset and provide summary statistics",
            pod_dir=pod_dir,
            session_id="session-int-001",
        )

        # Assert: Instructions file created
        assert Path(instructions_file).exists()
        assert (pod_dir / "instructions.json").exists()

        # Act Phase 2: Simulate 3 workers executing and producing results
        worker_ids = ["worker-001", "worker-002", "worker-003"]
        for worker_id in worker_ids:
            worker_dir = pod_dir / "workers" / worker_id
            worker_dir.mkdir(parents=True)

            result_mgr.write(
                result=f"{worker_id} completed analysis",
                worker_dir=worker_dir,
                worker_id=worker_id,
                pod_id="pod-integration-test",
                session_id="session-int-001",
            )

        # Act Phase 3: Aggregate all worker results
        aggregated = result_mgr.aggregate_worker_results(pod_dir)

        # Assert: All worker results aggregated correctly
        assert len(aggregated) == 3
        worker_ids_from_results = {r["worker_id"] for r in aggregated}
        assert worker_ids_from_results == set(worker_ids)


class TestRequirementComparatorFeedbackManagerIntegration:
    """Test RequirementComparator + FeedbackManager integration."""

    def test_evaluation_fail_writes_feedback_with_gaps(self, tmp_path):
        """Supervisor evaluates result → Writes FAIL feedback with gaps.

        Tests: RequirementComparator.evaluate() → FeedbackManager.write_fail()
        """
        # Arrange
        pod_dir = tmp_path / "pod-eval-fail"
        pod_dir.mkdir()

        comparator = RequirementComparator()
        feedback_mgr = FeedbackManager()

        # Act: Evaluate incomplete result
        instructions = "Create report with 5 sections: intro, methods, results, discussion, conclusion"
        result = "Report with intro and methods only"

        status, gaps = comparator.evaluate(instructions=instructions, result=result)

        assert status == "FAIL"
        assert len(gaps) > 0

        # Act: Write FAIL feedback
        feedback_file = feedback_mgr.write_fail(
            gaps=gaps,
            attempt=1,
            pod_dir=pod_dir,
            pod_id="pod-eval-fail",
        )

        # Assert: Feedback file contains evaluation gaps
        assert Path(feedback_file).exists()
        with open(feedback_file, "r") as f:
            feedback_data = json.load(f)

        assert feedback_data["status"] == "FAIL"
        assert feedback_data["attempt"] == 1
        assert len(feedback_data["gaps"]) > 0
        assert feedback_data["pod_id"] == "pod-eval-fail"

    def test_evaluation_pass_writes_feedback_with_result(self, tmp_path):
        """Supervisor evaluates result → Writes PASS feedback with result.

        Tests: RequirementComparator.evaluate() → FeedbackManager.write_pass()
        """
        # Arrange
        pod_dir = tmp_path / "pod-eval-pass"
        pod_dir.mkdir()

        comparator = RequirementComparator()
        feedback_mgr = FeedbackManager()

        # Act: Evaluate PASS result (RequirementComparator expects "PASS" string)
        instructions = "Verify user authentication"
        result = "PASS"  # Binary evaluator - only "PASS" succeeds

        status, gaps = comparator.evaluate(instructions=instructions, result=result)

        assert status == "PASS"
        assert gaps == []

        # Act: Write PASS feedback
        feedback_file = feedback_mgr.write_pass(
            result=result,
            attempts=2,
            pod_dir=pod_dir,
            pod_id="pod-eval-pass",
        )

        # Assert: Feedback file contains PASS status
        assert Path(feedback_file).exists()
        with open(feedback_file, "r") as f:
            feedback_data = json.load(f)

        assert feedback_data["status"] == "PASS"
        assert feedback_data["attempts"] == 2
        assert feedback_data["result"] == "PASS"


class TestWorkerExecutorComponentIntegration:
    """Test WorkerExecutor integration with LLMProvider and ResultManager."""

    @patch("src.components.worker_executor.LLMProvider")
    @patch("src.components.worker_executor.ResultManager")
    def test_worker_executor_reads_instructions_calls_llm_writes_result(
        self, mock_result_mgr_class, mock_llm_provider_class, tmp_path
    ):
        """WorkerExecutor orchestrates: Read instructions → Call LLM → Write result.

        Tests: WorkerExecutor integrates with LLMProvider and ResultManager
        """
        # Arrange: Setup mocks
        mock_llm_instance = Mock()
        mock_llm_instance.generate.return_value = "Analysis: Dataset has 1000 rows, 10 columns"
        mock_llm_provider_class.return_value = mock_llm_instance

        mock_result_mgr_instance = Mock()
        mock_result_mgr_instance.write.return_value = "/path/to/result.json"
        mock_result_mgr_class.return_value = mock_result_mgr_instance

        # Create instructions file
        worker_dir = tmp_path / "pod-worker-exec" / "workers" / "worker-001"
        worker_dir.mkdir(parents=True)

        instructions_file = worker_dir.parent.parent / "instructions.json"
        instructions_data = {
            "instructions": "Analyze dataset",
            "output_path": "result.json",
            "pod_id": "pod-worker-exec",
            "session_id": "session-worker-001",
            "project_root": str(tmp_path),
            "timestamp": "2025-12-24T23:30:00Z",
        }
        instructions_file.write_text(json.dumps(instructions_data))

        # Create mock LLM config file
        llm_config_file = tmp_path / "llm_config.json"
        llm_config_file.write_text(json.dumps({"model": "gpt-4", "temperature": 0.7}))

        # Act: Execute worker task
        executor = WorkerExecutor()
        result_path = executor.execute(
            instructions_path=str(instructions_file),
            worker_config={
                "worker_id": "worker-001",
                "worker_dir": str(worker_dir),
                "pod_id": "pod-worker-exec",
                "session_id": "session-worker-001",
                "llm_config_path": str(llm_config_file),
            },
        )

        # Assert: LLM called and result written
        mock_llm_instance.generate.assert_called_once()
        mock_result_mgr_instance.write.assert_called_once()
        assert result_path == "/path/to/result.json"


class TestSupervisorWorkerFeedbackLoop:
    """Test complete supervisor-worker feedback loop integration."""

    def test_fail_retry_pass_workflow_all_components(self, tmp_path):
        """Full workflow: Worker FAIL → Feedback → Worker RETRY → PASS.

        Tests: InstructionManager + ResultManager + RequirementComparator + FeedbackManager
        """
        # Arrange: Setup pod
        pod_dir = tmp_path / "pod-feedback-loop"
        pod_dir.mkdir()
        worker_dir = pod_dir / "workers" / "worker-001"
        worker_dir.mkdir(parents=True)

        instruction_mgr = InstructionManager()
        result_mgr = ResultManager()
        comparator = RequirementComparator()
        feedback_mgr = FeedbackManager()

        # Phase 1: Supervisor creates instructions
        instructions_file = instruction_mgr.create(
            instructions="Generate report with 3 sections",
            pod_dir=pod_dir,
            session_id="session-feedback-001",
        )

        # Phase 2: Worker attempt #1 - produces incomplete result
        result_mgr.write(
            result="Report with 2 sections",
            worker_dir=worker_dir,
            worker_id="worker-001",
            pod_id="pod-feedback-loop",
            session_id="session-feedback-001",
        )

        # Phase 3: Supervisor evaluates → FAIL
        status_1, gaps_1 = comparator.evaluate(
            instructions="Generate report with 3 sections",
            result="Report with 2 sections",
        )

        assert status_1 == "FAIL"
        assert len(gaps_1) > 0

        # Phase 4: Supervisor writes FAIL feedback
        feedback_file_1 = feedback_mgr.write_fail(
            gaps=gaps_1,
            attempt=1,
            pod_dir=pod_dir,
            pod_id="pod-feedback-loop",
        )

        # Phase 5: Worker attempt #2 - reads feedback, produces correct result
        # (In real system, worker reads feedback.json - here we simulate with "PASS")
        result_mgr.write(
            result="PASS",  # Binary evaluator expects "PASS" string
            worker_dir=worker_dir,
            worker_id="worker-001",
            pod_id="pod-feedback-loop",
            session_id="session-feedback-001",
        )

        # Phase 6: Supervisor evaluates → PASS
        status_2, gaps_2 = comparator.evaluate(
            instructions="Generate report with 3 sections",
            result="PASS",
        )

        assert status_2 == "PASS"
        assert gaps_2 == []

        # Phase 7: Supervisor writes PASS feedback
        feedback_file_2 = feedback_mgr.write_pass(
            result="PASS",
            attempts=2,
            pod_dir=pod_dir,
            pod_id="pod-feedback-loop",
        )

        # Assert: Complete feedback loop executed
        assert Path(feedback_file_1).exists()
        assert Path(feedback_file_2).exists()

        with open(feedback_file_2, "r") as f:
            final_feedback = json.load(f)

        assert final_feedback["status"] == "PASS"
        assert final_feedback["attempts"] == 2


class TestEndToEndPodLifecycleAllComponents:
    """Test complete pod lifecycle with all 6 components."""

    @patch("src.components.worker_executor.LLMProvider")
    def test_complete_pod_lifecycle_supervisor_creates_worker_executes_supervisor_evaluates(
        self, mock_llm_provider_class, tmp_path
    ):
        """End-to-end pod lifecycle: Instructions → Execution → Evaluation → Feedback.

        Tests: ALL 6 components working together
        - InstructionManager: Create instructions
        - WorkerExecutor: Execute task
        - LLMProvider: Generate result
        - ResultManager: Store result
        - RequirementComparator: Evaluate result
        - FeedbackManager: Write feedback
        """
        # Arrange: Mock LLM
        mock_llm_instance = Mock()
        mock_llm_instance.generate.return_value = "PASS"  # Binary evaluator
        mock_llm_provider_class.return_value = mock_llm_instance

        # Setup pod structure
        pod_dir = tmp_path / "pod-e2e-test"
        pod_dir.mkdir()
        worker_dir = pod_dir / "workers" / "worker-e2e-001"
        worker_dir.mkdir(parents=True)

        # Initialize all components
        instruction_mgr = InstructionManager()
        worker_executor = WorkerExecutor()
        result_mgr = ResultManager()
        comparator = RequirementComparator()
        feedback_mgr = FeedbackManager()

        # === PHASE 1: Supervisor creates instructions ===
        instructions_file = instruction_mgr.create(
            instructions="Validate user authentication flow",
            pod_dir=pod_dir,
            session_id="session-e2e-001",
        )

        assert Path(instructions_file).exists()

        # Create LLM config file for worker
        llm_config_file = tmp_path / "llm_config.json"
        llm_config_file.write_text(json.dumps({"model": "gpt-4", "temperature": 0.7}))

        # === PHASE 2: Worker executes task ===
        result_file = worker_executor.execute(
            instructions_path=instructions_file,
            worker_config={
                "worker_id": "worker-e2e-001",
                "worker_dir": worker_dir,  # Pass as Path object, not string
                "pod_id": "pod-e2e-test",
                "session_id": "session-e2e-001",
                "llm_config_path": str(llm_config_file),
            },
        )

        assert Path(result_file).exists()

        # === PHASE 3: Supervisor reads result ===
        result_data = result_mgr.read(result_file)
        assert "result" in result_data

        # === PHASE 4: Supervisor evaluates result ===
        status, gaps = comparator.evaluate(
            instructions="Validate user authentication flow",
            result=result_data["result"],
        )

        # === PHASE 5: Supervisor writes feedback ===
        if status == "PASS":
            feedback_file = feedback_mgr.write_pass(
                result=result_data["result"],
                attempts=1,
                pod_dir=pod_dir,
                pod_id="pod-e2e-test",
            )
        else:
            feedback_file = feedback_mgr.write_fail(
                gaps=gaps,
                attempt=1,
                pod_dir=pod_dir,
                pod_id="pod-e2e-test",
            )

        # Assert: Complete pod lifecycle executed
        assert Path(feedback_file).exists()

        with open(feedback_file, "r") as f:
            feedback_data = json.load(f)

        assert feedback_data["status"] == "PASS"
        assert feedback_data["pod_id"] == "pod-e2e-test"


class TestCrossComponentDataConsistency:
    """Test data consistency across component boundaries."""

    def test_pod_id_and_session_id_propagate_through_all_components(self, tmp_path):
        """Verify pod_id and session_id flow correctly through all components.

        Tests: Metadata consistency across InstructionManager → ResultManager → FeedbackManager
        """
        # Arrange
        pod_dir = tmp_path / "pod-metadata-test"
        pod_dir.mkdir()
        worker_dir = pod_dir / "workers" / "worker-meta-001"
        worker_dir.mkdir(parents=True)

        pod_id = "pod-metadata-test"
        session_id = "session-metadata-001"

        instruction_mgr = InstructionManager()
        result_mgr = ResultManager()
        feedback_mgr = FeedbackManager()

        # Act: Flow metadata through all components
        # 1. Instructions
        instructions_file = instruction_mgr.create(
            instructions="Test task",
            pod_dir=pod_dir,
            session_id=session_id,
        )

        with open(instructions_file, "r") as f:
            inst_data = json.load(f)

        # 2. Result
        result_file = result_mgr.write(
            result="Task complete",
            worker_dir=worker_dir,
            worker_id="worker-meta-001",
            pod_id=pod_id,
            session_id=session_id,
        )

        with open(result_file, "r") as f:
            result_data = json.load(f)

        # 3. Feedback
        feedback_file = feedback_mgr.write_pass(
            result="PASS",
            attempts=1,
            pod_dir=pod_dir,
            pod_id=pod_id,
        )

        with open(feedback_file, "r") as f:
            feedback_data = json.load(f)

        # Assert: Metadata consistent
        assert inst_data["pod_id"] == pod_id
        assert inst_data["session_id"] == session_id

        assert result_data["pod_id"] == pod_id
        assert result_data["session_id"] == session_id

        assert feedback_data["pod_id"] == pod_id


class TestComponentErrorPropagation:
    """Test error handling across component boundaries."""

    def test_invalid_instructions_rejected_before_reaching_worker(self, tmp_path):
        """InstructionManager validation prevents invalid data from reaching WorkerExecutor.

        Tests: Error handling at component boundary
        """
        # Arrange
        pod_dir = tmp_path / "pod-invalid-inst"
        pod_dir.mkdir()

        instruction_mgr = InstructionManager()

        # Act & Assert: Empty instructions raise ValueError
        with pytest.raises(ValueError, match="Instruction validation failed"):
            instruction_mgr.create(
                instructions="",  # Invalid - empty
                pod_dir=pod_dir,
                session_id="session-invalid-001",
            )

    def test_result_validation_failure_captured_in_feedback(self, tmp_path):
        """Invalid result triggers feedback loop with validation errors.

        Tests: ResultManager validation → FeedbackManager captures errors
        """
        # Arrange
        pod_dir = tmp_path / "pod-invalid-result"
        pod_dir.mkdir()
        worker_dir = pod_dir / "workers" / "worker-001"
        worker_dir.mkdir(parents=True)

        result_file = worker_dir / "result.json"
        # Invalid: missing required fields
        result_file.write_text(json.dumps({"result": "done"}))

        result_mgr = ResultManager()
        feedback_mgr = FeedbackManager()

        # Act: Validate result
        is_valid, errors = result_mgr.validate_file(str(result_file))

        assert is_valid is False
        assert len(errors) > 0

        # Act: Write feedback about validation failure
        feedback_file = feedback_mgr.write_fail(
            gaps=errors,
            attempt=1,
            pod_dir=pod_dir,
            pod_id="pod-invalid-result",
        )

        # Assert: Feedback captures validation errors
        with open(feedback_file, "r") as f:
            feedback_data = json.load(f)

        assert feedback_data["status"] == "FAIL"
        assert len(feedback_data["gaps"]) > 0
