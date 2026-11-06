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

## Results (2026-11-06, 0.12.0, quiet re-run)

Python 3.14.6, Windows 11, Intel Core i7-11850H (laptop, on mains, otherwise idle),
`xstate-statemachine` 0.12.0 (editable install of this checkout -- the same library code as
the 2026-11-05 table below) in a clean venv next to the other libraries. Median of 7
repetitions, GC disabled, setup excluded. All six columns come from the **same session**;
compare across a row, not against an older table. Higher is better. **Bold** = fastest in
the row (two bold cells = within 3 % of each other, a tie within the run-to-run noise).
Reproduce with `python run.py`; raw numbers in `results.json`.

| Scenario | xsm (sync) | xsm (pure) | xsm (async) | transitions 0.9.3 | python-statemachine 3.2.1 | sismic 1.6.11 |
|:--|--:|--:|--:|--:|--:|--:|
| Flat toggle (ev/s) | 96,369 | 47,599 | — | **158,707** | 10,469 | 14,665 |
| Guard + action (ev/s) | 102,251 | 45,590 | — | **129,061** | 9,086 | 13,473 |
| 3-level nested (ev/s) | **39,178** | 22,502 | — | 9,557 | 4,102 | 5,670 |
| Parallel regions (ev/s) | **30,461** | — | — | 6,692 | 4,226 | 5,343 |
| Construction (machines/s) | **12,770** | — | — | 9,794 | 1,565 | 317 |
| 1,000 instances (inst/s) | **47,019** | — | — | 36,834 | 4,478 | 8,230 |
| Delayed transition (timers/s) | **9,564** | — | — | 81 | 4,257 | 6,447 |
| Native asyncio (ev/s) | — | — | 28,892 | **42,188** | 7,488 | — |

xstate-statemachine is fastest in **5 of the 8 rows**: every statechart scenario (nested
4.1x and parallel 4.6x the next library), construction (1.30x `transitions`), 1,000
instances (1.28x `transitions`) and delayed transitions (1.5x `sismic`, 118x `transitions`).
`transitions` keeps the flat toggle (1.65x) and native asyncio (1.46x), and -- back on its
side of the line -- guard + action (1.26x).

This is a re-measurement of the 2026-11-05 table on identical library code: three full
sessions on a quiet machine a day later, of which the table above is the one closest to the
three-run medians. Every cell came out higher than the day before (ours by 3-22 %, the other
libraries by 5-30 %), which is machine state, not code. The one row that changes hands is
**guard + action**: `transitions` measured 127,000-131,000 ev/s in all three sessions against
83,360 on 2026-11-05 (its own earlier tables had it at 106,000 and 139,000), so that 83,360
was a low sample and the "1.14x ahead" claim built on it does not hold -- `transitions` leads
that row by 1.11-1.28x across the three sessions (ours 102,000-115,000 ev/s). Every other
ratio held within the run-to-run noise: construction 1.29-1.45x and 1,000 instances
1.28-1.35x over `transitions`, nested 4.1-4.3x, parallel 4.5-4.6x, delayed transitions
1.5-1.7x `sismic` and 115-160x `transitions` (whose thread-based timers swing between 65 and
84 timers/s from run to run), and `transitions` 1.6-1.7x on the flat toggle and 1.46x on
native asyncio.

### Previous table (2026-11-05, 0.12.0)

Python 3.14.6, Windows 11, Intel Core i7-11850H (laptop, on mains, otherwise idle),
`xstate-statemachine` 0.12.0 (editable install of this checkout) in a clean venv next to the
other libraries. Median of 7 repetitions, GC disabled, setup excluded. All six columns come
from the **same session**; compare across a row, not against an older table. Higher is
better. **Bold** = fastest in the row (two bold cells = within 3 % of each other, a tie
within the run-to-run noise). Reproduce with `python run.py`; raw numbers in `results.json`.

| Scenario | xsm (sync) | xsm (pure) | xsm (async) | transitions 0.9.3 | python-statemachine 3.2.1 | sismic 1.6.11 |
|:--|--:|--:|--:|--:|--:|--:|
| Flat toggle (ev/s) | 80,960 | 39,531 | — | **139,176** | 8,251 | 11,916 |
| Guard + action (ev/s) | **94,903** | 34,594 | — | 83,360 | 8,053 | 11,810 |
| 3-level nested (ev/s) | **35,252** | 18,592 | — | 6,701 | 3,487 | 4,784 |
| Parallel regions (ev/s) | **26,411** | — | — | 5,707 | 3,291 | 4,392 |
| Construction (machines/s) | **12,659** | — | — | 8,716 | 1,226 | 250 |
| 1,000 instances (inst/s) | **45,640** | — | — | 34,974 | 2,680 | 6,294 |
| Delayed transition (timers/s) | **8,472** | — | — | 66 | 2,565 | 5,446 |
| Native asyncio (ev/s) | — | — | 24,836 | **35,157** | 6,355 | — |

xstate-statemachine is fastest in **6 of the 8 rows**: every statechart scenario (nested
5.3x and parallel 4.6x the next library), construction
(1.45x `transitions`), 1,000 instances (1.30x `transitions`) and
delayed transitions (1.6x `sismic`, 129x `transitions`), and -- new on this release --
guard + action (1.14x `transitions`). `transitions` keeps the flat toggle (1.72x) and native
asyncio (1.42x) -- see "Reading the table honestly" below.

