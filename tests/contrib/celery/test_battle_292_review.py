# tests/contrib/celery/test_battle_292_review.py
"""#292 independent review -- regressions for what it found.

* **H1** `register_task` on an ``autofinalize=False`` app: a duplicate
  name, and a `@shared_task` of the same name, must be refused BEFORE
  ``finalize()`` silently keeps the wrong one;
* **H2** `outbox_relay_task` on a lazy app: attaching the closer must
  not evaluate the proxy; `close_relay_loop(app)` works after finalize;
* **M2** a completion whose record names another task is PARKED when a
  pending table is given (a re-entered invoke whose task finished before
  its record was saved), and settled by `poll_results`;
* **M3** `MemoryPendingResults(max_items=0)` / ``ttl_s<=0`` are refused.
"""

from __future__ import annotations

import time
import unittest

import pytest

celery = pytest.importorskip("celery")

from src.xstate_statemachine import create_machine  # noqa: E402
from src.xstate_statemachine.contrib.celery import (  # noqa: E402
    MemoryPendingResults,
    close_relay_loop,
    outbox_relay_task,
    register_task,
)
from src.xstate_statemachine.eda import MemoryOutboxStore  # noqa: E402
from src.xstate_statemachine.exceptions import InvalidConfigError  # noqa: E402


def _lazy() -> "celery.Celery":
    app = celery.Celery(
        f"lazy{time.monotonic_ns()}", broker="memory://", autofinalize=False
    )
    app.conf.task_always_eager = True
    return app


def _f() -> int:
    return 1


def _g() -> int:
    return 2


class TestLazyApp(unittest.TestCase):
    def test_duplicate_name_refused_before_finalize(self) -> None:
        app = _lazy()
        register_task(app, _f, name="dup.lazy")
        with self.assertRaises(InvalidConfigError):
            register_task(app, _g, name="dup.lazy")
        app.finalize()
        self.assertEqual(app.tasks["dup.lazy"].run(), 1)

    def test_shared_task_of_same_name_refused(self) -> None:
        name = f"shared.{time.monotonic_ns()}"

        @celery.shared_task(name=name)
        def shared() -> str:  # pragma: no cover - never run
            return "shared"

        app = _lazy()
        with self.assertRaises(InvalidConfigError):
            register_task(app, _g, name=name)

    def test_register_does_not_finalise_a_finalisable_app(self) -> None:
        app = celery.Celery(f"f{time.monotonic_ns()}", broker="memory://")
        register_task(app, _f, name="side.effect")
        self.assertFalse(app.finalized)

    def test_relay_on_lazy_app_closer_attached_after_finalize(self):
        class Broker:
            def publish(self, topic, env):  # pragma: no cover
                pass

        app = _lazy()
        outbox_relay_task(app, MemoryOutboxStore(), Broker())  # no raise
        app.finalize()
        task = app.tasks["xsm.outbox.relay"]
        self.assertTrue(callable(getattr(task, "close_relay_loop", None)))
        close_relay_loop(app)  # idempotent, no loop opened yet
        self.assertEqual(task.delay().result, 0)


class TestPendingTable(unittest.TestCase):
    def test_bad_limits_refused(self) -> None:
        with self.assertRaises(InvalidConfigError):
            MemoryPendingResults(max_items=0)
        with self.assertRaises(InvalidConfigError):
            MemoryPendingResults(ttl_s=0)

    def test_wrong_task_id_is_parked_not_dropped_with_a_table(self):
        """A re-entered invoke's NEW task finishing before its record is
        saved looks like "record names another task": with a pending
        table it is parked (not dropped) and `poll_results` then settles
        it against the final record."""
        from src.xstate_statemachine.contrib.celery import (
            deliver_result,
            poll_results,
        )
        from src.xstate_statemachine.contrib.celery.service import (
            CONTEXT_KEY,
        )

        from .test_battle_292_a import _async_result, _done, _durable

        task, m, store = _durable(["k"])
        rec = store.load("k")
        import json

        ctx = json.loads(rec.snapshot)["context"]
        [(inv_id, item)] = ctx[CONTEXT_KEY].items()
        recorded = item["task_id"]
        pend = MemoryPendingResults()
        # a completion for a task id the record does NOT name
        applied = deliver_result(
            store, m, "k", inv_id, "other-task", result={"v": 1}, pending=pend
        )
        self.assertFalse(applied)
        self.assertEqual(len(pend), 1)
        # ... and without a table it is dropped outright (the old path)
        self.assertFalse(
            deliver_result(store, m, "k", inv_id, "other-task", result={})
        )
        # `poll_results` retries the parked entry: still not ours -> gone,
        # while the REAL task's result lands
        app = celery.Celery(f"p{time.monotonic_ns()}", broker="memory://")
        with _async_result(lambda tid, app=None: _done({"v": 2})):
            n = poll_results(store, m, app=app, pending=pend)
        self.assertEqual(len(pend), 0)
        self.assertGreaterEqual(n, 1)
        self.assertIn("paid", json.loads(store.load("k").snapshot)["value"])
        del recorded, task
