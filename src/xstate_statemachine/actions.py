# /src/xstate_statemachine/actions.py
# -----------------------------------------------------------------------------
# 🎬 Built-in Action Creators
# -----------------------------------------------------------------------------
# This module provides the declarative action vocabulary that XState v5 offers:
# `raise`, `send_to`, `send_parent`, `forward_to`, `escalate`, `log`, `cancel`,
# `stop_child`, `spawn_child`, `emit`, `assign`, `pure`, `choose` and
# `enqueue_actions`.
#
# 🏛️ Architecture decision: these are *built-in* action types resolved by the
# interpreter itself rather than looked up in `MachineLogic.actions`. Before
# this module the only mechanism available to a machine was a user function
# mutating `context` in place — there was no declarative way to express
# inter-actor messaging at all, so an entire class of statechart designs was
# inexpressible.
#
# Two spellings are accepted for every creator so both JSON and Python
# authoring feel natural:
#
#   - camelCase, matching XState JSON: ``{"type": "sendTo", ...}``
#   - snake_case, matching Python:     ``{"type": "send_to", ...}``
#
# Helper functions are also exported so a machine written in Python can build
# the same action dicts without hand-writing them, e.g. ``send_to("logger",
# {"type": "PING"})``.
# -----------------------------------------------------------------------------
"""
Declarative built-in action creators for XState-compatible machines.
"""

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import logging
from typing import Any, Callable, Dict, List, Optional, Union

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# 🏷️ Built-in Action Type Names
# -----------------------------------------------------------------------------
# Each entry maps every accepted spelling to one canonical name. The
# interpreter dispatches on the canonical name only, so adding an alias never
# touches the dispatch table.
# -----------------------------------------------------------------------------
RAISE = "xstate.raise"
SEND_TO = "xstate.sendTo"
SEND_PARENT = "xstate.sendParent"
FORWARD_TO = "xstate.forwardTo"
ESCALATE = "xstate.escalate"
LOG = "xstate.log"
CANCEL = "xstate.cancel"
STOP_CHILD = "xstate.stopChild"
SPAWN_CHILD = "xstate.spawnChild"
EMIT = "xstate.emit"
ASSIGN = "xstate.assign"
PURE = "xstate.pure"
CHOOSE = "xstate.choose"
ENQUEUE_ACTIONS = "xstate.enqueueActions"

#: Every accepted spelling → canonical built-in name.
BUILTIN_ACTION_ALIASES: Dict[str, str] = {
    # raise
    "raise": RAISE,
    "raise_": RAISE,
    "xstate.raise": RAISE,
    # sendTo
    "sendTo": SEND_TO,
    "send_to": SEND_TO,
    "xstate.sendTo": SEND_TO,
    # sendParent
    "sendParent": SEND_PARENT,
    "send_parent": SEND_PARENT,
    "xstate.sendParent": SEND_PARENT,
    # forwardTo
    "forwardTo": FORWARD_TO,
    "forward_to": FORWARD_TO,
    "xstate.forwardTo": FORWARD_TO,
    # escalate
    "escalate": ESCALATE,
    "xstate.escalate": ESCALATE,
    # log
    "log": LOG,
    "xstate.log": LOG,
    # cancel
    "cancel": CANCEL,
    "xstate.cancel": CANCEL,
    # stopChild
    "stopChild": STOP_CHILD,
    "stop_child": STOP_CHILD,
    "stop": STOP_CHILD,
    "xstate.stopChild": STOP_CHILD,
    # spawnChild
    #
    # ⚠️ `spawn_child` is deliberately NOT an alias. The library's long-
    # standing convention is `spawn_<serviceKey>`, so `spawn_child` already
    # means "spawn the service named `child`". Treating it as the built-in
    # would silently break every existing machine that spawns a service by
    # that name. Use `spawnChild` (or `xstate.spawnChild`) for the built-in.
    "spawnChild": SPAWN_CHILD,
    "xstate.spawnChild": SPAWN_CHILD,
    # emit
    "emit": EMIT,
    "xstate.emit": EMIT,
    # assign
    "assign": ASSIGN,
    "xstate.assign": ASSIGN,
    # pure
    "pure": PURE,
    "xstate.pure": PURE,
    # choose
    "choose": CHOOSE,
    "xstate.choose": CHOOSE,
    # enqueueActions
    "enqueueActions": ENQUEUE_ACTIONS,
    "enqueue_actions": ENQUEUE_ACTIONS,
    "xstate.enqueueActions": ENQUEUE_ACTIONS,
}


