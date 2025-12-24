"""
TDD Red-Phase Tests for FileReader Primitive

Issue: #1 - [Sprint 1, Day 1] Primitive: FileReader
Status: RED PHASE - All tests should FAIL (no implementation yet)

Test coverage: 5 tests mapping 1:1 to 5 acceptance criteria
"""

import json
import pytest
from pathlib import Path


class TestFileReader:
    """Test suite for FileReader primitive - Red Phase"""

    def test_read_returns_dict_from_valid_json(self, tmp_path):
        """
        AC1: read() returns dict from valid JSON files (including nested structures)

        Verifies FileReader reads JSON and preserves structure (simple and nested)
        """
        # Setup: Create JSON file with nested structure
        test_file = tmp_path / "test.json"
        test_data = {
            "simple": "value",
            "number": 42,
            "nested": {
                "inner": ["item1", "item2"],
                "flag": True
            }
        }
        test_file.write_text(json.dumps(test_data), encoding="utf-8")

        # Action: Read the file
        from src.primitives.file_reader import FileReader
        reader = FileReader()
        result = reader.read(str(test_file))

        # Expected: Returns dict matching exact structure
        assert isinstance(result, dict)
        assert result["simple"] == "value"
        assert result["number"] == 42
        assert result["nested"]["inner"] == ["item1", "item2"]
        assert result["nested"]["flag"] is True  # Boolean preserved, not string

    def test_read_raises_error_for_missing_file(self):
        """
        AC2: read() raises FileNotFoundError for missing files

        Verifies FileReader raises appropriate error when file doesn't exist
        """
        # Setup: Non-existent file path
        non_existent_path = "/tmp/does_not_exist_12345.json"

        # Action & Expected: Should raise FileNotFoundError
        from src.primitives.file_reader import FileReader
        reader = FileReader()

        with pytest.raises(FileNotFoundError) as exc_info:
            reader.read(non_existent_path)

        # Error message should include the file path
        assert non_existent_path in str(exc_info.value)

    def test_read_raises_error_for_malformed_json(self, tmp_path):
        """
        AC3: read() raises JSONDecodeError for malformed JSON without crashing

        Verifies FileReader handles invalid JSON gracefully (no crash)
        """
        # Setup: Create file with malformed JSON
        malformed_file = tmp_path / "malformed.json"
        malformed_file.write_text('{"key": "value", "missing_closing_brace"', encoding="utf-8")

        # Action & Expected: Should raise JSONDecodeError, not crash
        from src.primitives.file_reader import FileReader
        reader = FileReader()

        with pytest.raises(json.JSONDecodeError) as exc_info:
            reader.read(str(malformed_file))

        # Error message should indicate JSON parsing failure
        assert "JSON" in str(exc_info.value) or "Expecting" in str(exc_info.value)

    def test_read_handles_utf8_encoding(self, tmp_path):
        """
        AC4: read() handles UTF-8 encoding correctly

        Verifies FileReader handles UTF-8 encoded content (non-ASCII characters)
        """
        # Setup: Create JSON file with UTF-8 characters
        utf8_file = tmp_path / "utf8.json"
        utf8_data = {
            "message": "Hello 世界 🌍",
            "emoji": "✅"
        }
        utf8_file.write_text(json.dumps(utf8_data, ensure_ascii=False), encoding="utf-8")

        # Action: Read the file
        from src.primitives.file_reader import FileReader
        reader = FileReader()
        result = reader.read(str(utf8_file))

        # Expected: UTF-8 strings intact, no encoding errors
        assert result["message"] == "Hello 世界 🌍"
        assert result["emoji"] == "✅"
        assert "世界" in result["message"]
        assert "🌍" in result["message"]

    def test_exists_identifies_file_presence(self, tmp_path):
        """
        AC5: exists() correctly identifies file presence (True/False)

        Verifies exists() method returns correct boolean for file existence
        """
        # Setup: Create a temporary JSON file
        existing_file = tmp_path / "exists.json"
        existing_file.write_text('{"test": "data"}', encoding="utf-8")

        # Setup: Non-existent file path
        non_existent_file = tmp_path / "does_not_exist.json"

        # Action: Check file existence
        from src.primitives.file_reader import FileReader
        reader = FileReader()

        # Expected: Returns True when file exists
        assert reader.exists(str(existing_file)) is True

        # Expected: Returns False when file doesn't exist
        assert reader.exists(str(non_existent_file)) is False
