# src/xstate_statemachine/contrib/django/signals.py
# -----------------------------------------------------------------------------
# 📣 pre_transition / post_transition / statechart_error
# -----------------------------------------------------------------------------
# 🏛️ Django developers wire behaviour through signals. All three fire from
#    INSIDE ``send()``'s ``transaction.atomic()``:
#
#      pre_transition   before the machine runs. A receiver raising
#                       `TransitionVetoed` answers the send with
#                       ``Receipt(denied=True)`` -- no state change, no
#                       audit row. Any other exception propagates (and
#                       rolls the transaction back).
#      post_transition  once per send, after the row is written. A receiver
#                       that raises rolls back the state change AND its
#                       audit row -- they cannot disagree.
#                       ``post_transition.connect(fn, on_commit=True)``
#                       defers *fn* to ``transaction.on_commit``: the ONLY
#                       safe place for external side effects (email, HTTP,
#                       a broker), because it never runs for a rolled-back
#                       transition.
#      statechart_error an action / service raised, or the chain budget
#                       tripped (mirrors the plugin hooks).
# -----------------------------------------------------------------------------
"""Signals and the `DjangoSignalPlugin` that emits them."""

from __future__ import annotations

import threading
import weakref
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction
from django.dispatch import Signal
from django.dispatch.dispatcher import _make_id

from ...events import Receipt
from ...exceptions import XStateMachineError
from ...plugins import PluginBase

__all__ = [
    "DjangoSignalPlugin",
    "TransitionVetoed",
    "post_transition",
    "pre_transition",
    "statechart_error",
]


class TransitionVetoed(XStateMachineError):
    """Raise from a `pre_transition` receiver to refuse the event."""

    def __init__(self, reason: str = "vetoed") -> None:
        super().__init__(reason)
        self.reason = reason


class _OnCommit:
    """Receiver wrapper that runs the real receiver after COMMIT.

    📝 #281 battle (A): honours ``weak=`` like Django does -- a bound
    method of a short-lived object is held by a `WeakMethod`, so the
    wrapper (which the signal holds strongly) never keeps it alive; once
    the referent is gone the wrapper is a no-op and disconnects itself.
    """

    def __init__(self, fn: Any, weak: bool, signal: Any, key: Any) -> None:
        self._key = key
        self._signal = signal
        if not weak:
            self._ref: Any = lambda: fn
        elif hasattr(fn, "__self__") and hasattr(fn, "__func__"):
            self._ref = weakref.WeakMethod(fn)
        else:
            self._ref = weakref.ref(fn)

    def __call__(self, signal: Any, sender: Any, **kw: Any) -> None:
        fn = self._ref()
        if fn is None:
            uid, sender = self._key
            Signal.disconnect(self._signal, None, sender, uid)
            return
        using = kw.get("using")
        transaction.on_commit(
            lambda: fn(signal=signal, sender=sender, **kw), using=using
        )


def _wrapper_uid(receiver: Any, dispatch_uid: Any) -> Any:
    # 📝 `_make_id` is Django's own: ``(id(self), id(func))`` for a bound
    #    method -- ``id(obj.method)`` differs on every attribute access,
    #    so `disconnect(obj.method)` could never find the wrapper.
    return dispatch_uid or ("xsm_on_commit", _make_id(receiver))