def resolve_builtin(action_type: str) -> Optional[str]:
    """Maps an action type to its canonical built-in name, if it is one.

    Args:
        action_type (str): The action's declared `type`.

    Returns:
        Optional[str]: The canonical built-in name, or `None` when the type
        refers to a user-supplied action.
    """
    return BUILTIN_ACTION_ALIASES.get(action_type)


def is_builtin(action_type: str) -> bool:
    """Reports whether an action type is handled natively by the interpreter.

    📝 A user may legitimately name their own action ``log`` or ``assign``.
    Built-in resolution therefore happens *after* a lookup in
    ``MachineLogic.actions``, so a user implementation always wins. This
    function only answers "could this be built in?".

    Args:
        action_type (str): The action's declared `type`.

    Returns:
        bool: `True` if a built-in handler exists for this type.
    """
    return action_type in BUILTIN_ACTION_ALIASES


# -----------------------------------------------------------------------------
# 🛠️ Action Creator Helpers
# -----------------------------------------------------------------------------
# These build the plain dictionaries the interpreter understands. They exist so
# Python-authored machines get the same ergonomics as XState's JS helpers,
# without needing to remember the params schema of each built-in.
# -----------------------------------------------------------------------------


def raise_(
    event: Union[str, Dict[str, Any]], *, delay: Optional[Any] = None
) -> Dict[str, Any]:
    """Builds a `raise` action, sending an event to this machine itself.

    Args:
        event (Union[str, Dict[str, Any]]): The event to raise.
        delay (Optional[Any]): Optional delay in milliseconds, or a named
            delay resolved from `MachineLogic.delays`.

    Returns:
        Dict[str, Any]: The action definition.
    """
    return {
        "type": RAISE,
        "params": {"event": event, "delay": delay},
    }


