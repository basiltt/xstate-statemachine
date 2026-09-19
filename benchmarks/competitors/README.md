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

## Results (2026-09-19, 0.8.1 after the construction/instance work)

Python 3.14.6, Windows 11, Intel Core i7-11850H (laptop, on mains, otherwise idle),
`xstate-statemachine` 0.8.1 (pre-release wheel built from `main` @ `816600c`) installed in
a clean venv next to the other libraries. Median of 7 repetitions, GC disabled, setup
excluded. All six columns come from the **same session**; compare across a row, not
against an older table. Higher is better. **Bold** = fastest in the row. Reproduce with
`python run.py`; raw numbers in `results.json`.

| Scenario | xsm (sync) | xsm (pure) | xsm (async) | transitions 0.9.3 | python-statemachine 3.2.1 | sismic 1.6.11 |
|:--|--:|--:|--:|--:|--:|--:|
| Flat toggle (ev/s) | 82,562 | 48,333 | — | **173,287** | 11,850 | 16,155 |
| Guard + action (ev/s) | 75,926 | 44,136 | — | **146,365** | 10,170 | 14,978 |
| 3-level nested (ev/s) | **34,023** | 22,583 | — | 10,485 | 3,302 | 6,248 |
| Parallel regions (ev/s) | **56,239** | — | — | 7,468 | 4,751 | 5,930 |
| Construction (machines/s) | **12,442** | — | — | 10,475 | 1,813 | 362 |
| 1,000 instances (inst/s) | **51,923** | — | — | 47,326 | 4,852 | 9,307 |
| Delayed transition (timers/s) | **11,609** | — | — | 72 | 4,664 | 6,805 |
| Native asyncio (ev/s) | — | — | 32,107 | **47,620** | 8,339 | — |

### Reading the table honestly

- **`transitions` wins the flat scenarios by ~2.1x** and native asyncio by ~1.5x. It is a
  transition table with method-name dispatch and no statechart algorithm: no
  configuration set, no entry/exit ordering, no history, no internal queue. When that is
  all you need, it is the fastest thing here.
- **xstate-statemachine wins every statechart scenario.** Nested: 3.2x `transitions`,
  5.4x `sismic`, 10.3x `python-statemachine`. Parallel: 7.5x the next best.
  Delayed transitions: ~162x `transitions` (whose `Timeout` extension arms an OS thread per
  state entry), 1.7x `sismic`. `transitions` drops from 173k to 10.5k ev/s the
  moment states nest -- a 17x cliff; ours drops 2.4x.
- **Construction and 1,000 instances are now ours** (1.19x and 1.10x `transitions`),
  and -- unlike the earlier coin-flip -- by a margin that survives the harness noise: six
  interleaved runs in both adapter orders never once had `transitions` ahead (S5 ratio
  1.16-1.25, S6 1.12-1.19). What changed: a single-pass parser with no post-parse tree
  walks, `__slots__` on the interpreters (1.6 KB -> 400 B per instance), a lazy deadline
  lock, no init `on_transition` record when no plugin is attached, and no task
  schedule/cancel for states that declare neither `after` nor `invoke`. We still run the
  full build-time validator on every `create_machine()`. Against the other two
  statechart libraries we are 5-35x faster on both rows.
- **The pure API is slower than `SyncInterpreter`, not faster.** Each
  `get_next_snapshot()` call deep-copies context in and out to guarantee the caller's
  snapshot is untouched (#54). Use it for its purity in tests, not for throughput.
- **Async costs ~61% versus sync** on the same machine (32.1k vs 82.6k ev/s). That is
  the price of `await send(wait=True)` per event: a Future, a queue put, a loop turn.
  Fire-and-forget `send()` with a final `wait_done()` sits much closer to the sync number;
  this scenario deliberately measures the request/response shape.

### What this benchmark does not measure

Feature parity is the point of the comparison table in the README; this page only
measures speed on shapes every library can express. Snapshots, actors, invoked
services, `always` chains, strict mode and error policies have no counterpart in the
other libraries and are not benchmarked here. See `benchmarks/production_characteristics.py`
for our own per-process throughput budget and timer-lateness curves.
