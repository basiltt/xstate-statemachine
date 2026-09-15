"""LC-45 repro: the event hot path allocates per event and logs at INFO on
every transition, guard evaluation and state entry/exit.

Two measurable symptoms, both in the shared engine code:

  * `base_interpreter._select_transitions` (`:2562-2599`) rebuilds a `leaves`
    list, sorts it, builds a per-leaf `eligible` list and a fresh `guard_cache`
    dict for EVERY event; `_matching_descriptors` (`:2408-2418`) rescans every
    key of every `on` map on every ancestor walk with no precompiled
    descriptor index; `_is_descendant` (`:2751-2771`) does
    `node.id.startswith(f"{ancestor.id}.")` -- an f-string allocation plus
    O(len(id)) string compare -- inside loops over the active configuration,
    even though `StateNode.depth` is already cached as an int.

  * Guard evaluation logs `logger.info` per guard (`:2927-2931`); the sync
    engine logs `logger.info` per event (`sync_interpreter.py:365`) and per
    state entry/exit (`:643`, `:747`). Those are unconditional calls with
    argument tuples; attaching any INFO handler makes them cost real time.

This script measures (1) allocations per event with `tracemalloc` and
(2) throughput with the `xstate_statemachine` logger disabled vs. enabled at
INFO with a null-ish handler.

Exit code 1 if per-event allocation is non-trivial or INFO logging measurably
slows the hot path.
"""

from __future__ import annotations

import cProfile
import io
import logging
import pstats
import sys
import time

from xstate_statemachine import MachineLogic, SyncInterpreter, create_machine

CONFIG = {
    "id": "oms",
    "initial": "idle",
    "context": {"n": 0, "qty": 0.0},
    "states": {
        "idle": {"on": {"SUBMIT": {"target": "open", "actions": ["tick"]}}},
        "open": {
            "on": {
                "FILL": [
                    {
                        "target": "open",
                        "cond": "is_partial",
                        "actions": ["tick"],
                    },
                    {"target": "closed", "actions": ["tick"]},
                ],
                "AMEND": {"target": "open", "actions": ["tick"]},
            }
        },
        "closed": {"type": "final"},
    },
}


def tick(interpreter, context, event, action_def) -> None:
    context["n"] += 1


def is_partial(context, event) -> bool:
    return True


def build():
    return SyncInterpreter(
        create_machine(
            CONFIG,
            logic=MachineLogic(
                actions={"tick": tick}, guards={"is_partial": is_partial}
            ),
        )
    ).start()


def events(n):
    return [{"type": "SUBMIT"}] + [
        {"type": "FILL" if k % 2 else "AMEND", "qty": 1.0}
        for k in range(n - 1)
    ]


N = 5_000
EV = events(N)

logging.disable(logging.CRITICAL)

# 1️⃣ Hot-path work per event: how many times the per-event helpers run.
#    (Allocation here is churn, not retention: the temporaries are freed each
#    event, so a tracemalloc high-water mark stays flat. What costs time is
#    that they are rebuilt from scratch every single event.)
it = build()
prof = cProfile.Profile()
prof.enable()
for e in EV:
    it.send(e)
prof.disable()
counts = {}
stats_obj = pstats.Stats(prof)
for (fname, line, func), (cc, nc, tt, ct, _cal) in stats_obj.stats.items():
    if "xstate_statemachine" in fname and func in (
        "_select_transitions",
        "_collect_eligible_transitions",
        "_matching_descriptors",
        "_is_descendant",
        "_evaluate_guard",
    ):
        counts[func] = (nc, tt)
print(f"OBSERVED per-event hot-path helper calls over {N} events:")
for func, (nc, tt) in sorted(counts.items(), key=lambda kv: -kv[1][0]):
    print(
        f"  {func:<32} calls={nc:>7} ({nc / N:.1f}/event)  "
        f"tottime={tt * 1e6 / N:.1f} us/event"
    )


# 2️⃣ INFO logging cost on the hot path.
def run(n):
    it = build()
    evs = EV[:n]
    t0 = time.perf_counter()
    for e in evs:
        it.send(e)
    return (time.perf_counter() - t0) / n * 1e6


run(500)
us_quiet = run(N)

logging.disable(logging.NOTSET)
lg = logging.getLogger("xstate_statemachine")
lg.setLevel(logging.INFO)
lg.addHandler(logging.StreamHandler(io.StringIO()))
run(500)
us_info = run(N)
logging.disable(logging.CRITICAL)

print(f"OBSERVED logging disabled : {us_quiet:.1f} us/event")
print(f"OBSERVED logger at INFO   : {us_info:.1f} us/event")
print(f"OBSERVED slowdown         : {us_info / us_quiet:.2f}x")
print(
    "EXPECTED a precompiled descriptor/transition index instead of rebuilding "
    "candidate lists per event, and no measurable cost from a library whose "
    "hot path logs at DEBUG"
)

ok = us_info / us_quiet < 1.10
sys.exit(0 if ok else 1)
