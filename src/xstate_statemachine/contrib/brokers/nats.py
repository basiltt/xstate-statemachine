# src/xstate_statemachine/contrib/brokers/nats.py
# -----------------------------------------------------------------------------
# 🟩 NATS JetStream broker (nats-py) -- subject suffix = partition (#294)
# -----------------------------------------------------------------------------
# 🏛️ Core NATS is at-most-once; the adapter uses JETSTREAM (persisted,
#    acked) only:
#
#    * topic ``orders`` = a stream capturing ``orders.>``; an envelope is
#      published on ``orders.<subject>`` (the subject token sanitised:
#      ``.``, ``*``, ``>`` and whitespace become ``_``). One durable PULL
#      consumer per (topic, durable) reads the whole stream in order, so
#      per-subject order is the stream's order.
#    * ``Nats-Msg-Id`` = ``envelope.id`` -> JetStream's duplicate window
#      drops a re-published outbox row server-side.
#    * ``ack`` = +ACK; ``nack(requeue=False)`` = +TERM (never redelivered;
#      dead-lettering is the dispatcher's, X0.8). attempts = the server's
#      ``num_delivered - 1``.
#    * ``ack_wait`` is JetStream's visibility timeout: a message held
#      longer than that is redelivered (at-least-once; dedup).
#    * TLS / creds: pass nats-py ``connect`` keyword arguments
#      (``tls=``, ``user_credentials=``) via ``connect_kw``; never echoed.
# -----------------------------------------------------------------------------
"""`NatsBroker` -- an async `BrokerAdapter` over NATS JetStream."""

from __future__ import annotations

import asyncio
import re
from typing import Any, Dict, List, Optional

from .._compat import require_extra

require_extra("nats", "nats")

from ...eda.envelope import Envelope  # noqa: E402
from ._base import (
    CE_CONTENT_TYPE,
    AsyncBroker,
    Raw,
    close_stale,
    structured,
)  # noqa: E402

__all__ = ["NatsBroker", "NatsTransport", "subject_token"]

#: M1: small by default (fetched messages wait while ack_wait runs).
_BATCH = 10
_UNSAFE = re.compile(r"[.*>\s]")


def subject_token(subject: Optional[str]) -> str:
    """A NATS-safe single token for an envelope subject."""
    token = _UNSAFE.sub("_", subject or "")
    return token or "_"


class NatsTransport:
    """The four native operations over a JetStream context."""

    def __init__(
        self,
        *,
        servers: Any = None,
        js: Any = None,
        durable: str = "xsm",
        ack_wait_s: float = 30.0,
        batch: int = _BATCH,
        max_bytes: int,
        connect_kw: Optional[Dict[str, Any]] = None,
    ) -> None:
        if servers is None and js is None:
            raise ValueError("pass servers= or js=")
        self._servers = servers
        self._js = js
        self._nc: Any = None
        self.durable = durable
        self.ack_wait_s = float(ack_wait_s)
        self.batch = int(batch)
        self.max_bytes = max_bytes
        self._connect_kw = dict(connect_kw or {})
        self.redelivery_window_s = self.ack_wait_s
        self._streams: Dict[str, Any] = {}
        self._subs: Dict[str, Any] = {}

    async def _jetstream(self) -> Any:
        if self._js is None:
            import nats

            self._nc = await nats.connect(self._servers, **self._connect_kw)
            self._js = self._nc.jetstream()
        return self._js

    async def _stream(self, topic: str) -> Any:
        js = await self._jetstream()
        if topic not in self._streams:
            try:
                await js.add_stream(name=topic, subjects=[f"{topic}.>"])
            except Exception as exc:  # already exists with another config
                if "already" not in str(exc).lower():
                    raise
            self._streams[topic] = True
        return js

    async def _sub(self, topic: str) -> Any:
        sub = self._subs.get(topic)
        if sub is None:
            js = await self._stream(topic)
            from nats.js.api import ConsumerConfig

            sub = await js.pull_subscribe(
                f"{topic}.>",
                durable=self.durable,
                stream=topic,
                config=ConsumerConfig(ack_wait=self.ack_wait_s),
            )
            self._subs[topic] = sub
        return sub

    # -- operations -------------------------------------------------------------
    async def send(self, topic: str, envelope: Envelope) -> None:
        """Publish *envelope* on *topic*; raise on failure."""
        js = await self._stream(topic)
        await js.publish(
            f"{topic}.{subject_token(envelope.subject)}",
            structured(envelope, self.max_bytes),
            headers={
                "Nats-Msg-Id": envelope.id,
                "content-type": CE_CONTENT_TYPE,
            },
        )

    async def fetch(self, topic: str, wait_s: float) -> List[Raw]:
        """Pull what is ready on *topic*, waiting at most *wait_s*."""
        sub = await self._sub(topic)
        try:
            msgs = await sub.fetch(self.batch, timeout=max(wait_s, 0.001))
        except asyncio.TimeoutError:
            return []
        except Exception as exc:  # nats.errors.TimeoutError
            if type(exc).__name__ == "TimeoutError":
                return []
            raise
        return [Raw(m.data, m, _attempts(m)) for m in msgs]

    async def ack(self, native: Any) -> None:
        """Settle a delivery for good."""
        await native.ack()

    async def drop(self, native: Any) -> None:
        """Settle without redelivery."""
        await native.term()

    def rebind(self) -> None:
        """Forget a connection opened on a previous event loop."""
        if self._servers is not None:
            if self._nc is not None:
                close_stale(self._nc.close)
            self._nc = None
            self._js = None
            self._streams.clear()
            self._subs.clear()

    async def close(self) -> None:
        """Release the client connections this object opened."""
        for sub in list(self._subs.values()):
            unsub = getattr(sub, "unsubscribe", None)
            if unsub is not None:
                await unsub()
        self._subs.clear()
        if self._nc is not None:
            await self._nc.drain()
            self._nc = None


def _attempts(msg: Any) -> int:
    try:
        return max(0, int(msg.metadata.num_delivered) - 1)
    except Exception:  # noqa: BLE001 - a non-JetStream message
        return 0


class NatsBroker(AsyncBroker):
    """Async `BrokerAdapter` over NATS JetStream.

    ::

        broker = NatsBroker(servers="nats://nats:4222", durable="orders")
        await broker.publish("orders", envelope)  # on orders.<subject>

    Args:
        servers: NATS URL(s); or
        js: A JetStream context you manage.
        durable: Durable consumer name (one per consumer service).
        ack_wait_s: JetStream redelivery timeout for un-acked messages.
        connect_kw: ``nats.connect`` keyword arguments (TLS, creds).
        max_bytes / on_disconnect / on_reconnect / on_undecodable: See
            `contrib.brokers`.
    """

    CLIENT_HINT = "`connect_kw=` (nats-py options) or `js=`"

    def __init__(
        self,
        *,
        servers: Any = None,
        js: Any = None,
        durable: str = "xsm",
        ack_wait_s: float = 30.0,
        batch: int = _BATCH,
        connect_kw: Optional[Dict[str, Any]] = None,
        **kw: Any,
    ) -> None:
        super().__init__(None, **kw)
        self.transport = NatsTransport(
            servers=servers,
            js=js,
            durable=durable,
            ack_wait_s=ack_wait_s,
            batch=batch,
            max_bytes=self.max_bytes,
            connect_kw=connect_kw,
        )

    def __repr__(self) -> str:
        return f"NatsBroker(durable={self.transport.durable!r})"
