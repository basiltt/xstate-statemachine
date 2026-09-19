# Bug: `SyncInterpreter` macrostep budget still discards legitimate external events; the CHANGELOG's \"the two engines now agree\" is not accurate


## Summary

`SyncInterpreter._process_event_queue` increments its runaway counter for
**every** event, and once `max_iterations` (default 1000) is exceeded it calls
`self._event_queue.clear()` — silently discarding every remaining queued event.

0.8.0's fix exempted only *replayed deferred* events via `replay_credit`. Plain
external events still count, so batching more than 1000 of them through
`send_events()` loses the tail with no exception, no return value to inspect, and
`queue_depth == 0` afterwards.

The async `Interpreter` processes all N through the identical call, so the
CHANGELOG line is not accurate as written:

> `SyncInterpreter`: replayed deferred events no longer count against the
> macrostep runaway budget … The async engine already behaved correctly; the two
> now agree.

## Environment

- Library: `xstate-statemachine` 0.8.0, commit `9bf6065`, local clone, `pip install -e .`
- Python: 3.13.7 (CPython, MSC v.1944 64-bit)
- OS: Windows 11 x64 (10.0.26200)

## Minimal reproduction

```python
from xstate_statemachine import SyncInterpreter, MachineLogic, create_machine

CFG = {"id": "bud", "initial": "a", "context": {"seen": 0},
       "states": {"a": {"on": {"T": {"target": "a", "actions": ["bump"],
                                     "reenter": True}}}}}

def bump(interp, ctx, event, action):
    ctx["seen"] = ctx.get("seen", 0) + 1

i = SyncInterpreter(create_machine(CFG, logic=MachineLogic(actions={"bump": bump})))
i.start()
i.send_events(["T"] * 1501)
print(i.context["seen"], i.queue_depth)     # -> 1000 0     (expected 1501 0)
```

Full script with the async control: `repro/N-03_sync-macrostep-budget-clears-queue.py`
(exits 1 while present, 0 once fixed).

## Observed

```
OBSERVED events batched via send_events : 1501
OBSERVED SyncInterpreter processed      : 1000  (queue_depth after: 0)
OBSERVED Interpreter (async) processed  : 1501
EXPECTED both engines processed         : 1501
OBSERVED lost silently by sync engine   : 501 (budget=1000; queue cleared, no exception, no signal)
RESULT: DEFECT REPRODUCED
```

The cliff is exactly at the budget:

| batch size | sync `seen` | async `seen` |
|---:|---:|---:|
| 999 | 999 | 999 |
| 1001 | **1000** | 1001 |
| 1501 | **1000** | 1501 |
| 3000 | **1000** | 3000 |

## Expected

Either both engines process all N, or the sync engine raises when it hits the
runaway guard. What must not happen is the current behaviour: the queue is
cleared, the caller's `send_events()` returns normally, `queue_depth` reads 0,
and there is no way to learn that 501 events were dropped.

The runaway guard exists to catch an infinite `always`/`raise` loop — a
*self-sustaining* microstep chain. A batch of N distinct external events is not
that, and counting them against the same budget conflates two different things.

## Root cause

`sync_interpreter.py::_process_event_queue`. The counter is incremented per
dequeued event rather than per *microstep*, and the overflow path is a silent
`clear()`:

```python
processed += 1
...
if processed > max_iterations:
    self._event_queue.clear()      # every remaining external event, gone
```

`replay_credit` exempts replayed deferred events (the 0.8.0 fix) but nothing
else. The async engine tracks `_raise_depth` — a *depth*, not a throughput count
— which is why it is unaffected.

## Impact

For CandleViewer this is Medium only because we do not use `SyncInterpreter`
(and, after N-02, will not). For anyone who does, it is a silent data-loss bug on
the default configuration of a shipped engine, reachable by an ordinary batch
ingest. It is also precisely the failure class the 0.8.0 release was written to
eliminate.

## Suggested fix

1. Port the async engine's `_raise_depth` concept: count **microstep depth
   within one macrostep**, not events processed across a drain. A runaway
   `always` loop trips it; 1501 external events do not.
2. Failing that, raise on overflow instead of clearing — a loud, wrong-ish
   behaviour beats a silent, wrong one — and never discard events the caller has
   already been told were accepted.
3. Correct the CHANGELOG line claiming the engines agree.

## Acceptance criteria

- [ ] `repro/N-03_sync-macrostep-budget-clears-queue.py` exits 0.
- [ ] `send_events(["T"] * 5000)` on the sync engine processes all 5000.
- [ ] A genuine runaway (an `always` self-loop with a guard that never settles)
      still trips the guard, and does so by raising rather than by clearing.
- [ ] Sync and async engines produce byte-identical action traces for a
      2000-event batch.
- [ ] Tests added:
  - `tests/test_core_algorithm.py::test_sync_large_batch_is_not_truncated`
  - `tests/test_core_algorithm.py::test_sync_runaway_always_loop_still_raises`
  - `tests/test_core_algorithm.py::test_engine_trace_parity_large_batch`

## Related

- The 0.8.0 `Fixed` entry about replayed deferred events and the macrostep
  budget — this is the unfixed remainder of the same code path.
- `#60` (LC-57) — the one-core-algorithm refactor; this is a place where the two
  engines still diverge.

## Verification

Independently verified on 2026-09-17.

- Library: 0.8.0, commit `9bf6065`, local clone, `pip install -e .`.
- Python 3.13.7, Windows 11 x64.
- Repro run in a fresh process → **exit 1**, output as quoted.
- Async control in the same process and the same run processes all 1501,
  isolating this to the sync engine.
- Boundary swept at 999 / 1001 / 1501 / 3000; the loss begins at exactly 1001,
  confirming `max_iterations = 1000` as the mechanism.


---
Found while re-verifying the 0.8.0 release against the adoption-readiness checklist in #26. Self-contained repro attached in the body; exits 1 while the defect is present, 0 once fixed.

