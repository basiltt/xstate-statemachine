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


class TestCamelToSnakeUnicode(unittest.TestCase):
    """Python identifiers may contain Unicode letters (PEP 3131). The
    sanitiser was ASCII-only, so every Cyrillic / CJK / accented name
    collapsed to the empty-name fallback `machine` -- and a machine with
    ten such actions generated ten methods all called `machine`, each
    silently overriding the last (subscription_ru.json in the corpus)."""

    def test_unicode_letters_are_kept(self) -> None:
        from src.xstate_statemachine.cli.utils import camel_to_snake

        out = camel_to_snake("Запомнить дату окончания подписки")
        self.assertTrue(out.isidentifier(), out)
        self.assertEqual(out, "запомнить_дату_окончания_подписки")
        self.assertEqual(
            camel_to_snake("überprüfen Status"), "überprüfen_status"
        )

    def test_distinct_unicode_names_stay_distinct(self) -> None:
        from src.xstate_statemachine.cli.utils import camel_to_snake

        names = ["Проверить статус", "Отправить письмо", "Закрыть"]
        self.assertEqual(len({camel_to_snake(n) for n in names}), 3)

    def test_ascii_behaviour_is_unchanged(self) -> None:
        from src.xstate_statemachine.cli.utils import camel_to_snake

        for raw, want in (
            ("fetchUserData", "fetch_user_data"),
            ("HTTPRequest", "http_request"),
            ("inline:m.a#entry[0]", "inline_m_a_entry_0"),
            ("  ", "machine"),
            ("2fa", "_2fa"),
        ):
            self.assertEqual(camel_to_snake(raw), want, raw)


class TestModuleSafeName(unittest.TestCase):
    """A machine id that is also a stdlib module name must not become the
    generated file's stem: `token.py` shadowed the stdlib `token` that
    `logging` imports, and the runner died mid-import with a message that
    named neither the cause nor the file (Token.json in the corpus)."""

    def test_stdlib_names_get_a_suffix(self) -> None:
        from src.xstate_statemachine.cli.utils import module_safe_name

        for name in ("token", "queue", "email", "types", "json", "logging"):
            self.assertEqual(module_safe_name(name), f"{name}_machine")

    def test_ordinary_names_are_unchanged(self) -> None:
        from src.xstate_statemachine.cli.utils import module_safe_name

        for name in ("checkout", "traffic_light", "order_flow", "auth"):
            self.assertEqual(module_safe_name(name), name)
