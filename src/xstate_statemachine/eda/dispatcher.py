# src/xstate_statemachine/eda/dispatcher.py
# -----------------------------------------------------------------------------
# 📥 InboundDispatcher -- envelope → persisted(key=subject) → send (#293)
# -----------------------------------------------------------------------------
# 🏛️ The generic consumer loop every broker adapter reuses:
#
#      delivery → validate → machine_for_type(type) → lock.run(store,
#      key=subject, machine, send(envelope.to_event())) → ack
#
#    * DEDUP -- with an `inbox`, an `IdempotencyPlugin` keyed on the
#      envelope id (principal = envelope source) answers a redelivery with
#      the original receipt; the inbox mark is written after the snapshot
#      save through `persisted()`'s `flush_marks` seam (same transaction
#      under `PessimisticLock` on a shared SQLite store).
#    * ORDER -- one subject is processed at a time; different subjects run
#      concurrently up to `max_in_flight` (X0.8 backpressure). When a
#      delivery fails and is requeued, the later deliveries of the SAME
#      subject held in this batch are requeued behind it, so order holds.
#    * POISON (X0.8) -- attempts = max(envelope ``xsmattempt`` extension,
#      the dispatcher's own redelivery count). At `max_attempts` the
#      envelope is dead-lettered (`DeadLetterStore.put`) and ACKED: never
#      an infinite redelivery loop. An unknown ``type`` is dead-lettered as
#      ``unknown_event`` and a malformed envelope as ``corrupt`` on the
#      first attempt -- neither is raised into the consumer loop.
#    * CAUSATION -- the inbound envelope is attached to the interpreter
#      (``_xsm_cause``) so `OutboxPlugin` stamps ``causationid`` and
#      inherits ``correlationid``.
#
#    The machine runs on the SYNC engine inside a worker thread
#    (`persisted()` is the act-loop); the async API only schedules.
# -----------------------------------------------------------------------------
"""`InboundDispatcher`, `DispatchResult`, `replay_dead_letter`."""

from __future__ import annotations

import asyncio
import functools
import inspect
import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field, replace
from typing import (
    Any,
    Callable,
    Iterable,
    List,
    Optional,
    Tuple,
)

from ..exceptions import InterpreterStoppedError, XStateMachineError
from ..patterns.dead_letter import DeadLetter, MemoryDeadLetterStore
from ..persistence.idempotency import (
    IdempotencyInFlightError,
    IdempotencyMismatchError,
    IdempotencyPlugin,
    fingerprint,
)
from ..plugins import redact
from .broker import Delivery
from .envelope import ATTEMPT_EXTENSION, Envelope, EnvelopeCorruptError

__all__ = [
    "DEFAULT_MAX_ATTEMPTS",
    "DEFAULT_MAX_IN_FLIGHT",
    "DispatchResult",
    "InboundDispatcher",
    "ProcessingFailedError",
    "ReplayRefusedError",
    "ReplayResult",
    "replay_dead_letter",
]

logger = logging.getLogger(__name__)

DEFAULT_MAX_ATTEMPTS = 5
DEFAULT_MAX_IN_FLIGHT = 16
#: Upper bound on deliveries pulled into one `run_once` batch.
DEFAULT_MAX_BATCH = 1000
_ATTEMPTS_MEMORY = 10_000


@dataclass
class DispatchResult:
    """What one `run_once` / `handle` did."""

    processed: int = 0
    duplicates: int = 0
    dead_lettered: int = 0
    retried: int = 0
    ignored: int = 0
    outcomes: List[Tuple[str, str]] = field(default_factory=list)

    def add(self, other: "DispatchResult") -> None:
        self.processed += other.processed
        self.duplicates += other.duplicates
        self.dead_lettered += other.dead_lettered
        self.retried += other.retried
        self.ignored += other.ignored
        self.outcomes.extend(other.outcomes)


class ProcessingFailedError(XStateMachineError):
    """The machine reported an error on the delivered event (an action
    raised, a runaway chain, ...). The delivery is not committed and is
    retried, then dead-lettered after `max_attempts`."""


class _Retry(Exception):
    """Internal: the delivery must be requeued."""


