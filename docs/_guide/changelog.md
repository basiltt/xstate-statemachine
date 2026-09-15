---
title: "Changelog"
description: "Release history and what changed in each version."
---

# Changelog

All notable changes to XState-StateMachine for Python are documented here.

For the full changelog with commit history, see [CHANGELOG.md on GitHub](https://github.com/basiltt/xstate-statemachine/blob/main/CHANGELOG.md).

---

## [Unreleased] — Adoption-readiness, part 1

A production adoption audit ([#26](https://github.com/basiltt/xstate-statemachine/issues/26))
filed 34 defects against 0.7.0 with a common theme: the library fails
*silently* by default. This batch closes the blockers and top priorities.
Every new behavior is a per-machine policy whose default preserves 0.7.x
semantics, so nothing changes on upgrade until you opt in.

### Added

- **`actionErrorPolicy: "continue" | "rollback" | "fail"`** — an action that
  raises no longer silently commits a half-built transition. `rollback`
  restores configuration and context; `fail` also stops with
  `TransitionFailedError`. New `on_transition_failed` hook and
  `interpreter.last_transition_ok`. Covers `entry`, `exit`, transition and
  action-only handlers alike. Default (`"continue"`) emits a one-shot
  `DeprecationWarning`; flips to `rollback` in 1.0.
- **`onUnhandled: "ignore" | "defer" | "error"`** — `"defer"` replays
  unhandled events at the head of the queue, survives snapshots, and is
  bounded by `DEFER_MAX`. New `on_unhandled_event` hook and
  `UnhandledEventError`.
- **`guardErrorPolicy: "false" | "true" | "raise"`** — a raising guard is now
  observable via `on_guard_error` before the substituted result is reported.
- **Build-time validation** — `create_machine()` rejects unresolvable
  transition targets and non-progressing `always` self-targets in one
  message. `strict_targets=False` downgrades target failures to a
  `DeprecationWarning` (removed in 1.0).
- **`strictTargets: true`** machine config disables the sibling fallback for
  `.child` targets.
- **`Interpreter.send_threadsafe()`** for delivering events from another
  thread; `send()` from a foreign thread now raises `WrongThreadError`.
- **Error-observability hooks** on `PluginBase`: `on_transition_failed`,
  `on_guard_error`, `on_unhandled_event`, `on_error`, `on_done`, all
  implemented by `LoggingInspector`.
- **Built-in action param validation** — `raise`, `sendTo`, `cancel`,
  `stopChild`, … fail at build time when a required key is missing, with a
  hint if it was placed at the top level instead of under `params`.
- New exceptions: `UnhandledEventError`, `TransitionFailedError`,
  `WrongThreadError`.
- **`interpreter.value`** — the active configuration in hierarchical form
  (a string for atomic, `{parent: child}` for compound, one key per region
  for parallel, `{}` before `start()`). `matches()` now also accepts a
  partial `value` dict.
- **Snapshot envelope v1** — persisted snapshots gain `version`,
  `machine_id`, `machine_hash`, and `taken_at`. `from_snapshot` refuses a
  newer `version` with `SnapshotVersionError` and a mismatched id or hash
  with `SnapshotDriftError`; `verify_machine_hash=False` opts out after a
  migration. Unversioned 0.7.x payloads restore unchanged. New
  `persistence` module owns the format contract.
- **Inbox durability** — `interpreter.pending_events`, `drain_pending()`,
  and `stop(drain=True)` (with `timeout=` on the async engine). Snapshots
  now carry `pending_events`, restored recursively for child actors too.
- **`invoke.input` may be a callable** — resolved per spawn via
  `InvokeDefinition.resolve_input()`, deep-copied, and forwarded to a
  child machine as its creation `input` (previously never forwarded at
  all for machine invokes).
- **`Interpreter.wait_done()`** — a future resolved the instant the
  machine reaches `"done"`/`"error"`, replacing a 5&nbsp;ms poll loop.
- **`spawnBlockingTimeout`** machine config key bounds how long
  `spawn_blocking_<key>` waits for the child.
- **Production Characteristics guide** — measured numbers for
  per-process throughput, `after` timer lateness under load, and the
  `SyncInterpreter` threading contract.

### Fixed

- `.child` targets resolve into the **source's** descendants, matching
  XState v5; the 0.7.x sibling reading is kept as a fallback.
- `internal: false` is honored as `reenter: true` instead of being silently
  dropped.
- `sendTo` can address an invoke by its explicit `id` and by `systemId`.
- `from_snapshot` deep-copies the persisted context and merges it over the
  machine's defaults instead of aliasing the caller's dict.
- `@action` / `@guard` / `@service` markers win over arity-based
  auto-registration in `MachineLogic` subclasses.
- Runtime target resolution no longer falls back to a whole-tree search by
  last id segment — a bare `target: "someState"` is strictly a sibling,
  `#id`, `.child`, or exact top-level key; both engines share one resolver.
- `spawn_blocking_<key>` on the async `Interpreter` now actually blocks the
  parent until the child reaches a terminal status (it previously ran
  non-blocking).
- The pure API caches one probe per machine instead of rebuilding one per
  call, cutting the cost of `transition()` / `get_next_snapshot()` by
  roughly 3x; semantics are unchanged.

### Changed

- Per-event `INFO` log calls on the hot path are now `DEBUG`.
- Reaching a top-level final state now tears down immediately — child
  actors are stopped, `after` timers and invoked services cancelled, and
  the machine's actor-system registration removed — instead of waiting
  for a later `stop()` call. `status`, `output`, `error`, and `context`
  are retained; `stop()` on an already-done machine is a quiet no-op.

For full details, see the [`[Unreleased]` section of CHANGELOG.md](https://github.com/basiltt/xstate-statemachine/blob/main/CHANGELOG.md#unreleased).

---

## [0.7.0] — 2026-08-12 *(Current Release)*

**The code generator rewrite.** Three of the five templates — every
`pythonic-*` one — produced machines that did not match their source JSON,
on inputs as simple as a two-state machine. Two failed *silently*, exit code 0.

Round-trip fidelity across the 104-machine real-world corpus went from
**0/104 to 103/104** for all three. The one exclusion has no `states` key and
is rejected by `create_machine()` too.

**If you generated code with `pythonic-class`, `pythonic-builder` or
`pythonic-functional` on 0.6.0 or earlier, regenerate it.** Run
`xsm generate-template <file.json> --template <id> --diff` to see what changes.

### Fixed

- `pythonic-functional` produced machines with **zero transitions** — every
  machine it ever generated could start but never move. `State.to()` returns a
  `Transition`; emitting it as a bare expression discarded it.
- `pythonic-builder` **silently dropped every nested state**, so the generated
  code ran as a different machine.
- `pythonic-class` failed outright with `Multiple initial states`.
- Colliding names (`"my-state"` / `"my_state"`) collapsed into one variable,
  destroying a state.
- `final`, `after`, `always`, `parallel`, `history`, `tags` and `meta` were
  dropped by all three templates.
- Composite guards (`and` / `or` / `not`) were never extracted, so leaf guards
  were never stubbed and machines died with `ImplementationMissingError`.
- Named delays (`after: {"BACKOFF": …}`) were never collected.
- Python keywords and non-ASCII names produced invalid Python.

### Added

- **Round-trip verification.** Generated code is compiled, executed, and
  compared structurally against `create_machine(source_json)` *before* anything
  is written. A mismatch prints what diverged and exits 1.
- **`--check` / `--diff`** — exit 1 when on-disk files differ from what would be
  generated. Makes generated code safe to commit.
- **Provenance header** — source JSON, template, version, regeneration command.
- **Support matrix** in `xsm list-templates`.
- `State(history=…)`, `State(tags=…)`, `State(meta=…)`,
  `build_machine(root=…)` and `MachineBuilder.root()` — machine-level `on`,
  `entry`, `exit`, `tags` and `type: parallel` were previously unrepresentable.

### Changed

- Generated code passes `black --check` and `pyflakes` cleanly.
- Runners now demo a **reachable** event path instead of alphabetical order.
- Removed the `await asyncio.sleep(0.1)` placeholder from async action stubs.
- The Pythonic API no longer raises where the JSON engine merely warns: a
  compound state with no `initial`, and a `final` state with outgoing
  transitions, are now accepted with a warning.

---

## [0.6.0] — 2026-08-10

### Added

- **XState v5 feature parity** — every gap in `docs/FEATURE_GAP_ANALYSIS.md` closed.
- **Built-in action creators** — `assign`, `log`, `raise_`, `send_to`,
  `send_parent`, `choose`, `pure`, `enqueue_actions`, `spawn_child`,
  `stop_child`, `cancel`, `emit`, `escalate`, `forward_to`.
  See [Actions](../actions/#built-in-action-creators-v060).
- **Actor system** — `spawnChild`, `sendTo`, `systemId` registry addressable
  from any actor, and `systemId` persistence across snapshots.
  See [Actor Model](../actors/#built-in-actor-actions-v060).
- **Pure API** — `initial_transition`, `pure_transition`, `get_next_snapshot`
  and `PureSnapshot` compute transitions with no side effects.
- **Waiting helpers** — `wait_for`, `wait_for_sync`, `to_promise`.
  See [Testing & The Pure API](../testing-and-pure-api/).
- **Composite guards** — `and` / `or` / `not` and `stateIn`.
- **Named delays**, state `tags`, `meta`, and machine `output`.
- **PEP 561** — `py.typed` is now shipped, so inline annotations reach mypy.

### Fixed

Repairs to the SCXML transition algorithm and a family of correctness defects
found by an adversarial battle test. Highlights:

- **Transitions are atomic.** A raising action previously left the machine with
  *zero* active states while still reporting `running`.
- **The async run loop survives per-event errors** instead of dying silently and
  dropping every later event.
- **Deep history into a parallel state** no longer activates two leaves in one
  region.
- **Invoked child machines** fire `onDone` only on a real top-level final state,
  `onError` on failure, and are always torn down (previously leaked).
- **Runaway `raise` chains are bounded** on both engines.
- **Entry/exit actions receive the real triggering event** on `SyncInterpreter`
  (previously a synthetic event with an empty payload).
- Custom state `id` now resolves `#myId` targets; plugin errors are contained;
  malformed configs raise actionable `InvalidConfigError`.

### Changed *(behavioural — see the [migration notes](../getting-started/#upgrading-from-older-versions))*

- Action errors are **contained**; `.send()` no longer re-raises them.
- `start()` on a **stopped** interpreter raises instead of silently no-opping.
- A state key containing `.` whose first segment is also a sibling is rejected.

---

## [0.5.0] — 2026-03-23

### Added

- **Pythonic API** — three new styles for defining state machines in pure Python:
  - `StateMachine` base class with metaclass (class-based declarative API)
  - `MachineBuilder` fluent builder API
  - `build_machine()` functional API with `State` objects
- **`@action`, `@guard`, `@service` decorators** for marking functions with automatic name mapping (snake_case to camelCase)
- **`State.to()` transition API** with `|` operator for combining transitions
- **`State.internal()` method** for internal transitions (no state change)
- **`State.enter()` / `State.exit()` decorators** for entry/exit action registration
- **CLI `--template` flag** with 5 code generation templates:
  - `pythonic-class` — `StateMachine` subclass
  - `pythonic-builder` — `MachineBuilder` chain
  - `pythonic-functional` — `build_machine()` call
  - `class-json` — class-based with JSON at runtime *(default)*
  - `function-json` — module functions with JSON at runtime
- **Strategy pattern architecture** for CLI code generation (easily extensible)
- **Rich generated code** with type hints, docstrings, error handling (try/except), and logging
- **143 Pythonic API tests** across 20 test classes
- **Stress test suite** with 50 real-world XState machine configs
- **Comprehensive documentation** overhaul (25 guide pages)

### Changed

- `_resolve_target()` signature updated with context-aware resolution for nested states
- Generated code now uses PEP 8 snake_case function names with auto-mapping to camelCase
- Template selection replaces the old `--style` flag
- Default async mode is template-dependent: sync for Pythonic templates, async for JSON templates

### Fixed

- Nested state target resolution when using dot-path references
- State/event name collision in generated code (event variables now get `_event` suffix)
- Empty actions list emission in generated transition code
- Conditional `service` decorator import (only imported when services exist)
- Function complexity compliance (flake8 C901) in generator code
- Windows console encoding errors with emoji characters in CLI output

### Deprecated

- `--style` flag (`class` / `function`) — use `--template` instead. Maps to `class-json` / `function-json`. Will be removed in v0.6.0.

---

## [0.4.3] — 2025-02-03

- Python 3.14 support
- Build system migration to `uv`

## [0.4.2] — 2025-08-13

- `reenter` flag for self-transitions (forces exit/re-entry)

## [0.4.1] — 2025-07-27

- Enhanced sync actor spawning in `SyncInterpreter`
- Hierarchical machine generation in CLI (`--json-parent`, `--json-child`)
- CLI subcommand aliases (`gt` for `generate-template`)

## [0.4.0] — 2025-07-16

- CLI tool introduction (`xsm generate-template`)
- `after` transition support in `SyncInterpreter`

## [0.3.x]

- Plugin framework (`PluginBase`, `LoggingInspector`)
- Snapshot system (save/restore interpreter state)
- Actor spawning (`invoke` with machine sources)
- Dual execution engines (`Interpreter` + `SyncInterpreter`)

## [0.2.x]

- `LogicLoader` with auto-discovery (snake_case → camelCase mapping)
- `logic_providers` and `logic_modules` support in `create_machine()`
- PyPI packaging and distribution

## [0.1.0]

- Initial release
- XState JSON parsing and validation
- Async interpreter with full statechart support
- Hierarchical states, parallel states, final states
- Guards, actions, services
- `after` (delayed) and `always` (eventless) transitions
