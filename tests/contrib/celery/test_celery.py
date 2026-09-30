# tests/contrib/celery/test_celery.py
"""#292: `[celery]` -- Celery in ``task_always_eager`` mode with an
in-memory result backend (no broker), plus a real in-process worker
thread (``memory://`` broker, ``cache+memory://`` backend) and a
``CELERY_BROKER_URL``-gated live test.

Covers: `celery_service` eager (inline onDone / onError, the issue's
snippet), live watcher (onDone, onError, timeout, revoke on exit, no
revoke on stop), durable delivery through signals and `poll_results`
with the stale-completion guard; `@statechart_task` (JSON-only, 8 threads
x 100 sends on one key without lost updates); `DurableTimerScheduler`
scan + ``eta`` generation check + idempotent double fire on a
`SimulatedClock`; `outbox_relay_task`."""

from __future__ import annotations

import json
import os
import threading
import time
import unittest
from typing import Any, List

import pytest

from src.xstate_statemachine import (
    MachineLogic,
    PluginBase,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.exceptions import InvalidConfigError
from src.xstate_statemachine.persistence import MemoryStore, persisted

from ..conftest import requires_extra

pytestmark = requires_extra("celery")
celery = pytest.importorskip("celery")


def _app(eager: bool = True) -> Any:
    app = celery.Celery(
        f"t{time.monotonic_ns()}",
        broker="memory://",
        backend="cache+memory://",
    )
    app.conf.task_always_eager = eager
    app.conf.task_store_eager_result = True
    return app


PAY = {
    "id": "o",
    "initial": "paying",
    "context": {},
    "states": {
        "paying": {
            "invoke": {
                "id": "charge",
                "src": "charge",
                "onDone": {"target": "paid", "actions": "keep"},
                "onError": {"target": "failed", "actions": "err"},
            },
            "on": {"CANCEL": "cancelled"},
        },
        "paid": {"type": "final"},
        "failed": {},
        "cancelled": {},
    },
}


def _keep(i: Any, ctx: Any, e: Any, a: Any) -> None:
    ctx["result"] = e.data


def _err(i: Any, ctx: Any, e: Any, a: Any) -> None:
    ctx["error"] = type(getattr(e, "error", None)).__name__


def _machine(service: Any) -> Any:
    return create_machine(
        PAY,
        logic=MachineLogic(
            services={"charge": service},
            actions={"keep": _keep, "err": _err},
        ),
    )


def _wait(pred: Any, interp: Any = None, timeout: float = 5.0) -> None:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if interp is not None:
            interp.tick()
        if pred():
            return
        time.sleep(0.01)
    raise AssertionError("condition not met")


class _Result:
    """A controllable AsyncResult stand-in for the live watcher."""

    def __init__(self) -> None:
        self.id = f"task-{time.monotonic_ns()}"
        self.value: Any = None
        self.error: Any = None
        self.done = False
        self.revoked = False

    def ready(self) -> bool:
        return self.done

    def get(self, propagate: bool = True, **kw: Any) -> Any:
        if self.error is not None:
            raise self.error
        return self.value

    def revoke(self, terminate: bool = False) -> None:
        self.revoked = True


class _Task:
    name = "fake.task"

    def __init__(self) -> None:
        self.calls: List[Any] = []
        self.result = _Result()

    def apply_async(self, args: Any, kwargs: Any, **opts: Any) -> _Result:
        self.calls.append((args, kwargs, opts))
        return self.result


# -----------------------------------------------------------------------------
class TestEager(unittest.TestCase):
    def test_issue_snippet_on_done_persisted(self) -> None:
        from src.xstate_statemachine.contrib.celery import celery_service

        app = _app()

        @app.task
        def charge(amount: int) -> dict:
            return {"ok": True, "amount": amount}

        m = _machine(
            celery_service(charge, args_from=lambda c, e: ((42,), {}))
        )
        store = MemoryStore()
        with persisted(store, "o1", m):
            pass
        with persisted(store, "o1", m) as i:
            self.assertIn("o.paid", i.current_state_ids)
            self.assertEqual(i.context["result"], {"ok": True, "amount": 42})

    def test_task_failure_is_on_error(self) -> None:
        from src.xstate_statemachine.contrib.celery import celery_service

        app = _app()

        @app.task
        def charge() -> None:
            raise ValueError("declined")

        i = SyncInterpreter(_machine(celery_service(charge))).start()
        self.assertIn("o.failed", i.current_state_ids)
        self.assertEqual(i.context["error"], "ValueError")
        i.stop()


class TestLiveWatcher(unittest.TestCase):
    def _run(self, **kw: Any) -> Any:
        from src.xstate_statemachine.contrib.celery import celery_service

        task = _Task()
        svc = celery_service(
            task, args_from=lambda c, e: ((1,), {"x": 2}), poll_s=0.01, **kw
        )
        return task, SyncInterpreter(_machine(svc)).start()

    def test_done_arrives_via_engine_path_and_headers_are_set(self) -> None:
        task, i = self._run(queue="payments")
        args, kwargs, opts = task.calls[0]
        self.assertEqual((args, kwargs), ((1,), {"x": 2}))
        self.assertEqual(opts["queue"], "payments")
        self.assertEqual(opts["headers"]["xsm_invocation_id"], "charge")
        self.assertNotIn("xsm_state_seq", opts["headers"])  # never checked
        self.assertEqual(
            i.context["_xsm_celery"]["charge"]["task_id"], task.result.id
        )
        # a forged completion is refused by the engine
        i.send("done.invoke.charge", data={"forged": True})
        self.assertIn("o.paying", i.current_state_ids)
        task.result.value, task.result.done = {"ok": 1}, True
        _wait(lambda: "o.paid" in i.current_state_ids, i)
        self.assertEqual(i.context["result"], {"ok": 1})
        i.stop()

    def test_failure_is_on_error(self) -> None:
        task, i = self._run()
        task.result.error, task.result.done = KeyError("x"), True
        _wait(lambda: "o.failed" in i.current_state_ids, i)
        self.assertEqual(i.context["error"], "KeyError")
        i.stop()

    def test_timeout_is_on_error_and_revokes(self) -> None:
        task, i = self._run(timeout_s=0.05)
        _wait(lambda: "o.failed" in i.current_state_ids, i)
        self.assertEqual(i.context["error"], "TimeoutError")
        self.assertTrue(task.result.revoked)
        i.stop()

    def test_state_exit_revokes_but_stop_does_not(self) -> None:
        task, i = self._run()
        i.send("CANCEL")
        self.assertTrue(task.result.revoked)
        i.stop()
        task2, i2 = self._run()
        i2.stop()
        self.assertFalse(task2.result.revoked)

    def test_race_exit_reenter_between_post_and_drain(self) -> None:
        """M4 (deterministic): the post lands while an exit+re-entry has
        replaced the handle under the same invocation id."""
        from src.xstate_statemachine.contrib.celery import service as svc

        task, i = self._run()
        live_old = next(
            p.wrapped if hasattr(p, "wrapped") else p
            for p in i._plugins
            if type(getattr(p, "wrapped", p)).__name__ == "_LiveGuard"
        )
        inv = [v for s in i._active_state_nodes for v in s.invoke][0]
        stale = svc._Live(inv, task.result, handle=object())  # not current
        event = svc._engine_done(
            type="done.invoke.charge", data={"stale": 1}, src="charge"
        )
        live_old.post(i, stale, event)
        i.tick()
        self.assertIn("o.paying", i.current_state_ids)
        self.assertIn("charge", i.context["_xsm_celery"])  # untouched
        i.stop()

    def test_settled_task_is_not_revoked(self) -> None:
        """M6: a successful live completion must not revoke its task."""
        task, i = self._run()
        task.result.value, task.result.done = {"ok": 1}, True
        _wait(lambda: "o.paid" in i.current_state_ids, i)
        self.assertFalse(task.result.revoked)
        i.stop()

    def test_live_completion_retires_the_durable_record(self) -> None:
        task, i = self._run()
        task.result.value, task.result.done = {"ok": 1}, True
        _wait(lambda: "o.paid" in i.current_state_ids, i)
        self.assertEqual(i.context["_xsm_celery"], {})
        i.stop()

    def test_revoke_failure_is_swallowed(self) -> None:
        task, i = self._run()

        def boom(terminate: bool = False) -> None:
            raise RuntimeError("backend down")

        task.result.revoke = boom  # type: ignore[method-assign]
        i.send("CANCEL")
        self.assertIn("o.cancelled", i.current_state_ids)
        i.stop()


class _Drops(PluginBase):
    def __init__(self) -> None:
        self.drops: List[str] = []

    def on_event_dropped(self, interpreter: Any, event: Any, reason: str):
        self.drops.append(reason)


class TestDurableDelivery(unittest.TestCase):
    def setUp(self) -> None:
        from src.xstate_statemachine.contrib.celery import celery_service

        self.task = _Task()
        self.m = _machine(celery_service(self.task, watch=False))
        self.store = MemoryStore()
        with persisted(self.store, "o1", self.m):
            pass

    def test_deliver_result_completes_and_persists(self) -> None:
        from src.xstate_statemachine.contrib.celery import deliver_result

        headers = self.task.calls[0][2]["headers"]
        self.assertEqual(headers["xsm_store_key"], "o1")
        ok = deliver_result(
            self.store,
            self.m,
            "o1",
            "charge",
            self.task.result.id,
            result={"ok": 2},
        )
        self.assertTrue(ok)
        with persisted(self.store, "o1", self.m) as i:
            self.assertIn("o.paid", i.current_state_ids)
            self.assertEqual(i.context["_xsm_celery"], {})

    def test_stale_or_forged_completion_is_ignored(self) -> None:
        from src.xstate_statemachine.contrib.celery import deliver_result

        plug = _Drops()
        self.assertFalse(
            deliver_result(
                self.store,
                self.m,
                "o1",
                "charge",
                "someone-else",
                result=1,
                plugins=[plug],
            )
        )
        self.assertEqual(plug.drops, ["stale_invocation"])
        self.assertFalse(
            deliver_result(self.store, self.m, "nope", "charge", "t")
        )
        # after the state was left, the real task's completion is stale too
        with persisted(self.store, "o1", self.m) as i:
            i.send("CANCEL")
        self.assertFalse(
            deliver_result(
                self.store,
                self.m,
                "o1",
                "charge",
                self.task.result.id,
                error=ValueError("late"),
            )
        )
        with persisted(self.store, "o1", self.m) as i:
            self.assertIn("o.cancelled", i.current_state_ids)

    def test_poll_results_delivers_and_times_out(self) -> None:
        from src.xstate_statemachine.contrib.celery import poll_results
        from src.xstate_statemachine.contrib.celery import service as svc

        app = _app()
        results = {}

        class R:
            def __init__(self, tid: str, app: Any = None) -> None:
                self.r = results.get(tid) or _Result()

            def ready(self) -> bool:
                return self.r.ready()

            def get(self, **kw: Any) -> Any:
                return self.r.get(**kw)

            def revoke(self, terminate: bool = False) -> None:
                self.r.revoked = True

        import celery.result as cr

        orig = cr.AsyncResult
        cr.AsyncResult = R  # type: ignore[misc]
        try:
            self.assertEqual(poll_results(self.store, self.m, app=app), 0)
            done = _Result()
            done.value, done.done = {"ok": 3}, True
            results[self.task.result.id] = done
            self.assertEqual(poll_results(self.store, self.m, app=app), 1)
        finally:
            cr.AsyncResult = orig  # type: ignore[misc]
        self.assertEqual(svc.pending_invocations(self.store), [])

    def test_poll_results_timeout_fails_the_invocation(self) -> None:
        from src.xstate_statemachine.contrib.celery import (
            celery_service,
            poll_results,
        )

        task = _Task()
        m = _machine(celery_service(task, watch=False, timeout_s=10))
        store = MemoryStore()
        with persisted(store, "o2", m):
            pass
        app = _app(eager=False)
        n = poll_results(store, m, app=app, now=lambda: time.time() + 60)
        self.assertEqual(n, 1)
        with persisted(store, "o2", m) as i:
            self.assertIn("o.failed", i.current_state_ids)
            self.assertEqual(i.context["error"], "TimeoutError")

    def test_signal_handlers_deliver(self) -> None:
        from src.xstate_statemachine.contrib.celery import connect_signals
        from celery.signals import task_failure, task_success

        disconnect = connect_signals(self.store, self.m, app=_app())
        try:

            class Req:
                id = self.task.result.id
                is_eager = False
                headers = {
                    "xsm_store_key": "o1",
                    "xsm_invocation_id": "charge",
                }

            class Sender:
                request = Req()

            task_success.send(sender=Sender(), result={"ok": 4})
            # ignored: eager, missing headers, no request
            Req.is_eager = True
            task_failure.send(sender=Sender(), exception=ValueError())
            task_success.send(sender=object(), result=1)
        finally:
            disconnect()
        with persisted(self.store, "o1", self.m) as i:
            self.assertIn("o.paid", i.current_state_ids)
            self.assertEqual(i.context["result"], {"ok": 4})


class TestEarlyCompletion(unittest.TestCase):
    """H1: the worker finishes BEFORE the caller's persisted() block saved
    the `_xsm_celery` record. The signal-path completion is parked, not
    dropped, and `poll_results` applies it once the record exists."""

    def test_worker_finishes_before_save(self) -> None:
        from celery.signals import task_success

        from src.xstate_statemachine.contrib.celery import (
            MemoryPendingResults,
            celery_service,
            connect_signals,
            poll_results,
        )

        task = _Task()
        m = _machine(celery_service(task, watch=False))
        store = MemoryStore()
        pending = MemoryPendingResults()
        app = _app(eager=False)
        disconnect = connect_signals(store, m, app=app, pending=pending)

        class Req:
            id = task.result.id
            is_eager = False
            headers = {"xsm_store_key": "e1", "xsm_invocation_id": "charge"}

        class Sender:
            request = Req()

        plug = _Drops()
        try:
            with persisted(store, "e1", m, plugins=[plug]):
                # the worker is faster than this block's save:
                task_success.send(sender=Sender(), result={"early": 1})
        finally:
            disconnect()
        self.assertEqual(len(pending), 1)
        self.assertEqual(plug.drops, [])  # not treated as stale
        import celery.result as cr

        orig = cr.AsyncResult
        cr.AsyncResult = lambda tid, app=None: _Result()  # type: ignore
        try:
            n = poll_results(store, m, app=app, pending=pending)
        finally:
            cr.AsyncResult = orig  # type: ignore[misc]
        self.assertEqual(n, 1)
        self.assertEqual(len(pending), 0)
        with persisted(store, "e1", m) as i:
            self.assertIn("o.paid", i.current_state_ids)
            self.assertEqual(i.context["result"], {"early": 1})

    def test_parked_entries_expire(self) -> None:
        from src.xstate_statemachine.contrib.celery import (
            MemoryPendingResults,
            PendingResult,
            poll_results,
        )

        pending = MemoryPendingResults(ttl_s=10)
        pending.add(PendingResult("x", "charge", "t", parked_at=0.0))
        store = MemoryStore()
        poll_results(store, None, app=_app(), pending=pending, now=lambda: 99)
        self.assertEqual(len(pending), 0)


class TestJsonOnly(unittest.TestCase):
    """H3: every entry point refuses pickle / YAML, by name or MIME type,
    for task AND result deserialisation."""

    def test_refusals(self) -> None:
        from src.xstate_statemachine.contrib.celery import (
            assert_json_serializer,
            celery_service,
            connect_signals,
            poll_results,
            statechart_task,
        )

        bad = [
            {"accept_content": ["json", "application/x-python-serialize"]},
            {"accept_content": ["json", "yaml"]},
            {"result_accept_content": ["pickle"]},
            {"result_serializer": "pickle"},
            {"task_serializer": "yaml"},
        ]
        for conf in bad:
            app = _app()
            for k, v in conf.items():
                setattr(app.conf, k, v)

            @app.task
            def t() -> None:
                pass

            with self.subTest(conf=conf):
                for call in (
                    lambda: assert_json_serializer(app),
                    lambda: celery_service(t),
                    lambda: statechart_task(app, MemoryStore(), None),
                    lambda: connect_signals(MemoryStore(), None, app=app),
                    lambda: poll_results(MemoryStore(), None, app=app),
                ):
                    with self.assertRaises(InvalidConfigError):
                        call()
        assert_json_serializer(_app())  # the default app is fine


class TestRealWorkerThread(unittest.TestCase):
    """A real Celery worker thread on the in-memory transport; completion
    reaches the persisted instance through the ``task_success`` signal."""

    def test_worker_signal_completion(self) -> None:
        from celery.contrib.testing.worker import start_worker

        from src.xstate_statemachine.contrib.celery import (
            celery_service,
            connect_signals,
        )

        app = _app(eager=False)

        @app.task(name="t.charge")
        def charge(n: int) -> dict:
            return {"n": n}

        m = _machine(
            celery_service(
                charge, args_from=lambda c, e: ((7,), {}), watch=False
            )
        )
        store = MemoryStore()
        disconnect = connect_signals(store, m, app=app)
        try:
            with start_worker(
                app, perform_ping_check=False, shutdown_timeout=10
            ):
                with persisted(store, "w1", m):
                    pass

                def paid() -> bool:
                    rec = store.load("w1")
                    return rec is not None and "paid" in rec.snapshot

                _wait(paid, timeout=15)
        finally:
            disconnect()
        with persisted(store, "w1", m) as i:
            self.assertEqual(i.context["result"], {"n": 7})


# -----------------------------------------------------------------------------
COUNTER = {
    "id": "c",
    "initial": "on",
    "context": {"n": 0},
    "states": {"on": {"on": {"INC": {"actions": "inc"}}}},
}


def _inc(i: Any, ctx: Any, e: Any, a: Any) -> None:
    ctx["n"] = ctx["n"] + 1


class TestStatechartTask(unittest.TestCase):
    def test_refuses_pickle(self) -> None:
        from src.xstate_statemachine.contrib.celery import statechart_task

        app = _app()
        app.conf.task_serializer = "pickle"
        with self.assertRaises(InvalidConfigError):
            statechart_task(app, MemoryStore(), None)
        app.conf.task_serializer = "json"
        app.conf.accept_content = ["json", "pickle"]
        with self.assertRaises(InvalidConfigError):
            statechart_task(app, MemoryStore(), None)

    def test_eight_threads_times_hundred_sends_no_lost_update(self) -> None:
        from src.xstate_statemachine.contrib.celery import statechart_task

        app = _app()
        store = MemoryStore()
        m = create_machine(COUNTER, logic=MachineLogic(actions={"inc": _inc}))

        @statechart_task(app, store, lambda key: m, max_retries=1000)
        def bump(counter: Any) -> int:
            counter.send("INC")
            return int(counter.context["n"])

        errors: List[BaseException] = []

        def worker() -> None:
            try:
                for _ in range(100):
                    # eager retries run synchronously inside `.delay()`;
                    # the outer result is SUCCESS or RETRY (the retry
                    # itself already applied), never a lost update.
                    res = bump.delay("k")
                    if res.state == "FAILURE":
                        raise res.result
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(120)
        self.assertEqual(errors, [])
        rec = store.load("k")
        assert rec is not None
        self.assertEqual(json.loads(rec.snapshot)["context"]["n"], 800)
        self.assertEqual(bump.name.split(".")[-1], "bump")


# -----------------------------------------------------------------------------
TIMED = {
    "id": "t",
    "initial": "waiting",
    "states": {
        "waiting": {"after": {"1000": "expired"}, "on": {"GO": "done"}},
        "expired": {},
        "done": {},
    },
}


class TestBeat(unittest.TestCase):
    def setUp(self) -> None:
        from src.xstate_statemachine.clock import SimulatedClock

        self.clock = SimulatedClock(wall_start=1_000_000.0)
        self.m = create_machine(TIMED)
        self.store = MemoryStore()
        with persisted(self.store, "t1", self.m, clock=self.clock):
            pass
        self.app = _app()

    def _sched(self, **kw: Any) -> Any:
        from src.xstate_statemachine.contrib.celery import (
            DurableTimerScheduler,
        )

        return DurableTimerScheduler(
            self.app, self.store, self.m, now=lambda: self.now, **kw
        )

    def _state(self) -> str:
        rec = self.store.load("t1")
        assert rec is not None
        return json.dumps(json.loads(rec.snapshot).get("value"))

    def test_scan_task_fires_matured_deadline_once(self) -> None:
        from src.xstate_statemachine.contrib.celery import xsm_deadlines_every

        s = self._sched()
        self.now = 1_000_000.5
        self.assertEqual(s.task.delay().result, 0)
        self.now = 1_000_002.0
        self.assertEqual(s.task.delay().result, 1)
        self.assertIn("expired", self._state())
        self.assertEqual(s.task.delay().result, 0)  # idempotent
        entry = xsm_deadlines_every(s, 5)["xsm-deadlines"]
        self.assertEqual(entry, {"task": s.task.name, "schedule": 5.0})

    def test_eta_job_checks_the_generation_and_double_fire_is_safe(
        self,
    ) -> None:
        s = self._sched()
        self.now = 1_000_002.0
        seen: List[Any] = []
        orig = s.fire_task.apply_async

        def capture(args: Any, eta: Any = None, **kw: Any) -> Any:
            seen.append((args, eta))
            return None

        s.fire_task.apply_async = capture  # type: ignore[method-assign]
        s.schedule_exact("t1")
        s.fire_task.apply_async = orig  # type: ignore[method-assign]
        (((key, state_id, seq), eta),) = seen
        self.assertEqual(key, "t1")
        self.assertEqual(eta.timestamp(), 1_000_001.0)
        self.assertFalse(s.fire(key, state_id, seq + 1))  # other generation
        self.assertTrue(s.fire(key, state_id, seq))
        self.assertIn("expired", self._state())
        self.assertFalse(s.fire(key, state_id, seq))  # fired already
        self.assertEqual(s.run_once(), 0)  # scanner safety net: nothing
        self.assertEqual(s.schedule_exact("missing"), [])

    def test_fire_does_not_wake_keys_sharing_the_prefix(self) -> None:
        with persisted(self.store, "t10", self.m, clock=self.clock):
            pass
        s = self._sched()
        self.now = 1_000_002.0
        (d,) = self.store.load("t1").deadlines
        self.assertTrue(s.fire("t1", d.state_id, d.entry_seq))
        rec = self.store.load("t10")
        assert rec is not None
        self.assertIn("waiting", json.dumps(json.loads(rec.snapshot)["value"]))

    def test_fire_ignores_the_global_scan_limit(self) -> None:
        """M5: with a backlog larger than `limit`, the eta job for one key
        still fires (it reads that key's deadlines directly)."""
        for n in range(5):
            with persisted(self.store, f"a{n}", self.m, clock=self.clock):
                pass
        s = self._sched(limit=2)
        self.now = 1_000_002.0
        (d,) = self.store.load("t1").deadlines
        self.assertTrue(s.fire("t1", d.state_id, d.entry_seq))
        self.assertIn("expired", self._state())

    def test_eta_job_for_a_left_state_is_skipped(self) -> None:
        s = self._sched()
        rec = self.store.load("t1")
        assert rec is not None
        (d,) = rec.deadlines
        with persisted(self.store, "t1", self.m, clock=self.clock) as i:
            i.send("GO")
        self.now = 1_000_002.0
        self.assertFalse(s.fire("t1", d.state_id, d.entry_seq))
        self.assertIn("done", self._state())


class TestOutboxRelayTask(unittest.TestCase):
    def test_one_loop_per_worker_no_connection_per_tick(self) -> None:
        """H2: an async broker is used from ONE private loop across Beat
        ticks (no rebind, no leaked client); `close_relay_loop` closes the
        broker and the loop."""
        from src.xstate_statemachine.contrib.celery import outbox_relay_task
        from src.xstate_statemachine.eda import Envelope, MemoryOutboxStore

        loops: List[Any] = []
        closed: List[bool] = []

        class Broker:
            async def publish(self, topic: str, env: Any) -> None:
                import asyncio

                loops.append(asyncio.get_running_loop())

            async def close(self) -> None:
                closed.append(True)

        outbox = MemoryOutboxStore()
        task = outbox_relay_task(_app(), outbox, Broker(), name="relay-h2")
        for _ in range(5):
            outbox.add("t", Envelope.new(type="x", subject="s"))
            self.assertEqual(task.delay().result, 1)
        self.assertEqual(len(set(map(id, loops))), 1)
        task.close_relay_loop()
        self.assertEqual(closed, [True])
        self.assertTrue(loops[0].is_closed())

    def test_sync_and_async_brokers(self) -> None:
        from src.xstate_statemachine.contrib.celery import outbox_relay_task
        from src.xstate_statemachine.eda import (
            Envelope,
            FakeBrokerAdapter,
            MemoryOutboxStore,
            SyncFakeBrokerAdapter,
        )

        app = _app()
        for broker in (SyncFakeBrokerAdapter(), FakeBrokerAdapter()):
            outbox = MemoryOutboxStore()
            outbox.add("t", Envelope.new(type="x", subject="s"))
            outbox.add("t", Envelope.new(type="x", subject="s"))
            task = outbox_relay_task(
                app, outbox, broker, name=f"relay-{id(broker)}"
            )
            self.assertEqual(task.delay().result, 2)
            self.assertEqual(len(broker.published), 2)
            self.assertEqual(task.delay().result, 0)


@pytest.mark.skipif(
    not os.environ.get("CELERY_BROKER_URL"),
    reason="live Celery broker: CELERY_BROKER_URL",
)
def test_live_broker_round_trip() -> None:
    from celery.contrib.testing.worker import start_worker

    from src.xstate_statemachine.contrib.celery import (
        celery_service,
        connect_signals,
    )

    app = celery.Celery(
        "live",
        broker=os.environ["CELERY_BROKER_URL"],
        backend=os.environ.get("CELERY_RESULT_BACKEND", "cache+memory://"),
    )

    @app.task(name="live.charge")
    def charge() -> dict:
        return {"live": True}

    m = _machine(celery_service(charge, watch=False))
    store = MemoryStore()
    disconnect = connect_signals(store, m, app=app)
    try:
        with start_worker(app, perform_ping_check=False):
            with persisted(store, "l1", m):
                pass
            end = time.monotonic() + 30
            while time.monotonic() < end:
                rec = store.load("l1")
                if rec is not None and "paid" in rec.snapshot:
                    break
                time.sleep(0.1)
    finally:
        disconnect()
    with persisted(store, "l1", m) as i:
        assert "o.paid" in i.current_state_ids
