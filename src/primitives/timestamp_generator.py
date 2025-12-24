"""TimestampGenerator Primitive - Issue #7

Generate and parse ISO 8601 timestamps in UTC timezone.
"""

from datetime import datetime, timezone


class TimestampGenerator:
    """Generate and parse ISO 8601 timestamps"""

    @staticmethod
    def now() -> str:
        """Generate current UTC timestamp in ISO 8601 format

        Returns:
            str: Current UTC timestamp in format YYYY-MM-DDTHH:MM:SS.ffffffZ
        """
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def parse(timestamp: str) -> datetime:
        """Parse ISO 8601 timestamp string to datetime object

        Args:
            timestamp: ISO 8601 formatted timestamp string

        Returns:
            datetime: Parsed datetime object in UTC timezone

        Raises:
            ValueError: If timestamp format is invalid
        """
        if not timestamp:
            raise ValueError("Invalid timestamp format: empty string")

        try:
            # Handle 'Z' suffix by replacing with '+00:00'
            normalized = timestamp.replace("Z", "+00:00")
            dt = datetime.fromisoformat(normalized)

            # Ensure timezone is UTC
            if dt.tzinfo != timezone.utc:
                raise ValueError(f"Invalid timestamp format: timezone is not UTC")

            return dt
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid timestamp format: {e}")
