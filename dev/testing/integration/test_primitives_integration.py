"""
Integration tests for primitives working together

Purpose: Verify primitives work correctly when combined in realistic workflows

Test Coverage:
- Config loading → path resolution → file writing workflow
- Concurrent file operations (writing + logging)
- End-to-end session/pod/worker directory creation
- Error propagation across primitive boundaries
- Realistic pod communication patterns (instructions → results → feedback)

Requirements tested: Issue #11 - Integration testing for all 10 primitives
"""

import concurrent.futures
import json
import os
import tempfile
from pathlib import Path

import pytest

from src.primitives.config_loader import ConfigLoader
from src.primitives.file_reader import FileReader
from src.primitives.file_writer import FileWriter
from src.primitives.gap_extractor import GapExtractor
from src.primitives.logger import Logger
from src.primitives.path_resolver import PathResolver
from src.primitives.timestamp_generator import TimestampGenerator


class TestConfigToFileWorkflow:
    """Test workflow: Load config → resolve paths → write output"""

    def test_load_config_resolve_path_write_result_happy_path(self, tmp_path):
        """
        INTEGRATION: ConfigLoader + PathResolver + FileWriter

        Scenario: Agent loads config, determines output path, writes result
        Expected: All primitives work together seamlessly
        """
        # Arrange: Create config file with path template
        config_data = {
            "agent_name": "test-agent",
            "output_template": "results/output-{session}.json",
        }
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps(config_data), encoding="utf-8")

        # Act: Load config, resolve paths, write output
        config_loader = ConfigLoader()
        path_resolver = PathResolver()
        file_writer = FileWriter()

        # Load configuration
        config = config_loader.load(str(config_path))

        # Resolve project root and create session directory
        project_root = path_resolver.get_project_root(tmp_path)
        session_dir = path_resolver.create_session_dir(project_root, config["agent_name"])

        # Construct output path and write result
        output_path = session_dir / "result.json"
        result_data = {"status": "PASS", "timestamp": "2025-12-24T10:00:00Z"}
        success = file_writer.write(str(output_path), result_data)

        # Assert: File written successfully with correct content
        assert success is True
        assert output_path.exists()

        written_content = json.loads(output_path.read_text(encoding="utf-8"))
        assert written_content == result_data

    def test_config_with_env_vars_creates_session_and_writes(self, tmp_path):
        """
        INTEGRATION: ConfigLoader (env substitution) + PathResolver + FileWriter

        Scenario: Config has env var, session created with resolved value
        Expected: Env var substituted, directory created, file written
        """
        # Arrange: Set env var and create config
        os.environ["TEST_AGENT_NAME"] = "env-agent"
        config_data = {"agent_name": "${TEST_AGENT_NAME}", "max_retries": 3}
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps(config_data), encoding="utf-8")

        try:
            # Act: Load config with env var substitution
            config_loader = ConfigLoader()
            path_resolver = PathResolver()
            file_writer = FileWriter()

            config = config_loader.load(str(config_path))
            assert config["agent_name"] == "env-agent"  # Env var substituted

            # Create session using resolved agent name
            project_root = path_resolver.get_project_root(tmp_path)
            session_dir = path_resolver.create_session_dir(project_root, config["agent_name"])

            # Write config to session directory
            output_path = session_dir / "loaded-config.json"
            file_writer.write(str(output_path), config)

            # Assert: Directory created with env-agent name
            assert "env-agent" in session_dir.name
            assert output_path.exists()
            assert json.loads(output_path.read_text())["agent_name"] == "env-agent"

        finally:
            del os.environ["TEST_AGENT_NAME"]

    def test_missing_env_var_prevents_downstream_operations(self, tmp_path):
        """
        INTEGRATION: ConfigLoader error propagation

        Scenario: Config has undefined env var, prevents file writing
        Expected: ConfigLoader raises ValueError, no files written
        """
        # Arrange: Config with undefined env var
        config_data = {"api_key": "${UNDEFINED_VAR}"}
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps(config_data), encoding="utf-8")

        # Act & Assert: ConfigLoader fails, preventing downstream operations
        config_loader = ConfigLoader()

        with pytest.raises(ValueError, match="Environment variable 'UNDEFINED_VAR' is not defined"):
            config_loader.load(str(config_path))

        # No session directory should be created (workflow stopped early)
        harness_dir = tmp_path / ".agent-harness"
        assert not harness_dir.exists()


