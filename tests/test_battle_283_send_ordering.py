# tests/test_battle_283_send_ordering.py
"""Battle #283 (adversary A): on a stopped / finished machine the sync
engine runs the `on_before_send` interceptors BEFORE the drop (parity
with the async engine). Pin the edges of that ordering on both engines."""

from __future__ import annotations

import asyncio
from typing import Any, List

import pytest

from xstate_statemachine import (
    Interpreter,
    PluginBase,
    SyncInterpreter,
    create_machine,
)
from xstate_statemachine.persistence.idempotency import (
    IdempotencyPlugin,
    MemoryInbox,
)

CFG = {
    "id": "m",
    "initial": "a",
    "states": {"a": {"on": {"GO": "b"}}, "b": {"type": "final"}},
}


class Spy(PluginBase[Any]):
    def __init__(self, answer: Any = None, boom: bool = False) -> None:
        self.answer, self.boom = answer, boom
        self.seen: List[str] = []
        self.dropped: List[Any] = []
        self.errors: List[str] = []

    def on_before_send(self, interpreter: Any, event: Any) -> Any:
        self.seen.append(event.type)
        if self.boom:
            raise RuntimeError("interceptor exploded")
        return self.answer

    def on_event_dropped(self, interpreter: Any, event: Any, reason: str):
        self.dropped.append((event.type, reason))

    def on_plugin_error(self, *a: Any, **k: Any) -> None:
        self.errors.append("x")


def _done_sync(*plugins: Any) -> SyncInterpreter:
    i = SyncInterpreter(create_machine(CFG))
    for p in plugins:
        i.use(p)
    i.start()
    i.send("GO")
    assert i.status == "done"
    return i


class TestSyncStoppedOrdering:
    def test_raising_interceptor_falls_through_to_the_drop(self) -> None:
        spy = Spy(boom=True)
        i = _done_sync(spy)
        r = i.send("GO", wait=True)
        assert type(r.error).__name__ == "InterpreterStoppedError"
        assert spy.dropped == [("GO", "not_running")]

    def test_non_intercepted_event_still_reports_the_drop(self) -> None:
        spy = Spy()
        i = _done_sync(spy)
        assert i.send("GO") is None  # wait=False
        assert spy.seen[-1] == "GO"
        assert spy.dropped == [("GO", "not_running")]

    def test_intercepted_event_is_not_dropped(self) -> None:
        from xstate_statemachine.receipts import Receipt

        answer = Receipt(frozenset({"m.b"}), False, None, duplicate=True)
        spy = Spy()
        i = _done_sync(spy)
        spy.answer = answer
        assert i.send("GO", wait=True) is answer
        assert i.send("GO") is None  # wait=False: answered, not returned
        assert spy.dropped == []

    def test_malformed_event_skips_interceptors(self) -> None:
        spy = Spy()
        i = _done_sync(spy)
        spy.seen.clear()
        assert i.send({"no": "type"}) is None
        assert spy.seen == []

    def test_send_events_on_stopped_reports_each_drop(self) -> None:
        """🐛 `send_events()` on a finished machine dropped the batch with
        a log line only -- `on_event_dropped` (the #123 audit contract)
        never fired, unlike `send()`."""
        spy = Spy()
        i = _done_sync(spy)
        i.send_events(["GO", {"type": "GO"}])
        assert spy.dropped == [("GO", "not_running")] * 2


@pytest.mark.parametrize("engine", ["sync", "async"])
def test_fresh_key_on_finished_machine_is_released(engine: str) -> None:
    """🐛 The interceptor claimed a NEW key, the engine then dropped the
    event: the claim stayed in flight -> every retry 409 for the TTL."""
    inbox = MemoryInbox()

    def plugin() -> IdempotencyPlugin:
        return IdempotencyPlugin(inbox, principal=lambda e: "u")

    if engine == "sync":
        i = _done_sync(plugin())
        r1 = i.send("GO", idempotency_key="k", wait=True)
        r2 = i.send("GO", idempotency_key="k", wait=True)
    else:

        async def run() -> Any:
            a = Interpreter(create_machine(CFG))
            a.use(plugin())
            await a.start()
            await a.send("GO")
            await asyncio.sleep(0.05)
            x = await a.send("GO", idempotency_key="k", wait=True)
            y = await a.send("GO", idempotency_key="k", wait=True)
            return x, y

        r1, r2 = asyncio.run(run())
    for r in (r1, r2):
        assert type(r.error).__name__ == "InterpreterStoppedError"
        assert r.duplicate is False
    assert inbox.get("u/m/m", "k") is None


def test_async_send_events_on_stopped_reports_each_drop() -> None:
    async def run() -> Spy:
        spy = Spy()
        a = Interpreter(create_machine(CFG))
        a.use(spy)
        await a.start()
        await a.send("GO")
        await asyncio.sleep(0.05)
        await a.send_events(["GO", "GO"])
        return spy

    assert run_spy(run) == [("GO", "not_running")] * 2


def run_spy(fn: Any) -> Any:
    return asyncio.run(fn()).dropped
