# /src/xstate_statemachine/exceptions.py
# -----------------------------------------------------------------------------
# 🚨 Custom Exception Hierarchy
# -----------------------------------------------------------------------------
# This module defines a set of custom exceptions for the state machine library.
# Having a specific exception hierarchy, with a clear base class, allows for
# more precise error handling and makes the library's failure modes more
# transparent and predictable for developers.
#
# This approach follows best practices by providing a single, catchable base
# exception (`XStateMachineError`) while also offering granular error types
# for more specific handling, improving the robustness and usability of the
# library.
# -----------------------------------------------------------------------------
"""
Defines a clear and specific exception hierarchy for the state machine library.

This allows consumers of the library to write robust error-handling logic.

Example:
    A demonstration of catching a specific vs. a general library error.

    >>> from xstate_statemachine import XStateMachineError, StateNotFoundError
    >>>
    >>> def run_some_machine_logic(should_succeed):
    ...     if not should_succeed:
    ...         # In a real scenario, the library would raise this internally.
    ...         raise StateNotFoundError(target="some.missing.state")
    ...     return "✅ Success"
    ...
    >>> try:
    ...     run_some_machine_logic(should_succeed=False)
    ... except StateNotFoundError as e:
    ...     # Handle a specific, recoverable error
    ...     print(f"Caught a specific error: {e}")
    ... except XStateMachineError:
    ...     # Handle any other library-specific error
    ...     print("Caught a general state machine error.")
    Caught a specific error: Could not find state with ID 'some.missing.state'.
"""

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
from typing import Optional


# -----------------------------------------------------------------------------
# 💥 Core Exception Classes
# -----------------------------------------------------------------------------


class XStateMachineError(Exception):
    """A base exception for all errors raised by this state machine library.

    Catching this exception allows a developer to handle any error originating
    from the state machine's logic, providing a reliable top-level error
    boundary. It is the common ancestor for all other exceptions in this module.
    """

    pass


class InvalidConfigError(XStateMachineError):
    """Raised when the machine configuration is structurally invalid.

    This error indicates a fundamental problem with the machine definition
    itself, such as malformed JSON, a missing 'id' or 'states' key, or
    other violations of the expected statechart structure.

    Example:
        >>> from xstate_statemachine import create_machine
        >>>
        >>> # This config is invalid because the root 'id' key is missing.
        >>> invalid_config = {"initial": "on", "states": {"on": {}}}
        >>> try:
        ...     create_machine(invalid_config)
        ... except InvalidConfigError as e:
        ...     print(e)
        Invalid config: must be a dict with 'id' and 'states' keys.
    """

    pass


class StateNotFoundError(XStateMachineError):
    """Raised when a target state ID cannot be found in the machine definition.

    This can happen during a transition if the `target` string does not
    correspond to a valid state ID, or when restoring an interpreter from a
    snapshot that contains an outdated or incorrect state ID.

    Attributes:
        target (str): The state ID string that could not be found.
        reference_id (Optional[str]): The ID of the state from which the
            resolution was attempted, providing valuable debugging context.
    """

    def __init__(
        self, target: str, reference_id: Optional[str] = None
    ) -> None:
        """Initializes the StateNotFoundError with context-rich details.

        Args:
            target: The state ID that could not be found.
            reference_id: The optional source state ID from which the
                lookup was performed. This provides more context for
                debugging.
        """
        # 🧍‍♂️ Store the context of the error for programmatic access.
        self.target = target
        self.reference_id = reference_id

        # ✍️ Craft a detailed, human-readable error message.
        if reference_id:
            message = (
                f"Could not resolve target state '{target}' "
                f"from state '{reference_id}'."
            )
        else:
            message = f"Could not find state with ID '{target}'."

        # 🚀 Call the parent constructor with the final, informative message.
        super().__init__(message)


class ImplementationMissingError(XStateMachineError):
    """Raised when a referenced action, guard, or service is not implemented.

    This error occurs when the machine definition refers to a named
    action, guard, or service (e.g., `"actions": ["myAction"]`), but no
    corresponding Python function is provided in the machine's implementation
    logic. This enforces a complete and correct binding between the machine's
    definition and its behavior.

    Example:
        >>> from xstate_statemachine import create_machine, SyncInterpreter, MachineLogic
        >>>
        >>> # The JSON config references a guard named "userIsAdmin".
        >>> config = {
        ...   "id": "test", "initial": "s1",
        ...   "states": {
        ...     "s1": {"on": {"EVENT": {"target": "s2", "guard": "userIsAdmin"}}},
        ...     "s2": {}
        ...   }
        ... }
        >>> # But the logic provided is empty.
        >>> logic = MachineLogic()
        >>> try:
        ...    machine = create_machine(config, logic=logic)
        ...    interpreter = SyncInterpreter(machine).start()
        ...    # This `send` will cause the interpreter to look for the guard.
        ...    interpreter.send("EVENT")
        ... except ImplementationMissingError as e:
        ...    print(e)
        Guard 'userIsAdmin' not implemented.
    """

    pass


class ActorSpawningError(XStateMachineError):
    """Raised when there is an error spawning a child actor machine.

    This is specific to machines that use `invoke` with a machine source or a
    `spawn_*` action. This error indicates a failure in the underlying
    mechanism of creating the child interpreter, often because the provided
    service did not return a valid `MachineNode`.
    """

    pass


class NotSupportedError(XStateMachineError):
    """Raised for features incompatible with the current interpreter mode.

    This is most commonly used to prevent the use of asynchronous operations
    (like `async def` actions or `after` timers) within the purely
    synchronous `SyncInterpreter`. It enforces a clean separation of concerns
    between the two execution modes and prevents subtle concurrency bugs.

    Example:
        >>> from xstate_statemachine import create_machine, SyncInterpreter
        >>>
        >>> # A machine with an `after` timer, which requires asyncio.
        >>> config = {
        ...   "id": "timer", "initial": "a",
        ...   "states": {"a": {"after": {"100": "b"}}, "b": {}}
        ... }
        >>> machine = create_machine(config)
        >>> # Attempting to run it with the SyncInterpreter.
        >>> try:
        ...     SyncInterpreter(machine).start()
        ... except NotSupportedError as e:
        ...     print(e)
        `after` transitions are not supported by SyncInterpreter.
    """

    pass
