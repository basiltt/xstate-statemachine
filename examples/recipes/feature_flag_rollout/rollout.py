# examples/recipes/feature_flag_rollout/rollout.py
# -----------------------------------------------------------------------------
# 🚩 Feature-flag rollout: staged exposure with a metrics guard (#308)
# -----------------------------------------------------------------------------
# 🏛️ The chart owns the POLICY (stages, bake times, what "unhealthy" does);
#    the application owns two plug points:
#      * `metrics()` -- a callable returning current health numbers. The
#        `metricsHealthy` guard calls it when a bake timer fires, so the
#        decision uses the numbers at promotion time, not at start.
#      * `apply_percent(flag, pct)` -- pushes exposure to your flag system
#        (LaunchDarkly, Unleash, a DB row). Called from the `setPercent`
#        entry action of every stage, so rollback ALWAYS zeroes exposure.
# 💡 Bake times are `after` delays: test them on a `SimulatedClock`, and in
#    production persist the machine so `DueTimerScanner` fires them.
# -----------------------------------------------------------------------------
"""Rollout logic for `machine.json`."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict

from xstate_statemachine import MachineLogic, create_machine

HERE = Path(__file__).resolve().parent
#: Promotion needs BOTH: error rate at most 1 %, p99 at most 800 ms.
MAX_ERROR_RATE = 0.01
MAX_P99_MS = 800.0

Metrics = Callable[[], Dict[str, float]]


def healthy(m: Dict[str, float]) -> bool:
    return (
        m.get("error_rate", 1.0) <= MAX_ERROR_RATE
        and m.get("p99_ms", float("inf")) <= MAX_P99_MS
    )


def build_machine(
    metrics: Metrics,
    apply_percent: Callable[[str, float], None] = lambda f, p: None,
) -> Any:
    def set_percent(i: Any, ctx: Dict, e: Any, a: Any) -> None:
        pct = float(a.params["percent"])
        ctx["percent"] = pct
        ctx["history"].append(pct)
        apply_percent(ctx["flag"], pct)

    logic = MachineLogic(
        actions={"setPercent": set_percent},
        guards={"metricsHealthy": lambda ctx, e: healthy(metrics())},
    )
    config = json.loads((HERE / "machine.json").read_text("utf-8"))
    return create_machine(config, logic=logic)
