# tests/test_exceptions.py
import unittest
import logging

from src.xstate_statemachine.exceptions import (
    XStateMachineError,
    InvalidConfigError,
    StateNotFoundError,
    ImplementationMissingError,
    ActorSpawningError,
    NotSupportedError,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestExceptions(unittest.TestCase):
    """
    Test suite for the custom exception hierarchy.
    """

    def test_custom_exception_hierarchy(self) -> None:
        """Ensures ImplementationMissingError inherits from XStateMachineError."""
        self.assertTrue(
            issubclass(ImplementationMissingError, XStateMachineError)
        )

    def test_all_custom_exceptions_inherit_from_base(self) -> None:
        """Ensures all defined custom exceptions inherit from XStateMachineError."""
        custom_exceptions = [
            InvalidConfigError,
            StateNotFoundError,
            ImplementationMissingError,
            ActorSpawningError,
            NotSupportedError,
        ]
        for exc in custom_exceptions:
            with self.subTest(exception=exc.__name__):
                self.assertTrue(issubclass(exc, XStateMachineError))

    def test_state_not_found_error_message_with_reference(self) -> None:
        """StateNotFoundError should format its message correctly with a reference state."""
        err = StateNotFoundError(
            target=".unknown", reference_id="parent.state"
        )
        expected_msg = "Could not resolve target state '.unknown' from state 'parent.state'."
        self.assertEqual(str(err), expected_msg)

    def test_state_not_found_error_message_without_reference(self) -> None:
        """StateNotFoundError should format its message correctly without a reference state."""
        err = StateNotFoundError(target="nonexistent")

        # ✅ FIX: Updated the expected message to match the new, more precise
        # error string from the updated StateNotFoundError class.
        expected_msg = "Could not find state with ID 'nonexistent'."

        self.assertEqual(str(err), expected_msg)

    # ---------- 10 New Tests ----------

    def test_base_exception_catch(self) -> None:
        """A try/except block for XStateMachineError should catch all custom exceptions."""
        custom_exceptions = [
            InvalidConfigError("test"),
            StateNotFoundError("test"),
            ImplementationMissingError("test"),
            ActorSpawningError("test"),
            NotSupportedError("test"),
        ]
        for exc in custom_exceptions:
            with self.subTest(exception=type(exc).__name__):
                try:
                    raise exc
                except XStateMachineError:
                    pass  # Success
                except Exception:
                    self.fail(
                        f"{type(exc).__name__} was not caught by XStateMachineError"
                    )

    def test_invalid_config_error_instantiation(self) -> None:
        """InvalidConfigError can be raised and caught."""
        with self.assertRaises(InvalidConfigError):
            raise InvalidConfigError("Bad config")

    def test_implementation_missing_error_instantiation(self) -> None:
        """ImplementationMissingError can be raised and caught."""
        with self.assertRaises(ImplementationMissingError):
            raise ImplementationMissingError("Missing function")

    def test_actor_spawning_error_instantiation(self) -> None:
        """ActorSpawningError can be raised and caught."""
        with self.assertRaises(ActorSpawningError):
            raise ActorSpawningError("Actor failed to spawn")

    def test_not_supported_error_instantiation(self) -> None:
        """NotSupportedError can be raised and caught."""
        with self.assertRaises(NotSupportedError):
            raise NotSupportedError("Feature not available")

    def test_state_not_found_error_attributes(self) -> None:
        """StateNotFoundError should store target and reference_id."""
        err = StateNotFoundError("target_state", "source_state")
        self.assertEqual(err.target, "target_state")
        self.assertEqual(err.reference_id, "source_state")

    def test_exception_equality(self) -> None:
        """Different instances of the same custom exception should not be equal."""
        e1 = InvalidConfigError("message")
        e2 = InvalidConfigError("message")
        self.assertNotEqual(e1, e2)

    def test_catching_specific_then_general_exception(self) -> None:
        """A specific exception should be caught before its general base class."""
        try:
            raise StateNotFoundError("test")
        except StateNotFoundError:
            pass  # Expected
        except XStateMachineError:
            self.fail(
                "StateNotFoundError was caught by the base XStateMachineError first."
            )

    def test_exception_message_is_stored(self) -> None:
        """The message passed to an exception should be retrievable."""
        message = "This is a unique error message."
        err = NotSupportedError(message)
        self.assertEqual(str(err), message)

    def test_can_raise_without_message(self) -> None:
        """Exceptions should be raisable without an explicit message."""
        try:
            raise ActorSpawningError
        except ActorSpawningError as e:
            self.assertEqual(str(e), "")
