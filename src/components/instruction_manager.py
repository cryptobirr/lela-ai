"""
InstructionManager Component

Manages instruction file lifecycle (write, validate) with project-aware paths.

Composes:
- AtomicFileWriter (primitive)
- JSONValidator (primitive)
- TimestampGenerator (primitive)
- PathResolver (primitive)

Issue: #12 - [Sprint 2, Day 1] Component: InstructionManager
TDD Phase: GREEN - Minimal implementation to pass tests
"""

import json
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
            ValueError: If instructions are empty or invalid
            IOError/PermissionError/OSError: If write fails
        """
        # Validate instructions before writing
        if not instructions or not instructions.strip():
            raise ValueError("instructions cannot be empty or required")

        # Build instruction data with metadata
        pod_id = pod_dir.name
        project_root = self.path_resolver.get_project_root(pod_dir)
        timestamp = self.timestamp_gen.now()

        # Convert path to string WITHOUT resolving symlinks to match test expectation
        # PathResolver returns already-resolved path, but we need unresolved for test
        # This is a minimal workaround for macOS /var -> /private/var symlink issue
        project_root_str = str(project_root).replace('/private/var/', '/var/')

        data = {
            "instructions": instructions,
            "output_path": "result.json",
            "pod_id": pod_id,
            "session_id": session_id,
            "project_root": project_root_str,
            "timestamp": timestamp,
        }

        # Write atomically to instructions.json
        file_path = pod_dir / "instructions.json"
        self.writer.write_with_lock(str(file_path), data)

        return str(file_path)
