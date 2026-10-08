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

## Results (2026-10-02, 0.11.0, re-run in the #307 battle test)

Python 3.14.6, Windows 11, Intel Core i7-11850H (laptop, on mains, otherwise idle),
`xstate-statemachine` 0.11.0 (editable install of this checkout) in a clean venv next to the
other libraries. Median of 7 repetitions, GC disabled, setup excluded. All six columns come
from the **same session**; compare across a row, not against an older table. Higher is
better. **Bold** = fastest in the row (two bold cells = a tie within the run-to-run noise).
Reproduce with `python run.py`; raw numbers in `results.json`.

| Scenario | xsm (sync) | xsm (pure) | xsm (async) | transitions 0.9.3 | python-statemachine 3.2.1 | sismic 1.6.11 |
|:--|--:|--:|--:|--:|--:|--:|
| Flat toggle (ev/s) | 77,354 | 45,354 | — | **165,649** | 11,413 | 15,630 |
| Guard + action (ev/s) | 66,677 | 41,982 | — | **139,134** | 9,877 | 14,545 |
| 3-level nested (ev/s) | **31,762** | 20,957 | — | 10,107 | 4,554 | 6,048 |
| Parallel regions (ev/s) | **26,960** | — | — | 7,166 | 4,602 | 5,692 |
| Construction (machines/s) | **9,600** | — | — | **9,850** | 1,802 | 349 |
| 1,000 instances (inst/s) | **43,836** | — | — | **44,658** | 4,730 | 9,096 |
| Delayed transition (timers/s) | **9,151** | — | — | 71 | 4,735 | 6,654 |
| Native asyncio (ev/s) | — | — | 27,581 | **45,177** | 8,215 | — |

### Reproduction check (2026-10-08, #286 battle)

Re-run with `python run.py` on the same laptop, same pinned versions (transitions 0.9.3,
python-statemachine 3.2.1, sismic 1.6.11, xstate-statemachine 0.11.0), but **not** idle:
other test suites were running. Every absolute figure came out 20-45 % lower, uniformly
across all libraries, so the table above is kept as the quiet-machine reference.
**Reproduce ratios, not absolutes:** the cross-library ratio in each row should hold within
±25 %. In that loaded run it did for every row except S6 (1,000 instances): ours / `transitions`
0.80 against 0.98 here, so read the S6 "tie" as "within 20 %". The orderings in "Reading
the table honestly" all held (flat: `transitions` ~2x ours; nested 3.1x, parallel 3.9x
`transitions`; delayed 82x `transitions`, 1.2x `sismic`).

### What the #307 audit changed

The 2026-09-19 table was not like-for-like in two rows; both adapters are fixed:

- **Parallel regions (S4) counted half the work for us.** `xstate_sync.setup_S4` sent ONE
  event per loop iteration (alternating `TOGGLE1`/`TOGGLE2`) while every other adapter sent
  two (`toggle1(); toggle2()`), and `ops_per_s` is `n / time`. Our S4 rate was therefore
  inflated exactly 2x and the published "7.5x the next best" was really ~3.8x.
- **3-level nested (S3) counted 1.5x the work for python-statemachine.** Its adapter routed
  each iteration through `A2` (three events) where every other adapter does two
  cross-branch events, understating its rate by 1.5x (3,302 -> 4,554 ev/s). Our "10.3x" over
  it is really ~7.0x.
- **Construction and 1,000 instances are a tie, not a win.** Six interleaved runs in both
  adapter orders on 0.11.0: S5 ratio (ours / `transitions`) 0.97-1.04, S6 0.98-1.06. The
  0.9.0 margin (1.16-1.25 / 1.12-1.19) did not survive the features added since.
- Every other row reproduced within 25 % of the 2026-09-19 figures (most within 10 %; the
  absolute xsm rows are 5-20 % lower on 0.11.0, the competitor rows within 5 %).

Fairness checks that passed: same guard count (S2: one guard + one action per event in every
adapter), same context (a single counter), same event count per iteration (after the fixes
above), every adapter warmed by `run.py` before timing, the same strict error policy
(`ignore_invalid_triggers=False` / no swallowed errors), and S7 uses each library's *native*
timer (`SimulatedClock` for us, python-statemachine's `delay=`, sismic's virtual clock,
`transitions`' thread-based `Timeout`) -- which is the honest comparison of what a user gets,
and is why `transitions` is two orders of magnitude behind there.

### Reading the table honestly

- **`transitions` wins the flat scenarios by ~2.1x** and native asyncio by ~1.6x. It is a
  transition table with method-name dispatch and no statechart algorithm: no
  configuration set, no entry/exit ordering, no history, no internal queue. When that is
  all you need, it is the fastest thing here.
- **xstate-statemachine wins every statechart scenario.** Nested: 3.1x `transitions`,
  5.3x `sismic`, 7.0x `python-statemachine`. Parallel: 3.8x the next best.
  Delayed transitions: ~129x `transitions` (whose `Timeout` extension arms an OS thread per
  state entry), 1.4x `sismic`. `transitions` drops from 166k to 10k ev/s the
  moment states nest -- a 16x cliff; ours drops 2.4x.
- **Construction and 1,000 instances are a tie with `transitions`** (see above), while we
  still run the full build-time validator on every `create_machine()`. Against the other two
  statechart libraries we are 5-27x faster on both rows.
- **The pure API is slower than `SyncInterpreter`, not faster.** Each
  `get_next_snapshot()` call deep-copies context in and out to guarantee the caller's
  snapshot is untouched (#54). Use it for its purity in tests, not for throughput.
- **Async costs ~64% versus sync** on the same machine (27.6k vs 77.4k ev/s). That is
  the price of `await send(wait=True)` per event: a Future, a queue put, a loop turn.
  Fire-and-forget `send()` with a final `wait_done()` sits much closer to the sync number;
  this scenario deliberately measures the request/response shape.

### What this benchmark does not measure

Feature parity is the point of the comparison table in the README; this page only
measures speed on shapes every library can express. Snapshots, actors, invoked
services, `always` chains, strict mode and error policies have no counterpart in the
other libraries and are not benchmarked here. See `benchmarks/production_characteristics.py`
for our own per-process throughput budget and timer-lateness curves.
