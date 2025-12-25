"""
SupervisorEvaluation Feature - Issue #19

Purpose: Complete supervisor evaluation logic (binary PASS/FAIL)

Composition:
- RequirementComparator (component #16)
- FeedbackManager (component #14)

Business Logic:
- Read instructions and result
- Compare using RequirementComparator
- Write feedback (PASS or FAIL with gaps)
- Track attempt count
- No partial credit (binary evaluation)
"""

import json
from pathlib import Path
from typing import Optional

from src.components.requirement_comparator import RequirementComparator
from src.components.feedback_manager import FeedbackManager
from src.primitives.logger import Logger


class SupervisorEvaluation:
    """
    Binary supervisor evaluation (PASS/FAIL only).

    Reads instructions and result, evaluates using RequirementComparator,
    writes feedback via FeedbackManager, and tracks evaluation history.
    """

    def __init__(self, current_attempt: int = 0):
        """
        Initialize SupervisorEvaluation.

        Args:
            current_attempt: Number of previous attempts (default: 0 for first attempt)
        """
        self.comparator = RequirementComparator()
        self.feedback_manager = FeedbackManager()
        self.logger = Logger()
        self.current_attempt = current_attempt
        self.evaluation_history: list[dict] = []

    def evaluate(self, pod_dir: Path, pod_id: str) -> str:
        """
        Evaluate result against instructions.

        Args:
            pod_dir: Pod directory containing instructions.json and result.json
            pod_id: Pod identifier

        Returns:
            str: "PASS" or "FAIL"

        Raises:
            FileNotFoundError: If instructions.json doesn't exist
            ValueError: If instructions.json is malformed
            json.JSONDecodeError: If instructions.json contains invalid JSON
        """
        # Read instructions
        instructions_file = pod_dir / "instructions.json"
        if not instructions_file.exists():
            raise FileNotFoundError(f"Instructions file not found: {instructions_file}")

        try:
            instructions_data = json.loads(instructions_file.read_text())
        except json.JSONDecodeError as e:
            raise ValueError(f"Malformed instructions file: {e}")

        instructions = instructions_data.get("instructions", "")

        # Read result (handle missing file gracefully)
        result_file = pod_dir / "result.json"
        result: Optional[str] = None

        if result_file.exists():
            result_data = json.loads(result_file.read_text())
            result = result_data.get("result", "")

        # Evaluate using comparator
        status, gaps = self.comparator.evaluate(instructions, result)

        # Write feedback based on status
        if status == "PASS":
            # PASS: write total attempts
            # If current_attempt=0 (default), this is attempt 1
            # If current_attempt=N (explicit), this is attempt N
            attempts = self.current_attempt if self.current_attempt > 0 else 1

            self.feedback_manager.write_pass(
                result=result or "",
                attempts=attempts,
                pod_dir=pod_dir,
                pod_id=pod_id
            )
            self.logger.info(
                f"Evaluation PASS for pod {pod_id}",
                {"status": status, "pod_id": pod_id, "attempts": attempts}
            )
        else:
            # FAIL: write next attempt number
            # Always increment: current_attempt + 1
            next_attempt = self.current_attempt + 1

            self.feedback_manager.write_fail(
                gaps=gaps,
                attempt=next_attempt,
                pod_dir=pod_dir,
                pod_id=pod_id
            )
            self.logger.info(
                f"Evaluation FAIL for pod {pod_id}",
                {"status": status, "pod_id": pod_id, "gaps": gaps, "attempt": next_attempt}
            )

        # Track evaluation in history
        from src.primitives.timestamp_generator import TimestampGenerator
        timestamp_gen = TimestampGenerator()

        history_entry = {
            "status": status,
            "pod_id": pod_id,
            "timestamp": timestamp_gen.now(),
            "instructions": instructions,
            "result": result,
            "gaps": gaps if status == "FAIL" else []
        }
        self.evaluation_history.append(history_entry)

        return status

    def get_current_attempt(self) -> int:
        """
        Get current attempt count.

        Returns:
            int: Current attempt number
        """
        return self.current_attempt
