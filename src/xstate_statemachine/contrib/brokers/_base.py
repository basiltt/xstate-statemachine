# src/xstate_statemachine/contrib/brokers/_base.py
# -----------------------------------------------------------------------------
# ðŸ§± The shared adapter skeleton: one bookkeeping core, thin transports (#294)
# -----------------------------------------------------------------------------
# ðŸ›ï¸ Every broker adapter is `SyncBroker` / `AsyncBroker` + a *transport*
#    that knows four native operations and nothing else:
#
#        send(topic, envelope)            -> publish, raise on failure
#        fetch(topic, wait_s) -> [Raw]    -> pull what is ready (<= wait_s)
#        ack(native)                      -> settle for good
#        drop(native)                     -> settle without redelivery
#
#    The core owns what the `BrokerAdapter` contract promises, identically
#    for every broker:
#
#      * a per-topic LOCAL deque: fetched messages wait there, and a
#        ``nack(requeue=True)`` puts the delivery back at its HEAD, so it
#        is redelivered before anything fetched after it (per-subject
#        order) WITHOUT a round trip to the broker. The native message
#        stays un-acked meanwhile, so a crash still means native
#        redelivery (at-least-once);
#      * settle-once: the second ack/nack of a delivery is a no-op;
#      * attempts (X0.8): a native redelivery count (Redis PEL, SQS
#        ApproximateReceiveCount, NATS num_delivered, AMQP redelivered)
#        and every local requeue are stamped with `Envelope.with_attempt`,
#        so `InboundDispatcher` dead-letters a poison message even across
#        consumer restarts;
#      * size cap (X0.4): inbound bytes go through `Envelope.from_json`
#        with ``max_bytes`` BEFORE parsing; an undecodable message is
#        reported to ``on_undecodable`` and dropped -- it can never loop;
#      * health: a transport call that raises marks the adapter unhealthy
#        and fires ``on_disconnect`` once; the next success fires
#        ``on_reconnect``. The client's own reconnect logic does the
#        reconnecting -- we only make it observable.
# -----------------------------------------------------------------------------
"""Shared bookkeeping for the broker adapters."""

from __future__ import annotations

import asyncio
import logging
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
    NamedTuple,
    Optional,
    Tuple,
)

from ...eda.broker import Delivery
from ...eda.envelope import Envelope, EnvelopeCorruptError
from ...persistence.store import DEFAULT_MAX_SNAPSHOT_BYTES

__all__ = [
    "AsyncBroker",
    "Raw",
    "SyncBroker",
    "ThreadedTransport",
    "default_on_undecodable",
]

logger = logging.getLogger(__name__)

#: Longest single blocking fetch when ``subscribe(timeout=None)``.
POLL_S = 1.0


class Raw(NamedTuple):
    """One message as a transport fetched it.

    Attributes:
        body: The structured-mode CloudEvents JSON (bytes or str).
        native: Whatever the transport needs to ack / drop it later.
        attempts: Deliveries the BROKER already made before this one
            (``0`` for a first delivery).
    """

    body: Any
    native: Any
    attempts: int = 0


def default_on_undecodable(topic: str, raw: Raw, exc: Exception) -> None:
    """Log (never the body -- it may be hostile or sensitive) and drop."""
    logger.warning(
        "ðŸ”¥ dropping undecodable message on %r: %s: %s",
        topic,
        type(exc).__name__,
        exc,
    )


