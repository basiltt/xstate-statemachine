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
    Set,
)

from .broker import Delivery
from .envelope import Envelope

__all__ = ["BrokerPublishError", "FakeBrokerAdapter", "SyncFakeBrokerAdapter"]

_POLL_S = 0.005


class BrokerPublishError(ConnectionError):
    """The failure `fail_next_publish()` injects by default."""


class _Core:
    """The broker state shared by both fakes. Thread-safe."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._queues: Dict[str, Deque[Envelope]] = {}
        self._inflight: Dict[int, Delivery] = {}
        self._settled: Set[int] = set()
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
        """Make the next *times* publishes raise *error*."""
        with self._lock:
            for _ in range(times):
                self._fail.append(error or BrokerPublishError("injected"))

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
        self._handlers[topic] = handler

    def drain(self, topic: Optional[str] = None) -> int:
        """Run registered handlers until their topics are empty.

        A handler that returns normally acks; one that raises nacks
        without requeue and the exception propagates. Handlers may
        publish; their output is drained in the same call. Returns the
        number of envelopes handled.
        """
        handled = 0
        while True:
            progressed = False
            for t, handler in list(self._handlers.items()):
                if topic is not None and t != topic:
                    continue
                d = self._take(t)
                if d is None:
                    continue
                progressed = True
                try:
                    handler(d.envelope)
                except BaseException:
                    self._settle(d, ack=False, requeue=False)
                    raise
                self._settle(d, ack=True, requeue=False)
                handled += 1
            if not progressed:
                return handled

    # -- primitives ----------------------------------------------------------
    def _publish(self, topic: str, envelope: Envelope) -> None:
        if not isinstance(envelope, Envelope):
            raise TypeError("publish() needs an Envelope")
        with self._lock:
            if self._fail:
                raise self._fail.pop(0)
            self.published.append(envelope)
            self._log.append((topic, envelope))
            self._queues.setdefault(topic, deque()).append(envelope)

    def _inject(self, topic: str, envelope: Envelope) -> None:
        with self._lock:
            self._queues.setdefault(topic, deque()).append(envelope)

    def _take(self, topic: str) -> Optional[Delivery]:
        with self._lock:
            q = self._queues.get(topic)
            if not q:
                return None
            env = q.popleft()
            d = self._make(topic, env)
            self._inflight[id(d)] = d
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
            if self._inflight.pop(id(d), None) is None:
                return  # settled already: a no-op
            if ack:
                self.acked.append(d.envelope)
                return
            self.nacked.append(d.envelope)
            if requeue:
                self._queues.setdefault(d.topic, deque()).appendleft(
                    d.envelope
                )

    @property
    def in_flight(self) -> int:
        with self._lock:
            return len(self._inflight)


class FakeBrokerAdapter(_Core):
    """In-memory async `BrokerAdapter`.

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
                yield d
                continue
            if deadline is not None and time.monotonic() >= deadline:
                return
            await asyncio.sleep(_POLL_S)

    async def ack(self, delivery: Delivery) -> None:
        self._settle(delivery, ack=True, requeue=False)

    async def nack(self, delivery: Delivery, *, requeue: bool) -> None:
        self._settle(delivery, ack=False, requeue=requeue)


class SyncFakeBrokerAdapter(_Core):
    """In-memory blocking `SyncBrokerAdapter` (threads, Celery, Django)."""

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
                yield d
                continue
            if deadline is not None and time.monotonic() >= deadline:
                return
            time.sleep(_POLL_S)

    def ack(self, delivery: Delivery) -> None:
        self._settle(delivery, ack=True, requeue=False)

    def nack(self, delivery: Delivery, *, requeue: bool) -> None:
        self._settle(delivery, ack=False, requeue=requeue)
