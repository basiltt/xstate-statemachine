## Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

Defects found by an adversarial battle test of v0.6.0 before release. None
reached PyPI. Six were release blockers.

**Transition atomicity.** `exit -> actions -> enter` had no rollback, so a
raising action left the source exited and the target never entered:
`current_state_ids == set()` while `status` still read `"running"`. The machine
was permanently dead *and* reporting itself healthy, so a supervisor watching
`is_running` would never restart it. Both engines now roll back and re-raise.

**Async run loop no longer dies silently.** Any per-event error — an
unresolvable target, a missing action, a raising guard — killed the loop and
flipped `status` to `"stopped"`. Because `send()` is fire-and-forget the caller
was never told, so the machine silently dropped every later event, while
`SyncInterpreter` raised and kept running. Per-event errors are now contained.

**Runaway `raise` storms are bounded.** `maxIterations` guarded only the
eventless (`always`) path, so an action raising its own trigger event hung
forever. On the async engine the whole `asyncio` loop starved — a task
scheduled every 50 ms ran zero times in four seconds, freezing every other
coroutine in the process.

**Deep history into a parallel state.** Restoring activated *two* leaves in one
region, which SCXML forbids and which breaks the one-state-per-region invariant
the library rests on.

**Invoked child machines.** On the async engine `onDone` fired immediately with
the child's *initial* context, because `await child.start()` returns once the
child's initial state is entered, not when it finishes; the child was then
orphaned, leaking its run loop and timers past the parent's own `stop()`
(measured +2 permanently live tasks per invocation). On the sync engine
`onDone` never fired at all.

**Entry/exit actions receive the real event.** `SyncInterpreter` synthesised
`entry.<id>` / `exit.<id>`, so an action reading `event.payload` — the normal
way to seed state from an event — silently received nothing.

Also fixed:

- Custom `id` on a state was ignored, so `#myId` cross-branch targets always
  raised `StateNotFoundError`. 37 of the 104 bundled Stately machines use them.
- A `.` in a state key collided with the id separator: a flat `"x.y"` and a
  nested `x > y` produced the same id, and targeting `"x.y"` silently entered
  the nested state. Now rejected at parse time.
- `start()` on a stopped interpreter silently no-opped, leaving a machine that
  looked live and dropped every event. Now raises.
- Plugin hook exceptions escaped to `send()` (sync) or killed the run loop
  (async), although actions and subscribers were already contained.
- `send()` to a stopped async interpreter queued unboundedly.
- `from_snapshot` leaked `json.JSONDecodeError`, so `except XStateMachineError`
  missed corrupt snapshots from Redis or disk.
- Exit-action order across parallel regions was non-deterministic.
- Malformed `states` / `on` / `after` / `invoke` / `initial` / `context`
  surfaced as raw `TypeError`/`AttributeError` from internals, or were silently
  accepted and produced a machine that hung.

### Added

- `tests/test_engine_conformance.py` — a cross-engine conformance suite that
  drives one config through **both** engines and asserts identical observable
  behaviour, including error paths. Each engine was previously pinned
  separately, which is exactly how these divergences survived 2,647 passing
  tests.

### Fixed

Defects found by the end-to-end review of merged `main` prior to the 0.6.0
release. None of these ever reached PyPI.

- **`py.typed` is now shipped.** `pyproject.toml` declared the
  `Typing :: Typed` classifier, but no PEP 561 marker was packaged, so every
  inline annotation was invisible to downstream type checkers and the
  classifier was simply untrue.
- **Built-in action failures are contained.** User-supplied actions were
  wrapped in error containment; built-in action creators (`assign`,
  `spawnChild`, `raise`, ...) were not — despite resolving user callables and
  raising for the same reasons. An escaping error killed the async run loop
  while callers still observed `status == "running"`.
- **The async engine accepts synchronous services.** `invoke` awaited the
  service result unconditionally, so a plain function raised `TypeError`
  inside a task whose exception was never retrieved; the machine sat in the
  invoking state forever. `SyncInterpreter` accepted the identical config.
- **`systemId` survives a snapshot round-trip.** The registry came back empty
  after a restore, so every `sendTo("sys", ...)` silently dropped its event.
- **The `MachineLogic` subclass style now works.** Defining actions, guards,
  and services as methods on a subclass is documented throughout the guides,
  but nothing collected those methods, so every such example raised
  `ImplementationMissingError`. Methods are classified by arity; explicitly
  supplied dictionaries always take precedence.
- **Importing the CLI no longer configures root logging.** `cli/__main__.py`
  called `logging.basicConfig()` at module import, attaching a handler to the
  host application's root logger.
- **CLI output degrades instead of leaking escapes.** `_safe_print` only
  caught `UnicodeEncodeError`, leaving it blind to a stream built with
  `errors="backslashreplace"` — which never raises and printed a literal
  `✅` to legacy Windows consoles.
