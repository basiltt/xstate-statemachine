# src/xstate_statemachine/inspect/replay.py
# -----------------------------------------------------------------------------
# ⏪ replay_messages -- stream a JSON Lines recording into any sink
# -----------------------------------------------------------------------------
"""Replay a recorded inspector session."""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, Iterable, Optional, Union

from .protocol import MESSAGE_TYPES
from .sinks import read_jsonl

__all__ = ["replay_messages"]


def replay_messages(
    source: Union[str, Iterable[Dict[str, Any]]],
    sink: Any,
    *,
    speed: float = 0.0,
    sleep: Optional[Callable[[float], None]] = None,
) -> int:
    """Send every protocol message from *source* to *sink*.

    Args:
        source: A `.jsonl` path or an iterable of message dicts.
        sink: Anything with ``send(dict)`` (or a callable).
        speed: ``0`` (default) sends as fast as possible; ``1.0`` honours
            the recorded ``createdAt`` gaps; ``2.0`` is twice as fast.
        sleep: Injected ``time.sleep`` (tests).

    Returns:
        The number of messages sent. Lines that are not protocol messages
        are skipped, never forwarded.
    """
    send = sink.send if hasattr(sink, "send") else sink
    doze = sleep or time.sleep
    messages = read_jsonl(source) if isinstance(source, str) else source
    sent = 0
    last: Optional[int] = None
    for msg in messages:
        if msg.get("type") not in MESSAGE_TYPES:
            continue
        if speed > 0:
            try:
                at = int(msg.get("createdAt", 0))
            except (TypeError, ValueError):
                at = None
            if at is not None and last is not None and at > last:
                doze((at - last) / 1000.0 / speed)
            if at is not None:
                last = at
        send(msg)
        sent += 1
    return sent
