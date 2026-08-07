# PR Review: #20 — fix: repair SCXML transition algorithm, align error handling, and add CI

**Reviewed**: 2026-08-07
**Author**: basiltt
**Branch**: `fix/scxml-algorithm-correctness` → `main`
**Scope**: 18 files, +2414/−137 (at review time)
**Decision**: **APPROVE** (after 3 blocking findings were fixed in-branch)

---

## Summary

A correctness release for the core SCXML transition algorithm plus the CI
pipeline that would have caught the original defects. The review was run
adversarially — 4 independent reviewers across correctness, error-handling,
compatibility and CI/test-quality, with every finding independently verified by
running code against both this branch and an `origin/main` worktree.

**11 findings raised. 3 were blocking (2 CRITICAL, 1 HIGH) and are now fixed
with regression tests. All fixes are mutation-verified.**

The two CRITICALs are notable because they were *introduced or unmasked by this
PR's own earlier commits* — precisely the class of defect a self-review is
prone to miss.

---

## Findings

### CRITICAL — fixed in-branch

**1. Sibling parallel regions annihilated by an in-region transition**
`src/xstate_statemachine/base_interpreter.py` — `_find_transition_domain`

An earlier commit discarded the target from the common-ancestor set when a
descendant targeted its own ancestor. For a region of a `parallel` state this
raised the domain to the parallel node, so `states_to_exit` swept up every
*sibling* region while the entry path re-entered only the targeted branch.
Siblings were exited and never restored — permanently dead, with no error.

```
before: ['m.P.A.a1', 'm.P.B.b1', 'm.P.C.c1']
send("RESTART")
after:  ['m.P.A.a1']            # B and C silently destroyed
send("NEXT")                    # no-op — regions are dead
```

*Fix*: domain steps to the target's parent; exit set scoped to the re-entered
branch via a shared `_compute_states_to_exit()`. Exiting the parallel state
entirely still exits all regions (explicitly tested).

**2. Phantom sibling leaf on deep entry**
`base_interpreter.py`, `sync_interpreter.py` — `_enter_states`

`_enter_states` descended into a compound's `initial` child unconditionally, in
addition to walking the explicit entry path. Targeting `B.b2` while
`B.initial == "b1"` activated **both** — an illegal SCXML configuration. The
phantom leaf then won the next selection pass, firing the wrong transition and
duplicating actions.

```
send("E")   -> leaves ['m.B.b1', 'm.B.b2']   # two live leaves, one region
send("X")   -> ['fromB1', 'fromB2']          # duplicate action execution
```

*Root-cause note*: this defect pre-dated the PR but was masked by the
`difference_update` that an earlier commit correctly removed. Removing the mask
made it observable, so it is fixed at the root rather than re-masked.

### HIGH — fixed in-branch

**3. External cancellation caused `stop()` to skip all cleanup**
`interpreter.py` — `_run_event_loop`

A `finally` clause forced `status = "stopped"` on the ordinary
`CancelledError` path. Cancellation is not always initiated by `stop()` — an
enclosing `TaskGroup`, supervisor, or timeout can cancel the loop task. The
premature status change made a subsequent `stop()` hit its idempotency guard
and return early, never cancelling invoked services or child actors.

Verified: invoked service kept ticking 4–5 times after `stop()`;
`task_manager.cancel_all()` calls were 0 on the PR vs 1 on `origin/main`.

*Fix*: `stop()` again owns the orderly-shutdown transition. The `BaseException`
handler still corrects bookkeeping on a genuine crash, and `is_running` stays
honest because it independently checks the loop task.

### MEDIUM — accepted with documentation

**4. Sync action exceptions no longer propagate**
This is the intended, documented behaviour change of the PR, but
`docs/_guide/interpreters.md` still shows a `try/except` example around
`send()` that no longer fires. → **follow-up: update that guide.**

