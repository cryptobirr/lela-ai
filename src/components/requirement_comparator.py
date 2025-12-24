"""
RequirementComparator Component

Purpose: Compare instructions to result (STRICT: only "PASS" = success, everything else = FAIL + retry)
Issue: #16 - Component: RequirementComparator
"""

from typing import Optional

from src.primitives.gap_extractor import GapExtractor
from src.primitives.logger import Logger


class RequirementComparator:
    """
    Compare instructions to result using binary PASS/FAIL evaluation.

    CRITICAL RULE: Only explicit "PASS" string in result = success
    """

    def __init__(self):
        """Initialize comparator with dependencies."""
        self.gap_extractor = GapExtractor()
        self.logger = Logger()

    def evaluate(self, instructions: str, result: Optional[str]) -> tuple[str, list[str]]:
        """
        Evaluate result against instructions using binary PASS/FAIL logic.

        Args:
            instructions: What must be done
            result: What was actually done

        Returns:
            Tuple of (status, gaps) where:
            - status: "PASS" or "FAIL"
            - gaps: List of specific gap descriptions (empty if PASS)

        Examples:
            >>> comparator = RequirementComparator()
            >>> comparator.evaluate("Calculate 2+2", "PASS")
            ('PASS', [])
            >>> status, gaps = comparator.evaluate("Calculate 2+2", "5")
            >>> status
            'FAIL'
        """
        # Check for PASS first (only success case)
        if self.gap_extractor.is_pass(result):
            self.logger.info(
                "Evaluation: PASS",
                {"instructions": instructions, "result": result, "status": "PASS", "gaps": []},
            )
            return ("PASS", [])

        # All other cases are FAIL - determine specific gaps
        gaps = self._determine_gaps(instructions, result)

        self.logger.info(
            "Evaluation: FAIL",
            {"instructions": instructions, "result": result, "status": "FAIL", "gaps": gaps},
        )

        return ("FAIL", gaps)

    def _determine_gaps(self, instructions: str, result: Optional[str]) -> list[str]:
        """
        Determine specific gaps between instructions and result.

        Args:
            instructions: Expected requirements
            result: Actual result

        Returns:
            List of specific gap descriptions
        """
        # Handle None or empty result
        if result is None or result == "":
            return ["No result provided"]

        # Handle whitespace-only result
        if result.strip() == "":
            return ["No result provided"]

        # Check for malformed JSON if instructions mention JSON
        if "json" in instructions.lower():
            if not self._is_valid_json_format(result):
                return [f"Malformed result: {result}"]

        # Check for partial/incomplete answers
        if ":" in instructions.lower() or ")" in instructions:
            # Instructions likely enumerate multiple requirements
            missing_items = self._find_missing_items(instructions, result)
            if missing_items:
                return [f"Incomplete result: missing {', '.join(missing_items)}"]

        # Extract requirements from instructions
        requirements = self.gap_extractor.extract_requirements(instructions)

        # If no specific requirements, return generic gap with result value
        if not requirements:
            return [f"Incorrect result: {result}"]

        # Find specific gaps using GapExtractor
        gaps = self.gap_extractor.find_gaps(requirements, result)

        # If gaps found, include result value in gap message
        if gaps:
            # Add result value to gap messages for clarity
            enhanced_gaps = []
            for gap in gaps:
                if "Missing requirement" in gap:
                    enhanced_gaps.append(f"Incorrect result: {result}")
                else:
                    enhanced_gaps.append(gap)
            return enhanced_gaps

        # If no specific gaps found but result != PASS, return generic gap
        return [f"Incorrect result: {result}"]

    def _find_missing_items(self, instructions: str, result: str) -> list[str]:
        """
        Find specific items mentioned in instructions that are missing from result.

        Args:
            instructions: Instruction text with enumerated items
            result: Result text to check

        Returns:
            List of missing item names
        """
        result_lower = result.lower()
        missing = []

        # Extract potential field names from instructions
        # Pattern: "fields: name, age, email" or "1) answer, 2) explanation"
        import re

        # Pattern 1: Find numbered items "1) answer, 2) explanation"
        numbered_pattern = r"\d+\)\s*([a-z][a-z0-9\s]*?)(?:,|\d+\)|$)"
        numbered_matches = re.findall(numbered_pattern, instructions.lower())
        for item in numbered_matches:
            item = item.strip()
            if item and item not in result_lower:
                missing.append(item)

        # Pattern 2: Find comma-separated items after colons "fields: name, age, email"
        if not missing:
            colon_pattern = r":\s*([a-z_][a-z0-9_,\s]*)"
            matches = re.findall(colon_pattern, instructions.lower())
            for match in matches:
                items = [item.strip() for item in match.split(",")]
                for item in items:
                    if item and item not in result_lower:
                        missing.append(item)

        return missing

    def _is_valid_json_format(self, text: str) -> bool:
        """
        Check if text appears to be valid JSON format.

        Args:
            text: Text to check

        Returns:
            True if appears to be valid JSON, False otherwise
        """
        import json

        try:
            json.loads(text)
            return True
        except (json.JSONDecodeError, TypeError):
            return False