class PostTransitionSignal(Signal):
    """A `Signal` whose ``connect`` takes ``on_commit=``."""

    def connect(  # type: ignore[override]
        self,
        receiver: Any,
        sender: Any = None,
        weak: bool = True,
        dispatch_uid: Any = None,
        on_commit: bool = False,
    ) -> None:
        if not on_commit:
            super().connect(receiver, sender, weak, dispatch_uid)
            return
        uid = _wrapper_uid(receiver, dispatch_uid)
        wrapper = _OnCommit(receiver, weak, self, (uid, sender))
        super().connect(wrapper, sender, False, uid)

    def disconnect(  # type: ignore[override]
        self,
        receiver: Any = None,
        sender: Any = None,
        dispatch_uid: Any = None,
        on_commit: bool = False,
    ) -> bool:
        # 📝 #281 battle: `disconnect(fn)` after `connect(fn, on_commit=
        #    True)` silently did nothing (the wrapper, not `fn`, was the
        #    receiver) -- the receiver kept firing for the rest of the
        #    process. Either spelling now disconnects it, per sender, and
        #    for bound methods too (battle A).
        if receiver is None and dispatch_uid is None:
            return False
        removed = super().disconnect(
            None, sender, _wrapper_uid(receiver, dispatch_uid)
        )
        if removed or on_commit:
            return removed
        return super().disconnect(receiver, sender, dispatch_uid)


#: ``(sender=Model, instance, event, from_states, actor, using)``
pre_transition = Signal()
#: ``(sender=Model, instance, event, receipt, from_states, to_states,
#: actions, actor, using)``
post_transition = PostTransitionSignal()
#: ``(sender=Model, instance, kind, error)`` -- kind is ``"action"``,
#: ``"service"`` or ``"chain_budget"``.
statechart_error = Signal()


class DjangoSignalPlugin(PluginBase[Any]):
    """Collects what a send did and emits `statechart_error` (attached by
    `StatechartModelMixin`; the mixin emits pre/post itself)."""

    def __init__(self, instance: Any) -> None:
        self.instance = instance
        self.sender = type(instance)
        self.actions: List[str] = []
        self._lock = threading.Lock()

    def on_action_execute(self, interpreter: Any, action: Any) -> None:
        with self._lock:
            self.actions.append(str(getattr(action, "type", action)))

    def _error(self, kind: str, error: BaseException) -> None:
        statechart_error.send(
            sender=self.sender, instance=self.instance, kind=kind, error=error
        )

    def on_action_error(
        self, interpreter: Any, action: Any, error: BaseException
    ) -> None:
        self._error("action", error)

    def on_service_error(
        self, interpreter: Any, invocation: Any, error: Exception
    ) -> None:
        self._error("service", error)

    def on_chain_budget_exceeded(
        self, interpreter: Any, error: BaseException, event: Any
    ) -> None:
        self._error("chain_budget", error)


def emit_pre(instance: Any, ctx: Dict[str, Any]) -> Optional[Receipt]:
    """Send `pre_transition`; a veto becomes ``Receipt(denied=True)``."""
    from ...events import Event

    event = Event(type=ctx["event_type"], payload=dict(ctx["payload"]))
    ctx["event"] = event
    try:
        pre_transition.send(
            sender=type(instance),
            instance=instance,
            event=event,
            from_states=tuple(ctx["before"]),
            actor=ctx.get("actor"),
            using=ctx["using"],
        )
    except TransitionVetoed as exc:
        ctx["vetoed"] = exc
        return Receipt(
            state_ids=frozenset(ctx["before"]),
            changed=False,
            error=None,
            denied=True,
        )
    return None


def _to_states(ctx: Dict[str, Any], receipt: Any) -> Tuple[str, ...]:
    """Where the row IS after the send. 🐛 #281 battle (A): the receipt
    covers the external event's step only; an engine step it raised
    (``done.state.*`` of a finished parallel region, an eventless chain)
    ran in the same send, so ``receipt.state_ids`` named a configuration
    the row had already left. The written snapshot is the truth."""
    snap = ctx.get("snapshot") or {}
    ids = snap.get("state_ids")
    return tuple(sorted(ids if ids is not None else receipt.state_ids))


def emit_post(instance: Any, ctx: Dict[str, Any], plugin: Any) -> None:
    receipt = ctx["receipt"]
    post_transition.send(
        sender=type(instance),
        instance=instance,
        event=ctx["event"],
        receipt=receipt,
        from_states=tuple(ctx["before"]),
        to_states=_to_states(ctx, receipt),
        actions=tuple(plugin.actions),
        actor=ctx.get("actor"),
        using=ctx["using"],
    )
