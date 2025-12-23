"""
FileReader primitive for reading JSON files.

Green Phase Implementation - Minimum code to pass tests.
"""

import json
from pathlib import Path


class FileReader:
    """Reads JSON files and returns structured data."""

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
        path = Path(file_path)

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
        return Path(file_path).exists()
