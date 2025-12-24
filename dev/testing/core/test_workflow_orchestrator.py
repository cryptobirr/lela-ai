"""Tests for WorkflowOrchestrator core module"""

import json
import time
from pathlib import Path

import pytest

from src.core.workflow_orchestrator import CircuitBreaker, WorkflowOrchestrator


class TestCircuitBreaker:
    """Test suite for CircuitBreaker"""

    def test_circuit_breaker_starts_closed(self):
        """Test circuit breaker starts in closed state"""
        breaker = CircuitBreaker(max_failures=3)
        assert breaker.is_open() is False
        assert breaker.failure_count == 0

    def test_circuit_breaker_opens_after_max_failures(self):
        """Test circuit breaker opens after reaching max failures"""
        breaker = CircuitBreaker(max_failures=3)
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.is_open() is False

        breaker.record_failure()
        assert breaker.is_open() is True
        assert breaker.failure_count == 3


class TestWorkflowOrchestratorBasics:
    """Test suite for WorkflowOrchestrator basic functionality"""

    def test_orchestrator_initialization(self):
        """Test orchestrator initializes with correct defaults"""
        orchestrator = WorkflowOrchestrator()
        assert orchestrator.max_retries == 3
        assert orchestrator.backoff_base == 1.0
        assert orchestrator.circuit_breaker.max_failures == 3

    def test_orchestrator_custom_config(self):
        """Test orchestrator accepts custom configuration"""
        orchestrator = WorkflowOrchestrator(max_retries=5, backoff_base=2.0)
        assert orchestrator.max_retries == 5
        assert orchestrator.backoff_base == 2.0

    def test_checkpoint_resume_skips_completed_steps(self, tmp_path):
        """Test checkpoint resume skips already completed steps (line 63)"""
        workflow_steps = [
            {"action": "step1", "checkpoint": True},
            {"action": "step2", "checkpoint": True},
            {"action": "step3"},
        ]

        orchestrator = WorkflowOrchestrator()

        # First execution - complete step1
        orchestrator._checkpoint_state["step1"] = True

        # Execute workflow
        result = orchestrator.execute_with_retry(workflow_steps, context={})

        # Assert: step1 was skipped (not executed)
        assert "step1_executions" not in result or result.get("step1_executions") == 0
        assert result["step2_executions"] == 1
        assert result["step3_executions"] == 1

    def test_write_file_action_tracks_created_files(self, tmp_path):
        """Test write_file action appends to created_files list (line 116)"""
        test_file = tmp_path / "test.json"
        workflow_steps = [
            {"action": "write_file", "path": str(test_file), "data": {"test": True}},
        ]

        orchestrator = WorkflowOrchestrator()
        orchestrator.execute_with_retry(workflow_steps, context={})

        # Assert: File was tracked in created_files
        assert len(orchestrator._created_files) == 1
        assert orchestrator._created_files[0] == Path(test_file)
        assert test_file.exists()

    def test_generic_step_failure_handling(self):
        """Test generic step with should_fail raises exception (line 122)"""
        workflow_steps = [
            {"action": "step_custom", "should_fail": True},
        ]

        orchestrator = WorkflowOrchestrator(max_retries=1)

        # Assert: Step failure raises exception (circuit breaker or step failure)
        with pytest.raises(Exception):
            orchestrator.execute_with_retry(workflow_steps, context={})

    def test_reraise_exception_after_max_retries(self, tmp_path):
        """Test exception is re-raised after max retries exhausted (line 149)"""
        workflow_steps = [
            {"action": "create_file", "path": "test.json"},
        ]

        orchestrator = WorkflowOrchestrator(max_retries=2)

        # Mock file_writer to always fail
        def failing_write(*args, **kwargs):
            raise Exception("Write failed")

        orchestrator.file_writer.write = failing_write

        # Assert: Exception re-raised after retries (circuit breaker opens after 2 failures)
        with pytest.raises(Exception, match="Circuit breaker opened"):
            orchestrator.execute_with_retry(workflow_steps, context={"root": tmp_path})

    def test_circuit_breaker_check_before_retry(self):
        """Test circuit breaker checked before retry (line 153)"""
        workflow_steps = [
            {"action": "step1", "should_fail_count": 5},  # Will fail multiple times
        ]

        orchestrator = WorkflowOrchestrator(max_retries=5, backoff_base=0.01)

        # Assert: Circuit breaker opens and stops retries
        with pytest.raises(Exception, match="Circuit breaker opened"):
            orchestrator.execute_with_retry(workflow_steps, context={})

        assert orchestrator.circuit_breaker.is_open() is True

    def test_reraise_original_exception_when_not_create_write_action(self):
        """Test line 149 - reraise original exception for non-create/write actions"""
        workflow_steps = [
            {"action": "some_other_action", "should_fail_count": 10},
        ]

        # Use high max_failures to prevent circuit breaker from opening
        orchestrator = WorkflowOrchestrator(max_retries=1)
        orchestrator.circuit_breaker = CircuitBreaker(max_failures=100)

        # Assert: Original exception is re-raised (not circuit breaker)
        with pytest.raises(Exception, match="Intentional failure"):
            orchestrator.execute_with_retry(workflow_steps, context={})

    def test_circuit_breaker_before_retry_on_intermediate_attempt(self):
        """Test line 153 - circuit breaker check before retry on intermediate attempts"""
        workflow_steps = [
            {"action": "step1", "should_fail_count": 2},
        ]

        orchestrator = WorkflowOrchestrator(max_retries=5, backoff_base=0.01)

        # Manually open circuit breaker before execution
        orchestrator.circuit_breaker._is_open = True

        # Assert: Circuit breaker check prevents retry
        with pytest.raises(Exception, match="Circuit breaker opened"):
            orchestrator.execute_with_retry(workflow_steps, context={})


