# src/xstate_statemachine/contrib/django/mixin.py
# -----------------------------------------------------------------------------
# ðŸ§¬ StatechartModelMixin -- ``order.send("PAY")`` in one transaction
# -----------------------------------------------------------------------------
# ðŸ›ï¸ create â†’ act â†’ persist â†’ discard against the ROW, inside
#    ``transaction.atomic()``:
#
#      pessimistic (default)  lock the row (``select_for_update``; on SQLite
#                             a no-op UPDATE takes the write lock first --
#                             SQLite has no row locks), re-read the snapshot,
#                             act, UPDATE. Concurrent senders serialise.
#      optimistic             act on the snapshot in memory, then
#                             ``UPDATE ... WHERE <name>_version = expected``;
#                             0 rows â†’ `ConflictError` (``send_with_retry``
#                             reloads and re-applies).
#      none                   last writer wins (single-writer rows only).
#
#    The deadline rows (``xsm_django_deadline``) and -- with #281 -- the
#    audit rows are written on the same connection, inside the same
#    ``atomic()``, so they commit with the state change or not at all.
#
# âš ï¸ X0.3: under optimistic retry the machine's ACTIONS MAY RUN MORE THAN
#    ONCE per logical send -- side effects belong in services, in an
#    outbox (`DjangoOutboxStore`), or in ``post_transition(on_commit=True)``.
# âš ï¸ Async views: there is no native async ``select_for_update``. Call
#    ``await order.asend(...)`` (``sync_to_async(thread_sensitive=True)``
#    around the whole locked section), never the ORM pieces separately.
# -----------------------------------------------------------------------------
"""`StatechartModelMixin`, `StatechartQuerySet`, `send_with_retry`."""

from __future__ import annotations

import contextlib
import contextvars
import json
import time
from typing import Any, ClassVar, Dict, Iterator, List, Optional, Tuple

from django.apps import apps
from django.db import models, router, transaction
from django.db.models import CharField, F, Q, Value
from django.db.models.functions import Concat, StrIndex

from ...events import Receipt
from ...exceptions import ConflictError
from ...models import MachineNode
from ...patterns.retry import RetryPolicy
from . import _deadlines
from ._events import declared_events
from ._machine import resolve_machine
from .fields import SEP, StatechartField, sibling_values

__all__ = [
    "LOCK_MODES",
    "StatechartManager",
    "StatechartModelMixin",
    "StatechartQuerySet",
    "current_actor",
    "current_instance",
    "send_with_retry",
]

LOCK_MODES = ("pessimistic", "optimistic", "none")
APP = "xstate_statemachine.contrib.django"
_RETRY_BACKOFF = RetryPolicy(
    max_attempts=8, base_ms=1.0, factor=2.0, max_ms=50.0, jitter="full"
)

#: The user object behind the ``actor_id`` of the send in progress --
#: `PermissionGuard` reads it so guards need not hit the database, and
#: the payload stays JSON (only the id travels in it).
current_actor: "contextvars.ContextVar[Any]" = contextvars.ContextVar(
    "xsm_django_actor", default=None
)
#: The row a guard is being evaluated for (object-level permissions).
current_instance: "contextvars.ContextVar[Any]" = contextvars.ContextVar(
    "xsm_django_instance", default=None
)


def statechart_field(model: Any) -> StatechartField:
    """The model's `StatechartField` (``statechart_field_name`` picks one
    when there are several)."""
    wanted = getattr(model, "statechart_field_name", None)
    found = [
        f for f in model._meta.get_fields() if isinstance(f, StatechartField)
    ]
    if wanted:
        found = [f for f in found if f.name == wanted]
    if len(found) != 1:
        raise TypeError(
            f"{model.__name__} needs exactly one StatechartField "
            f"(found {len(found)}); set statechart_field_name."
        )
    return found[0]