class TestConcurrentFileOperations:
    """Test concurrent writes and logging from multiple workers"""

    def test_concurrent_atomic_writes_no_corruption(self, tmp_path):
        """
        INTEGRATION: FileWriter.write_atomic() + concurrent execution

        Scenario: 10 workers write to same file simultaneously
        Expected: Atomic writes prevent corruption, final file is valid JSON
        """
        # Arrange: Shared file path
        output_file = tmp_path / "shared-result.json"

        def write_worker_result(worker_id: int):
            """Worker writes its result atomically"""
            writer = FileWriter()
            data = {"worker_id": worker_id, "status": "completed"}
            writer.write_atomic(str(output_file), data)

        # Act: Launch 10 concurrent workers
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(write_worker_result, i) for i in range(10)]
            concurrent.futures.wait(futures)

        # Assert: File exists and contains valid JSON (no corruption)
        assert output_file.exists()
        final_content = json.loads(output_file.read_text(encoding="utf-8"))
        assert "worker_id" in final_content
        assert final_content["status"] == "completed"

    def test_concurrent_locked_writes_no_corruption(self, tmp_path):
        """
        INTEGRATION: FileWriter.write_with_lock() + concurrent execution

        Scenario: 10 workers write to same file with file locking
        Expected: Locks prevent concurrent writes, final file is valid JSON
        """
        # Arrange: Shared file path
        output_file = tmp_path / "locked-result.json"

        def write_with_lock(worker_id: int):
            """Worker writes with file lock"""
            writer = FileWriter()
            data = {"worker_id": worker_id, "timestamp": "2025-12-24T10:00:00Z"}
            writer.write_with_lock(str(output_file), data)

        # Act: Launch 10 concurrent workers
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(write_with_lock, i) for i in range(10)]
            concurrent.futures.wait(futures)

        # Assert: File exists and contains valid JSON
        assert output_file.exists()
        final_content = json.loads(output_file.read_text(encoding="utf-8"))
        assert "worker_id" in final_content

    def test_concurrent_logging_and_writing(self, tmp_path):
        """
        INTEGRATION: Logger + FileWriter + concurrent execution

        Scenario: Workers simultaneously log and write results
        Expected: Both operations complete without deadlock or corruption
        """
        # Arrange: Shared log and result paths
        log_file = tmp_path / "worker.log"
        results_dir = tmp_path / "results"
        results_dir.mkdir()

        def worker_task(worker_id: int):
            """Worker logs activity and writes result"""
            logger = Logger(output_file=str(log_file))
            writer = FileWriter()

            # Log start
            logger.info(f"Worker {worker_id} starting", {"worker_id": worker_id})

            # Write result
            result_path = results_dir / f"result-{worker_id}.json"
            writer.write(str(result_path), {"worker_id": worker_id, "status": "done"})

            # Log completion
            logger.info(f"Worker {worker_id} completed", {"worker_id": worker_id})
            logger.close()

        # Act: Launch 5 concurrent workers
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker_task, i) for i in range(5)]
            concurrent.futures.wait(futures)

        # Assert: All result files written
        result_files = list(results_dir.glob("result-*.json"))
        assert len(result_files) == 5

        # Assert: Log file exists and contains entries
        assert log_file.exists()
        log_content = log_file.read_text(encoding="utf-8")
        assert "Worker 0 starting" in log_content or "starting" in log_content


