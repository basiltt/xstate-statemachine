---
title: "Changelog"
description: "Release history and what changed in each version."
---

# Changelog

All notable changes to XState-StateMachine for Python are documented here.

For the full changelog with commit history, see [CHANGELOG.md on GitHub](https://github.com/basiltt/xstate-statemachine/blob/main/CHANGELOG.md).

---

## [Unreleased] — Adoption-readiness, parts 1–3

**Adoption-readiness.** A production adoption audit (tracking issue
[#26](https://github.com/basiltt/xstate-statemachine/issues/26)) filed 34
defects against 0.7.0 with a common theme: the library fails *silently* by
default. Part 1 closed all four blockers and the filer's top priorities.
Part 2 (below, marked **[wave 2]**) closes the remaining small/medium items:
actor lifecycle, persistence envelope, `invoke.input`, the pure API's cost,
hierarchical `value`, and the production-characteristics documentation.
Part 3 (below, marked **[wave 3]**) closes the concurrency and correctness
items: the SCXML-correct internal event queue, a bounded inbox with
overflow policies, `send(wait=, priority=)` receipts, resumable
invocations after restore, an injectable clock with a starvation-free
timer lane, strict-mode event validation, and a refactor that now runs
both engines off one core algorithm.
Every new behaviour is a per-machine policy or an additive API whose default
preserves 0.7.x semantics, with two deliberate exceptions called out under
**Changed**.

### Added

- **`actionErrorPolicy: "continue" | "rollback" | "fail"`** (#27). Before,
  an action that raised left the transition committed with a half-built
  state. `rollback` restores configuration *and* context; `fail` rolls back
  and stops with `TransitionFailedError`. New `on_transition_failed` plugin
  hook and `interpreter.last_transition_ok`. The default (`continue`) emits
  a one-shot `DeprecationWarning`; it flips to `rollback` in 1.0. The policy
  covers **every** action slot -- `entry`, `exit`, the transition's own
  `actions`, targetless and internal self-transitions, and the initial
  entry performed by `start()` -- and a rollback cancels any `after` timers
  or invokes that a partially-entered target state had already armed.
- **`onUnhandled: "ignore" | "defer" | "error"`** (#28). `defer` is
  library-owned: replay is at the head of the queue in original order,
  still-unhandled events are re-deferred, the buffer survives snapshots and
  is bounded by `DEFER_MAX`. `interpreter.deferred_count`, new
  `on_unhandled_event` hook (fires under every policy) and
  `UnhandledEventError`.
- **`guardErrorPolicy: "false" | "true" | "raise"`** (#35). A raising guard
  is now observable via `on_guard_error` before the substituted result is
  reported; previously it was indistinguishable from a guard returning
  `False`.
- **Build-time validation** (#29, #30). `create_machine()` now walks the
  finished tree and rejects, in one message, every transition target that
  does not resolve and every `always` self-target that can never make
  progress. `create_machine(..., strict_targets=False)` downgrades target
  failures to a `DeprecationWarning`; that escape hatch is removed in 1.0.
- **`strictTargets: true`** machine config (#31) disables the sibling
  fallback for `.child` targets.
- **`Interpreter.send_threadsafe()`** (#37) for delivering events from a
  foreign thread. `send()` from a foreign thread now raises
  `WrongThreadError` instead of silently losing the event.
- **Error-observability hooks** on `PluginBase` (#33): `on_transition_failed`,
  `on_guard_error`, `on_unhandled_event`, `on_error`, `on_done`. All
  implemented by `LoggingInspector`. Existing plugins load unchanged.
- **Built-in action param validation** (#32). `raise`, `sendTo`, `cancel`,
  `stopChild`, … now fail at build time when a required key is missing, with
  a hint if the key was placed at the top level instead of under `params`.
- New exceptions exported: `UnhandledEventError`, `TransitionFailedError`,
  `WrongThreadError`.
- **[wave 2] `interpreter.value`** (#58) -- the active configuration in
  XState's hierarchical form: a leaf key for an atomic root, `{parent:
  child}` for compound (innermost collapses to a string), one key per
  region for parallel, `{}` before `start()`. Tree-walked, so state keys
  containing `.` are safe. `matches()` now also accepts a partial value
  dict. Snapshots carry a derived `"value"` key; restore ignores it.
- **[wave 2] Snapshot envelope v1** (#45). Persisted snapshots gain
  `version` (integer payload-layout version, bumped only on layout change),
  `machine_id`, `machine_hash` (a 16-hex structural fingerprint over
  states, transitions, guard/action *names*, invokes and delays -- stable
  across `meta`/`description` edits and key order) and `taken_at`.
  `from_snapshot` refuses a newer `version` with `SnapshotVersionError`
  and a mismatched id or hash with `SnapshotDriftError`;
  `from_snapshot(..., verify_machine_hash=False)` opts out after a
  migration. Unversioned 0.7.x payloads restore exactly as before.
  New module `persistence.py` owns the format contract.
- **[wave 2] Inbox durability** (#47), both engines:
  `interpreter.pending_events` (accepted-but-unprocessed, FIFO),
  `drain_pending()` (remove without processing), `stop(drain=True)`
  (process to empty; async engine also takes `timeout=`). Snapshots carry
  `pending_events` and restore re-enqueues them, recursively for child
  actors.
- **[wave 2] `invoke.input` may be a callable** (#42) --
  `fn({context, event})` (XState form) or `fn(context, event)` -- resolved
  per spawn via `InvokeDefinition.resolve_input()`, deep-copied, and
  passed to a child MACHINE as its creation `input` (previously it was
  never forwarded at all), so a child `context` factory receives
  `{input}` as in XState. A plain-dict child context receives it only at
  `context["input"]` -- declared keys are never overwritten. A raising
  resolver becomes `onError` on both engines.
- **[wave 2] `Interpreter.wait_done()`** (#43) -- a future resolved the
  instant the machine reaches `done`/`error`.
- **[wave 2] `spawnBlockingTimeout`** machine key (ms) bounds how long a
  `spawn_blocking_<key>` waits for the child (#41). Default 30 s; the wait
  is never unbounded, so a child that never reaches a final state cannot
  wedge its parent.
- **[wave 2] Docs: Production Characteristics** (#53, #56) -- a new guide
  page with measured numbers for the per-process throughput budget, `after`
  timer lateness under load, and the `SyncInterpreter` threading contract,
  plus `benchmarks/production_characteristics.py` to reproduce them.
- **[wave 3] SCXML internal event queue** (#36) -- a zero-delay `raise` to
  self during a macrostep now goes to a dedicated internal queue that both
  engines drain to completion before taking the next external event,
  instead of sharing one queue with the outside world. Trace order is now
  `['entry', 'RAISED', 'EXTERNAL']`, not `['entry', 'EXTERNAL', 'RAISED']`.
  Chains of raises stay FIFO; `always` transitions still run first within
  each microstep.
- **[wave 3] Bounded inbox** (#38) -- `Interpreter(max_queue_size=,
  overflow_policy=OverflowPolicy.*)` (`RAISE` the default once a bound is
  set, `BLOCK`, or `DROP_NEWEST`). `RAISE` raises `QueueOverflowError`;
  `DROP_NEWEST` warns and calls the new `PluginBase.on_event_dropped` hook.
  New `interpreter.queue_depth` on both engines for observability.
  `max_queue_size=None` keeps the unbounded queue (default, unchanged).
- **[wave 3] `send(wait=True)` / `send(priority=True)`** (#39) --
  `wait=True` resolves to a `Receipt(state_ids, changed, error)` once the
  macrostep for that exact event has run, so a caller can gate on the
  machine's decision without polling. `priority=True` (also
  `send_priority()`) delivers ahead of the inbox and is exempt from its
  bound. A dict-form payload using the reserved `wait`/`priority` keys
  still works but emits a `DeprecationWarning`. New exports: `Receipt`,
  `OverflowPolicy`, `QueueOverflowError`, `InterpreterStoppedError`.
- **[wave 3] `from_snapshot(restart_services=True)` and
  `pending_invocations()`** (#44) -- restoring a snapshot is still a
  static rebuild that starts nothing by default, but
  `pending_invocations()` now lists every `PendingInvocation(state_id,
  invoke_id, src)` in the active configuration with no live service or
  child actor, and `restart_services=True` re-invokes each of them from
  scratch (not resumed) through the same path `_enter_states` uses on
  both engines.
- **[wave 3] Injectable `Clock`** (#48, #49, #50) -- `Clock` protocol,
  `RealClock` (default) and `SimulatedClock` (virtual time), passed as
  `Interpreter(clock=)` / `SyncInterpreter(clock=)`; invoked and spawned
  children inherit the parent's clock. `RealClock` now delivers a fired
  `after` timer through a priority lane the async run loop checks ahead
  of the inbox, so a due timer can no longer be starved behind a burst of
  external events; `AfterEvent` gains `scheduled_for`, `fired_at`, and
  `lateness_ms`. `SyncInterpreter` no longer spawns an OS thread per
  `after` timer or delayed send -- a due deadline is delivered on the
  caller's thread at the top of `send()`, in the macrostep loop, or by the
  new `tick()`.
- **[wave 3] Strict mode** (#51) -- `strict` machine config key or
  `Interpreter`/`SyncInterpreter(strict=)` constructor flag (ctor wins).
  Under strict, `send()` of an event type the machine has never declared
  raises `UnknownEventError` synchronously at the call site, before the
  event is queued, with a difflib suggestion (`'Did you mean FILL?'`).
  `MachineNode.is_known_event()` applies the same matching rules as
  dispatch, including partial (`'mouse.*'`) and bare-`'*'` descriptors.
  `create_machine(event_schemas={'FILL': Fill})` adds opt-in,
  dependency-free payload validation -- any object with `validate(payload)`
  or `__call__` -- raising `InvalidEventPayloadError` at the call site
  regardless of the strict setting. Default (strict unset, no schemas) is
  unchanged.

### Deprecated

- **`actionErrorPolicy: "continue"` (the default)** (#27). Emits a one-shot
  `DeprecationWarning`; it flips to `"rollback"` in 1.0.
- **`create_machine(..., strict_targets=False)`** (#29, #30). Downgrades
  unresolvable transition targets to a `DeprecationWarning` instead of
  raising `InvalidConfigError`; that escape hatch is removed in 1.0.

### Fixed

- `.child` targets resolve into the **source's** descendants, matching
  XState v5; the 0.7.x sibling reading is kept as a fallback (#31).
- `internal: false` (XState v4 spelling) is honoured as `reenter: true`
  instead of being silently dropped (#29).
- `sendTo` can address an invoke by its explicit `id` and by `systemId`;
  a duplicate live `systemId` raises `ActorSpawningError` (#40).
- `from_snapshot` deep-copies the persisted context and merges it over the
  machine's defaults instead of aliasing the caller's dict (#46).
- `@action` / `@guard` / `@service` markers win over arity-based
  auto-registration in `MachineLogic` subclasses; ambiguous arities warn (#52).
- Resolving a transition no longer writes back into the shared
  `TransitionDefinition` (#59).
- `#machineId.path` targets resolve when the machine `id` itself contains a
  dot (`"my.machine"`); previously the first dotted segment alone was
  compared against the key and every such target was unresolvable.
- The unresolvable-target error names the absolute `#machine.path` form of
  any nested state matching the bare name, so a 0.7.x machine that relied on
  the fuzzy fallback gets the one-line fix in the message.
- Engine-synthesised `xstate.*` events (e.g. `xstate.error.actor.*` from
  `escalate`) are treated as system events by the `onUnhandled` policy, the
  same as `done.*` / `error.*` / `after.*`. Under `onUnhandled: "error"` an
  unhandled escalation no longer stops the parent with a misleading
  `UnhandledEventError`.
- `SyncInterpreter`: replayed deferred events no longer count against the
  macrostep runaway budget, so replaying a full `DEFER_MAX` buffer cannot
  trigger the overflow guard and discard live events queued behind it.
  The async engine already behaved correctly; the two now agree.
- Two tests in the suite declared a target as a sibling of `"states"`; the
  new validator caught them.
- **[wave 2]** Runtime target resolution no longer falls back to a
  whole-tree search by last id segment (#34). A bare `target: "filled"`
  declared in one parallel region used to bind `audit.archive.filled` in
  an unrelated region and move it. Resolution is now strictly lexical
  (sibling / `#id` / `.child` / exact top-level key) in both engines,
  which now share ONE resolver; the validator mirrors it one-for-one.
- **[wave 2]** `spawn_blocking_<key>` on the async `Interpreter` honoured
  only the `spawn_` half and ran non-blocking (#41). Both engines now wait
  for the child to reach a terminal status before the parent's next
  action; the sync engine also waits out a child driven by `after` timers,
  which it previously did not.
- **[wave 2]** The pure API (`transition` / `get_next_snapshot`) built a
  fresh interpreter subclass per call and deep-copied twice, costing 4x a
  real `send()` (#54). One probe per machine per THREAD is now cached
  (thread-local, so concurrent callers never share one) and reset;
  measured ~3x faster. Semantics unchanged.

### Changed

- Per-event `INFO` log calls on the hot path are now `DEBUG` (#55, part 1).
  Measured overhead of running at `INFO` on the filer's OMS machine dropped
  from 2.53× to ~1.0×.
- `Interpreter.send()` is a regular method that does **all** of its work
  eagerly -- thread check, normalisation, status guard and the queue put --
  and returns an already-resolved awaitable so `await interp.send(...)`
  is unchanged. A fire-and-forget `interp.send("GO")` from inside the loop
  is therefore delivered rather than silently dropped, and no
  "coroutine was never awaited" warning is ever emitted by the library.
- `send()` / `send_threadsafe()` on an interpreter whose event loop has
  since been closed raise a `RuntimeError` that says so, instead of a
  `WrongThreadError` naming the same thread on both sides.
- **[wave 2] Reaching a top-level final state now tears down** (#57):
  child actors are stopped, `after` timers and invoked services cancelled,
  and the machine's actor-system registration removed -- the moment
  `status` becomes `"done"` (or `"error"`), not when `stop()` is later
  called. `status`, `output`, `error` and `context` are retained;
  `stop()` on a done machine is a quiet no-op that keeps `status ==
  "done"`. Machines that relied on children outliving a completed parent
  must restructure (that dependence was on a leak).
- **[wave 2] Invoked child actors no longer poll** (#43). The parent
  awaited `child.status` every 5 ms in a second task; it now awaits a
  completion future. `onDone` latency drops from a 5 ms floor to ~0, which
  can expose tests that used the delay as a settling window.
  `_ACTOR_POLL_INTERVAL` is removed.
- `Interpreter` no longer constructs its `asyncio.Queue` in `__init__`; the
  queue is created when `start()` binds the loop, and events sent before
  `start()` are buffered and delivered in order. On Python 3.9
  `asyncio.Queue()` binds to the current loop at construction and raised
  when built outside one, so an `Interpreter` could not previously be
  instantiated in synchronous code on that version.
- **[wave 3] Hot-path work, both engines** -- roughly **+40-55% events/s**
  on every machine shape, measured on the same laptop: sync flat 23.5k ->
  35k ev/s, sync nested 25k -> 38k, async fire-and-forget 21k -> 29.5k,
  `send(wait=True)` 15k -> 18.5k. Four build-time answers replace per-event
  work: transition targets are resolved once by the build-time validator
  and memoised on the `TransitionDefinition` (the runtime re-ran the full
  multi-strategy resolver per transition); `_record_history` is skipped on
  machines that declare no history state; the transient-settle pass that
  ran a full transition selection after EVERY event is skipped on
  machines with no `always`; single-leaf configurations skip a sort. No
  semantics change -- the full suite is unchanged and each fast path has a
  pinned "slow path still taken when needed" test. Consequences visible in
  Production Characteristics: per-process budget ~20k -> ~30k trivial ev/s,
  `after` lateness at 500 busy machines ~63 ms -> ~46 ms.
- **[wave 3] Documentation is executed in CI.** `tests/test_docs_executable.py`
  runs every ```python block in README.md and docs/_guide/*.md that imports
  the package (a block opts out with a visible `<!-- doc-fragment -->`
  marker) and resolves every guide cross-link and anchor, so a sample that
  stops running or a link that 404s on the site fails the build. 34
  runnable feature examples now live under `examples/*/features/`, one per
  capability, all executed by `tests/test_examples.py`.
- **[wave 3] Real type safety for users** (`py.typed` was already
  shipped; now the types are worth having). Verified by
  `tests/test_type_safety.py`, which type-checks representative USER
  programs with mypy and pyright and asserts every real bug is flagged and
  no correct line is:
  - `create_machine(..., context_type=MyCtx)` -- a `TypedDict` or any
    `Mapping` subtype -- flows through to `interp.context`, so a typo'd key
    or wrong value type is a checker error. No runtime effect; without it
    the context is `Dict[str, Any]` as before.
  - `TContext` is bound to `Mapping[str, Any]`: `SyncInterpreter[MyCtx]`
    with a `TypedDict` was a type ERROR under the old `Dict` bound.
  - The unused `TEvent` type parameter is gone: `Interpreter[Ctx]`, not
    `Interpreter[Ctx, Any]`. It appeared in zero signatures.
  - `send(..., wait=True)` types as `Receipt` (sync) /
    `Awaitable[Receipt]` (async); `wait=` and `priority=` are checked as
    `bool` instead of being swallowed into `**payload`. `from_snapshot()`
    and `SyncInterpreter.start()` return their own class, not the base.
  - `MachineLogic` callables pin arity and the guard's `bool` return: a
    two-argument action or a guard returning `str` is now a type error.
  - `BaseInterpreter` is exported for annotating plugin hooks.
  - The library itself is at **zero mypy errors** (was 61) and zero
    pyright errors; mypy runs in the CI lint job.
- **[wave 3] CLI: four more generated-code defects from executing the
  104-machine corpus.** (1) `"guard": "!name"` -- Stately's shorthand for a
  negated guard -- was taken literally and demanded a guard called `!name`;
  the engine (`GuardDefinition`) and the CLI IR now desugar it to
  `{"type": "not", "children": ["name"]}` so the stub emitted is `name`.
  (2) `onDone` on a compound/parallel STATE was skipped by the logic
  extractor, so its guard/actions were never stubbed. (3) A machine `id`
  that is also a stdlib module name (`token`, `queue`, `email`, ...)
  produced `token.py`, which shadowed the stdlib module `logging` imports
  and died mid-import with an unrelated `AttributeError`; such stems get a
  `_machine` suffix. (4) `camel_to_snake` was ASCII-only, so every
  Cyrillic/CJK/accented name collapsed to the fallback `machine` and each
  generated method overwrote the last; identifiers now keep Unicode
  letters (PEP 3131). Also: two different config names that sanitise to
  the same identifier (`fetch-data` / `fetch.data`) are de-duplicated
  (`fetch_data`, `fetch_data_2`) by one shared allocator that every
  emitter and every reference site read from.
- **[wave 3] Generated code binds Stately `inline:` action names** (CLI).
  Stately exports anonymous actions as `inline:machine.state#entry[0]`;
  every template turned that into an identifier-safe method name and then
  relied on name matching (`@action` -> camelCase; `LogicLoader` -> method
  name / camelCase), which can never reproduce a name with `:`, `.`, `#`
  or `[`. The generated code compiled and imported, but `start()` raised
  `ImplementationMissingError` on 26 of the 104 real-world corpus
  machines. All five templates now emit `@action("<original>")` when the
  name does not round-trip (ordinary camelCase names are unchanged), and
  `LogicLoader` honours that marker for both `logic_modules` and
  `logic_providers` -- so a hand-written provider can implement such a
  name too. Found by executing, not just importing, every generated file.
- **[wave 3] `RestoredError` is exported** from the package root. It is what
  `interpreter.error` holds after restoring a snapshot taken in the `error`
  status, and the docs showed it as importable, but it was missing from
  `__all__` -- found by executing every documentation sample.
- **[wave 3] `OverflowPolicy.BLOCK` self-send deadlock** (#38). A
  `send()` issued from inside an action while the bounded inbox was full
  suspended the run loop -- the only consumer of that inbox -- forever,
  with `status` still `"running"`. A send issued during a macrostep is
  now routed to the internal event queue (#36 semantics), so it is
  processed before the next external event instead of blocking.
- **[wave 3] Rollback now stops actors spawned by the failed
  transition** (#27, #60). Under `actionErrorPolicy: "rollback"` a
  `spawn_*` action that succeeded before a later action raised left its
  child running and registered although the transition was undone.
- **[wave 3] Children inherit the parent's `clock` and `strict`** (#49,
  #51), spawned or invoked, on both engines. A child spawned by the sync
  engine was built with a fresh `RealClock`, so a `SimulatedClock`-driven
  parent could not advance its children's `after` timers; and on both
  engines a child fell back to `machine.strict` even when the parent had
  passed `strict=True` to its constructor.
- **[wave 2] Pure API: history no longer leaks between calls** (#54).
  The cached probe reset everything except `_history`, so a history
  target in one `get_next_snapshot()` call resolved to wherever an
  unrelated earlier call had exited. History now travels WITH the
  `PureSnapshot`: chained calls keep resolving `p.hist` to where that
  chain left `p`; an unrelated or hand-built snapshot resolves it to the
  default child.
- **[wave 3] One core algorithm, two execution strategies** (#60). The
  step, transition-execution, state-entry/exit, lifecycle-action, and
  built-in-action logic is now implemented once on `BaseInterpreter`;
  `SyncInterpreter` inherits it unchanged and drives each coroutine to
  completion synchronously instead of re-implementing it as a parallel
  set of plain-`def` methods. No behaviour change is intended -- an
  action trace is now pinned byte-identical across both engines by test
  -- other than incidental bug fixes already released in earlier wave-3
  commits (e.g. `functools.partial`-wrapped async actions on the sync
  engine now raise `NotSupportedError` instead of having their coroutine
  silently discarded).

For full details, see the [`[Unreleased]` section of CHANGELOG.md](https://github.com/basiltt/xstate-statemachine/blob/main/CHANGELOG.md#unreleased).

---

## [0.7.0] — 2026-08-12

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
