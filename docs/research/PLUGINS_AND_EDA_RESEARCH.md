# Integration Plugins & Event-Driven Architecture — Research Report

> **Status:** research only — no code. Prepared as the basis for a PRD and
> phased implementation plan for `xstate-statemachine` 0.11 → 1.0.
> Four parallel research tracks (framework integrations, event-driven
> architecture, ecosystem/packaging/adoption, developer pain points + XState
> parity), each with 15–30 live web searches, synthesised below. Sources are
> cited inline; download figures are order-of-magnitude (pepy.tech /
> pypistats) and should be re-verified before external use.

---

## 0. Executive summary

1. **The core stays zero-dependency.** Every integration ships behind a pip
   extra (`xstate-statemachine[django]`, `[fastapi]`, `[sqlalchemy]`,
   `[observability]`, …) and lazy-imports its target framework with a clear
   error. Heavy or fast-moving targets (LangGraph, Home Assistant) go to
   separate distributions later, following the OpenTelemetry-contrib model.
2. **Persistence is the keystone, not a plugin among plugins.** Almost every
   real problem surfaced — concurrent transitions, multi-worker deployments,
   sagas, outbox/inbox, durable timers, audit, migration of in-flight
   instances — reduces to *"a snapshot that lives in a store, with a lock and
   a version stamp."* A framework-agnostic **store adapter protocol** plus
   concurrency/idempotency layers is the first thing to build; Django,
   SQLAlchemy, Redis adapters are thin over it.
3. **Two markets, one narrative.**
   - *Web backends* (Django/DRF/FastAPI/Flask/SQLAlchemy/Celery): a crowded
     but huge space where the differentiator is real statecharts
     (hierarchy, parallel, `after`, `invoke`, actors) versus the flat FSMs of
     `django-fsm-2` / `transitions`, plus first-class async. **FastAPI has no
     incumbent at all.**
   - *LLM agents* (LangGraph ~44M/mo, LangChain, pydantic-ai, CrewAI,
     AutoGen): a fast-growing space explicitly asking for "the model proposes,
     the machine decides" — deterministic, inspectable, replayable control
     flow with guards for budget/safety and human-in-the-loop as a durable
     waiting state. `statelyai/agent` validates the concept in TypeScript
     (~460 ★, alpha); **no Python equivalent exists.** This is the lead
     marketing story.
4. **Event-driven architecture is won by being honest.** Nearly every pain
   point found (Temporal non-determinism surprises, Step Functions opaque
   debugging, Celery silent chord failures, broker reconnect bugs) is a gap
   between an implicit promise and delivered behaviour. We promise
   at-least-once + idempotent inbox, resume-from-last-snapshot durability,
   version-stamped snapshots that fail loudly, deterministic time — and we say
   plainly what we do not offer (true exactly-once, automatic mid-flight
   schema migration, deterministic replay of arbitrary user code).
5. **Testing is where we can exceed the JS ecosystem**, not merely match it:
   the chart already declares which events are legal in which state, so a
   Hypothesis `RuleBasedStateMachine` can be generated with preconditions
   derived from the graph — shrinking gives minimal failing event sequences
   for free. Plus `@xstate/graph`-style path generation, a state/transition
   coverage report, and pytest fixtures over the existing `SimulatedClock`.

---

## 1. What we have today (inventory)

