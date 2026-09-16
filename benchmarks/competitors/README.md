# Cross-Library State-Machine Benchmarks

This directory benchmarks `xstate-statemachine` against three other Python
state-machine libraries: `transitions`, `python-statemachine`, and `sismic`.

## Fairness rules

- **Idiomatic API per library.** Each adapter uses the API a typical user of
  that library would reach for (e.g. `transitions` uses model-based
  `trigger()` calls, `python-statemachine` uses declared `State`/`transition`
  objects, `sismic` drives statecharts via `Interpreter.queue().execute()`).
  We do not contort a library into an unnatural shape just to make it look
  faster or slower.
- **Same logical machine shape per scenario.** Every adapter that supports a
  scenario builds an equivalent machine: same states, same guard/action
  semantics, same nesting depth, so the comparison is apples-to-apples.
- **Setup excluded from the timed region.** All adapters build their machine
  objects, models, and interpreters inside `setup_<scenario>()`. Only the
  returned `hot(n)` callable — the actual "drive n events" work — is timed
  (except **S5 construction**, whose hot function *is* the construction, by
  design, since S5 measures per-machine setup cost).
- **Warm-up, then median of repeated runs.** Each hot function is called once
  with a small `n` to prime interpreters/lazy caches before timing starts.
  Then it is run `R` times (default 7, `--quick` uses 3) and we report the
  **median** wall-clock time, which is robust to occasional OS/scheduler
  noise without needing to discard "outliers" by hand.
- **GC disabled during timing.** `gc.collect()` runs between repetitions and
  `gc.disable()` is held for the duration of each timed call, so garbage
  collector pauses don't leak into one library's numbers more than another's.
- **Unsupported scenarios are skipped, not faked.** If a library genuinely
  cannot express a scenario (e.g. `sismic` has no native asyncio dispatch
  path), its adapter returns `None` from `setup_<scenario>()` along with a
  one-line reason in `CAPABILITY_NOTES`, and the harness records that as
  "not implemented" rather than a synthetic zero or infinity.

## Scenarios

| ID | Description |
|----|-------------|
| S1 | Flat 2-state machine, N events alternating A/B |
| S2 | Flat machine with a guarded counter (guard + action per event) |
| S3 | 3-level hierarchical machine, events crossing branches (entry/exit chains) |
| S4 | Two orthogonal parallel regions toggling independently |
| S5 | Machine construction cost (build N machine objects from scratch) |
| S6 | 1,000 independent machine instances, one event each |
| S7 | Delayed/`after` transition (1 ms), repeated N times |
| S8 | Same as S1 but through the library's native asyncio dispatch path, if any |

N per scenario: S1–S4 and S8 use N=20,000 events; S5 uses N=200 machines;
S6 uses N=1,000 instances; S7 uses N=200 timers. `--quick` divides N by 10
and uses 3 repetitions instead of 7, for a fast smoke test.

## Adapter contract

Each file under `adapters/<lib>.py` exposes:

```python
LIB_NAME: str
LIB_VERSION: str
CAPABILITY_NOTES: dict[str, str]   # scenario id -> why it's unsupported / caveat

def setup_S1() -> Callable[[int], None]: ...
# ... setup_S2 .. setup_S8, only the ones the library can express
```

`run.py` discovers every module under `adapters/` dynamically via
`pkgutil.iter_modules`, so adapters can be added or edited independently
without touching the harness. A broken/unimportable adapter is reported as a
warning and skipped rather than crashing the whole run.

## Running

```bash
# Fast smoke test (small N, 3 reps) for one scenario:
python run.py --quick --scenario S1

# Full run, all libraries, all scenarios:
python run.py

# Just one library, all scenarios:
python run.py --lib xstate_sync

# A subset of scenarios across all libraries:
python run.py --scenario S1,S5,S7
```

Results are printed as a table to stdout and also written to
`results.json` (path overridable with `--out`), containing:

```json
{
  "python": "...",
  "platform": "...",
  "cpu": "...",
  "libs": {"xstate_sync": "0.7.0-dev", "...": "..."},
  "results": [
    {"lib": "xstate_sync", "scenario": "S1", "n": 20000,
     "median_s": 0.0123, "ops_per_s": 1626016.3, "note": ""}
  ]
}
```

