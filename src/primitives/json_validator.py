"""
JSONValidator Primitive

Validates JSON data against schemas using jsonschema library.
Provides predefined schemas for instructions, result, and feedback.
"""

from typing import Any

from jsonschema import Draft7Validator


class JSONValidator:
    """Validates JSON against schemas"""

    @staticmethod
    def _format_validation_error(error: Any) -> str:
        """
        Format a jsonschema validation error into a readable message

        Args:
            error: ValidationError from jsonschema

        Returns:
            str: Formatted error message with path and details
        """
        path = ".".join(str(p) for p in error.path) if error.path else "root"
        return f"{path}: {error.message}"

    # Predefined schemas for pod communication
    INSTRUCTIONS_SCHEMA = {
        "type": "object",
        "properties": {
            "instructions": {"type": "string"},
            "output_path": {"type": "string"}
        },
        "required": ["instructions", "output_path"]
    }

    RESULT_SCHEMA = {
        "type": "object",
        "properties": {
            "result": {}  # Result can be any type
        },
        "required": ["result"]
    }

    FEEDBACK_PASS_SCHEMA = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["PASS"]},
            "result": {},
            "attempts": {"type": "integer"}
        },
        "required": ["status", "result", "attempts"]
    }

    FEEDBACK_FAIL_SCHEMA = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["FAIL"]},
            "gaps": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1
            },
            "attempt": {"type": "integer"}
        },
        "required": ["status", "gaps", "attempt"]
    }

    def validate(self, data: dict, schema: dict) -> tuple[bool, list[str]]:
        """
        Validate JSON data against a schema

        Args:
            data: The JSON data to validate
            schema: The JSON schema to validate against

        Returns:
            tuple[bool, list[str]]: (is_valid, error_messages)
                - is_valid: True if valid, False otherwise
                - error_messages: List of specific error messages (empty if valid)
        """
        validator = Draft7Validator(schema)
        errors = list(validator.iter_errors(data))

        if not errors:
            return (True, [])

        # Convert validation errors to specific error messages
        error_messages = [self._format_validation_error(error) for error in errors]
        return (False, error_messages)

    def validate_instructions(self, data: dict) -> tuple[bool, list[str]]:
        """Validate instructions.json against predefined schema"""
        return self.validate(data, self.INSTRUCTIONS_SCHEMA)

    def validate_result(self, data: dict) -> tuple[bool, list[str]]:
        """Validate result.json against predefined schema"""
        return self.validate(data, self.RESULT_SCHEMA)

    def validate_feedback(self, data: dict) -> tuple[bool, list[str]]:
        """
        Validate feedback.json against predefined schema (PASS or FAIL)

        Automatically selects the appropriate schema based on status field.
        """
        # Check which schema to use based on status
        status = data.get("status")

        if status == "PASS":
            return self.validate(data, self.FEEDBACK_PASS_SCHEMA)
        elif status == "FAIL":
            return self.validate(data, self.FEEDBACK_FAIL_SCHEMA)
        else:
            # Invalid status
            return (False, [f"status: Invalid status '{status}' (must be 'PASS' or 'FAIL')"])
