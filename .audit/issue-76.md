# Bug: `SyncInterpreter` `after` deadlines are unreachable by `tick()` when the interpreter is constructed inside a running asyncio loop


## Summary

`RealClock.set_timeout` chooses its delivery lane by inspecting the **caller's**
context rather than the engine that owns the clock. A `SyncInterpreter`
constructed from inside a running asyncio loop therefore parks its `after`
deadlines on `loop.call_later`, leaving `clock._heap` empty — and
`SyncInterpreter.tick()` and the pump at the top of `send()` drain only the heap.

The result is that **`tick()` stops being authoritative**: it cannot deliver a
deadline that is genuinely due, which is the one guarantee the new synchronous
timer lane exists to provide.

This is the same shape as #50, displaced rather than resolved: the sync engine no
longer spawns a thread per timer (confirmed: 25 machines → **+0 threads**), but
in a loop context it schedules onto machinery its own pump cannot reach.

## Environment

- Library: `xstate-statemachine` 0.8.0, commit `9bf6065`, local clone, `pip install -e .`
- Python: 3.13.7 (CPython, MSC v.1944 64-bit)
- OS: Windows 11 x64 (10.0.26200)

## Minimal reproduction

```python
import asyncio, time
from xstate_statemachine import SyncInterpreter, create_machine

CFG = {"id": "sy", "initial": "a", "states": {"a": {"after": {40: "b"}}, "b": {}}}

async def main():
    i = SyncInterpreter(create_machine(CFG))
    i.start()
    time.sleep(0.120)        # the 40 ms deadline is now unambiguously due
    i.tick()
    print(sorted(i.current_state_ids))   # -> ['sy.a']   (expected ['sy.b'])

asyncio.run(main())
```

The identical code on an off-loop thread prints `['sy.b']`.

Full script with the off-loop control: `repro/N-02_sync-timer-unreachable-in-loop.py`
(exits 1 while present, 0 once fixed).

## Observed

```
OBSERVED off-loop control  : clock.pending=1 states=['sy.a' -> 'sy.b']
OBSERVED in-running-loop   : clock.pending=0 states=['sy.a']
EXPECTED both              : clock.pending=1 before tick, states=['sy.b'] after
RESULT: DEFECT REPRODUCED
```

| construction context | `clock.pending` before `tick()` | state after `tick()` |
|---|---:|---|
| off-loop thread (control) | 1 | `{'sy.b'}` ✅ |
| inside a running loop | **0** | `{'sy.a'}` ❌ |

## Expected

A `SyncInterpreter`'s `after` deadline is delivered by `tick()` (or by the pump
at the top of `send()`, or by the macrostep loop) regardless of whether an
asyncio loop happens to be running on the constructing thread. The sync engine's
timing contract should depend on the engine, not on ambient context.

## Root cause

`clock.py`, `RealClock.set_timeout`:

```python
try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = None
if loop is not None:
    return loop.call_later(max(0.0, delay_sec), fn)   # asyncio lane
return self._heap.push(self.now() + max(0.0, delay_sec), fn, owner)
```

The branch is on ambient loop presence. `SyncInterpreter.tick()` →
`clock.pump()` drains only `self._heap`, so anything that went down the asyncio
lane is invisible to it.

Note that the clock already receives an `owner` argument on the heap path, so
the information needed to pick the correct lane is present — it is just not used
for the decision.

## Impact

- **Any async application that keeps one sync machine for a hot path.** Its
  timers are delivered only incidentally, on whatever loop turns happen to occur.
- **Any async test that constructs a sync machine** — which is the common case,
  since `pytest-asyncio` tests run inside a loop. A suite can be green while
  production behaviour differs, because the deadline that never fires under
  `tick()` does eventually fire via `call_later` once the loop turns enough
  times.

Partial mitigation, observed: the `call_later` callback still *enqueues* the
event, so a later `tick()` after enough loop turns does pick it up (probe cases
E7c/E7d pass for this reason). That makes the failure intermittent rather than
total, which is arguably worse — it is a timing-dependent bug that will present
as flakiness.

## Suggested fix

Preferred: **bind the lane at clock-attachment time, not at `set_timeout` time.**
The clock knows its owner; a clock owned by a `SyncInterpreter` should always use
the heap, and one owned by an `Interpreter` should always use the loop it is
bound to. This removes the ambient dependency entirely.

Acceptable alternative: have `SyncInterpreter.__init__` raise (or warn loudly)
when constructed inside a running loop with a `RealClock`, following this
release's own precedent of rejecting the ambiguous case rather than half-
supporting it. Document `SimulatedClock`, or a heap-only clock, as the supported
way to run a sync machine inside a loop.

## Acceptance criteria

- [ ] `repro/N-02_sync-timer-unreachable-in-loop.py` exits 0.
- [ ] A `SyncInterpreter` built inside a running loop shows `clock.pending == 1`
      for an armed `after`, and one `tick()` past the deadline moves it.
- [ ] `tick()` is authoritative: after it returns, no deadline that was due at
      entry remains undelivered, in either context.
- [ ] The off-loop behaviour is unchanged (no regression against #50 — still
      zero threads per timer).
- [ ] Tests added:
  - `tests/test_timer_scheduling.py::test_sync_after_fires_via_tick_inside_running_loop`
  - `tests/test_timer_scheduling.py::test_clock_lane_follows_owner_not_caller`
  - `tests/test_timer_scheduling.py::test_sync_timers_still_spawn_no_threads`

## Related

- `#50` (LC-38) — the thread-per-timer defect this replaces. Its core fix is
  genuine and verified; this is the new edge it introduced.
- `#48`, `#49` (LC-26, LC-27) — the timer lane and clock injection work.

## Verification

Independently verified on 2026-09-17.

- Library: 0.8.0, commit `9bf6065`, local clone, `pip install -e .`.
- Python 3.13.7, Windows 11 x64.
- Repro run in a fresh process → **exit 1**, output as quoted.
- Off-loop control (`threading.Thread`) fires correctly in the same process and
  the same run, so this is not a machine-wide timing artefact.
- Thread-count control: 25 sync machines with armed timers → +0 threads,
  confirming #50's own fix is intact and this is a distinct defect.


---
Found while re-verifying the 0.8.0 release against the adoption-readiness checklist in #26. Self-contained repro attached in the body; exits 1 while the defect is present, 0 once fixed.