# -----------------------------------------------------------------------------
# ðŸ”Ž QuerySet
# -----------------------------------------------------------------------------
class StatechartQuerySet(models.QuerySet):  # type: ignore[type-arg]
    """``in_state(*ids)`` -- rows where ANY id is active: a leaf, or an
    ancestor of one (``in_state("order.review")`` matches
    ``order.review.legal.pending``)."""

    def in_state(self, *state_ids: str) -> "StatechartQuerySet":
        if not state_ids:
            raise ValueError("in_state() needs at least one state id")
        col = f"{statechart_field(self.model).name}_state"
        wrapped = Concat(
            Value(SEP), F(col), Value(SEP), output_field=CharField()
        )
        qs = self.annotate(_xsm_state=wrapped)
        q = Q()
        n = 0
        for sid in state_ids:
            if not isinstance(sid, str) or not sid:
                raise ValueError("state ids must be non-empty strings")
            # ðŸ“ StrIndex (instr / strpos) is case-sensitive and takes the
            #    needle as a bound PARAMETER -- no LIKE wildcards to escape,
            #    no SQL built from the id (SQL-injection test pins this).
            for needle in (f"{SEP}{sid}{SEP}", f"{SEP}{sid}."):
                pos = f"_xsm_pos_{n}"
                n += 1
                qs = qs.annotate(
                    **{pos: StrIndex("_xsm_state", Value(needle))}
                )
                q |= Q(**{f"{pos}__gt": 0})
        return qs.filter(q)


StatechartManager = models.Manager.from_queryset(StatechartQuerySet)