- **Malformed `tags` / `meta` raise an actionable error.** `tags: 123`
  surfaced as `'int' object is not iterable` with no indication of which state
  was at fault, and `tags: {"a": 1}` was silently accepted as the tag set
  `{"a"}` by iterating the mapping's keys.

### Documentation

- `docs/_guide/interpreters.md` claimed that a raising action propagates out
  of `.send()`. Actions have been contained since 0.5.1; the section now
  documents the real behaviour and shows how to model a failure on `context`.
- `CHANGELOG.md` gained the link reference definitions its `[x.y.z]` headings
  had always assumed, and records that 0.5.1 was never published to PyPI.

## [0.6.0] - 2026-08-08

**XState v5 feature parity.** Closes all 73 gaps catalogued in
`docs/FEATURE_GAP_ANALYSIS.md` — every one verified by an executable probe.

> ⚠️ **Read the *Fixed* section first.** Several defects caused valid XState
> JSON to be accepted and then silently ignored, or to produce wrong
> behaviour. If you relied on any of those accidents, your machine's
> behaviour will change.

### Fixed

Silent-wrongness defects, in order of severity:

- **`cond` guards fired unconditionally.** Only `guard` was read, so any
  transition written with the XState v4 spelling ran **unguarded** — the
  predicate was never called. This silently inverted safety logic in every
  machine ported from v4 or copied from an older tutorial. `cond` is now a
  first-class alias for `guard`.
- **Object-form guards killed the async interpreter.** The standard v5 form
  `{"type": ..., "params": ...}` was used directly as a dictionary key,
  raising `TypeError: unhashable type: 'dict'` from inside the event loop.
  In `SyncInterpreter` this surfaced; in the async `Interpreter` it destroyed
  the run loop while `status` still read `"running"`, and every later `send()`
  was dropped. Guards are now normalised into a hashable `GuardDefinition`.
- **Child actors were dropped from snapshots.** A parent with live children
  serialised to `{status, context, state_ids}` and restored with **zero
  children** — unrecoverable data loss for anyone persisting a workflow.
  Snapshots are now deep.
- **History states stranded the machine.** `{"type": "history"}` parsed as a
  plain atomic state, so targeting it parked the machine *in the history node
  itself*.
- **Compound states with no `initial` started empty.** The machine reported
  success with an empty active configuration and silently dropped every
  event. A single child is now inferred; an ambiguous one raises at start.
- **Wildcard and partial event descriptors never matched.** `on: {"*": ...}`
  and `on: {"mouse.*": ...}` were valid config that did nothing, because event
  lookup was an exact dictionary test.
- **Forbidden transitions did not block.** `on: {"E": None}` vanished at parse
  time, so the ancestor's handler fired anyway.
- **Callable `params` were passed through raw.** User code received a function
  object where it expected a dict — silent corruption surfacing far from its
  cause. The same applied to a callable `context`.
- **Named delays crashed.** `after: {"TIMEOUT": ...}` raised a bare
  `ValueError` from `int()` with no hint that named delays were the feature.
- **Unhandled service failures were invisible.** A service that raised with no
  `onError` logged a message and the machine carried on as though nothing had
  happened.
- **Transient loops could spin forever.** Two `always` transitions targeting
  each other never terminated.

### Added

**Guards**
- Higher-order composition: `and`, `or`, `not`, with short-circuit evaluation
  and arbitrary nesting.
- The built-in `stateIn` guard, answered from the live configuration.
- Parameterised guards. Params reach the predicate as an optional third
  argument, arity-checked so existing two-argument guards are unaffected.

**Action creators** (`xstate_statemachine.actions`) — none of these existed;
the only previous mechanism was a user function mutating context in place:
- `raise`, `sendTo`, `sendParent`, `forwardTo`, `escalate`, `log`, `cancel`,
  `stopChild`, `spawnChild`, `emit`, `assign`, `pure`, `choose`,
  `enqueueActions`.
- Both camelCase (JSON) and snake_case (Python) spellings, plus helper
  functions so Python-authored machines need not hand-write params dicts.
- Built-ins resolve **after** a lookup in `MachineLogic.actions`, so a machine
  that defines its own `log` or `assign` keeps working.
- Delayed sends with cancellation: `delay` accepts a number, a callable, or a
  named delay; `cancel(send_id)` aborts a pending send.

**Actor system**
- `systemId` registration with `interpreter.system.get()` / `.get_all()`,
  backed by a registry on the root interpreter so ids are global to one
  hierarchy — which is what makes sibling-to-sibling messaging possible.
- `spawn` honours explicit `id`, `systemId` and `input`.

**Statechart primitives**
- History states, shallow and deep, including persistence and SCXML-correct
  fallback for an unvisited history state.
- Top-level `always` (the v5 spelling); the v4 `on: {"": ...}` still works.
- `tags` + `has_tag()` / `.tags`, `meta` + `get_meta()`, `description`.
- Final-state `output` carried as done-data on `done.state.*`, and machine
  completion via `status == "done"` with `interpreter.output`.

