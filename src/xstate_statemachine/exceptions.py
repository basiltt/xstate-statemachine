# src/xstate_statemachine/exceptions.py

# -----------------------------------------------------------------------------
# 🚨 Custom Exceptions
# -----------------------------------------------------------------------------
# Defining specific exceptions improves error handling and makes the library's
# failure modes clearer to the user.
# -----------------------------------------------------------------------------


class XStateMachineError(Exception):
    """Base exception for all errors raised by this library."""

    pass


class InvalidConfigError(XStateMachineError):
    """Raised when the machine configuration JSON is invalid."""

    pass


class StateNotFoundError(XStateMachineError):
    """Raised when a target state cannot be resolved."""

    # ✅ FIX: Made `reference_id` optional and updated the message logic.
    def __init__(self, target: str, reference_id: str = None):
        self.target = target
        self.reference_id = reference_id
        if reference_id:
            message = f"Could not resolve target state '{target}' from state '{reference_id}'."
        else:
            message = f"Could not resolve target state '{target}'."
        super().__init__(message)


class ImplementationMissingError(XStateMachineError):
    """Raised when an action, guard, or service implementation is missing."""

    pass


class ActorSpawningError(XStateMachineError):
    """Raised when there is an error spawning or communicating with an actor."""

    pass


class NotSupportedError(XStateMachineError):
    """
    Raised when a feature is used that is not supported by the current
    interpreter mode (e.g., calling an async action in the SyncInterpreter).
    """

    pass
