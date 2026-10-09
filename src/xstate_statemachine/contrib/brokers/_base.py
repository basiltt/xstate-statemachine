# src/xstate_statemachine/contrib/brokers/_base.py
# -----------------------------------------------------------------------------
# 🧱 The shared adapter skeleton: one bookkeeping core, thin transports (#294)
# -----------------------------------------------------------------------------
# 🏛️ Every broker adapter is `SyncBroker` / `AsyncBroker` + a *transport*
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
import inspect
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
        "🔥 dropping undecodable message on %r: %s: %s",
        topic,
        type(exc).__name__,
        exc,
    )


def _native_attempts(value: Any) -> int:
    """A transport's redelivery count, coerced: ``None`` / negative /
    non-numeric (a buggy or hostile transport) count as a first delivery
    instead of raising mid-batch and stranding everything fetched."""
    if isinstance(value, bool):
        return int(value)
    try:
        return max(0, int(value))
    except (TypeError, ValueError, OverflowError):
        return 0


def _notify(callback: Optional[Callable[..., Any]], *args: Any) -> None:
    """Run a health callback; a raising one is logged, never propagated
    (it fired AFTER a fetch succeeded: raising there lost the batch, and
    on failure it masked the transport's own exception)."""
    if callback is None:
        return
    try:
        callback(*args)
    except Exception:  # noqa: BLE001 - user hook
        logger.warning("🔥 broker health callback failed", exc_info=True)


