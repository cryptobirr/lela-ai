"""
Logger Primitive

Structured logging with levels and context.

Interface:
- debug(message: str, context: dict = {}) → None
- info(message: str, context: dict = {}) → None
- warning(message: str, context: dict = {}) → None
- error(message: str, context: dict = {}) → None
"""

import sys
from pathlib import Path
from typing import Optional

import structlog


class Logger:
    """Thread-safe structured logger with ISO 8601 timestamps."""

    def __init__(self, output_file: Optional[str] = None):
        """
        Initialize logger.

        Args:
            output_file: Path to log file. If None, logs to stdout.
        """
        self.output_file = output_file
        self._file_handle = None
        self._configure_structlog()

    def _configure_structlog(self):
        """Configure structlog processors and output."""
        processors = [
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ]

        if self.output_file:
            # File output
            log_path = Path(self.output_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            self._file_handle = open(self.output_file, "a", encoding="utf-8")
            structlog.configure(
                processors=processors,
                wrapper_class=structlog.make_filtering_bound_logger(0),
                context_class=dict,
                logger_factory=structlog.PrintLoggerFactory(file=self._file_handle),
                cache_logger_on_first_use=True,
            )
        else:
            # Stdout output
            structlog.configure(
                processors=processors,
                wrapper_class=structlog.make_filtering_bound_logger(0),
                context_class=dict,
                logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
                cache_logger_on_first_use=True,
            )

        self._logger = structlog.get_logger()

    def _normalize_context(self, context: Optional[dict]) -> dict:
        """Normalize context parameter, returning empty dict if None."""
        return context if context is not None else {}

    def debug(self, message: str, context: Optional[dict] = None) -> None:
        """
        Log DEBUG level message.

        Args:
            message: Log message
            context: Optional context dictionary
        """
        self._logger.debug(message, **self._normalize_context(context))

    def info(self, message: str, context: Optional[dict] = None) -> None:
        """
        Log INFO level message.

        Args:
            message: Log message
            context: Optional context dictionary
        """
        self._logger.info(message, **self._normalize_context(context))

    def warning(self, message: str, context: Optional[dict] = None) -> None:
        """
        Log WARNING level message.

        Args:
            message: Log message
            context: Optional context dictionary
        """
        self._logger.warning(message, **self._normalize_context(context))

    def error(self, message: str, context: Optional[dict] = None) -> None:
        """
        Log ERROR level message.

        Args:
            message: Log message
            context: Optional context dictionary
        """
        self._logger.error(message, **self._normalize_context(context))

    def close(self) -> None:
        """Close file handle if open."""
        if self._file_handle is not None:
            self._file_handle.close()
            self._file_handle = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures file handle is closed."""
        self.close()
        return False