class TestEndToEndPodWorkflow:
    """Test complete pod creation and communication workflow"""

    def test_create_session_pod_worker_hierarchy_and_communicate(self, tmp_path):
        """
        INTEGRATION: PathResolver + FileWriter + FileReader + TimestampGenerator

        Scenario: Create session → pod → worker dirs, write instructions, read results
        Expected: Full directory hierarchy created, file communication works
        """
        # Arrange: Initialize primitives
        path_resolver = PathResolver()
        file_writer = FileWriter()
        file_reader = FileReader()
        timestamp_gen = TimestampGenerator()

        # Act: Create directory hierarchy
        project_root = path_resolver.get_project_root(tmp_path)
        session_dir = path_resolver.create_session_dir(project_root, "test-agent")
        pod_dir = path_resolver.create_pod_dir(session_dir, "pod-01")
        worker_dir = path_resolver.create_worker_dir(pod_dir, "worker-01")

        # Write instructions.json to worker directory
        instructions = {
            "task": "Extract requirements",
            "input": "User wants authentication",
            "timestamp": timestamp_gen.now(),
        }
        instructions_path = worker_dir / "instructions.json"
        file_writer.write(str(instructions_path), instructions)

        # Write result.json to worker directory
        result = {
            "requirements": ["Implement user login", "Store credentials securely"],
            "status": "completed",
            "timestamp": timestamp_gen.now(),
        }
        result_path = worker_dir / "result.json"
        file_writer.write(str(result_path), result)

        # Read back the files
        read_instructions = file_reader.read(str(instructions_path))
        read_result = file_reader.read(str(result_path))

        # Assert: Directory hierarchy created
        assert session_dir.exists()
        assert pod_dir.exists()
        assert worker_dir.exists()
        assert "test-agent" in session_dir.name
        assert "pod-01" in pod_dir.name
        assert "worker-01" in worker_dir.name

        # Assert: File communication works
        assert read_instructions["task"] == "Extract requirements"
        assert read_result["status"] == "completed"
        assert len(read_result["requirements"]) == 2

    def test_multiple_pods_isolated_directories(self, tmp_path):
        """
        INTEGRATION: PathResolver creates isolated pod directories

        Scenario: Create 3 pods in same session
        Expected: Each pod has isolated directory with unique timestamp
        """
        # Arrange: Initialize path resolver
        path_resolver = PathResolver()

        # Act: Create session and 3 pods
        project_root = path_resolver.get_project_root(tmp_path)
        session_dir = path_resolver.create_session_dir(project_root, "multi-pod-agent")

        pod_dirs = [
            path_resolver.create_pod_dir(session_dir, f"pod-{i:02d}") for i in range(3)
        ]

        # Assert: All pod directories exist and are unique
        assert len(pod_dirs) == 3
        assert len(set(pod_dirs)) == 3  # All unique paths
        for pod_dir in pod_dirs:
            assert pod_dir.exists()
            assert pod_dir.parent == session_dir / "pods"

    def test_pod_feedback_loop_with_gap_extraction(self, tmp_path):
        """
        INTEGRATION: GapExtractor + FileWriter + FileReader

        Scenario: Supervisor writes instructions, worker fails, supervisor extracts gaps
        Expected: Gap extraction identifies missing requirements from feedback
        """
        # Arrange: Create pod directory
        path_resolver = PathResolver()
        file_writer = FileWriter()
        file_reader = FileReader()
        gap_extractor = GapExtractor()

        project_root = path_resolver.get_project_root(tmp_path)
        session_dir = path_resolver.create_session_dir(project_root, "feedback-agent")
        pod_dir = path_resolver.create_pod_dir(session_dir, "pod-feedback")

        # Write instructions
        instructions = {
            "requirements": [
                "Implement user authentication",
                "Add password hashing",
                "Support OAuth2",
            ]
        }
        instructions_path = pod_dir / "instructions.json"
        file_writer.write(str(instructions_path), instructions)

        # Write incomplete result
        result = {
            "implemented": ["User authentication", "Password hashing"],
            "status": "partial",
        }
        result_path = pod_dir / "result.json"
        file_writer.write(str(result_path), result)

        # Act: Extract gaps between instructions and result
        requirements = [
            "Implement user authentication",
            "Add password hashing",
            "Support OAuth2",
        ]
        result_text = "Implemented user authentication and password hashing"

        gaps = gap_extractor.find_gaps(requirements, result_text)

        # Assert: Gap extraction identifies missing OAuth2
        assert len(gaps) > 0
        # Gap should mention OAuth2 or missing requirement
        assert any("oauth" in gap.lower() or "missing" in gap.lower() for gap in gaps)