**5. Faulty entry action leaves invariants unestablished**
`_execute_actions` returns on first error, so later entry actions never run
while the state is reported active. Confirmed **pre-existing in spirit** and an
inherent consequence of the documented "skip remaining actions" contract.
Accepted; the alternative (rolling back entry) is a larger design change.

**6. `_select_transitions` guard memoisation**
Verified correct — a shared ancestor's guard now evaluates exactly once.

### LOW — fixed or accepted

**7. `.plugins` contract mismatch** — `use()` accepted duck-typed plugins while
the new setter demanded `isinstance(PluginBase)`. **Fixed**: the setter now
checks structurally, and the getter returns a copy so `plugins.append(junk)`
cannot bypass validation.

**8. Guard `except Exception` swallows arity/config errors** — a wrong-arity
guard silently routes to the fallback. Accepted as the documented contract, but
the traceback *is* logged at `exception` level, so it is diagnosable.

**9. Over-claiming test docstring** — `TestTransitionSelectionUsesTrueDepth`
claimed to pin `depth` vs `len(state.id)`. Mutation testing proved it does not:
with per-leaf selection the two keys are provably equivalent (within any single
ancestor chain `len(id)` is monotonic with `depth`). **Fixed**: docstring now
states honestly that it pins the *observable contract*, and why `depth` is
retained (correct metric, insurance, perf).

### Refuted by verification

- **Actor wait helpers cross-pollute via `threading.enumerate()`** — the
  "leaks" all drain in 2–13 ms; no real leak.
- **`wait_until` return value ignored** — every call site is followed by a
  specific assertion, which is the documented contract.

---

## Validation Results

| Check | Result |
|---|---|
| Lint (flake8) | **Pass** |
| Format (black) | **Pass** |
| Tests | **Pass** — 2455 passed |
| Coverage | **Pass** — 86.79% (gate 86%) |
| Doctests | **Pass** |
| Build + wheel smoke test | **Pass** |
| CI matrix (12 jobs, py3.9–3.14 × Linux/Win/macOS) | **12/12 Pass** |
| Python 3.9 AST compatibility | **Pass** |

Mutation testing: reverting each of the 3 blocking fixes individually causes
the corresponding new test to fail. The tests genuinely pin the behaviour.

---

## Known follow-ups (not blocking)

1. **`docs/_guide/interpreters.md`** still documents the old propagate-on-error
   behaviour for `SyncInterpreter.send()`.
2. **Transient (`always`) transitions still use single-winner selection** —
   `_process_transient_transitions` calls `_find_optimal_transition`, so
   parallel regions with `always` transitions advance one at a time. Verified
   **pre-existing on `origin/main`** and out of scope here, but it is now the
   only inconsistency left between event-driven and eventless selection.
3. **Entry-action rollback semantics** (finding 5) deserve an explicit design
   decision before 0.6.0.

---

## Files Reviewed

| File | Change |
|---|---|
| `.github/workflows/ci.yml` | Added |
| `src/xstate_statemachine/base_interpreter.py` | Modified |
| `src/xstate_statemachine/interpreter.py` | Modified |
| `src/xstate_statemachine/sync_interpreter.py` | Modified |
| `src/xstate_statemachine/models.py` | Modified |
| `src/xstate_statemachine/logic_loader.py` | Modified |
| `src/xstate_statemachine/exceptions.py` | Modified |
| `src/xstate_statemachine/__init__.py` | Modified |
| `src/xstate_statemachine/cli/__main__.py` | Modified |
| `tests/test_scxml_correctness.py` | Added |
| `tests/test_public_api_surface.py` | Added |
| `tests/test_interpreter.py` | Modified |
| `tests/test_sync_interpreter.py` | Modified |
| `README.md`, `AGENTS.md`, `CHANGELOG.md`, `docs/_guide/getting-started.md` | Modified |
| `pyproject.toml` | Modified (0.5.0 → 0.5.1) |