class TestWorkflowOrchestratorRollback:
    """Test rollback functionality"""

    def test_rollback_deletes_created_files(self, tmp_path):
        """Test rollback removes files created during workflow"""
        file1 = tmp_path / "file1.json"
        file2 = tmp_path / "file2.json"

        workflow_steps = [
            {"action": "write_file", "path": str(file1), "data": {}},
            {"action": "write_file", "path": str(file2), "data": {}},
            {"action": "invalid_operation"},  # Trigger rollback
        ]

        orchestrator = WorkflowOrchestrator(max_retries=1)

        with pytest.raises(Exception):
            orchestrator.execute_with_retry(workflow_steps, context={})

        # Assert: Files were deleted by rollback
        assert not file1.exists()
        assert not file2.exists()

    def test_rollback_removes_directories(self, tmp_path):
        """Test rollback removes directories created during workflow"""
        workflow_steps = [
            {"action": "create_session", "project_root": tmp_path, "agent_name": "test"},
            {"action": "fail_intentionally"},  # Trigger rollback
        ]

        orchestrator = WorkflowOrchestrator(max_retries=1)

        with pytest.raises(Exception):
            orchestrator.execute_with_retry(workflow_steps, context={"root": tmp_path})

        # Assert: .agent-harness directory removed
        harness_dir = tmp_path / ".agent-harness"
        assert not harness_dir.exists()


class TestWorkflowOrchestratorRetry:
    """Test retry logic with exponential backoff"""

    def test_retry_with_exponential_backoff(self):
        """Test retry waits with exponential backoff"""
        workflow_steps = [
            {"action": "step1", "should_fail_count": 2},  # Fails twice, succeeds on 3rd
        ]

        orchestrator = WorkflowOrchestrator(max_retries=3, backoff_base=0.1)
        start_time = time.time()

        result = orchestrator.execute_with_retry(workflow_steps, context={})
        elapsed = time.time() - start_time

        # Assert: Total wait time is roughly 0.1 + 0.2 = 0.3s
        assert elapsed >= 0.2  # At least 0.1s + 0.2s backoff
        assert result["step1_executions"] == 3

    def test_successful_retry_after_transient_failure(self):
        """Test workflow succeeds after transient failure"""
        workflow_steps = [
            {"action": "step1", "should_fail_once": True},
            {"action": "step2"},
        ]

        orchestrator = WorkflowOrchestrator(max_retries=3)
        result = orchestrator.execute_with_retry(workflow_steps, context={})

        assert result["status"] == "completed"
        assert result["step1_executions"] == 2  # Failed once, succeeded on retry
        assert result["step2_executions"] == 1