class _Core:
    """Thread-safe local state shared by the sync and async bases."""

    def __init__(
        self,
        *,
        max_bytes: int = DEFAULT_MAX_SNAPSHOT_BYTES,
        on_disconnect: Optional[Callable[[Exception], Any]] = None,
        on_reconnect: Optional[Callable[[], Any]] = None,
        on_undecodable: Optional[Callable[[str, Raw, Exception], Any]] = None,
    ) -> None:
        self.max_bytes = int(max_bytes)
        self.on_disconnect = on_disconnect
        self.on_reconnect = on_reconnect
        self.on_undecodable = on_undecodable or default_on_undecodable
        self._lock = threading.Lock()
        self._local: Dict[str, Deque[Tuple[Envelope, Any]]] = {}
        self._inflight: Dict[int, Tuple[Delivery, Any]] = {}
        self._healthy = True

    # -- health ---------------------------------------------------------------
    @property
    def healthy(self) -> bool:
        """``False`` after a transport call failed, until one succeeds."""
        return self._healthy

    def _io_ok(self) -> None:
        if not self._healthy:
            self._healthy = True
            logger.info("âœ… broker connection healthy again")
            if self.on_reconnect is not None:
                self.on_reconnect()

    def _io_failed(self, exc: Exception) -> None:
        if self._healthy:
            self._healthy = False
            logger.warning("ðŸ”¥ broker call failed: %s", exc)
            if self.on_disconnect is not None:
                self.on_disconnect(exc)

    # -- local queue ----------------------------------------------------------
    def _pop(self, topic: str) -> Optional[Tuple[Envelope, Any]]:
        with self._lock:
            q = self._local.get(topic)
            return q.popleft() if q else None

    def _decode(self, topic: str, raws: List[Raw]) -> List[Tuple[Any, Any]]:
        """Decode fetched messages; returns ``(envelope | None, native)``
        (``None`` = undecodable: the caller drops the native message)."""
        out: List[Tuple[Any, Any]] = []
        for raw in raws:
            try:
                env = Envelope.from_json(raw.body, max_bytes=self.max_bytes)
            except EnvelopeCorruptError as exc:
                self.on_undecodable(topic, raw, exc)
                out.append((None, raw.native))
                continue
            if raw.attempts > env.attempt:
                env = env.with_attempt(raw.attempts)
            out.append((env, raw.native))
        return out

    def _stash(self, topic: str, items: List[Tuple[Envelope, Any]]) -> None:
        with self._lock:
            self._local.setdefault(topic, deque()).extend(items)

    def _deliver(self, topic: str, env: Envelope, native: Any) -> Delivery:
        box: List[Delivery] = []

        def ack() -> Any:
            return self.ack(box[0])

        def nack(requeue: bool = True) -> Any:
            return self.nack(box[0], requeue=requeue)

        d = Delivery(env, topic, ack, nack)
        box.append(d)
        with self._lock:
            self._inflight[id(d)] = (d, native)
        return d

    def _claim(self, delivery: Delivery) -> Tuple[bool, Any]:
        with self._lock:
            entry = self._inflight.pop(id(delivery), None)
        if entry is None:
            return False, None
        return True, entry[1]

    def _requeue(self, delivery: Delivery, native: Any) -> None:
        env = delivery.envelope
        env = env.with_attempt(env.attempt + 1)
        with self._lock:
            self._local.setdefault(delivery.topic, deque()).appendleft(
                (env, native)
            )

    @property
    def in_flight(self) -> int:
        """Deliveries handed out and not yet settled."""
        with self._lock:
            return len(self._inflight)

    def held(self, topic: str) -> int:
        """Messages fetched (or requeued) locally and not yet delivered."""
        with self._lock:
            return len(self._local.get(topic, ()))

    # placeholders overridden by the bases
    def ack(self, delivery: Delivery) -> Any:  # pragma: no cover
        raise NotImplementedError

    def nack(
        self, delivery: Delivery, *, requeue: bool
    ) -> Any:  # pragma: no cover
        raise NotImplementedError


def _deadline(timeout: Optional[float]) -> Optional[float]:
    return None if timeout is None else time.monotonic() + timeout


def _expired(deadline: Optional[float]) -> bool:
    return deadline is not None and time.monotonic() >= deadline


def _wait_for(deadline: Optional[float]) -> float:
    if deadline is None:
        return POLL_S
    return max(0.0, min(POLL_S, deadline - time.monotonic()))


class SyncBroker(_Core):
    """A `SyncBrokerAdapter` over a blocking transport."""

    def __init__(self, transport: Any, **kw: Any) -> None:
        super().__init__(**kw)
        self.transport = transport

    def _call(self, fn: Callable[..., Any], *args: Any) -> Any:
        try:
            result = fn(*args)
        except Exception as exc:
            self._io_failed(exc)
            raise
        self._io_ok()
        return result

    def publish(self, topic: str, envelope: Envelope) -> None:
        if not isinstance(envelope, Envelope):
            raise TypeError("publish() needs an Envelope")
        self._call(self.transport.send, topic, envelope)

    def subscribe(
        self, topic: str, *, timeout: Optional[float] = None
    ) -> Iterator[Delivery]:
        deadline = _deadline(timeout)
        fetched = False
        while True:
            item = self._pop(topic)
            if item is not None:
                yield self._deliver(topic, *item)
                continue
            if fetched and _expired(deadline):
                return
            fetched = True
            raws = self._call(self.transport.fetch, topic, _wait_for(deadline))
            good = []
            for env, native in self._decode(topic, raws):
                if env is None:
                    self._call(self.transport.drop, native)
                else:
                    good.append((env, native))
            self._stash(topic, good)

    def ack(self, delivery: Delivery) -> None:
        claimed, native = self._claim(delivery)
        if claimed:
            self._call(self.transport.ack, native)

    def nack(self, delivery: Delivery, *, requeue: bool) -> None:
        claimed, native = self._claim(delivery)
        if not claimed:
            return
        if requeue:
            self._requeue(delivery, native)
        else:
            self._call(self.transport.drop, native)

    def close(self) -> None:
        close = getattr(self.transport, "close", None)
        if close is not None:
            close()


