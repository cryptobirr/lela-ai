"""
TDD Red-Phase Tests for GapExtractor Primitive

Issue: #8 - [Sprint 1, Day 4] Primitive: GapExtractor
Status: RED PHASE - All tests should FAIL (no implementation yet)

Test coverage: 7 tests mapping 1:1 to 7 acceptance criteria
"""

import pytest


class TestGapExtractor:
    """Test suite for GapExtractor primitive - Red Phase"""

    def test_is_pass_returns_true_only_for_exact_pass_string(self):
        """
        AC1: Returns True only for exact "PASS" string

        Verifies is_pass() returns True ONLY for exact "PASS" (case-sensitive, no whitespace)
        """
        # Setup: Import GapExtractor
        from src.primitives.gap_extractor import GapExtractor

        extractor = GapExtractor()

        # Action & Expected: Only exact "PASS" returns True
        assert extractor.is_pass("PASS") is True

        # All other variations return False
        assert extractor.is_pass("pass") is False  # Case-sensitive
        assert extractor.is_pass("Pass") is False
        assert extractor.is_pass("PASS ") is False  # Trailing whitespace
        assert extractor.is_pass(" PASS") is False  # Leading whitespace
        assert extractor.is_pass(" PASS ") is False  # Both

    def test_is_pass_returns_false_for_wrong_answer(self):
        """
        AC2: Returns False for wrong answer

        Verifies is_pass() returns False for any value that is not exact "PASS"
        """
        # Setup: Import GapExtractor
        from src.primitives.gap_extractor import GapExtractor

        extractor = GapExtractor()

        # Action & Expected: All non-"PASS" values return False
        wrong_answers = ["42", "FAIL", "Success", "true", "OK", "Completed"]

        for wrong_answer in wrong_answers:
            assert extractor.is_pass(wrong_answer) is False, (
                f"Expected is_pass('{wrong_answer}') to return False"
            )

    def test_is_pass_returns_false_for_no_answer(self):
        """
        AC3: Returns False for no answer (empty/null)

        Verifies is_pass() returns False for empty, None, or whitespace-only results
        """
        # Setup: Import GapExtractor
        from src.primitives.gap_extractor import GapExtractor

        extractor = GapExtractor()

        # Action & Expected: Empty/null values return False
        assert extractor.is_pass("") is False  # Empty string
        assert extractor.is_pass(None) is False  # None/null
        assert extractor.is_pass("   ") is False  # Whitespace only
        assert extractor.is_pass("\t") is False  # Tab
        assert extractor.is_pass("\n") is False  # Newline

    def test_is_pass_returns_false_for_partial_answer(self):
        """
        AC4: Returns False for partial answer

        Verifies is_pass() returns False when "PASS" is part of a larger string
        """
        # Setup: Import GapExtractor
        from src.primitives.gap_extractor import GapExtractor

        extractor = GapExtractor()

        # Action & Expected: Partial matches return False
        partial_answers = [
            "PASS with extra",
            "Almost PASS",
            "PASS but incomplete",
            "The result is PASS",
            "PASS!",
            "PASS.",
        ]

        for partial_answer in partial_answers:
            assert extractor.is_pass(partial_answer) is False, (
                f"Expected is_pass('{partial_answer}') to return False"
            )

    def test_is_pass_returns_false_for_malformed_result(self):
        """
        AC5: Returns False for malformed result

        Verifies is_pass() handles malformed input gracefully (no crash)
        """
        # Setup: Import GapExtractor
        from src.primitives.gap_extractor import GapExtractor

        extractor = GapExtractor()

        # Action & Expected: Malformed inputs return False (no crash)
        malformed_inputs = [
            "{invalid json}",
            "{'key': 'value'}",  # Python dict syntax (not JSON)
            "[unclosed array",
            '{"unclosed": "object"',
            "random { } brackets",
        ]

        for malformed_input in malformed_inputs:
            # Should not raise exception, just return False
            result = extractor.is_pass(malformed_input)
            assert result is False, f"Expected is_pass('{malformed_input}') to return False"

    def test_find_gaps_extracts_specific_gaps_not_generic_errors(self):
        """
        AC6: Extracts specific gaps (not generic errors)

        Verifies find_gaps() returns specific gap descriptions (actionable feedback)
        """
        # Setup: Import GapExtractor
        from src.primitives.gap_extractor import GapExtractor

        extractor = GapExtractor()

        # Setup: Define requirements and incomplete result
        requirements = ["Calculate sum of 2+2", "Return result as integer"]
        incomplete_result = "The sum is 4"  # Missing integer return format

        # Action: Find gaps
        gaps = extractor.find_gaps(requirements, incomplete_result)

        # Expected: Returns list of specific gaps
        assert isinstance(gaps, list), "find_gaps() must return a list"
        assert len(gaps) > 0, "find_gaps() must identify at least one gap"

        # Verify gaps are specific (not generic)
        for gap in gaps:
            assert isinstance(gap, str), "Each gap must be a string"
            assert len(gap) > 0, "Gap descriptions must not be empty"
            # Must not be generic errors
            assert gap.lower() not in ["fail", "error", "wrong"], (
                f"Gap '{gap}' is too generic - must reference specific requirement"
            )

        # At least one gap should reference a missing requirement
        gap_text = " ".join(gaps).lower()
        assert "requirement" in gap_text or "missing" in gap_text or "return" in gap_text, (
            "Gaps must reference specific requirements"
        )

    def test_extract_requirements_handles_complex_multi_requirement_instructions(self):
        """
        AC7: Handles complex instructions (multi-requirement)

        Verifies extract_requirements() parses multi-step instructions correctly
        """
        # Setup: Import GapExtractor
        from src.primitives.gap_extractor import GapExtractor

        extractor = GapExtractor()

        # Setup: Define complex multi-requirement instructions
        complex_instructions = """
        1. Read file from path X
        2. Parse JSON content
        3. Extract field 'name'
        4. Return value as string
        5. Handle missing file with error message
        """

        # Action: Extract requirements
        requirements = extractor.extract_requirements(complex_instructions)

        # Expected: Returns list of 5 discrete requirements
        assert isinstance(requirements, list), "extract_requirements() must return a list"
        assert len(requirements) == 5, f"Expected 5 requirements, got {len(requirements)}"

        # Verify each requirement is a non-empty string
        for req in requirements:
            assert isinstance(req, str), f"Requirement must be string, got {type(req)}"
            assert len(req) > 0, "Requirement must not be empty"

        # Verify requirements match instruction steps (order matters)
        assert "read file" in requirements[0].lower(), "First requirement should be about reading file"
        assert "parse" in requirements[1].lower(), "Second requirement should be about parsing JSON"
        assert "extract" in requirements[2].lower(), "Third requirement should be about extracting field"
        assert "return" in requirements[3].lower(), "Fourth requirement should be about returning value"
        assert "handle" in requirements[4].lower() or "error" in requirements[4].lower(), (
            "Fifth requirement should be about error handling"
        )

    def test_extract_requirements_handles_blank_lines(self):
        """
        Verify extract_requirements() filters out blank lines

        Tests edge case of instructions with empty lines
        """
        from src.primitives.gap_extractor import GapExtractor

        extractor = GapExtractor()

        # Setup: Instructions with blank lines
        instructions_with_blanks = """
        1. First requirement

        2. Second requirement


        3. Third requirement
        """

        # Action: Extract requirements
        requirements = extractor.extract_requirements(instructions_with_blanks)

        # Expected: Only 3 requirements (blank lines filtered)
        assert len(requirements) == 3, f"Expected 3 requirements, got {len(requirements)}"
        assert all(req.strip() for req in requirements), "All requirements should be non-empty"

    def test_has_integer_format_detects_pure_numbers(self):
        """
        Verify _has_integer_format() returns True for pure integer strings

        Tests edge case for integer format detection
        """
        from src.primitives.gap_extractor import GapExtractor

        extractor = GapExtractor()

        # Valid integer formats (should return True)
        assert extractor._has_integer_format("42", "42") is True
        assert extractor._has_integer_format("100", "100") is True

    def test_has_integer_format_rejects_prose(self):
        """
        Verify _has_integer_format() returns False for numbers in prose

        Tests edge case for rejecting prose descriptions
        """
        from src.primitives.gap_extractor import GapExtractor

        extractor = GapExtractor()

        # Prose descriptions (should return False)
        assert extractor._has_integer_format("The answer is 42", "the answer is 42") is False
        assert extractor._has_integer_format("Sum: 100", "sum: 100") is False

    def test_has_integer_format_rejects_no_digits(self):
        """
        Verify _has_integer_format() returns False for strings with no digits

        Tests edge case for strings without any numbers
        """
        from src.primitives.gap_extractor import GapExtractor

        extractor = GapExtractor()

        # Strings with no digits (should return False)
        assert extractor._has_integer_format("no digits here", "no digits here") is False
        assert extractor._has_integer_format("PASS", "pass") is False