class InboundDispatcher:
    """Consume envelopes into persisted machine instances.

    Args:
        store: A `StateStore` (instances are keyed by ``envelope.subject``).
        machine_for_type: ``(envelope_type) -> MachineNode | None`` (a dict
            works too). ``None`` / `KeyError` → ``unknown_event`` DLQ.
        lock: A `LockStrategy`; default `OptimisticLock()`.
        plugins: Extra plugins for every instance (e.g. `OutboxPlugin`).
        inbox: An `InboxStore` → dedup on ``envelope.id``.
        max_in_flight: Subjects processed concurrently (async API).
        max_attempts: Deliveries before a failing envelope is dead-lettered.
        dead_letters: A dead-letter store; default in-memory.
        event_type: ``(envelope) -> str`` event name override; default
            `default_event_name` (``xsm.<machine>.<EVENT>`` → ``EVENT``).
        clock: Passed to `persisted()` (tests use `SimulatedClock`).
        key_for: `(envelope, machine) -> str` store key; default the
            subject. ChoreographyRouter prefixes the machine id so two
            machines can own the same business key.
        dedup_key: `(envelope) -> str` inbox key; default `envelope.id`.
            Sagas dedup on `causationid` (the upstream event).
        on_unknown: `"dead_letter"` (default, X0.8) or `"ignore"` --
            ack types no machine handles. A choreography bus carries
            other services' events; those are not poison.
    """

    def __init__(
        self,
        store: Any,
        machine_for_type: Any,
        *,
        lock: Optional[Any] = None,
        plugins: Iterable[Any] = (),
        inbox: Optional[Any] = None,
        max_in_flight: int = DEFAULT_MAX_IN_FLIGHT,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        dead_letters: Optional[Any] = None,
        event_type: Optional[Callable[[Envelope], str]] = None,
        clock: Optional[Any] = None,
        max_batch: int = DEFAULT_MAX_BATCH,
        key_for: Optional[Callable[[Envelope, Any], str]] = None,
        dedup_key: Optional[Callable[[Envelope], Optional[str]]] = None,
        on_unknown: str = "dead_letter",
    ) -> None:
        from ..persistence.locking import OptimisticLock

        if max_in_flight < 1:
            raise ValueError("max_in_flight must be >= 1")
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        self.store = store
        self._machine_for_type = machine_for_type
        self.lock = lock if lock is not None else OptimisticLock()
        self.plugins = list(plugins)
        self.inbox = inbox
        self.max_in_flight = int(max_in_flight)
        self.max_attempts = int(max_attempts)
        self.dead_letters = (
            dead_letters
            if dead_letters is not None
            else MemoryDeadLetterStore()
        )
        self.event_type = event_type
        self.clock = clock
        self.max_batch = int(max_batch)
        if on_unknown not in ("dead_letter", "ignore"):
            raise ValueError("on_unknown must be 'dead_letter' or 'ignore'")
        self.on_unknown = on_unknown
        self.key_for = key_for or (lambda env, machine: str(env.subject))
        self.dedup_key = dedup_key or (lambda env: env.id)
        #: envelope id -> failed deliveries seen by THIS dispatcher.
        self._attempts: "OrderedDict[str, int]" = OrderedDict()
        self._lock = threading.Lock()

    # -- lookup ---------------------------------------------------------------
    def machine_for(self, envelope_type: str) -> Any:
        m = self._machine_for_type
        try:
            if isinstance(m, dict):
                return m.get(envelope_type)
            return m(envelope_type)
        except KeyError:
            return None

    # -- attempts -------------------------------------------------------------
    def attempts_of(self, envelope: Envelope) -> int:
        with self._lock:
            local = self._attempts.get(envelope.id, 0)
        return max(envelope.attempt, local)

    def _bump(self, envelope: Envelope) -> int:
        with self._lock:
            n = max(envelope.attempt, self._attempts.get(envelope.id, 0)) + 1
            self._attempts[envelope.id] = n
            self._attempts.move_to_end(envelope.id)
            while len(self._attempts) > _ATTEMPTS_MEMORY:
                self._attempts.popitem(last=False)
        return n

    def _forget(self, envelope: Envelope) -> None:
        with self._lock:
            self._attempts.pop(envelope.id, None)

    # -- one envelope (sync core) -----------------------------------------------
    def handle(
        self, envelope: Envelope, *, topic: Optional[str] = None
    ) -> DispatchResult:
        """Process ONE envelope synchronously; never raises.

        Returns the outcome. A transient failure below `max_attempts` is
        reported as ``retried`` and the caller (the loop) requeues. An
        error OUTSIDE the machine -- the dead-letter store or inbox is
        down, a user ``machine_for_type`` / ``key_for`` raised -- is
        logged and also reported as ``retried`` (nack + requeue), so the
        consumer loop and the other subjects keep running (X0.8).
        """
        res = DispatchResult()
        outcome: Optional[str]
        try:
            outcome = self._handle(envelope, topic)
        except _Retry:
            res.retried += 1
            res.outcomes.append((envelope.id, "retry"))
            return res
        except Exception as exc:  # noqa: BLE001 - infrastructure / user hooks
            logger.exception(
                "🔥 dispatching envelope %s failed outside the machine; "
                "requeueing",
                envelope.id,
            )
            outcome = self._outside_failure(envelope, topic, exc)
            if outcome is None:
                res.retried += 1
                res.outcomes.append((envelope.id, "retry"))
                return res
        if outcome == "duplicate":
            res.duplicates += 1
        elif outcome == "processed":
            res.processed += 1
        elif outcome == "ignored":
            res.ignored += 1
        else:
            res.dead_lettered += 1
        res.outcomes.append((envelope.id, outcome))
        return res

    def _outside_failure(
        self, env: Envelope, topic: Optional[str], exc: Exception
    ) -> Optional[str]:
        """Count a failure OUTSIDE the machine; dead-letter at the cap.

        🔥 #293-a battle: a ``machine_for_type`` / ``key_for`` that raised
        for one envelope requeued it forever -- the attempt counter was
        only bumped for failures inside the machine (X0.8: never an
        infinite redelivery loop). Returns ``None`` to requeue. If the
        dead-letter store itself is down the delivery is requeued (never
        acked without a record).
        """
        if self._bump(env) < self.max_attempts:
            return None
        try:
            return self._dead_letter(env, topic, "max_attempts", exc, None)
        except Exception:  # noqa: BLE001 - DLQ down: keep the message
            logger.exception(
                "🔥 dead-lettering envelope %s failed; requeueing", env.id
            )
            return None

    def _handle(self, env: Envelope, topic: Optional[str]) -> str:
        try:
            env.validate()
            if not env.subject:
                raise EnvelopeCorruptError(
                    "envelope has no subject (the instance key)"
                )
            event = env.to_event(
                self.event_type(env) if self.event_type else None
            )
        except EnvelopeCorruptError as exc:
            return self._dead_letter(env, topic, "corrupt", exc, None)
        machine = self.machine_for(env.type)
        if machine is None and self.on_unknown == "ignore":
            return "ignored"
        if machine is None:
            return self._dead_letter(
                env,
                topic,
                "unknown_event",
                LookupError(f"no machine handles type {env.type!r}"),
                None,
            )
        dup = self._known_duplicate(env, event, machine)
        if dup is not None:
            if dup == "mismatch":
                return self._dead_letter(
                    env,
                    topic,
                    "idempotency_mismatch",
                    IdempotencyMismatchError(str(self.dedup_key(env))),
                    machine,
                )
            self._forget(env)
            return "duplicate"
        try:
            receipt = self._run(env, event, machine)
        except ProcessingFailedError as exc:
            if isinstance(exc.__cause__, InterpreterStoppedError):
                # 🏁 The instance already finished: redelivering cannot
                #    help, so dead-letter now instead of burning attempts.
                return self._dead_letter(
                    env, topic, "instance_done", exc.__cause__, machine
                )
            return self._failed(env, topic, exc, machine)
        except Exception as exc:  # noqa: BLE001 - user code / store
            return self._failed(env, topic, exc, machine)
        err = getattr(receipt, "error", None)
        if getattr(receipt, "duplicate", False):
            if isinstance(err, IdempotencyMismatchError):
                return self._dead_letter(
                    env, topic, "idempotency_mismatch", err, machine
                )
            if isinstance(err, IdempotencyInFlightError):
                return self._failed(env, topic, err, machine)
            self._forget(env)
            return "duplicate"
        self._forget(env)
        return "processed"

    def _known_duplicate(
        self, env: Envelope, event: Any, machine: Any
    ) -> Optional[str]:
        """Answer a redelivery from the inbox BEFORE loading the instance.

        🐛 The `IdempotencyPlugin` runs in ``on_before_send``, which a
        FINISHED instance never reaches (the engine refuses the send with
        `InterpreterStoppedError` first). Without this pre-check a
        redelivery of the event that completed an instance was retried
        and dead-lettered instead of being answered as a duplicate.
        Returns ``"duplicate"``, ``"mismatch"`` or ``None``.
        """
        if self.inbox is None:
            return None
        key = self.dedup_key(env)
        if not key:
            return None
        scope = "/".join(
            (str(env.source), str(machine.id), self.key_for(env, machine))
        )
        entry = self.inbox.get(scope, key)
        if entry is None or entry.receipt_json is None:
            return None  # unseen, or in flight: the plugin decides
        if entry.fingerprint != fingerprint(event):
            return "mismatch"
        return "duplicate"

    def _run(self, env: Envelope, event: Any, machine: Any) -> Any:
        plugins = list(self.plugins)
        key = self.key_for(env, machine)
        dedup = self.dedup_key(env) if self.inbox is not None else None
        if dedup and self.inbox is not None:
            plugins.append(
                IdempotencyPlugin(
                    self.inbox,
                    principal=_const(env.source),
                    key=_const(dedup),
                    instance_key=_const(key),
                )
            )

        def act(interp: Any) -> Any:
            interp._xsm_cause = env
            receipt = interp.send(event, wait=True)
            err = getattr(receipt, "error", None)
            if err is not None and not getattr(receipt, "duplicate", False):
                # 🔁 Not committed: raising here makes `persisted()` skip
                #    the save (and discard inbox marks / outbox rows), so a
                #    redelivery retries from the last good snapshot.
                raise ProcessingFailedError(str(err)) from err
            return receipt

        return self.lock.run(
            self.store,
            key,
            machine,
            act,
            clock=self.clock,
            plugins=plugins,
        )

    def _failed(
        self, env: Envelope, topic: Optional[str], exc: Any, machine: Any
    ) -> str:
        n = self._bump(env)
        if n >= self.max_attempts:
            return self._dead_letter(env, topic, "max_attempts", exc, machine)
        raise _Retry() from exc

    def _dead_letter(
        self,
        env: Envelope,
        topic: Optional[str],
        reason: str,
        exc: Any,
        machine: Any,
    ) -> str:
        from ..persistence.snapshot import structure_hash

        mhash = mversion = None
        if machine is not None:
            try:
                mhash = structure_hash(machine)
            except Exception:  # noqa: BLE001
                mhash = None
            mversion = getattr(machine, "version", None)
        data = env.data if isinstance(env.data, dict) else {}
        record = DeadLetter(
            machine_id=str(
                getattr(machine, "id", None) or env.machineid or "?"
            ),
            state_id="",
            event={
                "type": env.type,
                "payload": redact(dict(data)),
            },
            attempts=max(self.attempts_of(env), 1),
            errors=[
                {
                    "source": "dispatcher",
                    "name": reason,
                    "type": type(exc).__name__,
                    "message": str(exc),
                }
            ],
            snapshot={},
            taken_at=time.time(),
            id=env.id,
            reason=reason,
            envelope=redact(env.to_dict()),
            topic=topic,
            machine_hash=mhash,
            machine_version=mversion,
        )
        put = getattr(self.dead_letters, "put", None) or self.dead_letters
        put(record)
        self._forget(env)
        return f"dead_lettered:{reason}"

    # -- sync consumer ------------------------------------------------------------
    def run_once_sync(
        self, broker: Any, topic: str, *, timeout: float = 0.0
    ) -> DispatchResult:
        """Drain what *topic* holds now through a `SyncBrokerAdapter`."""
        batch = self._collect_sync(broker, topic, timeout)
        total = DispatchResult()
        for subject_batch in _by_subject(batch).values():
            total.add(self._subject_sync(broker, topic, subject_batch))
        return total

    def _collect_sync(
        self, broker: Any, topic: str, timeout: float
    ) -> List[Delivery]:
        out: List[Delivery] = []
        for d in broker.subscribe(topic, timeout=timeout):
            out.append(d)
            if len(out) >= self.max_batch:
                break
        return out

    def _subject_sync(
        self, broker: Any, topic: str, batch: List[Delivery]
    ) -> DispatchResult:
        total = DispatchResult()
        for n, d in enumerate(batch):
            res = self.handle(d.envelope, topic=topic)
            total.add(res)
            if res.retried:
                # Requeue this one and every later one of the subject,
                # last first, so the head is the failed delivery.
                for later in reversed(batch[n:]):
                    broker.nack(later, requeue=True)
                return total
            broker.ack(d)
        return total

    # -- async consumer -----------------------------------------------------------
    async def run_once(
        self, broker: Any, topic: str, *, timeout: float = 0.0
    ) -> DispatchResult:
        """Drain what *topic* holds now (waiting up to *timeout* s for the
        first delivery) through an async `BrokerAdapter`."""
        loop = asyncio.get_running_loop()
        for p in self.plugins:
            if hasattr(p, "loop"):
                p.loop = loop
        batch: List[Delivery] = []
        async for d in broker.subscribe(topic, timeout=timeout):
            batch.append(d)
            if len(batch) >= self.max_batch:
                break
        sem = asyncio.Semaphore(self.max_in_flight)
        total = DispatchResult()

        async def one_subject(items: List[Delivery]) -> None:
            async with sem:
                for n, d in enumerate(items):
                    res = await loop.run_in_executor(
                        None,
                        functools.partial(
                            self.handle, d.envelope, topic=topic
                        ),
                    )
                    total.add(res)
                    if res.retried:
                        for later in reversed(items[n:]):
                            await _maybe_await(
                                broker.nack(later, requeue=True)
                            )
                        return
                    await _maybe_await(broker.ack(d))

        await asyncio.gather(
            *(one_subject(v) for v in _by_subject(batch).values())
        )
        for p in self.plugins:
            drain = getattr(p, "drain", None)
            if drain is not None and inspect.iscoroutinefunction(drain):
                await drain()
        return total

    async def run_forever(
        self,
        broker: Any,
        topic: str,
        stop: asyncio.Event,
        *,
        poll_timeout: float = 0.05,
    ) -> DispatchResult:
        """`run_once` in a loop until *stop* is set."""
        total = DispatchResult()
        while not stop.is_set():
            total.add(await self.run_once(broker, topic, timeout=poll_timeout))
        return total


