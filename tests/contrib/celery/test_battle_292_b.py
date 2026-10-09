"""#292 battle B -- the operator's and newcomer's view of ``[celery]``.

* A flood of forged ``xsm_store_key`` headers must not grow a worker's
  `MemoryPendingResults` without bound.
* A forged key that EXISTS (another tenant, another machine) applies
  nothing and writes nothing.
* `register_task`: two apps in one process keep their own tasks; a taken
  name on one app is refused.
* The guide names every public symbol and every operator-visible error.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("celery")

from celery import Celery  # noqa: E402

from xstate_statemachine import create_machine  # noqa: E402
from xstate_statemachine.contrib import celery as xc  # noqa: E402
from xstate_statemachine.exceptions import InvalidConfigError  # noqa: E402
from xstate_statemachine.persistence import (  # noqa: E402
    MemoryStore,
    persisted,
)

ROOT = Path(__file__).resolve().parents[3]
GUIDE = ROOT / "docs" / "_guide" / "integration-celery.md"


def _app(name: str) -> Celery:
    app = Celery(name, broker="memory://", backend="cache+memory://")
    app.conf.task_always_eager = True
    return app


def _idle() -> Any:
    return create_machine({"id": "o", "initial": "a", "states": {"a": {}}})


# -----------------------------------------------------------------------------
# 🛡️ forged headers
# -----------------------------------------------------------------------------
def test_forged_keys_cannot_grow_the_pending_table_without_bound(
    caplog: Any,
) -> None:
    pending = xc.MemoryPendingResults(max_items=50)
    store = MemoryStore()
    with caplog.at_level(logging.WARNING):
        for n in range(500):
            xc.deliver_result(
                store, _idle(), f"forged-{n}", "x", f"t{n}", pending=pending
            )
    assert len(pending) == 50
    kept = {p.task_id for p in pending.take_all()}
    assert kept == {f"t{n}" for n in range(450, 500)}  # newest kept
    assert "evicted" in caplog.text


def test_default_pending_table_is_bounded() -> None:
    assert xc.MemoryPendingResults().max_items == 10_000


def test_reparking_one_task_does_not_duplicate_or_evict() -> None:
    pending = xc.MemoryPendingResults(max_items=2)
    for _ in range(5):
        pending.add(xc.PendingResult("k", "x", "same"))
    pending.add(xc.PendingResult("k", "x", "other"))
    assert len(pending) == 2


def test_existing_key_of_another_machine_applies_and_writes_nothing() -> None:
    # 📝 tenant B's instance exists and even records the forged task id
    #    under the forged invocation id -- but no such invocation is
    #    ACTIVE, so the completion is stale: no apply, no version bump.
    store = MemoryStore()
    with persisted(store, "tenant-b", _idle()) as i:
        i.context["_xsm_celery"] = {"x": {"task_id": "T"}}
    before = store.load("tenant-b")
    assert not xc.deliver_result(
        store, _idle(), "tenant-b", "x", "T", result=1
    )
    after = store.load("tenant-b")
    assert '"T"' in before.snapshot
    # 📝 the matching task id is retired (it finished after the state was
    #    left); a WRONG task id changes nothing at all.
    assert '"T"' not in after.snapshot
    assert not xc.deliver_result(store, _idle(), "tenant-b", "x", "NOPE")
    assert store.load("tenant-b").version == after.version


# -----------------------------------------------------------------------------
# 🧩 register_task
# -----------------------------------------------------------------------------
def test_two_apps_in_one_process_keep_their_own_scan_tasks() -> None:
    a, b = _app("tenant-a"), _app("tenant-b")
    sa = xc.DurableTimerScheduler(a, MemoryStore(), _idle())
    sb = xc.DurableTimerScheduler(b, MemoryStore(), _idle())
    assert a.tasks[sa.task.name] is not b.tasks[sb.task.name]
    assert sa.scanner.store is not sb.scanner.store


def test_taken_name_is_refused_and_name_kwarg_is_the_way_out() -> None:
    app = _app("one")
    xc.DurableTimerScheduler(app, MemoryStore(), _idle())
    with pytest.raises(InvalidConfigError, match="already registered"):
        xc.DurableTimerScheduler(app, MemoryStore(), _idle())
    xc.DurableTimerScheduler(
        app,
        MemoryStore(),
        _idle(),
        name="eu.deadlines.scan",
        fire_name="eu.deadlines.fire",
    )


@pytest.mark.parametrize("which", ["scheduler", "relay"])
def test_beat_entry_points_refuse_pickle(which: str) -> None:
    # 🔐 the guide says EVERY entry point refuses pickle; these two did not
    app = _app("pickle")
    app.conf.accept_content = ["json", "pickle"]
    with pytest.raises(InvalidConfigError, match="pickle"):
        if which == "scheduler":
            xc.DurableTimerScheduler(app, MemoryStore(), _idle())
        else:
            xc.outbox_relay_task(app, object(), object())
    assert not [t for t in app.tasks if t.startswith("xsm.")]


# -----------------------------------------------------------------------------
# 📚 the guide
# -----------------------------------------------------------------------------
def test_guide_names_every_public_symbol() -> None:
    text = GUIDE.read_text("utf-8")
    missing = [
        n for n in xc.__all__ if f"`{n}" not in text and f"`@{n}" not in text
    ]
    assert not missing, missing


@pytest.mark.parametrize(
    "needle",
    [
        "already registered on this app",
        "Never call result.get() within a task",
        "ConflictError",
        "LockTimeoutError",
        "arrived before its record",
        "stale_invocation",
        "cache+memory://",
        "evicted",
        "## Operations",
        "PENDING_TTL_S",
        "lease_s",
    ],
)
def test_guide_explains_operator_visible_errors(needle: str) -> None:
    assert needle in GUIDE.read_text("utf-8")


def test_guide_threat_model_lists_every_pickle_entry_point() -> None:
    model = GUIDE.read_text("utf-8").split("## Threat model", 1)[1]
    model = model.split("\n## ", 1)[0]
    for name in (
        "celery_service",
        "statechart_task",
        "connect_signals",
        "poll_results",
        "DurableTimerScheduler",
        "outbox_relay_task",
    ):
        assert re.search(rf"`@?{name}", model), name
