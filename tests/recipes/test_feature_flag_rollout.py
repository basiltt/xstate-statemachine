# tests/recipes/test_feature_flag_rollout.py
"""Feature-flag rollout: bake times on a SimulatedClock, the metrics guard
reading a live callable, both engines."""

from __future__ import annotations

from typing import Any, Dict, List

import pytest

from .conftest import Driver, load_recipe

ro = load_recipe("feature_flag_rollout", "rollout")
HOUR = 3_600_000
GOOD = {"error_rate": 0.001, "p99_ms": 300.0}
BAD = {"error_rate": 0.05, "p99_ms": 300.0}


@pytest.fixture(params=["sync", "async"])
def flag(request: Any) -> Any:
    current: Dict[str, Any] = {"m": dict(GOOD)}
    pushed: List[Any] = []
    machine = ro.build_machine(
        lambda: current["m"], lambda f, p: pushed.append((f, p))
    )
    d = Driver(request.param, machine)
    d.metrics, d.pushed = current, pushed  # type: ignore[attr-defined]
    yield d
    d.close()


def leaf(d: Driver) -> str:
    return sorted(d.i.current_state_ids)[-1].rsplit(".", 1)[-1]


def test_healthy_rollout_reaches_ga(flag: Driver) -> None:
    flag.send("START")
    assert leaf(flag) == "internal"
    flag.wait(HOUR - 1)
    assert leaf(flag) == "internal"  # still baking
    flag.wait(1)
    assert leaf(flag) == "canary_1"
    flag.wait(HOUR)
    assert leaf(flag) == "canary_25"
    flag.wait(24 * HOUR)
    assert flag.value == "ga"
    assert flag.i.context["history"] == [0, 0.1, 1, 25, 100]
    assert flag.pushed[-1] == ("new_checkout", 100.0)


def test_metrics_read_at_promotion_time(flag: Driver) -> None:
    flag.send("START")
    flag.wait(HOUR)
    flag.metrics["m"] = dict(BAD)  # degrades during canary_1
    flag.wait(HOUR)
    assert flag.value == "rolled_back"
    assert flag.i.context["percent"] == 0
    assert flag.pushed[-1] == ("new_checkout", 0.0)


def test_alert_rolls_back_from_any_exposed_stage(flag: Driver) -> None:
    flag.send("START")
    flag.wait(2 * HOUR)
    assert leaf(flag) == "canary_25"
    flag.send("METRICS_BAD")
    assert flag.value == "rolled_back"
    flag.wait(48 * HOUR)  # bake timers were cancelled on exit
    assert flag.value == "rolled_back"
    flag.send("RETRY")
    assert flag.value == "disabled"


def test_manual_rollback_from_ga(flag: Driver) -> None:
    flag.send("START")
    flag.wait(26 * HOUR)
    assert flag.value == "ga"
    flag.send("ROLLBACK")
    assert flag.value == "rolled_back"


@pytest.mark.parametrize(
    "m,ok",
    [
        (GOOD, True),
        (BAD, False),
        ({"error_rate": 0.0, "p99_ms": 900.0}, False),
        ({}, False),  # missing metrics never promote
    ],
)
def test_health_rule(m: Dict[str, float], ok: bool) -> None:
    assert ro.healthy(m) is ok
