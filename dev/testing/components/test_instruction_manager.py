"""
TDD Red-Phase Tests for InstructionManager Component

Issue: #12 - [Sprint 2, Day 1] Component: InstructionManager
Status: RED PHASE - All tests should FAIL (no implementation yet)

Test coverage: 6 tests mapping 1:1 to 6 acceptance criteria

Component: InstructionManager composes 4 primitives:
- AtomicFileWriter (#10)
- JSONValidator (#3)
- TimestampGenerator (#7)
- PathResolver (#9)
"""

import json
import os
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch

import pytest


class TestInstructionManager:
    """Test suite for InstructionManager component - Red Phase"""

    @pytest.fixture
    def temp_project_root(self):
        """Create temporary project root for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create .git marker to simulate project root
            project_root = Path(tmpdir)
            (project_root / ".git").mkdir()
            yield project_root

    @pytest.fixture
    def pod_dir(self, temp_project_root):
        """Create temporary pod directory."""
        pod_dir = temp_project_root / ".agent-harness" / "sessions" / "test-pod"
        pod_dir.mkdir(parents=True)
        return pod_dir

    def test_create_writes_valid_instructions_json_to_pod_dir(self, pod_dir):
        """
        AC1: Creates valid instructions.json in pod directory

        Verifies InstructionManager.create() writes a valid instructions.json
        file to the specified pod directory with correct structure.
        """
        # Arrange
        from src.components.instruction_manager import InstructionManager

        manager = InstructionManager()
        instructions_text = "Write a function to calculate fibonacci numbers"
        session_id = "test-session-001"

        # Act
        file_path = manager.create(
            instructions=instructions_text, pod_dir=pod_dir, session_id=session_id
        )

        # Assert: File exists at expected location
        expected_path = pod_dir / "instructions.json"
        assert Path(file_path) == expected_path
        assert expected_path.exists()

        # Assert: File contains valid JSON
        with open(expected_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Assert: JSON has required fields
        assert "instructions" in data
        assert data["instructions"] == instructions_text
        assert "output_path" in data
        assert data["output_path"] == "result.json"

    def test_create_validates_schema_before_writing(self, pod_dir):
        """
        AC2: Validates before writing

        Verifies InstructionManager validates instruction schema before
        writing to file, preventing invalid data from being persisted.
        """
        # Arrange
        from src.components.instruction_manager import InstructionManager

        manager = InstructionManager()

        # Act & Assert: Empty instructions should raise ValueError
        with pytest.raises(ValueError, match="instructions.*empty|required"):
            manager.create(instructions="", pod_dir=pod_dir, session_id="test-session")

        # Assert: File should NOT be created
        instructions_file = pod_dir / "instructions.json"
        assert not instructions_file.exists(), "Validation failure should prevent file creation"

    def test_create_includes_all_required_metadata(self, pod_dir, temp_project_root):
        """
        AC3: Includes correct metadata (pod_id, session_id, project_root, timestamp)

        Verifies InstructionManager enriches instructions with all required
        metadata fields before writing.
        """
        # Arrange
        from src.components.instruction_manager import InstructionManager

        manager = InstructionManager()
        instructions_text = "Test instruction"
        session_id = "test-session-123"

        # Act
        file_path = manager.create(
            instructions=instructions_text, pod_dir=pod_dir, session_id=session_id
        )

        # Assert: Read created file
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Assert: All metadata fields present
        assert "pod_id" in data, "Missing pod_id metadata"
        assert "session_id" in data, "Missing session_id metadata"
        assert "project_root" in data, "Missing project_root metadata"
        assert "timestamp" in data, "Missing timestamp metadata"

        # Assert: Metadata values correct
        assert data["session_id"] == session_id
        assert data["pod_id"] == pod_dir.name  # Derived from pod directory name
        assert data["project_root"] == str(
            temp_project_root
        )  # From PathResolver.get_project_root()

        # Assert: Timestamp in ISO 8601 format
        import re

        iso8601_pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.*Z$"
        assert re.match(iso8601_pattern, data["timestamp"]), "Timestamp not in ISO 8601 format"

    def test_create_uses_atomic_write_no_partial_files(self, pod_dir):
        """
        AC4: Atomic writes (no partial files visible)

        Verifies InstructionManager uses AtomicFileWriter to ensure
        no partial files are visible during write operations.
        """
        # Arrange
        from src.components.instruction_manager import InstructionManager

        manager = InstructionManager()
        instructions_text = "Test atomic write"
        session_id = "test-session"

        # Act
        file_path = manager.create(
            instructions=instructions_text, pod_dir=pod_dir, session_id=session_id
        )

        # Assert: Final file exists and is complete
        assert Path(file_path).exists()
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)  # Should not raise (indicates complete, valid JSON)

        # Assert: No temp files left behind
        temp_files = list(pod_dir.glob("*.tmp"))
        assert len(temp_files) == 0, f"Temp files left behind: {temp_files}"

        # Assert: All expected fields present (indicates complete write)
        required_fields = ["instructions", "output_path", "pod_id", "session_id", "timestamp"]
        for field in required_fields:
            assert field in data, f"Missing field '{field}' - indicates partial write"

    def test_create_handles_write_failures_gracefully(self, temp_project_root):
        """
        AC5: Handles write failures gracefully

        Verifies InstructionManager handles write failures (permissions, disk full)
        without leaving partial files or corrupt state.
        """
        # Arrange
        from src.components.instruction_manager import InstructionManager

        manager = InstructionManager()

        # Create read-only pod directory
        readonly_dir = temp_project_root / "readonly-pod"
        readonly_dir.mkdir()
        os.chmod(readonly_dir, 0o444)  # Read-only

        try:
            # Act & Assert: Should raise appropriate exception
            with pytest.raises((IOError, PermissionError, OSError)):
                manager.create(
                    instructions="Test instruction", pod_dir=readonly_dir, session_id="test"
                )

            # Assert: No files created despite failure
            files_in_dir = list(readonly_dir.iterdir())
            assert len(files_in_dir) == 0, f"Files created despite permission error: {files_in_dir}"
        finally:
            # Cleanup: Restore permissions for deletion
            os.chmod(readonly_dir, 0o755)

    def test_concurrent_pods_isolated_directories(self, temp_project_root):
        """
        AC6: Concurrent pods don't collide (isolated directories)

        Verifies InstructionManager correctly isolates concurrent pod operations,
        ensuring no cross-contamination of instruction files.
        """
        # Arrange
        from src.components.instruction_manager import InstructionManager

        manager = InstructionManager()

        # Create two separate pod directories
        pod_a_dir = temp_project_root / ".agent-harness" / "sessions" / "pod-a"
        pod_b_dir = temp_project_root / ".agent-harness" / "sessions" / "pod-b"
        pod_a_dir.mkdir(parents=True)
        pod_b_dir.mkdir(parents=True)

        # Prepare different instructions
        instructions_a = "Pod A: Calculate fibonacci sequence"
        instructions_b = "Pod B: Sort array of integers"

        results = {}

        def create_instruction(pod_name, pod_dir, instructions, session_id):
            """Helper to create instruction in thread."""
            file_path = manager.create(
                instructions=instructions, pod_dir=pod_dir, session_id=session_id
            )
            results[pod_name] = file_path

        # Act: Create instructions concurrently
        thread_a = threading.Thread(
            target=create_instruction, args=("A", pod_a_dir, instructions_a, "session-a")
        )
        thread_b = threading.Thread(
            target=create_instruction, args=("B", pod_b_dir, instructions_b, "session-b")
        )

        thread_a.start()
        thread_b.start()
        thread_a.join()
        thread_b.join()

        # Assert: Both files exist in correct directories
        file_a = Path(results["A"])
        file_b = Path(results["B"])
        assert file_a.exists()
        assert file_b.exists()
        assert file_a.parent == pod_a_dir
        assert file_b.parent == pod_b_dir

        # Assert: Each file has correct content (no cross-contamination)
        with open(file_a, "r", encoding="utf-8") as f:
            data_a = json.load(f)
        with open(file_b, "r", encoding="utf-8") as f:
            data_b = json.load(f)

        assert data_a["instructions"] == instructions_a
        assert data_b["instructions"] == instructions_b
        assert data_a["session_id"] == "session-a"
        assert data_b["session_id"] == "session-b"
        assert data_a["pod_id"] == "pod-a"
        assert data_b["pod_id"] == "pod-b"

    def test_normalize_path_handles_non_private_var_paths(self, pod_dir):
        """
        Test _normalize_path() returns unchanged path for non-macOS /private/var paths.

        Covers line 51: return path_str (the non-/private/var/ code path)
        """
        # Arrange
        from src.components.instruction_manager import InstructionManager

        manager = InstructionManager()

        # Act - Test various paths that don't start with /private/var/
        regular_path = Path("/Users/test/project")
        normalized = manager._normalize_path(regular_path)

        # Assert - Should return unchanged
        assert normalized == "/Users/test/project"

        # Additional test cases
        assert manager._normalize_path(Path("/tmp/test")) == "/tmp/test"
        assert manager._normalize_path(Path("/home/user")) == "/home/user"

    def test_create_with_invalid_json_schema_raises_detailed_error(self, pod_dir):
        """
        Test create() with data that fails JSONValidator schema validation.

        Covers lines 106-107: validation failure error path with error_details
        """
        # Arrange
        from src.components.instruction_manager import InstructionManager
        from unittest.mock import patch

        manager = InstructionManager()

        # Mock validator to return validation failure with multiple errors
        with patch.object(manager.validator, "validate_instructions") as mock_validate:
            mock_validate.return_value = (False, ["Missing field: foo", "Invalid type: bar"])

            # Act & Assert - Should raise ValueError with joined error details
            with pytest.raises(
                ValueError, match="Instruction validation failed:.*Missing field: foo.*Invalid type: bar"
            ):
                manager.create(
                    instructions="Valid text",
                    pod_dir=pod_dir,
                    session_id="test-session",
                )
