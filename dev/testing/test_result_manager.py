"""
Test suite for ResultManager Component

Purpose: Verify result file lifecycle management with worker isolation

Test Coverage:
- Happy path: Read/write valid result.json files
- Edge cases: Missing files, empty results, multiple workers
- Error handling: Invalid paths, malformed JSON, write failures

Requirements tested: Issue #13 - ResultManager component
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from src.components.result_manager import ResultManager


class TestResultManagerRead:
    """Test reading result.json files from worker directories."""

    def test_read_valid_result_file_returns_dict(self, tmp_path):
        """Read a valid result.json and return its contents as dict."""
        # Arrange
        worker_dir = tmp_path / "workers" / "worker-001"
        worker_dir.mkdir(parents=True)
        result_file = worker_dir / "result.json"
        expected_data = {
            "result": "task completed",
            "worker_id": "worker-001",
            "metadata": {"timestamp": "2025-12-24T00:00:00Z"},
        }
        result_file.write_text(json.dumps(expected_data))
        manager = ResultManager()

        # Act
        result = manager.read(str(result_file))

        # Assert
        assert result == expected_data
        assert result["result"] == "task completed"

    def test_read_validates_file_structure_before_returning(self, tmp_path):
        """Read operation validates JSON structure before returning data."""
        # Arrange
        worker_dir = tmp_path / "workers" / "worker-001"
        worker_dir.mkdir(parents=True)
        result_file = worker_dir / "result.json"
        # Invalid structure - missing required 'result' field
        invalid_data = {"worker_id": "worker-001"}
        result_file.write_text(json.dumps(invalid_data))
        manager = ResultManager()

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid result structure"):
            manager.read(str(result_file))

    def test_read_nonexistent_file_raises_file_not_found(self, tmp_path):
        """Reading non-existent result.json raises FileNotFoundError."""
        # Arrange
        nonexistent_file = tmp_path / "workers" / "worker-999" / "result.json"
        manager = ResultManager()

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            manager.read(str(nonexistent_file))


class TestResultManagerWrite:
    """Test writing result.json files to worker directories."""

    def test_write_creates_result_file_in_worker_directory(self, tmp_path):
        """Write creates result.json in correct worker-specific directory."""
        # Arrange
        worker_dir = tmp_path / "workers" / "worker-001"
        result_content = "analysis complete"
        manager = ResultManager()

        # Act
        file_path = manager.write(
            result=result_content,
            worker_dir=worker_dir,
            worker_id="worker-001",
            pod_id="pod-123",
            session_id="session-456",
        )

        # Assert
        assert Path(file_path).exists()
        assert Path(file_path).name == "result.json"
        assert Path(file_path).parent == worker_dir

    def test_write_includes_all_required_metadata(self, tmp_path):
        """Write includes worker_id, pod_id, session_id, and timestamp."""
        # Arrange
        worker_dir = tmp_path / "workers" / "worker-001"
        result_content = "task done"
        manager = ResultManager()

        # Act
        file_path = manager.write(
            result=result_content,
            worker_dir=worker_dir,
            worker_id="worker-001",
            pod_id="pod-123",
            session_id="session-456",
        )

        # Assert
        with open(file_path, "r") as f:
            data = json.load(f)
        assert data["worker_id"] == "worker-001"
        assert data["pod_id"] == "pod-123"
        assert data["session_id"] == "session-456"
        assert "timestamp" in data
        assert data["result"] == result_content

    def test_write_performs_atomic_write_operation(self, tmp_path):
        """Write uses atomic write (temp file + rename) to prevent partial files."""
        # Arrange
        worker_dir = tmp_path / "workers" / "worker-001"
        result_content = "atomic test"
        manager = ResultManager()

        # Act
        with patch("src.components.result_manager.AtomicFileWriter") as mock_writer:
            mock_writer.return_value.write.return_value = str(worker_dir / "result.json")
            file_path = manager.write(
                result=result_content,
                worker_dir=worker_dir,
                worker_id="worker-001",
                pod_id="pod-123",
                session_id="session-456",
            )

            # Assert
            mock_writer.return_value.write.assert_called_once()

    def test_write_validates_before_writing(self, tmp_path):
        """Write validates result structure before writing to disk."""
        # Arrange
        worker_dir = tmp_path / "workers" / "worker-001"
        # Empty result should fail validation
        invalid_result = ""
        manager = ResultManager()

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid result"):
            manager.write(
                result=invalid_result,
                worker_dir=worker_dir,
                worker_id="worker-001",
                pod_id="pod-123",
                session_id="session-456",
            )


class TestResultManagerValidation:
    """Test validation of result.json file structure."""

    def test_validate_file_returns_true_for_valid_structure(self, tmp_path):
        """Validate returns (True, []) for correctly structured result.json."""
        # Arrange
        worker_dir = tmp_path / "workers" / "worker-001"
        worker_dir.mkdir(parents=True)
        result_file = worker_dir / "result.json"
        valid_data = {
            "result": "completed",
            "worker_id": "worker-001",
            "pod_id": "pod-123",
            "session_id": "session-456",
            "timestamp": "2025-12-24T00:00:00Z",
        }
        result_file.write_text(json.dumps(valid_data))
        manager = ResultManager()

        # Act
        is_valid, errors = manager.validate_file(str(result_file))

        # Assert
        assert is_valid is True
        assert errors == []

    def test_validate_file_returns_false_with_errors_for_invalid_structure(self, tmp_path):
        """Validate returns (False, [errors]) for missing required fields."""
        # Arrange
        worker_dir = tmp_path / "workers" / "worker-001"
        worker_dir.mkdir(parents=True)
        result_file = worker_dir / "result.json"
        # Missing required fields
        invalid_data = {"result": "incomplete"}
        result_file.write_text(json.dumps(invalid_data))
        manager = ResultManager()

        # Act
        is_valid, errors = manager.validate_file(str(result_file))

        # Assert
        assert is_valid is False
        assert len(errors) > 0
        assert any("worker_id" in err for err in errors)


class TestResultManagerAggregation:
    """Test aggregating results from multiple workers in a pod."""

    def test_aggregate_worker_results_returns_all_worker_results(self, tmp_path):
        """Aggregate reads result.json from all workers in pod directory."""
        # Arrange
        pod_dir = tmp_path / "pod-123"
        workers = ["worker-001", "worker-002", "worker-003"]

        for worker_id in workers:
            worker_dir = pod_dir / "workers" / worker_id
            worker_dir.mkdir(parents=True)
            result_file = worker_dir / "result.json"
            result_data = {
                "result": f"{worker_id} completed",
                "worker_id": worker_id,
                "pod_id": "pod-123",
            }
            result_file.write_text(json.dumps(result_data))

        manager = ResultManager()

        # Act
        aggregated = manager.aggregate_worker_results(pod_dir)

        # Assert
        assert len(aggregated) == 3
        worker_ids = [r["worker_id"] for r in aggregated]
        assert set(worker_ids) == set(workers)

    def test_aggregate_handles_missing_worker_results_gracefully(self, tmp_path):
        """Aggregate skips workers with missing result.json files."""
        # Arrange
        pod_dir = tmp_path / "pod-123"
        # Worker 1 has result
        worker1_dir = pod_dir / "workers" / "worker-001"
        worker1_dir.mkdir(parents=True)
        result1_file = worker1_dir / "result.json"
        result1_file.write_text(json.dumps({"result": "done", "worker_id": "worker-001"}))

        # Worker 2 directory exists but no result.json
        worker2_dir = pod_dir / "workers" / "worker-002"
        worker2_dir.mkdir(parents=True)

        manager = ResultManager()

        # Act
        aggregated = manager.aggregate_worker_results(pod_dir)

        # Assert
        # Should return only worker-001's result, skip worker-002
        assert len(aggregated) == 1
        assert aggregated[0]["worker_id"] == "worker-001"

    def test_aggregate_returns_empty_list_when_no_workers_exist(self, tmp_path):
        """Aggregate returns [] when pod has no workers directory."""
        # Arrange
        pod_dir = tmp_path / "pod-empty"
        pod_dir.mkdir()
        manager = ResultManager()

        # Act
        aggregated = manager.aggregate_worker_results(pod_dir)

        # Assert
        assert aggregated == []


class TestResultManagerConcurrency:
    """Test concurrent worker isolation and collision prevention."""

    def test_concurrent_workers_write_to_isolated_directories(self, tmp_path):
        """Multiple workers writing simultaneously don't collide (isolated dirs)."""
        # Arrange
        pod_dir = tmp_path / "pod-123"
        worker_ids = ["worker-001", "worker-002", "worker-003"]
        manager = ResultManager()

        # Act - Simulate concurrent writes
        file_paths = []
        for worker_id in worker_ids:
            worker_dir = pod_dir / "workers" / worker_id
            file_path = manager.write(
                result=f"{worker_id} result",
                worker_dir=worker_dir,
                worker_id=worker_id,
                pod_id="pod-123",
                session_id="session-456",
            )
            file_paths.append(Path(file_path))

        # Assert - All files exist in separate directories
        assert len(file_paths) == 3
        parent_dirs = [fp.parent for fp in file_paths]
        assert len(set(parent_dirs)) == 3  # All in different directories

        # Verify each file contains correct worker_id
        for worker_id, file_path in zip(worker_ids, file_paths):
            with open(file_path, "r") as f:
                data = json.load(f)
            assert data["worker_id"] == worker_id
