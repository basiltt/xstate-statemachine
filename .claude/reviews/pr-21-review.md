# PR Review: #21 — feat: XState v5 feature parity (v0.6.0)

**Reviewed**: 2026-08-08
**Author**: basiltt
**Branch**: `feat/xstate-v5-parity` → `main` (stacked on PR #20)
**Scope**: 16 files, +7,426/−100 relative to the PR #20 tip
**Decision**: **APPROVE** (17 findings confirmed, all fixed in-branch)

---

## Summary

Closes the 73 XState v5 gaps catalogued in `docs/FEATURE_GAP_ANALYSIS.md`. The
review was run adversarially across four dimensions — correctness, concurrency,
API compatibility, and maintainability/test-quality — with every finding
independently verified by running code against this branch, an `origin/main`
worktree, and the PR #20 tip for correct attribution.

**20 findings raised. 3 refuted on attribution. 17 confirmed and all 17 fixed.**

The most valuable outcome was not any single bug but the **mutation testing**:
it proved one of the new tests passed with its own fix reverted, and separately
surfaced that an earlier async fix had been silently lost during a file restore.

---

## Findings

### HIGH — all fixed in-branch

**1. Auto-discovery rejected every built-in action creator**
`logic_loader.py`

Built-ins were registered as required actions, so any machine using
`assign`/`raise`/`sendTo` raised `ImplementationMissingError` unless the caller
bypassed discovery with an explicit `logic=`. This made the PR's headline
feature unusable with the library's convention-over-configuration story.

**2. Auto-discovery required implementations for composite guards**
`logic_loader.py`

`and`/`or`/`not`/`stateIn` are interpreter-evaluated but were collected as user
guards, so discovery rejected every machine using higher-order guards. Guard
collection now recurses through composites and gathers only leaf predicates. A
genuinely missing leaf still fails loudly.

**3. CLI codegen emitted stubs that shadowed built-ins**
`cli/extractor.py`

The extractor collected every action `type`, so a machine using `assign` got a
generated `def assign(...)`. Because the interpreter resolves **user actions
before built-ins**, those stubs silently converted a working machine into a
no-op. Verified the generated machine now builds *and runs* with real built-ins.

**4. Async engine orphaned superseded delayed sends**
`interpreter.py`

Reusing a send id overwrote the registry entry without cancelling the earlier
task, so `cancel(id)` reached only the newest send. It also had a `finally` that
popped the **new** registration when an old task was cancelled.

**5. Machine-level `output` was parsed but never used**
`base_interpreter.py`, `sync_interpreter.py`

A machine declaring top-level `output` completed with `output is None`.

**6. A user guard named `and`/`or`/`not` was a hard parse error**
`models.py`

Any guard with one of those names was treated as a composite and rejected for
having no children — a regression against `main`, where the name worked. A bare
string is now always a user predicate; only the object form composes.

**7. Non-numeric named delay crashed startup**
`base_interpreter.py`

`float()` on a string or dict raised inside `_schedule_state_tasks` during
entry, taking the whole interpreter down at `start()`.

**8. Weak test — passed with its own fix reverted**
`tests/test_xstate_v5_parity.py`

`test_duplicate_send_id_supersedes_earlier_timer` asserted registry size, which
is 1 either way by dict semantics. Rewritten to use two *different* delays (the
superseded one longer, so an orphan outlives the cancel) and assert the
observable outcome. Verified to fail under the mutant.

### MEDIUM — fixed

**9. Transient selection bypassed the guard memo.** `always` used the legacy
`_find_optimal_transition`, so a guard on an ancestor shared by N regions was
evaluated N times per microstep — measured **8× for 3 regions**, now 2.

**10. `always` guards were missed by CLI extraction**, so generated code could
not build.

**11. Dead code.** `_find_optimal_transition` (98 lines, highest complexity in
the module) had no remaining callers. Removing it took `base_interpreter.py`
from 2,913 → 2,815 lines and *raised* coverage 86.19% → 86.74%.

### LOW — fixed

**12.** Eight unused imports in `base_interpreter.py` (pyflakes now clean).
**13.** The `--style` deprecation promised removal "in v0.6.0" — the release now
shipping with the flag still honoured. Now names v0.7.0.

### Refuted on attribution

Three findings reproduced but belong to `origin/main` or PR #20, not this PR.

---

## Validation Results

| Check | Result |
|---|---|
| Lint (flake8) | **Pass** |
| Format (black) | **Pass** |
| Tests | **Pass** — 2,612 passing |
| Coverage | **Pass** — 86.74% (gate 86%) |
| Python 3.9 AST compatibility | **Pass** |
| CI matrix (12 jobs, py3.9–3.14 × Linux/Win/macOS) | **12/12 Pass**, SHA-matched to tip |

---

## Accepted, not fixed — known follow-ups

These are real and were deliberately deferred rather than silently ignored:

1. **`base_interpreter.py` is 2,815 lines / 71 methods** against a global rule of
   <800. 15 functions exceed 50 *code* lines. The class is cohesive (it is the
   engine), but `actions`, `persistence` and `observation` are natural extraction
   seams. **Recommend a follow-up refactor PR** — doing it here would have mixed
   a large structural change into a feature PR.

2. **`_execute_builtin_action` is ~60% duplicated** between the two engines. The
   shared preamble could move to `BaseInterpreter`, leaving only delivery
   (asyncio tasks vs daemon threads) engine-specific.

3. **The Pythonic DSL cannot express 5 of the new features** (`tags`, `meta`,
   `description`, `output`, `history`). JSON and DSL authoring are now
   inconsistent. Worth closing before the DSL is advertised as equivalent.

4. **`stateIn` matches by id suffix**, so a partial id can be satisfied by an
   unrelated state with the same leaf name. Consistent with the library's
   existing target-resolution behaviour, so left as-is — but it is a sharp edge.

5. **One OS thread per pending delayed send** in `SyncInterpreter`, unbounded
   (200 sends → 200 threads). Fine for typical use; a shared scheduler would be
   the fix if anyone drives it hard.

---

## Files Reviewed

| File | Change |
|---|---|
| `src/xstate_statemachine/actions.py` | Added (526 lines) |
| `src/xstate_statemachine/helpers.py` | Added (403 lines) |
| `src/xstate_statemachine/base_interpreter.py` | Modified (major) |
| `src/xstate_statemachine/interpreter.py` | Modified |
| `src/xstate_statemachine/sync_interpreter.py` | Modified |
| `src/xstate_statemachine/models.py` | Modified |
| `src/xstate_statemachine/logic_loader.py` | Modified |
| `src/xstate_statemachine/machine_logic.py` | Modified |
| `src/xstate_statemachine/exceptions.py` | Modified |
| `src/xstate_statemachine/cli/extractor.py` | Modified |
| `src/xstate_statemachine/cli/args.py` | Modified |
| `src/xstate_statemachine/__init__.py` | Modified |
| `tests/test_xstate_v5_parity.py` | Added (157 tests) |
| `tests/test_models.py` | Modified |
| `CHANGELOG.md`, `README.md`, `AGENTS.md`, `docs/` | Modified |
| `pyproject.toml` | Modified (0.5.1 → 0.6.0) |
