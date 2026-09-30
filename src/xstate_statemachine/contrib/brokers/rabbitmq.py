# src/xstate_statemachine/contrib/brokers/rabbitmq.py
# -----------------------------------------------------------------------------
# ðŸ‡ RabbitMQ broker (aio-pika) -- one durable queue per topic (#294)
# -----------------------------------------------------------------------------
# ðŸ›ï¸ The thinnest mapping that keeps the contract:
#
#    * topic = a durable queue of the same name, published through the
#      default exchange (routing key = topic) as PERSISTENT messages with
#      publisher confirms (aio-pika channels confirm by default).
#      Scaling out while keeping per-subject order is the consistent-hash
#      exchange recipe (one queue per consumer, routing key = subject) --
#      pass ``exchange=`` and bind the queues yourself; the adapter then
#      publishes with ``routing_key = subject``.
#    * ``ack`` = basic.ack; ``nack(requeue=False)`` = basic.reject without
#      requeue (dead-lettering is the dispatcher's, X0.8 -- or configure a
#      broker-side DLX, which then sees the reject).
#    * attempts: quorum queues stamp ``x-delivery-count``; classic queues
#      only say ``redelivered`` (counted as 1).
#    * ``prefetch`` bounds un-acked messages per channel (backpressure,
#      X0.8). TLS: an ``amqps://`` URL plus aio-pika's ``ssl_options``
#      through ``connect_kw``; ``repr`` never shows the URL.
# -----------------------------------------------------------------------------
"""`RabbitMQBroker` -- an async `BrokerAdapter` over aio-pika."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from .._compat import require_extra

require_extra("rabbitmq", "aio_pika")

import aio_pika  # noqa: E402

from ...eda.envelope import Envelope  # noqa: E402
from ._base import CE_CONTENT_TYPE, AsyncBroker, Raw, structured  # noqa: E402

__all__ = ["RabbitMQBroker", "RabbitMQTransport"]

_BATCH = 100
_GET_TIMEOUT_S = 5.0


class RabbitMQTransport:
    """The four native operations over one aio-pika channel."""

    def __init__(
        self,
        *,
        url: Optional[str] = None,
        channel: Any = None,
        exchange: Optional[str] = None,
        prefetch: int = _BATCH,
        batch: int = _BATCH,
        max_bytes: int,
        connect_kw: Optional[Dict[str, Any]] = None,
    ) -> None:
        if url is None and channel is None:
            raise ValueError("pass url= or channel=")
        self._url = url
        self._channel = channel
        self.exchange_name = exchange
        self.prefetch = int(prefetch)
        self.batch = int(batch)
        self.max_bytes = max_bytes
        self._connect_kw = dict(connect_kw or {})
        self._connection: Any = None
        self._queues: Dict[str, Any] = {}
        self._exchange: Any = None

    async def _chan(self) -> Any:
        if self._channel is None:
            self._connection = await aio_pika.connect_robust(
                self._url, **self._connect_kw
            )
            self._channel = await self._connection.channel()
            await self._channel.set_qos(prefetch_count=self.prefetch)
        return self._channel

    async def _queue(self, topic: str) -> Any:
        q = self._queues.get(topic)
        if q is None:
            chan = await self._chan()
            q = await chan.declare_queue(topic, durable=True)
            self._queues[topic] = q
        return q

    async def _target(self) -> Any:
        chan = await self._chan()
        if self.exchange_name is None:
            return chan.default_exchange
        if self._exchange is None:
            self._exchange = await chan.get_exchange(self.exchange_name)
        return self._exchange

    # -- operations -------------------------------------------------------------
    async def send(self, topic: str, envelope: Envelope) -> None:
        if self.exchange_name is None:
            await self._queue(topic)  # a publish to no queue is lost
            routing_key = topic
        else:
            routing_key = envelope.subject or ""
        message = aio_pika.Message(
            body=structured(envelope, self.max_bytes),
            content_type=CE_CONTENT_TYPE,
            message_id=envelope.id,
            type=envelope.type,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            headers={"ce_subject": envelope.subject or ""},
        )
        exchange = await self._target()
        await exchange.publish(message, routing_key=routing_key)

    async def fetch(self, topic: str, wait_s: float) -> List[Raw]:
        queue = await self._queue(topic)
        out: List[Raw] = []
        timeout = max(wait_s, 0.001)
        while len(out) < self.batch:
            try:
                msg = await queue.get(
                    no_ack=False,
                    fail=False,
                    timeout=timeout if not out else _GET_TIMEOUT_S,
                )
            except asyncio.TimeoutError:  # the basic.get RPC timed out
                msg = None
            if msg is None:
                break
            out.append(Raw(msg.body, msg, _attempts(msg)))
        return out

    async def ack(self, native: Any) -> None:
        await native.ack()

    async def drop(self, native: Any) -> None:
        await native.reject(requeue=False)

    def rebind(self) -> None:
        """Forget a connection opened on a previous event loop."""
        if self._url is not None:
            self._connection = None
            self._channel = None
            self._exchange = None
            self._queues.clear()

    async def close(self) -> None:
        if self._connection is not None:
            await self._connection.close()
            self._connection = None
            self._channel = None
            self._queues.clear()


def _attempts(msg: Any) -> int:
    headers = getattr(msg, "headers", None) or {}
    count = headers.get("x-delivery-count")
    if isinstance(count, int) and count >= 0:
        return count
    return 1 if getattr(msg, "redelivered", False) else 0


class RabbitMQBroker(AsyncBroker):
    """Async `BrokerAdapter` over RabbitMQ (aio-pika).

    ::

        broker = RabbitMQBroker(url="amqps://user:pw@rabbit/")
        await broker.publish("orders", envelope)

    Args:
        url: AMQP URL (``connect_robust`` reconnects); or
        channel: An open aio-pika channel you manage.
        exchange: Publish through this exchange with ``routing_key =
            subject`` (consistent-hash recipe) instead of the default
            exchange.
        prefetch: Channel QoS (un-acked messages in flight).
        connect_kw: Extra ``connect_robust`` arguments (``ssl_options``).
        max_bytes / on_disconnect / on_reconnect / on_undecodable: See
            `contrib.brokers`.
    """

    def __init__(
        self,
        *,
        url: Optional[str] = None,
        channel: Any = None,
        exchange: Optional[str] = None,
        prefetch: int = _BATCH,
        batch: int = _BATCH,
        connect_kw: Optional[Dict[str, Any]] = None,
        **kw: Any,
    ) -> None:
        super().__init__(None, **kw)
        self.transport = RabbitMQTransport(
            url=url,
            channel=channel,
            exchange=exchange,
            prefetch=prefetch,
            batch=batch,
            max_bytes=self.max_bytes,
            connect_kw=connect_kw,
        )

    def __repr__(self) -> str:
        return f"RabbitMQBroker(exchange={self.transport.exchange_name!r})"
