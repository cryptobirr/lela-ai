"""
JSONValidator Primitive

Validates JSON data against schemas using jsonschema library.
Provides predefined schemas for instructions, result, and feedback.
"""

from jsonschema import validate, ValidationError, Draft7Validator


class JSONValidator:
    """Validates JSON against schemas"""

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
        error_messages = []
        for error in errors:
            # Build a specific error message with path and details
            path = ".".join(str(p) for p in error.path) if error.path else "root"
            message = f"{path}: {error.message}"
            error_messages.append(message)

        return (False, error_messages)

    def validate_instructions(self, data: dict) -> tuple[bool, list[str]]:
        """
        Validate instructions.json format

        Args:
            data: The instructions data to validate

        Returns:
            tuple[bool, list[str]]: (is_valid, error_messages)
        """
        return self.validate(data, self.INSTRUCTIONS_SCHEMA)

    def validate_result(self, data: dict) -> tuple[bool, list[str]]:
        """
        Validate result.json format

        Args:
            data: The result data to validate

        Returns:
            tuple[bool, list[str]]: (is_valid, error_messages)
        """
        return self.validate(data, self.RESULT_SCHEMA)

    def validate_feedback(self, data: dict) -> tuple[bool, list[str]]:
        """
        Validate feedback.json format (handles both PASS and FAIL)

        Args:
            data: The feedback data to validate

        Returns:
            tuple[bool, list[str]]: (is_valid, error_messages)
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
