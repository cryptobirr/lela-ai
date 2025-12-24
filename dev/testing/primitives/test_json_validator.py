"""
Tests for JSONValidator Primitive

Tests the JSONValidator implementation for validating JSON data against schemas.
Covers validation of instructions, results, and feedback schemas used in pod communication.
"""

import pytest
from src.primitives.json_validator import JSONValidator


class TestJSONValidatorBasic:
    """Basic validation tests"""

    def test_validate_returns_true_for_valid_data(self):
        """Valid data against schema returns (True, [])"""
        validator = JSONValidator()
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"}
            },
            "required": ["name"]
        }
        data = {"name": "Alice", "age": 30}

        is_valid, errors = validator.validate(data, schema)

        assert is_valid is True
        assert errors == []

    def test_validate_returns_false_for_invalid_type(self):
        """Invalid type returns (False, [error messages])"""
        validator = JSONValidator()
        schema = {
            "type": "object",
            "properties": {
                "age": {"type": "integer"}
            }
        }
        data = {"age": "not a number"}

        is_valid, errors = validator.validate(data, schema)

        assert is_valid is False
        assert len(errors) > 0
        assert "age" in errors[0]

    def test_validate_returns_false_for_missing_required_field(self):
        """Missing required field returns (False, [error message])"""
        validator = JSONValidator()
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"}
            },
            "required": ["name"]
        }
        data = {}

        is_valid, errors = validator.validate(data, schema)

        assert is_valid is False
        assert len(errors) > 0
        assert "'name'" in errors[0] or "name" in errors[0]

    def test_validate_handles_nested_validation_errors(self):
        """Nested validation errors include path information"""
        validator = JSONValidator()
        schema = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string"}
                    },
                    "required": ["email"]
                }
            }
        }
        data = {"user": {}}

        is_valid, errors = validator.validate(data, schema)

        assert is_valid is False
        assert len(errors) > 0
        # Error should mention "user" in the path
        assert any("user" in err.lower() or "email" in err.lower() for err in errors)


class TestInstructionsSchema:
    """Tests for validate_instructions() using INSTRUCTIONS_SCHEMA"""

    def test_validate_instructions_accepts_valid_instructions(self):
        """Valid instructions with required fields passes"""
        validator = JSONValidator()
        data = {
            "instructions": "Do something",
            "output_path": "/path/to/output.json"
        }

        is_valid, errors = validator.validate_instructions(data)

        assert is_valid is True
        assert errors == []

    def test_validate_instructions_rejects_missing_instructions_field(self):
        """Missing 'instructions' field fails validation"""
        validator = JSONValidator()
        data = {
            "output_path": "/path/to/output.json"
        }

        is_valid, errors = validator.validate_instructions(data)

        assert is_valid is False
        assert len(errors) > 0
        assert any("instructions" in err.lower() for err in errors)

    def test_validate_instructions_rejects_missing_output_path_field(self):
        """Missing 'output_path' field fails validation"""
        validator = JSONValidator()
        data = {
            "instructions": "Do something"
        }

        is_valid, errors = validator.validate_instructions(data)

        assert is_valid is False
        assert len(errors) > 0
        assert any("output_path" in err.lower() for err in errors)

    def test_validate_instructions_rejects_wrong_type_for_instructions(self):
        """Wrong type for 'instructions' field fails validation"""
        validator = JSONValidator()
        data = {
            "instructions": 123,  # Should be string
            "output_path": "/path/to/output.json"
        }

        is_valid, errors = validator.validate_instructions(data)

        assert is_valid is False
        assert len(errors) > 0

    def test_validate_instructions_allows_extra_fields(self):
        """Extra fields are allowed in instructions (open schema)"""
        validator = JSONValidator()
        data = {
            "instructions": "Do something",
            "output_path": "/path/to/output.json",
            "extra_field": "extra_value"
        }

        is_valid, errors = validator.validate_instructions(data)

        # JSON Schema Draft 7 allows additional properties by default
        assert is_valid is True


class TestResultSchema:
    """Tests for validate_result() using RESULT_SCHEMA"""

    def test_validate_result_accepts_valid_result_with_any_type(self):
        """Valid result with any type for 'result' field passes"""
        validator = JSONValidator()

        # Test with string result
        is_valid, errors = validator.validate_result({"result": "success"})
        assert is_valid is True

        # Test with dict result
        is_valid, errors = validator.validate_result({"result": {"key": "value"}})
        assert is_valid is True

        # Test with number result
        is_valid, errors = validator.validate_result({"result": 42})
        assert is_valid is True

        # Test with list result
        is_valid, errors = validator.validate_result({"result": [1, 2, 3]})
        assert is_valid is True

    def test_validate_result_rejects_missing_result_field(self):
        """Missing 'result' field fails validation"""
        validator = JSONValidator()
        data = {"other_field": "value"}

        is_valid, errors = validator.validate_result(data)

        assert is_valid is False
        assert len(errors) > 0
        assert any("result" in err.lower() for err in errors)

    def test_validate_result_accepts_null_result(self):
        """Null/None as result value is valid"""
        validator = JSONValidator()
        data = {"result": None}

        is_valid, errors = validator.validate_result(data)

        assert is_valid is True


