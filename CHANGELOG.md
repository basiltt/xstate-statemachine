# Changelog
All notable changes to **xstate_statemachine** will be documented in this file.

_This project adheres to [Semantic Versioning](https://semver.org) and the format follows [Keep a Changelog](https://keepachangelog.com)._

---

## [0.3.0] - 2025‑07‑11
### Added
- **Dual Execution Engines**
  New **`SyncInterpreter`** (blocking) complements the existing async `Interpreter`, both inheriting from a shared `BaseInterpreter`.
- **State Snapshotting**
  `get_snapshot()` / `restore_from_snapshot()` enable one‑call persistence and time‑travel debugging.
- **Plugin Framework**
  Formal `PluginBase` with life‑cycle hooks (`on_event`, `on_state_enter`, …) for custom loggers, telemetry, persistence, etc.
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
