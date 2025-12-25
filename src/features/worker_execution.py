"""
WorkerExecution Feature - Complete worker execution flow

Issue: #20 - [Sprint 3, Day 2] Feature: WorkerExecution
Status: GREEN PHASE - Minimal implementation to pass tests

Purpose:
Execute complete worker lifecycle: read instructions, execute with LLM, write result,
handle feedback, support retries, and manage state.

This is the orchestration layer that combines components to create the full worker execution workflow.
"""

import json
import time
from pathlib import Path
from typing import Optional


class WorkerExecution:
    """Orchestrate complete worker execution flow with feedback loop"""

    def __init__(
        self,
        working_dir: Path,
        llm_provider: str = "mock",
        max_retries: int = 5,
        poll_interval: float = 1.0,
        worker_id: Optional[str] = None,
    ):
        """
        Initialize WorkerExecution

        Args:
            working_dir: Working directory for file I/O
            llm_provider: LLM provider name (openai, anthropic, mock)
            max_retries: Maximum retry attempts on FAIL feedback
            poll_interval: Polling interval in seconds
            worker_id: Optional worker identifier
        """
        self.working_dir = Path(working_dir)
        self.llm_provider = llm_provider
        self.max_retries = max_retries
        self.poll_interval = poll_interval
        self.worker_id = worker_id
        self.execution_status = "idle"
        self.execution_history = []

    def read_instructions(self) -> dict:
        """
        Read instructions.json from working directory

        Returns:
            dict: Instructions data

        Raises:
            FileNotFoundError: If instructions.json doesn't exist
            json.JSONDecodeError: If JSON is invalid
            ValueError: If required fields are missing
        """
        instructions_file = self.working_dir / "instructions.json"

        if not instructions_file.exists():
            raise FileNotFoundError(f"Instructions file not found: {instructions_file}")

        content = instructions_file.read_text()
        data = json.loads(content)

        # Validate required fields
        if "instructions" not in data:
            raise ValueError("Missing required field: instructions")

        return data

    def execute(self, instructions: dict) -> dict:
        """
        Execute instructions using configured LLM provider

        Args:
            instructions: Instructions dictionary with 'instructions' and 'output_path'

        Returns:
            dict: Result with 'result' key

        Raises:
            Exception: If LLM execution fails
        """
        instruction_text = instructions["instructions"]
        result_text = self._call_llm(instruction_text)
        return result_text

    def _call_llm(self, prompt: str) -> dict:
        """
        Call LLM provider with prompt (minimal mock implementation)

        Args:
            prompt: Prompt text

        Returns:
            dict: Result with 'result' key
        """
        # Minimal implementation for tests to pass
        return {"result": f"Mock LLM response to: {prompt}"}

    def write_result(self, result_data: dict, output_path: str) -> None:
        """
        Write result to JSON file

        Args:
            result_data: Result data to write
            output_path: Output file path (relative to working_dir)

        Raises:
            PermissionError: If write permission is denied
        """
        output_file = self.working_dir / output_path

        # Create parent directories
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Write JSON
        output_file.write_text(json.dumps(result_data, indent=2))

    def read_feedback(self) -> Optional[dict]:
        """
        Read feedback.json from working directory

        Returns:
            dict or None: Feedback data if file exists, None otherwise
        """
        feedback_file = self.working_dir / "feedback.json"

        if not feedback_file.exists():
            return None

        content = feedback_file.read_text()
        return json.loads(content)

    def execute_with_feedback(self, instructions: dict, feedback: dict) -> dict:
        """
        Execute with feedback context (for retries)

        Args:
            instructions: Original instructions
            feedback: Feedback from supervisor with gaps

        Returns:
            dict: Execution result
        """
        # Build enhanced prompt with gap context
        gaps = feedback.get("gaps", [])
        gap_context = "\n".join(f"- {gap}" for gap in gaps)
        enhanced_prompt = f"{instructions['instructions']}\n\nPrevious attempt had these issues:\n{gap_context}\n\nPlease address these issues."

        result = self._call_llm(enhanced_prompt)
        return result

    def check_completion(self) -> str:
        """
        Check if execution is complete based on feedback

        Returns:
            str: 'COMPLETE' if PASS feedback exists, 'IN_PROGRESS' otherwise
        """
        feedback = self.read_feedback()

        if feedback and feedback.get("status") == "PASS":
            return "COMPLETE"

        return "IN_PROGRESS"

    def run(self) -> None:
        """
        Run single execution based on feedback state

        - If no feedback exists: Do initial execution
        - If FAIL feedback exists: Retry with feedback context
        - If PASS feedback exists: Mark as complete

        NOTE: Current implementation makes 1 execution per run() call.
        Integration tests expect run() to be called separately for each attempt.
        Known issue: test_retries_on_fail_feedback expects >= 2 LLM calls from single run(),
        which conflicts with integration test expectations. Prioritizing integration test behavior.
        """
        # Read instructions
        instructions = self.read_instructions()

        # Check for existing feedback
        feedback = self.read_feedback()

        # Execute based on feedback state
        if feedback:
            if feedback.get("status") == "FAIL":
                attempt = feedback.get("attempt", 0)

                # Check retry limit
                if attempt >= self.max_retries:
                    self.execution_status = "MAX_RETRIES_EXCEEDED"
                    return

                # Retry with feedback context
                result = self.execute_with_feedback(instructions, feedback)
                self.execution_history.append({"attempt": attempt + 1, "result": result})
                self.write_result(result, instructions["output_path"])
                self.execution_status = "RETRY"
            elif feedback.get("status") == "PASS":
                self.execution_status = "COMPLETE"
        else:
            # Initial execution (no feedback yet)
            result = self.execute(instructions)
            self.execution_history.append({"attempt": 1, "result": result})
            self.write_result(result, instructions["output_path"])
            self.execution_status = "WAITING_FEEDBACK"

    def wait_for_instructions(self, timeout: Optional[float] = None) -> Optional[dict]:
        """
        Poll for instructions.json file with optional timeout

        Args:
            timeout: Optional timeout in seconds

        Returns:
            dict or None: Instructions if file exists, None otherwise
        """
        start_time = time.time()

        while True:
            instructions_file = self.working_dir / "instructions.json"

            if instructions_file.exists():
                return self.read_instructions()

            # Check timeout
            if timeout and (time.time() - start_time) >= timeout:
                return None

            # Sleep before next check
            time.sleep(self.poll_interval)

    def clear_state(self) -> None:
        """Clear execution state for new instructions"""
        self.execution_status = "idle"
        self.execution_history = []

    def should_retry(self) -> bool:
        """
        Check if worker should retry based on feedback and retry limit

        Returns:
            bool: True if should retry, False if max retries exceeded
        """
        feedback = self.read_feedback()

        if not feedback:
            return False

        if feedback.get("status") != "FAIL":
            return False

        attempt = feedback.get("attempt", 0)
        return attempt < self.max_retries

    def check_for_instructions(self) -> bool:
        """
        Check if instructions.json exists

        Returns:
            bool: True if instructions file exists
        """
        instructions_file = self.working_dir / "instructions.json"
        return instructions_file.exists()

    def get_status(self) -> str:
        """
        Get current execution status

        Returns:
            str: Current status (idle, running, complete, etc.)
        """
        return self.execution_status

    def set_status(self, status: str) -> None:
        """
        Set execution status

        Args:
            status: New status value
        """
        self.execution_status = status

    def add_to_history(self, entry: dict) -> None:
        """
        Add entry to execution history

        Args:
            entry: History entry dict
        """
        self.execution_history.append(entry)

    def get_history(self) -> list:
        """
        Get execution history

        Returns:
            list: Execution history entries
        """
        return self.execution_history

    def reset(self) -> None:
        """Reset execution state to initial values"""
        self.execution_status = "idle"
        self.execution_history = []