| Capability | Where | Relevance to plugins |
|:--|:--|:--|
| 23 lifecycle hooks on `PluginBase` (`on_transition`, `on_action_error`, `on_service_*`, `on_chain_budget_exceeded`, `on_event_dropped`, `on_invalid_event`, `on_guard_evaluated`, `on_done`, …) | `plugins.py` | Observability, audit, outbox and metrics plugins are "just" hook implementations |
| `get_snapshot()` / `from_snapshot(..., clock=, restart_timers=, minimum_version=, plugins=)` | interpreters | Store adapters serialise this; `restart_timers` is the lever for durable `after` |
| `send(wait=True) -> Receipt` (`changed`, `denied`, `deferred`, `error`) | interpreters | HTTP status mapping (200 / 409 / 422) for web plugins |
| `can(event)`, `known_events`, `matches()` | interpreters | Admin "available actions" buttons, OpenAPI per-event routes |
| `SimulatedClock`, `wait_for`, `to_promise`, pure `transition()` | `clock.py`, `helpers.py` | Testing plugin, deterministic EDA tests |
| Actors (`spawn`), `sendTo`, `raise` built-ins | `base_interpreter.py` | Saga orchestration, process managers |
| `strict`, `event_schemas`, `strict_config`, `actionErrorPolicy`, `onUnhandled` | factory / interpreters | Pydantic event validation maps onto `event_schemas`; failure policies map onto HTTP semantics |
| `xsm` CLI (generate, inspect, simulate, diagram, docs, setup, update) | `cli/` | Codegen of framework glue (DRF viewsets, FastAPI routers), `xsm inspect --live` |
| Packaging: `[project.optional-dependencies] format = [black, isort]` only | `pyproject.toml` | Extras mechanism already exists; add groups |

---

## 2. Framework integration landscape

### 2.1 Django (+ DRF) — priority HIGH

**Incumbents.** `django-fsm-2` (maintained fork of the archived `django-fsm`;
`FSMField`, `@transition(source, target)`, `can_proceed`), `django-fsm-admin2`
(transition buttons in admin), `django-fsm-log` (signal-driven audit),
**Viewflow** (2.9k ★, AGPL/commercial BPMN engine with a lighter
`viewflow.fsm.State`), `django-lifecycle` (`@hook` conditions, not an FSM),
`django-model-utils` (`StatusField`/`MonitorField`, no transitions).

**Voiced gaps** (GitHub issues): no nested / hierarchical machines
(`viewflow/django-fsm#125`, open since 2016 — the maintainer's answer was
"call code inline"); `transitions` has no first-party Django adapter and its
per-instance decoration has documented overhead (`pytransitions#435`);
migration pain from the archived `django-fsm` to Viewflow; transitions only
persist on explicit `.save()` so async/serializer paths silently lose them;
`ConcurrentTransition` exists in django-fsm precisely because concurrent
writes are unsolved.

**Idiomatic surface:** Django app + `AppConfig`, model field (`JSONField`-
backed), `ModelAdmin` mixin, management command, `pre_/post_` signals,
migrations, `select_for_update()`.

**Wishlist for `xstate-statemachine[django]`:**

| Feature | Notes |
|:--|:--|
| `StatechartField` (JSONField-backed snapshot; `state` + `context` columns optional for indexing/filtering) | Hydrates a `SyncInterpreter` lazily on access; `queryset.filter(state__in=[...])` via a denormalised `state_ids` array/text column |
| `StatechartModelMixin`: `obj.send("PAY")`, `obj.can("PAY")`, `obj.available_events`, `obj.machine` | Mirrors `can_proceed`; sends are wrapped in `transaction.atomic()` + `select_for_update()` by default, opt-out flag |
| `pre_transition` / `post_transition` Django signals dispatched from `on_transition` | Lets `django-fsm-log`-style audit apps work unmodified |
| `TransitionAdminMixin`: buttons for **guard-computed available events** (not just declared ones), confirmation, reason field | Reuses `django-fsm-admin2`'s hidden-input dispatch pattern |
| `PermissionGuard(perm="app.can_approve")` helper → `user.has_perm` as a guard, user passed via event payload | Matches Viewflow's `.Permission()` idiom |
| `TransitionLog` model + `AuditPlugin` (from, to, event, actor, reason, ts) written in the **same transaction** | Fixes django-fsm-log's separate-write race |
| Version-stamped snapshots + `SnapshotMigrator.register(from, to, fn)` hook | Fails loudly on mismatch; manual upcast recipe (see §5) |
| Management commands: `python manage.py xsm_inspect app.Model`, `xsm_diagram`, `xsm_docs` | Reuse the CLI |
| **DRF**: `StatechartViewSetMixin` auto-generating `@action(detail=True, methods=["post"])` per declared event; `StatechartSerializerField` exposing `state`, `context`, `available_events`; `Receipt` → HTTP: `changed`→200, `denied`→409, `deferred`→202, unknown/invalid→422 | Viewflow's 2026 changelog splitting `TransitionNotAllowed` into `NoTransition` shows this mapping is live, non-trivial and valuable |
| Django Channels `StatechartConsumer` mixin: WS `{"event": "...", "payload": {...}}` → `send()`, `on_transition` → group broadcast; interpreter lifecycle tied to `disconnect()` | Prevents the "consumer coroutine lingers" leak documented in Channels posts |

