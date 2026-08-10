---
title: "Changelog"
description: "Release history and what changed in each version."
---

# Changelog

All notable changes to XState-StateMachine for Python are documented here.

For the full changelog with commit history, see [CHANGELOG.md on GitHub](https://github.com/basiltt/xstate-statemachine/blob/main/CHANGELOG.md).

---

## [0.6.0] — unreleased *(Current)*

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
