"""
Test suite for RequirementComparator Component

Purpose: Verify STRICT binary evaluation logic (PASS only if result == "PASS")

Test Coverage:
- PASS case: result == "PASS" → ("PASS", [])
- Wrong answer: result != "PASS" → ("FAIL", [gaps])
- Empty/null result: "" or None → ("FAIL", ["No result provided"])
- Partial answer: incomplete → ("FAIL", [specific gaps])
- Malformed result: invalid format → ("FAIL", [error details])
- Multi-requirement instructions: complex evaluations
- Logging: all evaluations logged

Requirements tested: Issue #16 - Component: RequirementComparator
"""

import pytest
from src.components.requirement_comparator import RequirementComparator


class TestRequirementComparatorPassCase:
    """Test the ONLY case that should return PASS."""

    def test_evaluate_returns_pass_when_result_is_pass(self):
        """CRITICAL: Only return PASS when result is exactly 'PASS'."""
        comparator = RequirementComparator()
        instructions = "Calculate 2 + 2"
        result = "PASS"

        status, gaps = comparator.evaluate(instructions, result)

        assert status == "PASS"
        assert gaps == []


class TestRequirementComparatorFailCases:
    """Test all cases that should return FAIL with specific gaps."""

    def test_evaluate_returns_fail_for_wrong_answer(self):
        """Wrong answer should return FAIL with specific gap."""
        comparator = RequirementComparator()
        instructions = "Calculate 2 + 2 and return 4"
        result = "5"  # Wrong answer

        status, gaps = comparator.evaluate(instructions, result)

        assert status == "FAIL"
        assert len(gaps) > 0
        assert any("Incorrect result" in gap or "5" in gap for gap in gaps)

    def test_evaluate_returns_fail_for_empty_result(self):
        """Empty result should return FAIL with 'No result provided' gap."""
        comparator = RequirementComparator()
        instructions = "Calculate 2 + 2"
        result = ""

        status, gaps = comparator.evaluate(instructions, result)

        assert status == "FAIL"
        assert len(gaps) > 0
        assert any("No result provided" in gap for gap in gaps)

    def test_evaluate_returns_fail_for_none_result(self):
        """None result should return FAIL with 'No result provided' gap."""
        comparator = RequirementComparator()
        instructions = "Calculate 2 + 2"
        result = None

        status, gaps = comparator.evaluate(instructions, result)

        assert status == "FAIL"
        assert len(gaps) > 0
        assert any("No result provided" in gap for gap in gaps)

    def test_evaluate_returns_fail_for_partial_answer(self):
        """Partial answer should return FAIL with specific missing requirements."""
        comparator = RequirementComparator()
        instructions = "Return result with: 1) answer, 2) explanation, 3) confidence score"
        result = "answer: 42"  # Missing explanation and confidence

        status, gaps = comparator.evaluate(instructions, result)

        assert status == "FAIL"
        assert len(gaps) > 0
        assert any("Incomplete" in gap or "missing" in gap.lower() for gap in gaps)

    def test_evaluate_returns_fail_for_malformed_result(self):
        """Malformed result should return FAIL with error details."""
        comparator = RequirementComparator()
        instructions = "Return valid JSON with status field"
        result = "{invalid json]"  # Malformed JSON

        status, gaps = comparator.evaluate(instructions, result)

        assert status == "FAIL"
        assert len(gaps) > 0
        assert any("Malformed" in gap or "error" in gap.lower() for gap in gaps)

    def test_evaluate_returns_fail_for_any_non_pass_string(self):
        """Any string other than 'PASS' should return FAIL."""
        comparator = RequirementComparator()
        instructions = "Complete the task"

        non_pass_values = ["pass", "Pass", "PASSED", "SUCCESS", "OK", "true", "1"]

        for result in non_pass_values:
            status, gaps = comparator.evaluate(instructions, result)
            assert status == "FAIL", f"Expected FAIL for result='{result}', got {status}"
            assert len(gaps) > 0, f"Expected gaps for result='{result}'"