# -----------------------------------------------------------------------------
# ðŸ§¬ Mixin
# -----------------------------------------------------------------------------
class StatechartModelMixin(models.Model):
    """Mix into a model that declares one `StatechartField`.

    Class attributes:
        statechart_machine: JSON path / config dict / `MachineNode` /
            dotted callable (``"shop.charts:order"``) returning one.
        statechart_logic: Optional `MachineLogic`, dotted callable or
            dotted module (`LogicLoader` binds functions by name).
        statechart_lock: Default lock mode (``"pessimistic"``).
        statechart_migrator / statechart_on_version_mismatch: Forwarded
            to `from_snapshot` (#263).
        statechart_clock: Clock for the per-send interpreter.
        statechart_initialize: Build the initial snapshot on insert
            (entry actions run once, at creation). Default ``True``.
    """

    statechart_machine: ClassVar[Any] = None
    statechart_logic: ClassVar[Any] = None
    statechart_lock: ClassVar[str] = "pessimistic"
    statechart_migrator: ClassVar[Any] = None
    statechart_on_version_mismatch: ClassVar[Optional[str]] = None
    statechart_clock: ClassVar[Any] = None
    statechart_initialize: ClassVar[bool] = True
    #: Write `TransitionLog` rows in send()'s transaction (#281).
    #: ``None`` (default) = on when the app + contenttypes are installed.
    statechart_audit: ClassVar[Optional[bool]] = None
    #: Extra plugins per send: a list, or ``(row) -> list`` (e.g.
    #: ``lambda row: [OutboxPlugin(DjangoOutboxStore())]``).
    statechart_plugins: ClassVar[Any] = ()

    objects = StatechartManager()

    class Meta:
        abstract = True

    # -- machine ----------------------------------------------------------------
    @classmethod
    def statechart_field_obj(cls) -> StatechartField:
        return statechart_field(cls)

    def statechart_machine_node(self) -> MachineNode[Any]:
        """The chart for this row (cached per class for static specs)."""
        cls = type(self)
        spec, logic = cls.statechart_machine, cls.statechart_logic
        static = not callable(spec) or isinstance(spec, MachineNode)
        static = static and (logic is None or not callable(logic))
        if static:
            cache = cls.__dict__.get("_xsm_machine_cache")
            if cache is None:
                cache = resolve_machine(spec, logic=logic, owner=cls, row=self)
                setattr(cls, "_xsm_machine_cache", cache)
            return cache
        return resolve_machine(spec, logic=logic, owner=cls, row=self)

    def _xsm_names(self) -> Tuple[str, str]:
        name = statechart_field(type(self)).name
        return name, f"{name}_version"

    def _xsm_snapshot(self) -> Optional[Dict[str, Any]]:
        return getattr(self, self._xsm_names()[0])

    def _xsm_key(self) -> str:
        if self.pk is None:
            raise ValueError("row has no primary key yet; save() it first")
        return str(self.pk)

    # -- read side --------------------------------------------------------------
    def _xsm_interp(self, *, started: bool = False) -> Any:
        from ...sync_interpreter import SyncInterpreter

        m = self.statechart_machine_node()
        snap = self._xsm_snapshot()
        if snap is None:
            interp = SyncInterpreter(m, clock=type(self).statechart_clock)
            return interp.start() if started else interp
        return SyncInterpreter.from_snapshot(
            json.dumps(snap), m, **self._xsm_restore_kwargs(timers=False)
        )

    def _xsm_restore_kwargs(self, *, timers: bool = True) -> Dict[str, Any]:
        cls = type(self)
        kw: Dict[str, Any] = {"restart_timers": "resume" if timers else False}
        if cls.statechart_clock is not None:
            kw["clock"] = cls.statechart_clock
        if cls.statechart_migrator is not None:
            kw["migrator"] = cls.statechart_migrator
        if cls.statechart_on_version_mismatch is not None:
            kw["on_version_mismatch"] = cls.statechart_on_version_mismatch
        return kw

    @property
    def machine(self) -> Any:
        """A (not started) `SyncInterpreter` restored from the snapshot --
        read ``.context`` / ``.current_state_ids`` / ``.can()`` without
        sending anything."""
        return self._xsm_interp(started=self._xsm_snapshot() is None)

    @property
    def state(self) -> Optional[str]:
        """``<field>_state``: the sorted, comma-joined leaf ids (one id
        unless a parallel state is active)."""
        return getattr(self, f"{self._xsm_names()[0]}_state")

    @property
    def state_ids(self) -> List[str]:
        return list(getattr(self, f"{self._xsm_names()[0]}_state_ids") or [])

    def matches(self, state_id: str) -> bool:
        """``True`` when *state_id* (a leaf or an ancestor) is active."""
        return any(
            s == state_id or s.startswith(state_id + ".")
            for s in self.state_ids
        )

    def can(self, event: Any, *, actor: Any = None, **payload: Any) -> bool:
        """Would *event* cause a transition now? Guards run (with
        *actor* visible to `PermissionGuard`); nothing is written."""
        etype = event if isinstance(event, str) else event.get("type")
        body = self._xsm_payload(actor, None, dict(payload))
        with self._xsm_bind(actor):
            return bool(self.machine.can({"type": etype, **body}))

    @property
    def available_events(self) -> List[str]:
        """Declared events that would cause a transition now (no actor:
        permission guards evaluate ``False``)."""
        return self.available_events_for(None)

    def available_events_for(self, actor: Any) -> List[str]:
        """`available_events` as *actor* sees them."""
        interp = self.machine
        body = self._xsm_payload(actor, None, {})
        with self._xsm_bind(actor):
            return [
                e
                for e in declared_events(interp.machine)
                if interp.can({"type": e, **body})
            ]

    @contextlib.contextmanager
    def _xsm_bind(self, actor: Any) -> Iterator[None]:
        """Expose *actor* and this row to guards for the duration."""
        ta = current_actor.set(actor)
        ti = current_instance.set(self)
        try:
            yield
        finally:
            current_instance.reset(ti)
            current_actor.reset(ta)

    # -- write side ---------------------------------------------------------------
    @staticmethod
    def _xsm_payload(
        actor: Any, reason: Optional[str], payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        if actor is not None:
            payload.setdefault("actor_id", getattr(actor, "pk", actor))
        if reason is not None:
            payload.setdefault("reason", str(reason))
        return payload

    def send(
        self,
        event_type: str,
        *,
        lock: Optional[str] = None,
        actor: Any = None,
        reason: Optional[str] = None,
        plugins: Any = (),
        using: Optional[str] = None,
        wait: bool = True,
        **payload: Any,
    ) -> Receipt:
        """Apply *event_type* to this row's statechart and write it.

        Args:
            lock: ``"pessimistic"`` (default, `statechart_lock`),
                ``"optimistic"`` or ``"none"`` (see module notes).
            actor: The acting user; its pk travels as ``actor_id`` and
                `PermissionGuard` / the audit log see the object.
            reason: Free text for the audit log.
            plugins: Extra plugins for this send only.
            wait: Accepted for symmetry with ``Interpreter.send``; a model
                send always completes before returning.

        Raises:
            ConflictError: optimistic fence lost (roll back and retry --
                `send_with_retry` does).
        """
        del wait
        lock = lock or type(self).statechart_lock
        if lock not in LOCK_MODES:
            raise ValueError(f"lock must be one of {LOCK_MODES}")
        using = using or self._state.db or router.db_for_write(type(self))
        if self.pk is None:
            self.save(using=using)
        body = self._xsm_payload(actor, reason, dict(payload))
        with self._xsm_bind(actor), transaction.atomic(using=using):
            return self._xsm_send_locked(
                event_type, body, lock, list(plugins), using, actor
            )

    async def asend(self, event_type: str, **kw: Any) -> Receipt:
        """`send` for async views: the WHOLE locked section runs in one
        ``sync_to_async(thread_sensitive=True)`` call."""
        from asgiref.sync import sync_to_async

        return await sync_to_async(self.send, thread_sensitive=True)(
            event_type, **kw
        )

    def _xsm_lock_row(self, mgr: Any, using: str) -> Tuple[Any, int]:
        """Take the row lock; return the fresh (snapshot, version)."""
        name, vcol = self._xsm_names()
        from django.db import connections

        if connections[using].vendor == "sqlite":
            # ðŸ”’ SQLite has no row locks and `select_for_update` is a
            #    no-op: lead with a WRITE so this transaction holds the
            #    database write lock before it reads (other writers then
            #    wait on busy_timeout instead of deadlocking on upgrade).
            mgr.filter(pk=self.pk).update(**{vcol: F(vcol)})
        row = mgr.select_for_update().only(name, vcol).get(pk=self.pk)
        return getattr(row, name), int(getattr(row, vcol) or 0)

    def _xsm_send_locked(
        self,
        event_type: str,
        payload: Dict[str, Any],
        lock: str,
        plugins: List[Any],
        using: str,
        actor: Any,
    ) -> Receipt:
        name, vcol = self._xsm_names()
        mgr = type(self)._base_manager.using(using)
        if lock == "pessimistic":
            snap, expected = self._xsm_lock_row(mgr, using)
        else:
            snap, expected = self._xsm_snapshot(), int(
                getattr(self, vcol) or 0
            )
        ctx: Dict[str, Any] = {
            "actor": actor,
            "event_type": event_type,
            "payload": payload,
            "using": using,
            "before": sorted((snap or {}).get("state_ids") or ()),
        }
        plugins = plugins + self._xsm_plugins(ctx)
        early = self._xsm_before_run(ctx)
        if early is not None:
            return early
        receipt, new_snap, deadlines = self._xsm_run(
            snap, event_type, payload, plugins
        )
        values = sibling_values(name, new_snap)
        values[name] = new_snap
        values[vcol] = expected + 1
        q = mgr.filter(pk=self.pk)
        if lock != "none":
            q = q.filter(**{vcol: expected})
        if q.update(**values) != 1:
            actual = mgr.filter(pk=self.pk).values_list(vcol, flat=True)
            raise ConflictError(
                self._xsm_key(), expected, next(iter(actual), None)
            )
        self._xsm_write_deadlines(using, deadlines)
        for k, v in values.items():
            setattr(self, k, v)
        ctx.update(receipt=receipt, snapshot=new_snap)
        self._xsm_after_write(ctx)
        return receipt

    def _xsm_run(
        self,
        snap: Optional[Dict[str, Any]],
        event_type: str,
        payload: Dict[str, Any],
        plugins: List[Any],
    ) -> Tuple[Receipt, Dict[str, Any], Tuple[Any, ...]]:
        from ...sync_interpreter import SyncInterpreter

        m = self.statechart_machine_node()
        if snap is None:
            interp = SyncInterpreter(m, clock=type(self).statechart_clock)
            for p in plugins:
                interp.use(p)
        else:
            interp = SyncInterpreter.from_snapshot(
                json.dumps(snap),
                m,
                plugins=plugins,
                **self._xsm_restore_kwargs(),
            )
        interp.store_key = self._xsm_key()
        setattr(interp, "_xsm_django_row", self)
        interp.start()
        try:
            receipt = interp.send(event_type, wait=True, **payload)
            new_snap = json.loads(interp.get_snapshot())
            deadlines = tuple(interp._persist_deadlines())
        finally:
            interp.stop()
        return receipt, new_snap, deadlines

    # -- signals / audit / plugins (#281) --------------------------------------------
    def _xsm_plugins(self, ctx: Dict[str, Any]) -> List[Any]:
        """Plugins attached to every send of this row: the signal plugin,
        the audit plugin (`statechart_audit`), and `statechart_plugins`."""
        from .signals import DjangoSignalPlugin

        sig = DjangoSignalPlugin(self)
        ctx["signal_plugin"] = sig
        out: List[Any] = [sig]
        if type(self)._xsm_audit_enabled():
            from .audit import DjangoAuditPlugin

            audit = DjangoAuditPlugin(self, using=ctx["using"])
            audit.store.actor = ctx.get("actor")
            audit.store.buffer = []
            ctx["audit_plugin"] = audit
            out.append(audit)
        extra = type(self).statechart_plugins
        if callable(extra):
            extra = extra(self)
        out.extend(extra or ())
        return out

    @classmethod
    def _xsm_audit_enabled(cls) -> bool:
        flag = cls.statechart_audit
        if flag is None:
            return cls._xsm_has_tables() and apps.is_installed(
                "django.contrib.contenttypes"
            )
        return bool(flag)

    def _xsm_before_run(self, ctx: Dict[str, Any]) -> Optional[Receipt]:
        """`pre_transition`: a `TransitionVetoed` answers ``denied``."""
        from .signals import emit_pre

        return emit_pre(self, ctx)

    def _xsm_after_write(self, ctx: Dict[str, Any]) -> None:
        """Audit rows, then `post_transition` -- both inside the send's
        transaction: a failing insert or a raising receiver rolls back
        the state AND its audit row."""
        from .signals import emit_post

        audit = ctx.get("audit_plugin")
        if audit is not None:
            audit.store.flush()
        emit_post(self, ctx, ctx["signal_plugin"])

    @property
    def history(self) -> Any:
        """This row's `TransitionLog` rows, ordered by ``seq``."""
        from .audit import history_of

        return history_of(self)

    # -- deadlines -------------------------------------------------------------------
    @classmethod
    def _xsm_has_tables(cls) -> bool:
        return apps.is_installed(APP)

    def _xsm_write_deadlines(self, using: str, deadlines: Any) -> None:
        if not type(self)._xsm_has_tables():
            # ðŸ“ Without the app the deadlines still live INSIDE the
            #    snapshot and resume when the row is next touched; only
            #    the scanner's index is absent.
            return
        _deadlines.write(
            using, self._meta.db_table, self._xsm_key(), deadlines
        )

    # -- save / forget ---------------------------------------------------------------
    def save(self, *args: Any, **kwargs: Any) -> None:
        """Insert builds the initial snapshot (`statechart_initialize`);
        an UPDATE never rewrites the statechart columns unless they are
        named in ``update_fields`` -- only `send()` moves the state, so a
        stale instance saved for another field cannot roll it back."""
        name, vcol = self._xsm_names()
        siblings = sibling_values(name, None)
        cols = {name, vcol, *siblings}
        adding = self._state.adding or self.pk is None
        deadlines: Tuple[Any, ...] = ()
        if adding:
            if (
                self._xsm_snapshot() is None
                and type(self).statechart_initialize
            ):
                snap, deadlines = self._xsm_initial()
                setattr(self, name, snap)
            for k, v in sibling_values(name, self._xsm_snapshot()).items():
                setattr(self, k, v)
        elif kwargs.get("update_fields") is None and not kwargs.get(
            "force_insert"
        ):
            kwargs["update_fields"] = [
                f.name
                for f in self._meta.concrete_fields
                if not f.primary_key and f.name not in cols
            ]
        else:
            for k, v in sibling_values(name, self._xsm_snapshot()).items():
                setattr(self, k, v)
        super().save(*args, **kwargs)
        if adding and deadlines:
            self._xsm_write_deadlines(
                kwargs.get("using") or self._state.db or "default", deadlines
            )

    def _xsm_initial(self) -> Tuple[Dict[str, Any], Tuple[Any, ...]]:
        from ...sync_interpreter import SyncInterpreter

        interp = SyncInterpreter(
            self.statechart_machine_node(), clock=type(self).statechart_clock
        ).start()
        try:
            return (
                json.loads(interp.get_snapshot()),
                tuple(interp._persist_deadlines()),
            )
        finally:
            interp.stop()

    def forget_statechart(self, using: Optional[str] = None) -> Dict[str, int]:
        """X0.5: erase the snapshot, its deadline rows and its audit rows
        (#281); the business row itself stays. Returns counts per kind."""
        using = using or self._state.db or "default"
        name, vcol = self._xsm_names()
        counts = {"snapshots": int(self._xsm_snapshot() is not None)}
        with transaction.atomic(using=using):
            counts["deadlines"] = (
                _deadlines.write(
                    using, self._meta.db_table, self._xsm_key(), ()
                )
                if type(self)._xsm_has_tables()
                else 0
            )
            counts.update(self._xsm_forget_extra(using))
            values = sibling_values(name, None)
            values[name] = None
            values[vcol] = F(vcol) + 1
            type(self)._base_manager.using(using).filter(pk=self.pk).update(
                **values
            )
        self.refresh_from_db(
            using=using, fields=[name, vcol, *sibling_values(name, None)]
        )
        return counts

    def _xsm_forget_extra(self, using: str) -> Dict[str, int]:
        if not type(self)._xsm_audit_enabled():
            return {}
        from .audit import forget_log

        mode = type(self).statechart_forget_log
        return {"log_entries": forget_log(self, using=using, mode=mode)}

    #: X0.5 choice for the audit trail on `forget_statechart`:
    #: ``"redact"`` keeps the append-only chain, ``"delete"`` removes it.
    statechart_forget_log: ClassVar[str] = "redact"


# -----------------------------------------------------------------------------
# ðŸ” retry
# -----------------------------------------------------------------------------
def send_with_retry(
    row: Any,
    event_type: str,
    *,
    retries: int = 10,
    backoff: Optional[RetryPolicy] = None,
    lock: str = "optimistic",
    **kw: Any,
) -> Receipt:
    """`send()` retried on `ConflictError`: reload the row's statechart
    columns, back off, re-apply. Actions may run once per attempt (X0.3).
    On exhaustion the last `ConflictError` is raised with ``attempts``.
    Call it OUTSIDE an enclosing ``atomic()`` (a conflict inside one is
    only a savepoint rollback, but the retry needs a fresh read)."""
    if retries < 0:
        raise ValueError("retries must be >= 0")
    policy = backoff or _RETRY_BACKOFF
    name, vcol = row._xsm_names()
    attempt = 0
    while True:
        attempt += 1
        try:
            return row.send(event_type, lock=lock, **kw)
        except ConflictError as exc:
            if attempt > retries:
                setattr(exc, "attempts", attempt)
                raise
            row.refresh_from_db(
                fields=[name, vcol, *sibling_values(name, None)]
            )
            time.sleep(policy.delay_ms(min(attempt, 30)) / 1000.0)
