---
title: "Changelog"
description: "Release history and what changed in each version."
---

# Changelog

All notable changes to XState-StateMachine for Python are documented here.

For the full changelog with commit history, see [CHANGELOG.md on GitHub](https://github.com/basiltt/xstate-statemachine/blob/main/CHANGELOG.md).

---

## [Unreleased] — targeting 0.8.1

**Naming, and the site.**

### Fixed

- **Round-7 re-verification findings** (#179–#190; reopened #167, #168,
  #175). Every one reproduced against `main` @ `221ce7c` with the
  reporter's standalone repro before the fix (all twelve exited 1) and
  pinned in `tests/test_round7_findings.py` (37 tests). **Every test that
  involves a service or an action is parametrised over `def` / `async def`**
  and runs both engines where parity is the point — the round-6 pins were
  spelled `def` only and were structurally blind to the coroutine lane; the
  #167/#168 pins are retrofitted the same way.
  - **One charged lane for every completion (#179; reopened #167/#168).**
    An `async def` service's `done.invoke` (and an invoked child's terminal,
    and `error.platform` on every path) was published via `send()` onto the
    public inbox, where it was never charged to the chain budget and, arriving
    `from_inbox`, reset the settle budget on every lap — so `maxIterations`
    was inert for any machine whose services were `async def`, the style the
    docs recommend, while the identical `def` service tripped. All
    completions now go through `_publish_completion` → the priority lane,
    marked as engine completions and charged. A step that armed a coroutine
    service keeps its chain open until the completion lands
    (`_chain_owed`); a step that armed nothing still ends the chain, so a
    long service beside independent traffic never accumulates. Both service
    kinds now trip at the same lap count as the sync engine.
  - **External `send(priority=True)` is never charged (#180).** The priority
    lane charged whatever arrived while a step was open — provenance by
    *timing*. A producer whose send landed mid-macrostep lost ~50% of its
    events as `chain_budget`, the failure #105 fixed on the inbox lane
    resurfacing here. Accounting is by *who issued it*: only engine
    completions and self-raised events count.
  - **`start()` bounds the wait for invoked children (#181).**
    `start(children_timeout=)`, default `DEFAULT_CHILDREN_TIMEOUT` (2 s); a
    slow child's `async def` entry action no longer holds `await start()`
    for its whole duration. On timeout a WARNING is logged, `start()`
    returns with the machine running, and the child registers when its
    bring-up completes.
  - **The in-flight flag covers `start()` (#182) and every action hook
    (#187).** The initial descent runs entry actions and writes context, but
    `_processing` was left `False`, so a snapshot from an initial entry
    action was accepted and torn on the async engine while the sync engine
    refused it. The flag is set for the whole descent and cleared in a
    `finally`. `on_action_execute` is inside the refusal window on both
    engines.
  - **A child mid-step is never harvested half-applied (#183), and the wait
    never spins the event loop (#184).** The child branch tested
    configuration *legality*, which is true inside an entry action while
    the context is half-written; and `_await_settled_for_snapshot` spun
    `time.sleep` on the event-loop thread, so an async child could not
    progress, the wait burned its full 0.5 s and then returned the torn
    blob anyway. Now: a child stepping on another thread (a non-blocking
    sync actor) is waited for until *settled*; a child on the caller's own
    thread is refused instantly with `SnapshotMidStepError(child=True)`.
  - **Null/absent `machine_hash` on a versioned payload is drift (#185).**
    The v0 bypass was keyed on the field's presence, so a `version: 2` blob
    that lost its hash in transit restored into a drifted machine silently.
    The bypass is keyed on the declared version; `verify_machine_hash=False`
    remains the explicit opt-out.
  - **A `configuration` that contradicts `state_ids` is corrupt (#186).**
    `configuration or state_ids` let an emptied or rewritten
    `configuration` silently win or silently lose; the two must agree or
    the blob is refused with `SnapshotCorruptError`.
  - **`SyncInterpreter` clears its per-step scopes on every step (#188).**
    `_deferred_this_step` was cleared only on the `wait=True` path and grew
    unbounded under fire-and-forget sends, contaminating the next receipt's
    `deferred`.
  - **The `onUnhandled: "error"` kill is on the sender's receipt (#189).**
    `Receipt.error` is the `UnhandledEventError`; a success-shaped receipt
    no longer goes back to the caller whose event stopped the machine.
  - **A `"*"` handler does not defeat `strict` (#190).** `is_known_event()`
    answered the *dispatch* question ("would some handler match?") so one
    wildcard anywhere silently disabled event-name enforcement for the whole
    chart. It now answers the *declaration* question; the validator's
    `raise` check asks the dispatch question explicitly
    (`wildcard_matches=True`). Dispatch is unchanged.
  - **#175 case D pinned as filed:** N sends of one reused `Event` instance
    followed by `stop()` before the loop runs resolve every receipt as
    `InterpreterStoppedError`; across the racing window a receipt is `ok`
    iff its event was applied and every event still queued at `stop()` is
    stopped.
  - **#174 re-measured on the fixed tree:** `after: 50` under a 100-event
    busy loop on the same machine, and under 100 busy machines sharing the
    loop, is 0–1 ms late (median of 5). The plain-`def`-service case is
    unchanged and documented; `async def` — now budget-safe — is the
    documented remedy and fires on time (122 ms for `after: 100` beside a
    500 ms service).
- **Loop-side `RAISE` refusals from `send_threadsafe()` are observable**
  (#157, reopened). The call-site `qsize()` check is optimistic; under
  load — the only time backpressure matters — a concurrent producer is
  refused *on the loop*, and that refusal landed only on the future the
  fire-and-forget pattern never reads: correct load shedding with a hidden
  shed rate. The future still carries the error; the interpreter now also
  logs a WARNING and fires `on_event_dropped(reason="queue_full")` for
  each such refusal. Same-thread `send()` under `RAISE` is unchanged — the
  exception reaches the caller and *is* the signal.
- **Round-6 re-verification findings** (#166–#175; reopened #122). Every one
  reproduced against `main` with an independent probe before the fix and
  pinned in `tests/test_round6_findings.py`, both engines wherever parity is
  the point. Three of the four candidate blockers were "fixed on the engine
  the issue was filed against"; the fixes below are on the async engine and
  each test runs the sync engine alongside it.
  - **Every self-generated cycle is bounded on `Interpreter`.** An `always`
    into a child whose plain service finished inside the settle pass hung
    `send(wait=True)` for ever (#166): the settle budget was a local
    counter per call, restarting at 0 on every completion-driven re-entry.
    It is now per macrostep on the instance, reset only when an external
    event begins its step — the sync engine's #103/#151 rule — and a trip
    is observable (`last_error` is `RunawayChainError`). A completion the
    machine produced *while processing* (a rollback that re-armed an
    invoke, #167; an invoke ping-pong `ver -> arm -> ver`, #168) is charged
    to the chain budget, and only the first completion that arrives at the
    trip is spared (#120). A drop that leaves nothing self-generated
    pending ends the chain, so a service that finishes later after an idle
    trip is still delivered. The invoke cycle now trips at the same lap
    count on both engines.
  - **`get_persisted_snapshot()` from inside an entry/exit action is
    refused** on both engines (#169). The guard was `in flight AND
    illegal`; inside an entry action the new leaf is already active
    (legal) while the context that entry is still writing is half-applied,
    so a torn "filled with `filled_qty=0`" blob persisted and restored
    cleanly. At the root, in flight alone now refuses; legality remains the
    test for the bounded wait on a child caught mid-step by its parent.
  - **`Receipt.denied` is `False` for a guard that *crashed*** under
    `guardErrorPolicy: "raise"` (#170); `error` carries the exception, so
    `(denied, error is None)` discriminates all three cases. Documented,
    with the note that a denied event under `onUnhandled: "defer"` enters
    the defer buffer.
  - **`await Interpreter.start()` returns with the initial configuration's
    invoked children registered** (#171), so `sendTo("kid")` on the first
    event resolves as it does after `SyncInterpreter.start()`. A plain
    service the initial state invoked still runs while `start()` returns
    (#149), but its completion is awaited before the first inbox event is
    read, so `start(); send("CANCEL")` orders identically on both engines
    (#116).
  - **`send_threadsafe(internal=True)` in-flight counter balances on every
    terminal outcome** (#172) — delivered, refused, cancelled, loop
    stopped before the coroutine ran — via a done-callback on the returned
    future. A leaked count gated the chain-budget reset for the rest of
    the machine's life.
  - **`tick()` on a `RealClock` real-delay ladder** (#122, reopened): closed
    as working as designed. `tick()` drains what is *due at the current
    reading*; no synchronous call can make wall time pass, so a 50 ms
    ladder needs one `tick()` per rung (or a `SimulatedClock`). The repro
    encoded the async engine's *wall-clock wait* as a sync expectation.

### Added

- **`Interpreter(service_pool_size=N)`** and `DEFAULT_SERVICE_POOL_SIZE`
  (#173). The executor plain-`def` services run on was a hard-coded pool
  of 4; the fifth concurrent service waited in a wave, and because the
  entering macrostep awaits the result each wave blocked a macrostep —
  nine 0.2 s services took 5 s, worse than serial. The size is now public
  and its interaction with macrostep blocking is documented.

### Changed

- **Production Characteristics** documents that a plain-`def` service
  blocks its own machine's `after` timers for its whole duration (#174) —
  an `after: 100` armed alongside a 500 ms plain service fires at ~500 ms;
  make the service a coroutine if a timer must interrupt it — and that the
  `maxIterations` settle budget bounds microsteps, not wall-clock lateness.

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
  - After the round-5 hardening (per-region configuration legality on
    every snapshot, the conservative-cycle chain check, the guard-denied
    flag, the receipt-hook wrappers) the hot path was re-measured with an
    interleaved A/B against the pre-round-5 tree: an initial 5–9% cost was
    clawed back to ~2% by inlining the split-out `_execute_selected`
    coroutine, a `str` fast path in `_prepare_event_reporting`, an early
    return in `_run_held_replays`, and skipping receipt-only bookkeeping
    for `send(wait=False)` on the sync engine. Published numbers (home
    page, README, `benchmarks/competitors/results.json`,
    Production Characteristics) are from a fresh clean-venv run of the
    final tree.
  - **Construction and 1,000-instance fan-out** -- the two rows where the
    table was a coin-flip against `transitions` -- are now won by a margin
    that survives harness noise (six interleaved runs in both adapter
    orders: 1.16-1.25x and 1.12-1.19x). Two PR-sized pieces:
    - *Parser single-pass.* `StateNode.__init__` reads every optional key
      in one `items()` pass (`_prefetch_node_keys`) and hands the values to
      the `_parse_*` helpers instead of each re-probing the dict; the two
      post-parse whole-tree walks (`_mark_subtree_actions`,
      `_scan_tree_features`) are folded into the parse as post-order
      accumulation; `_on_partials` is computed only when a `.*` key
      exists; parser / resolver / build-path INFO and DEBUG records sit
      behind one level check each; auto-discovery hands `MachineNode` a
      shared placeholder logic. A structural fingerprint of 154 configs is
      byte-identical before/after. `create_machine()` on the 7-node
      benchmark machine: 87 -> 77 us.
    - *Thin interpreter.* `__slots__` on `BaseInterpreter` /
      `SyncInterpreter` / `Interpreter` (1.6 KB -> 400 B per instance;
      `__dict__` kept for subclasses and ad-hoc attributes); the deadline
      heap's `threading.Lock` is allocated on first push; six per-instance
      INFO records gated; the init `on_transition` record is only built
      when a plugin is attached; `StateNode.owns_tasks` lets entry/exit
      skip the task schedule/cancel round-trip for states that declare
      neither `after` nor `invoke`; init/exit trigger events are shared
      sentinels; a flat immutable initial context is `dict()`-copied.
    - Every row moved: flat toggle 55k -> 83k, nested 23k -> 34k, parallel
      40k -> 56k, construction 8.5k -> 12.4k, 1,000 instances 27k -> 52k,
      timers 8.7k -> 11.6k, async `send(wait=True)` 23k -> 32k. Our own
      per-process budget (Production Characteristics) 44k -> 59k ev/s and
      `after` lateness at 500 busy machines 62 -> 36 ms.
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

---

## [0.8.0] — 2026-09-17 — Fortify *(Current Release)*

**Adoption-readiness, parts 1–3.**

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

For full details, see the [`[0.8.0]` section of CHANGELOG.md](https://github.com/basiltt/xstate-statemachine/blob/main/CHANGELOG.md#080---2026-09-17).

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