class TestErrorPropagation:
    """Test error handling across primitive boundaries"""

    def test_invalid_config_prevents_session_creation(self, tmp_path):
        """
        INTEGRATION: ConfigLoader validation error stops workflow

        Scenario: Invalid config fails validation, prevents downstream operations
        Expected: ValueError raised, no session directories created
        """
        # Arrange: Create invalid config and schema
        config_data = {"agent_name": 123}  # Should be string
        schema = {
            "type": "object",
            "properties": {"agent_name": {"type": "string"}},
            "required": ["agent_name"],
        }
        config_path = tmp_path / "invalid-config.json"
        config_path.write_text(json.dumps(config_data), encoding="utf-8")

        # Act & Assert: ConfigLoader fails validation
        config_loader = ConfigLoader()

        with pytest.raises(ValueError, match="Config validation failed"):
            config_loader.load(str(config_path), schema)

        # No session directory should be created
        harness_dir = tmp_path / ".agent-harness"
        assert not harness_dir.exists()

    def test_permission_error_propagates_from_file_writer(self, tmp_path):
        """
        INTEGRATION: FileWriter permission error prevents result writing

        Scenario: Worker attempts to write to read-only directory
        Expected: PermissionError raised, workflow stops
        """
        # Arrange: Create read-only directory
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)  # Read-only

        # Act & Assert: FileWriter raises PermissionError
        writer = FileWriter()
        result_path = readonly_dir / "result.json"

        with pytest.raises(PermissionError):
            writer.write(str(result_path), {"status": "FAIL"})

        # Cleanup: Restore permissions for pytest cleanup
        readonly_dir.chmod(0o755)

    def test_missing_config_file_prevents_pod_creation(self, tmp_path):
        """
        INTEGRATION: FileNotFoundError from ConfigLoader stops workflow

        Scenario: Config file doesn't exist
        Expected: FileNotFoundError raised, no pods created
        """
        # Arrange: Path to non-existent config
        config_path = tmp_path / "missing-config.json"

        # Act & Assert: ConfigLoader raises FileNotFoundError
        config_loader = ConfigLoader()

        with pytest.raises(FileNotFoundError):
            config_loader.load(str(config_path))

        # No directories should be created
        harness_dir = tmp_path / ".agent-harness"
        assert not harness_dir.exists()


