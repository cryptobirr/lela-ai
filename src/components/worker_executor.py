"""
WorkerExecutor Component - Execute worker tasks

Issue: #17 - [Sprint 2, Day 4] Component: WorkerExecutor
Status: GREEN PHASE - Minimal implementation to pass tests

Composition:
- LLMProvider (component) - Makes LLM calls
- ResultManager (component) - Writes results
- Logger (primitive) - Logs execution

Interface:
- execute(instructions_path: str, worker_config: dict) -> str (result file path)

State: Stateless
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
        required_fields = ["worker_id", "pod_id", "session_id", "worker_dir", "llm_config_path"]
        for field in required_fields:
            if field not in worker_config:
                raise KeyError(f"Missing required field in worker_config: {field}")

        # Log execution start
        self.logger.info(
            f"Starting worker execution: worker_id={worker_config['worker_id']}, "
            f"pod_id={worker_config['pod_id']}"
        )

        # Read instructions.json
        instructions_file = Path(instructions_path)
        if not instructions_file.exists():
            raise FileNotFoundError(f"Instructions file not found: {instructions_path}")

        instructions_text = instructions_file.read_text()
        instructions_data = json.loads(instructions_text)

        # Extract instructions
        instructions = instructions_data.get("instructions", "")
        if not instructions or len(instructions.strip()) == 0:
            raise ValueError("prompt cannot be empty")

        # Generate prompt from instructions
        prompt = instructions

        # Call LLM via LLMProvider
        self.logger.info("Calling LLM with generated prompt")
        provider_config = {"config_path": worker_config["llm_config_path"]}
        try:
            llm_response = self.llm_provider.generate(prompt, provider_config)
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
