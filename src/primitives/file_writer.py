"""
FileWriter primitive for writing JSON files.

Green Phase - Minimum viable implementation to pass all tests.
"""

import json
import os
import tempfile
from pathlib import Path


class FileWriter:
    """Writes JSON files with atomic write support."""

    def _to_path(self, file_path: str) -> Path:
        """
        Convert string path to Path object.

        Args:
            file_path: String path to convert

        Returns:
            Path: Path object
        """
        return Path(file_path)

    def _ensure_parent_dirs(self, path: Path) -> None:
        """
        Ensure parent directories exist.

        Args:
            path: File path whose parent directories should exist
        """
        path.parent.mkdir(parents=True, exist_ok=True)

    def _dump_json(self, data: dict, file_handle) -> None:
        """
        Serialize dict to JSON and write to file handle.

        Args:
            data: Dictionary to serialize
            file_handle: Open file handle to write to
        """
        json.dump(data, file_handle, ensure_ascii=False, indent=2)

    def write(self, file_path: str, data: dict) -> bool:
        """
        Write dict to JSON file.

        Creates parent directories if they don't exist.

        Args:
            file_path: Path to write the JSON file
            data: Dictionary to serialize as JSON

        Returns:
            bool: True if write successful

        Raises:
            PermissionError: If cannot write to location
        """
        path = self._to_path(file_path)
        self._ensure_parent_dirs(path)

        # Write JSON with UTF-8 encoding
        with open(path, "w", encoding="utf-8") as f:
            self._dump_json(data, f)

        return True

    def write_atomic(self, file_path: str, data: dict) -> bool:
        """
        Write dict to JSON file atomically.

        Uses temp file + rename to prevent partial writes.
        Creates parent directories if they don't exist.

        Args:
            file_path: Path to write the JSON file
            data: Dictionary to serialize as JSON

        Returns:
            bool: True if write successful

        Raises:
            PermissionError: If cannot write to location
        """
        path = self._to_path(file_path)
        self._ensure_parent_dirs(path)

        # Write to temp file in same directory
        # Using same directory ensures atomic rename (same filesystem)
        fd, temp_path = tempfile.mkstemp(
            dir=path.parent,
            suffix=".tmp",
            prefix=f".{path.name}."
        )

        try:
            # Write JSON to temp file
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                self._dump_json(data, f)

            # Atomic rename
            os.rename(temp_path, path)

        except Exception:
            # Clean up temp file on error
            try:
                os.unlink(temp_path)
            except FileNotFoundError:
                pass
            raise

        return True