class TestRealisticPodCommunication:
    """Test realistic pod communication patterns from CLAUDE.md"""

    def test_supervisor_worker_pass_workflow(self, tmp_path):
        """
        INTEGRATION: Complete PASS workflow

        Scenario: Supervisor writes instructions → Worker writes result → Supervisor evaluates PASS
        Expected: All files written correctly, workflow completes successfully
        """
        # Arrange: Create pod structure
        path_resolver = PathResolver()
        file_writer = FileWriter()
        file_reader = FileReader()
        timestamp_gen = TimestampGenerator()

        project_root = path_resolver.get_project_root(tmp_path)
        session_dir = path_resolver.create_session_dir(project_root, "supervisor-agent")
        pod_dir = path_resolver.create_pod_dir(session_dir, "pod-pass")

        # Act: Supervisor writes instructions
        instructions = {
            "instructions": "Extract user requirements from input text",
            "output_path": "result.json",
            "timestamp": timestamp_gen.now(),
        }
        instructions_path = pod_dir / "instructions.json"
        file_writer.write(str(instructions_path), instructions)

        # Worker writes result
        result = {
            "requirements": ["User authentication", "Data storage"],
            "status": "completed",
            "timestamp": timestamp_gen.now(),
        }
        result_path = pod_dir / instructions["output_path"]
        file_writer.write(str(result_path), result)

        # Supervisor evaluates and writes PASS feedback
        feedback = {
            "status": "PASS",
            "result": result,
            "attempts": 1,
            "timestamp": timestamp_gen.now(),
        }
        feedback_path = pod_dir / "feedback.json"
        file_writer.write(str(feedback_path), feedback)

        # Assert: All files exist and contain correct data
        read_instructions = file_reader.read(str(instructions_path))
        read_result = file_reader.read(str(result_path))
        read_feedback = file_reader.read(str(feedback_path))

        assert read_instructions["instructions"] == instructions["instructions"]
        assert read_result["status"] == "completed"
        assert read_feedback["status"] == "PASS"
        assert read_feedback["attempts"] == 1

    def test_supervisor_worker_fail_retry_workflow(self, tmp_path):
        """
        INTEGRATION: FAIL → retry workflow

        Scenario: Worker result incomplete → Supervisor writes FAIL feedback → Worker retries
        Expected: Feedback loop works, retry attempt tracked
        """
        # Arrange: Create pod structure
        path_resolver = PathResolver()
        file_writer = FileWriter()
        timestamp_gen = TimestampGenerator()

        project_root = path_resolver.get_project_root(tmp_path)
        session_dir = path_resolver.create_session_dir(project_root, "retry-agent")
        pod_dir = path_resolver.create_pod_dir(session_dir, "pod-retry")

        # Act: Supervisor writes instructions
        instructions = {
            "instructions": "Implement features A, B, and C",
            "output_path": "result.json",
        }
        instructions_path = pod_dir / "instructions.json"
        file_writer.write(str(instructions_path), instructions)

        # Worker writes incomplete result (attempt 1)
        result_attempt1 = {"implemented": ["A", "B"], "status": "partial"}
        result_path = pod_dir / "result.json"
        file_writer.write(str(result_path), result_attempt1)

        # Supervisor writes FAIL feedback
        feedback_attempt1 = {
            "status": "FAIL",
            "gaps": ["Missing feature C"],
            "attempt": 1,
            "timestamp": timestamp_gen.now(),
        }
        feedback_path = pod_dir / "feedback.json"
        file_writer.write(str(feedback_path), feedback_attempt1)

        # Worker retries and writes complete result (attempt 2)
        result_attempt2 = {"implemented": ["A", "B", "C"], "status": "completed"}
        file_writer.write(str(result_path), result_attempt2)

        # Supervisor writes PASS feedback
        feedback_attempt2 = {
            "status": "PASS",
            "result": result_attempt2,
            "attempts": 2,
            "timestamp": timestamp_gen.now(),
        }
        file_writer.write(str(feedback_path), feedback_attempt2)

        # Assert: Feedback loop completed successfully
        assert instructions_path.exists()
        assert result_path.exists()
        assert feedback_path.exists()

        final_feedback = json.loads(feedback_path.read_text(encoding="utf-8"))
        assert final_feedback["status"] == "PASS"
        assert final_feedback["attempts"] == 2

    def test_chained_pods_output_becomes_input(self, tmp_path):
        """
        INTEGRATION: Multi-pod chain workflow

        Scenario: Pod1 output → Pod2 input → Pod3 input
        Expected: File-based communication chains pods together
        """
        # Arrange: Create 3 pods
        path_resolver = PathResolver()
        file_writer = FileWriter()
        file_reader = FileReader()

        project_root = path_resolver.get_project_root(tmp_path)
        session_dir = path_resolver.create_session_dir(project_root, "chain-agent")

        pod1_dir = path_resolver.create_pod_dir(session_dir, "pod-extract")
        pod2_dir = path_resolver.create_pod_dir(session_dir, "pod-process")
        pod3_dir = path_resolver.create_pod_dir(session_dir, "pod-format")

        # Act: Pod 1 extracts requirements
        pod1_result = {
            "requirements": ["Auth", "Storage", "API"],
            "status": "PASS",
        }
        pod1_output = pod1_dir / "result.json"
        file_writer.write(str(pod1_output), pod1_result)

        # Pod 2 reads Pod 1 output and processes
        pod1_data = file_reader.read(str(pod1_output))
        pod2_result = {
            "processed_requirements": [f"Process {req}" for req in pod1_data["requirements"]],
            "status": "PASS",
        }
        pod2_output = pod2_dir / "result.json"
        file_writer.write(str(pod2_output), pod2_result)

        # Pod 3 reads Pod 2 output and formats
        pod2_data = file_reader.read(str(pod2_output))
        pod3_result = {
            "formatted_output": "\n".join(pod2_data["processed_requirements"]),
            "status": "PASS",
        }
        pod3_output = pod3_dir / "result.json"
        file_writer.write(str(pod3_output), pod3_result)

        # Assert: Data flowed through all 3 pods
        final_result = file_reader.read(str(pod3_output))
        assert "Process Auth" in final_result["formatted_output"]
        assert "Process Storage" in final_result["formatted_output"]
        assert "Process API" in final_result["formatted_output"]
        assert final_result["status"] == "PASS"