**Observation & lifecycle**
- `subscribe()` returning an unsubscribe callable; listener exceptions are
  logged and contained.
- `matches()`, `can()`, `has_tag()`, `get_meta()`.
- `input` at creation plus `context` factories receiving `{input}`.
- Error snapshots: `status == "error"` and `interpreter.error`.
- `emit()` with `interpreter.on(type | "*", listener)`.

**Pure API** (`xstate_statemachine.helpers`), mirroring XState v5.19.0:
- `initial_transition()` / `pure_transition()` returning
  `(snapshot, actions)` — genuinely side-effect free: a throwaway probe
  records the actions a real run would execute and suppresses timers and
  services. Exported as `pure_transition` so it does not shadow the Pythonic
  DSL's `transition()`.
- `get_initial_snapshot()` / `get_next_snapshot()`.
- `wait_for()`, `wait_for_sync()`, `to_promise()`.

**Safety**
- `max_iterations` (default 1000, configurable via `maxIterations`) bounds the
  microstep loop.
- `MachineLogic(delays=...)` for symbolic delays.

### Changed
- `TransitionDefinition.guard` is now a read-only property returning the
  guard's *type name*. Use the new `guard_def` for params and nested guards.
- `StateNode.type` may be `"history"`.
- `after` map keys may be `str` (a named delay) as well as `int`.
- `get_snapshot()` output gained `configuration`, `output`, `error`,
  `history` and `actors`. Older snapshots still restore — the loader falls
  back to `state_ids` when `configuration` is absent.

### Testing
- New `tests/test_xstate_v5_parity.py`: **140 tests**, one class per feature
  area, asserting observable behaviour. Where a gap previously failed
  silently, the test pins that the feature now takes effect — a test that
  only checked "no exception" would still pass against the broken version.
- Suite: 2455 → **2595 passing**. Coverage **86%**.
- The implementation was then reviewed adversarially. **15 defects were
  confirmed and all 15 are fixed**, each pinned by a regression test. The
  most serious:
  - A `raise` during initial entry corrupted the configuration, and a
    transition into a parallel region double-entered it — both left two
    active leaves in one non-parallel region.
  - Wildcard descriptors swallowed the engine's own `done.*` / `error.*` /
    `after.*` events, silently breaking every invoke and delayed transition
    in a state declaring `on: {"*": ...}`.
  - A `MachineNode` used as an `invoke` `src` raised `TypeError` which, via
    the new unhandled-error path, put the machine into a permanent `error`
    status — a **regression** against a configuration that previously worked.
  - `stop()` guarded on `status != "running"`, so the newly-routine `done`
    and `error` statuses made teardown a silent no-op, leaking child actors
    and their timers.
  - Actors parked in `_pending_actor_snapshots` were never re-serialised, so
    the "preserved" child vanished on the next save — the same data loss deep
    persistence exists to prevent, one round-trip later.
  - `get_persisted_snapshot()` returned the live context by reference, so
    later execution retroactively rewrote an already-taken snapshot.
  - A restored async interpreter was frozen: `status == "running"` with no
    event-loop task, and `start()` refused to create one. `start()` now
    resumes a restored actor and its children.
  - Snapshot `error` was written but never read back; `stopChild` left actors
    in the system registry; nested `enqueueActions` could recurse until
    `RecursionError`; `sendTo` could not address auto-id actors; a reused
    send id orphaned the first timer; and both `get_persisted_snapshot()` and
    `stop()` recursed forever on an actor cycle.

### Added
- **Continuous Integration** (`.github/workflows/ci.yml`). The project had
  issue and PR templates but no workflows, so nothing verified a push. Every
  defect fixed in 0.5.1 — including a permanently deadlocked machine and a
  README whose headline example raised `AttributeError` — was reachable
  precisely because no automated gate existed. Four independent jobs:
  - **lint** — `black --check` plus `flake8`, using the same flags and pinned
    tool versions as `.pre-commit-config.yaml` so a local `pre-commit run` and
    CI cannot disagree.
  - **test** — the full suite across Python 3.9–3.14 on Linux, plus Windows
    3.9/3.14 and macOS 3.14 spot-checks. The matrix mirrors the versions
    advertised in `pyproject.toml`; a support claim that CI does not exercise
    is only a hope. Also executes the `doctest` examples, which had rotted
    silently across releases because nothing ran them.
  - **coverage** — one authoritative measurement gated at `--cov-fail-under=86`.
  - **build** — `python -m build` and `twine check`, then installs the built
    *wheel* into a clean virtualenv and smoke-tests the public API and the
    `xsm` console entry point. This validates the packaged artifact rather than
    the source tree, catching a module that exists on disk but was never
    included in the distribution.

## [0.5.1] - 2026-08-07

