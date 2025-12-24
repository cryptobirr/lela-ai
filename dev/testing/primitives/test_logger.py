"""
TDD Red-Phase Tests for Logger Primitive

Issue: #4 - [Sprint 1, Day 2] Primitive: Logger
Status: RED PHASE - All tests should FAIL (no implementation yet)

Test coverage: 9 tests mapping 1:1 to 9 acceptance criteria
"""

import json
import re
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


class TestLogger:
    """Test suite for Logger primitive - Red Phase"""

    def test_debug_logs_with_debug_level(self, capsys):
        """
        AC1: Logs DEBUG messages with DEBUG level

        Verifies that calling logger.debug() produces a log entry with level="debug"
        """
        # Setup: Create Logger instance configured for stdout
        from src.primitives.logger import Logger

        logger = Logger()

        # Action: Log debug message
        logger.debug("test debug message")

        # Expected: Log output contains message and DEBUG level
        captured = capsys.readouterr()
        output = captured.out.lower()

        assert "test debug message" in output
        assert "debug" in output
        # Ensure no other log levels appear
        assert "info" not in output or "debug" in output
        assert "warning" not in output
        assert "error" not in output or "debug" in output  # "error" might be in "debug"

    def test_info_logs_with_info_level(self, capsys):
        """
        AC2: Logs INFO messages with INFO level

        Verifies that calling logger.info() produces a log entry with level="info"
        """
        # Setup: Create Logger instance configured for stdout
        from src.primitives.logger import Logger

        logger = Logger()

        # Action: Log info message
        logger.info("test info message")

        # Expected: Log output contains message and INFO level
        captured = capsys.readouterr()
        output = captured.out.lower()

        assert "test info message" in output
        assert "info" in output
        # Ensure it's specifically info level
        assert "debug" not in output
        assert "warning" not in output

    def test_warning_logs_with_warning_level(self, capsys):
        """
        AC3: Logs WARNING messages with WARNING level

        Verifies that calling logger.warning() produces a log entry with level="warning"
        """
        # Setup: Create Logger instance configured for stdout
        from src.primitives.logger import Logger

        logger = Logger()

        # Action: Log warning message
        logger.warning("test warning message")

        # Expected: Log output contains message and WARNING level
        captured = capsys.readouterr()
        output = captured.out.lower()

        assert "test warning message" in output
        assert "warning" in output or "warn" in output
        # Ensure it's specifically warning level
        assert "debug" not in output
        assert "info" not in output

    def test_error_logs_with_error_level(self, capsys):
        """
        AC4: Logs ERROR messages with ERROR level

        Verifies that calling logger.error() produces a log entry with level="error"
        """
        # Setup: Create Logger instance configured for stdout
        from src.primitives.logger import Logger

        logger = Logger()

        # Action: Log error message
        logger.error("test error message")

        # Expected: Log output contains message and ERROR level
        captured = capsys.readouterr()
        output = captured.out.lower()

        assert "test error message" in output
        assert "error" in output
        # Ensure it's specifically error level
        assert "debug" not in output
        assert "warning" not in output

    def test_includes_iso8601_timestamp(self, capsys):
        """
        AC5: Includes ISO 8601 timestamps in log output

        Verifies that log output includes a valid ISO 8601 timestamp
        """
        # Setup: Create Logger instance and record current time
        from src.primitives.logger import Logger

        logger = Logger()
        before_time = datetime.now(timezone.utc).replace(tzinfo=None)

        # Action: Log message
        logger.info("timestamp test")

        # Expected: Log output contains ISO 8601 timestamp
        captured = capsys.readouterr()
        output = captured.out

        # ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ or similar
        iso8601_pattern = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?"
        match = re.search(iso8601_pattern, output)

        assert match is not None, "No ISO 8601 timestamp found in output"

        # Verify timestamp is within reasonable range (±10 seconds)
        timestamp_str = match.group(0)
        # Handle both with and without 'Z' suffix
        timestamp_str_clean = timestamp_str.rstrip("Z")

        # Parse timestamp (handle optional microseconds)
        if "." in timestamp_str_clean:
            parsed_time = datetime.fromisoformat(timestamp_str_clean)
        else:
            parsed_time = datetime.strptime(timestamp_str_clean, "%Y-%m-%dT%H:%M:%S")

        time_diff = abs((parsed_time - before_time).total_seconds())
        assert time_diff < 10, f"Timestamp too far from current time: {time_diff}s"

    def test_includes_context_in_output(self, capsys):
        """
        AC6: Includes context dictionary in log output

        Verifies that context passed to log methods appears in output
        """
        # Setup: Create Logger instance
        from src.primitives.logger import Logger

        logger = Logger()

        # Action: Log with context
        logger.info("context test", context={"pod_id": "pod-123", "worker_id": "worker-456"})

        # Expected: Log output contains context values
        captured = capsys.readouterr()
        output = captured.out

        assert "pod_id" in output or "pod-123" in output
        assert "worker_id" in output or "worker-456" in output
        assert "pod-123" in output
        assert "worker-456" in output

        # Verify it's structured (appears to be key-value pairs, not just concatenated)
        # This is a basic check - actual structure will depend on implementation
        assert ":" in output or "=" in output, "Context should be structured"

    def test_writes_to_stdout_when_configured(self, capsys):
        """
        AC7: Writes to stdout when configured for console output

        Verifies that Logger writes to stdout when configured for console output
        """
        # Setup: Create Logger instance (default should be stdout)
        from src.primitives.logger import Logger

        logger = Logger()

        # Action: Log message
        logger.info("stdout test")

        # Expected: Output appears in stdout
        captured = capsys.readouterr()

        assert "stdout test" in captured.out
        assert captured.out != "", "Stdout should not be empty"
        # Verify it's stdout, not stderr
        assert "stdout test" not in captured.err

    def test_writes_to_file_when_configured(self, tmp_path):
        """
        AC8: Writes to file when configured for file output

        Verifies that Logger writes to file when configured for file output
        """
        # Setup: Create temporary log file path
        from src.primitives.logger import Logger

        log_file = tmp_path / "test.log"

        # Create Logger configured for file output
        with Logger(output_file=str(log_file)) as logger:
            # Action: Log message
            logger.info("file test")

        # Expected: Log file exists and contains message
        assert log_file.exists(), "Log file should be created"

        log_content = log_file.read_text()
        assert "file test" in log_content
        assert "info" in log_content.lower()

        # Verify structured log entry (has timestamp, level, message)
        assert re.search(r"\d{4}-\d{2}-\d{2}", log_content), "Should have timestamp"

    def test_thread_safe_logging(self, tmp_path):
        """
        AC9: Thread-safe logging when accessed from multiple threads

        Verifies that Logger handles concurrent logging without data corruption
        """
        # Setup: Create Logger configured for file output
        from src.primitives.logger import Logger

        log_file = tmp_path / "thread_test.log"

        with Logger(output_file=str(log_file)) as logger:
            num_threads = 10
            messages_per_thread = 100
            threads = []

            def log_messages(thread_id):
                """Worker function to log messages from a thread"""
                for i in range(messages_per_thread):
                    logger.info(f"thread-{thread_id}-message-{i}")

            # Action: Start all threads concurrently
            for thread_id in range(num_threads):
                thread = threading.Thread(target=log_messages, args=(thread_id,))
                threads.append(thread)
                thread.start()

            # Wait for all threads to complete
            for thread in threads:
                thread.join()

        # Expected: All messages present, no corruption
        log_content = log_file.read_text()
        log_lines = [line for line in log_content.strip().split("\n") if line]

        # Should have exactly 1000 log entries
        expected_total = num_threads * messages_per_thread
        assert (
            len(log_lines) == expected_total
        ), f"Expected {expected_total} log entries, got {len(log_lines)}"

        # Verify all unique messages are present
        for thread_id in range(num_threads):
            for msg_id in range(messages_per_thread):
                expected_msg = f"thread-{thread_id}-message-{msg_id}"
                assert (
                    expected_msg in log_content
                ), f"Missing message: {expected_msg}"

        # Verify no corrupted lines (basic check - each line should have a timestamp)
        iso8601_pattern = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
        for line in log_lines:
            assert re.search(
                iso8601_pattern, line
            ), f"Corrupted log line (missing timestamp): {line[:100]}"
