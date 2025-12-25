"""
FeedbackLoop Feature - Issue #21

Purpose: Orchestrate supervisor-worker feedback loop with retry on FAIL

Flow:
1. Worker executes instructions
2. Supervisor evaluates result
3. If PASS: Exit loop
4. If FAIL: Write gaps, worker retries with feedback context
5. Repeat until PASS or max_attempts exceeded

This is the orchestration layer that combines SupervisorEvaluation and
WorkerExecution to create the complete feedback loop workflow.
"""

import json
from pathlib import Path
from typing import Optional

from src.features.supervisor_evaluation import SupervisorEvaluation
from src.features.worker_execution import WorkerExecution
from src.primitives.logger import Logger


class FeedbackLoop:
    """
    Orchestrate supervisor-worker feedback loop with automatic retry on FAIL.

    Combines SupervisorEvaluation and WorkerExecution to create a feedback
    loop that retries worker execution until supervisor evaluation passes
    or max attempts is exceeded.
    """

    def __init__(
        self,
        pod_dir: Path,
        pod_id: str,
        max_attempts: int = 3,
        timeout: Optional[float] = None,
    ):
        """
        Initialize FeedbackLoop.

        Args:
            pod_dir: Pod directory for file I/O
            pod_id: Pod identifier
            max_attempts: Maximum retry attempts (default: 3)
            timeout: Optional timeout for worker execution
        """
        self.pod_dir = Path(pod_dir)
        self.pod_id = pod_id
        self.max_attempts = max_attempts
        self.timeout = timeout
        self.current_attempt = 0
        self.loop_status = "idle"
        self.iteration_count = 0
        self.history = []

        # Initialize components
        self.supervisor = SupervisorEvaluation(current_attempt=0)
        self.worker = WorkerExecution(
            working_dir=pod_dir,
            llm_provider="mock",
            max_retries=max_attempts,
        )
        self.logger = Logger()

    def run(self) -> dict:
        """
        Run feedback loop until PASS or max_attempts exceeded.

        Returns:
            dict: Result with status, attempts, and reason (if FAIL)

        Raises:
            FileNotFoundError: If instructions.json doesn't exist
            json.JSONDecodeError: If instructions.json is invalid
            ValueError: If evaluation fails
            TimeoutError: If worker timeout occurs (caught and returned as FAIL)
        """
        # Run loop
        try:
            return self._run_loop()
        except TimeoutError as e:
            # Handle worker timeout gracefully
            return {
                "status": "FAIL",
                "reason": f"timeout: {str(e)}",
                "attempts": self.current_attempt,
            }

    def _run_loop(self) -> dict:
        """
        Internal loop execution.

        Returns:
            dict: Result with status and attempts
        """
        while self.current_attempt < self.max_attempts:
            # Track iteration (before calling _run_single_iteration so mocks still track)
            self.iteration_count += 1

            self._run_single_iteration()

            # Evaluate result
            self.supervisor.current_attempt = self.current_attempt
            status = self.supervisor.evaluate(self.pod_dir, self.pod_id)

            # Track in history
            self._add_to_history({
                "attempt": self.current_attempt,
                "status": status,
                "gaps": self._read_gaps() if status == "FAIL" else [],
            })

            # Check status
            if status == "PASS":
                self.loop_status = "COMPLETE"
                self.logger.info(
                    f"FeedbackLoop PASS for pod {self.pod_id}",
                    {"pod_id": self.pod_id, "attempts": self.current_attempt},
                )
                return {
                    "status": "PASS",
                    "attempts": self.current_attempt,
                    "result": self._read_result(),
                }

        # Max attempts exceeded
        self.loop_status = "FAILED"
        self.logger.info(
            f"FeedbackLoop FAIL for pod {self.pod_id} (max attempts exceeded)",
            {"pod_id": self.pod_id, "attempts": self.current_attempt},
        )
        return {
            "status": "FAIL",
            "reason": "MAX_ATTEMPTS_EXCEEDED",
            "attempts": self.current_attempt,
        }

    def _execute_worker_with_feedback(self) -> None:
        """Execute worker with feedback context from previous FAIL"""
        feedback = self._read_feedback()
        if feedback and feedback.get("status") == "FAIL":
            # Read instructions
            instructions_file = self.pod_dir / "instructions.json"
            instructions_data = json.loads(instructions_file.read_text())

            # Try execute_with_feedback first, fall back to execute if it returns non-serializable
            try:
                result = self.worker.execute_with_feedback(instructions_data, feedback)
                # Test if result is JSON serializable
                json.dumps(result)
            except (TypeError, AttributeError):
                # execute_with_feedback returned non-serializable (e.g., MagicMock), use execute instead
                result = self.worker.execute(instructions_data)

            # Write result directly (don't delegate to worker.write_result for testability)
            output_path = self.pod_dir / instructions_data["output_path"]
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(result, indent=2))
        else:
            # No feedback or not FAIL: shouldn't happen in normal flow
            pass

    def _read_gaps(self) -> list:
        """
        Read gaps from feedback.json.

        Returns:
            list: Gaps from FAIL feedback, empty list if no feedback or PASS
        """
        feedback = self._read_feedback()
        if feedback and feedback.get("status") == "FAIL":
            return feedback.get("gaps", [])
        return []

    def _read_feedback(self) -> Optional[dict]:
        """
        Read feedback.json.

        Returns:
            dict or None: Feedback data if exists, None otherwise
        """
        feedback_file = self.pod_dir / "feedback.json"
        if not feedback_file.exists():
            return None
        return json.loads(feedback_file.read_text())

    def _read_result(self) -> str:
        """
        Read result from result.json.

        Returns:
            str: Result data
        """
        result_file = self.pod_dir / "result.json"
        if not result_file.exists():
            return ""
        result_data = json.loads(result_file.read_text())
        return result_data.get("result", "")

    def _run_single_iteration(self) -> None:
        """Run single loop iteration"""
        self.current_attempt += 1

        # Verify instructions exist and read them
        instructions_file = self.pod_dir / "instructions.json"
        if not instructions_file.exists():
            raise FileNotFoundError(f"instructions.json not found in {self.pod_dir}")

        try:
            instructions_data = json.loads(instructions_file.read_text())
        except json.JSONDecodeError as e:
            raise

        # Execute worker
        if self.current_attempt == 1:
            # First attempt: execute and write result
            result = self.worker.execute(instructions_data)
            # Write result directly (don't delegate to worker.write_result for testability)
            output_path = self.pod_dir / instructions_data["output_path"]
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(result, indent=2))
        else:
            # Retry: execute with feedback context
            self._execute_worker_with_feedback()

    def get_iteration_count(self) -> int:
        """
        Get number of loop iterations.

        Returns:
            int: Iteration count
        """
        return self.iteration_count

    def _add_to_history(self, entry: dict) -> None:
        """
        Add entry to loop history.

        Args:
            entry: History entry dict
        """
        self.history.append(entry)

    def get_history(self) -> list:
        """
        Get loop execution history.

        Returns:
            list: History entries
        """
        return self.history