### 2.2 FastAPI / Starlette — priority HIGHEST

**Incumbents: none.** `fastapi-state` (0.2.0) is a generic app-state DI helper,
not an FSM; `carvalhocaio/fastapi-state-machine` is a teaching repo. FastAPI is
~500M downloads/month and growing fastest of all web frameworks. Best
architectural template to copy: `svcs` (Hynek) — a `Registry` on `app.state`
built in `lifespan`, a `Container` injected via `Depends()`. FastAPI
discussions #11742/#11427 confirm DI is not natively usable inside `lifespan`;
route around it.

**Wishlist for `xstate-statemachine[fastapi]`** (built on a Starlette-native
core so `[starlette]` and later `[litestar]` are thin):

| Feature | Notes |
|:--|:--|
| `StatechartRegistry` managed by `lifespan` (start/stop every live actor on shutdown) | Reuses `TaskManager` cleanup; multi-worker caveat documented (§5) |
| `Depends(get_interpreter("order", key=Path("order_id")))` — per-key interpreter resolved from a store adapter (create-act-persist-discard) | The only honest pattern under gunicorn/uvicorn workers |
| `StatechartRouter(machine, prefix="/orders")` → one `POST /{id}/events/{EVENT}` (or `/{id}/send`) per declared event, plus `GET /{id}` (state, context, available_events) and `GET /{id}/diagram.mmd` | **Automatic OpenAPI docs of the machine's public surface** — no Python FSM library offers this |
| Pydantic v2 **discriminated-union** request body over the chart's event names (`Field(discriminator="type")`), per-event payload models, 422 on bad payload; bridges to `event_schemas=` | Pydantic's own docs recommend discriminated unions for exactly this multi-shape case |
| `Receipt` → HTTP status mapping (200/202/409/422), `Idempotency-Key` header → inbox dedup | |
| WebSocket / SSE **transition streaming**: `WebSocketBroadcastPlugin`, `sse_stream(interpreter)` for `StreamingResponse` | Live UIs, dashboards, inspector |
| `BackgroundTasks` integration for fire-and-forget side effects from actions | |
| Litestar `XStatePlugin` following its documented plugin API (`SQLAlchemyPlugin` is the reference) | Cheap once the Starlette core exists |

### 2.3 Flask (+ Quart) — priority MEDIUM

No Flask FSM extension exists. Canonical `init_app` pattern (must not bind app
state on the instance, per Flask docs). Wishlist: `XState(app)` extension →
`current_app.extensions["xstate"]` registry; `g.interpreter` via
`before_request`/`teardown_appcontext`; `create_statechart_blueprint(machine,
url_prefix)` (one route per event, same Receipt→status mapping); `flask xsm …`
CLI group reusing `xsm`. Quart inherits it almost verbatim.

### 2.4 SQLAlchemy (sync + async) — priority MEDIUM-HIGH (leveraged)