> **Note:** 0.5.1 was never published to PyPI. Its changes ship as part
> of [0.6.0](#060---2026-08-08); this section is retained so the
> provenance of each fix stays traceable.

This is a **correctness release**. It repairs a family of defects in the core
SCXML transition algorithm, aligns the runtime's error handling with the
contract documented in `AGENTS.md`, and implements the public interpreter
attributes that the README and guides had been documenting without them
existing.

> ⚠️ **Behavioural changes.** Exceptions raised inside user-supplied guards and
> actions are now contained rather than propagated. If your code relied on a
> failing action tearing down the interpreter, see *Changed* below.

### Fixed
- **Compound re-entry left the machine dead** (`base_interpreter.py`,
  `sync_interpreter.py`). `_process_event` finalised the active configuration
  with `difference_update(states_to_exit)` *after* `_enter_states` had already
  inserted the recursively-entered initial children. Because those children
  were themselves members of `states_to_exit`, the finalisation step deleted
  the states that had just been entered. The machine was left holding only
  non-atomic ancestors, so `current_state_ids` returned an empty set and no
  further leaf-level event could ever match — a permanent deadlock. This broke
  the `reenter: True` feature shipped in 0.4.2 and the standard "restart a
  submachine" idiom (a child targeting its own compound parent). `_exit_states`
  and `_enter_states` are now the sole authorities on active-set membership.
- **Transitions up to an ancestor entered nothing** (`base_interpreter.py`).
  `_find_transition_domain` could return the target state itself as the
  transition domain when the target was an ancestor of the source, making
  `_get_path_to_state` return an empty path. The domain is now always a
  *proper* ancestor of the target.
- **Transition selection ranked states by name length** (`base_interpreter.py`,
  `models.py`). Depth was approximated with `len(state.id)`, so a shallow state
  with a verbose name outranked a genuinely deeper state with a terse one and
  the wrong transition was taken. `StateNode` now carries a cached integer
  `depth`, computed once at construction, which is both correct and cheaper
  than repeated string work on the hot path.
- **Parallel regions took only one transition per event** (`base_interpreter.py`,
  `sync_interpreter.py`). Selection returned a single `max(...)` winner across
  the whole configuration, so an event handled by two orthogonal regions
  advanced only one of them — contrary to SCXML, which requires one transition
  per region. The new `_select_transitions` picks the deepest eligible
  transition for each active leaf and de-duplicates by identity, so a
  transition defined on a shared ancestor still fires exactly once.
- **Actor spawning was incompatible with logic auto-discovery**
  (`logic_loader.py`). `spawn_<key>` / `spawn_blocking_<key>` are built-in
  action types resolved from `logic.services` at execution time, but the
  extractor registered them as required *actions*. Any machine using `spawn_`
  therefore raised `ImplementationMissingError` unless the caller bypassed
  discovery with an explicit `logic=`. Spawn keys now route to `services` with
  their prefix stripped.
- **Spawn service keys were derived three different (and wrong) ways**
  (`models.py`, `interpreter.py`, `sync_interpreter.py`). `Interpreter` used
  `type.replace("spawn_", "")` — unanchored and global, so
  `spawn_blocking_worker` resolved to `blocking_worker` and
  `spawn_respawn_handler` to `rehandler`. `SyncInterpreter` used
  `type.split("_", 2)[-1]`, truncating every multi-word key
  (`spawn_my_worker` → `worker`). Both silently looked up the wrong service.
  A single `spawn_service_key()` helper in `models.py` is now the sole source
  of truth, shared by the loader and both interpreters so discovery and lookup
  agree by construction.
- **A dead async run loop could still report itself as running**
  (`interpreter.py`). `_run_event_loop` only reset `status` inside
  `except Exception`, so a `BaseException` escaping the loop left the
  interpreter reporting `status == "running"` forever with nothing draining
  the queue — every subsequent `send()` silently dropped. The handler now
  catches `BaseException` (always re-raising) and a `finally` clause
  guarantees the status can never outlive the loop.
- **`is_running` lied after `from_snapshot()`** (`interpreter.py`).
  Restoration assigns the persisted status verbatim, producing an async
  interpreter with `status == "running"` and no event-loop task. `is_running`
  now additionally requires a live loop task, so it never claims a machine can
  process events when nothing is consuming its queue.
- **A shared ancestor's guard was evaluated once per parallel region**
  (`base_interpreter.py`). Because selection walks up from every active leaf,
  a transition on a common ancestor was guard-evaluated N times for N regions
  before de-duplication discarded the duplicates — multiplying any side effects
  and firing `on_guard_evaluated` N times for one logical decision. Guard
  results are now memoised per selection pass.
- **Sibling parallel regions were annihilated by an in-region transition**
  (`base_interpreter.py`, `sync_interpreter.py`). When a descendant targeted
  one of its own ancestors and that ancestor was a region of a `parallel`
  state, the transition domain became the parallel node itself. `states_to_exit`
  then swept up every *sibling* region while the entry path re-entered only the
  targeted branch, so the siblings were exited and never restored — permanently
  dead and unable to answer any further event. The exit set is now scoped to
  the branch actually being re-entered whenever the domain is parallel, via the
  shared `_compute_states_to_exit()` helper.
- **Deep entry left a phantom sibling leaf** (`base_interpreter.py`,
  `sync_interpreter.py`). `_enter_states` descended into a compound's `initial`
  child unconditionally, *in addition* to walking the explicit entry path. A
  transition targeting `B.b2` while `B.initial` was `b1` activated both — two
  simultaneously active leaves in one non-parallel region, which SCXML forbids.
  The phantom leaf then took part in the next selection pass, so a later event
  fired the wrong transition and duplicated its actions. The default descent is
  now skipped when the entry path already names a child of that state.
- **External cancellation caused `stop()` to skip all cleanup**
  (`interpreter.py`). The run loop forced `status = "stopped"` in a `finally`
  clause, which also ran on the ordinary `CancelledError` path. Cancellation is
  not always initiated by `stop()` — an enclosing `TaskGroup`, supervisor, or
  timeout can cancel `_event_loop_task` directly. The premature status change
  then made `stop()` hit its own idempotency guard and return early, never
  cancelling invoked services or child actors, which kept running forever.
  `stop()` again owns the status transition for orderly shutdown; the
  `BaseException` handler still corrects the bookkeeping on a genuine crash.
- **Stale doctests** (`exceptions.py`). The `NotSupportedError` example
  asserted an error message that exists nowhere in the codebase and claimed
  `after` transitions are unsupported by `SyncInterpreter` — they have been
  supported (via background threads) since v0.4.1. The `InvalidConfigError`
  example asserted a stale message. Both now pass under `doctest`.
- **Documentation claimed ASCII diagram export.** Only `to_mermaid()` and
  `to_plantuml()` exist; the README, guides, and CLI banner no longer advertise
  an ASCII exporter.

### Added
- **`Interpreter.active_state_ids` / `SyncInterpreter.active_state_ids`** — an
  alias of `current_state_ids`. This name appears in ~130 places across the
  README and `docs/` guides (including the headline quickstart) but was never
  implemented, so every published example raised `AttributeError` on contact.
- **`.is_running`** — a boolean convenience wrapper over `.status`, as
  documented in the API reference tables.
- **`.plugins`** — a readable/assignable property over the registered plugin
  list, supporting the documented `interpreter.plugins = [LoggingInspector()]`
  form. Assigning a non-list raises `TypeError`.
- **`StateNode.depth`** — the node's true tree depth, cached at construction.
- **`models.spawn_service_key()` / `models.is_spawn_action()`** — the shared
  helpers that define how a `spawn_` action maps to a `services` key.
- **`.plugins` element validation** — assigning a list containing an object
  that does not implement the plugin hooks now raises `TypeError` at the
  assignment site, rather than surfacing later as an `AttributeError` from deep
  inside event processing. The check is structural rather than a strict
  `isinstance`, so `use()` and `plugins = [...]` accept exactly the same
  objects. The getter returns a copy, so `plugins.append(...)` cannot bypass it.
- **`tests/test_scxml_correctness.py`** — 23 regression tests, one class per
  defect, each asserted against *both* the async and sync engines (the two
  interpreters implement the algorithm independently, so a one-sided fix is a
  latent bug).
- **`tests/test_public_api_surface.py`** — 20 contract tests pinning the
  documented public attributes, spawn key derivation, and `spawn_`
  auto-discovery, so documentation and implementation cannot silently diverge
  again.

### Changed
- **Guards that raise are now treated as `False`** (`base_interpreter.py`).
  Previously the exception propagated out of `send()` and, in async mode, tore
  down the run loop. A guard is a user-supplied predicate, so a defect in it
  blocks its transition and lets lower-priority alternatives (e.g. an unguarded
  fallback in the same `on` array) be considered, while leaving the machine
  responsive. This matches the contract documented in `AGENTS.md`.
  A *missing* guard still raises `ImplementationMissingError` — that is a
  configuration error, not a runtime condition.
- **Actions that raise are now contained** (`interpreter.py`,
  `sync_interpreter.py`). The error is logged with a traceback, the remaining
  actions in that list are skipped, and the state change still completes. This
  was the most damaging gap: because `Interpreter.send()` is fire-and-forget,
  an escaping exception killed `_run_event_loop` while callers still observed
  `status == "running"` — a silently dead machine. `asyncio.CancelledError`
  still propagates so cooperative cancellation on `stop()` is unaffected, and
  `ImplementationMissingError` / `NotSupportedError` remain fatal.
  - *Migration*: if you depended on an action's exception surfacing, raise it
    from an `invoke`d service instead — service failures still trigger
    `onError` transitions — or attach a plugin and inspect the logs.


## [0.5.0] - 2026-03-23

### Added
- **CLI `--template` flag** with 5 template types for Pythonic code generation:
  - `pythonic-class`: Class-based state machine using `StateMachine` base class
  - `pythonic-builder`: Builder pattern using `MachineBuilder` fluent API
  - `pythonic-functional`: Functional style using `build_machine()` factory
  - `class`: Classic class-based template (existing behavior)
  - `functional`: Classic functional template (existing behavior)
- **Strategy pattern architecture** for code generation with pluggable `CodeGenStrategy` implementations
- **Pythonic API** for defining state machines in pure Python without JSON dicts:
  - `StateMachine` base class with metaclass for class-based declarations
  - `MachineBuilder` fluent builder for programmatic/dynamic construction
  - `build_machine()` function for functional-style machine definition
  - `State` class for defining states with all features (hierarchy, parallel, final, after, invoke, always, onDone)
  - `Transition` and `TransitionGroup` for fluent transition definitions with `|` combinator
  - `@action`, `@guard`, `@service` decorators with auto snake_case-to-camelCase naming
  - `transition()` standalone function for functional API
  - Full backward compatibility — all existing JSON-based APIs work unchanged
- **Comprehensive validation** for Pythonic API:
  - Final state validation: blocks outgoing transitions, child states, and Transition objects from final states
  - Parallel child validation: raises `InvalidConfigError` if a child of a parallel state has `initial=True`
  - `MachineBuilder` duplicate state name detection
  - `MachineBuilder.build()` validates initial state is defined (multi-state machines)
  - `@state.enter`/`@state.exit` decorators raise `InvalidConfigError` when used outside a `StateMachine` class
  - `Transition.__or__` and `TransitionGroup.__or__` return `NotImplemented` for invalid operand types
- **`__repr__` methods** on `State`, `Transition`, `TransitionGroup`, and `MachineBuilder` for better debugging
- **143 Pythonic API tests** across 20 test classes covering all three API styles, error handling, edge cases, merge rules, async/sync interpreter compatibility, and snapshot/restore
- **Comprehensive README rewrite** (2,508 lines): Complete documentation overhaul covering all 24 public API symbols with accurate signatures, code examples, and full feature coverage including:
  - `get_snapshot()` / `from_snapshot()` API with persistence examples
  - `transition()` standalone function, `TransitionGroup`, `State.internal()`, `reenter` parameter
  - `MachineLogic` constructor, `LogicLoader` singleton with global module registration
  - `DoneEvent` / `AfterEvent` internal event types
  - `MachineNode.get_state_by_id()` / `.get_next_state()` inspection methods
  - `State.__init_subclass__` class inheritance pattern
  - `PluginBase` hooks with correct signatures (`on_transition(interpreter, from_states, to_states, transition)`)
  - `LoggingInspector` output format reference
  - `always` (eventless transitions) with full example
  - All 5 CLI templates deep dive with generated code examples
- **Stress test suite**: 50 real-world XState machine configs tested against all 5 templates (250 code generation runs) with `py_compile` + `importlib` validation

### Changed
- Generated code now includes rich docstrings, error handling, and type hints
- `--async-mode` defaults are template-aware (Pythonic templates default to sync)
- **Performance**: `_snake_to_camel` helper uses `@functools.lru_cache(maxsize=256)` for hot-path optimization
- **Idempotent builds**: `MachineBuilder.build()` uses `copy.deepcopy` on internal state so repeated calls produce independent machines
- **Defensive copying**: `_compile_state()` copies `entry`, `exit`, and `on` data from State objects to prevent mutation of shared State instances across builds
- **Falsy context handling**: All context checks use `is not None` instead of truthiness to preserve empty dicts `{}`
- **State.exit naming**: Internal storage uses `_exit_actions` with a public `exit_actions` property, keeping `exit()` as the decorator method — avoids shadowing Python's `exit` builtin
- **`_resolve_target()` signature**: Added optional `source_prefix` parameter for hierarchical context-aware target resolution
- **`collect_all_transitions()`**: Now passes `source_prefix` to `_resolve_target()` for accurate nested state resolution

### Fixed
- **Nested state target resolution**: Fixed 14 `pythonic-class` template failures where child states with the same name under different parents (e.g., `login.idle` vs `signup.idle`) resolved to the wrong target. Added `source_prefix` parameter to `_resolve_target()` for context-aware sibling resolution that walks up the parent chain to find the closest matching state.
- **State/event name collision in code generation**: Fixed `'Transition' object has no attribute 'to'` error when event names (e.g., `preview_failed`) collide with state variable names. Code generator now detects collisions and appends `_event` suffix to transition variable names.
- **Empty actions list emission**: Changed `actions_val is not None` to truthy check to avoid emitting `actions=[]` in generated `pythonic-class` code.
- **Conditional `service` decorator import**: The `service` decorator is now only imported in generated code when the machine actually defines services, preventing unused import warnings.
- **Function complexity compliance**: Extracted `_format_action_list_kwarg()` helper in `pythonic_functional.py` to reduce `_generate_build_function` complexity from 36 to ≤35, fixing flake8 C901 violation.

### Deprecated
- `--style` flag (use `--template` instead; `--style` will be removed in v0.6.0)

## [0.4.3] - 2025-02-03

### Added

- **Python 3.14 Support**: Added full support for Python 3.14 with comprehensive testing across all supported Python versions (3.9-3.14).
  - Verified compatibility with 2,754 tests across Python 3.9, 3.10, 3.11, 3.12, 3.13, and 3.14.
  - Updated project classifiers to include Python 3.14.
- **Enhanced Test Coverage for `logic_providers`**: Added comprehensive tests for `logic_providers` camelCase to snake_case auto-discovery feature (Issue #17).
  - Tests verify that camelCase action names in JSON (e.g., `storeJobParams`) are correctly mapped to snake_case Python methods (e.g., `store_job_params`).
  - Added end-to-end async execution tests to ensure actions are properly invoked through the interpreter.
- **Documentation Improvements**: Cleaned up README.md by removing outdated version-specific references ("New in 0.4.1", "Headline for 0.4.1", "Upgrade Notes: 0.4.0 → 0.4.1") to make documentation more maintainable and version-agnostic.

### Changed

- **Build System Migration**: Migrated from Poetry to `uv` for faster, more reliable package management.
  - Switched build backend from `poetry-core` to `hatchling`.
  - Updated `pyproject.toml` to use PEP 621 metadata format.
  - Replaced Poetry dependency groups with `uv` dependency groups (`dev`, `lint`, `test`).
  - Updated all documentation with new `uv` commands:
    - `uv pip install -e . --group dev --group lint --group test`
    - `uv run pytest`
    - `uv run pre-commit run --all-files`
- **Python Version Support**: Updated minimum Python requirement from 3.8 to 3.9.
  - Python 3.8 reached end-of-life and is no longer supported.
  - All dependencies updated to require Python 3.9+.
- **CI/CD Updates**: Updated pre-commit configuration to use Python 3.14 and Black 26.1.0.

### Fixed

- **Deprecation Warning**: Replaced deprecated `asyncio.iscoroutinefunction()` with `inspect.iscoroutinefunction()` to resolve deprecation warnings and ensure compatibility with Python 3.16+.
- **Python 3.9 Compatibility**: Fixed union syntax usage in test files (`| None` → `Optional[...]`) to ensure compatibility with Python 3.9, which does not support PEP 604 union syntax.

## [0.4.2] - 2025-08-13

### Added

- **`reenter` Flag for Self-Transitions**: Introduced a `reenter` boolean flag for transitions to align with XState v5's handling of self-transitions.
  - When `reenter: true`, a self-transition becomes "external," causing the state to be exited and re-entered, triggering all entry and exit actions.
  - By default, or when `reenter: false`, a self-transition is "internal," meaning only the transition's actions are executed, and the state is not exited or re-entered. This is the new default behavior.
  - This feature is fully supported in both the asynchronous (`Interpreter`) and synchronous (`SyncInterpreter`) engines.

### Changed

- **Refactored Transition Logic**: The core event processing logic in both `BaseInterpreter` and `SyncInterpreter` was refactored to cleanly distinguish between internal and external transitions, improving clarity and maintainability.
- **Updated Self-Transition Tests**: Existing tests for self-transitions were updated to use `reenter: true` to preserve their original intent of testing external transitions. New tests were added to specifically validate the `reenter: false` internal transition behavior.

## [0.4.1] - 2025-07-27

### Added

- **Enhanced Sync Actor Spawning**: The `SyncInterpreter` now supports **non-blocking actor spawning** (via `spawn_` actions) by running child `SyncInterpreter` instances in dedicated background threads. This significantly expands the `SyncInterpreter`'s capabilities to manage concurrent, independent state machine processes without blocking the main thread, offering more flexibility for synchronous applications.
- **Multiple `after` Timers per State in SyncInterpreter**: Introduced the ability for a single state in the `SyncInterpreter` to declare and manage **multiple independent `after` (delayed) transitions**. This provides finer-grained control over time-based logic, enabling more complex timing behaviors within synchronous state machines.
- **Hierarchical Machine Generation in CLI**: The `xsm` CLI's `generate-template` command now intelligently handles **hierarchical state machine definitions** (parent-child relationships across multiple JSON files). This streamlines boilerplate generation for complex systems composed of a main machine orchestrating several child actors. The CLI can also **heuristically identify parent-child relationships** among input JSON files and offers interactive confirmation for the user.
- **CLI Subcommand Aliases**: Added support for shorter, alternative names (aliases) for CLI subcommands. This significantly enhances command-line usability and convenience. For example:
    - `generate-template` can now be invoked as `gt`.
    - `--json-parent` can be used as `-jp`.
    - `--json-child` can be used as `-jc`.
    - `--file-count` can be used as `-fc`.
    - `--async-mode` can be used as `-am`.
    - `--loader` can be used as `-l`.
    - `--style` can be used as `-s`.
    - `--output` can be used as `-o`.
    - `--force` can be used as `-f`.

### Changed

- **CLI Command Renamed**: The primary command-line interface tool has been renamed from `xstate-statemachine` to `xsm` for brevity and ease of use. All examples and documentation related to the CLI usage now reflect this new command.
- **Improved `SyncInterpreter` Shutdown**: The `stop()` method of the `SyncInterpreter` now ensures a more orderly shutdown by explicitly iterating and stopping all child actors *before* canceling any active `after` timers. This enhances reliability and resource management for complex synchronous systems.
- **Robust `after` Timer Management in `SyncInterpreter`**: The internal mechanism for managing `after` timers in the `SyncInterpreter` was refined to accurately track and cancel multiple timers associated with a single state. Each timer is now assigned a unique identifier, ensuring precise lifecycle management and preventing lingering background threads.
- **Streamlined Logic Loader for `spawn_` actions**: The `LogicLoader` no longer applies special parsing rules to `spawn_*` actions when extracting logic names. This simplifies the configuration and binding process by treating these as regular actions, with the runtime interpreter now handling the specific spawning behavior.
- **Refined Runner Code Logic Binding**: The generated runner code for both single and multiple machine setups now features more robust and accurate logic for binding the Python implementation (actions, guards, services) to the state machine. This ensures seamless integration and execution, especially with class-based logic and auto-discovery.
- **Enhanced Configuration File Path Resolution in Runner**: The boilerplate runner code generated by the CLI now incorporates smarter logic for locating the source JSON configuration file. It first attempts to find the file relative to the generated script, and then, as a fallback, relative to the script's parent directory, improving adaptability to various project structures.
- **CLI Argument Validation and User Experience**:
    - The CLI's argument parsing is now stricter, explicitly disabling partial matching of command-line options (`allow_abbrev=False`) to ensure clearer and more predictable behavior.
    - Added specific validation checks to prevent invalid command-line argument combinations, such as supplying the `--json-parent` flag multiple times.
    - Improved consistency and clarity in CLI prompts, especially during interactive hierarchy guessing.
    - The code generation logic now automatically adjusts generated Python function names if they conflict with Python's reserved keywords (e.g., `def` becomes `def_`), preventing syntax errors in the generated boilerplate.

### Fixed

- **CLI Subcommand Alias Execution**: Resolved a critical issue where CLI subcommand aliases (like `gt` for `generate-template`) were not correctly executing the associated workflow and instead displayed the help message. This was fixed by modifying the main CLI entry point to correctly dispatch to the appropriate subcommand logic when an alias is used.
- **Regression Fix: `SyncInterpreter` Target Resolution**: Corrected a regression in the `SyncInterpreter` where the internal `TransitionDefinition` object's `target_str` was not consistently updated with the fully resolved path after a successful state target resolution. This fix ensures that all subsequent internal logic consistently uses the correct, fully qualified state ID.
- **Generated Code Keyword Conflicts**: Addressed a bug that could lead to syntax errors in generated Python code when state machine action, guard, or service names coincided with Python's reserved keywords. The generator now automatically renames such conflicting elements by appending an underscore.
- **Minor Logging Consistency**: Ensured that the generated Python logic files consistently use the correct and intended logging messages when actions are executed, maintaining clarity in debug outputs.

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

---

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
  Helpers suchs as `get_state_by_id()`, `get_next_state()`, and public camel⇄snake converters.
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

<!-- ---------------------------------------------------------------- -->
<!-- 🔗 Link reference definitions                                     -->
<!-- Every `## [x.y.z]` heading above is a Markdown reference link.    -->
<!-- Without these definitions they render as literal bracketed text.  -->
<!-- ---------------------------------------------------------------- -->

[Unreleased]: https://github.com/basiltt/xstate-statemachine/compare/v0.6.0...HEAD
[0.6.0]: https://github.com/basiltt/xstate-statemachine/compare/v0.5.1...v0.6.0
[0.5.1]: https://github.com/basiltt/xstate-statemachine/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/basiltt/xstate-statemachine/compare/v0.4.3...v0.5.0
[0.4.3]: https://github.com/basiltt/xstate-statemachine/compare/v0.4.2...v0.4.3
[0.4.2]: https://github.com/basiltt/xstate-statemachine/compare/v0.4.1...v0.4.2
[0.4.1]: https://github.com/basiltt/xstate-statemachine/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/basiltt/xstate-statemachine/compare/v0.3.1...v0.4.0
[0.3.1]: https://github.com/basiltt/xstate-statemachine/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/basiltt/xstate-statemachine/compare/v0.2.3...v0.3.0
[0.2.3]: https://github.com/basiltt/xstate-statemachine/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/basiltt/xstate-statemachine/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/basiltt/xstate-statemachine/compare/v0.1.0...v0.2.1
[0.1.0]: https://github.com/basiltt/xstate-statemachine/releases/tag/v0.1.0