Construction, the 1,000-instance row and guard + action are the ones that moved since 0.11.0
(guard + action went from 1.7x behind `transitions` to 1.14x ahead): `create_machine()`
is ~25 % cheaper and an interpreter starts ~20 % cheaper (one-pass key reads in the parser, the
validator consuming the parser's own list of targeted transitions instead of re-walking the
tree, discovery skipping its matching indexes for a chart that names no logic, memoised
callable-shape checks, a single clock pump per `send()` and a ~1.4 KB smaller idle
`SyncInterpreter`), with semantics unchanged. Those two rows are also the noisiest in the
suite on a laptop (their timed region is 20-40 ms, and `transitions`' own figures swing by
up to 60 % between runs): across 3 full quiet runs on this tree the construction ratio
(ours / `transitions`) was 1.31-1.48x and the 1,000-instance ratio 1.00-1.46x. Benchmark on an
idle machine, and read the instances row with that spread in mind: a lead in two of the three
runs and level in the third.

### Previous table (2026-10-11, 0.11.0 + the construction / send fast paths)

Python 3.14.6, Windows 11, Intel Core i7-11850H (laptop, on mains, freshly rebooted and
otherwise idle), `xstate-statemachine` 0.11.0 (editable install of this checkout) in a clean
venv next to the other libraries. Median of 7 repetitions, GC disabled, setup excluded. All
six columns come from the **same session**; compare across a row, not against an older
table. Higher is better. **Bold** = fastest in the row (two bold cells = a tie within the
run-to-run noise). Reproduce with `python run.py`; raw numbers in `results.json`.

| Scenario | xsm (sync) | xsm (pure) | xsm (async) | transitions 0.9.3 | python-statemachine 3.2.1 | sismic 1.6.14 |
|:--|--:|--:|--:|--:|--:|--:|
| Flat toggle (ev/s) | 71,210 | 39,038 | — | **124,773** | 7,365 | 12,153 |
| Guard + action (ev/s) | 61,777 | 35,518 | — | **105,978** | 6,410 | 10,935 |
| 3-level nested (ev/s) | **28,502** | 18,774 | — | 7,806 | 2,901 | 4,669 |
| Parallel regions (ev/s) | **25,349** | — | — | 5,654 | 2,537 | 4,333 |
| Construction (machines/s) | **8,684** | — | — | 7,649 | 854 | 220 |
| 1,000 instances (inst/s) | **33,213** | — | — | 30,215 | 2,221 | 7,109 |
| Delayed transition (timers/s) | **7,706** | — | — | 79 | 2,077 | 5,037 |
| Native asyncio (ev/s) | — | — | 23,609 | **30,926** | 5,355 | — |

A second full run immediately after agreed on every ratio (xsm / transitions: construction
1.14 then 1.05, 1,000 instances 1.10 then 1.06, nested 3.6x, parallel 4.4x).

### What changed since the 2026-10-02 table

`create_machine()` and a flat `send()` were profiled after construction slipped from a tie
to 6-9 % behind `transitions` on a loaded machine. The 0.8-0.11 validators had added
per-node work that the common case never needed: the unknown-key check sorted keys and
imported `difflib` for every state and transition even when every key was known; the
target validator formatted a label string for every transition and only read it on a
failure; the aliased-cycle guard did three thread-local lookups per child; tag/meta
validation ran for nodes declaring neither. On the event path the ancestor walk re-derived
the event's kind at every level, and a single-leaf machine paid for the parallel-region
selection (leaf filter, two sorts, de-dup, `max`). All of that is now behind a cheap check,
with semantics unchanged. Construction is ~20 % cheaper and a flat event ~15 %.

### Previous table (2026-10-02, 0.11.0, re-run in the #307 battle test)

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

- **`transitions` wins the flat rows and native asyncio:** the flat toggle by ~1.65x, guard +
  action by ~1.26x (1.11-1.28x across three quiet sessions) and native asyncio by ~1.46x. It
  is a transition table with method-name dispatch and no statechart algorithm: no
  configuration set, no entry/exit ordering, no history, no internal queue. When that is
  all you need, it is the fastest thing here.
- **xstate-statemachine wins every statechart scenario.** Nested: 4.1x `transitions`,
  6.9x `sismic`, 9.6x `python-statemachine`. Parallel: 4.6x the next best.
  Delayed transitions: ~118x `transitions` (whose `Timeout` extension arms an OS thread per
  state entry), 1.5x `sismic`.
- **Construction and 1,000 instances lead `transitions`.** 1.30x and 1.28x in the table
  above, 1.29-1.45x and 1.28-1.35x across 3 quiet sessions -- while we still run the full
  build-time validator on every `create_machine()`. Against the other two statechart
  libraries we are 6-40x faster on both rows.

### What this benchmark does not measure

Feature parity is the point of the comparison table in the README; this page only
measures speed on shapes every library can express. Snapshots, actors, invoked
services, `always` chains, strict mode and error policies have no counterpart in the
other libraries and are not benchmarked here. See `benchmarks/production_characteristics.py`
for our own per-process throughput budget and timer-lateness curves.