class AsyncBroker(_Core):
    """A `BrokerAdapter` over an async transport."""

    def __init__(self, transport: Any, **kw: Any) -> None:
        super().__init__(**kw)
        self.transport = transport
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def _check_loop(self) -> None:
        """Client connections (aiokafka, aio-pika, nats-py) belong to the
        event loop that opened them. When the adapter is used from a NEW
        loop (a second ``asyncio.run``), the transport drops its
        connections and reconnects lazily; messages fetched on the old
        connection are forgotten locally -- the broker still holds them
        un-acked and redelivers them (at-least-once; the inbox dedups)."""
        loop = asyncio.get_running_loop()
        if self._loop is loop:
            return
        if self._loop is not None:
            rebind = getattr(self.transport, "rebind", None)
            if rebind is not None:
                rebind()
                with self._lock:
                    self._local.clear()
                    self._inflight.clear()
        self._loop = loop

    async def _call(self, fn: Callable[..., Any], *args: Any) -> Any:
        try:
            result = await fn(*args)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._io_failed(exc)
            raise
        self._io_ok()
        return result

    async def publish(self, topic: str, envelope: Envelope) -> None:
        if not isinstance(envelope, Envelope):
            raise TypeError("publish() needs an Envelope")
        self._check_loop()
        await self._call(self.transport.send, topic, envelope)

    async def subscribe(
        self, topic: str, *, timeout: Optional[float] = None
    ) -> AsyncIterator[Delivery]:
        self._check_loop()
        deadline = _deadline(timeout)
        fetched = False
        while True:
            item = self._pop(topic)
            if item is not None:
                yield self._deliver(topic, *item)
                continue
            if fetched and _expired(deadline):
                return
            fetched = True
            raws = await self._call(
                self.transport.fetch, topic, _wait_for(deadline)
            )
            good = []
            for env, native in self._decode(topic, raws):
                if env is None:
                    await self._call(self.transport.drop, native)
                else:
                    good.append((env, native))
            self._stash(topic, good)

    async def ack(self, delivery: Delivery) -> None:
        self._check_loop()
        claimed, native = self._claim(delivery)
        if claimed:
            await self._call(self.transport.ack, native)

    async def nack(self, delivery: Delivery, *, requeue: bool) -> None:
        self._check_loop()
        claimed, native = self._claim(delivery)
        if not claimed:
            return
        if requeue:
            self._requeue(delivery, native)
        else:
            await self._call(self.transport.drop, native)

    async def close(self) -> None:
        close = getattr(self.transport, "close", None)
        if close is not None:
            result = close()
            if asyncio.iscoroutine(result):
                await result


class ThreadedTransport:
    """Run a blocking transport's calls on a worker thread (async view).

    Used where the client library is synchronous (boto3) or where one
    thread-safe connection pool should back both engines (redis-py).
    """

    def __init__(self, inner: Any) -> None:
        self.inner = inner

    async def send(self, topic: str, envelope: Envelope) -> None:
        await asyncio.get_running_loop().run_in_executor(
            None, self.inner.send, topic, envelope
        )

    async def fetch(self, topic: str, wait_s: float) -> List[Raw]:
        return await asyncio.get_running_loop().run_in_executor(
            None, self.inner.fetch, topic, wait_s
        )

    async def ack(self, native: Any) -> None:
        await asyncio.get_running_loop().run_in_executor(
            None, self.inner.ack, native
        )

    async def drop(self, native: Any) -> None:
        await asyncio.get_running_loop().run_in_executor(
            None, self.inner.drop, native
        )

    def close(self) -> None:
        close = getattr(self.inner, "close", None)
        if close is not None:
            close()


def structured(envelope: Envelope, max_bytes: int) -> bytes:
    """The structured-mode body every adapter publishes (size-capped)."""
    return envelope.to_json(max_bytes=max_bytes).encode("utf-8")


#: CloudEvents structured-mode content type (Kafka/AMQP/NATS bindings).
CE_CONTENT_TYPE = "application/cloudevents+json; charset=UTF-8"