def _const(value: Any) -> Callable[[Any], Any]:
    def _f(_: Any) -> Any:
        return value

    return _f


async def _maybe_await(value: Any) -> None:
    if asyncio.iscoroutine(value) or isinstance(value, asyncio.Future):
        await value


def _by_subject(batch: List[Delivery]) -> "OrderedDict[str, List[Delivery]]":
    groups: "OrderedDict[str, List[Delivery]]" = OrderedDict()
    for d in batch:
        groups.setdefault(str(d.envelope.subject), []).append(d)
    return groups


# -----------------------------------------------------------------------------
# 🔁 Replay a dead letter (used by `xsm dlq replay`)
# -----------------------------------------------------------------------------
class ReplayRefusedError(XStateMachineError):
    """A dead-letter replay was refused (no envelope, machine mismatch,
    missing ``reason``)."""


@dataclass
class ReplayResult:
    record_id: str
    dry_run: bool
    outcome: str
    warnings: List[str] = field(default_factory=list)


def replay_dead_letter(
    dead_letters: Any,
    record_id: str,
    dispatcher: InboundDispatcher,
    *,
    reason: str,
    dry_run: bool = True,
    force: bool = False,
    actor: Optional[str] = None,
) -> ReplayResult:
    """Re-send a dead-lettered envelope through *dispatcher*.

    * Reuses the envelope ``id`` (attempt counter reset) so an inbox dedups
      a double replay.
    * Refuses when the record's ``machine_hash`` / ``machine_version``
      differ from the machine the dispatcher would use, unless *force*.
    * *dry_run* (the default) only reports; otherwise the record is marked
      resolved on success and the action is audited when the store
      supports ``audit()``.
    """
    if not reason or not reason.strip():
        raise ReplayRefusedError("a replay needs a --reason")
    rec = dead_letters.get(record_id)
    if rec is None:
        raise ReplayRefusedError(f"no dead letter with id {record_id!r}")
    if not rec.envelope:
        raise ReplayRefusedError(
            "this dead letter was captured from a chart state, not an "
            "envelope; restore its snapshot instead"
        )
    env = Envelope.from_dict(dict(rec.envelope))
    ext = {k: v for k, v in env.extensions.items() if k != ATTEMPT_EXTENSION}
    env = replace(env, extensions=ext)
    warnings = _replay_mismatches(rec, dispatcher.machine_for(env.type))
    if warnings and not force:
        raise ReplayRefusedError(
            "; ".join(warnings) + " (use --force to replay anyway)"
        )
    if dry_run:
        return ReplayResult(rec.id, True, "would_replay", warnings)
    res = dispatcher.handle(env, topic=rec.topic)
    outcome = res.outcomes[-1][1] if res.outcomes else "unknown"
    if outcome in ("processed", "duplicate"):
        dead_letters.mark_resolved(rec.id, time.time())
    audit = getattr(dead_letters, "audit", None)
    if callable(audit):
        audit(
            "replay",
            rec.id,
            reason,
            {"outcome": outcome, "forced": bool(force and warnings)},
            actor=actor,
        )
    return ReplayResult(rec.id, False, outcome, warnings)


def _replay_mismatches(rec: DeadLetter, machine: Any) -> List[str]:
    from ..persistence.snapshot import structure_hash

    if machine is None:
        return [f"no machine handles type {rec.event.get('type')!r} now"]
    out: List[str] = []
    if rec.machine_hash and rec.machine_hash != structure_hash(machine):
        out.append(
            f"machine structure changed since capture "
            f"({rec.machine_hash} != {structure_hash(machine)})"
        )
    version = getattr(machine, "version", None)
    if rec.machine_version and rec.machine_version != version:
        out.append(
            f"machine version changed since capture "
            f"({rec.machine_version!r} != {version!r})"
        )
    return out
