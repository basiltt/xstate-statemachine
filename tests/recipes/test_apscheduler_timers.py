# tests/recipes/test_apscheduler_timers.py
"""APScheduler recipe: durable 7/14-day timers fired by the scanner job."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, List

import pytest

from .conftest import load_recipe, requires

rec = load_recipe("apscheduler_timers", "apscheduler_timers")
DAY = 86_400.0


def _setup(tmp_path: Path) -> Any:
    from xstate_statemachine import SimulatedClock
    from xstate_statemachine.persistence import DueTimerScanner, SQLiteStore

    store = SQLiteStore(tmp_path / "t.db")
    sent: List[str] = []
    machine = rec.build_machine(sent)
    rec.start_trial(store, machine, "ann", clock=SimulatedClock(wall_start=0))
    scanner = DueTimerScanner(store, lambda k: machine, prefix=rec.PREFIX)
    return store, sent, scanner


def _state(store: Any) -> Any:
    return json.loads(store.load("trial.ann").snapshot)


def test_scanner_fires_reminder_then_expiry(tmp_path: Path) -> None:
    store, sent, scanner = _setup(tmp_path)
    assert scanner.run_once(now=6 * DAY) == 0  # nothing due yet
    assert scanner.run_once(now=7 * DAY + 60) == 1
    assert sent == ["reminder:trial.ann"]
    assert _state(store)["context"]["reminders"] == 1
    assert scanner.run_once(now=7 * DAY + 120) == 0  # fired once only
    assert scanner.run_once(now=14 * DAY + 60) == 1
    assert sent[-1] == "expired:trial.ann"
    assert store.load("trial.ann").deadlines == ()
    store.close()


def test_subscribe_cancels_the_durable_timers(tmp_path: Path) -> None:
    from xstate_statemachine import SimulatedClock
    from xstate_statemachine.persistence import persisted

    store, sent, scanner = _setup(tmp_path)
    machine = scanner.machine_for_key("trial.ann")
    day_one = SimulatedClock(wall_start=DAY)  # the user subscribes on day 1
    with persisted(store, "trial.ann", machine, clock=day_one) as t:
        t.send("SUBSCRIBE")
    assert scanner.run_once(now=30 * DAY) == 0 and sent == []
    store.close()


@requires("apscheduler")
@pytest.mark.parametrize("cron", [False, True])
def test_apscheduler_job_runs_the_scanner(tmp_path: Path, cron: bool) -> None:
    store, sent, scanner = _setup(tmp_path)
    scanner.now = lambda: 7 * DAY + 60  # the job calls run_once() bare
    ran = threading.Event()
    real = scanner.run_once

    def run_once(now: Any = None) -> int:
        n = real(now)
        ran.set()
        return n

    scanner.run_once = run_once  # type: ignore[method-assign]
    sched = rec.build_scheduler(scanner, cron=cron)
    job = sched.get_job("xsm-due-timers")
    assert job.max_instances == 1 and job.coalesce is True
    sched.start()
    try:
        # 📝 don't wait a minute: pull the job forward to "now"
        import datetime as dt

        job.modify(next_run_time=dt.datetime.now(dt.timezone.utc))
        assert ran.wait(10), "APScheduler never ran the scanner job"
    finally:
        sched.shutdown(wait=True)
    assert sent == ["reminder:trial.ann"]
    store.close()


def test_scheduler_role_parity_with_fastapi_example() -> None:
    src = (Path(rec.__file__)).read_text("utf-8")
    assert '"--role"' in src and '"scheduler"' in src
    app = (
        Path(rec.__file__).parents[2] / "integrations" / "fastapi_orders"
    ) / "app.py"
    assert "--role scheduler" in app.read_text("utf-8")
