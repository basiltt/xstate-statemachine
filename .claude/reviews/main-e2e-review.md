# End-to-End Review — merged `main` @ v0.6.0

**Date:** 2026-08-10
**Scope:** merged `main` after PR #20 (SCXML correctness) and PR #21 (XState v5 parity)
**Outcome:** 9 defects found and fixed, shipped via PR #22. **Not published to PyPI** — held for documentation work.

---

## Why this review happened

PRs #20 and #21 were each reviewed in isolation. This pass reviewed the *merged*
result, because a merge can be clean at the text level and still be wrong at the
behavioural level: #20 introduced error containment for user actions, and #21
introduced built-in action creators that #20's containment had never seen.

That is exactly where the most serious finding came from.

---

## Findings

Severity uses the house scale. `Blocker` = must not ship.

| # | Severity | Area | Finding |
|---|----------|------|---------|
| 1 | **Blocker** | correctness | Built-in action failures tore down the async run loop |
| 2 | High | packaging | `Typing :: Typed` classifier was false — no `py.typed` shipped |
| 3 | High | correctness | Async engine rejected synchronous invoked services |
| 4 | High | correctness | Documented `MachineLogic` subclass style always raised |
| 5 | Medium | persistence | `systemId` registry was not persisted across snapshots |
| 6 | Medium | hygiene | Importing the CLI configured the host's **root** logger |
| 7 | Medium | validation | Malformed `tags` raised a raw `TypeError`; a dict was silently accepted |
| 8 | Medium | cli-ux | CLI printed literal `✅` on legacy Windows consoles |
| 9 | Low | docs | `interpreters.md` documented behaviour removed in 0.5.1 |

---

### 1 — Built-in action failures tore down the async run loop (Blocker)

PR #20 added error containment for user-supplied actions and documented the
contract in the README. PR #21 added built-in action creators whose dispatch
branch `continue`d *before* reaching that `try/except`.

Built-ins are not infallible — `assign` resolves a user-supplied callable, and
`spawnChild` resolves a user-supplied service. They raise for precisely the same
reasons user actions do.

The failure was silent. Because `send()` is fire-and-forget on the async engine,
a raising built-in killed `_run_event_loop` while callers still observed
`status == "running"`; every subsequent event was enqueued and dropped.
`SyncInterpreter` was unaffected, so the two engines disagreed.

Reproducible from **pure JSON config** — no user Python required:

```python
{"type": "xstate.raise", "params": {"event": None}}   # -> status "stopped"
```

**Fix:** the built-in dispatch moved inside the same containment as user actions,
so both share one policy. Verified on both engines.

### 2 — `py.typed` was missing

`pyproject.toml` advertised `Typing :: Typed` and the source is extensively
annotated, but no PEP 561 marker was in the wheel. Under PEP 561 a package
without the marker is treated as **entirely unannotated** regardless of inline
types, so downstream `mypy` reported `import-untyped` and resolved every public
symbol to `Any`.

This mattered on a release boundary specifically because PyPI artifacts are
immutable — the false claim would have been permanent for 0.6.0.

### 3 — Async engine rejected synchronous services

`invoke` awaited the service result unconditionally. A plain function `src`
therefore raised `TypeError` inside a task whose exception was never retrieved:
no traceback, no `onError`, and the machine sat in the invoking state forever.
`SyncInterpreter` accepted the identical config, so the same machine definition
worked on one engine and hung on the other.

### 4 — The documented `MachineLogic` subclass style always raised

`docs/_guide/actions.md`, `guards.md`, `context.md` and `docs/api/index.md` all
teach defining logic as methods on a `MachineLogic` subclass. Nothing ever
collected those methods, so **every published example of that style** died with
`ImplementationMissingError` on the first transition that used it.

**Fix:** methods are classified by arity — `(context, event)` is a guard,
`(interpreter, context, event)` a service, `(interpreter, context, event,
action)` an action. Underscore-prefixed methods are treated as private.

Explicitly passed dictionaries always win. Arity cannot be right for every
conceivable signature, so the constructor argument stays an escape hatch rather
than being silently overwritten — and registration happens in `__init__`, which
keeps `logic.actions/.guards/.services` the single source of truth no matter
which authoring style produced them.

### 5–9

- **`systemId` persistence:** the registry came back empty after a restore, so
  every `sendTo("sys", ...)` silently dropped its event. Now serialised as
  `systemId -> actorId` and rebound on restore.
- **Root logger:** `cli/__main__.py` called `logging.basicConfig()` at *module
  import*. Moved into `main()`. A library must never configure the root logger.
- **`tags` validation:** `set(raw_tags)` decided the outcome, so `tags: 123`
  surfaced as `'int' object is not iterable` naming no state, and
  `tags: {"a": 1}` was silently accepted as `{"a"}` by iterating the mapping's
  keys — a typo that produced working-looking nonsense. Both now raise
  `InvalidConfigError` naming the state.
- **CLI encoding:** `_safe_print` caught `UnicodeEncodeError`, which made it
  structurally blind to a stream built with `errors="backslashreplace"` — that
  configuration never raises and prints a literal `✅`. It now checks
  encodability up front, which additionally avoids a torn line (`print` can
  flush a prefix before the encoder reaches the offending character).
- **Stale docs:** `interpreters.md` still told users to wrap `.send()` in
  `try/except` to catch action exceptions. Containment landed in 0.5.1; the
  section now documents the real behaviour and shows how to model failure on
  `context`.

---

## Verification

- **2647 tests passing**, coverage **86.93%** (gate 86%).
- **19 regression tests** added, each asserting observable behaviour rather than
  absence of an exception.
- **Mutation-verified:** reverting the `MachineLogic` registration call and the
  `_safe_print` encodability check each killed their tests. This matters —
  earlier in this effort three tests were found that passed with their own fix
  reverted, so "test added" is not evidence on its own.
- CI green **12/12** (Python 3.9–3.14 × ubuntu/macos/windows, lint, coverage,
  distribution build).
- Wheel rebuilt and confirmed to contain `py.typed`.

## Repository state

- PRs #20, #21, #22 merged to `main`.
- Remote branches reduced to `main` + one unrelated feature branch. Every
  deleted branch was tagged `archive/*` and pushed first, so nothing is
  unrecoverable.

---

## Outstanding before release

**Not published to PyPI**, per instruction. Remaining work is documentation:

1. **No doc coverage** for these shipped v0.6.0 features: `sendTo`/`send_to`,
   `spawnChild`, `systemId`, `to_promise`, `wait_for`, `enqueueActions`,
   `pure_transition`. They are in the API reference by signature only — no
   guide, no worked example.
2. Consider a **migration note** for 0.5.x users covering the changed action
   error semantics, since that is the one behavioural change that could
   surprise an existing user.
3. `CHANGELOG.md` now records that **0.5.1 was never published**; its entries
   ship as part of 0.6.0.
