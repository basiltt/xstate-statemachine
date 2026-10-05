# src/xstate_statemachine/eda/fake.py
# -----------------------------------------------------------------------------
# 🧪 FakeBrokerAdapter -- an in-memory broker for tests (#272)
# -----------------------------------------------------------------------------
# 🏛️ Lives in CORE (stdlib only): a fake that needs nothing is not an
#    extra, and `tests/eda/` must run in the default CI job. The
#    `[testing]` extra re-exports it (`contrib.testing.FakeBrokerAdapter`)
#    next to the replay helpers.
#
#    Semantics are the `BrokerAdapter` contract, no more: FIFO per topic
#    (hence per subject), explicit ack/nack, requeue to the head. Test
#    affordances on top: `published` (everything ever published),
#    `deliver()` to inject inbound traffic, `fail_next_publish()` for
#    failure injection, `on()` + `drain()` to run handlers synchronously.
# -----------------------------------------------------------------------------
"""`FakeBrokerAdapter` (async) and `SyncFakeBrokerAdapter`."""

from __future__ import annotations

import asyncio
import threading
import time
from collections import deque
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Deque,
    Dict,
    Iterator,
    List,
    Optional,
    Tuple,
)

from .broker import Delivery
from ..persistence.store import DEFAULT_MAX_SNAPSHOT_BYTES
from .envelope import Envelope

__all__ = [
    "BrokerPublishError",
    "DEFAULT_DRAIN_LIMIT",
    "FakeBrokerAdapter",
    "SyncFakeBrokerAdapter",
]

_POLL_S = 0.005
#: `drain()` refuses to loop forever: a handler that republishes to its
#: own topic is a test bug, reported loudly instead of hanging CI.
DEFAULT_DRAIN_LIMIT = 100_000


class BrokerPublishError(ConnectionError):
    """The failure `fail_next_publish()` injects by default."""


