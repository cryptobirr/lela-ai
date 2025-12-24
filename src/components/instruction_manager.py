"""
InstructionManager Component

Manages instruction file lifecycle (write, validate) with project-aware paths.

Composes:
- AtomicFileWriter (primitive)
- JSONValidator (primitive)
- TimestampGenerator (primitive)
- PathResolver (primitive)

Issue: #12 - [Sprint 2, Day 1] Component: InstructionManager
TDD Phase: REFACTOR - Code quality improvements completed
"""

from pathlib import Path

from src.primitives.file_writer import FileWriter
from src.primitives.json_validator import JSONValidator
from src.primitives.path_resolver import PathResolver
from src.primitives.timestamp_generator import TimestampGenerator


class InstructionManager:
    """Manages instruction file lifecycle with validation and metadata."""

    def __init__(self):
        """Initialize InstructionManager with required primitives."""
        self.writer = FileWriter()
        self.validator = JSONValidator()
        self.timestamp_gen = TimestampGenerator()
        self.path_resolver = PathResolver()

    def _normalize_path(self, path: Path) -> str:
        """
        Normalize path for cross-platform compatibility.

        On macOS, /var is a symlink to /private/var. PathResolver.get_project_root()
        resolves symlinks, but we want the canonical form (/var) for consistency.

        Args:
            path: Path to normalize

        Returns:
            str: Normalized path string
        """
        path_str = str(path)
        # Normalize macOS /private/var symlink to /var
        if path_str.startswith("/private/var/"):
            return path_str.replace("/private/var/", "/var/", 1)
        return path_str

    def _build_instruction_data(self, instructions: str, pod_dir: Path, session_id: str) -> dict:
        """
        Build instruction data dictionary with metadata.

        Args:
            instructions: Instruction text
            pod_dir: Path to pod directory
            session_id: Session identifier

        Returns:
            dict: Complete instruction data with metadata
        """
        pod_id = pod_dir.name
        project_root = self.path_resolver.get_project_root(pod_dir)
        timestamp = self.timestamp_gen.now()

        return {
            "instructions": instructions,
            "output_path": "result.json",
            "pod_id": pod_id,
            "session_id": session_id,
            "project_root": self._normalize_path(project_root),
            "timestamp": timestamp,
        }

    def create(self, instructions: str, pod_dir: Path, session_id: str) -> str:
        """
        Create instructions.json file in pod directory with metadata.

        Args:
            instructions: Instruction text to write
            pod_dir: Path to pod directory
            session_id: Session identifier

        Returns:
            str: Path to created instructions.json file

        Raises:
            ValueError: If instructions are empty or invalid JSON schema
            IOError/PermissionError/OSError: If write fails
        """
        # Validate instructions before writing (manual check for empty)
        if not instructions or not instructions.strip():
            raise ValueError(
                "Instruction validation failed: instructions field cannot be empty or whitespace"
            )

        # Build instruction data with metadata
        data = self._build_instruction_data(instructions, pod_dir, session_id)

        # Validate complete data structure against schema
        is_valid, errors = self.validator.validate_instructions(data)
        if not is_valid:
            error_details = "; ".join(errors)
            raise ValueError(f"Instruction validation failed: {error_details}")

        # Write atomically to instructions.json
        file_path = pod_dir / "instructions.json"
        self.writer.write_with_lock(str(file_path), data)

        return str(file_path)
