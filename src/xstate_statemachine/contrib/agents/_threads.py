# src/xstate_statemachine/contrib/agents/_threads.py
# -----------------------------------------------------------------------------
# 🧵 Run a blocking model call on a daemon thread the loop can abandon (#287)
# -----------------------------------------------------------------------------
"""`_in_daemon_thread` -- NOT the loop's default executor (review H1): a
hung provider call would pin one of its few workers, and `asyncio.run`
waits for that pool on exit -- the very hang `model_timeout_s` removes."""

from __future__ import annotations

import asyncio
import threading
from typing import Any

__all__ = ["_in_daemon_thread"]


async def _in_daemon_thread(fn: Any, *args: Any) -> Any:
    """Run ``fn(*args)`` on a daemon thread; the awaiting task may be
    cancelled (timeout) and the thread is then abandoned, never joined."""
    loop = asyncio.get_running_loop()
    fut: "asyncio.Future[Any]" = loop.create_future()

    def _run() -> None:
        try:
            value = fn(*args)
        except BaseException as exc:  # noqa: BLE001 -- forwarded
            loop.call_soon_threadsafe(_settle, fut, None, exc)
            return
        loop.call_soon_threadsafe(_settle, fut, value, None)

    threading.Thread(target=_run, name="xsm-model-call", daemon=True).start()
    return await fut


def _settle(fut: Any, value: Any, exc: Any) -> None:
    if fut.done():  # the awaiting task was cancelled (timeout)
        return
    if exc is not None:
        fut.set_exception(exc)
    else:
        fut.set_result(value)
