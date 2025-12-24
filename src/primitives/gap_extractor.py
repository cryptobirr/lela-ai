"""
GapExtractor Primitive

Issue: #8 - [Sprint 1, Day 4] Primitive: GapExtractor
Purpose: Parse instruction requirements and extract gaps with binary PASS/FAIL evaluation
"""

import re
from typing import Optional


class GapExtractor:
    """
    Parse instruction requirements and extract gaps between instructions and results.

    CRITICAL RULE: Only explicit "PASS" string = success, everything else = FAIL
    """

    def is_pass(self, result: Optional[str]) -> bool:
        """
        Binary evaluation: Returns True ONLY for exact "PASS" string.

        Args:
            result: The result string to evaluate

        Returns:
            True if result is exactly "PASS", False otherwise

        Examples:
            >>> extractor = GapExtractor()
            >>> extractor.is_pass("PASS")
            True
            >>> extractor.is_pass("pass")
            False
            >>> extractor.is_pass("PASS ")
            False
            >>> extractor.is_pass(None)
            False
        """
        # Only exact "PASS" string returns True
        return result == "PASS"

    def find_gaps(self, requirements: list[str], result: str) -> list[str]:
        """
        Extract specific gaps between requirements and result.

        Args:
            requirements: List of discrete requirements
            result: The actual result to compare against

        Returns:
            List of specific gap descriptions (what's missing/wrong)

        Examples:
            >>> extractor = GapExtractor()
            >>> reqs = ["Calculate sum of 2+2", "Return result as integer"]
            >>> result = "The sum is 4"
            >>> gaps = extractor.find_gaps(reqs, result)
            >>> len(gaps) > 0
            True
        """
        gaps = []

        # Check each requirement against the result
        for requirement in requirements:
            # Extract key terms from requirement
            key_terms = self._extract_key_terms(requirement)

            # Check if result satisfies requirement
            if not self._requirement_satisfied(requirement, key_terms, result):
                gaps.append(f"Missing requirement: {requirement}")

        return gaps

    def extract_requirements(self, instructions: str) -> list[str]:
        """
        Parse complex multi-requirement instructions into discrete requirements.

        Args:
            instructions: Multi-line instruction string (may contain numbered steps)

        Returns:
            List of discrete requirements extracted from instructions

        Examples:
            >>> extractor = GapExtractor()
            >>> instructions = "1. Read file\\n2. Parse JSON\\n3. Extract field 'name'"
            >>> reqs = extractor.extract_requirements(instructions)
            >>> len(reqs)
            3
        """
        # Split instructions by newlines
        lines = instructions.strip().split('\n')

        requirements = []

        for line in lines:
            # Remove leading/trailing whitespace
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Remove numbered list prefix (1. 2. etc.)
            cleaned_line = re.sub(r'^\d+\.\s*', '', line)

            # Add to requirements if not empty
            if cleaned_line:
                requirements.append(cleaned_line)

        return requirements

    def _extract_key_terms(self, requirement: str) -> list[str]:
        """
        Extract key terms from a requirement for matching.

        Args:
            requirement: A single requirement string

        Returns:
            List of key terms (lowercased words)
        """
        # Remove common words and extract key terms
        common_words = {'the', 'a', 'an', 'as', 'to', 'from', 'with', 'and', 'or', 'of'}

        # Split into words, lowercase, filter common words
        words = requirement.lower().split()
        key_terms = [word for word in words if word not in common_words]

        return key_terms

    def _requirement_satisfied(
        self, requirement: str, key_terms: list[str], result: str
    ) -> bool:
        """
        Check if a requirement is satisfied by the result.

        Args:
            requirement: The original requirement string
            key_terms: Key terms extracted from requirement
            result: The actual result string

        Returns:
            True if requirement appears satisfied, False otherwise
        """
        result_lower = result.lower()

        # Simple heuristic: check if key terms appear in result
        # For "Return result as integer", check for both "integer" concept
        if "integer" in requirement.lower():
            # Check if result looks like an integer response
            # If result is just prose (no number format), requirement not satisfied
            if not any(char.isdigit() for char in result):
                return False
            # If result mentions "is" or "sum" but doesn't format as integer
            if "is" in result_lower or "sum" in result_lower:
                # Check if it's returned AS an integer (not just mentioned)
                # If it's in a sentence, it's not formatted as integer
                return False

        # Check if most key terms appear in result
        matches = sum(1 for term in key_terms if term in result_lower)

        # If less than 50% of key terms match, requirement not satisfied
        return matches >= len(key_terms) * 0.5
