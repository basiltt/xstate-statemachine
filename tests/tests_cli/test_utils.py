# tests/tests_cli/test_utils.py
# -----------------------------------------------------------------------------
# 🧪 Test Suite: CLI Utilities
# -----------------------------------------------------------------------------
# This module contains unit tests for the miscellaneous helper functions
# found in `xstate_statemachine.cli.utils`.
#
# It specifically validates the behavior of pure functions like boolean
# normalization to ensure they are robust, predictable, and handle all
# expected edge cases, such as different string inputs and case variations.
# This ensures that user input from the command line is interpreted
# consistently across the application.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import logging
import unittest

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from src.xstate_statemachine.cli.utils import normalize_bool

# -----------------------------------------------------------------------------
# 🪵 Module-level Logger
# -----------------------------------------------------------------------------
# Configures a logger for this test module to provide detailed output.
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 🏛️ Test Class: TestNormalizeBool
# -----------------------------------------------------------------------------
class TestNormalizeBool(unittest.TestCase):
    """
    Verifies the `normalize_bool` utility function.

    This test suite covers all expected behaviors of the function, including
    the normalization of various "true" and "false" string representations,
    case-insensitivity, and proper error handling for invalid inputs.
    """

    def test_normalize_true_values(self) -> None:
        """
        🧪 Ensures various 'true' strings are correctly normalized to `True`.

        This test validates that common affirmative string representations,
        such as 'true', 'yes', 'y', and '1', all correctly resolve to the
        boolean value `True`.
        """
        logger.info("✅ Testing normalization of 'true' string values.")
        # Test all recognized "true" string variations.
        self.assertTrue(normalize_bool("true"), "Failed on 'true'")
        self.assertTrue(normalize_bool("YES"), "Failed on 'YES'")
        self.assertTrue(normalize_bool("y"), "Failed on 'y'")
        self.assertTrue(normalize_bool("1"), "Failed on '1'")

    def test_normalize_false_values(self) -> None:
        """
        🧪 Ensures various 'false' strings are correctly normalized to `False`.

        This test validates that common negative string representations,
        such as 'false', 'no', 'n', and '0', all correctly resolve to the
        boolean value `False`.
        """
        logger.info("❌ Testing normalization of 'false' string values.")
        # Test all recognized "false" string variations.
        self.assertFalse(normalize_bool("false"), "Failed on 'false'")
        self.assertFalse(normalize_bool("NO"), "Failed on 'NO'")
        self.assertFalse(normalize_bool("n"), "Failed on 'n'")
        self.assertFalse(normalize_bool("0"), "Failed on '0'")

    def test_normalize_case_insensitive(self) -> None:
        """
        🧪 Confirms that boolean normalization is case-insensitive.

        This test ensures that the function correctly handles mixed-case
        inputs, which is crucial for robust user input processing from the CLI.
        """
        logger.info("🔠 Testing case-insensitive normalization.")
        # Test mixed-case values for both true and false.
        self.assertTrue(normalize_bool("TrUe"), "Failed on 'TrUe'")
        self.assertFalse(normalize_bool("fAlSe"), "Failed on 'fAlSe'")

    def test_normalize_invalid_value(self) -> None:
        """
        🧪 Verifies that an unrecognized string raises a `ValueError`.

        This test ensures the function's failure mode is correct, raising a
        `ValueError` when presented with a string that does not map to a
        boolean value.
        """
        logger.info("🚦 Testing that invalid values raise a ValueError.")
        # Assert that a completely invalid string raises the correct exception.
        with self.assertRaises(ValueError):
            normalize_bool("invalid")

    def test_normalize_empty_string(self) -> None:
        """
        🧪 Verifies that an empty string raises a `ValueError`.

        This test confirms that an empty input string is treated as invalid,
        preventing ambiguous interpretations.
        """
        logger.info("🗑️ Testing that an empty string raises a ValueError.")
        # Assert that an empty string is not considered a valid boolean.
        with self.assertRaises(ValueError):
            normalize_bool("")

    def test_normalize_other_numeric_strings(self) -> None:
        """
        🧪 Checks normalization of numeric strings beyond '0' and '1'.

        This test validates that only the specific numeric strings '0' and '1'
        are considered valid boolean representations, and all other numbers
        are rejected.
        """
        logger.info("🔢 Testing numeric strings other than '0' and '1'.")
        # Any number other than 1 or 0 should be invalid.
        with self.assertRaises(ValueError, msg="Failed to raise on '2'"):
            normalize_bool("2")
        with self.assertRaises(ValueError, msg="Failed to raise on '-1'"):
            normalize_bool("-1")

    def test_normalize_full_yes_no_variations(self) -> None:
        """
        🧪 Tests single-letter and full-word variations of 'yes' and 'no'.

        This test provides comprehensive coverage for the 'yes'/'no' style
        of boolean representation, including both full words and single-letter
        abbreviations.
        """
        logger.info("👍👎 Testing all 'yes'/'no' variations.")
        # Affirmative checks (full word and abbreviation).
        self.assertTrue(normalize_bool("yes"), "Failed on 'yes'")
        self.assertTrue(normalize_bool("Y"), "Failed on 'Y'")

        # Negative checks (full word and abbreviation).
        self.assertFalse(normalize_bool("no"), "Failed on 'no'")
        self.assertFalse(normalize_bool("N"), "Failed on 'N'")
