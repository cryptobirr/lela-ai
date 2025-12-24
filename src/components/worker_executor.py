"""
WorkerExecutor Component - Execute worker tasks

Issue: #17 - [Sprint 2, Day 4] Component: WorkerExecutor
Status: REFACTOR PHASE - Improved code quality with helper methods

Composition:
- LLMProvider (component) - Makes LLM calls
- ResultManager (component) - Writes results
- Logger (primitive) - Logs execution

Interface:
- execute(instructions_path: str, worker_config: dict) -> str (result file path)

State: Stateless

Refactorings Applied:
- Extracted _read_instructions() for file I/O separation
- Extracted _extract_instructions() for validation logic
- Extracted _validate_worker_config() for config validation
- Extracted _build_provider_config() for config construction
- Removed redundant variable assignment (prompt = instructions)
"""

import json
from pathlib import Path

from src.components.llm_provider import LLMProvider
from src.components.result_manager import ResultManager
from src.primitives import logger


class WorkerExecutor:
    """Execute worker tasks: read instructions, call LLM, write result"""

    def __init__(self):
        """Initialize WorkerExecutor with dependencies"""
        self.llm_provider = LLMProvider()
        self.result_manager = ResultManager()
        self.logger = logger.Logger()

    def execute(self, instructions_path: str, worker_config: dict) -> str:
        """
        Execute worker task: read instructions, call LLM, write result

        Args:
            instructions_path: Path to instructions.json file
            worker_config: Worker configuration dict with required fields:
                - worker_id: Worker identifier
                - pod_id: Pod identifier
                - session_id: Session identifier
                - worker_dir: Working directory path
                - llm_config_path: Path to LLM config file

        Returns:
            str: Path to result.json file

        Raises:
            FileNotFoundError: If instructions file doesn't exist
            ValueError: If instructions are empty or config is invalid
            json.JSONDecodeError: If instructions.json has invalid JSON
            KeyError: If required worker_config fields are missing
        """
        # Validate worker_config has required fields
        self._validate_worker_config(worker_config)

        # Log execution start
        self.logger.info(
            f"Starting worker execution: worker_id={worker_config['worker_id']}, "
            f"pod_id={worker_config['pod_id']}"
        )

        # Read and parse instructions file
        instructions_data = self._read_instructions(instructions_path)

        # Extract and validate instructions
        instructions = self._extract_instructions(instructions_data)

        # Call LLM via LLMProvider
        self.logger.info("Calling LLM with generated prompt")
        provider_config = self._build_provider_config(worker_config["llm_config_path"])
        try:
            llm_response = self.llm_provider.generate(instructions, provider_config)
        except Exception as e:
            self.logger.error(f"LLM API error: {str(e)}")
            raise

        # Write result.json via ResultManager
        result_path = self.result_manager.write(
            llm_response,
            worker_config["worker_dir"],
            worker_config["worker_id"],
            worker_config["pod_id"],
            worker_config["session_id"],
        )

        # Log completion
        self.logger.info(f"Worker execution complete: result_path={result_path}")

        return result_path

    def _read_instructions(self, instructions_path: str) -> dict:
        """
        Read and parse instructions JSON file

        Args:
            instructions_path: Path to instructions.json file

        Returns:
            dict: Parsed instructions data

        Raises:
            FileNotFoundError: If instructions file doesn't exist
            json.JSONDecodeError: If JSON is invalid
        """
        instructions_file = Path(instructions_path)
        if not instructions_file.exists():
            raise FileNotFoundError(f"Instructions file not found: {instructions_path}")

        instructions_text = instructions_file.read_text()
        return json.loads(instructions_text)

    def _extract_instructions(self, instructions_data: dict) -> str:
        """
        Extract and validate instructions from parsed data

        Args:
            instructions_data: Parsed instructions dictionary

        Returns:
            str: Validated instructions text

        Raises:
            ValueError: If instructions are empty
        """
        instructions = instructions_data.get("instructions", "")
        if not instructions or len(instructions.strip()) == 0:
            raise ValueError("prompt cannot be empty")
        return instructions

    def _validate_worker_config(self, worker_config: dict) -> None:
        """
        Validate worker configuration has all required fields

        Args:
            worker_config: Worker configuration dictionary to validate

        Raises:
            KeyError: If required field is missing
        """
        required_fields = ["worker_id", "pod_id", "session_id", "worker_dir", "llm_config_path"]
        for field in required_fields:
            if field not in worker_config:
                raise KeyError(f"Missing required field in worker_config: {field}")

    def _build_provider_config(self, llm_config_path: str) -> dict:
        """
        Build LLM provider configuration dictionary

        Args:
            llm_config_path: Path to LLM configuration file

        Returns:
            dict: Provider configuration with config_path
        """
        return {"config_path": llm_config_path}
