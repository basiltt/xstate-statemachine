## Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] — targeting 0.8.1

### Fixed

- **Round-5 re-verification findings** (#142–#162; reopened #118, #122,
  #125, #133, #134). Twenty-six issues, every one reproduced against
  `main` with an independent probe before the fix and pinned in
  `tests/test_round5_findings.py` (52 tests, both engines wherever parity
  is the point).
  - **Configuration legality, both directions.** The mid-step snapshot
    guard tested "some atomic node is active"; in a `parallel` machine one
    region mid-transition left the other's leaf to satisfy it and the
    snapshot recorded a torn region (#142). Legality is now *exactly one
    active leaf per region* (`_configuration_is_legal`), used on the write
    side and mirrored on the read side: a `running` snapshot whose
    `configuration` lost its leaves restored as a live, permanently inert
    machine (#143) and is now `SnapshotCorruptError`.
  - **Hostile snapshot fields are typed** (#146): `version`, `status`,
    `history`, `actors`, `system`, `deferred` and a non-`str` payload all
    raised bare `TypeError` / `ValueError` / `AttributeError`; a pending
    event with a non-`str` `type` walked in through the restore door
    (#158). Every top-level key `from_snapshot` reads is now shape-checked
    and `restore_event` re-checks per record.
  - **`actionErrorPolicy: "fail"` stops the machine** as documented
    (#145): `status` is `"stopped"`, the configuration is cleared, children
    and timers are torn down, and the `TransitionFailedError` is retained
    on `.error`. Before, it parked in `"error"` still reporting the
    pre-transition leaf — a bricked machine that persisted as resumable.
    A child stopped this way fails its parent's `invoke` (`onError`) on
    both engines. Read side: an `"error"` snapshot with no recorded error
    is refused.
  - **`strict_targets=False` no longer reopens the root-target hole**
    (#147): the #108 rejection was emitted from the *unresolvable-targets*
    branch that the flag downgrades to a warning. It is now a
    non-downgradable `RootTargetError` on every flag setting.
  - **Two livelocks / budget faults on the sync engine.** A nested `invoke`
    whose `onDone` re-enters the common ancestor is a conservative cycle
    (dequeue one, enqueue one) that reset the chain budget every lap and
    hung `start()` for ever regardless of `maxIterations` (#144); a chain
    now ends only when nothing self-generated remains queued. The
    `always`-settle budget was reset per *drain*, so two independent
    events in one `send_events()` batch shared one allowance and the second
    tripped where `send(A); send(B)` did not (#151); it is per macrostep.
  - **Async run-loop death is published from the task** (#148): a cancel
    landing before the loop's first scheduling turn never entered the
    coroutine body, so #114's handler never ran — `status="running"`,
    `is_running=False`, `send(wait=True)` hung. A done-callback now fires
    for every way the task ends (`_die` is idempotent).
  - **Plain-`def` services run off the loop** (#149): #116 made them run
    inline so their completion lands at the same point as on the sync
    engine, at the price of blocking the event loop for the service's
    whole duration — every timer, actor and inbound send stalled. They
    now run on `Interpreter(service_executor=...)` (default: a small
    owned `ThreadPoolExecutor`) and the entering *macrostep* awaits the
    result, so #116's ordering holds while the loop keeps turning.
  - **`send_threadsafe` is classified and bounded on the calling thread.**
    An action that handed its own re-trigger to a worker thread was never
    charged to `maxIterations` (#150): the self-send decision is made on
    the caller's thread (context-inheriting threads/executors are
    recognised; a plain `threading.Thread` should pass `internal=True`),
    in-flight self-sends keep the chain alive, and the trip is
    observable. Under `OverflowPolicy.RAISE` a full inbox raises
    `QueueOverflowError` at the `send_threadsafe()` call site instead of
    on a future the fire-and-forget pattern never reads (#157).
  - **`guardErrorPolicy: "raise"` cancels only its own candidate** (#152):
    the exception used to abort the whole selection pass, so an unguarded
    fallback on an `invoke.onDone` was never taken and the completion was
    lost. The fallback is now taken; a caller-driven event still delivers
    the exception to the sync `send()` caller / async receipt, and an
    engine-driven one records it on `last_transition_ok` / `last_error`.
  - **Guard-denied is distinguishable from undeclared** (#153):
    `on_unhandled_event` reports `"guard_denied"` and `Receipt.denied` is
    `True` when a handler was declared but every guard refused.
  - **Sync engine parity for three round-4 fixes** (reopened): a deferred
    event's replay is its own macrostep on `SyncInterpreter` too — the
    caller's `Receipt` is final before any replay runs (#125);
    `on_resolve_error` fires from the shared algorithm, on both engines
    (#134); `forwardTo` shares `sendTo`'s unresolved-target reporting
    (`on_event_dropped(reason="unresolved_target")` + soft step error)
    through one helper (#133).
  - **Sync restore attaches the `SimulatedClock`** (#154): both restore
    branches of `start()` returned before `clock._attach(tick)`, so
    `restart_timers=True` re-armed deadlines nothing would ever drain.
  - **A user action named `spawn_*` is the user's** (#155): the built-in
    spawn prefix was resolved *before* `logic.actions`, the only built-in
    that claimed a name out of the user's namespace; discovery and the
    runtime now both prefer an implemented action.
  - **`escalate` reaches `onError` without an explicit `invoke.id`**
    (#156): the child records the invoke id its parent knows it by
    (`_invoked_as`) instead of parsing it back out of a runtime actor id
    whose first segment is the *service* key for anonymous invokes.
  - **Error hooks** (#159): new `on_invalid_event` and `on_snapshot_error`
    fire before `InvalidEventError` / `SnapshotMidStepError` /
    `SnapshotSerializationError` propagate.
  - **Redaction** (#160): `get_snapshot()`'s DEBUG log is redacted (it
    wrote the whole context verbatim, `LoggingInspector` or not);
    `DEFAULT_REDACT_KEYS` covers financial, session and personal
    identifiers (`iban`, `pan`, `cvc`, `bearer`, `cookie`, `session`,
    `signature`, `otp`, `pin`, `mnemonic`, `seed_phrase`, `dob`, `email`,
    `phone`, `passport`, …); `LoggingInspector` redacts service results
    and `DoneEvent` / `ErrorEvent` data.
  - **Dict-event validation is explicit** (#161): the mapping form
    requires a non-empty `str` `type` and `str` keys (non-`str` keys raise
    `InvalidEventError`); payload *values* are the caller's — documented
    on `send()` for both engines.
  - **v1 pending events are user events** (#162): re-deriving provenance
    from the *name* laundered a user's `after.hours` into an engine event
    exempt from `onUnhandled` / `strict`. Only the init sentinel keeps
    system provenance. See the migration note in Snapshots.
  - **Telemetry honesty** (#118): absent `AfterEvent.scheduled_for` /
    `fired_at` restore as `None`, never `0.0`; `lateness_ms` is `None`
    when unknown. **`tick()` contract documented** (#122): it drains what
    is *due*, does not advance time; a real-delay ladder needs one
    `tick()` per rung or a `SimulatedClock`.
- **Round-4 re-verification findings** (#102–#138; reopened #91, #99).
  Thirty-nine issues, every one reproduced against `main` with an
  independent probe before the fix and pinned in
  `tests/test_round4_findings.py`. Two blockers first:
  - **Mid-macrostep snapshots are refused** (#102): between a transition's
    exit set and entry set the configuration has no leaf; a snapshot taken
    there persisted `state_ids: []` and restored as a permanently inert
    machine reporting `running`. `get_persisted_snapshot()` now raises
    `SnapshotMidStepError` in that window.
  - **`SyncInterpreter.start()` terminates** (#103): a cross-region `always`
    into an invoking state re-armed the invoke on every settling pass and
    the microstep budget restarted at 0 each time, so it tripped forever.
    The budget is now per macrostep. A settle trip is also observable and
    leaves a legal configuration (#112).
  - **Engine parity.** A plain-sync `invoke` completes at the same point on
    both engines (#116 — the identical `(GO, CANCEL)×10` script gave
    `ok=10` on sync and `cancel=10` on async; the async engine now runs a
    non-coroutine service inline, and the sync engine queues an in-step
    completion ahead of the inbox, so `send_events([GO, X])` and
    `send(GO); send(X)` agree too); an unhandled invoked-child
    failure fails the parent on both (#99); `send()` to a stopped machine,
    the init `on_transition` record, and `stop()`'s abandoned events fire
    the same hooks on both (#123, #124, #129); the async trip spares engine
    completions like the sync one (#120).
  - **Async `send()` under `OverflowPolicy.BLOCK` enqueues eagerly** when
    the inbox has room (#104) — a fire-and-forget send was silently lost
    even on an empty inbox. An external producer sending during an
    in-flight step is no longer charged to `maxIterations` (#105): the
    self-send gate is now "issued from one of this interpreter's actions",
    tracked per task, not "the loop is busy".
  - **Persistence.** The priority (fired-timer) lane is persisted (#107);
    `after` timers can be re-armed on restore with `restart_timers=True`
    and `has_dormant_timers` reports when they are not (#128);
    `from_snapshot(clock=)` (#117); malformed snapshots raise
    `SnapshotCorruptError` (#110); non-JSON pending data raises
    `SnapshotSerializationError` instead of being stringified (#131);
    `AfterEvent` lateness telemetry round-trips (#118); `status` after a
    restore is documented as not-a-liveness-signal (#135).
  - **Provenance.** `send(engine_event, wait=True)` no longer strips the
    engine marker (#111); the marker survives `deepcopy` / `pickle` (#138);
    `is_system_event`, `system_event`, `DoneEvent`, `AfterEvent`,
    `ENGINE_EVENT_SHAPES` are exported and documented (#137);
    `Receipt.deferred` bookkeeping is per-step and by reference, so it can
    neither grow nor mislabel an unrelated later event (#106); a deferred
    event's replay is its own macrostep and no longer folds into the
    triggering event's `Receipt` (#125).
  - **Actors.** `done.invoke` carries the child's declared `output`, not
    its private context (#109); `escalate` from an invoked child reaches
    the parent's `onError` (#130); a `sendTo` with no live target fires
    `on_event_dropped(reason="unresolved_target")` and marks the step
    (#133).
  - **Validation.** A transition targeting the machine root is rejected at
    build (#108); a bare `stateIn` name that is ambiguous in the machine is
    rejected at first use (#132); a self-referential config dict raises
    `InvalidConfigError` instead of `RecursionError` (#136); a non-`str`
    event `type` raises `InvalidEventError` (also a `TypeError`) instead
    of escaping the hierarchy (#113); two *config* names that normalise
    equal and resolve to one callable warn (#91); a duck-typed logic
    object is copied like a `MachineLogic` (#121).
  - **Plugins.** A hook raising `asyncio.CancelledError` is contained like
    any other failure, and an externally cancelled run loop flips `status`
    to `error` and fails pending receipts instead of leaving a dead machine
    reporting `running` (#114); an `async def` hook is reported via the new
    `on_plugin_error` / `last_plugin_error` instead of silently never
    running (#127); `on_resolve_error` (#134); `LoggingInspector` redacts
    sensitive keys by default (#126).
  - **Timers.** `SyncInterpreter.tick()` drains chained due deadlines in
    one call (#122); `SimulatedClock` detaches an interpreter's settle hook
    on teardown (#115).
  - **Ride-alongs found while landing #102 / #116.** A non-blocking
    `spawnChild` on `SyncInterpreter` now *starts* the child on the
    spawning thread (its pump thread only ticks it), so a snapshot, `sendTo`
    or `stop_child` issued right after the spawn sees a fully entered child
    and its grandchildren — previously a load-dependent race. The #102
    mid-step refusal applies to the root of `get_persisted_snapshot()`
    only; a child actor caught mid-step is waited for (bounded) instead of
    failing the parent's snapshot. A plain `def` service that returns an
    awaitable, or a `unittest.mock.AsyncMock`, that *fails* now reaches
    `onError` on Python 3.9–3.11 too.
- **Round-3 re-verification findings** (#84–#99; reopened #31, #77, #79).
  Every item was reproduced against `main` before the fix and pinned in
  `tests/test_round3_findings.py`.
  - **`Receipt.deferred`** (#84): an event held by `onUnhandled: "defer"`
    resolved `changed=False, error=None` — indistinguishable from a correct
    no-op. The receipt now says `deferred=True`.
  - **Provenance is not forgeable** (#85): `Event(system=True)` let user
    code mint engine-status events that bypassed `strict`, `onUnhandled`
    and `"*"`. The public constructor has no such parameter; `Event.system`
    is a read-only property backed by an engine-private identity sentinel
    that only `system_event()` can set.
  - **Provenance and engine events survive a snapshot** (#86, #87): pending
    `DoneEvent` / `ErrorEvent` were silently dropped by
    `get_persisted_snapshot()`, and a restored engine `Event` became user
    traffic that failed an `onUnhandled: "error"` machine. Snapshot layout
    **v2** persists a `kind` per record and round-trips every event class;
    v1 restores unchanged.
  - **Runaway-chain trip is observable** (#77 criterion 6): the triggering
    receipt carries `RunawayChainError`, `last_transition_ok` is `False`,
    `last_error` is set, and `on_event_dropped(reason="chain_budget")`
    fires per discarded event — on **both** engines.
  - **`tripped` is per chain** (#88): one runaway no longer starves
    unrelated events queued behind it in the same `send_events()` batch.
  - **Completions are never discarded** (#94): a `done.invoke` /
    `error.platform` arriving during or after a trip is delivered, so a
    trip can no longer strand the machine in the invoking state. It is still
    counted, so a rollback→re-arm→done cycle remains bounded.
  - **Async action-side `send()` is budgeted** (#90): an action calling
    `await interp.send(...)` on its own interpreter spun unbounded; it now
    routes to the internal queue and counts against the chain like `raise`.
  - **`**kwargs` is not consent** (#89): a legacy clock wrapper forwarding
    `**kwargs` was fed `sync=`; only an explicitly named parameter opts in.
  - **`create_machine()` no longer mutates the caller's `MachineLogic`**
    (#92): aliases are resolved into a machine-owned copy of each registry,
    so a second machine from the same logic still trips the ambiguity guard
    and an earlier machine is never retroactively rebound.
  - **Shadowed near-duplicates warn** (#91): an exact key still wins by
    design, but if a *different* callable is also registered under a
    spelling that normalises to it, a `UserWarning` names both.
  - **`logic_modules` / `logic_providers` apply the ambiguity rule** (#93):
    two different callables whose names normalise equal, for a name the
    machine requires, are `InvalidConfigError` instead of iteration-order
    roulette. The legacy forward snake→camel alias that masked this is gone.
  - **Library no longer reads `ErrorEvent.data`** (#95), so
    `-W error::DeprecationWarning` CI passes.
  - **`_resolve_event_spec` always yields a dict payload** (#96): an
    `ErrorEvent` re-sent through `sendTo`/`forwardTo` carried the exception
    *as* the payload; it is now `{"error": exc, "src": id}`.
  - **`escalate` mints an `ErrorEvent`** (#97) — the one failure path that
    still delivered a plain `Event`.
  - **Strict mode exempts by provenance only** (#98): forged engine-shaped
    user events (`done.invoke.NEVER`, `after.party`, `xstate.whatever`,
    `___xstate_forged`) are rejected like any undeclared name.
  - **`SyncInterpreter` delivers `onError` for a failed invoked child
    machine** (#99), and fails the parent when no handler is declared —
    parity with the async engine and with failing callable services.
  - **Engines cut a deep chain at the same link** (#77 ride-along): the
    sync budget counted raises seeded by `start()`'s initial entry; the
    async one did not, so a 1 001-deep chain landed on `s1000` vs `s1001`.
    Pre-drain internals now have user-event standing on both engines.
  - **`_SIBLING_FALLBACKS_WARNED` is bounded** (#31 ride-along) to 1 024
    pairs; a long-lived process no longer accumulates entries forever.
  - **Runtime parity for unresolvable targets under `strict_targets=False`**
    (#31): both engines now expose the same surface — `StateNotFoundError`
    on the receipt, `last_transition_ok=False`, `last_error` set, machine
    still `running`; the sync engine additionally raises from a
    fire-and-forget `send()` as before.
- **`send(event, wait=True)` no longer hangs when one `Event` instance is
  in flight twice** (#75, #39). Receipts were keyed on `id(event)`, so two
  concurrent sends of the same pre-built `Event` collided and the first
  awaiter never resolved — no error, no timeout, and `stop()` could not
  reach it. The queued envelope now gets its own identity; the caller's
  object is never mutated and reuse as a template is fine.
- **`SyncInterpreter` `after` deadlines are reachable by `tick()` even when
  the interpreter is constructed inside a running asyncio loop** (#76, #50).
  `RealClock.set_timeout` chose its lane by whether a loop happened to be
  running on the calling thread; a sync machine built inside one parked
  its timers on `loop.call_later`, where its own pump could not see them.
  The lane now follows the *owning engine* (`sync=` on `set_timeout`);
  third-party clocks written against the 0.8.0 `Clock` protocol still work
  — the engine inspects `set_timeout`'s signature once at construction and
  calls it exactly once, so a clock's own errors surface unchanged.
- **`SyncInterpreter` no longer discards a batch of more than
  `maxIterations` external events** (#77). The runaway guard counted every
  dequeued event and `clear()`ed the inbox on overflow, so
  `send_events(["T"] * 1501)` processed 1000 and silently dropped 501. It
  now budgets only *self-generated* work — events that arrive while the
  drain is running (a `raise`, an action calling `send()` on its own
  interpreter, a `done.invoke` from a sync service, a due timer). Every
  event that was in the inbox when the drain began, or is replayed from the
  defer buffer, is processed in full regardless of count. The budget is
  per *chain*, matching the async engine: it resets whenever a macrostep
  generates nothing, so 3 000 independent one-deep `raise`s in one batch
  are all delivered, while a self-feeding loop is still broken and only the
  generated tail is discarded — never events the caller was told were
  accepted. The 0.8.0 note claiming the two engines already agreed was
  wrong; they do now, and an engine-parity test pins it.
- **System-event exemption is decided by provenance, not by name** (#79).
  The `"*"` / `"prefix.*"` wildcard matcher, `onUnhandled` and `strict`
  mode used to exempt any event whose *type* began with `done.`, `error.`,
  `after.` or `xstate.` — so a user-sent `done.review` was invisible to
  `"*"`, could not trip `onUnhandled: "error"`, and passed `strict`
  undeclared. The engine now flags the events it mints (`DoneEvent`,
  `ErrorEvent`, `AfterEvent`, and `Event.system=True` for its sentinels,
  `escalate` and restore) and the three checks consult that flag. A user
  event is user traffic whatever it is called; engine events remain exempt
  with no regression to the 0.8.0 `escalate` / `onUnhandled` fix. The
  build-time reserved-namespace warning added earlier in this release is
  withdrawn — its premise no longer holds.
- **An invoked child actor costs one asyncio task, not two** (#43). The
  parent no longer runs a manager task per child that sat awaiting
  `wait_done()`; completion is pushed from the child's terminal listener
  the instant its status flips, and exiting the owning state stops its
  children directly. 50 idle children add ≤ 51 tasks over baseline
  (pinned), the loop schedules no timer callbacks while they idle
  (pinned), and `onDone` latency is sub-2 ms median (pinned). The
  `Production Characteristics` task budget is now `children + 1`.
- **`send_threadsafe()` applies `strict` and `event_schemas`** (#78, #51).
  It skipped `_check_strict`, so the *recommended* cross-thread path was the
  one without the guardrail — a typo'd event was accepted and dropped, and a
  payload the schema rejects drove a real transition. It now raises
  `UnknownEventError` / `InvalidEventPayloadError` on the calling thread
  before anything is queued, exactly like `send()`.
- **`actionErrorPolicy: "rollback"` / `"fail"` withdraws events `raise`d by
  the failed action list** (#27). Rollback restores configuration and
  context; it cannot un-send a `sendTo` (that effect has left the machine),
  but a `raise` is an event the machine queued *for itself* and had not yet
  processed, so it is now dropped instead of being delivered into a
  configuration the undone transition never reached. Events raised by
  *earlier* transitions are untouched.
- **The `actionErrorPolicy` default-flip `DeprecationWarning` fires once per
  process, not once per `MachineNode`** (#27). A service building
  interpreters from one module-level machine used to see it exactly once,
  ever — typically in a warm-up path nobody reads.
- **`rollback` no longer checkpoints context on transitions that run no
  actions** (#27). The per-transition deep copy cost ~22 % throughput on an
  idle `rollback` machine; it is now skipped when neither the transition,
  the exited states nor the entered subtree declare any action
  (≈ 0.98× of the default on the same benchmark).

### Added

- **`Interpreter(service_executor=)`**, **`send_threadsafe(internal=)`**,
  **`Receipt.denied`**, `on_unhandled_event` disposition `"guard_denied"`,
  **`on_invalid_event`** / **`on_snapshot_error`** plugin hooks.
- **`SnapshotMidStepError`, `SnapshotCorruptError`,
  `SnapshotSerializationError`, `InvalidEventError`, `RootTargetError`** —
  typed members of the `XStateMachineError` hierarchy for the conditions
  above.
- **`from_snapshot(clock=, restart_timers=)`**, **`has_dormant_timers`**.
- **`on_resolve_error`**, **`on_plugin_error`** plugin hooks;
  **`interpreter.last_plugin_error`**.
- **`LoggingInspector(redact_keys=, log_context=)`**, `redact()`,
  `DEFAULT_REDACT_KEYS`.
- Package-root exports: `is_system_event`, `system_event`, `DoneEvent`,
  `AfterEvent`, `ENGINE_EVENT_SHAPES`.
- **`interp.last_error`** — the exception behind the most recent
  `last_transition_ok=False`, on both engines, so a fire-and-forget caller
  can detect a failed step without `wait=True`.
- **`RunawayChainError`** — carried on receipts / `last_error` when a
  self-generated chain exceeds `maxIterations`.
- **`events.persist_event` / `events.restore_event`** — the snapshot record
  codec for every event class (layout v2).
- **`has_dormant_invocations`** on both engines (#44). After a static
  `from_snapshot()` the machine reports `status == "running"` — it *is*
  processing events — while every `invoke` in the configuration is parked.
  `status` is therefore not a liveness signal after a restore; this boolean
  (and `pending_invocations()`) is. A new `status` value was rejected
  because it would break every consumer switching on the existing four.
- **`MachineLogic(strict=True)`** (#52). Refuses to register an undecorated
  public method: `InvalidConfigError` at construction instead of an
  arity-based guess plus a `UserWarning`. Decorated methods and `_private`
  helpers are unaffected. Default `False`; behaviour unchanged unless set.
- **Static `raise` targets are validated at build time on `strict`
  machines** (#51). `_check_strict` already ran on the `raise` built-in, but
  under the default `actionErrorPolicy: "continue"` that failure was
  contained like any action error — logged, hooked, transition committed —
  so a typo'd internal event never *raised* to anyone. A literal event name
  in the config is a configuration error; `create_machine()` now rejects it
  with a `Did you mean …?` suggestion. Dynamic (callable) `raise` events are
  still checked at runtime.
- **`ErrorEvent`** (#80). Service and child-actor failures are delivered
  as a dedicated `ErrorEvent(type, error, src)` instead of a `DoneEvent`
  whose `data` happened to hold an exception — `onError` handlers can now
  branch on `isinstance(event, ErrorEvent)` or read `event.error`, as in
  XState v5. `DoneEvent` is used only for success (`done.invoke.*`,
  `done.state.*`). `ErrorEvent.data` still returns the exception with a
  `DeprecationWarning` and is removed in 0.9.
- **`events.ENGINE_EVENT_SHAPES`** — the exact name shapes the engine
  synthesises (`done.invoke.`, `done.state.`, `error.platform.`, `after.`,
  `xstate.`, the sentinels), for build-time checks and documentation.
  `SYSTEM_EVENT_PREFIXES` remains exported for compatibility.
- **snake_case ↔ camelCase logic names, everywhere.** A PEP 8 Python
  function now implements the camelCase name in an XState config through
  *every* entry point — `MachineLogic(actions={"store_user": fn})`,
  `MachineLogic` subclass methods, `logic_modules`, `logic_providers`, and
  the Pythonic decorators. Matching is case- and separator-insensitive on
  both sides (`normalize_logic_name`), so acronyms (`logHTTPStatus` ↔
  `log_http_status`), digits (`fetchUserV2` ↔ `fetch_user_v2`) and Stately's
  non-identifier names (`inline:m.a#entry[0]` ↔ `inline_m_a_entry_0`,
  `fetch-data` ↔ `fetch_data`) all bind without an `@action("…")`
  decorator. Previously only `logic_modules`/`logic_providers` mapped names,
  via a forward snake→camel conversion that was lossy for acronyms and
  undefined for non-identifiers; an explicit `MachineLogic` dict with
  snake_case keys raised `ImplementationMissingError`. Aliases are resolved
  once in `create_machine()` (`resolve_aliases`) so the interpreter hot path
  is unchanged. An exact-name entry always wins over an alias.

### Changed

- **`actionErrorPolicy: "fail"` now leaves `status == "stopped"`**, not
  `"error"`, with the configuration cleared (#145). Code that checked
  `status == "error"` after a policy halt should check `"stopped"` (or
  `interp.error is not None`). `"error"` remains the status for an invoked
  service that died.
- **`guardErrorPolicy: "raise"` takes the fallback candidate** before
  surfacing the exception (#152); a machine that relied on the raise
  aborting the whole array now lands on the fallback.
- **`Receipt` gained a fifth field, `denied`** (#153). A positional
  destructure of exactly four fields now raises `ValueError`; read fields
  by attribute.
- **`AfterEvent.scheduled_for` / `fired_at` are `Optional[float]`** and
  `lateness_ms` is `Optional[float]` (#118): `None` means "not recorded".
- **v1 persisted events with engine-shaped names restore as user events**
  (#162). See Snapshots for the one-time re-persist note.
- **`Receipt` gained a fourth field, `deferred`** (#84 in this release;
  flagged as undeclared by #119). A positional destructure written for
  0.8.0 — `state_ids, changed, error = receipt` — now raises `ValueError`.
  Destructure by attribute, or `state_ids, changed, error, _ = receipt`.
- **`WrongThreadError` message corrected** (#37). It claimed events sent
  from a foreign thread "would be silently lost", which was false for the
  correct 0.7.x idiom `asyncio.run_coroutine_threadsafe(interp.send(…),
  loop)` — that form *worked* in 0.7.x and is rejected since 0.8.0 because
  the thread check runs before the coroutine is scheduled. The message now
  names that idiom explicitly and points to `send_threadsafe()`. **This is a
  0.8.0 behavioural break for previously-correct code** that the 0.8.0 notes
  omitted; see *Sending from Another Thread* in the interpreters guide.
- **Ambiguous logic registrations are rejected.** Registering two
  *different* callables whose names differ only by case or separators
  (`fetch_data` and `fetchData`) for a name the machine requires now raises
  `InvalidConfigError` at build time instead of silently picking one.
- Every Python snippet in the guides and README now uses snake_case
  implementations against camelCase JSON, matching what `xsm gt` generates.

### Performance

- **Hot-path work, measured on the cross-library benchmark** (same host,
  Python 3.14, `benchmarks/competitors/run.py`; details in the PR). Nothing
  observable changed -- every shortcut is pinned by
  `tests/test_perf_hot_path.py` and the full parity suite.
  - `create_machine()` builds the tree **once**: auto-discovery used to
    construct a throwaway `MachineNode` just to collect required names,
    then the real one -- 43% of construction time. The loader now walks the
    tree it is handed, and the required-name walk is memoised on the machine.
  - `_accepts_kwarg` (the 0.8.0-clock `sync=` probe run in every
    interpreter `__init__`) is memoised per function; `inspect.signature`
    was 32% of interpreter construction.
  - **Static transition geometry is memoised** on the
    `TransitionDefinition` (domain / LCCA and entry path), keyed on the
    resolved target's identity so live-resolved targets are never served a
    stale plan. The exit set stays dynamic. ~6 µs of a 21 µs flat
    macrostep.
  - No coroutine is created for an **empty action list** (entry, exit,
    transition): the sync engine's trampoline paid two frames per entered
    state for nothing.
  - `send()` fixed costs trimmed: `Clock.pump()` returns immediately on an
    empty heap; `_check_strict` is one attribute read when not strict and
    no schemas; the reserved-key scan skips empty payloads; hot-path
    `logger.debug` calls sit behind one `isEnabledFor` per macrostep.
  - **`Receipt` no longer deep-copies `context`** on a machine that
    declares no actions anywhere (`MachineNode.context_is_immutable`):
    nothing can mutate it, so `changed` is the configuration compare.
  - The async run loop yields to the event loop every
    `Interpreter._INBOX_YIELD_EVERY` (16) inbox events instead of every
    one; the #48 fairness bound for `call_later` timers is now N events
    (microseconds) rather than one, and `send(wait=True)` throughput rises
    ~35%. Priority and internal lanes are still checked before each take.
  - Net, full cross-library harness (median of 7, GC off, same session):
    flat toggle 48.6k → 62.4k ev/s (+28%), nested 20.8k → 25.9k (+24%),
    parallel 37.6k → 44.5k (+18%), construction 5.9k → 9.4k machines/s
    (+61%), 1,000 instances 17.1k → 28.3k/s (+65%), delayed transitions
    6.8k → 8.9k timers/s (+31%), async `send(wait=True)` 23.5k → 27.1k
    (+15%). Construction and 1,000-instances are now the fastest of the
    four libraries benchmarked.

### Removed

- **Dead CLI code**: `generator._generate_logic_header` /
  `_generate_logic_component` (superseded by the `strategies/` templates
  in 0.7.0) and `strategies._shared.collect_all_states` /
  `collect_all_transitions` / `_resolve_target` (superseded by the typed
  IR in `cli/ir.py`). None was reachable from any command; ~390 lines.

### Deprecated

- **The 0.7.x sibling reading of a leading-dot target now warns** (#31).
  `{"target": ".b"}` on a state with no child `b` still resolves to the
  sibling, but emits a `DeprecationWarning` (once per source/target pair)
  naming the unambiguous `#machine.path` spelling and the `strictTargets`
  switch. This was acceptance criterion 2 of #31 and did not ship in 0.8.0.
  The fallback is removed in 1.0.

### Documentation

- **Site redesign, round two.** Light theme by default (dark is remembered
  once chosen — the previous build forced dark and persisted it on first
  load), emerald→teal→blue accent, darker dark mode, readable sidebar and
  table-of-contents active states, zebra-striped tables, theme-aware code
  blocks and code tabs, an orange event pulse on the landing statechart.
- **Every hand-drawn ASCII diagram replaced with a live Mermaid statechart**
  (43 across the guides) with a full-screen viewer, zoom, and consistent
  padding; edge labels are legible in both themes.
- New **Reliability & Failure Policies** guide collecting the 0.8.0 hardening
  surface with a runnable example per policy; FAQ grown from 19 to 36
  questions; a *Naming* section in Core Concepts; emoji signposting on
  section headings throughout.
- Two pre-existing broken in-page anchors fixed (`cli`, `troubleshooting`);
  the docs link checker now models kramdown and GitHub slugging separately.
- **Mobile pass.** Tables are wrapped in a scroll container with a sticky
  first column (the old `display:block` table gave scroll but broke
  `width:100%`, so rows shrank to content on every screen size); phone
  breakpoint tightens the type scale and gutter, stacks the hero CTAs, and
  separates the three floating controls that shared one corner. The
  Requirements table now lists Python 3.9 – 3.14.

## [0.8.0] - 2026-09-17 — Fortify

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
  The async engine already behaved correctly. *(0.8.1 note: plain
  external events were still counted and could be discarded — see
  #77 above; the two engines agree as of 0.8.1.)*
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


## [0.7.0] - 2026-08-12

**The code generator rewrite.** An audit of the five code-generation templates
found that three of them — every `pythonic-*` template — produced machines that
did not match their source JSON, on inputs as simple as a two-state machine.
Two failed *silently*, with exit code 0.

Measured on the 104-machine real-world corpus, round-trip fidelity went from
**0/104 to 103/104** for all three templates. The single exclusion has no
`states` key and is rejected by `create_machine()` too.

> [!IMPORTANT]
> If you generated code with `pythonic-class`, `pythonic-builder` or
> `pythonic-functional` on 0.6.0 or earlier, **regenerate it**. The output was
> not a faithful representation of your machine. `xsm generate-template … --diff`
> will show you exactly what changes.

### Fixed — silent wrong output (these produced working-looking, broken code)

- **`pythonic-functional` produced machines with zero transitions.** The emitter
  wrote `idle.to(busy, event="GO")` as a bare expression. `State.to()` *returns*
  a `Transition`; it does not register one. The value was discarded and
  `build_machine()` was called without it. Every machine this template ever
  produced could start and then never move — including a flat two-state one.
- **`pythonic-builder` silently dropped every nested state.** It never recursed
  into `states`. One level of nesting lost two of four states, so the generated
  code ran as a *different machine* and stubs were written against behaviour
  that did not exist.
- **`pythonic-class` failed to build at all**, raising
  `InvalidConfigError: Multiple initial states`. Nested states were emitted as
  sibling class attributes, and the metaclass treats every class-level `State`
  as top-level — so a child marked `initial=True` became a second initial state
  of the machine.
- **Colliding state names destroyed states.** `"my-state"` and `"my_state"` both
  sanitised to `my_state`; the second assignment silently overwrote the first.
  In the reproducer the casualty was the machine's *initial* state.
- **`final`, `after`, `always`, `parallel`, `history`, `tags` and `meta` were
  dropped** by all three templates, so machines never completed, `onDone` never
  fired, and timers vanished.

### Fixed — hard failures

- **Composite guards were never extracted.** `{"type": "and", "params":
  {"guards": [...]}}` was tested with `isinstance(value, str)`, so the real leaf
  guards were never stubbed and the machine died at runtime with
  `ImplementationMissingError`.
- **Named delays were never collected.** `after: {"BACKOFF": …}` produced no
  `delays=` stub, and the transition silently never fired.
- **Python keywords as state or service names emitted invalid code** — a service
  named `None` produced `None = none`, a `SyntaxError`.
- **Non-ASCII state names produced invalid Python.** Cyrillic and CJK names were
  emitted verbatim as variable names.

### Added

- **Golden round-trip harness.** Generated code is now compiled, executed, and
  the machine it builds compared structurally against
  `create_machine(source_json)`. The pre-existing CLI tests asserted on generated
  *strings* — one literally asserted `"green.to(yellow"`, pinning the defect as
  correct behaviour, and passed for the entire life of the bug.
- **The generator refuses to emit an unfaithful machine.** Verification runs
  *before* anything is written; a mismatch prints what diverged and exits 1.
  Nothing is written. `--no-verify` opts out.
- **`--check` and `--diff`** — regenerate in memory and exit 1 if the files on
  disk differ. Makes generated code safe to commit and keeps it honest in CI.
  Both are strictly read-only and never prompt.
- **Provenance header** in every generated file: source JSON, template,
  generator version, and the exact command to regenerate.
- **Support matrix** in `xsm list-templates`, showing which templates build the
  machine in Python (and are structurally verified) versus which load JSON at
  runtime.
- **`[format]` extra** — `pip install "xstate-statemachine[format]"` pulls in
  `black` and `isort` so generated code is line-wrapped. The core library keeps
  its zero runtime dependencies; without the extra the output is still valid
  and faithful, just not reformatted, and the CLI says so.
- **`State(history=…)`, `State(tags=…)`, `State(meta=…)`** on the Pythonic API.
  These were previously unrepresentable, so *no* emitter could have preserved
  them.
- **`build_machine(root=…)` and `MachineBuilder.root()`** for machine-level
  `on` / `entry` / `exit` / `tags` / `type: parallel`. Without these a global
  escape transition such as `on: {EMERGENCY: …}` simply stopped existing.

### Changed

- **Generated code now passes `black --check` and `pyflakes` cleanly.** Unused
  imports are pruned per-machine; previously a simple machine arrived with
  `Optional`, `Union` and `Interpreter` unused (14 flake8 findings).
- **Generated runners demonstrate a reachable path.** Events were previously
  sent in *alphabetical* order, so a demo could end by firing an event nothing
  handles. The runner now walks the machine and emits only transitions that can
  actually fire — 94% of emitted events move the machine, measured on the corpus.
- **Removed the `await asyncio.sleep(0.1)` placeholder** from async action stubs.
  It was justified as making the stub "awaitable", which is false — an
  `async def` is awaitable regardless. It only injected 100 ms of real latency
  into every action of a machine the user had not written yet.

### Changed — Pythonic API now matches the JSON engine

The Pythonic API had drifted **stricter** than the config format it wraps,
raising on machines `create_machine()` accepts. That made a whole class of real
Stately exports impossible to code-generate. These now warn instead of raising,
exactly as the engine does:

- A compound state (or machine) with child states but no `initial`.
- A `final` state with outgoing transitions — real exports ship these as
  "undo" / "reconsider" transitions. `final` with *children* is still rejected.

If you relied on these raising, they now emit a `WARNING` and continue.

## [0.6.0] - 2026-08-10

**XState v5 feature parity, plus a full correctness pass.** This entry covers
everything shipping in 0.6.0. Neither 0.5.1 nor the earlier 0.6.0 development
builds were ever published to PyPI, so for anyone upgrading from **0.5.0** this
is the single relevant changelog entry.

### Added — observability for contained action errors

- **`PluginBase.on_action_error`** — action failures are contained so a buggy
  side effect cannot kill a long-lived machine, but that also made them
  invisible: the transition completes as though the action succeeded. This
  hook fires on both engines, for user actions and built-in creators, so a
  failure can be routed to Sentry, a metric, or a dead-letter queue.

  > Upgrading from 0.5.0 and relying on `send()` re-raising? See the
  > [migration notes](https://basiltt.github.io/xstate-statemachine/guide/getting-started/#upgrading-from-older-versions).

### Fixed — pre-release hardening

Defects found by an adversarial battle test run against the merged release
branch. None reached PyPI. Six were release blockers.

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

### XState v5 feature parity

Closes all 73 gaps catalogued in `docs/FEATURE_GAP_ANALYSIS.md` — every one
verified by an executable probe.

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

[Unreleased]: https://github.com/basiltt/xstate-statemachine/compare/v0.8.0...HEAD
[0.8.0]: https://github.com/basiltt/xstate-statemachine/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/basiltt/xstate-statemachine/compare/v0.6.0...v0.7.0
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
