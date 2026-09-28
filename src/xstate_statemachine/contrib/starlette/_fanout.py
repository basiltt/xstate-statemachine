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
from typing import Any, Dict, List, Optional, Set, Tuple

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
        for body in bodies:
            seq = self._seq.get(topic, 0) + 1
            self._seq[topic] = seq
            item = (seq, body)
            for sub in list(self._subs.get(topic, ())):
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