class _Core:
    """The broker state shared by both fakes. Thread-safe.

    Envelopes cross the fake the way they cross a real broker: encoded
    with ``to_json(max_bytes=...)`` and decoded again (battle #272). So a
    non-JSON payload or an oversized envelope fails at ``publish`` /
    ``deliver`` like a real adapter, and a consumer that mutates
    ``delivery.envelope.data`` cannot rewrite the ``published`` record.
    A ``nack(requeue=True)`` redelivers with ``attempt + 1`` stamped, as
    the real adapters do. Records (``published`` / ``acked`` /
    ``nacked``) grow by design; `clear()` resets everything.
    """

    def __init__(self, *, max_bytes: int = DEFAULT_MAX_SNAPSHOT_BYTES) -> None:
        self.max_bytes = int(max_bytes)
        self._lock = threading.Lock()
        self._queues: Dict[str, Deque[Envelope]] = {}
        # id(delivery) -> (delivery, the pristine envelope a requeue uses)
        self._inflight: Dict[int, Tuple[Delivery, Envelope]] = {}
        self.published: List[Envelope] = []
        self._log: List[Any] = []  # (topic, envelope)
        self.acked: List[Envelope] = []
        self.nacked: List[Envelope] = []
        self._fail: List[BaseException] = []
        self._handlers: Dict[str, Callable[[Envelope], Any]] = {}

    # -- test affordances ----------------------------------------------------
    def fail_next_publish(
        self, error: Optional[BaseException] = None, *, times: int = 1
    ) -> None:
        """Make the next *times* publishes (any topic, in call order) raise
        *error* (default `BrokerPublishError`). *error* must be an
        `Exception`: injecting ``KeyboardInterrupt`` / ``SystemExit``
        would tear down the test runner, not simulate a broker."""
        if error is not None and not isinstance(error, Exception):
            raise TypeError(
                "fail_next_publish() needs an Exception instance, got "
                f"{type(error).__name__}"
            )
        if isinstance(times, bool) or not isinstance(times, int) or times < 1:
            raise ValueError(f"times must be an int >= 1, got {times!r}")
        with self._lock:
            for _ in range(times):
                self._fail.append(error or BrokerPublishError("injected"))

    def clear(self) -> None:
        """Forget everything: queues, records, pending failures, handlers.
        In-flight deliveries become unknown (settling them is a no-op)."""
        with self._lock:
            for coll in (
                self._queues,
                self._inflight,
                self.published,
                self._log,
                self.acked,
                self.nacked,
                self._fail,
                self._handlers,
            ):
                coll.clear()

    def published_on(self, topic: str) -> List[Envelope]:
        with self._lock:
            return [e for t, e in self._log if t == topic]

    def pending(self, topic: str) -> int:
        with self._lock:
            return len(self._queues.get(topic, ()))

    def topics(self) -> List[str]:
        with self._lock:
            return sorted(self._queues)

    def on(self, topic: str, handler: Callable[[Envelope], Any]) -> None:
        """Register a handler `drain()` calls for each envelope on *topic*."""
        with self._lock:  # the class promises thread-safety (#272 review)
            self._handlers[topic] = handler

    def drain(
        self, topic: Optional[str] = None, *, limit: int = DEFAULT_DRAIN_LIMIT
    ) -> int:
        """Run registered handlers until their topics are empty.

        A handler that returns normally acks; one that raises nacks
        without requeue and the exception propagates. Handlers may
        publish; their output is drained in the same call. Returns the
        number of envelopes handled. With *topic*, only that topic's
        handler runs. Handling more than *limit* envelopes raises
        `RuntimeError` -- a handler feeding its own topic would otherwise
        never return.
        """
        # 📝 #272 review (H1): `limit` is validated and checked BEFORE each
        #    take, so a drain that handles exactly `limit` envelopes and
        #    empties the topics returns normally; only a take that would
        #    exceed it raises. The old top-of-pass check fired after a
        #    completed drain of exactly `limit`, and k handlers could
        #    overshoot by k-1.
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError(
                f"drain(): limit must be an int >= 1, got {limit!r}"
            )
        handled = 0
        while True:
            progressed = False
            with self._lock:
                handlers = list(self._handlers.items())
            for t, handler in handlers:
                if topic is not None and t != topic:
                    continue
                if handled >= limit:
                    with self._lock:
                        empty = not self._queues.get(t)
                    if empty:
                        continue  # nothing more here; keep checking
                    raise RuntimeError(
                        f"drain() handled {handled} envelopes and the topics "
                        f"are still not empty (a handler feeding itself?)"
                    )
                d = self._take(t)
                if d is None:
                    continue
                progressed = True
                try:
                    handler(d.envelope)
                except Exception:
                    # a handler FAILURE: nack without requeue, propagate
                    self._settle(d, ack=False, requeue=False)
                    raise
                except BaseException:
                    # 📝 #272 review (H2): KeyboardInterrupt / SystemExit
                    #    tear down the runner -- they must not permanently
                    #    drop the envelope. Release it (no nack counted,
                    #    ``attempt`` unchanged) and re-raise untouched.
                    self._release(d)
                    raise
                self._settle(d, ack=True, requeue=False)
                handled += 1
            if not progressed:
                return handled

    # -- primitives ----------------------------------------------------------
    def _publish(self, topic: str, envelope: Envelope) -> None:
        if not isinstance(envelope, Envelope):
            raise TypeError("publish() needs an Envelope")
        # 📝 #272 review (L2): the injected failure is checked BEFORE the
        #    size cap -- "the broker is down" wins over "too big", as a
        #    real client fails on connect before it serialises. Note that
        #    the failure is NOT consumed when the envelope is malformed
        #    (the TypeError above fires first).
        with self._lock:
            if self._fail:
                raise self._fail.pop(0)
        envelope = self._wire(envelope)
        with self._lock:
            # 📝 #272 review (L1): the `published` record is a SECOND copy,
            #    so ``broker.published[0] is env`` is False by design --
            #    compare by ``id`` / value, never identity.
            self.published.append(self._wire(envelope))
            self._log.append((topic, envelope))
            self._queues.setdefault(topic, deque()).append(envelope)

    def _inject(self, topic: str, envelope: Envelope) -> None:
        # 📝 Battle #268: same typed refusal as `publish` -- a malformed
        #    injection must fail HERE, not later inside the consumer.
        if not isinstance(envelope, Envelope):
            raise TypeError(
                f"deliver() needs an Envelope, got {type(envelope).__name__}"
            )
        envelope = self._wire(envelope)
        with self._lock:
            self._queues.setdefault(topic, deque()).append(envelope)

    def _wire(self, envelope: Envelope) -> Envelope:
        """Encode + decode, as a real broker would (size cap; values JSON
        cannot hold become ``str`` exactly as on a real wire; no mutable
        ``data`` shared between parties)."""
        return Envelope.from_json(
            envelope.to_json(max_bytes=self.max_bytes),
            max_bytes=self.max_bytes,
        )

    def _take(self, topic: str) -> Optional[Delivery]:
        with self._lock:
            q = self._queues.get(topic)
            if not q:
                return None
            # 📝 Each delivery gets its own decoded copy: a consumer that
            #    mutates ``data`` and nacks must not change the redelivery.
            pristine = q.popleft()
            d = self._make(topic, self._wire(pristine))
            self._inflight[id(d)] = (d, pristine)
            return d

    def _make(self, topic: str, env: Envelope) -> Delivery:
        box: List[Delivery] = []

        def ack() -> None:
            self._settle(box[0], ack=True, requeue=False)

        def nack(requeue: bool = True) -> None:
            self._settle(box[0], ack=False, requeue=requeue)

        box.append(Delivery(env, topic, ack, nack))
        return box[0]

    def _settle(self, d: Delivery, *, ack: bool, requeue: bool) -> None:
        with self._lock:
            # 📝 Identity, not just id(): an unknown delivery (another
            #    broker's, or one forgotten by `clear()`) is a no-op.
            entry = self._inflight.get(id(d))
            if entry is None or entry[0] is not d:
                return  # settled already / unknown: a no-op
            del self._inflight[id(d)]
            pristine = entry[1]
            if ack:
                self.acked.append(d.envelope)
                return
            self.nacked.append(d.envelope)
            if requeue:
                # 📝 As every real adapter (`_base._requeue`): the
                #    redelivery carries ``attempt + 1``.
                env = pristine.with_attempt(pristine.attempt + 1)
                self._queues.setdefault(d.topic, deque()).appendleft(env)

    def _release(self, d: Delivery) -> None:
        """Put an UNSETTLED delivery back at the head of its queue.

        📝 #272 review (M4): a consumer loop cancelled / closed while the
        last yielded delivery was still in flight must not lose it. This
        is neither an ack nor a nack -- the consumer never decided -- so
        nothing is counted and ``attempt`` is unchanged.
        """
        with self._lock:
            entry = self._inflight.get(id(d))
            if entry is None or entry[0] is not d:
                return
            del self._inflight[id(d)]
            self._queues.setdefault(d.topic, deque()).appendleft(entry[1])

    @property
    def in_flight(self) -> int:
        with self._lock:
            return len(self._inflight)