class TestFeedbackSchemas:
    """Tests for validate_feedback() using FEEDBACK_PASS_SCHEMA and FEEDBACK_FAIL_SCHEMA"""

    def test_validate_feedback_pass_accepts_valid_pass_feedback(self):
        """Valid PASS feedback with all required fields passes"""
        validator = JSONValidator()
        data = {
            "status": "PASS",
            "result": "completed successfully",
            "attempts": 1
        }

        is_valid, errors = validator.validate_feedback(data)

        assert is_valid is True
        assert errors == []

    def test_validate_feedback_fail_accepts_valid_fail_feedback(self):
        """Valid FAIL feedback with all required fields passes"""
        validator = JSONValidator()
        data = {
            "status": "FAIL",
            "gaps": ["Missing X", "Y is incorrect"],
            "attempt": 2
        }

        is_valid, errors = validator.validate_feedback(data)

        assert is_valid is True
        assert errors == []

    def test_validate_feedback_rejects_invalid_status(self):
        """Invalid status (not PASS or FAIL) returns error"""
        validator = JSONValidator()
        data = {
            "status": "PENDING",
            "result": "something"
        }

        is_valid, errors = validator.validate_feedback(data)

        assert is_valid is False
        assert len(errors) > 0
        assert any("PENDING" in err for err in errors)
        assert any("PASS" in err and "FAIL" in err for err in errors)

    def test_validate_feedback_rejects_pass_without_result(self):
        """PASS feedback missing 'result' field fails"""
        validator = JSONValidator()
        data = {
            "status": "PASS",
            "attempts": 1
        }

        is_valid, errors = validator.validate_feedback(data)

        assert is_valid is False
        assert len(errors) > 0

    def test_validate_feedback_rejects_pass_without_attempts(self):
        """PASS feedback missing 'attempts' field fails"""
        validator = JSONValidator()
        data = {
            "status": "PASS",
            "result": "done"
        }

        is_valid, errors = validator.validate_feedback(data)

        assert is_valid is False
        assert len(errors) > 0

    def test_validate_feedback_rejects_fail_without_gaps(self):
        """FAIL feedback missing 'gaps' field fails"""
        validator = JSONValidator()
        data = {
            "status": "FAIL",
            "attempt": 1
        }

        is_valid, errors = validator.validate_feedback(data)

        assert is_valid is False
        assert len(errors) > 0

    def test_validate_feedback_rejects_fail_with_empty_gaps(self):
        """FAIL feedback with empty 'gaps' array fails (minItems: 1)"""
        validator = JSONValidator()
        data = {
            "status": "FAIL",
            "gaps": [],  # Must have at least 1 item
            "attempt": 1
        }

        is_valid, errors = validator.validate_feedback(data)

        assert is_valid is False
        assert len(errors) > 0

    def test_validate_feedback_rejects_fail_without_attempt(self):
        """FAIL feedback missing 'attempt' field fails"""
        validator = JSONValidator()
        data = {
            "status": "FAIL",
            "gaps": ["Missing something"]
        }

        is_valid, errors = validator.validate_feedback(data)

        assert is_valid is False
        assert len(errors) > 0

    def test_validate_feedback_rejects_pass_with_wrong_attempts_type(self):
        """PASS feedback with non-integer 'attempts' fails"""
        validator = JSONValidator()
        data = {
            "status": "PASS",
            "result": "done",
            "attempts": "not a number"
        }

        is_valid, errors = validator.validate_feedback(data)

        assert is_valid is False
        assert len(errors) > 0

    def test_validate_feedback_handles_missing_status_field(self):
        """Feedback with no status field returns appropriate error"""
        validator = JSONValidator()
        data = {
            "result": "something"
        }

        is_valid, errors = validator.validate_feedback(data)

        assert is_valid is False
        assert len(errors) > 0
        # Should mention that status is None or missing
        assert any("None" in err or "null" in err.lower() for err in errors)


class TestErrorFormatting:
    """Tests for error message formatting"""

    def test_format_validation_error_includes_path_for_nested_errors(self):
        """Error messages include JSON path for nested validation errors"""
        validator = JSONValidator()
        schema = {
            "type": "object",
            "properties": {
                "nested": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "integer"}
                    }
                }
            }
        }
        data = {
            "nested": {
                "value": "not an integer"
            }
        }

        is_valid, errors = validator.validate(data, schema)

        assert is_valid is False
        assert len(errors) > 0
        # Error should include the path "nested.value"
        assert any("nested" in err for err in errors)

    def test_format_validation_error_shows_root_for_top_level_errors(self):
        """Top-level validation errors use 'root' in path"""
        validator = JSONValidator()
        schema = {"type": "array"}
        data = {"not": "an array"}

        is_valid, errors = validator.validate(data, schema)

        assert is_valid is False
        assert len(errors) > 0
        # Error should mention root or be at top level
        assert any("root" in err.lower() or "type" in err.lower() for err in errors)
