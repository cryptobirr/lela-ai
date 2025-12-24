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

    # Words to filter out when extracting key terms
    _COMMON_WORDS = frozenset({"the", "a", "an", "as", "to", "from", "with", "and", "or", "of"})

    # Match threshold for requirement satisfaction (50% of key terms must match)
    _MATCH_THRESHOLD = 0.5

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
        lines = instructions.strip().split("\n")
        requirements = []

        for line in lines:
            cleaned_line = self._clean_requirement_line(line)
            if cleaned_line:
                requirements.append(cleaned_line)

        return requirements

    def _clean_requirement_line(self, line: str) -> str:
        """
        Clean a single requirement line by removing whitespace and numbering.

        Args:
            line: Raw requirement line

        Returns:
            Cleaned requirement string (empty if line was only whitespace/numbering)
        """
        # Remove leading/trailing whitespace
        line = line.strip()

        # Return empty for blank lines
        if not line:
            return ""

        # Remove numbered list prefix (1. 2. etc.)
        cleaned = re.sub(r"^\d+\.\s*", "", line)

        return cleaned

    def _extract_key_terms(self, requirement: str) -> list[str]:
        """
        Extract key terms from a requirement for matching.

        Args:
            requirement: A single requirement string

        Returns:
            List of key terms (lowercased words, common words filtered)
        """
        # Split into words, lowercase, filter common words
        words = requirement.lower().split()
        key_terms = [word for word in words if word not in self._COMMON_WORDS]

        return key_terms

    def _requirement_satisfied(self, requirement: str, key_terms: list[str], result: str) -> bool:
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
        requirement_lower = requirement.lower()

        # Check type-specific requirements
        if "integer" in requirement_lower:
            if not self._has_integer_format(result, result_lower):
                return False

        # Check if majority of key terms appear in result
        matches = sum(1 for term in key_terms if term in result_lower)

        return matches >= len(key_terms) * self._MATCH_THRESHOLD

    def _has_integer_format(self, result: str, result_lower: str) -> bool:
        """
        Check if result is formatted as an integer (not just mentioning a number).

        Args:
            result: Original result string
            result_lower: Lowercased result string

        Returns:
            True if result appears to be formatted as an integer
        """
        # Result must contain at least one digit
        if not any(char.isdigit() for char in result):
            return False

        # If result contains prose indicators, it's not formatted as integer
        prose_indicators = ["is", "sum", "the"]
        if any(indicator in result_lower for indicator in prose_indicators):
            return False

        return True
