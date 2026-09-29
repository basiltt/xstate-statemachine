---
title: "Changelog"
description: "Release history and what changed in each version."
---

# Changelog

All notable changes to XState-StateMachine for Python are documented here.

For the full changelog with commit history, see [CHANGELOG.md on GitHub](https://github.com/basiltt/xstate-statemachine/blob/main/CHANGELOG.md).

---

## [Unreleased]

### Added

- **Example app: `examples/integrations/sqlalchemy_orders/` (#286).** An
  order lifecycle on SQLAlchemy 2.0 in a sync variant (`StatechartMixin`
  with `optimistic()`, `send_with_retry`, `in_state` queries, audit rows)
  and an async variant (`AsyncSQLAlchemyStore` + `apersisted()` on
  aiosqlite), sharing one database. The 15-minute payment `after` is fired
  by `DueTimerScanner` for orders nobody touches. Ships an Alembic
  environment and the generated migration for the model and every `xsm_*`
  table; a test runs `alembic upgrade head` and asserts autogenerate sees
  no diff. The transactional outbox is not faked: the README points at
  #293.
- **Example app: `examples/integrations/flask_wizard/` (#286).** A 4-step
  server-rendered onboarding wizard: one machine per browser session
  (`XState` + session-derived key), NEXT / BACK / SUBMIT as events the
  chart validates, `SessionStore` by default with a `SQLiteStore` variant
  (`WIZARD_STORE=sqlite`), an oversize context refused with 413 and
  nothing saved, Flask-WTF CSRF when installed, and
  `flask xsm inspect wizard`. `tests/test_examples_integrations.py` now
  runs each example's suite under its own extra, and the `[sqlalchemy]`
  and `[flask]` CI cells run it.

- **SQLAlchemy & Flask (Phase D) -- `[sqlalchemy]` extra (#284 parts 1–2).**
  A statechart on your mapped row, or a `StateStore` on any RDBMS.
  - `StatechartType` (JSON; `JSONB` on Postgres; size-capped both ways)
    and `StatechartMixin`: queryable `statechart_state` /
    `statechart_state_ids` (every parallel leaf), `statechart_version`
    as `version_id_col` via `StatechartMixin.optimistic()` (a stale write
    is `ConflictError`; `send_with_retry` rolls back and retries -- 16
    threads × 100 sends on one row → exactly 1600), `in_state(*ids)`
    matching leaves and ancestors, `row.send(event, session=,
    lock="optimistic"|"pessimistic")`. One flush writes the snapshot,
    the columns, the `xsm_deadlines` index and (with `__xsm_audit__`)
    the audit rows -- raising inside `send()` leaves none of them. A
    mapper listener keeps the columns true when the snapshot is edited
    directly. `Model.statechart_store()` lets `DueTimerScanner` fire
    persisted `after` timers. `xsm_sqlalchemy_ddl(metadata)`; Alembic
    autogenerate proposes no diff (tested).
  - `SQLAlchemyStore` / `AsyncSQLAlchemyStore` pass the store contract
    suite (SQLite, aiosqlite; Postgres opt-in via `DATABASE_URL`):
    conditional-UPDATE optimistic writes, a portable lease `lock()` that
    wraps the block in one transaction, `due_keys()` for the scanner,
    `forget()` erasing record + deadlines + lease + log (X0.5), a
    versioned schema with newer versions refused (X0.10).
    `SQLAlchemyInbox` / `SQLAlchemyLog` share the store's transaction so
    inbox marks and audit rows commit with the save (X0.3).
  - The transactional **outbox** (#284 part 3) arrives with the EDA core
    (#293), whose `BrokerAdapter` / `OutboxStore` protocols it needs.
    Guide: *SQLAlchemy*.
- **SQLAlchemy & Flask (Phase D) -- `[flask]` extra (#285).** The `init_app`
  extension Flask never had.
  - `XState()` / `init_app(app, store, lock=, plugins=, inbox=,
    principal=, log=)` keeps per-app state in `app.extensions["xstate"]`
    (two apps from one extension share nothing); `register(...,
    authorize=)` is **required** (`allow_all` warns once, X0.1); `act()`
    is `persisted()` with the app's policies and refuses to run inside a
    GET; `g.xsm`; `receipt_response()` maps status through the core
    `receipts` table.
  - `create_statechart_blueprint(xsm, name, url_prefix,
    per_event_routes=)`: state, send, per-event, events, history (log),
    SSE stream, Mermaid diagram. JSON only (415), capped (413), RFC 9457
    problems carrying class names only (X0.7), principal-scoped
    `Idempotency-Key` whose replays are not re-saved (X0.2), GET on a
    write path → 405 problem. 50 concurrent requests on one
    `SQLiteStore` key → no lost updates.
  - `SessionStore`: wizard state in the signed session cookie with a hard
    3 KiB cap and `SessionStoreTooLargeError`.
  - `flask xsm inspect|diagram|docs|simulate <name>` -- output identical
    to `xsm`. Flask-WTF `CSRFProtect` compatibility documented and tested
    (exempt blueprint or `X-CSRFToken`).
  - Quart shim (`contrib.quart`, `async with xsm.act()`), a soft import --
    no separate extra; the same route tests run under Quart in CI.
    Guide: *Flask*.
- **LLM agents (Phase E) -- `[agents]` extra (#287, #290).** The model
- **LLM agents (Phase E) -- `[agents]` extra (#287-#291).** The model
  proposes, the machine decides: an agent is the `TOOL_LOOP` reference
  chart (`contrib/agents/charts/tool_loop.json`, Stately-editable, strict
  and `xsm inspect` clean) plus `agent_logic()`.
  - **Tool registry** -- `tool_registry(*fns, timeout_s=, side_effect=)`
    derives JSON-schema tools from signatures via pydantic. `run_tool`
    enforces **inside itself** (X0.13), before executing anything:
    registration, the active state's `meta.tools` allow-list, strict
    argument validation, per-call human approval for `side_effect=True`
    tools, a mandatory `timeout_s`, and output truncation. A denied call
    raises `ToolDeniedError` and is never executed -- including one an
    injected tool result talked the model into.
  - **Budgets and timeouts** -- `budget_guards(max_tokens, max_usd,
    max_turns)` on the single entry to every model turn; `after`
    timeouts on model and tool calls with `RetryPolicy` backoff.
  - **Human-in-the-loop as a durable state** -- `awaiting_human`
    persists in any store with its escalation deadline, resumes on
    `HUMAN_APPROVED` after a restart, escalates via `DueTimerScanner`.
  - **Structured output** -- `output_model=` / `meta.output_model`;
    invalid replies are re-prompted (`RETRY_OUTPUT`) and count against
    the budget.
  - `run_agent` / `run_agent_sync` (with `apersisted` / `persisted`),
    `FakeModel` for offline tests, bounded `messages` (`max_messages` /
    `summarise`), default redaction of `api_key` / `authorization` /
    `*token*` keys, `AgentTracePlugin` (JSONL, `gen_ai.*` fields,
    `record_content=False` default, `on_span` seam for OTel).
  - **Providers** -- `providers.openai.openai_model` and
    `providers.anthropic.anthropic_model`; the SDKs are soft imports
    (`MissingExtraError` names `pip install openai` / `anthropic`),
    contract-tested against recorded fixtures.
  - **Multi-agent recipes** -- example `supervisor`, `pipeline` and
    `debate` charts; `spawn_agent(child_chart, model, tools, budget=)`
    spawns a `TOOL_LOOP` actor per sub-task with its own budget and a
    tool allow-list that must be a subset of the parent's (refused
    loudly otherwise); `BudgetPlugin` rolls child usage into the parent
    and raises `BUDGET_EXCEEDED`; `handoff_guard` makes an unauthorised
    handoff `Receipt.denied`. Guide: *LLM agents*.
  - **LangGraph interop (#288)** -- `contrib.agents.langgraph`
    (soft import `langgraph`, tested `>=0.2,<2.0`; outside that range the
    import raises `ImportError` naming it). `statechart_node` runs a
    statechart as one LangGraph node with its snapshot as plain JSON in
    the graph state (so any checkpointer persists it);
    `route_by_statechart` routes conditional edges by active state (an
    unmapped state is loud, never a silent `END`); `langgraph_service`
    runs a compiled graph as an `invoke` service (`ainvoke`, or `astream`
    chunks as `STREAM` events), with errors to `onError` and cancellation
    on state exit; `LangChainCallbackPlugin` mirrors transitions into a
    LangChain callback handler. Tools in a `TOOL_LOOP` node still run only
    through `run_tool` (X0.13). It ships inside `contrib.agents`, and a
    separate distribution is the plan if LangGraph churn bites.
  - **pydantic-ai and structured output (#289)** --
    `contrib.agents.pydantic_ai.pydantic_ai_service(agent, prompt_from=,
    deps_from=, stream=)` runs a pydantic-ai `Agent` as an `invoke`
    service. Output and usage go to `onDone`, and `usage_logic()` merges
    usage into the context `budget_guards` read. With `stream=True`, text
    deltas are `STREAM` events. `agent_tool_from_machine(runner)` exposes
    a statechart run as a pydantic-ai `Tool`. `structured_output(Model,
    retries=2)` is the public switch for the existing `RETRY_OUTPUT`
    mechanism (per-state `meta.output_model`), using instructor's JSON
    extractor when installed; `agent_logic` gains `output_parser=`.
  - **Comparisons, example, launch drafts (#291)** -- guide pages *vs
    LangGraph*, *vs Burr* and *vs @statelyai/agent*, with feature tables
    generated from `docs/_data/comparisons.json`;
    `examples/integrations/agents_support_bot` (order lookup via the
    FastAPI example, a refund gated by `awaiting_human`, budgets, a JSONL
    trace, `SQLiteStore`; `run.py --fake` runs offline); a README "For
    LLM agents" section; PyPI keywords `llm-agents` and
    `agent-orchestration`. Launch-post drafts sit under
    `docs/research/launch/` and are not published.

- **Adoption kit (#309).**
  - **`xsm new --template fastapi DIR`** scaffolds a minimal project from
    the `fastapi_orders` example -- `machine.json`, `models.py`,
    `logic.py`, `app.py`, `static/`, `tests/`, `README.md` and a
    `requirements.txt` pinning `xstate-statemachine[fastapi]` -- with the
    standard library's `string.Template` (no cookiecutter). `--name`
    (lower_snake_case, default `orders`) sets the URL and store prefix and
    the camelCased machine id; a non-empty directory is refused without
    `--force`; `--list` shows `fastapi` and the planned `django` (#280) /
    `flask` (#285) templates, which are refused with their issue. Exit 2 on
    any refusal. Also in the interactive launcher.
  - **`xsm-check` GitHub Action** (`action.yml`, composite): installs the
    library, runs `xsm validate --plain` on a `files` glob and, when
    `generated-dir` is given, `xsm gt --check`. `setup-python` is pinned to
    the same SHA as CI. Self-tested on the example app in
    `.github/workflows/xsm-check-selftest.yml`.
  - **pre-commit hooks** (`.pre-commit-hooks.yaml`): `xsm-validate`
    (`*machine.json`) and `xsm-gt-check` (`pass_filenames: false`; pass
    your generation flags as `args`).
  - **Editor JSON Schema** `schemas/xstate-machine.schema.json`, generated
    from `contrib.pydantic.MachineConfig` by
    `scripts/gen_machine_schema.py`; a test regenerates it and fails on
    drift, and every machine in the test corpus validates against it.
  - **PyPI metadata:** classifiers `Framework :: FastAPI`,
    `Framework :: AsyncIO`, `Framework :: Pytest`; keywords `statechart`,
    `xstate`, `fsm`, `state-machine`, `workflow-engine`, `saga`,
    `event-driven`, `fastapi`, `persistence`. The sdist now includes
    `schemas/`, `action.yml` and `.pre-commit-hooks.yaml`.

- **Web framework integrations (Phase C).**
  - **`[starlette]` extra (#275).** `StatechartRegistry` runs named
    machines over any `StateStore` / `AsyncStateStore` with the honest
    multi-worker model -- **create → act → persist → discard**:
    `async with registry.act(name, key)` builds one async `Interpreter`
    via `apersisted`, saves with `expected_version`, and publishes each
    changed receipt to this process's SSE/WebSocket subscribers only after
    the save commits. `register(authorize=)` is **required** (closed by
    default; `allow_all` logs a one-time WARNING); responses carry state
    only unless a `context_serializer=` is given. `receipt_to_status` /
    `ReceiptResponse` map `Receipt` to HTTP (denied 409, deferred 202,
    duplicate 200, error 500), `problem()` emits RFC 9457
    `application/problem+json` without exception text, and
    `status_for_exception` maps strict-mode 422, drift/version 409 (with a
    `machine_version` hint), conflict/lock 409 and missing key 404.
    `send_event()` honours `Idempotency-Key` through the principal-scoped
    `IdempotencyPlugin` (reused body → 422, in flight → 409), accepts only
    size-capped `application/json` (415 / 413). `transition_stream()`
    (SSE) and `websocket_endpoint()` stream a snapshot on connect and one
    `transition` per committed change with a monotonically increasing
    sequence, 15 s heartbeats, `Origin`/`Host` checks and
    `max_connections_per_key`. Opt-in `resident()` actors are LRU/TTL
    bounded; `lifespan` runs `DueTimerScanner` when `run_timers=True` and
    drains residents within `drain_timeout_s`; `health_route()` /
    `ready_route()` probes; `mount_inspector()` refuses unless
    `debug=True` (the sink ships with #274). Guide:
    *Integrations → Starlette*.
  - **`[fastapi]` extra (#276).** `StatechartRouter(registry, name)` turns
    a registered chart into an `APIRouter`: `GET /{id}` (state only),
    `POST /{id}/send` whose body is a **discriminated union** of the
    machine's `EventModel`s on `type` (or a deterministic
    `{type: Literal[<declared>], payload}` fallback), one
    `POST /{id}/events/<EVENT>` per declared event, `GET /{id}/events`
    (what `can()` accepts now + declared schemas), `GET /{id}/diagram.mmd`,
    SSE `/{id}/stream` and `WS /{id}/ws`. Every handler delegates to the
    `[starlette]` registry (`send_event`, `peek`, `transition_stream`,
    `websocket_endpoint`), so status mapping, `Idempotency-Key` and
    `authorize` are shared; the principal comes from an `actor` dependency,
    never the body. `app.openapi()` validates, documents every 4xx/5xx as
    `application/problem+json`, and request-validation failures are 422
    problems listing only field locations and error types.
    `dependencies=` / `per_event_dependencies=` add FastAPI-native auth (a
    gated event is refused on `/send`). `get_interpreter()` is a
    `Depends` yielding inside `act()` -- saved when the handler returns,
    not when it raises, a conflict → 409. `instrument_app()` mounts
    probes, composes `registry.lifespan` with the app's own
    (`compose_lifespan()`) and maps library exceptions to problems.
    Extra: `fastapi>=0.100`, `pydantic>=2.5`, `starlette>=0.27`. Guide:
    *Integrations → FastAPI*.
  - **`[litestar]` extra (#278).** `create_statechart_controller()`
    generates a `Controller` with the same route table; `XStatePlugin`
    appends `registry.lifespan`, mounts probes, maps library exceptions to
    problem+json, documents the `/send` body as `oneOf` + `discriminator`
    in OpenAPI and can register per-machine `Provide()` dependencies;
    `get_interpreter()` is the `Provide` form. Litestar requests and
    responses are adapted at the edge -- one registry, one set of
    semantics. Extra: `litestar>=2.0`, `starlette>=0.27`. Guide:
    *Integrations → Litestar*.
  - `EventModel` validators ignore the transport-level `idempotency_key`
    payload field, so `Idempotency-Key` works with `extra="forbid"`
    models.
  - **`examples/integrations/fastapi_orders` + multi-worker guide (#277).**
    A runnable order-lifecycle service (`cart → paying → paid → shipped`,
    `after` expiry, an invoked gateway retried with `RetryPolicy`, a
    parallel `fulfilment` region) on `StatechartRegistry` over
    `SQLiteStore` or, with `XSM_REDIS_URL`, `RedisStore`; typed events,
    `Idempotency-Key`, a `BackgroundTasks` confirmation email scheduled only
    for a committed first-time change, SSE consumed by a static page, and a
    `--role scheduler` process running `DueTimerScanner` (timers in exactly
    one process). `loadtest.py` starts N uvicorn workers (Windows-safe
    launcher polling `/_xsm/health`) and fires 200 concurrent `PAY`s at one
    order: exactly one changed receipt, with and without a key. Docker
    Compose runs 4 workers + scheduler + Redis. The FastAPI guide gains
    *Multi-worker deployments*, *Side effects*, *Sessions & wizards*,
    *Testing* and *Troubleshooting*; `tests/test_examples_integrations.py`
    validates every example chart and runs each example's suite in the
    `[fastapi]` CI cell.
  - **Fixed:** `send_event()` no longer persists a duplicate / in-flight
    receipt. Saving a replay bumped the version so the ORIGINAL request's
    save lost with 409; under a burst of retries with one
    `Idempotency-Key`, nobody won.
  - **`xsm gt --with-api` / `--with-models` (#279).** Two companion
    templates: `fastapi-router` writes `<machine>_api.py`, an editable
    `APIRouter` (`GET /{id}`, one typed `POST /{id}/events/<EVENT>` per
    event via `Depends(get_interpreter)`, `ReceiptResponse`, an undeclared
    event → 404 problem) whose `authorize` stub raises
    `NotImplementedError` until implemented (X0.1, closed by default);
    `pydantic-models` writes `<machine>_models.py`, a context `BaseModel`
    plus one `EventModel` per event (declared payloads typed, else
    `extra="allow"`). With the extra installed the generator mounts the
    router on a throwaway `FastAPI()` and checks `openapi()` lists one
    route per event; `--check` / `--diff` report drift. Listed by
    `xsm list-templates` and the launcher. Guide: *CLI templates →
    Companion templates*.

- **Graph algorithms `shortest_paths`, `simple_paths`, `reachable_states`,
  `transition_coverage_targets`, `Path`, `Step`** (#269; core, zero-dep;
  the Python counterpart of `@xstate/graph`). Every candidate step is
  EXECUTED by the real engine on a `SimulatedClock` with stub logic, so
  parallel regions, history, `after` timers and `onDone`/`onError` behave
  exactly as at runtime -- no hand-written semantics. `guards="both"`
  explores each guarded step both ways and records the assumption a path
  relies on (`guard:x=False`, `service:s=error`, `delay:d=unknown`);
  `weight="time"` is Dijkstra over `after` delays. `Path.replay(interp,
  clock)` lands exactly on `final_states`; `Path.event_string()` is the
  `xsm simulate --events` grammar. New CLI `xsm paths machine.json
  [--simple] [--guards both] [--json]`; `xsm inspect` gains one finding
  the static reachability pass cannot produce -- "state is never entered
  by the engine (reachable statically only)" -- and never removes a
  static one (corpus output unchanged). Guide: Testing &sect; "Path
  generation"; CLI &sect; "Paths".
- **Security and operability baseline X0 (#303) closed out for Phase A.**
  `SECURITY.md` at the repository root states the trust model (installed
  packages and the machine definition are trusted; events and snapshots
  are not), the reporting process and the supported versions. Two new
  guide pages: **Guarantees** -- the crash-consistency specification
  (order of actions / save / inbox mark / timer fire, what is exactly-once
  and what is at-least-once, every crash window with the test that proves
  it) -- and **Security** -- every X0 item mapped to the test or CI job
  that enforces it. New in code: `FileStore` records carry a `format`
  version (X0.10; a newer format is refused with an upgrade message, never
  guessed at); a `pip-audit --strict` CI job over the `[all]` extra, which
  now lists every shipped extra (X0.14); `tests/test_security_baseline.py`
  greps `src/` for `pickle` / `yaml.load` / `eval` / `exec` (one justified,
  marked exemption in the CLI verifier) and refuses any GitHub Action that
  is not pinned to a commit SHA.
- **Integration performance budgets** (#307): a reproducible seven-run
  import, persistence, plugin, validator and snapshot benchmark for both
  engines, with reviewed p50 baselines and a 25% regression margin. A
  deterministic default-job guard detects eager contrib/third-party
  imports; timing gates run only on the nightly reference runner
  (`XSM_PERF=1`). Unshipped integrations remain explicitly unmeasured.
- **Actor logic helpers `from_callback`, `from_async_iterator`,
  `from_iterator`, `from_coroutine`, `from_callable`, `from_interpreter`**
  (#267; both engines) -- XState v5 `fromPromise` / `fromCallback` /
  `fromObservable` / `fromActor` parity as ordinary services. A callback
  service's `send_back` is thread-safe from any thread or loop (async:
  `call_soon_threadsafe`; sync: the #305 mailbox drained on the owner's
  next `send()` / `tick()` -- never the plain queue); `receive(handler)`
  gets events the parent `sendTo`s the invocation id (`sendTo` now
  resolves running actor logic by invocation id); cleanup runs exactly
  once on state exit, `stop()` or setup error, `async def` cleanups are
  awaited by the async `stop()`. Streams deliver each item as
  `Event("STREAM", {"data": item})` in order, `onDone` with the last item,
  `onError` on exception, `aclose()` / `close()` on state exit. Docs:
  services guide "Actor logic helpers" (parity table, paho-mqtt-shaped
  callback and LLM-stream examples, executable).
- **`[pydantic]` extra: typed context, typed events, static config
  validation, JSON Schema** (#266). Built on core seams only -- core never
  imports pydantic. `context_model(Model)` builds the
  `create_machine(context_validator=)` callable (a failure is
  `ContextValidationError`, an action error, so `rollback` keeps the
  machine valid; defaults and coerced values are written back into the
  dict); `typed_context(Model, cfg)` validates the initial context;
  `TypedContextPlugin(Model)` re-coerces on start, fresh or restored
  (`Decimal` comes back a `Decimal`); `PydanticCodec(Model)` is a store
  codec that keeps `Decimal` / `datetime` exact at rest; `context_of()`
  for a typed view. `EventModel` subclasses ARE events (`__xstate_event__`)
  and `events_union(*models)` is the `event_schemas=` mapping (bad payload
  → the existing `InvalidEventPayloadError` with the pydantic error as
  `cause`). `validate_machine_json(raw, strict=)` is a Pydantic model of
  the XState subset the parser implements, erroring **with JSON paths**
  before `create_machine`; a lock-step test pins its fields to
  `validation.KNOWN_*_KEYS` and it passes the whole Stately corpus.
  `machine_json_schema(machine, events=, context_model=)` emits a JSON
  Schema (discriminated event union, context, state-id enum, machine
  id/version/hash). Guide page *Pydantic*.
- **`[redis]` extra: `RedisStore` / `AsyncRedisStore`, `RedisInbox`,
  `RedisLog`** (#306) -- the first shipped integration under
  `xstate_statemachine.contrib`. Shared state for multi-worker / multi-host
  deployments implementing the same `StateStore` / `AsyncStateStore`,
  `InboxStore` and `TransitionLogStore` protocols, so `persisted()`,
  `apersisted()`, `IdempotencyPlugin`, `AuditPlugin` and `DueTimerScanner`
  work unchanged -- and pass the SAME contract suites as the stdlib
  backends (run on `fakeredis` in CI, live server via `XSM_REDIS_URL`).
  Optimistic save is one atomic Lua script; the pessimistic lock is a
  token-owned `SET NX PX` and **fenced** (an expired lock yields
  `ConflictError`, never a lost update); `forget()` is atomic;
  `list_keys()` escapes glob metacharacters; `prefix` is mandatory
  (X0.15) with a `{prefix}:schema` key; deadlines are indexed in a sorted
  set the scanner reads directly. Guide page *Redis* with guarantees and
  threat-model boxes.
- `require_extra()` now turns every failure mode -- not installed, import
  refused by a finder, installed-but-broken -- into `MissingExtraError`
  (it used to let a raw `ImportError` escape from the subpackage's own
  import). Docs: `<!-- doc-requires: mod, ... -->` marks an example that
  runs only when the named modules import (an extra's CI cell runs it).
- **Durable `after` timers: persisted deadlines, `restart_timers="resume" |
  "fire_due"`, `pending_deadlines()`, `DueTimerScanner`** (#264; both
  engines). Every armed `after` timer is now recorded in the snapshot's
  `deadlines` (layout v4) as a wall-clock `Deadline` (`state_id`,
  `entry_seq`, `due_at_wall`, resolved `delay_ms`, `event_type`) --
  **reversing the 0.8.0 "timers are not persisted" decision**, because
  under create → act → persist → discard an in-memory deadline never
  fired. `from_snapshot(restart_timers=)` widens from a bool to
  `False | True/"restart" | "resume" | "fire_due"`: resume re-arms the
  REMAINING wall time, fire_due also fires matured deadlines during
  `start()` in deadline order; `persisted()` / `load_interpreter()` default
  to `"resume"`. A parked deadline whose state vanished after a migration
  fails loudly (`StateNotFoundError`). `DueTimerScanner(store,
  machine_for_key)` -- `run_once(now)` / `scan()` / `run_forever()` -- is
  the zero-dependency driver that wakes due machines under a lock
  strategy, re-reading under the lock so a machine another worker advanced
  is skipped; `ScanResult` carries the lag metric. Docs: "Durable timers"
  with the guarantees box (no earlier than the deadline, no later than the
  next tick; at-least-once on crash -- pair with the inbox).
- **Chart versioning on restore: `MachineVersionMismatchError`,
  `SnapshotMigrator`, `from_snapshot(on_version_mismatch=, migrator=)`,
  `xsm snapshots --stale`** (#263; both engines). A snapshot's
  `machine_version` label (written since #305) is now compared with
  `machine.version` on restore: a mismatch raises
  `MachineVersionMismatchError` (a `SnapshotDriftError`, distinct from the
  layout-level `SnapshotVersionError`) unless `on_version_mismatch="warn"`
  or a `SnapshotMigrator` with a registered `from → to` step (chained along
  the shortest path; `NoMigrationPathError` otherwise) is given. A migrated
  blob has its hash dropped and is validated against the new machine like
  any other (every state id must exist, X0.4; `strict` still applies);
  child actors follow the same policy with steps scoped by `machine_id`.
  Unlabelled (0.10.x) blobs restore with a warning. `persisted()` /
  `apersisted()` / `lock.run()` pass `migrator` / `on_version_mismatch`
  through. New `xsm snapshots --store sqlite:///… [machine.json] [--stale]
  [--json]` lists a store's keys with record version, machine version and
  age, or only the stale ones. Docs: "Versioning in-flight instances" with
  the rollout recipes and an explicit "we do not automatically migrate".
- **`persistence.TransitionLogPlugin` / `AuditPlugin`, log stores
  (`MemoryLog`, `JSONLinesLog`, `SQLiteLog`) and `replay()`** (#262; both
  engines). One append-only `TransitionRecord` per processed event --
  transitions AND denied / unhandled / deferred / errored attempts, each
  with a `disposition` -- written from the hook that observed the outcome,
  with a gap-free per-key `seq`, redacted payload, the actions that ran,
  and `actor` / `reason` / `correlation_id` (payload keys or the
  `correlation_id_var` contextvar). `SQLiteLog(store)` shares the store's
  connection so the row joins the snapshot's transaction under
  `PessimisticLock`; `append(..., connection=None)` is the seam for
  Django / SQLAlchemy. `replay()` rebuilds a machine from the log on a
  `SimulatedClock`: user events re-sent, `after` steps by advancing the
  clock, service completions by stub services replaying the recorded
  `done` / `error` -- never re-sending engine-minted events -- with stub
  logic unless `logic=` is given, and `ReplayDivergenceError(seq)` on the
  first mismatch. Docs: "Audit log & replay" with an approval-workflow
  example and the "event sourcing lite" scope note.
- **`persistence.IdempotencyPlugin` + `InboxStore` (`MemoryInbox`,
  `SQLiteInbox`)** (#261; both engines). At-least-once deduplication as a
  plugin: an unseen idempotency key is claimed atomically, a redelivery is
  answered from the inbox with the **original** receipt (`duplicate=True`)
  before the machine sees it, a reused key with a different payload is
  refused (`IdempotencyMismatchError` → 422) and an in-flight key answers
  409 -- refusals are receipts, not exceptions. Scope is
  `principal / machine / instance` (X0.2; `principal` is required);
  fingerprint = sha256 of type + canonical payload minus the key; TTL 7
  days; keys ≤ 255 printable ASCII. Crash-consistent with `persisted()`
  (X0.3): marks are buffered and written after the snapshot save (inside
  the same SQLite transaction when `SQLiteInbox(store)` shares the store),
  and a 64-key `processed_ids` ring inside the snapshot covers the
  save→mark window -- three fault-injection tests. `interpreter.store_key`
  (new attribute) records the key `persisted()` / `load_interpreter()`
  loaded a machine under. `receipt_to_status` gains 422 and
  `STATUS_UNPROCESSABLE`. Docs: "Idempotency: the inbox" with a
  Stripe-shaped example and the at-least-once + inbox guarantees box.
- **`persistence.persisted()` / `apersisted()` / `persisted_retry()` and
  lock strategies `OptimisticLock` / `PessimisticLock` / `NoLock`** (#260).
  `with persisted(store, key, machine) as order: order.send("PAY")` is
  create → act → persist → discard with a started interpreter, persisting
  on clean exit and **writing nothing if the block raises**. A block
  cannot be re-run, so under the default `OptimisticLock` a concurrent
  write raises `ConflictError` at exit and the caller retries;
  `persisted_retry(fn)` / `lock.run(fn)` is the retrying form (guarantee:
  *fn* and its actions may run up to `retries + 1` times per logical send
  -- keep side effects in services or an outbox). `PessimisticLock` holds
  `store.lock()` for the block and still saves with `expected_version` as
  a fence. `SQLiteStore.lock()` is now the thread's own `BEGIN IMMEDIATE`
  transaction (saves inside the block join it and commit together);
  `FileStore.save()` inside its own `lock()` no longer self-deadlocks;
  `as_async()` funnels every call through one worker thread so
  `async with adapter.lock(): await adapter.save()` is correct by
  construction. Docs: "persisted()" and "Concurrency: choosing a lock"
  sections with the decision table.
- **`persistence` stores: `StateStore` protocol + `MemoryStore` /
  `FileStore` / `SQLiteStore`, `load_interpreter` / `aload_interpreter` /
  `save_interpreter`, `as_async()`** (#259; zero-dependency). The
  create → act → persist → discard model with optimistic locking
  (`save(expected_version=)` → `ConflictError`) and pessimistic
  `lock(key)` (`LockTimeoutError`). Every backend passes one contract test
  suite. Safety rails on all of them: `max_snapshot_bytes` (1 MiB) on
  save AND load (`SnapshotTooLargeError`), key validation
  (`InvalidKeyError`), `forget(key)`, a `codec=` seam, `health()`.
  `FileStore`: atomic writes, percent-encoded keys (never the raw key in a
  path; case-collision-free), advisory locks with stale reclaim, 0700/0600
  modes, documented as unsafe on network shares. `SQLiteStore`: WAL,
  connection per thread, `xsm_schema` versioning, `database is locked` →
  `LockTimeoutError`, 0600 files, UNC warning. Guide page *Persistence
  Stores*; new `StoreError` family in `exceptions`.
- **`xstate_statemachine.patterns`: `RetryPolicy`, `DeadLetterPlugin`,
  `CircuitBreaker`** (#265; zero-dependency; both engines). Guide page
  *Resilience Patterns*.
  - `RetryPolicy(max_attempts, base_ms, factor, max_ms, jitter, rng)`:
    AWS-style `none` / `full` / `equal` / `decorrelated` jitter, capped,
    deterministic with an injected `rng`. `policy.logic()` yields
    `retryDelay` (named delay), `retryCanRetry`, `retryBump`, `retryReset`
    so the documented four-state retry chart works verbatim.
  - `DeadLetterPlugin(sink)`: on entry to a state tagged `dead-letter`
    (or in `state_ids`) emits one `DeadLetter` -- event, attempts, the
    **error chain** from `on_service_error` / `on_action_error`, and a
    snapshot -- **redacted** before it reaches the sink (#303).
    `DeadLetterStore` in-memory sink with `purge_older_than()`.
  - `CircuitBreaker` / `@circuit_breaker`: Nygard's breaker *as a
    statechart* (`CIRCUIT_BREAKER_CONFIG`, renderable by `xsm inspect`) on
    a lock-guarded `SyncInterpreter`; `call` / `acall`; fast
    `CircuitOpenError` when open; half-open admits exactly
    `half_open_max_calls` probes under a 32-thread hammer; cooldown on the
    injected clock.
  - `MachineLogic.merge(*others)` returns a new combined logic (later wins;
    nothing mutated).
  - Both engines now fire `on_event_processed` with the step **settled**,
    so a plugin may call `get_persisted_snapshot()` from it (the sync engine
    previously still reported mid-step there). `on_transition` remains
    mid-step and still refuses a snapshot.
- **Global plugin registry, `context_validator` seam, `__xstate_event__`
  adapter, `SyncInterpreter.send_threadsafe()`** (#305 part 2; both
  engines).
  - `register_global(plugin)` / `unregister_global(plugin)` /
    `global_plugins()` (top-level exports; `plugins.clear_global_plugins()`
    for teardown). A registered plugin is attached -- with the same
    containment as `.use()` -- to every interpreter constructed **after**
    registration: both engines, `from_snapshot`, and engine-spawned
    children. Opt-in only; the library never registers anything itself.
    Thread-safe (100-thread registration test).
  - `create_machine(..., context_validator=fn)`: `fn(context)` raises when
    the context is invalid. Both engines call it after any action that
    *changed* `context` (never when unchanged) and treat a raise as that
    action's failure, so `actionErrorPolicy` applies (`"rollback"` restores
    the pre-transition context) and `on_action_error` fires. Stored on
    `MachineNode.context_validator`. The seam for the pydantic extra (#266).
  - Any object implementing `__xstate_event__() -> str | dict | Event` is
    accepted wherever an event is: `send`, `send_events`, `send_threadsafe`,
    `can`, `sendTo` specs -- one normaliser, one level, same rules as a
    direct argument. Keyword payload merges over an adapter's dict.
  - `SyncInterpreter.send_threadsafe(event, **payload)`: the only legal
    cross-thread entry to a sync machine. A locked mailbox the owning
    thread drains at the top of `send()` / `tick()`, ahead of its own
    event, each as its own macrostep with the normal admission checks.
    FIFO per producer thread; nothing lost (8 threads x 1,000 events test);
    an admission refusal at drain time surfaces on the owner via
    `on_event_dropped(..., "invalid")` + `last_error`.
- **Snapshot layout v4, `MachineNode.version`, wall clock, `Deadline`,
  receipt codec** (#305 part 1 — core prerequisites for the persistence
  and web integrations; both engines).
  - `SNAPSHOT_VERSION` is **4**. Every snapshot now carries
    `machine_version` (the chart's root `"version"` label, or `null`) and
    `deadlines` (durable wall-clock `after` timers, #264 — always `[]`
    until that lands, so the layout is settled once). v0–v3 blobs upcast
    with `machine_version=None, deadlines=[]`; `check_shape` validates both
    keys (`SnapshotCorruptError`); `check_version` refuses v5+. **Rolling
    deploys:** a v4 blob does not load on 0.10.x (`SnapshotVersionError`)
    — deploy readers before writers; see the snapshots guide.
  - `MachineNode.version: Optional[str]` reads the root `"version"` key
    that `validation.py` accepted and silently ignored. Not part of
    `structure_hash`, so re-labelling a chart keeps old snapshots loadable.
    `xsm inspect` shows it (`--json` adds `"version"`).
  - `interpreter.wall_now()` on both engines — epoch seconds via
    `clock.wall_now()` when the clock has one (`RealClock` →
    `time.time()`; `SimulatedClock(wall_start=…)` → `wall_start` + virtual
    elapsed, so a test can say "restarted an hour later"), else
    `time.time()`. Anything persisted anchors to this, never to
    `clock.now()`.
  - `persistence.Deadline` frozen dataclass (`state_id`, `entry_seq`,
    `due_at_wall`, `delay_ms`, `event_type`; `to_dict` / `from_dict` /
    `remaining_ms`) and `check_deadline_record()`. `entry_seq` is the
    state-entry generation, so a deadline armed by an earlier visit is
    dropped on fire rather than honoured.
  - `xstate_statemachine.receipts`: `receipt_to_status()` (error → 500,
    deferred → 202, denied → 409, else 200; `duplicate` is neutral),
    `receipt_to_json()` / `receipt_from_json()` with `error` as
    `{"type", "message"}` strings only (never pickled, #303) and a
    `ReceiptError` on the way back. Also exported from the top level.
- **Plugin hooks `on_before_send` and `on_event_processed`** (#304;
  both engines, parity-tested). `on_before_send(interpreter, event)`
  fires from `send()`, `send_events()` and `send_threadsafe()` after the
  `strict` / `event_schemas` admission checks and *before* the event is
  queued; returning a `Receipt` **short-circuits** the send — the event is
  never queued, `on_event_received` / `on_event_processed` do not fire for
  it, and the caller receives that receipt (a `send(wait=True)` resolves to
  it immediately). First plugin to return wins. It is **fail-open**: a
  raising interceptor is reported via `on_plugin_error` and the event is
  admitted, so a blocker must return a receipt, not raise. This is the seam
  the idempotency inbox (#261), rate limiting and maintenance-mode plugins
  use. `on_event_processed(interpreter, event, receipt)` fires exactly once
  per event that entered the machine — user and engine-minted alike —
  after it settled or was denied / unhandled / deferred / dropped, with the
  same `Receipt` a `wait=True` caller gets; the outcome hook that audit,
  coverage, tracing and the inbox's "mark" attach to. Both engines build
  the receipt from a per-event before-image, so a sync `send()` that also
  drains a due timer reports each event separately; the bookkeeping runs
  only when an attached plugin overrides the hook. `LoggingInspector`
  implements it at DEBUG.
- **`Receipt.duplicate`** (#304) — sixth field, default `False`; set by an
  `on_before_send` interceptor answering a redelivered event with the
  original outcome. Appended last so positional unpacking of the five
  older fields still works; prefer attribute access.
- **`stub_logic()` / `logic_names()`** (#304) — `xstate_statemachine.
  testing_utils`, exported from the package root: a `MachineLogic` that
  satisfies every name a chart declares (actions record into `ran`,
  guards answer a fixed value or a *live* mapping, services complete
  synchronously with `service_results`), so tools and tests can drive any
  chart without its business logic. Promoted from the CLI's internal trace
  recorder; the `pytest` codegen template and `xsm simulate` now share it.
  Builds every machine in the example corpus and the Stately fixtures.
- **Integration programme scaffolding** (#258; epic #257). The library
  is growing optional framework integrations while the core stays
  **zero-dependency** — a promise now enforced rather than asserted:
  - `xstate_statemachine.contrib` — the home for optional integrations
    (Django, FastAPI, SQLAlchemy, Celery, brokers, observability, testing,
    LLM agents), one pip extra each. The package imports nothing; each
    subpackage begins with `require_extra(...)`.
  - `MissingExtraError` (also an `ImportError`) — raised when an
    integration is imported without its extra; the message is the exact
    `pip install "xstate-statemachine[<extra>]"` command. Exported from
    the top-level package.
  - `xstate_statemachine.persistence` is now a **package**. The snapshot
    envelope module moved to `persistence/snapshot.py`; every public name
    (`SNAPSHOT_VERSION`, `structure_hash`, `check_version`, `upcast`, …)
    is re-exported, so existing imports are unaffected. Stores, locking,
    idempotency and durable timers land here in the next issues.
  - 22 integration extras declared in `pyproject.toml` as **empty
    placeholders** (`pydantic`, `fastapi`, `django`, `sqlalchemy`,
    `celery`, `redis`, `testing`, `observability`, `agents`, `web`, `eda`,
    `all`, …) so they already resolve; each fills when its issue ships.
    `contrib/_registry.py` is the single table tests and CI check against.
  - `tests/test_zero_dependency.py` — a subprocess guard that blocks every
    non-stdlib import, imports the package the way a user would, walks
    every core module, and asserts `contrib` was never touched. Proven to
    fail on a planted third-party import.
  - CI: `core-zero-dep` job (bare install + the guard), a `contrib`
    matrix with one cell per extra that installs **only** that extra,
    `pytest-socket` on the default suite (no accidental network), a grep
    banning `pickle`/`yaml.load`/`eval`/`exec` under `src/`, and all
    actions pinned to commit SHAs.
  - Docs: an **Integrations** guide page and sidebar section; a page
    template every integration copies (Install / Quick start / Reference /
    **Guarantees** / **Threat model** / Compatibility / Troubleshooting).
  - PR template gains an integrations checklist, including "this PR does
    not tag or publish a release".

### Fixed

- **`SyncInterpreter.send(..., wait=True)` on a finished or stopped machine
  now returns a `Receipt`** carrying `InterpreterStoppedError`, exactly as
  the async engine does -- not `None`, which the `wait=True -> Receipt`
  overload never promised and which made the `[flask]` blueprint answer a
  POST to a completed order with a 500. The core `receipts.receipt_to_status`
  table (and the Starlette/FastAPI/Litestar layer, which now defers to it
  for error classes) maps that receipt to **409** -- the instance refused
  the event, like a guard -- instead of 500. Fire-and-forget `send()` still
  returns `None` and fires `on_event_dropped`.
- **A parent snapshot can no longer harvest a non-blocking sync child's
  half-applied context.** "Wait until the child is settled" and "copy its
  context" were two separate reads; the child's pump thread could begin a
  step between them (a deterministic interleaving reproduced it even via
  the supported `send_threadsafe()` path), and CI saw it as "1 torn of
  150". The pump now runs each step under a per-child step gate that the
  parent holds across the check and the copy; a gate not free within
  0.5 s refuses with `SnapshotMidStepError(child=True)`. The async engine
  needs no gate (its children step on the caller's loop). A foreign-thread
  `send()` on a `SyncInterpreter` remains unsupported and voids the
  guarantee -- use `send_threadsafe()`.
### Documentation

- **Comparison pages vs django-fsm, transitions and python-statemachine
  (#286).** Feature tables (hierarchy, parallel, timers, invoke, actors,
  async, locking, versioning, admin, REST/DRF, audit, visual editor, typed
  context, persistence, XState JSON) render from three new entries in
  `docs/_data/comparisons.json`; every row carries a source note naming
  the competitor version checked, and a test enforces it. Each page has
  a side-by-side order lifecycle (ours executed by the docs test, theirs
  fenced as `text`) and an honest "When to choose them instead" section.
  The django-fsm page has a migration recipe pointing at the planned
  `xsm_migrate_fsm` (#310). Linked from the README, the landing page and
  the Integrations journey.

- **Integrations journey (#309).** *Integrations* is now the entry point:
  a Mermaid "pick your path" tree (framework × store × worker model ×
  events-in) with every leaf linked to an existing page, planned leaves
  naming their issue; a 15-minute tutorial whose steps run in CI (`xsm
  validate` / `inspect` / `gt --with-api --with-models --with-tests` → FastAPI on `SQLiteStore` →
  inbox deduplication → `RedisStore` via `fakeredis`), with the coverage
  gate (#270) and live inspector (#274) steps labelled as not yet shipped;
  "what you get / what you don't"; where next. The extras table moved,
  unchanged, to the new *Integration extras* page.
- **Stately editor → Python** page: export steps, the `version` key,
  what `meta` / `description` / `tags` / `x-` keys do today
  (`meta.publish` and `meta.tools` marked planned), `xsm validate` after
  export, the VS Code `json.schemas` snippet for `*.machine.json`, and the
  round trip.
- *CLI*: "In CI and pre-commit" and "New project" sections; README badge
  line under Install.

### Changed

- **`SyncInterpreter.send_events()` now applies the same admission checks as `send()`** — `strict` / `event_schemas` (`UnknownEventError` / `InvalidEventPayloadError` at the call site) and the reserved-payload-key warning — and both engines' `send_events()` run the new `on_before_send` interception (#304). Previously a batched send on the sync engine bypassed `strict` entirely.
- AGENTS.md now states the real Python floor, **3.9** (it said 3.8+;
  `requires-python` and CI have been 3.9 since 0.9).

### Fixed

- **`SyncInterpreter.send(..., wait=True)` on a finished or stopped machine
  now returns a `Receipt`** carrying `InterpreterStoppedError`, exactly as
  the async engine does -- not `None`, which the `wait=True -> Receipt`
  overload never promised and which made the `[flask]` blueprint answer a
  POST to a completed order with a 500. The core `receipts.receipt_to_status`
  table (and the Starlette/FastAPI/Litestar layer, which now defers to it
  for error classes) maps that receipt to **409** -- the instance refused
  the event, like a guard -- instead of 500. Fire-and-forget `send()` still
  returns `None` and fires `on_event_dropped`.
- **Idempotency refusals over HTTP are RFC 9457 problems.** A reused
  `Idempotency-Key` with a different body (422) or a still-in-flight request
  (409) returned a *receipt* body with a 4xx status and `application/json`;
  every other 4xx was already `application/problem+json`. They are problems
  now (`title`, `status`, `error` class name -- never exception text). A
  plain replay still returns the original receipt with `duplicate=True`.
  Found by driving the installed wheel over a real uvicorn server.
- **`--with-tests` output could not find its JSON when generated into a
  subdirectory** (`xsm gt machine.json --with-tests -o generated/`, the
  layout the docs recommend): the scaffold looked only beside the test
  module and failed with `FileNotFoundError` on the first run. It now looks
  beside the module first, then one level up -- the lookup the runner
  template already used. Found by installing the wheel into a clean venv
  and running the generated project.
- **Bare-string `and` / `or` / `not` guard names** are user predicates
  (only the dict form declares composition), but the CLI's guard parser
  dropped them and `camel_to_snake` stripped the `_` suffix `safe_identifier`
  adds for Python keywords -- so `stub_logic(raw_config)` missed a guard the
  engine demanded (`ImplementationMissingError` on `DebtState_v4.json`) and
  the typed template emitted `def and(...)`, a SyntaxError. Both fixed;
  generated names for keyword guards are now `and_` / `not_` (#269).

## [0.10.5] - 2026-09-25

### Fixed

Findings from a manual pass over every `xsm` command against the example
corpus.

- **Launcher → Simulate read from its own keyboard**, not the launcher's.
  `run_simulate` decided live-vs-scripted from `console.interactive` and
  opened the real key reader itself, so the flow could not be driven by
  the launcher's injected key source (and was untestable end to end).
  `run_simulate(..., source=)` now threads the launcher's source through;
  a launcher test drives Simulate → send → undo → quit.
- **Multiselect `space` toggled without advancing**, so the natural
  "space, space, enter" in the generate wizard's *Companion files* step
  toggled the first row on and off again and emitted no companions.
  `space` now toggles and moves to the next row (Inquirer / fzf
  convention); `Home` / `End` work in multiselect as they already did in
  select.
- **`xsm docs machines/*.json` stopped at the first broken file.** It now
  reports that file, documents the rest, and exits 1 at the end.

## [0.10.4] - 2026-09-24

### Fixed

- **Ctrl+C in the launcher or simulator printed a Python traceback.** The
  raw-mode key reader deliberately raises `KeyboardInterrupt` on `Ctrl+C`
  so the interactive prompts honour it, but nothing at the entry point
  caught it. `main()` now restores the cursor (a prompt or spinner may
  have hidden it), prints `interrupted` to stderr and exits with status
  130, the conventional SIGINT exit — no traceback, like every other
  terminal program.

## [0.10.3] - 2026-09-24

### Fixed

- **`xsm simulate` looked frozen on a chart with no sendable events.** A
  machine whose transitions are all `always` / `after` (e.g. the
  `quality_check_sync` example settles in `passed` immediately) has
  nothing for the event picker to offer, so the loop dropped straight
  into command mode — silently, under a `↑↓ pick event` hint. Arrow keys
  did nothing and it read as broken input. Command mode now prints a
  `❯ no event can be sent from here` line with the command keys, and
  `↑`/`↓`/`enter` there explain why and point at `t` / `c` / `u` / `r`.

## [0.10.2] - 2026-09-24

### Fixed

- **`xsm update` failed on Windows when run through `xsm.exe`** with
  `WinError 32: The process cannot access the file because it is being
  used by another process: '...\Scripts\xsm.exe'`, leaving the package
  uninstalled but the launcher present. pip's launcher is the parent of
  the update process and stays alive until it exits, so pip cannot delete
  it (pip has the same constraint with itself — hence
  `python -m pip install --upgrade pip`). `update` now detects that it was
  started via the launcher (`sys.argv[0]` is `Scripts/xsm[.exe]` next to
  this interpreter) and hands over to a detached
  `python -m xstate_statemachine update --yes`, which runs pip after the
  launcher has exited; the header is printed once and the child prints
  pip's output and the result. Verified end to end from PowerShell, `cmd`
  and `python -m` in a fresh venv upgrading 0.10.0 → 0.10.1.

## [0.10.1] - 2026-09-24

### Fixed

- **Launcher: pasted Windows paths were reported "not found".** Explorer's
  *Copy as path* wraps the path in double quotes (and a dragged file may
  carry single quotes); the file picker handed the quoted string to
  `Path()` verbatim, which looked for a file literally named `"C:\…"`.
  Every path prompt in the launcher (machine files, output directories)
  now normalises its input: surrounding quotes are stripped, `~` is
  expanded, a `file:///` URI is accepted, and typing a directory selects
  its `*.json` files. Driven end to end through the launcher with the
  quoted form in the tests.

## [0.10.0] - 2026-09-24

A CLI release. The runtime library is unchanged apart from one additive
overload; `xsm` grows from a code generator into a terminal toolkit — with
the same **zero runtime dependencies** as the library. Colour, box-drawing,
spinners, single-key input and Windows VT enablement are all standard
library. When stdout is not a terminal (or `--plain` is given) every command
emits deterministic plain text, so existing pipelines and CI logs are
unaffected.

### Added

- **Interactive launcher.** A bare `xsm` on a terminal opens a menu (arrows or
  digits, `enter`, `esc`) over every command, with recently used machine
  files remembered in `~/.xsm/recent.json` (`$XSM_HOME` overrides) and a
  **generate wizard** that picks files, template, companions and options,
  shows the head of the module it is about to write in a preview panel and
  asks before writing. The wizard builds the same `argparse.Namespace` the
  `gt` command uses, so nothing is implemented twice. Off a terminal, a
  bare `xsm` still gives the argparse "subcommand required" error.
- **`xsm inspect` (`ins`).** Builds the machine with the real library and
  lays out a summary panel, the state tree (kind glyphs, `initial`, `after`
  and `invoke` annotations), a transitions table (event, from, to, guard as
  the library resolved it, actions), the logic left to implement and the
  failure-policy block (`actionErrorPolicy`, `guardErrorPolicy`,
  `onUnhandled`, `maxIterations`, `strict`, `strictTargets`, event schemas).
  `--no-events` skips the table; `--json` emits the facts.
- **`xsm simulate` (`sim`).** One `Session` engine — `SyncInterpreter` on a
  `SimulatedClock` with stub logic, guard overrides, a snapshot undo stack
  and a step history — drives two modes. **Live** (on a terminal): a picker
  of the events `can()` says would do something now, then `t` fire the
  armed timer, `c` advance the clock, `g` toggle guards, `u` undo (timers
  re-armed via `from_snapshot(restart_timers=True)`), `r` reset, `h`
  history table, `s` snapshot, `q` quit; changed states pulse. **Scripted**
  (`--events A,+500,B`, `--clock`, `--script file.json` with
  `{"send"}` / `{"clock"}` / `{"guard","value"}` / `{"undo"}` / `{"reset"}`,
  `--guards-false a,b`, `--json`, or simply no terminal): replays the
  commands, prints each step and the final state, exits 0/1. The JSON
  document carries `active`, `value`, `context`, `clock_ms`,
  `enabled_events`, `chain_trips` and a per-step `history`.
- **`xsm diagram` (`dia`).** Mermaid (`to_mermaid`), PlantUML
  (`to_plantuml`) or an ASCII tree-plus-transition-list, to stdout or
  `-o FILE|DIR` (named `<machine-id>.mmd/.puml/.txt` in a directory).
- **`xsm docs`.** A Markdown reference page per machine — summary, embedded
  Mermaid, state tree, transitions, logic to implement, policies and a
  getting-started snippet — to stdout or `-o DIR`.
- **Companion templates** `pytest`, `typed`, `plugin`, usable as
  `--template` on their own or alongside any primary template via
  `--with-tests` / `--with-types` / `--with-plugin`:
  - `pytest` → `test_<machine>.py`: a test module **recorded from the
    engine** — the chart is run with stub logic on a `SimulatedClock` along
    its reachable event sequence and the configuration and actions after
    every step become assertions; plus initial-state, final-state,
    guard-denial, known-events and snapshot-round-trip tests. Runs green on
    day one and fails only when the chart (or the library) changes. The
    generated suites are themselves executed against the Stately corpus in
    the test-suite.
  - `typed` → `<machine>_types.py`: `Context` as a `TypedDict` inferred from
    the JSON `context`, `EventType` / `StateId` `Literal` aliases, one
    correctly annotated stub per action, guard and service, and a `logic()`
    binder.
  - `plugin` → `<machine>_observer.py`: a `PluginBase` subclass overriding
    exactly the hooks the chart can fire (`on_service_*` only with
    `invoke`, `on_guard_error` only with guards, `on_transition_failed`
    only under a rollback/fail policy, …), each writing one JSON log line;
    a trailing comment lists the hooks left out and why.
  Companions are compiled and import-checked before writing, carry the
  provenance banner and participate in `--check` / `--diff`.
- **Presentation flags**, accepted before *or* after the subcommand:
  `--plain`, `--no-color` (also `NO_COLOR` and `TERM=dumb`), `--no-anim`
  (also `XSM_NO_ANIM=1`), `--verbose` (INFO log on stderr; default is
  warnings only). Truecolor when `COLORTERM=truecolor|24bit`, else 256/16
  colours; Windows consoles get VT processing enabled. Unicode glyphs only
  when the stream can encode them; on an ASCII console separators and
  arrows are transliterated (`->`, `-`, `...`) instead of becoming `?`.
- **`--json`** on `validate`, `inspect`, `simulate`, `list-templates` and
  `info`.
- **`xsm update`** — checks PyPI (stdlib `urllib`, 10 s timeout) and
  upgrades to the latest release **with the installer that installed this
  copy**: `pip` (incl. `uv pip`), `pipx upgrade`, `uv tool upgrade`. Refuses
  an editable checkout (use `git`) and a conda environment (prints the
  `conda` command) rather than corrupt them. Asks on a terminal, prints the
  command and exits 1 off-terminal without `--yes`, `--check` exits 1 when
  a newer release exists, `--json` for scripts. Confirms the result by
  asking a fresh interpreter for `--version`, and on Windows re-applies the
  `setup` shim afterwards since pip recreates `xsm.exe`. Also on the
  launcher menu.
- **`xsm setup`** — makes the `xsm` command work on Windows machines
  whose Application Control / AppLocker / Smart App Control policy blocks
  pip's unsigned `Scripts\xsm.exe` launcher ("An Application Control
  policy has blocked this file") while `python.exe` is trusted. Run once
  as `python -m xstate_statemachine setup`: it parks the launcher as
  `xsm.exe.blocked` (Windows resolves `.exe` before `.cmd`, so it must move
  aside) and writes an `xsm.cmd` batch shim that runs the CLI through the
  trusted `cmd.exe` → the same interpreter. Idempotent; re-run after
  `pip install --upgrade` (which recreates the exe); `--check` reports the
  state (exit 1 if `xsm` still resolves to the exe), `--undo` restores
  pip's launcher, `--json` for scripts; a no-op with a message on other
  OSes. Verified on a WDAC-managed machine from PowerShell and `cmd`. The
  launcher is generated by pip on the user's disk, so nothing in the wheel
  can sign or replace it automatically — this is the closest thing to a
  fix a package can ship.
- **`python -m xstate_statemachine`** runs the CLI (a top-level
  `__main__.py`; `python -m xstate_statemachine.cli` still works) — the
  launcher-free spelling that works on every machine where Python does.
  `xsm info` prints it on an `Also run as:` line and, on Windows, points
  at `setup`.
- **`xsm validate --lenient`** downgrades unknown config keys to warnings.
- **`create_machine(config, logic=..., strict_config=...)`** — the
  logic-object overload now accepts `strict_config` like the other
  overloads (it was accepted at runtime but rejected by type-checkers).
- **`cli.ui` toolkit** (internal, stdlib only): `Capabilities` detection,
  a role-based theme with colour tiers, ANSI-aware `visible_width` /
  `pad` / `truncate` / `wrap`, boxes, tables (auto-shrinking columns,
  zebra rows), trees, `Spinner` / `ProgressBar` / `StepList` with
  non-animated fallbacks, `select` / `multiselect` / `confirm` / `text`
  prompts driven by an injectable key source (`keys.scripted("enter esc
  q")`) so every interactive path is tested without a pty, a block-letter
  banner and a `Console` facade.

### Changed

- **`xsm validate`** now builds each file through
  `create_machine(strict_config=True)` with stub logic instead of a
  hand-rolled structural check, so it refuses exactly what the library
  would refuse at runtime — including misspelled keys with the library's
  "did you mean" hints — and additionally reports states no transition,
  `initial` or history target can reach, plus every warning the library
  logged while building. The plain-text report keeps its previous shape
  (`ok <file>`, `Machine:`, `States:`, …, `All N file(s) are valid.`).
- **`xsm list-templates`** groups the catalogue (JSON-at-runtime,
  pure-Python, companions) and adds the companion rows to the feature
  table.
- **`xsm info`** renders the banner, an environment panel and feature
  cards; the previous `Version:` / `Python:` / links lines are still
  present.
- **Library log noise.** The CLI now shows the library's log at WARNING by
  default while it builds machines; pass `--verbose` for INFO.
- **Generated-code banner** reports `Generator: xstate-statemachine 0.10.0`.

### Documentation

- The [CLI Tool](https://basiltt.github.io/xstate-statemachine/guide/cli/)
  guide is rewritten around the six commands, the launcher, the
  presentation flags and the `--json` outputs; the
  [Templates Deep Dive](https://basiltt.github.io/xstate-statemachine/guide/cli-templates/)
  gains a companion-templates section with the generated `pytest`, `typed`
  and `plugin` output for the checkout example; README CLI section and
  the getting-started "What's New" updated.

### Tests

- 145 new tests under `tests/tests_cli/` cover the UI toolkit (rendering in
  truecolor / 256 / plain, width arithmetic on styled text, prompts driven
  by scripted keys), the platform readers and probes with fakes
  (`msvcrt`, `ctypes`, `termios`), the companion generators (including
  running the generated pytest suites in a subprocess), inspect / diagram /
  docs, the simulator engine, scripted and interactive modes, the
  launcher menu and wizard end to end, the `setup` shim lifecycle in a
  temp directory on every OS, and `update` with every I/O seam patched.
  Suite total 3,735 tests at 93% coverage.

## [0.9.1] - 2026-09-24

### Fixed

- **Round-13 re-verification findings** (#239–#248). Every bug
  reproduced against `v0.9.0` with the reporter's standalone repro before
  the fix and pinned in `tests/test_round13_findings.py` (24 tests, both
  engines where parity is the point).
  - **`Interpreter.drain_pending()` drains the priority lane too (#239).**
    It read the inbox only, so fired timers, engine completions and
    `send_priority()` events were omitted from the result *and* left
    queued, where `stop()` cleared them — the documented "drain, persist,
    stop" recipe silently lost every deadline that fired just before
    shutdown. Both lanes are drained now, priority first (the order
    `pending_events` reports); a `wait=True` receipt on a drained event is
    failed with `InterpreterStoppedError` instead of hanging.
  - **`on_interpreter_start` fires on a restored interpreter (#240).**
    Every resume branch of `start()` on both engines returned above the
    hook loop, so a lifecycle plugin saw a `stop` with no `start`. The
    hook now fires on every path, once; `interpreter.restored_from_snapshot`
    tells a plugin bring-up from resume.
  - **Malformed `chain_trips` / `last_chain_error` are
    `SnapshotCorruptError` (#241).** The #226 fields were read after the
    validator had passed the blob, so `"NaN"`, a list or a dict escaped
    `from_snapshot` as a raw `ValueError` / `TypeError` and broke the
    `except SnapshotCorruptError: quarantine` idiom. `check_shape` now
    requires a non-negative integer (a numeric string is accepted; `bool`
    is not) and a string-or-null message.
  - **The restored chain latch is a `RestoredChainError`, which IS a
    `RunawayChainError` (#243).** It also remains a `RestoredError`, so
    the live-machine guard `isinstance(interp.last_chain_error,
    RunawayChainError)` keeps firing across a restart instead of going
    silently `False`. `.limit` / `.dropped` are `None` on a restored
    latch (JSON kept the message); `chain_trips > 0` remains the
    type-independent signal. The generic `error` field is unchanged.
  - **A dropped `wait=True` receipt is observable deterministically
    (#244).** The #232 `RuntimeWarning` comes from a finaliser, which
    CPython routes to `sys.unraisablehook` — invisible to `-W error` and
    `pytest.warns`. New: `Interpreter.dropped_receipts` (a counter) and
    `PluginBase.on_receipt_dropped(interpreter, event_type)`, both driven
    from the same finaliser, so a test or health check can assert on them
    under any warning filter. Transition behaviour is unchanged.

### Added

- **`events.re_mint(original, **fields)`** (#248) — the sanctioned way to
  change a field of an engine-minted event and keep engine provenance
  (redact `data` before re-emitting, say). Gated on the input: it accepts
  only an event that already `is_system_event`, so it can carry
  provenance forward but never create it. `_replace()` stays a deliberate
  one-way demotion (#235) and the design note now says so.
- **`SyncInterpreter(max_queue_size=None, overflow_policy=None)`** (#245)
  for signature parity with `Interpreter`. The sync engine has no inbox to
  bound — `send()` runs each event to completion before returning — so a
  non-`None` bound raises a documented `ValueError` naming the alternative
  (admission control in the caller's wrapper) instead of a bare
  `TypeError` from a missing keyword. The class docstring and the API
  reference state the asymmetry.
- **`benchmarks/production_characteristics.py --json` / `--json-file
  PATH`** (#246) emits one JSON object with the host description
  (`library_version`, `python_version`, `platform`, `machine`,
  `processor`, `cpu_count`, `method`) and every measured row, so a CI job
  can gate on `lateness_ms` for its own hardware instead of scraping the
  table. The guide's "Measured on" line is that host block.

### Changed

- **Release provenance (#247).** Releases are published through PyPI
  Trusted Publishing (OIDC, no long-lived token — already the case since
  0.8.0) and now carry **PEP 740 build provenance attestations**
  (`attestations: true`, Sigstore-signed), binding each wheel and sdist to
  the GitHub Actions run, commit and workflow that built it. Verify with
  `pypi-attestations verify pypi --repository
  https://github.com/basiltt/xstate-statemachine <dist-url>` (see the
  README *Install* section).
- **Docs (#242, #243).** `snapshots.md` states the latch's type change in
  the same sentence as its restart survival, recommends `chain_trips > 0`
  for restart-safe guards, and spells out that `chain_trips` /
  `last_chain_error` are restored verbatim inside the #205 trust boundary
  — a party who can write the blob can manufacture or suppress a
  chain-trip alert.

## [0.9.0] - 2026-09-23 — Adopted

**Naming, and the site.**

### Fixed

- **Round-12 re-verification findings** (#225–#235). Every one
  reproduced against `main` @ `f4067b6` with the reporter's standalone
  repro before the fix and pinned in `tests/test_round12_findings.py`
  (31 tests, parametrised over `def` / `async def`, both engines where
  parity is the point).
  - **Self-send provenance is decided by task identity, not an inherited
    context (#225).** The #105 "issued from one of my actions" predicate
    rode a `ContextVar`, and `asyncio.ensure_future` / `create_task` copy
    the context, so a helper task spawned from an action was treated as
    the action for its whole life: its later `send(wait=True)` was refused
    by the #219 guard, and its plain `send()` was routed to the internal
    queue — drained only inside a macrostep — so with the loop idle the
    event sat there and the machine never advanced. The documented
    `ensure_future(i.send(..., wait=True))` escape hatch also flipped to
    a refusal whenever the spawning action awaited again afterwards. Both
    predicates now ask "is the *current task* running one of my actions?"
    (`_action_tasks`, per task with a nesting depth); the `ContextVar` is
    gone. A worker that outlives its action, and the hand-out idiom
    whether or not the action yields, are ordinary external traffic; the
    genuine in-step await is still refused.
  - **A `def` action that drops its `wait=True` receipt is told so
    (#232).** A synchronous action cannot await, so
    `r = i.send("B", wait=True)` handed it the #219 guard object and
    nothing ever said so. The object now emits a `RuntimeWarning` if it
    is finalised without ever being awaited or handed out — exactly as
    CPython does for a never-awaited coroutine. `ensure_future(...)`,
    `.add_done_callback`, `.result()` and `await` all count as use, so
    the supported shapes stay silent.
  - **The chain-trip latch survives a snapshot (#226).** `chain_trips`
    and `last_chain_error` are v3 envelope fields (additive; old blobs
    upcast to `0` / `None`). A restore reports the same count and a
    `RestoredError` carrying the message — the `error` precedent — and
    `clear_chain_error()` remains the only thing that clears it. The
    counter stays monotonic across the restart.
  - **`strict` and event schemas apply to restored `scheduled_sends`
    (#227).** `_rearm_restored_self_sends` re-armed every record
    unchecked, so an undeclared type in that lane was admitted silently
    on a `strict: True` machine while the same record in
    `pending_events` was refused (#214). Both lanes now go through
    `_admit_restored`; the refusal fires `on_invalid_event` and lands on
    `last_error`; the function returns how many were *armed*. A schema
    refusal (`InvalidEventPayloadError`) on either lane is now caught
    and reported the same way instead of aborting the whole restore.
  - **`from_snapshot(plugins=...)` (#230).** Plugins are registered
    *before* the persisted events are admitted, so a restore-time refusal
    reaches `on_invalid_event` like a runtime one. Same effect as `.use()`
    on the result, just early enough; the parameter is optional.
  - **The sync engine honours the priority lane on restore (#233).**
    `SyncInterpreter._enqueue_restored` accepted `priority` and ignored
    it; a `lane: "priority"` record now restores at the head of the
    single queue (FIFO within the lane, ahead of the inbox), the order the
    async engine's two lanes give.
  - **An inline-dict `invoke.src` is refused by name (#231).** The
    XState-JS inline-machine shape died as
    `TypeError: unhashable type: 'dict'` inside `logic_loader`. The parser
    now raises `InvalidConfigError` naming the state, the invoke id, the
    type it got and the supported alternative (build with
    `create_machine`, register in `MachineLogic(services=...)`).
  - **Engine mint helpers are private; `_replace` demotes to the public
    class (#235).** `events.engine_done` / `engine_error` / `engine_after`
    are renamed `_engine_*`; the unprefixed names remain as
    `DeprecationWarning` shims until 1.0. `_replace()` on an engine-minted
    event returns a plain `DoneEvent` / `ErrorEvent` / `AfterEvent` with
    `is_system_event(...) == False`: a caller-chosen variant is user
    traffic. `pickle` / `deepcopy` still preserve provenance (they
    reproduce the same value). The engine's own `fired_at` stamps re-mint.
  - **Test quality (#228).** The `nested_invoke` lap-parity shape in
    `tests/test_round9_findings.py` never exited its initial state and
    fired exactly two calls at every `maxIterations` — a constant agreeing
    with itself. It now re-enters the outer state (call count `mi + 3`,
    trips the guard, agrees on all three lanes). Every other limit sweep in
    the round pins (rounds 3, 5, 8, 9, 10) was audited: each asserts a
    `RunawayChainError` or a limit-derived landing state, so none is
    inert. `TestLivelockPinsAreLimitDependent` asserts, for each shape the
    sweep uses, that the count differs between two limits and at least one
    trips — so a future inert shape fails CI.
  - **Docs (#229).** `interpreters.md` states what the hand-out idiom
    requires and that a spawned helper may talk back to the machine;
    `snapshots.md` and Production Characteristics § 2 record that the
    chain-trip latch now crosses a restart.

- **Round-11 re-verification findings** (#218–#222). Every one
  reproduced against `main` @ `c78ce99` with the reporter's standalone
  repro before the fix and pinned in `tests/test_round11_findings.py`
  (23 tests, parametrised over `def` / `async def`, both engines where
  parity is the point).
  - **A delayed self-send releases its clock handle when it fires or is
    cancelled (#218).** The handle was registered under the interpreter
    id (so `stop()` could clear it) but the only pruner ran on *state*
    exit, so the list grew by one dead handle per beat for the life of a
    `raise(delay=)` heartbeat — unbounded now that #212 made such cycles
    legal. Both engines; a 200-beat heartbeat holds at most one handle.
  - **An action that awaits `send(..., wait=True)` on its own interpreter
    gets `ReentrantWaitError`, not a deadlock (#219).** The receipt
    resolves only when the run loop processes the event, and the loop
    cannot advance until the action returns; #215's descent gate made the
    hang reachable from `start()`. The receipt can still be handed out
    (`asyncio.ensure_future(i.send(..., wait=True))`) and awaited later,
    from any other task; only an await performed by the action's own
    task, while it runs, is refused (predicate narrowed in #225). The sync engine refuses the same
    shape for parity (there the receipt would have described the wrong
    step).
  - **Unknown config keys are checked in every state, transition and
    invoke, not only at the root (#220).** #216 iterated the root dict
    only, so `{"states": {"a": {"entyr": [...], "onn": {...}}}}` built a
    clean machine with no entry action and no transition, with no WARNING,
    under every strict setting. The check now recurses (nested `states`,
    parallel regions, `on` / `always` / `after` / `onDone` transition
    bodies, `invoke` entries and their `onDone` / `onError`) with a
    per-level known set — `KNOWN_ROOT_KEYS`, `KNOWN_STATE_KEYS`,
    `KNOWN_TRANSITION_KEYS`, `KNOWN_INVOKE_KEYS` (`KNOWN_MACHINE_KEYS` is
    kept as an alias of the root set). Findings name the path
    (`m.r2.y.z: 'tpye' (did you mean 'type'?)`); one WARNING or one
    `InvalidConfigError` lists them all. `x-` keys and `meta` /
    `description` / `tags` are accepted at every level.
  - **Restore → re-persist without `start()` keeps armed delayed
    self-sends (#221).** `from_snapshot` parked the v3 `scheduled_sends`
    records for `start()` to re-arm, but `get_persisted_snapshot` read
    only the live armed set — so a journal-compaction or migration job
    that loads and rewrites blobs without starting a machine silently
    dropped every deadline it touched. The parked records are now
    re-emitted verbatim until `start()` consumes them.
  - **A chain-budget trip is sticky (#222).** `last_error` is recomputed
    per processed event, so one benign handled event erased the only
    record that the machine had discarded work — and post-#212 a heartbeat
    guarantees such an event arrives. New on both engines:
    `interpreter.chain_trips` (monotonic count), `interpreter.
    last_chain_error` (a latch, cleared only by `clear_chain_error()`)
    and `PluginBase.on_chain_budget_exceeded(interpreter, error, event)`,
    fired once per trip (settle-budget trips included). `last_error` is
    documented as the per-step read it always was.

- **Round-10 re-verification findings** (#212–#216). Every one
  reproduced against `main` @ `19cb1f1` with the reporter's standalone
  repro before the fix and pinned in `tests/test_round10_findings.py`
  (15 tests, parametrised over `def` / `async def`, both engines where
  parity is the point).
  - **A delayed self-send is a timer, not a chain (#212; supersedes the
    #206 rule).** #206 charged a `raise(delay=)` self-send as a debt of
    the arming step; #212 showed that killed every self-paced heartbeat or
    poller at `maxIterations` beats regardless of period — the charge was
    time-blind. The rule is now the `after` rule: arming a delay ends the
    step's chain, the firing is a clock event. A `raise(delay=)` heartbeat
    of any period runs indefinitely, exactly as an `after` one does, and a
    1 ms `raise(delay=)` ping-pong is a periodic process exactly as an
    `after: 1` ping-pong has always been. `maxIterations` bounds work the
    machine feeds itself *within* a step (zero-delay `raise`, self-`send`,
    completions re-arming invokes) — stated in `json-config.md`,
    Production Characteristics § 2 and the round-9 pins, which are
    rewritten to the new rule.
  - **An armed, unfired delayed self-send survives a snapshot (#213).**
    It existed nowhere the snapshot could see and was silently
    discharged, so a state whose only exit was a delayed self-raise
    restored permanently parked. Snapshot layout **v3** adds
    `scheduled_sends`: each armed self-send with its *remaining* delay and
    id; `start()` re-arms them, on both engines, with the standing they
    had. Cancelled sends leave no record.
  - **The restore path applies `strict`, keeps legacy `after` deadlines,
    and restores the priority lane as a lane (#214).** Restored user
    events pass the same `strict` check a `send()` does; a refusal is
    reported (`on_invalid_event`, `last_error`) and the event dropped.
    A v2 (0.8.0-era) `done` / `error` / `after` record is upcast as
    engine-minted — only the engine could have written one — so a
    persisted deadline still fires rather than being silently demoted by
    #203's gate; a v3 record without the flag stays user traffic. Records
    carry `lane`, so a fired timer restores ahead of the inbox.
  - **Three-lane lap parity on an engine-work-only chart (#215).** Two
    async-only defects: the settle budget reset on a self-raised plain
    event (the sync drain keeps it for anything the machine generated),
    and the run loop consumed the initial descent's own `raise` while an
    `async def` entry action was still yielding — interleaving two
    macrosteps the sync engine's re-entrancy guard forbids. The reset now
    keys on external provenance; the loop waits for the descent to settle;
    descent-queued raises get seed standing. `always` + zero-delay `raise`
    agrees on all three lanes at limits 1–25, pinned as a sweep.
  - **Unknown top-level config keys are caught (#216).** A misspelled
    policy key (`actionErrorPolicyy`, `Strict`, `maxIteration`,
    `onUnhandledEvent`) was silently dropped and the policy reverted to
    its permissive default. Default: WARNING with a "did you mean" hint;
    `create_machine(strict_config=True)` or config-level
    `"strictConfig": true`: `InvalidConfigError`. `x-`-prefixed keys and
    `meta` / `description` / `tags` / `version` are always accepted.
    `KNOWN_MACHINE_KEYS` is the single list.

### Changed

- **Snapshot layout version 2 → 3** (#213, #214): adds `scheduled_sends`,
  per-record `engine` provenance and `lane`. v2 payloads upcast
  transparently; `from_snapshot(minimum_version=3)` refuses anything
  older.

### Fixed

- **Round-9 re-verification findings** (#203–#210). Every one
  reproduced against `main` @ `f28719c` with the reporter's standalone
  repro before the fix and pinned in `tests/test_round9_findings.py`
  (19 tests, parametrised over `def` / `async def`, both engines where
  parity is the point).
  - **`invoke` runs after eventless transitions settle (#204; SCXML §6.1
    `statesToInvoke`).** Entry recorded the state; the settle pass, once
    stable, arms invokes for the recorded states still active. A state
    entered and exited within one macrostep — rolled forward by an
    `always`, rolled back by `actionErrorPolicy` — never submits its
    service, on either engine and for either service kind. This closes
    the roll-forward half of #193 that had landed on one engine only.
  - **`after` transitions match on provenance (#203).** #195 minted
    `_EngineAfter` but selection still matched the public `AfterEvent`
    class, so a hand-built event or a forged snapshot record fired a
    60-second timer instantly. Only an engine-minted `AfterEvent` drives
    an `after` transition, as `done`/`error` already required.
  - **A delayed self-`send` is self-generated work (#206) — superseded
    by #212 in round 10.** #206 made a `raise(delay=)` self-send a debt of
    the arming step so a 1 ms ping-pong would trip; #212 showed that rule
    was time-blind and killed every self-paced heartbeat at
    `maxIterations` beats. The shipped rule is the `after` rule (see the
    round-10 entry): a delayed self-send is a timer, its firing is a clock
    event, and a delayed ping-pong of any period is a periodic process —
    as an `after: 1` ping-pong has always been. `maxIterations` bounds
    work generated *within* a step.
  - **A chain cut that strands an invocation is observable (#207).** A
    `rollback + onDone` storm cut at `maxIterations` left the machine
    parked in the invoking state with nothing running and no completion
    that could ever arrive, distinguishable from "waiting on a slow
    service" only by polling the configuration against the chart. Both
    engines now name it: `RunawayChainError.stranded` carries the invoke
    ids, the new `on_invocation_stranded(interpreter, state_id, invoke_id,
    error)` hook fires, an ERROR log names the state, and
    `has_dormant_invocations` / `pending_invocations()` answer on demand.
    The reporter's "self-terminates below the limit" reading was the
    plateau sampled at 0.45 s while the `def` lane was still climbing; the
    cycle trips at exactly `maxIterations + 2` on both lanes.
  - **A receipt is never success-shaped over an empty configuration
    (#208).** Receipts are resolved after the in-flight flag is down, so
    the reported coincidence with a `SnapshotMidStepError` cannot occur on
    this tree (the repro's own run shows 0 hits); the receipt path now also
    refuses to report `ok` when the step ended with an illegal
    configuration, as belt and braces.
  - **Lap parity, stated exactly and pinned as a sweep (#209).** The
    sync engine ran two laps more than async at every *odd* limit on
    `rollback + onDone` because the initial descent's settle work was
    charged against the seed chain on the async engine only. The seed's
    standing now covers the settle budget too; all three lanes agree at
    limits 1–25, odd and even, on both shapes. The #201 changelog sentence
    is corrected.
  - **`TestAsyncRollbackRearmCycleBounded` waits for convergence (#210)**
    instead of sampling at fixed 0.6 s / 0.9 s, and asserts the exact
    plateau (`maxIterations + 3`, identical to the sync engine).

### Added

- **`from_snapshot(minimum_version=0, expected_machine_hash=None)`**
  (#205). A snapshot is trusted input by contract; `machine_hash` is a
  fingerprint against accidental drift, not a MAC. A caller who does not
  trust the payload can refuse a version-0 downgrade
  (`SnapshotVersionError`, new `.minimum` attribute) and compare the
  fingerprint against a value *they* hold (`SnapshotDriftError` on
  mismatch or absence, regardless of version), so the payload cannot
  select its own level of checking. The trust boundary is stated in the
  `from_snapshot` docstring, the API reference, the snapshot guide and
  `structure_hash`.
- **`PluginBase.on_invocation_stranded`** (#207) and
  **`RunawayChainError.stranded`**.

### Fixed

- **Round-8 re-verification findings** (#192–#201; reopened #181, #186).
  Every one reproduced against `main` @ `6db65d8` with the reporter's
  standalone repro before the fix and pinned in
  `tests/test_round8_findings.py` (29 tests, every service/action test
  parametrised over `def` / `async def`, both engines where parity is the
  point).
  - **The priority lane sheds by provenance, not position (#192).** #180
    taught the *charge* site who issued an event; the *shed* site still cut
    whatever sat at the head of the FIFO when a chain tripped, so an
    external `send(priority=True)` could be destroyed as `chain_budget` by
    a runaway it had nothing to do with, and a priority send issued from an
    action was never charged at all. Each lane item now carries its
    provenance; only self-generated items are ever shed, and an
    action-issued priority send is charged like a `raise`.
  - **A `def` service is unwound by rollback and roll-forward (#193).** The
    executor handoff moved from arm time into the task the engine holds,
    so a transition that arms the invoke and is then rolled back
    (`actionErrorPolicy: "rollback"`) or rolled forward (an `always` out of
    the state) cancels it before the callable is submitted — as a coroutine
    service's task is never started. A result that arrives for an exited
    state is ignored (SCXML §6.4.2). The cancellation half of the report is
    the documented plain-`def` contract on **both** engines — the entering
    step awaits the service, so an event cannot pre-empt it — and
    Production Characteristics § 2 now says so; `async def` remains the
    interruptible kind.
  - **`children_timeout` is per child and always reports an overrun
    (#194; reopened #181).** The bound was aggregate and its WARNING sat on
    the same timeout path, so a non-yielding `def` entry action both defeated
    the bound and silenced the warning. N coroutine children settle in ~D;
    the WARNING fires whenever the allowance was exceeded, including the
    single-threaded case a bound cannot pre-empt — which the docs now state.
  - **`DoneEvent` / `ErrorEvent` / `AfterEvent` carry provenance (#195).**
    They were public NamedTuples trusted on a bare `isinstance`, so a
    hand-built `DoneEvent("done.invoke.fill", ...)` bypassed `strict` and
    `onUnhandled` and drove a real `onDone` while the genuine service was
    still running — in-process, or reconstituted from a snapshot record by
    `restore_event()`. The engine now mints private subclasses
    (`_engine_done` / `_engine_error` / `_engine_after`, private since #235), `is_system_event`
    requires them, a user-built one is refused under `strict` with a message
    naming it as an engine-generated name, and persisted completions carry
    `"engine": true` so a genuine round-trip keeps its provenance while a
    forged record restores as user traffic.
  - **An `always` never competes for a named event (#196).** Eventless
    transitions were eligible candidates for *named* events, and a deeper
    `always` outranked a shallower handler, so under a spinning `always`
    every external event was consumed by a transition unrelated to it and
    its own actions never ran — with `last_error` clean. Eventless
    transitions are now selected only in the eventless settle pass (SCXML
    §3.13); the settle trip is reported on every step it affects. The
    reporter's parity gap was #179's inbox-lane reset, closed in round 7.
    Surfaced alongside: `SyncInterpreter` did not stop the child actor an
    exited state's `invoke` had started (the async engine has since #43),
    so the re-entering cycle leaked one pump thread per lap; it now keeps
    the same owner map and reaps invoked children on exit and on `stop()`.
  - **#197 pinned.** `send(wait=True)` never resolves over an empty
    configuration on either engine or lane (property test, 15 laps × 2
    kinds × 2 engines); the window closed with #179/#182.
  - **Versioned payloads carry both configuration fields (#198; reopened
    #186).** The agreement rule short-circuited on an *empty* field, so
    emptying `state_ids` — a strictly simpler mutation than contradicting
    it — let a forged `configuration` relocate the machine. On a
    `version >= 1` running snapshot both fields must be present and
    non-empty; v0 payloads keep the `state_ids`-only shape.
  - **`on_interpreter_start` is inside the in-flight window (#199).** The
    hook fired a few lines before #182's guard was raised, with
    `status="running"` and no configuration; a snapshot from it was the
    exact torn shape #182 closed. The flag is up before the hook on both
    engines.
  - **The owed-completion ledger is task-keyed and leak-free (#200).** A
    bare counter was decremented by whichever completion arrived next and
    leaked when a service task ended with a `BaseException` that was
    neither `Exception` nor `CancelledError`. Each debt is now the owing
    task itself, settled by that task's done-callback on every terminal
    outcome; one invocation's completion can never pay another's debt.
  - **Lap parity, stated exactly (#201).** The round-7 sentence "both
    service kinds trip at the same lap count as the sync engine" was one
    lap off for a cycle starting from the *initial* state (22 vs 23): the
    first completion the initial descent produces is the chain's seed
    (user standing, the sync drain's #77 rule), not a link. Fixed; all
    three lanes agreed on the shapes tested at the time. (Round 9, #209,
    found the sync engine two laps ahead at every *odd* limit on the
    `rollback + onDone` shape; with invokes armed at the end of the
    macrostep (#204) and the initial descent's settle work given seed
    standing, all three lanes now agree at every limit, odd and even, on
    both the ping-pong and rollback shapes -- pinned as a sweep.)
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
  The async engine already behaved correctly. *(0.9.0 note: plain
  external events were still counted and could be discarded — see
  #77 above; the two engines agree as of 0.9.0.)*
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
