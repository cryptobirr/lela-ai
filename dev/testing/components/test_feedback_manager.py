"""
TDD Red-Phase Tests for FeedbackManager Component

Issue: #14 - [Sprint 2, Day 2] Component: FeedbackManager
Status: RED PHASE - All tests should FAIL (no implementation yet)

Test coverage: 6 tests mapping 1:1 to 6 acceptance criteria

Component: FeedbackManager composes 3 primitives:
- FileWriter (#2) - Atomic write operations
- JSONValidator (#3) - Schema validation
- TimestampGenerator (#7) - ISO 8601 timestamps
"""

import json
import os
import tempfile
import threading
from pathlib import Path

import pytest


class TestFeedbackManager:
    """Test suite for FeedbackManager component - Red Phase"""

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

    def test_write_pass_creates_valid_feedback_in_pod_dir(self, pod_dir):
        """
        AC1: Writes valid PASS feedback in pod directory

        Verifies FeedbackManager.write_pass() writes a valid feedback.json
        file with PASS status to the specified pod directory.
        """
        # Arrange
        from src.components.feedback_manager import FeedbackManager

        manager = FeedbackManager()
        result = "Implementation successful - all tests pass"
        attempts = 3
        pod_id = "test-pod"

        # Act
        file_path = manager.write_pass(
            result=result, attempts=attempts, pod_dir=pod_dir, pod_id=pod_id
        )

        # Assert: File exists at expected location
        expected_path = pod_dir / "feedback.json"
        assert Path(file_path) == expected_path
        assert expected_path.exists()

        # Assert: File contains valid JSON
        with open(expected_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Assert: JSON has required PASS fields
        assert data["status"] == "PASS"
        assert data["result"] == result
        assert data["attempts"] == attempts
        assert "timestamp" in data
        assert data["pod_id"] == pod_id

    def test_write_fail_creates_valid_feedback_in_pod_dir(self, pod_dir):
        """
        AC2: Writes valid FAIL feedback in pod directory

        Verifies FeedbackManager.write_fail() writes a valid feedback.json
        file with FAIL status to the specified pod directory.
        """
        # Arrange
        from src.components.feedback_manager import FeedbackManager

        manager = FeedbackManager()
        gaps = [
            "Missing validation for empty input",
            "Error handling incomplete for network failures",
            "Edge case not covered: negative numbers",
        ]
        attempt = 2
        pod_id = "test-pod"

        # Act
        file_path = manager.write_fail(
            gaps=gaps, attempt=attempt, pod_dir=pod_dir, pod_id=pod_id
        )

        # Assert: File exists at expected location
        expected_path = pod_dir / "feedback.json"
        assert Path(file_path) == expected_path
        assert expected_path.exists()

        # Assert: File contains valid JSON
        with open(expected_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Assert: JSON has required FAIL fields
        assert data["status"] == "FAIL"
        assert data["gaps"] == gaps
        assert data["attempt"] == attempt
        assert "timestamp" in data
        assert data["pod_id"] == pod_id

    def test_write_pass_includes_all_required_fields(self, pod_dir):
        """
        AC3: Includes all required fields (status, result/gaps, attempts/attempt, timestamp, pod_id)

        Verifies FeedbackManager includes ALL required metadata fields in
        PASS feedback, and validates timestamp format.
        """
        # Arrange
        from src.components.feedback_manager import FeedbackManager

        manager = FeedbackManager()
        result = "Test result data"
        attempts = 1
        pod_id = "pod-123"

        # Act
        file_path = manager.write_pass(
            result=result, attempts=attempts, pod_dir=pod_dir, pod_id=pod_id
        )

        # Assert: Read created file
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Assert: All required fields present
        required_fields = ["status", "result", "attempts", "timestamp", "pod_id"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Assert: Field values correct
        assert data["status"] == "PASS"
        assert data["result"] == result
        assert data["attempts"] == attempts
        assert data["pod_id"] == pod_id

        # Assert: Timestamp in ISO 8601 format with Z suffix
        import re

        iso8601_pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z$"
        assert re.match(
            iso8601_pattern, data["timestamp"]
        ), f"Timestamp '{data['timestamp']}' not in ISO 8601 format (YYYY-MM-DDTHH:MM:SS.ffffffZ)"

    def test_validates_before_writing(self, pod_dir):
        """
        AC4: Validates before writing

        Verifies FeedbackManager validates feedback schema before writing,
        preventing invalid data from being persisted.
        """
        # Arrange
        from src.components.feedback_manager import FeedbackManager

        manager = FeedbackManager()

        # Act & Assert: Invalid PASS (missing result) should raise ValueError
        with pytest.raises(ValueError, match="result.*required|validation failed"):
            # Attempt to write PASS feedback without result field
            # This should fail validation before file write
            manager._write_feedback(
                data={"status": "PASS", "attempts": 1, "timestamp": "2024-01-01T00:00:00.000000Z"},
                pod_dir=pod_dir,
            )

        # Act & Assert: Invalid FAIL (empty gaps) should raise ValueError
        with pytest.raises(ValueError, match="gaps.*required|validation failed"):
            # Attempt to write FAIL feedback with empty gaps
            manager._write_feedback(
                data={
                    "status": "FAIL",
                    "gaps": [],  # Invalid: must have at least 1 gap
                    "attempt": 1,
                    "timestamp": "2024-01-01T00:00:00.000000Z",
                },
                pod_dir=pod_dir,
            )

        # Assert: No files should be created due to validation failures
        feedback_file = pod_dir / "feedback.json"
        assert not feedback_file.exists(), "Validation failure should prevent file creation"

    def test_uses_atomic_write_no_partial_files(self, pod_dir):
        """
        AC5: Atomic writes (no partial files visible)

        Verifies FeedbackManager uses FileWriter.write_atomic() to ensure
        no partial feedback files are visible during write operations.
        """
        # Arrange
        from src.components.feedback_manager import FeedbackManager

        manager = FeedbackManager()
        result = "Test atomic write behavior"
        attempts = 1
        pod_id = "test-pod"

        # Act
        file_path = manager.write_pass(
            result=result, attempts=attempts, pod_dir=pod_dir, pod_id=pod_id
        )

        # Assert: Final file exists and is complete
        assert Path(file_path).exists()
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)  # Should not raise (indicates complete, valid JSON)

        # Assert: No temp files left behind
        temp_files = list(pod_dir.glob("*.tmp"))
        temp_files += list(pod_dir.glob(".*tmp"))  # Hidden temp files
        temp_files += list(pod_dir.glob(".feedback.json.*"))  # Temp file pattern
        assert len(temp_files) == 0, f"Temp files left behind: {temp_files}"

        # Assert: All expected fields present (indicates complete write)
        required_fields = ["status", "result", "attempts", "timestamp", "pod_id"]
        for field in required_fields:
            assert field in data, f"Missing field '{field}' - indicates partial write"

    def test_concurrent_pods_isolated_directories(self, temp_project_root):
        """
        AC6: Concurrent pods don't collide (isolated directories)

        Verifies FeedbackManager correctly isolates concurrent pod operations,
        ensuring no cross-contamination of feedback files.
        """
        # Arrange
        from src.components.feedback_manager import FeedbackManager

        manager = FeedbackManager()

        # Create two separate pod directories
        pod_a_dir = temp_project_root / ".agent-harness" / "sessions" / "pod-a"
        pod_b_dir = temp_project_root / ".agent-harness" / "sessions" / "pod-b"
        pod_a_dir.mkdir(parents=True)
        pod_b_dir.mkdir(parents=True)

        # Prepare different feedback data
        result_a = "Pod A: All tests passed successfully"
        result_b = "Pod B: Implementation complete"
        attempts_a = 2
        attempts_b = 1

        results = {}

        def write_pass_feedback(pod_name, pod_dir, result, attempts, pod_id):
            """Helper to write PASS feedback in thread."""
            file_path = manager.write_pass(
                result=result, attempts=attempts, pod_dir=pod_dir, pod_id=pod_id
            )
            results[pod_name] = file_path

        # Act: Write feedback concurrently
        thread_a = threading.Thread(
            target=write_pass_feedback, args=("A", pod_a_dir, result_a, attempts_a, "pod-a")
        )
        thread_b = threading.Thread(
            target=write_pass_feedback, args=("B", pod_b_dir, result_b, attempts_b, "pod-b")
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

        assert data_a["status"] == "PASS"
        assert data_b["status"] == "PASS"
        assert data_a["result"] == result_a
        assert data_b["result"] == result_b
        assert data_a["attempts"] == attempts_a
        assert data_b["attempts"] == attempts_b
        assert data_a["pod_id"] == "pod-a"
        assert data_b["pod_id"] == "pod-b"

        # Assert: Timestamps are present and valid
        import re

        iso8601_pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z$"
        assert re.match(iso8601_pattern, data_a["timestamp"])
        assert re.match(iso8601_pattern, data_b["timestamp"])
