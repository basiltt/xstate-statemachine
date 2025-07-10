# /tests/test_exceptions.py
# -----------------------------------------------------------------------------
# 🧪 Test Suite: Custom Exception Hierarchy
# -----------------------------------------------------------------------------
# This module contains the unit tests for the custom exceptions defined in
# `src.xstate_statemachine.exceptions`. It verifies the correctness of the
# exception hierarchy, ensuring that all custom exceptions properly inherit
# from the base `XStateMachineError`.
#
# The tests also validate the behavior of specific exceptions, such as the
# formatting of context-rich error messages in `StateNotFoundError`, to
# guarantee that developers receive clear and useful feedback when errors occur.
# -----------------------------------------------------------------------------
"""
Test suite for validating the custom exception hierarchy of the library.
"""

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import logging
import unittest

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from src.xstate_statemachine.exceptions import (
    ActorSpawningError,
    ImplementationMissingError,
    InvalidConfigError,
    NotSupportedError,
    StateNotFoundError,
    XStateMachineError,
)

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
# Basic logging setup to show test execution status if run verbosely.
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 🧪 Test Class Definition
# -----------------------------------------------------------------------------


class TestExceptions(unittest.TestCase):
    """A collection of unit tests for the custom exception classes."""

    # -------------------------------------------------------------------------
    # 🏛️ Hierarchy and Inheritance Tests
    # -------------------------------------------------------------------------

    def test_all_custom_exceptions_inherit_from_base(self) -> None:
        """Ensures all defined custom exceptions inherit from XStateMachineError.

        This test validates the core design of the exception hierarchy, confirming
        that a single `except XStateMachineError:` block can catch any error
        originating from this library.
        """
        logger.info(
            "🧪 Testing if all custom exceptions inherit from XStateMachineError"
        )
        # Arrange: Define all specific exception classes.
        custom_exceptions = [
            InvalidConfigError,
            StateNotFoundError,
            ImplementationMissingError,
            ActorSpawningError,
            NotSupportedError,
        ]

        # Act & Assert: Loop through each and check its lineage.
        for exc in custom_exceptions:
            with self.subTest(exception=exc.__name__):
                self.assertTrue(
                    issubclass(exc, XStateMachineError),
                    f"❌ {exc.__name__} should inherit from XStateMachineError.",
                )

    def test_base_exception_catch(self) -> None:
        """Verifies a try/except for XStateMachineError catches all custom exceptions.

        This test provides practical validation of the "is-a" relationship,
        ensuring the base exception acts as a reliable catch-all.
        """
        logger.info(
            "🧪 Testing if the base exception class can catch all child exceptions"
        )
        # Arrange: Create instances of all specific exceptions.
        custom_exceptions = [
            InvalidConfigError("test"),
            StateNotFoundError("test"),
            ImplementationMissingError("test"),
            ActorSpawningError("test"),
            NotSupportedError("test"),
        ]

        # Act & Assert: Ensure each one is caught by the base class.
        for exc in custom_exceptions:
            with self.subTest(exception=type(exc).__name__):
                try:
                    raise exc
                except XStateMachineError:
                    # ✅ This is the expected success path.
                    pass
                except Exception:
                    # ❌ This block should never be reached.
                    self.fail(
                        f"{type(exc).__name__} was not caught by XStateMachineError"
                    )

    def test_catching_specific_then_general_exception(self) -> None:
        """Ensures a specific exception is caught before its general base class.

        This validates standard Python `try...except` block ordering, confirming
        that developers can handle specific errors before falling back to a
        general handler.
        """
        logger.info(
            "🧪 Testing that specific exception handlers are prioritized"
        )
        # Arrange, Act, Assert
        try:
            raise StateNotFoundError("test")
        except StateNotFoundError:
            # ✅ This is the correct, expected block to be executed.
            pass
        except XStateMachineError:
            # ❌ If this block is reached, the test fails.
            self.fail(
                "StateNotFoundError was caught by the base XStateMachineError first."
            )

    # -------------------------------------------------------------------------
    # 📝 Message and Attribute Formatting Tests
    # -------------------------------------------------------------------------

    def test_state_not_found_error_message_with_reference(self) -> None:
        """Verifies StateNotFoundError formats its message with a reference state."""
        logger.info(
            "🧪 Testing StateNotFoundError message with reference context"
        )
        # Arrange
        err = StateNotFoundError(
            target=".unknown", reference_id="parent.state"
        )
        expected_msg = "Could not resolve target state '.unknown' from state 'parent.state'."

        # Act & Assert
        self.assertEqual(str(err), expected_msg)

    def test_state_not_found_error_message_without_reference(self) -> None:
        """Verifies StateNotFoundError formats its message without a reference state."""
        logger.info(
            "🧪 Testing StateNotFoundError message without reference context"
        )
        # Arrange
        err = StateNotFoundError(target="nonexistent")
        expected_msg = "Could not find state with ID 'nonexistent'."

        # Act & Assert
        self.assertEqual(str(err), expected_msg)

    def test_state_not_found_error_attributes(self) -> None:
        """Ensures StateNotFoundError correctly stores target and reference_id."""
        logger.info("🧪 Testing StateNotFoundError attribute storage")
        # Arrange
        err = StateNotFoundError("target_state", "source_state")

        # Act & Assert
        self.assertEqual(err.target, "target_state")
        self.assertEqual(err.reference_id, "source_state")

    def test_exception_message_is_stored(self) -> None:
        """Verifies that the message passed to an exception is retrievable."""
        logger.info("🧪 Testing basic exception message storage")
        # Arrange
        message = "This is a unique error message."
        err = NotSupportedError(message)

        # Act & Assert
        self.assertEqual(str(err), message)

    # -------------------------------------------------------------------------
    # 💥 Instantiation and Behavior Tests
    # -------------------------------------------------------------------------

    def test_invalid_config_error_instantiation(self) -> None:
        """Verifies InvalidConfigError can be raised and caught correctly."""
        logger.info("🧪 Testing InvalidConfigError instantiation")
        with self.assertRaises(InvalidConfigError):
            raise InvalidConfigError("Bad config")

    def test_implementation_missing_error_instantiation(self) -> None:
        """Verifies ImplementationMissingError can be raised and caught correctly."""
        logger.info("🧪 Testing ImplementationMissingError instantiation")
        with self.assertRaises(ImplementationMissingError):
            raise ImplementationMissingError("Missing function")

    def test_actor_spawning_error_instantiation(self) -> None:
        """Verifies ActorSpawningError can be raised and caught correctly."""
        logger.info("🧪 Testing ActorSpawningError instantiation")
        with self.assertRaises(ActorSpawningError):
            raise ActorSpawningError("Actor failed to spawn")

    def test_not_supported_error_instantiation(self) -> None:
        """Verifies NotSupportedError can be raised and caught correctly."""
        logger.info("🧪 Testing NotSupportedError instantiation")
        with self.assertRaises(NotSupportedError):
            raise NotSupportedError("Feature not available")

    def test_can_raise_without_message(self) -> None:
        """Ensures exceptions can be raised without an explicit message."""
        logger.info("🧪 Testing raising exceptions without a message")
        try:
            raise ActorSpawningError
        except ActorSpawningError as e:
            # The default string representation should be empty.
            self.assertEqual(str(e), "")

    def test_exception_equality(self) -> None:
        """Ensures different instances of an exception are not equal."""
        logger.info("🧪 Testing that exception instances are unique objects")
        # Arrange
        e1 = InvalidConfigError("message")
        e2 = InvalidConfigError("message")

        # Act & Assert
        self.assertIsNot(e1, e2)
        self.assertNotEqual(e1, e2)

    def test_custom_exception_hierarchy(self) -> None:
        """Ensures a specific child exception inherits from XStateMachineError.

        This test serves as a simple, direct check on a single exception's
        lineage, complementing the more comprehensive test that checks all
        exceptions in the hierarchy.
        """
        # 🧪 Arrange: This test focuses on a single, representative exception.
        logger.info(
            "🧪 Testing if ImplementationMissingError specifically inherits from XStateMachineError"
        )

        # 🚀 Act & Assert: Confirm the 'is-a' relationship.
        self.assertTrue(
            issubclass(ImplementationMissingError, XStateMachineError),
            "❌ ImplementationMissingError should be a subclass of XStateMachineError.",
        )
