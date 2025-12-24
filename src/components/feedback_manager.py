"""
FeedbackManager Component - Issue #14

Manages feedback file lifecycle (write PASS/FAIL) in pod directory.

Composition:
- FileWriter (primitive #2) - Atomic write operations
- JSONValidator (primitive #3) - Schema validation
- TimestampGenerator (primitive #7) - ISO 8601 timestamps
"""

from pathlib import Path

from src.primitives.file_writer import FileWriter
from src.primitives.json_validator import JSONValidator
from src.primitives.timestamp_generator import TimestampGenerator


class FeedbackManager:
    """Manage feedback file lifecycle in pod directories"""

    def __init__(self):
        """Initialize FeedbackManager with required primitives"""
        self.file_writer = FileWriter()
        self.validator = JSONValidator()
        self.timestamp_gen = TimestampGenerator()

    def write_pass(self, result: str, attempts: int, pod_dir: Path, pod_id: str) -> str:
        """
        Write PASS feedback to pod directory.

        Args:
            result: The result message
            attempts: Number of attempts taken
            pod_dir: Pod directory path
            pod_id: Pod identifier

        Returns:
            str: Path to written feedback.json file
        """
        data = {
            "status": "PASS",
            "result": result,
            "attempts": attempts,
            "timestamp": self.timestamp_gen.now(),
            "pod_id": pod_id,
        }

        return self._write_feedback(data, pod_dir)

    def write_fail(self, gaps: list[str], attempt: int, pod_dir: Path, pod_id: str) -> str:
        """
        Write FAIL feedback to pod directory.

        Args:
            gaps: List of gap descriptions
            attempt: Current attempt number
            pod_dir: Pod directory path
            pod_id: Pod identifier

        Returns:
            str: Path to written feedback.json file
        """
        data = {
            "status": "FAIL",
            "gaps": gaps,
            "attempt": attempt,
            "timestamp": self.timestamp_gen.now(),
            "pod_id": pod_id,
        }

        return self._write_feedback(data, pod_dir)

    def _write_feedback(self, data: dict, pod_dir: Path) -> str:
        """
        Validate and write feedback data to pod directory.

        Args:
            data: Feedback data dictionary
            pod_dir: Pod directory path

        Returns:
            str: Path to written feedback.json file

        Raises:
            ValueError: If validation fails
        """
        # Validate before writing
        is_valid, errors = self.validator.validate_feedback(data)
        if not is_valid:
            raise ValueError(f"Feedback validation failed: {', '.join(errors)}")

        # Write atomically to pod directory
        feedback_path = str(pod_dir / "feedback.json")
        self.file_writer.write_atomic(feedback_path, data)

        return feedback_path