class TestRequirementComparatorComplexInstructions:
    """Test evaluation with multi-requirement instructions."""

    def test_evaluate_with_multi_requirement_instructions_all_met(self):
        """Multi-requirement instructions with result='PASS' should pass."""
        comparator = RequirementComparator()
        instructions = """
        Requirements:
        1. Calculate sum of numbers
        2. Round to 2 decimal places
        3. Return with units
        """
        result = "PASS"

        status, gaps = comparator.evaluate(instructions, result)

        assert status == "PASS"
        assert gaps == []

    def test_evaluate_with_multi_requirement_instructions_not_met(self):
        """Multi-requirement instructions with non-PASS result should fail."""
        comparator = RequirementComparator()
        instructions = """
        Requirements:
        1. Calculate sum of numbers
        2. Round to 2 decimal places
        3. Return with units
        """
        result = "3.14"  # Missing units, not PASS

        status, gaps = comparator.evaluate(instructions, result)

        assert status == "FAIL"
        assert len(gaps) > 0

    def test_evaluate_extracts_requirements_from_instructions(self):
        """Should extract and validate requirements from complex instructions."""
        comparator = RequirementComparator()
        instructions = "Return JSON with fields: name, age, email"
        result = '{"name": "John"}'  # Missing age and email

        status, gaps = comparator.evaluate(instructions, result)

        assert status == "FAIL"
        assert len(gaps) > 0
        # Should identify missing fields
        assert any("age" in gap.lower() or "email" in gap.lower() for gap in gaps)


class TestRequirementComparatorLogging:
    """Test that all evaluations are logged."""

    def test_evaluate_logs_pass_evaluation(self):
        """PASS evaluations should be logged."""
        comparator = RequirementComparator()
        instructions = "Complete task"
        result = "PASS"

        # Should log: instructions, result, status, gaps
        status, gaps = comparator.evaluate(instructions, result)

        # Verify logging occurred (check logger was called)
        # Implementation will inject logger dependency for testing
        assert status == "PASS"

    def test_evaluate_logs_fail_evaluation(self):
        """FAIL evaluations should be logged with gaps."""
        comparator = RequirementComparator()
        instructions = "Return number 42"
        result = "43"

        status, gaps = comparator.evaluate(instructions, result)

        # Verify logging occurred with gaps
        assert status == "FAIL"
        assert len(gaps) > 0

    def test_evaluate_logs_all_fields(self):
        """Should log instructions, result, status, and gaps."""
        comparator = RequirementComparator()
        instructions = "Task description"
        result = "incomplete"

        status, gaps = comparator.evaluate(instructions, result)

        # In implementation, verify logger.log() was called with:
        # - instructions
        # - result
        # - status
        # - gaps
        assert status == "FAIL"


class TestRequirementComparatorStateless:
    """Test that comparator is stateless."""

    def test_evaluate_multiple_calls_independent(self):
        """Multiple evaluations should be independent (no state)."""
        comparator = RequirementComparator()

        # First evaluation: PASS
        status1, gaps1 = comparator.evaluate("Task 1", "PASS")
        assert status1 == "PASS"

        # Second evaluation: FAIL (should not be affected by first)
        status2, gaps2 = comparator.evaluate("Task 2", "wrong")
        assert status2 == "FAIL"

        # Third evaluation: PASS again (should not be affected by second)
        status3, gaps3 = comparator.evaluate("Task 3", "PASS")
        assert status3 == "PASS"


class TestRequirementComparatorEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_evaluate_with_empty_instructions(self):
        """Empty instructions should still evaluate result."""
        comparator = RequirementComparator()
        instructions = ""
        result = "PASS"

        status, gaps = comparator.evaluate(instructions, result)

        assert status == "PASS"
        assert gaps == []

    def test_evaluate_with_whitespace_only_result(self):
        """Whitespace-only result should be treated as empty/FAIL."""
        comparator = RequirementComparator()
        instructions = "Complete task"
        result = "   "

        status, gaps = comparator.evaluate(instructions, result)

        assert status == "FAIL"
        assert len(gaps) > 0

    def test_evaluate_with_pass_in_middle_of_result(self):
        """'PASS' within other text should still FAIL."""
        comparator = RequirementComparator()
        instructions = "Complete task"
        result = "The test will PASS when complete"

        status, gaps = comparator.evaluate(instructions, result)

        assert status == "FAIL"
        assert len(gaps) > 0

    def test_evaluate_with_case_sensitive_pass(self):
        """'PASS' is case-sensitive (pass, Pass should FAIL)."""
        comparator = RequirementComparator()
        instructions = "Complete task"

        # Test lowercase
        status, gaps = comparator.evaluate(instructions, "pass")
        assert status == "FAIL"

        # Test mixed case
        status, gaps = comparator.evaluate(instructions, "Pass")
        assert status == "FAIL"

        # Test only uppercase should PASS
        status, gaps = comparator.evaluate(instructions, "PASS")
        assert status == "PASS"
