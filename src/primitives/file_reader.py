"""
FileReader primitive for reading JSON files.

Refactor Phase - Clean, maintainable implementation.
"""

import json
from pathlib import Path


class FileReader:
    """Reads JSON files and returns structured data."""

    def _to_path(self, file_path: str) -> Path:
        """
        Convert string path to Path object.

        Args:
            file_path: String path to convert

        Returns:
            Path: Path object
        """
        return Path(file_path)

    def read(self, file_path: str) -> dict:
        """
        Read JSON file and return as dict.

        Args:
            file_path: Path to the JSON file

        Returns:
            dict: Parsed JSON content

        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If JSON is malformed
        """
        path = self._to_path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def exists(self, file_path: str) -> bool:
        """
        Check if file exists.

        Args:
            file_path: Path to check

        Returns:
            bool: True if file exists, False otherwise
        """
        return self._to_path(file_path).exists()
