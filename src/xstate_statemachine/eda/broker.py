# src/xstate_statemachine/eda/broker.py
# -----------------------------------------------------------------------------
# 📡 BrokerAdapter / SyncBrokerAdapter -- the one contract every broker meets
# -----------------------------------------------------------------------------
# 🏛️ Defined ONCE here (#272); the broker adapters of #294 (Kafka, RabbitMQ,
#    NATS, SQS, Redis Streams) implement it, and `tests/eda/contract.py`
#    is the suite every implementation runs. The contract is deliberately
#    small:
#
#      * ``publish(topic, envelope)``;
#      * ``subscribe(topic)`` yields ``Delivery(envelope, ack, nack)``;
#      * ``ack()`` settles a delivery, ``nack(requeue=...)`` returns it to
#        the HEAD of the topic (so it is redelivered before anything
#        published after it) or drops it.
#
#    Ordering is per ``subject`` (the partition key), never global. An
#    un-acked delivery is not redelivered until it is nacked: there is no
#    visibility timeout in the contract (brokers that have one document
#    it). A consumer that nacks one delivery must also nack the later
#    deliveries of the same subject it already holds -- `InboundDispatcher`
#    does -- or per-subject order is lost.
#
#    The sync twin exists for Celery / Django / scripts that do not run an
#    event loop; its `subscribe` returns a plain iterator.
# -----------------------------------------------------------------------------
"""Broker protocols and the `Delivery` handle."""

from __future__ import annotations

import asyncio
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Iterator,
    List,
    NamedTuple,
    Optional,
    Protocol,
    runtime_checkable,
)

from .envelope import Envelope

__all__ = [
    "BrokerAdapter",
    "Delivery",
    "SyncBrokerAdapter",
    "settle_awaitable",
]


class Delivery(NamedTuple):
    """One received envelope plus the callables that settle it.

    ``ack()`` and ``nack(requeue)`` may return an awaitable (async
    adapters) or ``None`` (sync adapters); `InboundDispatcher` handles
    both. Settling twice is a no-op.
    """

    envelope: Envelope
    topic: str
    ack: Callable[[], Any]
    nack: Callable[[bool], Any]


@runtime_checkable
class BrokerAdapter(Protocol):
    """Async broker contract (asyncio)."""

    async def publish(self, topic: str, envelope: Envelope) -> None:
        """Publish *envelope* on *topic*. Raises on failure."""

    def subscribe(
        self, topic: str, *, timeout: Optional[float] = None
    ) -> AsyncIterator[Delivery]:
        """Deliveries from *topic* in per-subject order.

        With *timeout* the iterator ends when nothing arrives for that
        many seconds (``0`` = drain what is ready, then stop).
        """

    async def ack(self, delivery: Delivery) -> None:
        """Protocol member."""

    async def nack(self, delivery: Delivery, *, requeue: bool) -> None:
        """Protocol member."""


@runtime_checkable
class SyncBrokerAdapter(Protocol):
    """Blocking broker contract (threads, Celery, Django)."""

    def publish(self, topic: str, envelope: Envelope) -> None:
        """Protocol member."""

    def subscribe(
        self, topic: str, *, timeout: Optional[float] = None
    ) -> Iterator[Delivery]:
        """Protocol member."""

    def ack(self, delivery: Delivery) -> None:
        """Protocol member."""

    def nack(self, delivery: Delivery, *, requeue: bool) -> None:
        """Protocol member."""


#: Seconds a worker thread waits for a publish scheduled on the loop.
PUBLISH_TIMEOUT_S = 30.0


def settle_awaitable(
    result: Any,
    *,
    loop: Optional[asyncio.AbstractEventLoop] = None,
    tasks: Optional[List[Any]] = None,
) -> None:
    """Run what a maybe-async broker call returned, from any context.

    * ``None`` (sync adapter): nothing to do;
    * on the event loop's own thread: scheduled as a task (appended to
      *tasks* so the caller can await it later);
    * on a worker thread with *loop* running elsewhere: submitted to that
      loop and waited for (`PUBLISH_TIMEOUT_S`);
    * no loop anywhere: run to completion with ``asyncio.run``.
    """
    if not asyncio.iscoroutine(result):
        return
    try:
        running: Optional[asyncio.AbstractEventLoop] = (
            asyncio.get_running_loop()
        )
    except RuntimeError:
        running = None
    if running is not None:
        task = running.create_task(result)
        if tasks is not None:
            tasks.append(task)
    elif loop is not None and loop.is_running():
        asyncio.run_coroutine_threadsafe(result, loop).result(
            PUBLISH_TIMEOUT_S
        )
    else:
        asyncio.run(result)