No FSM-specific library; idioms are `TypeDecorator`, `event.listens_for`
(`before_update`, `propagate=True`), `version_id_col`, `AsyncSession`.
Wishlist for `xstate-statemachine[sqlalchemy]`: `StatechartType(TypeDecorator)`
over JSON/JSONB (`cache_ok = True`); `StatechartMixin` with hybrid `state`
column; **optimistic locking via `version_id_col`** on the state column (the
declarative answer to django-fsm's `ConcurrentTransition`); `before_update`
listener wired to `on_transition` for transactional audit; `AsyncSession`
support paired with the async `Interpreter`; **outbox table** helper
(transition → integration-event row in the same transaction). Underlies both
Flask and FastAPI persistence, so it multiplies reach.

### 2.5 Celery — priority MEDIUM (unique)

Celery has no state abstraction beyond a fixed task-state enum; users compose
with canvas (`chain`/`group`/`chord`), which has documented hangs and OOM
issues (`celery#5354`, `#5000`, `#6197`, `#8211`). Nobody maps XState
`invoke`/`onDone`/`onError` onto Celery. Wishlist: `celery_service(task)` —
an `invoke` service that `.apply_async()`es and resolves `onDone`/`onError`
from `task_success`/`task_failure` signals (or result-backend polling) via a
store-backed interpreter; **Celery Beat-backed durable `after`** (timers
survive process restarts); `@shared_task` helper that loads-sends-persists a
machine by id (the worker-side create-act-persist-discard).

### 2.6 Pydantic v2 — shared infrastructure

Not a standalone extra: typed `Context` (`BaseModel`/`TypedDict` validated on
every `assign`, `ContextValidationError` — "silent acceptance is a bug"), typed
events as discriminated unions feeding `event_schemas=`, `TypeAdapter`
validation of raw machine JSON before `create_machine()`, and
`generate_json_schema(machine)` for frontend teams. Consumed by the FastAPI,
DRF and testing plugins.

### 2.7 Others (defer)

Sanic (declining mindshare), Tortoise/peewee (small), aiohttp (Starlette-core
recipe suffices). Revisit on demand.

---

## 3. Event-driven architecture: what developers struggle with

### 3.1 Pattern → statechart → what the library must provide

| Pattern | Today (pain) | Statechart shape | Library/plugin need |
|:--|:--|:--|:--|
| Saga / process manager | Hand-rolled step ledgers per project (`python-saga-orchestrator`, countless tutorials) | States = steps, `invoke` per step, `onError` = compensation path, `after` = step timeout, context = accumulated results | Persist snapshot on every transition (store adapter); a documented saga recipe + `SagaBuilder` sugar |
| Outbox | Dual-write bug; no Python library standardises it | `on_transition` writes integration-event rows in the **same** transaction as the snapshot | `OutboxPlugin` + drain worker; requires SQLAlchemy/Django adapter |
| Inbox / idempotency | At-least-once redelivery double-processes (webhooks, SQS, Kafka) | Dedup before `send()` keyed by `(machine_id, event_id)` | `IdempotencyPlugin` over the same store; `Idempotency-Key` header support in web plugins |
| Exactly-once | Vendors over-promise; brokers converge on "dedupe at the edge" (Redis 8.6 idempotent XADD) | — | **Never claim it.** Ship the inbox and say so |
| DLQ / retries | Poison messages; `tenacity` raises instead of routing; lost error context | Retry count in context, backoff via `after` with dynamic delay, `onError` → `dead_lettered` state | `RetryPolicy` helper (backoff+jitter delay fn), `DeadLetterPlugin` publishing full error context |
| Durable timers | In-process timers die with the process (also true for us today) | Persist `(state, deadline)`; on restore re-arm or fire matured | `from_snapshot(restart_timers=)` exists; add deadline persistence + a `DurableTimerScheduler` (Celery Beat / APScheduler / DB-polled) |
| Versioning in-flight instances | Temporal requires `patched()`/Worker Versioning; no Python FSM handles it at all | Stamp every snapshot with `machine_version`/config hash | Fail loudly on mismatch; `SnapshotMigrator` hook + manual upcast recipe. **Do not promise automatic migration** |
| Event sourcing + CQRS | `eventsourcing` lib is DDD-first, steep, no graph | Snapshot = checkpoint; `on_transition` log = append-only event stream; replay via `transition()` | `TransitionLogPlugin`; `replay(events) -> snapshot` test helper |
| Domain vs integration events | Every internal event leaks to the bus | Whitelist per state via `meta`/`tags` | Outbox/broker plugin publishes only tagged events |
| Choreography | Machines must react to a shared bus | Inbound broker messages → `send()` keyed by partition/machine id | Broker adapter protocol (§3.3) |

### 3.2 Existing tooling and pain (evidence)

| Tool | Top pain (issue) |
|:--|:--|
| Temporal Python SDK | Non-determinism after code change (`sdk-python#1591`), boilerplate (`#1184`), OTel gaps (`#449`), needs a server |
| Prefect | 24h execution ceilings; event-API limits silently disabling automations |
| Airflow / Dagster | DAG boilerplate, hard unit testing, data-centric not event-centric |
| Celery canvas | Chord needs result backend (`#6197`), recursive chord OOM (`#5000`), `ChordError` despite handler (`#8211`) |
| Dramatiq | Silent stalls on specific queues (`#224`) |
| Faust | Dormant original; hangs (`#670`), stuck recovery (`#651`) |
| aio-pika / nats-py | Reconnect-but-never-resume (`aio-pika#563`, `nats.py#751/#184`) |
| AWS Step Functions | Opaque debugging, all logic via Lambda, weak local testing |
| `eventsourcing` | Steep, no Django ORM integration |
| `transitions` / `python-statemachine` / `django-fsm-2` | No persistence / partial Django only / flat single field |

Cross-cutting: most broker bugs are **reconnect/resume** or **silent
stall/duplicate** — exactly what an explicit interpreter lifecycle
(`status`, `on_interpreter_start/stop`, snapshot-driven resume) makes
observable and recoverable.

### 3.3 Broker adapter surface (proposal)

One `BrokerAdapter` protocol, one extra per broker (`[kafka]` aiokafka,
`[rabbitmq]` aio-pika, `[redis]` redis streams, `[nats]`, `[sqs]` boto3):
`consume(topic) -> AsyncIterator[Envelope]` → `interpreter.send()`, partition
key = machine id (preserves per-entity ordering; matches Kafka partitioning and
SQS FIFO group ids); `publish(envelope)` from an `on_transition` plugin for
whitelisted events. **Envelope = CloudEvents** (`cloudevents` PyPI SDK exists;
`correlationid`/`causationid` extension; add `machineid`), so AsyncAPI docs
can `$ref` the schema and non-Python consumers interoperate. Retries reuse
`after`-based backoff; dedup uses envelope `id`. FastStream (5.3k ★) is the
closest prior art for an idiomatic multi-broker surface and its **in-memory
test broker** is the pattern to copy (`FakeBrokerAdapter`). Consider a
"FastStream subscriber → interpreter" recipe before building every adapter.

### 3.4 Observability (cheapest, high signal)

All four map onto existing hooks: **OpenTelemetry** — messaging semantic
conventions for broker spans; custom `statechart.*` span attributes for
transitions (no official convention exists; say so). **Prometheus** —
`xstatemachine_transitions_total{machine,from,to,event}`,
`_transition_duration_seconds`, `_guard_evaluations_total{guard,result}`,
`_service_duration_seconds`, `_dlq_depth`. **structlog/loguru** — bind
`machine_id`/`state_id`/`correlation_id` context vars in `on_transition`.
**Sentry** — breadcrumb per transition, turning "silently dead machine" into a
trail.

### 3.5 Honest guarantees

Can promise: at-least-once + idempotent inbox; resume-from-last-snapshot
(at most one transition of work redone); loud failure on version mismatch;
deterministic tests with `SimulatedClock`. Cannot promise (and must say so):
true exactly-once; automatic mid-flight schema migration; deterministic replay
of arbitrary user action code (Temporal/Restate journal every side effect —
far larger scope); broker guarantees beyond the client's own.

---

## 4. The LLM-agent opportunity (lead narrative)

LangGraph is a Pregel-style flowchart: nodes = functions, edges = routers,
shared `TypedDict`; no compound/parallel states, no declarative guards, no
`after`, checkpointing is complex. pydantic-ai is single-agent/code-first with
no graph; CrewAI hides transitions; AutoGen is conversation-centric with no
formal state. 2025–26 engineering posts explicitly frame the fix as "wrap the
LLM in an explicit state machine: the model proposes, code decides".
`statelyai/agent` (XState, TypeScript, ~460 ★, alpha) validates the concept;
`burr` (2.5k ★) is the nearest Python analogue but targets agent DAGs, not
XState-compatible statecharts. **There is no Python "XState for agents".**

What we uniquely offer: guards as budget/safety policy (`underTokenBudget`,
`toolAllowedInState`), `after` timeouts for stuck tools, human-in-the-loop as
a **durable waiting state** (web request pauses, worker resumes — awkward in
graph-node models), snapshot/replay, actors per sub-agent (parallel regions
for multi-agent handoff), and **design in the free Stately editor, run in
Python**.

Deliverable: `[agents]` — recipes first (tool-use loop as a statechart:
`awaiting_model` → `awaiting_tool` → `awaiting_human` → `done`/`error`;
`invoke` wraps the provider call; `instructor`/Pydantic validates per-state
output), then thin adapters (statechart-as-LangGraph-node for incremental
adoption; pydantic-ai agent as an `invoke` service), and comparison pages
("vs LangGraph", "vs Burr", "vs statelyai/agent"). Submit to awesome-LLM /
awesome-langchain lists with the recipe.

---

## 5. Concurrency, persistence, multi-worker (the keystone)

**Problem.** An interpreter is process memory; gunicorn/uvicorn workers and
concurrent requests on the same entity make "keep it in RAM" wrong. The model
that every durable system converges on is **create → act → persist →
discard**: load the last snapshot at request start, send one (or a batch of)
event(s), persist, drop the object. `after` timers are the casualty and need a
durable scheduler.

**Mechanisms (all should be pluggable):**

| Mechanism | Use | Cost |
|:--|:--|:--|
| Pessimistic row lock (`select_for_update`, SA `with_for_update`) | Financial/critical, conflicts common | Serialises; deadlock risk |
| Optimistic version column (Django `F()`/SA `version_id_col`) + retry | High concurrency, low conflict (most web entities) | Retry loop |
| Redis lock (`redis.lock`/Redlock) | Multi-host, non-DB entities | Extra infra; TTL tuning |
| Idempotency key table | Webhooks, retried calls, double-submits | Does not replace locking |

**Store adapter protocol** (core, zero-dep): `load(key) -> (snapshot,
version)`, `save(key, snapshot, expected_version)`, `lock(key)` context
manager, `seen(event_id)`/`mark(event_id)`. Backends: Django ORM, SQLAlchemy,
Redis, SQLite/file (zero-dep, for local/dev), DynamoDB later. Event-sourced
variant: `append(event)` + periodic snapshot.

**Versioning.** Stamp `machine_version` (explicit or config hash) in every
snapshot; on load, if mismatched, run registered upcasters or **refuse
loudly**. Prefer additive changes. Scope initial actor-tree snapshot restore as
"best effort" — XState itself still has an open bug there (`xstate#5077`).

---

## 6. Real developer problems → plugin features (catalogue, abridged)

| Problem (source) | Plugin feature |
|:--|:--|
| Order/checkout "boolean flag hell" (dev.to enums-over-booleans) | ORM field + guards; `state__in` queries |
| Stripe subscription webhooks as `elif` chains; retries double-apply | **`[stripe]` recipe/adapter**: event name → XState event, signature check, `event.id` idempotency |
| KYC / approvals; "who approved and why" lives in Slack | Parallel regions for independent checks; `AuditPlugin` with actor + reason |
| Circuit breaker reimplemented per service | Cookbook chart + `@circuit_breaker(machine)` decorator |
| Feature-flag rollout stages | Recipe; metrics-guard adapter (low priority) |
| Upload/processing pipelines → Step Functions for want of state | `invoke` + `onError` in-process; Celery/RQ/arq **task-runner adapter** for off-process work |
| Webhook idempotency | `IdempotencyPlugin` |
| WebSocket reconnect flag tangles | Backoff-with-jitter delay factory; `from_callback` actor logic |
| Chatbot slot filling | Recipe |
| Multi-step wizards / server-side session state | Flask/Django **session store adapter** |
| IoT device state, escalation ladders | Covered by timers + idempotency + persistence |

The distinct plugin count is small because the same primitives recur:
**persistence, concurrency, idempotency, audit, live inspector, typed
context/events, testing.**

---

## 7. XState parity table

| JS | Python proposal | Value / effort |
|:--|:--|:--|
| `@xstate/inspect` + Stately Inspector (WS protocol: `@xstate.actor/event/snapshot`) | `InspectorPlugin` speaking the same protocol over a local WS; `xsm inspect --live`; reuse Stately's UI | **High** / M-H |
| `@xstate/graph` (`getShortestPaths`, `getSimplePaths`) | `shortest_paths()`/`simple_paths()`; pytest auto-parametrised reachability tests — **shipped** (#269: `graph.py`, `xsm paths`, the `[testing]` `xsm_path` fixture) | **High** / M |
| `@xstate/test` | Hypothesis `RuleBasedStateMachine` generated from the chart (preconditions derived from legal events), per-state assertions — **shipped** (#271: `contrib.testing.model_test`, `events_strategy`; shrinking + replayable `xsm simulate --script`) | **Very high** (exceeds JS) / M-H |
| Stately coverage view | State & transition coverage — **shipped** (#270: `coverage.CoverageCollector`, `pytest --xsm-coverage`, `xsm coverage`) | High / M |
| `getPersistedSnapshot` + versioning | §5 store adapters + `SnapshotMigrator` | High / M |
| `fromPromise/fromCallback/fromObservable` | `from_coroutine`, `from_callback`, `from_async_iterator` actor logic | M-H / M |
| `setup()` typed API | Pydantic typed context/events plugin (§2.6) | High / M-H |
| `@xstate/react` | Django context processor / FastAPI dependency exposing snapshot + `send` | M / L |
| `waitFor`/`toPromise` | already shipped | — |
| Stately Sky | out of scope (SaaS); recipe on our store adapters | — |

---

## 8. Packaging & repo layout (recommendation)

Three tiers, mirroring Sentry (lazy imports, single package), Litestar (extras
for small integrations, separate packages for heavy ones) and OpenTelemetry
(separate distributions for fast-moving targets):

- **Tier 0 — docs/recipes only:** OpenAI/Anthropic tool-loop, APScheduler,
  Streamlit/Gradio wizard, Step Functions comparison, circuit breaker, Stripe.
- **Tier 1 — extras in this repo**, `xstate_statemachine/contrib/<name>/`,
  lazy `try/except ImportError` with a message naming the extra:
  ```toml
  [project.optional-dependencies]
  django = ["django>=4.2"]
  drf = ["xstate-statemachine[django]", "djangorestframework>=3.14"]
  fastapi = ["fastapi>=0.100", "pydantic>=2"]
  starlette = ["starlette>=0.27"]
  flask = ["flask>=2.3"]
  sqlalchemy = ["sqlalchemy>=2.0"]
  celery = ["celery>=5.3"]
  redis = ["redis>=5"]
  pydantic = ["pydantic>=2"]
  observability = ["opentelemetry-api>=1.20", "prometheus-client>=0.17"]
  testing = ["pytest>=8", "hypothesis>=6"]
  web = ["xstate-statemachine[fastapi,django,drf,flask,sqlalchemy,pydantic]"]
  eda = ["xstate-statemachine[celery,redis,observability]"]
  all = [...]
  ```
  Core `import xstate_statemachine` never imports `contrib`. Each contrib
  module type-checks with its dependency absent (`TYPE_CHECKING` guards).
  CI: core-only job stays as is; one job per extra (or a matrix of
  `pip install .[x]` + `pytest tests/contrib/x`). Compatibility table in docs.
- **Tier 2 — separate distributions** (`xstate-statemachine-langgraph`,
  `-home-assistant`, broker adapters if they churn): own release cadence.
- **Entry-point group** `xstate_statemachine.plugins` so third parties register
  `PluginBase` subclasses; discovered via `importlib.metadata.entry_points`.

---

## 9. Adoption playbook

- Listings: djangopackages.org (public repo + PyPI; request "State Machine"
  grid), awesome-django / awesome-fastapi / awesome-python PRs, awesome-LLM /
  awesome-langchain lists (with the agent recipe), Stately community
  ("XState for Python"), PyPI classifiers (`Framework :: Django`, `Framework
  :: FastAPI`, `Framework :: AsyncIO`) and keywords (`statechart`, `xstate`,
  `fsm`, `llm-agents`, `workflow-engine`, `saga`).
- Content: comparison pages ("vs transitions", "vs python-statemachine", "vs
  django-fsm-2", "vs LangGraph", "vs Burr", "vs Step Functions"); a Show
  HN / r/Python post timed to the **agents** launch, not the core.
- Become a documented dependency of bigger projects (pydantic grew on FastAPI).

---

## 10. Recommended phasing (for the PRD)

| Phase | Scope | Why first |
|:--|:--|:--|
| **A. Foundation** | Store adapter protocol + SQLite/file + Redis backends; locking (pessimistic/optimistic/Redis); `IdempotencyPlugin`; `AuditPlugin`/`TransitionLogPlugin`; version-stamped snapshots + `SnapshotMigrator`; durable-timer deadline persistence; Pydantic typed context/events; `RetryPolicy`/backoff helper | Everything else stands on it; mostly zero-dep |
| **B. Testing + observability** | `[testing]`: fixtures, `shortest/simple_paths`, coverage report, Hypothesis model-based testing, replay helper, `FakeBrokerAdapter`; `[observability]`: OTel, Prometheus, structlog, Sentry plugins | Cheapest (pure hooks), highest trust signal |
| **C. FastAPI/Starlette** | Registry + `Depends`, `StatechartRouter` with OpenAPI + discriminated-union bodies, Receipt→HTTP, WS/SSE streaming, `InspectorPlugin` | Blue ocean, async-native fit |
| **D. Django + DRF + SQLAlchemy** | Field/mixin/admin/signals/permission guard/management commands; DRF viewset mixin; SA `TypeDecorator` + `version_id_col` + outbox | Largest footprint; hierarchy is the differentiator |
| **E. Agents** | Recipes, LangGraph-node adapter, pydantic-ai/instructor recipe, comparison pages, list submissions, launch post | Growth engine; core already has ~90% |
| **F. EDA adapters** | Celery service/Beat timers; Kafka/RabbitMQ/Redis Streams/SQS via CloudEvents envelopes; Outbox/DLQ plugins; Flask/Quart; Channels; Litestar | Unique `invoke`→Celery bridge; broker adapters after demand signal |

Each phase ships its own docs page, compatibility table, changelog entry and
CI job; the core's zero-dependency promise is a CI-enforced invariant (the
existing `_zero_dep_guard` pattern in `tests/tests_cli` can be generalised).

---

## Appendix — key sources

django-fsm-2 · viewflow/django-fsm#125 · pytransitions/transitions#435 ·
viewflow/viewflow · rsinger86/django-lifecycle · fgmacedo/python-statemachine ·
apache/burr · statelyai/agent · fastapi/fastapi discussions #11742 ·
svcs.hynek.me · pypi fastapi-state · flask extensiondev docs · sqlalchemy event
& TypeDecorator docs · celery signals/canvas docs, celery#5000/#5354/#6197/#8211
· temporalio/sdk-python#1591/#1184/#449 · mosquito/aio-pika#563 ·
nats-io/nats.py#751 · Bogdanp/dramatiq#224 · faust-streaming/faust#670 ·
cloudevents/spec correlation extension · opentelemetry messaging semconv ·
channels consumers docs · litestar-org/litestar · pydantic discriminated unions
· hypothesis stateful testing · stately.ai/docs (graph, inspect, persistence) ·
statelyai/xstate#5077 · pepy.tech / pypistats download figures.
