## Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2025-07-16

### Added

- **CLI Tool**: Introduced a new command-line interface (CLI) tool for interacting with state machines, including commands for creating, validating, and running machines from JSON configurations. This enhances usability for developers and enables easier integration into scripts and CI/CD pipelines.
- **'after' Transition Support in SyncInterpreter**: Added support for timed 'after' transitions in the synchronous interpreter (`SyncInterpreter`). This allows for delayed transitions without requiring an asynchronous event loop, using blocking sleep mechanisms for simplicity in synchronous environments. Note: This feature is limited to deterministic, non-concurrent use cases and may block the main thread.

### Changed

- Updated the `SyncInterpreter` to handle delayed events synchronously, ensuring compatibility with basic timing requirements while maintaining the blocking execution model.
- Minor internal refactoring in the `SyncInterpreter` to accommodate the new 'after' logic, including updates to task scheduling and event processing loops.
- Removed special treatment for 'spawn_' actions in the logic loader (`LogicLoader`), now treating them as regular actions. This may require users to adjust bindings for actor spawning in configurations.

### Fixed

- Resolved potential re-entrancy issues in the synchronous event queue by adding safeguards during processing cycles.
- Improved error messages for unsupported asynchronous features in `SyncInterpreter` to provide clearer guidance on limitations.

## [0.3.1] - 2025‑07‑11
### Added
- **Extended Plugin Hooks**
  Introduced new lifecycle hooks in `PluginBase` for granular introspection:
  - `on_guard_evaluated`: Notifies when a guard condition is checked and its result.
  - `on_service_start`: Notifies when an invoked service begins execution.
  - `on_service_done`: Notifies when an invoked service completes successfully, including its result.
  - `on_service_error`: Notifies when an invoked service encounters an error, including the exception.

### Changed
- **Improved Event Handling Robustness**
  Refactored `send` methods in `Interpreter` and `SyncInterpreter` for more resilient event object preparation, resolving `TypeError` issues with pre-formed `Event` instances and improving compatibility with mock objects in testing.

---

## [0.3.0] - 2025‑07‑11
### Added
- **Dual Execution Engines**
  New **`SyncInterpreter`** (blocking) complements the existing async `Interpreter`, both inheriting from a shared `BaseInterpreter`.
- **State Snapshotting**
  `get_snapshot()` / `restore_from_snapshot()` enable one‑call persistence and time‑travel debugging.
- **Plugin Framework**
  Formal `PluginBase` with life‑cycle hooks (`on_event`, `on_state_enter`, …) for custom loggers, telemetry, persistence, etc.
- **Actor Spawning Contract**
  `spawn_*` helpers plus `ActorSpawningError` for type‑safe child‑machine creation.
- **Utility APIs**
  Helpers such as `get_state_by_id()`, `get_next_state()`, and public camel⇄snake converters.
- **Enhanced Logging**
  Emoji‑tagged, interpreter‑ID‑stamped logs with an automatic `NullHandler`.

### Changed
- **Interpreter Hierarchy Refactor** — core transition logic moved to `BaseInterpreter`; async & sync variants now thin wrappers.
- **Factory** `create_machine()` gains `mode="async" | "sync"` (default *async*).
- **TaskManager** rewrite with smarter cancellation graph.
- **Logger** pre‑configured; manual `NullHandler` boilerplate no longer needed.
- **LogicLoader** faster discovery and clearer error messages.

### Removed
- Internal, non‑public helpers (e.g. `_legacy_cancel_all`) pruned; _no public API removed_.

---

## [0.2.3] - 2025‑07‑08
### Changed
- **Packaging‑only bump** — version strings updated to `0.2.3`; library code identical to `0.2.2`.

---

## [0.2.2] - 2025‑07‑08
### Changed
- **Packaging‑only bump** — version strings updated to `0.2.2`; library code identical to `0.2.1`.

---

## [0.2.1] - 2025‑07‑08
### Added
- **Automatic Logic Discovery**
  Introduced `LogicLoader`, a singleton that auto‑registers action/guard/service functions from user modules.
- **Plug‑and‑Play Modules**
  `create_machine()` now accepts `logic_modules`, letting you wire logic without boilerplate.
- **Public Exports**
  `LogicLoader` and `ActionDefinition` exported at package root.

### Changed
- **Factory API Upgrade**
  Extended signature of `create_machine()`; richer type hints and early validation.
- **Structured Logging**
  Emoji‑tagged logs with machine context.
- **Internal Naming Helpers**
  Robust camel⇄snake converters exposed publicly.

---

## [0.1.0] - 2025‑07‑07 — _Initial release_