`median_s`/`ops_per_s` are `null` and `note` explains why when a scenario is
unsupported for that library.

## Notes on timing methodology

Because measurements are timing-sensitive, the maintainer runs the full
(non-`--quick`) benchmark suite serially on a quiet machine to get the
authoritative numbers reported elsewhere (README, docs). This directory's
`--quick` mode exists purely to validate that adapters and the harness work
end-to-end; its numbers should not be treated as representative performance
figures.

## Results (2026-09-16)

Python 3.14.6, Windows 11, Intel Core i7-11850H (laptop, on mains, otherwise idle).
Median of 7 repetitions, GC disabled, setup excluded. Higher is better. **Bold** = fastest
in the row. Reproduce with `python run.py`; raw numbers in `results.json`.

| Scenario | xsm (sync) | xsm (pure) | xsm (async) | transitions 0.9.3 | python-statemachine 3.2.1 | sismic 1.6.11 |
|:--|--:|--:|--:|--:|--:|--:|
| Flat toggle (ev/s) | 24,514 | 15,841 | — | **98,196** | 9,575 | 10,965 |
| Guard + action (ev/s) | 28,987 | 17,958 | — | **77,860** | 7,604 | 10,009 |
| 3-level nested (ev/s) | **10,823** | 7,630 | — | 6,609 | 2,619 | 3,659 |
| Parallel regions (ev/s) | **18,817** | — | — | 4,891 | 2,721 | 4,595 |
| Construction (machines/s) | 5,592 | — | — | **7,357** | 866 | 182 |
| 1,000 instances (inst/s) | 11,988 | — | — | **23,765** | 2,817 | 5,781 |
| Delayed transition (timers/s) | **5,625** | — | — | 77 | 2,843 | 4,332 |
| Native asyncio (ev/s) | — | — | 13,636 | **34,739** | 5,389 | — |

### Reading the table honestly

- **`transitions` wins every flat scenario by 3-4x.** It is a transition table with
  method-name dispatch and no statechart algorithm: no configuration set, no
  entry/exit ordering, no history, no internal queue. When that is all you need, it is
  the fastest thing here and nothing in this library will catch it.
- **xstate-statemachine wins every statechart scenario.** As soon as the machine has
  depth (nested: 1.6x `transitions`, 3x `sismic`, 4x `python-statemachine`) or
  orthogonal regions (parallel: 3.8x the next best), the SCXML algorithm that costs us
  on flat machines is what the others have to emulate, and we pull ahead. `transitions`
  in particular drops from 98k to 6.6k ev/s the moment states nest -- a 15x cliff;
  ours drops 2.3x.
- **Delayed transitions are 70x faster than `transitions`** because `transitions`
  has no native timer -- its `Timeout` extension arms a `threading.Timer` (an OS thread) per state entry.
  We schedule on a `Clock` (here `SimulatedClock`, so the number is dispatch cost,
  not wall time). `sismic` and `python-statemachine` also have native timers and are
  in the same order of magnitude as us.
- **The pure API is slower than `SyncInterpreter`, not faster.** Each
  `get_next_snapshot()` call deep-copies context in and out to guarantee the caller's
  snapshot is untouched (#54). Use it for its purity in tests, not for throughput.
- **Async costs 45% versus sync** on the same machine (13.6k vs 24.5k ev/s). That is
  the price of `await send(wait=True)` per event: a Future, a queue put, a loop turn.
  Fire-and-forget `send()` with a final `wait_done()` would sit much closer to the sync
  number; this scenario deliberately measures the request/response shape.
- **Construction and instance fan-out**: `transitions` builds ~30% faster; we are
  6-30x faster than `python-statemachine` and `sismic`, both of which validate or
  parse (YAML) at construction.

### What this benchmark does not measure

Feature parity is the point of the comparison table in the README; this page only
measures speed on shapes every library can express. Snapshots, actors, invoked
services, `always` chains, strict mode and error policies have no counterpart in the
other libraries and are not benchmarked here. See `benchmarks/production_characteristics.py`
for our own per-process throughput budget and timer-lateness curves.
