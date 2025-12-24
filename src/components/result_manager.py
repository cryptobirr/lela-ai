"""
ResultManager Component

Manages result file lifecycle (read, write, validate) with worker isolation.

Composes:
- FileReader (primitive)
- AtomicFileWriter (primitive) -> Actually FileWriter
- JSONValidator (primitive)
- PathResolver (primitive)

Issue: #13 - [Sprint 2, Day 1] Component: ResultManager
TDD Phase: GREEN - Minimal implementation to pass tests
"""

import json
from pathlib import Path

from src.primitives.file_reader import FileReader
from src.primitives.file_writer import FileWriter
from src.primitives.json_validator import JSONValidator
from src.primitives.timestamp_generator import TimestampGenerator

# Alias for tests that expect AtomicFileWriter
AtomicFileWriter = FileWriter


class ResultManager:
    """Manages result file lifecycle with worker isolation."""

    def __init__(self):
        """Initialize ResultManager with required primitives."""
        self.reader = FileReader()
        self.validator = JSONValidator()
        self.timestamp_gen = TimestampGenerator()
        self._writer = None

    @property
    def writer(self):
        """Lazy-load writer to allow test mocking."""
        if self._writer is None:
            self._writer = AtomicFileWriter()
        return self._writer

    def read(self, file_path: str) -> dict:
        """
        Read result.json file and return its contents.

        Args:
            file_path: Path to result.json file

        Returns:
            dict: Result data

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If result structure is invalid
        """
        # Read the file
        data = self.reader.read(file_path)

        # Validate structure
        is_valid, errors = self.validator.validate_result(data)
        if not is_valid:
            raise ValueError(f"Invalid result structure: {'; '.join(errors)}")

        return data

    def write(
        self, result: str, worker_dir: Path, worker_id: str, pod_id: str, session_id: str
    ) -> str:
        """
        Write result.json file in worker-specific directory.

        Args:
            result: Result content
            worker_dir: Path to worker directory
            worker_id: Worker identifier
            pod_id: Pod identifier
            session_id: Session identifier

        Returns:
            str: Path to created result.json file

        Raises:
            ValueError: If result is invalid
        """
        # Validate result is not empty
        if not result:
            raise ValueError("Invalid result: result cannot be empty")

        # Build result data with metadata
        timestamp = self.timestamp_gen.now()
        data = {
            "result": result,
            "worker_id": worker_id,
            "pod_id": pod_id,
            "session_id": session_id,
            "timestamp": timestamp,
        }

        # Write atomically to result.json
        file_path = worker_dir / "result.json"
        self.writer.write(str(file_path), data)

        return str(file_path)

    def validate_file(self, file_path: str) -> tuple[bool, list[str]]:
        """
        Validate result.json file structure.

        Args:
            file_path: Path to result.json file

        Returns:
            tuple[bool, list[str]]: (is_valid, error_messages)
        """
        # Read the file
        try:
            data = self.reader.read(file_path)
        except (FileNotFoundError, json.JSONDecodeError):
            return (False, ["File not found or invalid JSON"])

        # Check for required metadata fields
        required_fields = ["result", "worker_id", "pod_id", "session_id", "timestamp"]
        errors = []

        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")

        if errors:
            return (False, errors)

        return (True, [])

    def aggregate_worker_results(self, pod_dir: Path) -> list[dict]:
        """
        Aggregate results from all workers in pod.

        Args:
            pod_dir: Path to pod directory

        Returns:
            list[dict]: List of worker results
        """
        workers_dir = pod_dir / "workers"

        # If workers directory doesn't exist, return empty list
        if not workers_dir.exists():
            return []

        results = []

        # Iterate through worker directories
        for worker_dir in workers_dir.iterdir():
            if not worker_dir.is_dir():
                continue

            result_file = worker_dir / "result.json"

            # Skip workers without result.json
            if not result_file.exists():
                continue

            # Read result
            try:
                data = self.reader.read(str(result_file))
                results.append(data)
            except Exception:
                # Skip workers with invalid result files
                continue

        return results
