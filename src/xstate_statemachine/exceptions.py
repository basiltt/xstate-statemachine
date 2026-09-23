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
from typing import Iterable, Optional

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
        >>> from xstate_statemachine import InvalidConfigError, create_machine
        >>>
        >>> # This config is invalid because the root 'id' key is missing.
        >>> invalid_config = {"initial": "on", "states": {"on": {}}}
        >>> try:
        ...     create_machine(invalid_config)
        ... except InvalidConfigError as e:
        ...     print(e)
        ❌ Machine configuration must have a root 'id'.
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

    This is used to prevent the use of `async def` actions and services within
    the purely synchronous `SyncInterpreter`. It enforces a clean separation of
    concerns between the two execution modes and prevents subtle concurrency
    bugs.

    📝 Note: `after` (delayed) transitions ARE supported by `SyncInterpreter`
    since v0.4.1, where they are backed by background threads rather than
    asyncio timers. Only genuinely coroutine-based logic is rejected.

    Example:
        >>> from xstate_statemachine import (
        ...     MachineLogic, NotSupportedError, SyncInterpreter, create_machine
        ... )
        >>>
        >>> async def async_action(interpreter, ctx, event, action_def):
        ...     pass
        >>>
        >>> # A machine whose entry action is a coroutine function.
        >>> config = {
        ...   "id": "m", "initial": "a",
        ...   "states": {"a": {"entry": "async_action"}}
        ... }
        >>> machine = create_machine(
        ...     config, logic=MachineLogic(actions={"async_action": async_action})
        ... )
        >>> # Attempting to run it with the SyncInterpreter.
        >>> try:
        ...     SyncInterpreter(machine).start()
        ... except NotSupportedError as e:
        ...     print(e)
        Async action 'async_action' not supported by SyncInterpreter.
    """

    pass


class RestoredError(XStateMachineError):
    """Carries an error message recovered from a persisted snapshot.

    The original exception type cannot survive JSON serialisation, so
    :meth:`BaseInterpreter.from_snapshot` wraps the recorded message in this
    class. It preserves *what went wrong* for a machine restored in the
    `error` status, which would otherwise expose `error is None`.
    """

    pass


class UnhandledEventError(XStateMachineError):
    """Raised when an event selects no transition and ``onUnhandled`` is ``"error"``.

    🏛️ Per XState an unhandled event is silently ignored, and that remains
    the default. On a critical path — an order lifecycle, a payment — a
    typo'd event name being a silent no-op is exactly the failure that no
    test can catch. Setting ``"onUnhandled": "error"`` on the machine turns
    it into this exception instead.

    Attributes:
        event_type: The type of the event that matched nothing.
        active_states: The state ids that were active when it arrived.
    """

    def __init__(self, event_type: str, active_states: Iterable[str]):
        self.event_type = event_type
        self.active_states = sorted(active_states)
        super().__init__(
            f"Event '{event_type}' is not handled in any active state "
            f"{self.active_states} and the machine's onUnhandled policy "
            f"is 'error'."
        )


class TransitionFailedError(XStateMachineError):
    """Raised when ``actionErrorPolicy`` is ``"fail"`` and an action raised.

    Wraps the original exception (available as ``__cause__``) and records
    which action failed so the caller can act on it programmatically.

    Attributes:
        action_type: The ``type`` of the action that raised.
        source_state: The id of the state the transition left from.
    """

    def __init__(self, action_type: str, source_state: str):
        self.action_type = action_type
        self.source_state = source_state
        super().__init__(
            f"Action '{action_type}' raised during a transition from "
            f"'{source_state}'; the transition was rolled back and the "
            f"machine stopped (actionErrorPolicy='fail')."
        )


class SnapshotVersionError(XStateMachineError):
    """Raised when a snapshot's ``version`` is outside what the caller accepts.

    A snapshot's ``version`` is an integer bumped only when the payload
    layout changes. Older versions are upcast transparently; a newer one
    cannot be read safely, so restoring it is refused rather than guessed.

    #205: also raised when the version is BELOW the caller's
    ``from_snapshot(minimum_version=...)`` floor. A version-0 payload
    carries no ``machine_hash`` and is accepted without a drift check by
    design; a caller who never wrote v0 payloads can refuse them (a
    "downgrade" of a tampered blob) by setting ``minimum_version=1``.

    Attributes:
        found: The version recorded in the snapshot.
        supported: The highest version this library can read.
        minimum: The caller's floor, when that is what was violated.
    """

    def __init__(
        self, found: int, supported: int, *, minimum: Optional[int] = None
    ):
        self.found = found
        self.supported = supported
        self.minimum = minimum
        if minimum is not None:
            super().__init__(
                f"Snapshot version {found} is below the caller's "
                f"minimum_version={minimum}. A payload this old carries "
                f"no drift fingerprint; refuse it, or lower the floor if "
                f"the source is trusted."
            )
            return
        super().__init__(
            f"Snapshot version {found} is newer than the supported version "
            f"{supported}. Upgrade xstate-statemachine to restore it."
        )


class SnapshotDriftError(XStateMachineError):
    """Raised when a snapshot does not belong to the machine restoring it.

    Either the recorded ``machine_id`` differs, or the machine's structural
    hash (states, transitions, guard/action names, invokes, delays) has
    changed since the snapshot was taken -- a guard added, a state renamed.
    Pass ``verify_machine_hash=False`` to `from_snapshot` when the drift is
    known to be compatible and the application has migrated the payload.
    """

    pass


class QueueOverflowError(XStateMachineError):
    """Raised by ``send()`` when a BOUNDED inbox is full (#38).

    Only when the interpreter was built with ``max_queue_size`` and the
    ``OverflowPolicy.RAISE`` policy (the default once a bound is set).

    Attributes:
        interpreter_id: Which machine refused the event.
        depth: Events queued at the moment of refusal.
        maxsize: The configured bound.
    """

    def __init__(self, interpreter_id: str, depth: int, maxsize: int):
        self.interpreter_id = interpreter_id
        self.depth = depth
        self.maxsize = maxsize
        super().__init__(
            f"Interpreter '{interpreter_id}' inbox is full ({depth}/"
            f"{maxsize}); event refused. Shed load, slow the producer, or "
            f"raise max_queue_size."
        )


class InterpreterStoppedError(XStateMachineError):
    """Resolves a ``send(wait=True)`` receipt when the machine stopped, or
    dropped the event, before that event was processed (#39)."""

    pass


class UnknownEventError(XStateMachineError):
    """Raised under ``strict`` when an event type is not declared anywhere
    in the machine (#51).

    Distinct from an event that IS declared but not handled by the current
    state -- that is a normal, silently ignored no-op per XState. Unknown
    means a typo or an outdated producer, which is a bug.

    Attributes:
        event_type: The offending type.
        machine_id: The machine that refused it.
        known: The declared descriptor set, sorted.
    """

    def __init__(self, event_type: str, machine_id: str, known: "list[str]"):
        import difflib

        from .events import ENGINE_EVENT_SHAPES

        self.event_type = event_type
        self.machine_id = machine_id
        self.known = known
        if event_type.startswith(ENGINE_EVENT_SHAPES):
            # 🛡️ #195: the name is one only the ENGINE may author. Say so
            #    instead of suggesting the caller "meant" the very name it
            #    sent -- a `DoneEvent("done.invoke.k", ...)` built by hand
            #    is refused as user traffic, not as a typo.
            super().__init__(
                f"Event '{event_type}' is an engine-generated name and "
                f"cannot be sent as user traffic to machine '{machine_id}'. "
                f"Completions (`done.invoke.*`, `error.platform.*`), "
                f"timers (`after.*`) and engine sentinels are minted by "
                f"the interpreter when the work they describe actually "
                f"happens; a hand-built one is refused under strict mode."
            )
            return
        hint = difflib.get_close_matches(event_type, known, n=1, cutoff=0.6)
        suggestion = f" Did you mean '{hint[0]}'?" if hint else ""
        shown = ", ".join(known[:20]) + (" ..." if len(known) > 20 else "")
        super().__init__(
            f"Event '{event_type}' is not declared by machine "
            f"'{machine_id}'. Known events: {shown}.{suggestion}"
        )


class InvalidEventPayloadError(XStateMachineError):
    """Raised when an event's payload fails its declared schema (#51).

    Attributes:
        event_type: The event whose payload was rejected.
        cause: The exception the validator raised.
    """

    def __init__(self, event_type: str, cause: BaseException):
        self.event_type = event_type
        self.cause = cause
        super().__init__(
            f"payload for '{event_type}' failed validation: {cause}"
        )


class WrongThreadError(XStateMachineError):
    """Raised when a loop-affine method is called from a foreign thread.

    🏛️ `Interpreter.send()` returns an awaitable bound to the event loop
    that started the interpreter. Called from another thread there is
    nothing to await it, so before 0.8.0 the coroutine was silently
    discarded and every event lost. This exception is raised eagerly, at
    the call site, so the mistake is loud. Use
    ``Interpreter.send_threadsafe()`` from other threads.
    """

    pass


class ReentrantWaitError(XStateMachineError):
    """An action awaited a ``send(..., wait=True)`` receipt on its OWN
    interpreter (#219).

    A receipt resolves when the run loop finishes processing the event. An
    action runs *inside* a macrostep the run loop is executing (or inside
    `start()`'s initial descent, which the loop waits for, #215), so the
    loop cannot take the new event until the action returns -- and the
    action will not return until the receipt resolves. That is a deadlock
    with no error and ``status == "running"``, which this exception raises
    eagerly at the call site instead. Use ``send()`` / ``raise`` without
    ``wait`` from inside an action: the event is queued as self-generated
    work and processed after the current step, and its receipt is not the
    caller's to await.

    A plain ``def`` action that calls ``send(..., wait=True)`` and drops the
    result gets a ``RuntimeWarning`` at finalisation instead (#232) -- the
    call is not a deadlock, just a receipt nobody can read -- while handing
    the awaitable out (``asyncio.ensure_future(...)``) stays silent.

    NOT raised (#225) for a task an action spawned that outlives it and
    sends later (``asyncio.ensure_future(worker(i))``), nor for the
    documented hand-out shape ``asyncio.ensure_future(i.send(...,
    wait=True))`` awaited from outside the step -- whether or not the
    spawning action awaits again afterwards. Only an await that runs while
    one of the interpreter's own actions is genuinely on the stack is a
    deadlock.
    """

    def __init__(self, machine_id: str, event_type: str):
        self.machine_id = machine_id
        self.event_type = event_type
        super().__init__(
            f"Action on '{machine_id}' awaited send('{event_type}', "
            f"wait=True) on its own interpreter. The receipt resolves only "
            f"when the run loop processes the event, and the loop cannot "
            f"advance until this action returns -- that is a deadlock. Send "
            f"without wait=True from inside an action (the event runs after "
            f"the current step), or await the receipt from outside."
        )


class RunawayChainError(XStateMachineError):
    """The self-generated event chain exceeded ``maxIterations`` (#77).

    An action raised or sent the event that triggers it, or a service
    completion re-armed the invoke that produced it, more than
    ``maxIterations`` times without an external event in between. The
    engine breaks the chain by discarding the offending tail; the machine
    stays ``running`` and every event the caller queued is still
    processed. This error is how the break is made OBSERVABLE: it is the
    ``Receipt.error`` of the triggering ``send(..., wait=True)``,
    ``interp.last_transition_ok`` is ``False``, and the
    ``on_event_dropped`` plugin hook fires with ``reason="chain_budget"``
    for each discarded event.

    Attributes:
        limit: The ``maxIterations`` that was exceeded.
        dropped: How many self-generated events were discarded.
        stranded: #207 -- invoke ids whose completion was among the
            discarded events while their state stayed active. Such an
            invocation will never complete: the machine rests in a state
            that declares `invoke` with nothing running. The same fact is
            reported through `on_invocation_stranded` and is readable
            afterwards from `has_dormant_invocations` /
            `pending_invocations()`.
    """

    def __init__(
        self,
        machine_id: str,
        limit: int,
        dropped: int,
        stranded: Optional[Iterable[str]] = None,
    ):
        # 🧭 `Optional` because `RestoredChainError` (#243) carries the
        #    persisted MESSAGE only -- JSON kept no limit / dropped count.
        self.limit: Optional[int] = limit
        self.dropped: Optional[int] = dropped
        self.stranded: tuple = tuple(stranded or ())
        tail = (
            f" The cut stranded invocation(s) {list(self.stranded)}: their "
            f"state is still active with no service running, and no "
            f"onDone/onError will arrive."
            if self.stranded
            else ""
        )
        super().__init__(
            f"Machine '{machine_id}' exceeded {limit} chained self-generated "
            f"events in one macrostep and discarded {dropped} of them. An "
            f"action raises or sends the event that triggers it; break the "
            f"cycle or raise 'maxIterations'.{tail}"
        )


class RestoredChainError(RestoredError, RunawayChainError):
    """The chain-trip latch (`last_chain_error`) recovered from a snapshot.

    #243: `RestoredError` alone put the restored latch OUTSIDE the
    `RunawayChainError` hierarchy, so the natural live-machine guard
    ``isinstance(interp.last_chain_error, RunawayChainError)`` was ``True``
    while the process ran and silently ``False`` the moment the same
    machine was restored -- precisely at the restart a supervisor is
    watching for. Subclassing both, a restored latch satisfies BOTH
    checks. ``.limit`` / ``.dropped`` are
    ``None`` and ``.stranded`` is empty: JSON kept only the message. The
    stable, type-independent signal remains ``chain_trips > 0``.
    """

    limit: Optional[int] = None
    dropped: Optional[int] = None
    stranded: tuple = ()

    def __init__(self, message: str):
        # 🧭 Bypass `RunawayChainError.__init__` (it composes its message
        #    from limit / dropped); the persisted message is the message.
        XStateMachineError.__init__(self, message)


class SnapshotMidStepError(XStateMachineError):
    """A snapshot was requested while a macrostep is in flight (#102).

    `exit -> actions -> enter` is one transaction; between exit and enter
    the configuration has no leaf. A snapshot taken there would persist an
    empty configuration that restores as a permanently inert machine
    reporting ``status="running"``. Take snapshots from a settled
    interpreter -- after ``send(wait=True)`` resolves, from a plugin hook
    such as ``on_transition``, or after ``stop(drain=True)``.
    """

    def __init__(self, machine_id: str, *, child: bool = False):
        self.machine_id = machine_id
        #: ``True`` when the mid-step actor is a CHILD of the interpreter
        #: the snapshot was requested on (#183): the root was settled, but
        #: a deep capture would have harvested the child's half-applied
        #: context.
        self.child = child
        if child:
            msg = (
                f"Child actor '{machine_id}' is mid-macrostep: its actions "
                f"are still running, so a snapshot of its parent would "
                f"persist a half-applied child context. Snapshot once the "
                f"child settles (await its send(..., wait=True), or from "
                f"an on_transition hook on the child)."
            )
        else:
            msg = (
                f"Interpreter '{machine_id}' is mid-macrostep: a "
                f"transition's actions are still running and the "
                f"configuration has no leaf. Snapshot it once the step "
                f"settles (await send(..., wait=True), or from "
                f"on_transition)."
            )
        super().__init__(msg)


class InvalidEventError(XStateMachineError, TypeError):
    """An event could not be normalised into a valid event object (#113).

    Raised by ``send()`` for a non-``str`` ``type`` (``None``, ``5``), a
    dict without a ``type`` key, or an object that is none of ``str`` /
    ``dict`` / an event class. Replaces the bare ``TypeError`` /
    ``AttributeError`` that used to escape the documented hierarchy.

    🏛️ Also a ``TypeError``: 0.8.0 raised that for the unsupported-object
    case, so an existing ``except TypeError`` keeps working while
    ``except XStateMachineError`` now catches it too.
    """


class RootTargetError(InvalidConfigError):
    """A transition targets the machine root itself (#108).

    Entering the root node re-enters nothing below it, leaving the
    configuration empty while ``status`` stays ``"running"`` -- a silently
    inert machine. Target the root's ``initial`` child, or a specific state.
    """


class SnapshotSerializationError(XStateMachineError):
    """A pending event's data is not JSON-representable (#131).

    `get_snapshot()` refuses rather than coercing: a `Decimal` persisted as
    ``"10.50"`` would be handed to the restored `onDone` handler as a
    `str`, and arithmetic that worked before the restore would break after
    it. Convert the value in the service that produced it (e.g. `str()` /
    `float()` explicitly), or drain the inbox before snapshotting.
    """

    def __init__(self, event_type: str, cause: BaseException):
        super().__init__(
            f"Pending event '{event_type}' carries data that is not JSON-"
            f"serialisable ({cause}). Snapshots refuse to coerce values "
            f"silently; make the data JSON-native or snapshot from a "
            f"quiesced interpreter."
        )


class SnapshotCorruptError(XStateMachineError):
    """A snapshot's payload is structurally invalid (#110).

    Missing required keys, a non-mapping ``context``, an unknown ``status``,
    or a ``configuration`` that is not a list of state ids. Distinct from
    `SnapshotVersionError` (too new) and `SnapshotDriftError` (wrong
    machine): the blob is for the right machine but its shape is wrong.
    """