def send_to(
    target: Union[str, Callable[..., Any]],
    event: Union[str, Dict[str, Any]],
    *,
    delay: Optional[Any] = None,
    send_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Builds a `sendTo` action, addressing another actor.

    Args:
        target (Union[str, Callable]): The actor id / `systemId`, or a
            callable resolving one from `{context, event, system}`.
        event (Union[str, Dict[str, Any]]): The event to send.
        delay (Optional[Any]): Optional delay in milliseconds or a named delay.
        send_id (Optional[str]): Identifier allowing the send to be cancelled.

    Returns:
        Dict[str, Any]: The action definition.
    """
    return {
        "type": SEND_TO,
        "params": {
            "to": target,
            "event": event,
            "delay": delay,
            "id": send_id,
        },
    }


def send_parent(
    event: Union[str, Dict[str, Any]], *, delay: Optional[Any] = None
) -> Dict[str, Any]:
    """Builds a `sendParent` action.

    Args:
        event (Union[str, Dict[str, Any]]): The event to send upward.
        delay (Optional[Any]): Optional delay in milliseconds or a named delay.

    Returns:
        Dict[str, Any]: The action definition.
    """
    return {"type": SEND_PARENT, "params": {"event": event, "delay": delay}}


def forward_to(target: str) -> Dict[str, Any]:
    """Builds a `forwardTo` action, relaying the current event onward.

    Args:
        target (str): The actor id to forward to.

    Returns:
        Dict[str, Any]: The action definition.
    """
    return {"type": FORWARD_TO, "params": {"to": target}}


def escalate(error: Any) -> Dict[str, Any]:
    """Builds an `escalate` action, raising an error to the parent actor.

    Args:
        error (Any): The error payload.

    Returns:
        Dict[str, Any]: The action definition.
    """
    return {"type": ESCALATE, "params": {"error": error}}


def log(
    expr: Union[str, Callable[..., Any]] = "", *, label: Optional[str] = None
) -> Dict[str, Any]:
    """Builds a `log` action.

    Args:
        expr (Union[str, Callable]): A message, or a callable of
            `{context, event}` returning one.
        label (Optional[str]): Optional label prefixed to the message.

    Returns:
        Dict[str, Any]: The action definition.
    """
    return {"type": LOG, "params": {"expr": expr, "label": label}}


def cancel(send_id: str) -> Dict[str, Any]:
    """Builds a `cancel` action, aborting a pending delayed send.

    Args:
        send_id (str): The `send_id` given to the original delayed send.

    Returns:
        Dict[str, Any]: The action definition.
    """
    return {"type": CANCEL, "params": {"sendId": send_id}}


def stop_child(actor_id: Union[str, Callable[..., Any]]) -> Dict[str, Any]:
    """Builds a `stopChild` action.

    Args:
        actor_id (Union[str, Callable]): The child actor's id, or a callable
            resolving one.

    Returns:
        Dict[str, Any]: The action definition.
    """
    return {"type": STOP_CHILD, "params": {"id": actor_id}}


def spawn_child(
    src: str,
    *,
    actor_id: Optional[str] = None,
    system_id: Optional[str] = None,
    input: Optional[Any] = None,
) -> Dict[str, Any]:
    """Builds a `spawnChild` action.

    Args:
        src (str): The service key of the actor logic to spawn.
        actor_id (Optional[str]): Explicit id for the spawned actor.
        system_id (Optional[str]): Register the actor under this system id.
        input (Optional[Any]): Input passed to the child.

    Returns:
        Dict[str, Any]: The action definition.
    """
    return {
        "type": SPAWN_CHILD,
        "params": {
            "src": src,
            "id": actor_id,
            "systemId": system_id,
            "input": input,
        },
    }


def emit(event: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Builds an `emit` action, publishing an event to external listeners.

    Args:
        event (Union[str, Dict[str, Any]]): The event to emit.

    Returns:
        Dict[str, Any]: The action definition.
    """
    return {"type": EMIT, "params": {"event": event}}


def assign(
    assignment: Union[Dict[str, Any], Callable[..., Any]],
) -> Dict[str, Any]:
    """Builds an `assign` action updating the machine context.

    Args:
        assignment (Union[Dict[str, Any], Callable]): Either a mapping of key
            to value (values may themselves be callables of
            `{context, event}`), or a callable returning the whole update.

    Returns:
        Dict[str, Any]: The action definition.
    """
    return {"type": ASSIGN, "params": {"assignment": assignment}}


def pure(fn: Callable[..., Any]) -> Dict[str, Any]:
    """Builds a `pure` action returning actions to run.

    📝 Deprecated in XState v5 in favour of `enqueue_actions`, but retained
    here because it appears throughout existing v4-era configurations.

    Args:
        fn (Callable): Called with `{context, event}`; returns an action, a
            list of actions, or `None`.

    Returns:
        Dict[str, Any]: The action definition.
    """
    return {"type": PURE, "params": {"get": fn}}


def choose(conditions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Builds a `choose` action selecting the first matching branch.

    Args:
        conditions (List[Dict[str, Any]]): Entries of
            `{"guard": ..., "actions": ...}`. The first whose guard passes
            (or which has no guard) contributes its actions.

    Returns:
        Dict[str, Any]: The action definition.
    """
    return {"type": CHOOSE, "params": {"conditions": conditions}}


def enqueue_actions(fn: Callable[..., Any]) -> Dict[str, Any]:
    """Builds an `enqueueActions` action.

    The callable receives a single mapping with `context`, `event`, `enqueue`,
    `check` and `self`, and enqueues actions imperatively. This subsumes both
    `pure` and `choose`.

    Args:
        fn (Callable): The enqueueing callback.

    Returns:
        Dict[str, Any]: The action definition.
    """
    return {"type": ENQUEUE_ACTIONS, "params": {"callback": fn}}


# -----------------------------------------------------------------------------
# 📥 Enqueue Helper
# -----------------------------------------------------------------------------


class ActionEnqueuer:
    """Collects actions inside an `enqueue_actions` callback.

    Mirrors XState's `enqueue` object. Instances are single-use and created
    fresh for every `enqueue_actions` invocation.

    Attributes:
        items (List[Any]): The action definitions collected so far.
    """

    def __init__(self, interpreter: Any, event: Any) -> None:
        """Initializes the enqueuer.

        Args:
            interpreter (Any): The interpreter running the action.
            event (Any): The event that triggered it.
        """
        self.items: List[Any] = []
        self._interpreter = interpreter
        self._event = event

    def __call__(self, action: Union[str, Dict[str, Any]]) -> None:
        """Enqueues an action by name or definition.

        Args:
            action (Union[str, Dict[str, Any]]): The action to enqueue.
        """
        self.items.append(action)

    # 🛠️ Convenience methods mirroring XState's `enqueue.*` helpers.
    def assign(
        self, assignment: Union[Dict[str, Any], Callable[..., Any]]
    ) -> None:
        """Enqueues a context assignment.

        Args:
            assignment: Mapping or callable, as for :func:`assign`.
        """
        self.items.append(assign(assignment))

    def raise_(self, event: Union[str, Dict[str, Any]]) -> None:
        """Enqueues a self-directed event.

        Args:
            event: The event to raise.
        """
        self.items.append(raise_(event))

    def send_to(self, target: str, event: Union[str, Dict[str, Any]]) -> None:
        """Enqueues a `sendTo`.

        Args:
            target: The destination actor id.
            event: The event to send.
        """
        self.items.append(send_to(target, event))

    def send_parent(self, event: Union[str, Dict[str, Any]]) -> None:
        """Enqueues a `sendParent`.

        Args:
            event: The event to send upward.
        """
        self.items.append(send_parent(event))

    def emit(self, event: Union[str, Dict[str, Any]]) -> None:
        """Enqueues an `emit`.

        Args:
            event: The event to publish.
        """
        self.items.append(emit(event))

    def log(self, expr: Union[str, Callable[..., Any]] = "") -> None:
        """Enqueues a `log`.

        Args:
            expr: Message or callable producing one.
        """
        self.items.append(log(expr))

    def cancel(self, send_id: str) -> None:
        """Enqueues a `cancel`.

        Args:
            send_id: The id of the delayed send to abort.
        """
        self.items.append(cancel(send_id))

    def stop_child(self, actor_id: str) -> None:
        """Enqueues a `stopChild`.

        Args:
            actor_id: The child actor to stop.
        """
        self.items.append(stop_child(actor_id))

    def spawn_child(self, src: str, **kwargs: Any) -> None:
        """Enqueues a `spawnChild`.

        Args:
            src: The service key to spawn.
            **kwargs: Forwarded to :func:`spawn_child`.
        """
        self.items.append(spawn_child(src, **kwargs))


__all__ = [
    "ActionEnqueuer",
    "BUILTIN_ACTION_ALIASES",
    "assign",
    "cancel",
    "choose",
    "emit",
    "enqueue_actions",
    "escalate",
    "forward_to",
    "is_builtin",
    "log",
    "pure",
    "raise_",
    "resolve_builtin",
    "send_parent",
    "send_to",
    "spawn_child",
    "stop_child",
]
