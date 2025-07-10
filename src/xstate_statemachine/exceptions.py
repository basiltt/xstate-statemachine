# src/xstate_statemachine/exceptions.py

# -----------------------------------------------------------------------------
# 🚨 Custom Exception Hierarchy
# -----------------------------------------------------------------------------
# This module defines a set of custom exceptions for the state machine library.
# Having a specific exception hierarchy, with a clear base class, allows for
# more precise error handling and makes the library's failure modes more
# transparent and predictable for developers.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# 📦 Imports
# -----------------------------------------------------------------------------
from typing import Optional


# -----------------------------------------------------------------------------
# 💥 Core Exception Classes
# -----------------------------------------------------------------------------


class XStateMachineError(Exception):
    """A base exception for all errors raised by this state machine library.

    Catching this exception allows you to handle any error originating from
    the state machine's logic, providing a reliable top-level error boundary.
    """

    pass


class InvalidConfigError(XStateMachineError):
    """Raised when the machine configuration is structurally invalid.

    This error indicates a problem with the machine definition itself, such as
    malformed JSON, incorrect state structure, or violations of the SCXML
    (State Chart XML) conventions.

    Example:
        >>> # This might be raised if a state is missing an 'id'.
        >>> try:
        ... # machine.from_json({...})
        ... pass
        >>> except InvalidConfigError as e:
        ... print(f"Configuration error: {e}")
    """

    pass


class StateNotFoundError(XStateMachineError):
    """Raised when a target state ID cannot be found in the machine definition.

    This can happen during a transition if the `target` string does not
    correspond to a valid state ID, or when restoring an interpreter from a

    snapshot that contains an outdated or incorrect state ID.

    Attributes:
        target (str): The state ID that could not be found.
        reference_id (Optional[str]): The ID of the state from which the
            resolution was attempted, if applicable.
    """

    def __init__(
        self, target: str, reference_id: Optional[str] = None
    ) -> None:
        """Initializes the StateNotFoundError with context-rich details.

        Args:
            target: The state ID that could not be found.
            reference_id: The optional source state ID from which the
                lookup was performed. This provides more context for debugging.
        """
        # 🧍‍♂️ Store the context of the error for programmatic access.
        self.target = target
        self.reference_id = reference_id

        # ✍️ Craft a detailed error message based on the available information.
        if reference_id:
            message = (
                f"Could not resolve target state '{target}' "
                f"from state '{reference_id}'."
            )
        else:
            message = f"Could not resolve target state '{target}'."

        # 🚀 Call the parent constructor with the final, informative message.
        super().__init__(message)


class ImplementationMissingError(XStateMachineError):
    """Raised when a referenced action, guard, or service is not implemented.

    This error occurs when the machine definition refers to a named
    action, guard, or service (e.g., `actions: "myAction"`), but no
    corresponding function is provided in the machine's implementation logic.

    Example:
        >>> # If machine is defined with `guards: { "userIsAdmin": ... }`
        >>> # but "userIsAdmin" is not provided in the implementation object.
        >>> try:
        ... # interpreter.send("SOME_EVENT")
        ... pass
        >>> except ImplementationMissingError as e:
        ... print(f"Missing implementation: {e}")
    """

    pass


class ActorSpawningError(XStateMachineError):
    """Raised when there is an error spawning or communicating with a child actor.

    This is specific to machines that use the `invoke` property with a machine
    source, creating a parent-child relationship between state machine interpreters.
    Failures in creating the child interpreter or issues with the communication
    channel will trigger this error.
    """

    pass


class NotSupportedError(XStateMachineError):
    """Raised for features incompatible with the current interpreter mode.

    This is most commonly used to prevent the use of asynchronous operations
    (like `async def` actions) within the purely synchronous `SyncInterpreter`.
    It enforces a clean separation of concerns between the two execution modes.

    Example:
        >>> # Using SyncInterpreter with an async action
        >>> try:
        ... # sync_interpreter.send("EVENT_WITH_ASYNC_ACTION")
        ... pass
        >>> except NotSupportedError as e:
        ... print(f"Compatibility error: {e}")
    """

    pass