class _Core:
    """Thread-safe local state shared by the sync and async bases."""

    #: Where this adapter takes its client's own options (named in the
    #: unknown-option error); subclasses override.
    CLIENT_HINT = "the client object you pass in (`client=`)"

    def __init__(
        self,
        *,
        max_bytes: int = DEFAULT_MAX_SNAPSHOT_BYTES,
        on_disconnect: Optional[Callable[[Exception], Any]] = None,
        on_reconnect: Optional[Callable[[], Any]] = None,
        on_undecodable: Optional[Callable[[str, Raw, Exception], Any]] = None,
        dead_letters: Optional[Any] = None,
        **unknown: Any,
    ) -> None:
        if unknown:
            # 💡 #294 review (B): `KafkaBroker(sasl_plain_password=...)`
            #    died with `TypeError: _Core.__init__()` -- name the
            #    option and where client options go.
            names = ", ".join(sorted(unknown))
            raise TypeError(
                f"unknown broker option(s): {names}. Client options "
                f"(TLS, SASL, credentials) go in {self.CLIENT_HINT}; the "
                "adapter's own options are max_bytes, on_disconnect, "
                "on_reconnect, on_undecodable, dead_letters."
            )
        self.max_bytes = int(max_bytes)
        self.on_disconnect = on_disconnect
        self.on_reconnect = on_reconnect
        self.on_undecodable = on_undecodable or default_on_undecodable
        #: X0.8: a DeadLetterStore; undecodable / oversized messages are
        #: recorded here (reason ``"corrupt"``) before being dropped.
        self.dead_letters = dead_letters
        self._lock = threading.Lock()
        #: topic -> deque of (envelope, native, fetched_at monotonic)
        self._local: Dict[str, Deque[Tuple[Envelope, Any, float]]] = {}
        self._inflight: Dict[int, Tuple[Delivery, Any, float]] = {}
        self._healthy = True

    # -- health ---------------------------------------------------------------
    @property
    def healthy(self) -> bool:
        """``False`` after a transport call failed, until one succeeds."""
        return self._healthy

    def _io_ok(self) -> None:
        with self._lock:
            flipped, self._healthy = not self._healthy, True
        if flipped:
            logger.info("✅ broker connection healthy again")
            _notify(self.on_reconnect)

    def _io_failed(self, exc: Exception) -> None:
        with self._lock:
            flipped, self._healthy = self._healthy, False
        if flipped:
            # 🔐 type only: client errors may embed URLs with credentials
            logger.warning("🔥 broker call failed: %s", type(exc).__name__)
            _notify(self.on_disconnect, exc)

    # -- local queue ----------------------------------------------------------
    def _hold_s(self) -> Optional[float]:
        """How long a fetched message may wait locally (M1): half the
        transport's redelivery window (ack_wait / visibility timeout /
        min_idle_ms). ``None`` / ``0`` = never released (no clock, or a
        zero window -- a degenerate configuration)."""
        window = getattr(self._transport_obj(), "redelivery_window_s", None)
        return None if window is None else float(window) / 2.0

    def _transport_obj(self) -> Any:
        t = getattr(self, "transport", None)
        return getattr(t, "inner", t)

    def _pop(self, topic: str) -> Optional[Tuple[Envelope, Any, float]]:
        """Next local entry. Entries held past `_hold_s` are RELEASED:
        forgotten locally without a native ack, so the broker redelivers
        them on its own clock -- never delivered here too late (which
        would inflate attempts and dead-letter healthy messages)."""
        hold = self._hold_s()
        released: List[Any] = []
        item = None
        with self._lock:
            q = self._local.get(topic)
            while q:
                env, native, at = q.popleft()
                if hold and time.monotonic() - at > hold:
                    released.append(native)
                    continue
                item = (env, native, at)
                break
        forget = getattr(self._transport_obj(), "forget", None)
        for native in released:
            logger.debug("released a locally expired message on %r", topic)
            if forget is not None:
                forget(native)
        return item

    def _decode_one(self, topic: str, raw: Raw) -> Optional[Envelope]:
        """One fetched message -> envelope, or ``None`` if undecodable.

        🔐 battle #294-a: the attempt is the BROKER's count only. The
        wire ``xsmattempt`` is producer-controlled (a forged ``10**9``
        dead-lettered a healthy message on its first transient failure,
        and a re-published envelope carried a stale count); local
        requeues and the dispatcher's own counter cover the rest.
        """
        try:
            env = Envelope.from_json(raw.body, max_bytes=self.max_bytes)
        except EnvelopeCorruptError as exc:
            # 💡 the DLQ record and the user hook are best-effort: a
            #    failure in either must not lose the rest of the batch
            for report in (self._dead_letter_raw, self.on_undecodable):
                try:
                    report(topic, raw, exc)
                except Exception:  # noqa: BLE001
                    logger.warning(
                        "🔥 reporting an undecodable message on %r failed",
                        topic,
                        exc_info=True,
                    )
            return None
        n = _native_attempts(raw.attempts)
        return env if env.attempt == n else env.with_attempt(n)

    def _stash_decoded(self, topic: str, raws: List[Raw]) -> List[Any]:
        """Stash every decodable message FIRST; return the natives of the
        undecodable ones for the caller to drop. A drop (or a user
        ``on_undecodable``) that raises must never strand good messages
        that the transport already marked as fetched."""
        good: List[Tuple[Envelope, Any]] = []
        bad: List[Any] = []
        try:
            for raw in raws:
                env = self._decode_one(topic, raw)
                if env is None:
                    bad.append(raw.native)
                else:
                    good.append((env, raw.native))
        finally:
            self._stash(topic, good)
        return bad

    def _dead_letter_raw(self, topic: str, raw: Raw, exc: Exception) -> None:
        """X0.8: record an undecodable message (body NOT stored -- it
        may be hostile or sensitive; size and error only)."""
        if self.dead_letters is None:
            return
        from ...patterns.dead_letter import DeadLetter

        body = raw.body
        size = len(body) if isinstance(body, (bytes, bytearray, str)) else 0
        record = DeadLetter(
            machine_id="?",
            state_id="",
            event={"type": "", "payload": {"bytes": size}},
            attempts=raw.attempts + 1,
            errors=[
                {
                    "source": "broker",
                    "name": "corrupt",
                    "type": type(exc).__name__,
                    "message": str(exc)[:200],
                }
            ],
            snapshot={},
            taken_at=time.time(),
            reason="corrupt",
            topic=topic,
        )
        put = getattr(self.dead_letters, "put", None) or self.dead_letters
        put(record)

    def _stash(self, topic: str, items: List[Tuple[Envelope, Any]]) -> None:
        now = time.monotonic()
        with self._lock:
            self._local.setdefault(topic, deque()).extend(
                (env, native, now) for env, native in items
            )

    def _deliver(
        self, topic: str, env: Envelope, native: Any, at: float
    ) -> Delivery:
        box: List[Delivery] = []

        def ack() -> Any:
            """Settle a delivery for good."""
            return self.ack(box[0])

        def nack(requeue: bool = True) -> Any:
            """Requeue locally (``requeue=True``) or settle without redelivery."""
            return self.nack(box[0], requeue=requeue)

        d = Delivery(env, topic, ack, nack)
        box.append(d)
        with self._lock:
            self._inflight[id(d)] = (d, native, at)
        return d

    def _claim(self, delivery: Delivery) -> Tuple[bool, Any, float]:
        """``(claimed, native, fetched_at)``; claimed once only."""
        with self._lock:
            entry = self._inflight.pop(id(delivery), None)
        if entry is None:
            return False, None, 0.0
        return True, entry[1], entry[2]

    def _requeue(self, delivery: Delivery, native: Any, at: float) -> None:
        env = delivery.envelope
        env = env.with_attempt(env.attempt + 1)
        with self._lock:
            self._local.setdefault(delivery.topic, deque()).appendleft(
                (env, native, at)
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
        """Settle a delivery for good."""
        raise NotImplementedError

    def nack(
        self, delivery: Delivery, *, requeue: bool
    ) -> Any:  # pragma: no cover
        """Requeue locally (``requeue=True``) or settle without redelivery."""
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
        """Publish *envelope* on *topic* (raises if the broker refuses)."""
        if not isinstance(envelope, Envelope):
            raise TypeError("publish() needs an Envelope")
        self._call(self.transport.send, topic, envelope)

    def subscribe(
        self, topic: str, *, timeout: Optional[float] = None
    ) -> Iterator[Delivery]:
        """Yield deliveries on *topic*; end after *timeout* idle seconds."""
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
            bad = self._stash_decoded(topic, raws)
            for native in bad:  # after stashing: a failing drop loses none
                self._call(self.transport.drop, native)
            if raws and timeout is not None:
                # the protocol: end once NOTHING arrived for `timeout`
                # (a draining consumer must not stop mid-backlog)
                deadline = _deadline(timeout)

    def ack(self, delivery: Delivery) -> None:
        """Settle a delivery for good."""
        claimed, native, at = self._claim(delivery)
        if claimed:
            self._call(self.transport.ack, native)

    def nack(self, delivery: Delivery, *, requeue: bool) -> None:
        """Requeue locally (``requeue=True``) or settle without redelivery."""
        claimed, native, at = self._claim(delivery)
        if not claimed:
            return
        if requeue:
            self._requeue(delivery, native, at)
        else:
            self._call(self.transport.drop, native)

    def close(self) -> None:
        """Release the client connections this object opened."""
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
            # 📝 The old loop is closed (asyncio.run returned), so its
            #    sockets cannot be closed gracefully from here: the broker
            #    notices the dead connection and redelivers what it held
            #    un-acked (AMQP / JetStream at once, a Kafka group member
            #    after its session timeout). Long-lived services should
            #    keep ONE loop per adapter and call `close()` on shutdown.
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
        """Publish *envelope* on *topic* (raises if the broker refuses)."""
        if not isinstance(envelope, Envelope):
            raise TypeError("publish() needs an Envelope")
        self._check_loop()
        await self._call(self.transport.send, topic, envelope)

    async def subscribe(
        self, topic: str, *, timeout: Optional[float] = None
    ) -> AsyncIterator[Delivery]:
        """Yield deliveries on *topic*; end after *timeout* idle seconds."""
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
            bad = self._stash_decoded(topic, raws)
            for native in bad:  # after stashing: a failing drop loses none
                await self._call(self.transport.drop, native)
            if raws and timeout is not None:
                # the protocol: end once NOTHING arrived for `timeout`
                # (a draining consumer must not stop mid-backlog)
                deadline = _deadline(timeout)

    async def ack(self, delivery: Delivery) -> None:
        """Settle a delivery for good."""
        self._check_loop()
        claimed, native, at = self._claim(delivery)
        if claimed:
            await self._call(self.transport.ack, native)

    async def nack(self, delivery: Delivery, *, requeue: bool) -> None:
        """Requeue locally (``requeue=True``) or settle without redelivery."""
        self._check_loop()
        claimed, native, at = self._claim(delivery)
        if not claimed:
            return
        if requeue:
            self._requeue(delivery, native, at)
        else:
            await self._call(self.transport.drop, native)

    async def close(self) -> None:
        """Release the client connections this object opened."""
        close = getattr(self.transport, "close", None)
        if close is not None:
            result = close()
            if asyncio.iscoroutine(result):
                await result


def close_stale(*closers: Any) -> None:
    """Best-effort close of clients opened on a loop that is gone (H2).

    Each *closer* is a zero-argument callable returning an awaitable (or
    ``None``). They run on a PRIVATE short-lived loop in a helper thread,
    bounded by `STALE_CLOSE_S`; any error is logged at debug and ignored
    -- the goal is to release sockets, not to be graceful.
    """
    todo = [c for c in closers if c is not None]
    if not todo:
        return

    async def run_all() -> None:
        for closer in todo:
            try:
                res = closer()
                if inspect.isawaitable(res):
                    await asyncio.wait_for(res, STALE_CLOSE_S)
            except Exception:  # noqa: BLE001 - best effort by contract
                logger.debug("closing a stale client failed", exc_info=True)

    def target() -> None:
        try:
            asyncio.run(run_all())
        except Exception:  # noqa: BLE001
            logger.debug("stale-client close loop failed", exc_info=True)

    t = threading.Thread(target=target, name="xsm-close-stale", daemon=True)
    t.start()
    t.join(STALE_CLOSE_S * (len(todo) + 1))


#: Seconds allowed per stale client close.
STALE_CLOSE_S = 2.0


class ThreadedTransport:
    """Run a blocking transport's calls on a worker thread (async view).

    Used where the client library is synchronous (boto3) or where one
    thread-safe connection pool should back both engines (redis-py).
    """

    def __init__(self, inner: Any) -> None:
        self.inner = inner

    async def send(self, topic: str, envelope: Envelope) -> None:
        """Publish *envelope* on *topic*; raise on failure."""
        await asyncio.get_running_loop().run_in_executor(
            None, self.inner.send, topic, envelope
        )

    async def fetch(self, topic: str, wait_s: float) -> List[Raw]:
        """Pull what is ready on *topic*, waiting at most *wait_s*."""
        return await asyncio.get_running_loop().run_in_executor(
            None, self.inner.fetch, topic, wait_s
        )

    async def ack(self, native: Any) -> None:
        """Settle a delivery for good."""
        await asyncio.get_running_loop().run_in_executor(
            None, self.inner.ack, native
        )

    async def drop(self, native: Any) -> None:
        """Settle without redelivery."""
        await asyncio.get_running_loop().run_in_executor(
            None, self.inner.drop, native
        )

    def close(self) -> None:
        """Release the client connections this object opened."""
        close = getattr(self.inner, "close", None)
        if close is not None:
            close()


def structured(envelope: Envelope, max_bytes: int) -> bytes:
    """The structured-mode body every adapter publishes (size-capped)."""
    return envelope.to_json(max_bytes=max_bytes).encode("utf-8")


#: CloudEvents structured-mode content type (Kafka/AMQP/NATS bindings).
CE_CONTENT_TYPE = "application/cloudevents+json; charset=UTF-8"
