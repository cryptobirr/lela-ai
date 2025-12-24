"""
Test suite for TimestampGenerator primitive

Issue: #7
Phase: RED (all tests should fail until implementation)
"""

import re
from datetime import datetime, timezone

import pytest

from src.primitives.timestamp_generator import TimestampGenerator


class TestTimestampGenerator:
    """Test suite for TimestampGenerator primitive - Issue #7"""

    @staticmethod
    def _parse_timestamp_to_datetime(timestamp: str) -> datetime:
        """Helper method to parse ISO 8601 timestamp with 'Z' suffix"""
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    def test_now_returns_valid_iso8601_timestamp(self):
        """
        Test 1: Generates valid ISO 8601 timestamps
        Maps to AC1: "Generates valid ISO 8601 timestamps"
        """
        # Setup: Capture current time for validation
        before_call = datetime.now(timezone.utc)

        # Action: Call now()
        timestamp = TimestampGenerator.now()

        # Expected: Valid ISO 8601 format
        # Pattern: YYYY-MM-DDTHH:MM:SSZ (with optional microseconds)
        iso8601_pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$"
        assert isinstance(timestamp, str), "Timestamp must be a string"
        assert re.match(
            iso8601_pattern, timestamp
        ), f"Timestamp '{timestamp}' does not match ISO 8601 format"

        # Parse and validate it's a valid datetime
        parsed_time = self._parse_timestamp_to_datetime(timestamp)
        assert isinstance(parsed_time, datetime), "Timestamp must be parseable as datetime"

        # Validate it's "now" (within ±10 seconds)
        after_call = datetime.now(timezone.utc)
        assert (
            before_call <= parsed_time <= after_call
        ), f"Timestamp {parsed_time} is not within current time range"

    def test_now_always_returns_utc_timezone(self):
        """
        Test 2: Always uses UTC timezone
        Maps to AC2: "Always uses UTC timezone"
        """
        # Setup: No timezone manipulation needed

        # Action: Call now() multiple times
        timestamps = [TimestampGenerator.now() for _ in range(5)]

        # Expected: Every timestamp ends with 'Z' (UTC indicator)
        for timestamp in timestamps:
            assert timestamp.endswith("Z"), f"Timestamp '{timestamp}' does not end with 'Z'"

            # Parse and verify UTC timezone
            parsed_time = self._parse_timestamp_to_datetime(timestamp)
            assert (
                parsed_time.tzinfo == timezone.utc
            ), f"Timestamp '{timestamp}' is not in UTC timezone"

            # Ensure no other timezone indicators (+HH:MM or -HH:MM)
            assert "+" not in timestamp[:-1], f"Timestamp '{timestamp}' contains timezone offset"
            assert "-" not in timestamp.split("T")[1], (
                f"Timestamp '{timestamp}' contains timezone offset in time portion"
            )

    def test_parse_converts_iso8601_to_datetime(self):
        """
        Test 3: Parses ISO 8601 strings correctly
        Maps to AC3: "Parses ISO 8601 strings correctly"
        """
        # Setup: Define test ISO 8601 timestamp
        test_timestamp = "2025-12-23T15:45:30Z"

        # Action: Call parse()
        result = TimestampGenerator.parse(test_timestamp)

        # Expected: Returns datetime object with correct values
        assert isinstance(result, datetime), "parse() must return datetime object"
        assert result.year == 2025, f"Year should be 2025, got {result.year}"
        assert result.month == 12, f"Month should be 12, got {result.month}"
        assert result.day == 23, f"Day should be 23, got {result.day}"
        assert result.hour == 15, f"Hour should be 15, got {result.hour}"
        assert result.minute == 45, f"Minute should be 45, got {result.minute}"
        assert result.second == 30, f"Second should be 30, got {result.second}"
        assert result.tzinfo == timezone.utc, (
            f"Timezone should be UTC, got {result.tzinfo}"
        )

    def test_parse_raises_error_for_invalid_formats(self):
        """
        Test 4: Handles invalid timestamp formats
        Maps to AC4: "Handles invalid timestamp formats"
        """
        # Setup: Define invalid timestamp strings
        invalid_timestamps = [
            "not-a-timestamp",
            "2025-13-45",  # Invalid month/day
            "2025/12/23",  # Wrong separator
            "",  # Empty string
        ]

        # Action & Expected: Each invalid format raises ValueError
        for invalid_ts in invalid_timestamps:
            with pytest.raises(ValueError) as exc_info:
                TimestampGenerator.parse(invalid_ts)

            # Verify error message is descriptive
            error_message = str(exc_info.value).lower()
            assert "invalid" in error_message or "format" in error_message, (
                f"Error message should mention 'invalid' or 'format', got: {exc_info.value}"
            )

    def test_parse_rejects_non_utc_timezone(self):
        """
        Verify parse() raises ValueError for non-UTC timezones

        Tests that only UTC timezone is accepted
        """
        # Setup: Define timestamps with non-UTC timezones
        non_utc_timestamps = [
            "2025-12-23T15:45:30+05:00",  # UTC+5
            "2025-12-23T15:45:30-08:00",  # UTC-8
            "2025-12-23T15:45:30+01:00",  # UTC+1
        ]

        # Action & Expected: Each non-UTC timestamp raises ValueError
        for timestamp in non_utc_timestamps:
            with pytest.raises(ValueError) as exc_info:
                TimestampGenerator.parse(timestamp)

            # Verify error message mentions timezone/UTC
            error_message = str(exc_info.value).lower()
            assert "utc" in error_message or "timezone" in error_message, (
                f"Error should mention UTC/timezone, got: {exc_info.value}"
            )
