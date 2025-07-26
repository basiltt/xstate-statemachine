# tests_cli/test_utils.py
# -----------------------------------------------------------------------------
# 🧪 Test Suite: CLI Utilities
# -----------------------------------------------------------------------------
# This module contains unit tests for the miscellaneous helper functions
# found in `xstate_statemachine.cli.utils`.
#
# It specifically validates the behavior of pure functions like boolean
# normalization to ensure they are robust and handle all expected edge cases.
# -----------------------------------------------------------------------------
"""
Unit tests for the CLI utility functions.
"""

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import logging
import unittest

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from xstate_statemachine.cli.utils import normalize_bool

# -----------------------------------------------------------------------------
# 🪵 Module-level Logger
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 🏛️ Test Class: TestNormalizeBool
# -----------------------------------------------------------------------------


class TestNormalizeBool(unittest.TestCase):
    """
    Verifies the `normalize_bool` utility function.
    """

    def test_normalize_true_values(self) -> None:
        """
        Ensures various 'true' strings are correctly normalized to `True`.
        """
        logger.info("🧪 Testing normalization of 'true' string values.")
        # ✅ Test all recognized "true" variations.
        self.assertTrue(normalize_bool("true"))
        self.assertTrue(normalize_bool("YES"))
        self.assertTrue(normalize_bool("y"))
        self.assertTrue(normalize_bool("1"))

    def test_normalize_false_values(self) -> None:
        """
        Ensures various 'false' strings are correctly normalized to `False`.
        """
        logger.info("🧪 Testing normalization of 'false' string values.")
        # ✅ Test all recognized "false" variations.
        self.assertFalse(normalize_bool("false"))
        self.assertFalse(normalize_bool("NO"))
        self.assertFalse(normalize_bool("n"))
        self.assertFalse(normalize_bool("0"))

    def test_normalize_case_insensitive(self) -> None:
        """
        Confirms that boolean normalization is case-insensitive.
        """
        logger.info("🧪 Testing case-insensitive normalization.")
        # ✅ Test mixed-case values.
        self.assertTrue(normalize_bool("TrUe"))
        self.assertFalse(normalize_bool("FaLsE"))

    def test_normalize_invalid_value(self) -> None:
        """
        Verifies that an unrecognized string raises a `ValueError`.
        """
        logger.info("🧪 Testing that invalid values raise a ValueError.")
        # ❌ Assert that a completely invalid string raises the correct exception.
        with self.assertRaises(ValueError):
            normalize_bool("invalid")

    def test_normalize_empty_string(self) -> None:
        """
        Verifies that an empty string raises a `ValueError`.
        """
        logger.info("🧪 Testing that an empty string raises a ValueError.")
        # ❌ Assert that an empty string is not considered a valid boolean.
        with self.assertRaises(ValueError):
            normalize_bool("")

    def test_normalize_other_numeric_strings(self) -> None:
        """
        Checks normalization of numeric strings beyond '0' and '1'.
        """
        logger.info("🧪 Testing numeric strings other than '0' and '1'.")
        # ❌ Any number other than 1 or 0 should be invalid.
        with self.assertRaises(ValueError):
            normalize_bool("2")
        with self.assertRaises(ValueError):
            normalize_bool("-1")

    def test_normalize_full_yes_no_variations(self) -> None:
        """
        Tests single-letter and full-word variations of 'yes' and 'no'.
        """
        logger.info("🧪 Testing all 'yes'/'no' variations.")
        # ✅ Affirmative checks.
        self.assertTrue(normalize_bool("yes"))
        self.assertTrue(normalize_bool("Y"))
        # ❌ Negative checks.
        self.assertFalse(normalize_bool("no"))
        self.assertFalse(normalize_bool("N"))
