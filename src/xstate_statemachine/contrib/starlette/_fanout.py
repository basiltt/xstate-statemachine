# src/xstate_statemachine/contrib/starlette/_fanout.py
# -----------------------------------------------------------------------------
# 📡 In-process transition fan-out for SSE / WebSocket subscribers
# -----------------------------------------------------------------------------
# 🏛️ `act()` notifies this map AFTER its save commits, so a subscriber never
#    sees a transition that a conflict later rolled back. It is strictly
#    per-process: with N workers a client only hears transitions made by
#    the worker it is connected to. Cross-worker fan-out needs a broker
#    (Redis pub/sub, NATS ...) and is out of scope for #275.
# -----------------------------------------------------------------------------
"""`_Subscribers`: per-(name, key) queues with a monotonic sequence."""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

#: Per-subscriber backlog. A consumer that falls this far behind is cut off
#: (it receives the close sentinel) rather than growing memory unbounded.
MAX_BACKLOG = 256
CLOSED = object()

Topic = Tuple[str, str]


class _Subscriber:
    __slots__ = ("queue", "topic")

    def __init__(self, topic: Topic) -> None:
        self.topic = topic
        self.queue: "asyncio.Queue[Any]" = asyncio.Queue(MAX_BACKLOG + 1)


class _Subscribers:
    """Topic → subscribers, plus a per-topic sequence counter."""

    def __init__(self) -> None:
        self._subs: Dict[Topic, Set[_Subscriber]] = {}
        self._seq: Dict[Topic, int] = {}

    def subscribe(self, name: str, key: str) -> _Subscriber:
        sub = _Subscriber((name, key))
        self._subs.setdefault(sub.topic, set()).add(sub)
        return sub

    def unsubscribe(self, sub: _Subscriber) -> None:
        subs = self._subs.get(sub.topic)
        if subs is None:
            return
        subs.discard(sub)
        if not subs:
            del self._subs[sub.topic]
            # 🔥 battle #275: the per-topic `seq` lived forever -- one int
            #    per instance key ever acted on (5 000 orders → 5 000
            #    entries, with or without a subscriber). The sequence is
            #    only meaningful to a connected client; forget it with
            #    the last one. A reconnecting client starts from the
            #    `snapshot` frame anyway.
            self._seq.pop(sub.topic, None)

    def count(
        self, name: Optional[str] = None, key: Optional[str] = None
    ) -> int:
        if name is None:
            return sum(len(s) for s in self._subs.values())
        return len(self._subs.get((name, str(key)), ()))

    def seq(self, name: str, key: str) -> int:
        return self._seq.get((name, key), 0)

    def publish(
        self, name: str, key: str, bodies: List[Dict[str, Any]]
    ) -> None:
        """Stamp each body with the next ``seq`` and enqueue it."""
        topic = (name, key)
        subs = self._subs.get(topic)
        if not subs:
            return  # nobody listening: no sequence to advance, no state
        for body in bodies:
            seq = self._seq.get(topic, 0) + 1
            self._seq[topic] = seq
            item = (seq, body)
            for sub in list(subs):
                if sub.queue.qsize() >= MAX_BACKLOG:
                    # 🔥 Slow consumer: cut it off, never block the writer.
                    self.unsubscribe(sub)
                    sub.queue.put_nowait(CLOSED)
                    continue
                sub.queue.put_nowait(item)

    def close_all(self) -> None:
        for subs in list(self._subs.values()):
            for sub in list(subs):
                with_room = sub.queue.qsize() <= MAX_BACKLOG
                if with_room:
                    sub.queue.put_nowait(CLOSED)
        self._subs.clear()
        self._seq.clear()


class TimerPublisher:
    """Scanner-thread plugin: fan out timer-driven transitions.

    🔥 battle #275: `DueTimerScanner` wakes an expired ``after`` through
    `persisted()` in its own thread, never through `act()` -- so an open
    SSE / WebSocket stream never heard ``awaitingPayment → expired`` and
    showed a stale state until reload. This plugin rides the scanner's
    marker protocol (`flush_marks` runs only AFTER the save committed;
    `discard_marks` on a refused save) and hands the bodies to the loop
    with ``call_soon_threadsafe`` -- `asyncio.Queue` is not thread-safe.
    """

    flush_priority = 100  # after the inbox / outbox marks

    def __init__(
        self,
        subscribers: _Subscribers,
        loop: asyncio.AbstractEventLoop,
        body_of: Callable[[Any, Any, str], Dict[str, Any]],
        sep: str = ".",
    ) -> None:
        self._subs = subscribers
        self._loop = loop
        self._body_of = body_of
        self._sep = sep
        self._pending = threading.local()
        self.buffer_marks = False

    def _buf(self) -> List[Tuple[str, str, Dict[str, Any]]]:
        buf = getattr(self._pending, "items", None)
        if buf is None:
            buf = self._pending.items = []
        return buf

    def on_event_processed(
        self, interpreter: Any, event: Any, receipt: Any
    ) -> None:
        if not getattr(receipt, "changed", False):
            return
        skey = str(getattr(interpreter, "store_key", "") or "")
        name, sep, key = skey.partition(self._sep)
        if not sep:
            return
        try:
            body = self._body_of(interpreter, receipt, name)
        except Exception:  # noqa: BLE001 -- never break the scanner
            logger.exception("📡 timer fan-out body failed for %r", skey)
            return
        self._buf().append((name, key, body))

    def flush_marks(self) -> None:
        items, self._pending.items = self._buf(), []
        for name, key, body in items:
            try:
                self._loop.call_soon_threadsafe(
                    self._subs.publish, name, key, [body]
                )
            except RuntimeError:  # loop closed: nobody left to tell
                return

    def discard_marks(self) -> None:
        self._pending.items = []
