# tests/contrib/celery/test_battle_292_a.py
"""#292 battle, adversary A: the Celery bridge under failure injection,
concurrency and a real worker thread.

Defects pinned here (each test failed before its fix):

* ``@statechart_task`` did not retry `LockTimeoutError` -- under a
  `PessimisticLock` the first contended lock FAILED the task;
* `poll_results` aborted the whole scan when ONE key raised (store blip,
  unknown machine type) -- every later instance starved on every tick;
* `poll_results(pending=...)` dropped every parked completion behind one
  whose delivery raised (`take_all` had already emptied the table);
* `OutboxRelay.relay_once_sync` marked a row SENT when a plain ``def
  publish`` returned an un-awaited coroutine -- a silently lost message;
* every stale / forged `deliver_result` SAVED a no-op version -- 10 000
  forged signals were 10 000 writes and as many `ConflictError`s for
  legitimate writers;
* `register_task` crashed on an ``autofinalize=False`` app.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import threading
import time
import unittest
from typing import Any, List

import pytest

celery = pytest.importorskip("celery")

from src.xstate_statemachine import (  # noqa: E402
    Interpreter,
    MachineLogic,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.contrib.celery import (  # noqa: E402
    MemoryPendingResults,
    PendingResult,
    celery_service,
    deliver_result,
    outbox_relay_task,
    poll_results,
    register_task,
    statechart_task,
)
from src.xstate_statemachine.exceptions import (  # noqa: E402
    LockTimeoutError,
)
from src.xstate_statemachine.persistence import (  # noqa: E402
    MemoryStore,
    PessimisticLock,
    persisted,
)

from .test_celery import (  # noqa: E402
    COUNTER,
    _app,
    _Drops,
    _inc,
    _machine,
    _Result,
    _Task,
    _wait,
    _worker,
)


@contextlib.contextmanager
def _async_result(factory: Any) -> Any:
    """Swap ``celery.result.AsyncResult`` (what `poll_results` reads)."""
    import celery.result as cr

    orig = cr.AsyncResult
    cr.AsyncResult = factory  # type: ignore[misc]
    try:
        yield
    finally:
        cr.AsyncResult = orig  # type: ignore[misc]


def _done(value: Any) -> _Result:
    r = _Result()
    r.value, r.done = value, True
    return r


def _durable(keys: Any) -> Any:
    task = _Task()
    m = _machine(celery_service(task, watch=False))
    store = MemoryStore()
    for k in keys:
        task.result = _Result()  # one task id per instance, as in life
        with persisted(store, k, m):
            pass
    return task, m, store


def _state(store: Any, key: str) -> Any:
    rec = store.load(key)
    assert rec is not None
    return json.loads(rec.snapshot)


# -----------------------------------------------------------------------------
# 🐛 defects
# -----------------------------------------------------------------------------
class TestPollIsolation(unittest.TestCase):
    def test_one_unloadable_key_does_not_stop_the_scan(self) -> None:
        _, m, store = _durable(["a", "bad", "c"])
        orig = store.load

        def load(key: str) -> Any:
            if key == "bad":
                raise OSError("disk")
            return orig(key)

        store.load = load  # type: ignore[method-assign]
        with _async_result(lambda tid, app=None: _done({"v": 1})):
            n = poll_results(store, m, app=_app())
        self.assertEqual(n, 2)
        for k in ("a", "c"):
            self.assertIn("paid", json.dumps(_state(store, k)["value"]))

    def test_one_failing_delivery_does_not_stop_the_scan(self) -> None:
        _, m, store = _durable(["a", "c"])

        def mfk(key: str) -> Any:
            if key == "a":
                raise KeyError("unknown machine type")
            return m

        with _async_result(lambda tid, app=None: _done({"v": 1})):
            self.assertEqual(poll_results(store, mfk, app=_app()), 1)
            # ✅ the failed key is still pending: the next tick retries it
            self.assertEqual(poll_results(store, m, app=_app()), 1)

    def test_parked_completions_survive_a_failing_neighbour(self) -> None:
        task, m, store = _durable(["x", "y"])
        ids = [c[2]["headers"] for c in task.calls]
        self.assertEqual([h["xsm_store_key"] for h in ids], ["x", "y"])
        tx, ty = (_state(store, k)["context"]["_xsm_celery"] for k in "xy")
        pending = MemoryPendingResults()
        pending.add(PendingResult("x", "charge", tx["charge"]["task_id"], 1))
        pending.add(PendingResult("y", "charge", ty["charge"]["task_id"], 2))

        def mfk(key: str) -> Any:
            if key == "x":
                raise RuntimeError("blip")
            return m

        with _async_result(lambda tid, app=None: _Result()):
            n = poll_results(store, mfk, app=_app(), pending=pending)
            self.assertEqual(n, 1)
            self.assertEqual(len(pending), 1)  # x re-parked, not lost
            n = poll_results(store, m, app=_app(), pending=pending)
        self.assertEqual(n, 1)
        self.assertEqual(_state(store, "x")["context"]["result"], 1)


class TestStatechartTaskLock(unittest.TestCase):
    def test_lock_timeout_is_retried_then_surfaces(self) -> None:
        attempts: List[int] = []

        class Busy(MemoryStore):
            @contextlib.contextmanager
            def lock(self, key: str, timeout: Any = None) -> Any:
                attempts.append(1)
                raise LockTimeoutError(key, 0.01)
                yield  # pragma: no cover

        app = _app()
        m = create_machine(COUNTER, logic=MachineLogic(actions={"inc": _inc}))

        @statechart_task(
            app, Busy(), m, lock=PessimisticLock(timeout=0.01), max_retries=2
        )
        def bump(counter: Any) -> None:
            counter.send("INC")

        res = bump.delay("k")
        self.assertEqual(len(attempts), 3)  # 1 + max_retries
        self.assertEqual(res.state, "FAILURE")
        # 📝 the JSON result backend rebuilds it as its `StoreError` base
        self.assertIn("Could not lock", str(res.result))


class TestSyncRelayAwaitable(unittest.TestCase):
    def test_coroutine_from_plain_publish_is_not_marked_sent(self) -> None:
        from src.xstate_statemachine.eda import Envelope, MemoryOutboxStore

        published: List[Any] = []

        class Facade:
            async def _publish(self, topic: str, env: Any) -> None:
                published.append(env)

            def publish(self, topic: str, env: Any) -> Any:
                return self._publish(topic, env)

        outbox = MemoryOutboxStore()
        outbox.add("t", Envelope.new(type="x", subject="s"))
        task = outbox_relay_task(_app(), outbox, Facade(), name="r-facade")
        res = task.apply()
        self.assertEqual(res.state, "FAILURE")
        self.assertIsInstance(res.result, TypeError)
        self.assertEqual(published, [])
        self.assertEqual(len(outbox.pending()), 1)  # ✅ still to send


class TestRegisterTaskNotAutofinalized(unittest.TestCase):
    def test_registers_on_a_lazy_app(self) -> None:
        app = celery.Celery(f"lz{time.monotonic_ns()}", autofinalize=False)

        def lazy_job() -> int:
            return 1

        task = register_task(app, lazy_job, name="lz.job")
        app.finalize()
        self.assertIn("lz.job", app.tasks)
        self.assertEqual(task.name, "lz.job")  # the proxy resolves


# -----------------------------------------------------------------------------
# ✅ looked for, held (pinned so they stay held)
# -----------------------------------------------------------------------------
class TestWorkerConcurrency(unittest.TestCase):
    def test_eight_concurrent_sends_one_key_on_a_real_worker(self) -> None:
        """The issue's acceptance criterion with a REAL worker (8 pool
        threads), not eager mode: every ConflictError is retried."""
        app = _app(eager=False)
        store = MemoryStore()
        m = create_machine(COUNTER, logic=MachineLogic(actions={"inc": _inc}))

        @statechart_task(
            app, store, m, max_retries=100, retry_backoff=False, name="a.inc"
        )
        def bump(counter: Any) -> None:
            counter.send("INC")

        with _worker(app, pool="threads", concurrency=8, shutdown_timeout=10):
            results = [bump.delay("k") for _ in range(8)]
            for r in results:
                r.get(timeout=30, disable_sync_subtasks=False)
        self.assertEqual(_state(store, "k")["context"]["n"], 8)


class TestDurableHeld(unittest.TestCase):
    def test_duplicate_delivery_applies_once(self) -> None:
        task, m, store = _durable(["o1"])
        drops = _Drops()
        tid = task.result.id
        out: List[bool] = []

        def go() -> None:
            out.append(
                deliver_result(
                    store, m, "o1", "charge", tid, result=1, plugins=[drops]
                )
            )

        threads = [threading.Thread(target=go) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(10)
        self.assertEqual(sorted(out), [False, False, False, True])
        self.assertIn("paid", json.dumps(_state(store, "o1")["value"]))

    def test_real_key_wrong_task_id_from_another_machine(self) -> None:
        """A forged header naming a REAL key and an invocation id that a
        DIFFERENT machine type also uses: the task id must match."""
        task, m, store = _durable(["o1"])
        other, m2, store2 = _durable(["o2"])  # another machine's task
        ok = deliver_result(
            store, m, "o1", "charge", other.result.id, result={"x": 1}
        )
        self.assertFalse(ok)
        self.assertIn("paying", json.dumps(_state(store, "o1")["value"]))

    def test_disconnect_is_idempotent_and_other_tasks_ignored(self) -> None:
        from celery.signals import task_success

        from src.xstate_statemachine.contrib.celery import connect_signals

        _, m, store = _durable(["o1"])
        disconnect = connect_signals(store, m, app=_app())

        class Req:
            id = "unrelated"
            is_eager = False
            headers: dict = {}

        class Sender:
            request = Req()

        task_success.send(sender=Sender(), result=1)
        disconnect()
        disconnect()
        self.assertIn("paying", json.dumps(_state(store, "o1")["value"]))

    def test_ten_thousand_stale_deliveries_never_write(self) -> None:
        _, m, store = _durable(["o1"])
        pending = MemoryPendingResults()
        for n in range(10_000):
            deliver_result(store, m, "o1", "charge", f"f{n}", pending=pending)
        self.assertEqual(len(pending), 0)  # recorded -> stale, not parked
        self.assertEqual(store.load("o1").version, 1)  # type: ignore


class TestLiveHeld(unittest.TestCase):
    def test_async_engine_live_completion(self) -> None:
        async def main() -> Any:
            task = _Task()
            i = await Interpreter(
                _machine(celery_service(task, poll_s=0.01))
            ).start()
            task.result.value, task.result.done = {"ok": 1}, True
            for _ in range(300):
                if "o.paid" in i.current_state_ids:
                    break
                await asyncio.sleep(0.01)
            ids = set(i.current_state_ids)
            await i.stop()
            return ids

        self.assertIn("o.paid", asyncio.run(main()))

    def test_watcher_threads_do_not_leak(self) -> None:
        before = threading.active_count()
        for _ in range(500):
            task = _Task()
            i = SyncInterpreter(
                _machine(celery_service(task, poll_s=0.005))
            ).start()
            i.stop()
        _wait(lambda: threading.active_count() <= before + 2, timeout=10)

    def test_backend_raising_on_ready_and_get(self) -> None:
        task = _Task()

        def bad_ready() -> bool:
            raise ConnectionError("backend down")

        task.result.ready = bad_ready  # type: ignore[method-assign]
        i = SyncInterpreter(
            _machine(celery_service(task, poll_s=0.01, timeout_s=0.1))
        ).start()
        _wait(lambda: "o.failed" in i.current_state_ids, i)
        self.assertEqual(i.context["error"], "TimeoutError")
        i.stop()
        task2 = _Task()
        task2.result.done = True
        task2.result.get = lambda **kw: (_ for _ in ()).throw(  # type: ignore
            ConnectionError("down")
        )
        i2 = SyncInterpreter(_machine(celery_service(task2))).start()
        self.assertIn("o.failed", i2.current_state_ids)  # eager path
        i2.stop()
