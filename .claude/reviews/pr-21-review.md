# PR Review: #21 — feat: XState v5 feature parity (v0.6.0)

**Reviewed**: 2026-08-08
**Author**: basiltt
**Branch**: `feat/xstate-v5-parity` → `main` (stacked on PR #20)
**Scope**: 25 files, +10,758/−228 (v0.6.0-only: 16 files, +7,426/−100)
**Decision**: **APPROVE** — all 19 confirmed findings fixed in-branch

---

## Summary

Closes the 73 XState v5 gaps catalogued in `docs/FEATURE_GAP_ANALYSIS.md`. The
review ran adversarially across four dimensions — correctness, concurrency, API
compatibility, and maintainability/test-quality — with every finding
independently verified by running code against this branch, an `origin/main`
worktree, and the PR #20 tip for correct attribution.

**22 findings raised → 19 confirmed, 3 refuted on attribution. All 19 fixed**,
each pinned by a regression test.

The most valuable outcome was not any single bug but the **mutation testing**:
it proved three of the new tests passed with their own fix reverted, and
separately surfaced that an earlier async fix had been silently lost during a
file restore.

---

## Findings

### HIGH — all fixed in-branch

**1. Auto-discovery rejected the entire new action vocabulary**
`logic_loader.py`

Built-in creators were collected as *required user actions*, so any machine
using `assign` / `raise` / `sendTo` raised `ImplementationMissingError` unless
the caller bypassed discovery with an explicit `logic=`. The headline
convention-over-configuration feature was unusable with the headline new
feature.

**2. Auto-discovery required implementations for composite guards**
`logic_loader.py`

`and` / `or` / `not` / `stateIn` are evaluated by the interpreter but were
collected as user guards, so every machine using higher-order guards was
rejected. Collection now recurses through composites and gathers only the leaf
predicates. A genuinely missing leaf still fails loudly.

**3. Named-delay callables only accepted one calling convention**
`base_interpreter.py`

Everything else in this release — action/guard `params`, `output`, inline
`delay` — passes a single `{context, event}` mapping. A named delay written
that way raised `TypeError` inside `_schedule_state_tasks` and **killed
startup**. Both conventions are now accepted; a raising callable disables that
one timer rather than the machine.

**4. Async engine orphaned superseded delayed sends**
`interpreter.py`

Reusing a send id overwrote the registry entry without cancelling the earlier
task, so `cancel(id)` reached only the newest send and the first fired anyway.
A `finally` also popped the *new* registration when an old task was cancelled,
leaving the live send uncancellable.

**5. CLI codegen shadowed real built-ins with stubs**
`cli/extractor.py`

The extractor collected every action `type`, so codegen emitted
`def assign(...)` / `def log(...)`. Because the interpreter resolves **user
actions before built-ins**, those stubs silently shadowed real behaviour and
turned a working machine into a no-op with no error.

**6. Machine-level `output` was parsed but never used**
`base_interpreter.py`, `sync_interpreter.py`

A machine declaring a top-level `output` completed with
`interpreter.output is None`.

**7. A user guard named `and` / `or` / `not` was a hard parse error**
`models.py`

Any guard with one of those names was parsed as a composite and rejected for
having no children — a regression against `main`. A **bare string** guard is
now always a user predicate; only the object form declares composition.

### MEDIUM — all fixed in-branch

**8. User-registered `stateIn` silently bypassed.** The built-in was consulted
unconditionally, so the user's predicate was never called and the transition
was decided by the built-in state test — a silent behaviour swap.

**9. `always` transitions were skipped by CLI extraction**, so a guard used
only by an eventless transition was omitted and the generated machine could
not be built.

**10. Transient selection used the un-memoised legacy path.** A guard on an
ancestor shared by N parallel regions was evaluated N times per microstep —
measured **8× for 3 regions**, now 2 (one per microstep, which is correct).

**11. Cancelled sends leaked a `threading.Event`** until the *original* delay
elapsed. Twenty schedule/cancel cycles against a 5s delay held 20 live Events.

### Test quality — three mutation survivors

Tests that passed with their own fix reverted (i.e. pinned nothing):

| Test | Problem | Fix |
|---|---|---|
| `test_duplicate_send_id_supersedes_earlier_timer` | Asserted registry size, which is 1 either way by dict semantics | Two *different* delays, superseded one longer, asserts observable outcome |
| `test_max_iterations_breaks_infinite_loop` | Asserted only that the loop terminated — true for the hardcoded default too | Counts guard evaluations (10 at `maxIterations=5` vs 2000 at 1000) |
| spawnChild `input` / async `stopChild` deregistration | Untested entirely | Added on both engines |

All three now **verified to fail** under their respective mutants.

### LOW — fixed

- Eight unused imports in `base_interpreter.py` (pyflakes now clean).
- `--style` deprecation promised removal "in v0.6.0" — the release now
  shipping *with the flag still honoured*. Retargeted to v0.7.0.
- Dead `_find_optimal_transition` (98 lines, highest-complexity function in
  the module) removed; coverage rose 86.19% → 86.74% as a result.

### Refuted by verification

- CLI extraction gap attributed to PR #21 — the traversal limitation
  pre-exists on `main`.
- `_find_optimal_transition` "duplication" framed as a PR #21 defect — the
  duplication was real but pre-existing; removed anyway.
- A numeric claim that reproduced but was mis-attributed to this PR.

---

## Validation Results

| Check | Result |
|---|---|
| Lint (flake8) | **Pass** |
| Format (black, 79 cols) | **Pass** |
| Tests | **Pass** — 2,621 passed |
| Coverage | **Pass** — 86.86% (gate 86%) |
| Python 3.9 AST compatibility | **Pass** |
| CI matrix (12 jobs, py3.9–3.14 × Linux/Win/macOS) | **12/12 Pass** on tip `8535a408` |
| Generated CLI code builds and runs | **Pass** |

---

## Accepted with comment (not blocking)

**`base_interpreter.py` is 2,815 lines with a 72-method class**, against a
global guideline of 800. 15 functions exceed 50 *code* lines (38 by raw line
count, but most of that is docstrings). This is real debt, but splitting a
correctness-critical engine mid-release is riskier than the debt itself. The
natural seams are visible: built-in action dispatch, the actor system, and
persistence are each cohesive enough to move to their own module.

**`_execute_builtin_action` is ~60% duplicated between the two engines.** The
shared preamble could move to `BaseInterpreter`, leaving only delivery
(asyncio tasks vs daemon threads) engine-specific.

**The Pythonic DSL cannot express `tags`, `meta`, `description`, `output` or
`history`.** The two authoring surfaces have diverged: JSON now supports the
full v5 vocabulary, the DSL does not.

**Sync `_deliver` spawns one unbounded daemon thread per delayed send**
(~34 KB stack each). 200 pending sends = 200 threads. Acceptable for typical
use; a shared scheduler would be the fix if this ever matters.

---

## Files Reviewed

| File | Change |
|---|---|
| `src/xstate_statemachine/actions.py` | Added (526) |
| `src/xstate_statemachine/helpers.py` | Added (403) |
| `src/xstate_statemachine/base_interpreter.py` | Modified (+1,476) |
| `src/xstate_statemachine/sync_interpreter.py` | Modified (+390) |
| `src/xstate_statemachine/interpreter.py` | Modified (+298) |
| `src/xstate_statemachine/models.py` | Modified (+323) |
| `src/xstate_statemachine/logic_loader.py` | Modified |
| `src/xstate_statemachine/cli/extractor.py` | Modified |
| `src/xstate_statemachine/{__init__,exceptions,machine_logic,cli/args}.py` | Modified |
| `tests/test_xstate_v5_parity.py` | Added (166 tests) |
| `CHANGELOG.md`, `README.md`, `AGENTS.md`, `docs/` | Modified |
