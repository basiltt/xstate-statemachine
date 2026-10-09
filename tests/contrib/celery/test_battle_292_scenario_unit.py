# tests/contrib/celery/test_battle_292_scenario_unit.py
"""#292 battle (scenario finding): Celery tasks are ``shared=True`` by
default, so a task registered on app A was RE-CREATED on every app built
later -- with A's closure. A second `FulfilmentApp` ran the FIRST app's
Beat scan against the first app's store and reported 0 woken for its
own. `register_task` registers ``shared=False`` and refuses a same-app
duplicate name instead of silently returning the existing task."""

from __future__ import annotations

import time
import unittest

import pytest

celery = pytest.importorskip("celery")

from src.xstate_statemachine import create_machine  # noqa: E402
from src.xstate_statemachine.contrib.celery import (  # noqa: E402
    DurableTimerScheduler,
    outbox_relay_task,
    register_task,
    statechart_task,
)
from src.xstate_statemachine.eda import MemoryOutboxStore  # noqa: E402
from src.xstate_statemachine.exceptions import InvalidConfigError  # noqa: E402
from src.xstate_statemachine.persistence import MemoryStore  # noqa: E402


def _app() -> "celery.Celery":
    app = celery.Celery(
        f"t{time.monotonic_ns()}",
        broker="memory://",
        backend="cache+memory://",
    )
    app.conf.task_always_eager = True
    return app


CFG = {"id": "m", "initial": "a", "states": {"a": {}}}


class TestSharedTaskLeak(unittest.TestCase):
    def test_second_app_gets_its_own_scheduler_not_the_first_apps(self):
        m = create_machine(CFG)
        store_a, store_b = MemoryStore(), MemoryStore()
        sched_a = DurableTimerScheduler(_app(), store_a, m)
        app_b = _app()
        # 🔥 before the fix app_b.tasks already held app A's scan task
        self.assertNotIn("xsm.deadlines.scan", app_b.tasks)
        sched_b = DurableTimerScheduler(app_b, store_b, m)
        self.assertIsNot(sched_a.task, sched_b.task)
        self.assertIs(sched_b.task.app, app_b)

    def test_same_app_duplicate_default_name_is_refused(self) -> None:
        m = create_machine(CFG)
        app = _app()
        DurableTimerScheduler(app, MemoryStore(), m)
        with self.assertRaises(InvalidConfigError) as cm:
            DurableTimerScheduler(app, MemoryStore(), m)
        self.assertIn("xsm.deadlines.scan", str(cm.exception))
        # a distinct name is the way to have two
        DurableTimerScheduler(
            app, MemoryStore(), m, name="scan2", fire_name="fire2"
        )

    def test_relay_and_statechart_task_are_guarded_too(self) -> None:
        app = _app()
        outbox_relay_task(app, MemoryOutboxStore(), object())
        with self.assertRaises(InvalidConfigError):
            outbox_relay_task(app, MemoryOutboxStore(), object())
        m = create_machine(CFG)

        @statechart_task(app, MemoryStore(), m, name="x.pay")
        def pay(order):  # pragma: no cover - never run
            pass

        with self.assertRaises(InvalidConfigError):

            @statechart_task(app, MemoryStore(), m, name="x.pay")
            def pay2(order):  # pragma: no cover
                pass

    def test_register_task_is_not_shared(self) -> None:
        app = _app()

        def probe() -> int:  # Celery cannot wrap a lambda
            return 1

        t = register_task(app, probe, name="leak.probe")
        self.assertNotIn("leak.probe", _app().tasks)
        self.assertIs(t.app, app)
