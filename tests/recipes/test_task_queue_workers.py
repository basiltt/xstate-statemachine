# tests/recipes/test_task_queue_workers.py
"""RQ / arq / Dramatiq recipe: fake queues that call the job function,
plus the optimistic retry on `ConflictError`."""

from __future__ import annotations

import asyncio
import json
import threading
from pathlib import Path
from typing import Any, Callable, List, Tuple

import pytest

from .conftest import load_recipe

qw = load_recipe("task_queue_workers", "queue_workers")


class FakeQueue:
    """Stands in for RQ's `Queue`, arq's pool and a Dramatiq actor: it
    records enqueued jobs and runs them when `work()` is called."""

    def __init__(self) -> None:
        self.jobs: List[Tuple[Callable, tuple]] = []

    def enqueue(self, fn: Callable, *args: Any) -> None:  # RQ shape
        self.jobs.append((fn, args))

    def work(self) -> List[Any]:
        out = []
        while self.jobs:
            fn, args = self.jobs.pop(0)
            res = fn(*args)
            if asyncio.iscoroutine(res):
                res = asyncio.run(res)
            out.append(res)
        return out


@pytest.fixture
def store(tmp_path: Path) -> Any:
    from xstate_statemachine.persistence import SQLiteStore

    s = SQLiteStore(tmp_path / "q.db")
    qw.configure(s)
    yield s
    s.close()


def _value(store: Any, key: str = "shipment.42") -> Any:
    return json.loads(store.load(key).snapshot)


FLOW = ["LABEL_PRINTED", "PICKED_UP", "SCANNED", "SCANNED", "DELIVERED"]


def test_rq_style(store: Any) -> None:
    q = FakeQueue()
    for ev in FLOW:
        q.enqueue(qw.rq_job, "shipment.42", ev)
    results = q.work()
    assert results[-1] == {"state": "delivered", "changed": True}
    assert _value(store)["context"]["scans"] == 2


def test_arq_style(store: Any) -> None:
    q = FakeQueue()
    for ev in FLOW:
        q.enqueue(qw.arq_job, {"redis": None}, "shipment.42", ev)
    assert q.work()[-1]["state"] == "delivered"


def test_dramatiq_style(store: Any) -> None:
    q = FakeQueue()  # `actor.send(...)` -> the worker calls the function
    for ev in FLOW:
        q.enqueue(qw.dramatiq_job, "shipment.42", ev)
    assert q.work() == [None] * len(FLOW)
    assert _value(store)["value"] == "delivered"


class RacingStore:
    """Proxy whose Nth load is followed by a competing write -- the save of
    whoever loaded first then raises `ConflictError`."""

    def __init__(self, inner: Any, races: int) -> None:
        self.inner, self.races = inner, races

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)

    def load(self, key: str) -> Any:
        rec = self.inner.load(key)
        if self.races and rec is not None:
            self.races -= 1
            from xstate_statemachine.persistence import persisted

            with persisted(self.inner, key, qw.MACHINE) as other:
                other.send("SCANNED")
        return rec


@pytest.mark.parametrize("job", ["sync", "async"])
def test_conflict_is_retried_and_nothing_is_lost(store: Any, job: str) -> None:
    for ev in ("LABEL_PRINTED", "PICKED_UP"):
        qw.apply_event("shipment.42", ev)
    qw.configure(RacingStore(store, races=2), qw.MACHINE)
    if job == "sync":
        qw.apply_event("shipment.42", "SCANNED")
    else:
        asyncio.run(qw.apply_event_async("shipment.42", "SCANNED"))
    # two competing scans + ours: all three counted, none overwritten
    assert _value(store)["context"]["scans"] == 3


def test_conflict_gives_up_after_retries(store: Any) -> None:
    from xstate_statemachine.persistence import ConflictError

    for ev in ("LABEL_PRINTED", "PICKED_UP"):
        qw.apply_event("shipment.42", ev)
    qw.configure(RacingStore(store, races=99), qw.MACHINE)
    with pytest.raises(ConflictError):
        qw.apply_event("shipment.42", "SCANNED")


def test_threads_racing_one_key_lose_no_update(store: Any) -> None:
    for ev in ("LABEL_PRINTED", "PICKED_UP"):
        qw.apply_event("shipment.42", ev)
    qw.RETRIES, old = 50, qw.RETRIES
    try:
        ts = [
            threading.Thread(
                target=qw.apply_event, args=("shipment.42", "SCANNED")
            )
            for _ in range(8)
        ]
        [t.start() for t in ts]
        [t.join() for t in ts]
    finally:
        qw.RETRIES = old
    assert _value(store)["context"]["scans"] == 8


def test_dramatiq_actor_is_soft() -> None:
    import importlib.util

    if importlib.util.find_spec("dramatiq") is None:
        with pytest.raises(ImportError):
            qw.dramatiq_actor()
    else:  # pragma: no cover - dramatiq installed
        assert callable(qw.dramatiq_actor().send)