class FakeBrokerAdapter(_Core):
    """In-memory async `BrokerAdapter`.

    ``subscribe(topic, timeout=None)`` waits forever for traffic (like a
    real consumer) -- in a test that is a HANG, so pass a *timeout* (idle
    seconds; ``0`` = "drain what is queued and stop"). Breaking out of /
    cancelling the loop while a yielded delivery is unsettled requeues it
    untouched (no nack counted, ``attempt`` unchanged) when the generator
    is closed -- immediately on ``break`` / ``aclose()``, on the loop's
    next turn after a task cancellation (asyncio finalises it then).

    ::

        broker = FakeBrokerAdapter()
        await broker.deliver("orders", Envelope.new(type="xsm.o.GO",
                                                    subject="o-1"))
        async for d in broker.subscribe("orders", timeout=0):
            ...
            await broker.ack(d)
    """

    async def publish(self, topic: str, envelope: Envelope) -> None:
        self._publish(topic, envelope)

    async def deliver(self, topic: str, envelope: Envelope) -> None:
        """Inject an inbound envelope (not recorded in `published`)."""
        self._inject(topic, envelope)

    async def subscribe(
        self, topic: str, *, timeout: Optional[float] = None
    ) -> AsyncIterator[Delivery]:
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            d = self._take(topic)
            if d is not None:
                try:
                    yield d
                except BaseException:
                    # GeneratorExit / CancelledError: see `_release`
                    self._release(d)
                    raise
                # 📝 As the real adapters: *timeout* is IDLE time; a
                #    consumer must not stop mid-backlog.
                if timeout is not None:
                    deadline = time.monotonic() + timeout
                continue
            if deadline is not None and time.monotonic() >= deadline:
                return
            await asyncio.sleep(_POLL_S)

    async def ack(self, delivery: Delivery) -> None:
        self._settle(delivery, ack=True, requeue=False)

    async def nack(self, delivery: Delivery, *, requeue: bool) -> None:
        self._settle(delivery, ack=False, requeue=requeue)


class SyncFakeBrokerAdapter(_Core):
    """In-memory blocking `SyncBrokerAdapter` (threads, Celery, Django).

    ``subscribe(topic, timeout=None)`` blocks forever when idle -- pass an
    idle *timeout* in tests (``0`` drains the backlog and stops). A
    ``break`` out of the loop with the last delivery unsettled requeues
    it untouched.
    """

    def publish(self, topic: str, envelope: Envelope) -> None:
        self._publish(topic, envelope)

    def deliver(self, topic: str, envelope: Envelope) -> None:
        self._inject(topic, envelope)

    def subscribe(
        self, topic: str, *, timeout: Optional[float] = None
    ) -> Iterator[Delivery]:
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            d = self._take(topic)
            if d is not None:
                try:
                    yield d
                except BaseException:
                    # GeneratorExit (a `break`): see `_release`
                    self._release(d)
                    raise
                # 📝 As the real adapters: *timeout* is IDLE time; a
                #    consumer must not stop mid-backlog.
                if timeout is not None:
                    deadline = time.monotonic() + timeout
                continue
            if deadline is not None and time.monotonic() >= deadline:
                return
            time.sleep(_POLL_S)

    def ack(self, delivery: Delivery) -> None:
        self._settle(delivery, ack=True, requeue=False)

    def nack(self, delivery: Delivery, *, requeue: bool) -> None:
        self._settle(delivery, ack=False, requeue=requeue)
