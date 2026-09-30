# Integration Plugins & Event-Driven Architecture — Master Build Plan

> Companion to [`PLUGINS_AND_EDA_RESEARCH.md`](./PLUGINS_AND_EDA_RESEARCH.md).
> Every task below is mirrored as a GitHub issue (label `epic/plugins`,
> milestone per phase). Epic: [#257](https://github.com/basiltt/xstate-statemachine/issues/257). The issue is the source of truth for acceptance
> criteria; this file is the map.
>
> **Reviewed 2026-09-27** by three independent audits (engine feasibility, product
> completeness, security/operations). Outcome: 8 issues added, 34 amended in place
> (each carries a *Review amendments* block that supersedes conflicting text), and
> the phases reordered to **A → B → E (agents) → C → D → F → G**. A programme-wide
> security & operability baseline ([#303](https://github.com/basiltt/xstate-statemachine/issues/303)) gates every release candidate.
>
> **Release policy for this programme:** nothing is tagged or published to
> PyPI without the maintainer's explicit confirmation. Each phase ends in a
> release-candidate PR that is merged, then *waits*.

---

## 0. Programme-wide invariants (apply to every task)

| Invariant | How it is enforced |
|:--|:--|
| **Core stays zero-dependency.** `import xstate_statemachine` must succeed with every third-party import blocked. Nothing under `xstate_statemachine/` outside `contrib/` may import a third-party module, even lazily. | `tests/test_zero_dependency.py` (generalised from `tests/tests_cli/test_ui_toolkit.py::_zero_dep_guard`): a `MetaPathFinder` that raises on any non-stdlib import while importing every core module. CI job `core-zero-dep`. |
| **Every integration is an extra.** `pip install xstate-statemachine[<name>]`; `contrib/<name>/__init__.py` lazy-imports its target and raises `MissingExtraError("pip install xstate-statemachine[<name>]")` naming the extra. | `tests/contrib/test_extras_matrix.py` imports every `contrib.*` with its dependency blocked and asserts the error text; CI matrix job per extra installs *only* that extra. |
| **Public surface is typed.** `py.typed` ships; every `contrib` module type-checks with its dependency absent (`TYPE_CHECKING` guards / `Any` fallbacks). | `mypy` in the `lint` job with the extra absent AND with it installed. |
| **Coverage ≥ 90%** repository-wide (ratchet, never lowered). New contrib code targets ≥ 90% on its own. | `pytest --cov` fail-under; per-extra jobs report their own %. |
| **Docs are executable.** Every Python block in a new guide page runs in CI (existing `tests/test_docs_executable.py` harness). Contrib pages that need a framework are skipped-with-reason when the extra is absent. | Extend the harness with an `# doc-requires: fastapi` marker. |
| **Honest guarantees.** Every persistence/EDA page carries the "What this does / does not guarantee" box (at-least-once + idempotent inbox; resume-from-last-snapshot; loud version mismatch; no exactly-once; no automatic mid-flight migration). | Docs review checklist item; `tests/test_docs_site.py` asserts the box exists on the listed pages. |
| **Changelog + docs + examples** updated in the same PR as the code. | PR template checklist. |
| **Code standard.** Black 79, flake8 (CI flags), mypy clean, emoji-prefixed architecture comments (`🏛️ / 📝 / ⚠️`) explaining *why*, Google docstrings. | `lint` job. |
| **Verification script.** Each issue has a committed `scripts/verify/<issue>.py` a reviewer can run on any OS (the shell snippets in issue bodies are illustrative). | X0.16 |
| **Security & operability baseline** ([#303](https://github.com/basiltt/xstate-statemachine/issues/303)): closed-by-default HTTP surfaces, principal-scoped idempotency, crash-consistency spec, JSON-only deserialisation with limits, redaction + `forget(key)`, telemetry hygiene, web hardening (CSRF/Origin/RFC 9457), poison/backpressure, entry-generation-tagged timers, schema lifecycle, graceful shutdown, health/metrics, agent tool safety, supply chain, platform rules (Python floor **3.9**), test hygiene (`pytest-socket`, containers opt-in). | Each RC issue ticks "X0 items for this phase verified". |
| **Performance budgets** ([#307](https://github.com/basiltt/xstate-statemachine/issues/307)): import time, `persisted()` round-trip, plugin overhead, snapshot v4 cost; nightly job; import-time guard in the default job. | `benchmarks/budgets.json`. |

### Repository layout added by this programme

```
src/xstate_statemachine/
├── persistence/          # zero-dep: store protocol, locks, idempotency, versioning, timers
├── contrib/              # each subpackage guarded by MissingExtraError
│   ├── _compat.py        # require_extra("fastapi", "fastapi") helper
│   ├── pydantic/  observability/  testing/
│   ├── starlette/ fastapi/  litestar/  flask/
│   ├── django/  drf/  channels/
│   ├── sqlalchemy/  redis/  celery/
│   ├── brokers/          # kafka rabbitmq redis_streams nats sqs + CloudEvents envelope
│   └── agents/           # langgraph adapter, recipes
tests/contrib/<name>/     # one folder per extra, run only when the extra is installed
docs/_guide/integrations/ # one page per extra + "choosing a store" + "EDA guarantees"
examples/integrations/    # runnable apps per framework
```

### pyproject extras (target end state)

Placeholders are **empty lists** until the owning issue lands (a populated `[all]` would pull every framework for nothing). Every extra gets a lower bound; CI runs an *oldest* and a *newest* resolution per extra (X0.14).

```toml
[project.optional-dependencies]
pydantic      = ["pydantic>=2.5"]
observability = ["opentelemetry-api>=1.20", "prometheus-client>=0.17"]
testing       = ["pytest>=8", "hypothesis>=6.100"]
redis         = ["redis>=5"]
sqlalchemy    = ["sqlalchemy>=2.0"]
starlette     = ["starlette>=0.27"]
fastapi       = ["fastapi>=0.100", "xstate-statemachine[pydantic,starlette]"]
litestar      = ["litestar>=2.0"]
flask         = ["flask>=2.3"]
django        = ["django>=4.2"]
drf           = ["djangorestframework>=3.14", "xstate-statemachine[django]"]
channels      = ["channels>=4", "xstate-statemachine[django]"]
celery        = ["celery>=5.3"]
kafka         = ["aiokafka>=0.10"]
rabbitmq      = ["aio-pika>=9"]
nats          = ["nats-py>=2"]
sqs           = ["boto3>=1.28"]
cloudevents   = ["cloudevents>=1.10"]
agents        = ["xstate-statemachine[pydantic]"]
web           = ["xstate-statemachine[fastapi,django,drf,flask,sqlalchemy]"]
eda           = ["xstate-statemachine[celery,redis,kafka,rabbitmq,cloudevents,observability]"]
all           = ["xstate-statemachine[web,eda,testing,litestar,channels,nats,sqs,agents]"]
```

---

## Phase A — Foundation (release target 0.11.0)

The keystone. Almost entirely zero-dependency; lives in `xstate_statemachine.persistence`.

| # | Task | Issue |
|:--|:--|:--|
| X0 | **Security & operability baseline** — programme-wide, gates every RC | [#303](https://github.com/basiltt/xstate-statemachine/issues/303) |
| X2 | **Performance budgets** — defined now, rows added per phase | [#307](https://github.com/basiltt/xstate-statemachine/issues/307) |
| A0 | **Core hooks**: `on_before_send` (fail-open interceptor) + `on_event_processed` (final `Receipt`), `Receipt.duplicate`, `stub_logic()` — both engines | [#304](https://github.com/basiltt/xstate-statemachine/issues/304) |
| A0b | **Core prerequisites**: snapshot v4 (+`machine_version`, `deadlines`, one `upcast`), `wall_now()`, global plugin registry, `context_validator` seam, `__xstate_event__` adapter, `SyncInterpreter.send_threadsafe`, `MachineNode.version`, `receipts` codec | [#305](https://github.com/basiltt/xstate-statemachine/issues/305) |
| A1 | Programme scaffolding: `contrib/` + `persistence/` packages, `MissingExtraError` + `require_extra()`, extras in `pyproject`, zero-dependency guard test, CI extras matrix, docs "Integrations" section + sidebar, PR template checklist | [#258](https://github.com/basiltt/xstate-statemachine/issues/258) |
| A2 | `StateStore` protocol + `MemoryStore`, `FileStore`, `SQLiteStore` (stdlib `sqlite3`) with `load/save/lock/delete/list`; optimistic `expected_version` | [#259](https://github.com/basiltt/xstate-statemachine/issues/259) |
| A3 | *(after A8 — needs `RetryPolicy`)* Concurrency layer: `LockStrategy` protocol — `OptimisticLock` (version column + retry policy), `PessimisticLock` (store-provided), `NoLock`; `ConflictError`; `Persisted` context manager implementing create → act → persist → discard | [#260](https://github.com/basiltt/xstate-statemachine/issues/260) |
| A4 | `IdempotencyPlugin` + `InboxStore` protocol (`seen`/`mark`, TTL) — dedup before `send()`, `Idempotency-Key` semantics, returns cached `Receipt` | [#261](https://github.com/basiltt/xstate-statemachine/issues/261) |
| A5 | `TransitionLogPlugin` (append-only event/transition log, `replay()`), `AuditPlugin` (from/to/event/actor/reason/ts with actor extracted from event payload) | [#262](https://github.com/basiltt/xstate-statemachine/issues/262) |
| A6 | Snapshot versioning **on top of the existing `structure_hash`/`SnapshotDriftError`**: add `machine_version` label; `SnapshotMigrator.register(from, to, fn)`; `MachineVersionMismatchError` (is-a `SnapshotDriftError`); manual upcast recipe | [#263](https://github.com/basiltt/xstate-statemachine/issues/263) |
| A7 | Durable timers: persist `after` deadlines in the snapshot; `from_snapshot(restart_timers="resume")` re-arms remaining time or fires matured timers; `DueTimerScanner` for stores (list machines with deadlines ≤ now) | [#264](https://github.com/basiltt/xstate-statemachine/issues/264) |
| A8 | `RetryPolicy` (exponential backoff + jitter as an `after` delay function), `dead_letter` helper transition pattern, `CircuitBreaker` recipe chart + `@circuit_breaker` decorator (zero-dep, in `xstate_statemachine.patterns`) | [#265](https://github.com/basiltt/xstate-statemachine/issues/265) |
| A12 | `[redis]`: `RedisStore` / `RedisInbox` / `RedisLog` with fencing locks — **moved forward from Phase F** (multi-worker story needs it before Phase C) | [#306](https://github.com/basiltt/xstate-statemachine/issues/306) |
| A9 | `[pydantic]`: `TypedContext` (BaseModel validated on every assign; `ContextValidationError`), discriminated-union `EventModel` bridge → `event_schemas=`, `validate_machine_json()`, `machine_json_schema()` | [#266](https://github.com/basiltt/xstate-statemachine/issues/266) |
| A10 | Actor logic helpers: `from_coroutine`, `from_callback`, `from_async_iterator` (XState `fromPromise/fromCallback/fromObservable` parity) | [#267](https://github.com/basiltt/xstate-statemachine/issues/267) |
| A11 | Phase A docs: "Persistence & Durability" guide, "Choosing a store", "Guarantees" box, changelog `[0.11.0]`, release-candidate PR (**no publish**) | [#297](https://github.com/basiltt/xstate-statemachine/issues/297) |

## Phase B — Testing & Observability (0.12.0)

| # | Task | Issue |
|:--|:--|:--|
| B1 | `[testing]` pytest plugin: fixtures `machine`, `interp`, `clock`, `store`; `xstate_machine` marker loading JSON; `assert_snapshot_matches` | [#268](https://github.com/basiltt/xstate-statemachine/issues/268) |
| B2 | Graph algorithms: `shortest_paths(machine)`, `simple_paths(machine)`, `reachable_states()`; `pytest_generate_tests` hook auto-parametrising reachability tests; `--xsm-full-paths` | [#269](https://github.com/basiltt/xstate-statemachine/issues/269) |
| B3 | State/transition coverage: `on_transition` collector, session report "N/M states visited, unreached: […]", `--xsm-fail-under-state-coverage=N`; `xsm coverage` CLI reads the JSON report | [#270](https://github.com/basiltt/xstate-statemachine/issues/270) |
| B4 | Hypothesis model-based testing: `machine_state_machine(machine, assertions)` generating a `RuleBasedStateMachine` with preconditions derived from legal events; shrinking to minimal failing sequences; `events_strategy(machine)` | [#271](https://github.com/basiltt/xstate-statemachine/issues/271) |
| B5 | `FakeBrokerAdapter` + `replay()` test helpers; given/when/then recipe (pytest-bdd) | [#272](https://github.com/basiltt/xstate-statemachine/issues/272) |
| B6 | `[observability]`: `OpenTelemetryPlugin` (spans per transition/service, `statechart.*` attributes, messaging semconv on broker spans), `PrometheusPlugin` (metric set from research Â§3.4), `StructlogPlugin`/`LoguruPlugin` context binding, `SentryPlugin` breadcrumbs | [#273](https://github.com/basiltt/xstate-statemachine/issues/273) |
| B7 | Live inspector: `InspectorPlugin` speaking the Stately Inspector WebSocket protocol (`@xstate.actor/@xstate.event/@xstate.snapshot`); `xsm inspect --live` serving it; verified against the Stately Inspector UI | [#274](https://github.com/basiltt/xstate-statemachine/issues/274) |
| B9 | Recipes pack: Stripe (signature-verified), APScheduler, RQ/arq/Dramatiq, Streamlit/Gradio wizard, slot filling, feature flags, WebSocket reconnect, vs Step Functions | [#308](https://github.com/basiltt/xstate-statemachine/issues/308) |
| B8 | Phase B docs + changelog `[0.12.0]`, RC PR (**no publish**) | [#298](https://github.com/basiltt/xstate-statemachine/issues/298) |




## Phase E — LLM Agents (0.13.0) — *moved forward: the growth story depends only on Phase A + B6*

| # | Task | Issue |
|:--|:--|:--|
| E1 | `[agents]` recipes: tool-use loop chart (`awaiting_model → awaiting_tool → awaiting_human → done/error`), budget/safety guards, `after` tool timeouts, human-in-the-loop as durable waiting state, snapshot/replay; provider-agnostic `invoke` wrappers for OpenAI/Anthropic SDK calls | [#287](https://github.com/basiltt/xstate-statemachine/issues/287) |
| E2 | `contrib.agents.langgraph`: statechart as a LangGraph node; LangGraph subgraph as an `invoke` service | [#288](https://github.com/basiltt/xstate-statemachine/issues/288) |
| E3 | `contrib.agents.pydantic_ai` + `instructor` recipe: per-state output models validated on transition | [#289](https://github.com/basiltt/xstate-statemachine/issues/289) |
| E4 | Multi-agent **as recipes** + `spawn_agent` (subset tool allow-lists, per-agent budgets) + `BudgetPlugin` + trace rollup; no framework-like runtime | [#290](https://github.com/basiltt/xstate-statemachine/issues/290) |
| E5 | Comparison pages "vs LangGraph", "vs Burr", "vs statelyai/agent"; launch post draft; awesome-LLM list submissions drafted | [#291](https://github.com/basiltt/xstate-statemachine/issues/291) |
| E6 | Phase E docs + changelog `[0.13.0]`, RC PR (**no publish**) | [#301](https://github.com/basiltt/xstate-statemachine/issues/301) |

## Phase C — FastAPI / Starlette / Litestar (0.14.0)

| # | Task | Issue |
|:--|:--|:--|
| C1 | `[starlette]` core: `StatechartRegistry` (lifespan-managed, store-backed, create-act-persist-discard), `Receipt → HTTP status` mapping (200/202/409/422), `Idempotency-Key` header → `IdempotencyPlugin`, SSE `transition_stream()`, WebSocket endpoint | [#275](https://github.com/basiltt/xstate-statemachine/issues/275) |
| C2 | `[fastapi]`: `Depends(get_interpreter(...))`, `StatechartRouter(machine, prefix)` → `GET /{id}`, `POST /{id}/send`, `POST /{id}/events/{EVENT}`, `GET /{id}/events`, `GET /{id}/diagram.mmd`; Pydantic discriminated-union bodies; OpenAPI verified | [#276](https://github.com/basiltt/xstate-statemachine/issues/276) |
| C3 | `BackgroundTasks` bridge for actions; multi-worker guide (uvicorn/gunicorn) with Redis/SQLite store; example app `examples/integrations/fastapi_orders` | [#277](https://github.com/basiltt/xstate-statemachine/issues/277) |
| C4 | `[litestar]` `XStatePlugin` on the Starlette-family core | [#278](https://github.com/basiltt/xstate-statemachine/issues/278) |
| C5 | `xsm gt --template fastapi-router` codegen companion (router module for a chart) | [#279](https://github.com/basiltt/xstate-statemachine/issues/279) |
| C7 | Getting-started journey + adoption kit (classifiers, Stately export page, `xsm-check` GitHub Action, pre-commit hook, VS Code schema, `xsm new`) | [#309](https://github.com/basiltt/xstate-statemachine/issues/309) |
| C6 | Phase C docs + changelog `[0.14.0]`, RC PR (**no publish**) | [#299](https://github.com/basiltt/xstate-statemachine/issues/299) |

## Phase D — Django / DRF / SQLAlchemy / Flask (0.15.0)

| # | Task | Issue |
|:--|:--|:--|
| D1 | `[django]` `StatechartField` (JSONField snapshot + denormalised `state_ids`/`state` columns, lookups `state__in`), `StatechartModelMixin` (`send/can/available_events/machine`), `transaction.atomic()+select_for_update()` default, optimistic alternative, migration helpers | [#280](https://github.com/basiltt/xstate-statemachine/issues/280) |
| D2 | `pre_transition`/`post_transition` signals; `TransitionLog` model + `DjangoAuditPlugin` in-transaction; `PermissionGuard`; `DjangoStore` implementing `StateStore` | [#281](https://github.com/basiltt/xstate-statemachine/issues/281) |
| D3 | `StatechartAdminMixin`: guard-computed action buttons, confirm + reason, history inline; management commands `xsm_inspect/xsm_diagram/xsm_docs/xsm_simulate` | [#282](https://github.com/basiltt/xstate-statemachine/issues/282) |
| D4 | `[drf]` `StatechartViewSetMixin` (`@action` per event), `StatechartSerializerField`, Receipt→status, OpenAPI via drf-spectacular; `[channels]` `StatechartConsumer` | [#283](https://github.com/basiltt/xstate-statemachine/issues/283) |
| D5 | `[sqlalchemy]` `StatechartType(TypeDecorator)`, `StatechartMixin`, `version_id_col` optimistic locking, `before_update` audit listener, `SQLAlchemyStore` (sync + `AsyncSession`), `OutboxMixin` + drain helper | [#284](https://github.com/basiltt/xstate-statemachine/issues/284) |
| D6 | `[flask]` `XState(app)` extension (`init_app`), `g.interpreter`, `create_statechart_blueprint`, `flask xsm` CLI group; Quart note | [#285](https://github.com/basiltt/xstate-statemachine/issues/285) |
| D9 | `[django]` `xsm_migrate_fsm`: mechanical migration from django-fsm-2; `from_state_ids()` in core | [#310](https://github.com/basiltt/xstate-statemachine/issues/310) |
| D7 | Example apps: `examples/integrations/django_approvals`, `sqlalchemy_orders`, `flask_wizard`; comparison pages "vs django-fsm-2", "vs transitions", "vs python-statemachine" | [#286](https://github.com/basiltt/xstate-statemachine/issues/286) |
| D8 | Phase D docs + changelog `[0.15.0]`, RC PR (**no publish**); djangopackages.org + awesome-list submissions drafted | [#300](https://github.com/basiltt/xstate-statemachine/issues/300) |

## Phase F — EDA adapters (0.16.0)

| # | Task | Issue |
|:--|:--|:--|
| F1 | `[celery]`: `celery_service(task)` invoke bridge (`onDone/onError` from `task_success/failure` or result polling), `@statechart_task` load-send-persist worker helper, Celery Beat `DurableTimerScheduler` | [#292](https://github.com/basiltt/xstate-statemachine/issues/292) |
| F2 | `[cloudevents]` `Envelope` (CloudEvents + `correlationid/causationid/machineid`), `BrokerAdapter` protocol, `OutboxPlugin`, `DeadLetterPlugin`, `FakeBrokerAdapter` parity | [#293](https://github.com/basiltt/xstate-statemachine/issues/293) |
| F3 | Broker adapters: `[redis]` streams, `[kafka]` aiokafka, `[rabbitmq]` aio-pika, `[nats]`, `[sqs]`; partition key = machine id; consume → `send`, publish tagged events; integration tests via testcontainers (opt-in CI job) | [#294](https://github.com/basiltt/xstate-statemachine/issues/294) |
| F4 | `SagaBuilder` sugar + saga guide; choreography guide; AsyncAPI generation from a chart's tagged events | [#295](https://github.com/basiltt/xstate-statemachine/issues/295) |
| F5 | Phase F docs + changelog `[0.16.0]`, RC PR (**no publish**) | [#302](https://github.com/basiltt/xstate-statemachine/issues/302) |

## Phase G — Hardening & 1.0 (no date)

| # | Task | Issue |
|:--|:--|:--|
| G1 | Entry-point plugin discovery (`xstate_statemachine.plugins` group), compatibility table per framework version, deprecation policy, `[all]` smoke test in a clean venv, 1.0 checklist | [#296](https://github.com/basiltt/xstate-statemachine/issues/296) |

---

## Cross-cutting verification (run at every phase gate)

```bash
# 1. core is still zero-dependency
python -m pytest tests/test_zero_dependency.py -q
# 2. every extra imports cleanly WITH and errors cleanly WITHOUT its dependency
python -m pytest tests/contrib/test_extras_matrix.py -q
# 3. full suite + coverage gate
python -m pytest --cov -q
# 4. lint / type (CI flags)
black --check src tests --line-length=79
python -m flake8 src tests --max-complexity=35 --select=B,C,E,F,W,T4,B9 --ignore=E203,E266,E501,W503,F403,F401,E402
python -m mypy
# 5. wheel builds and installs with NO deps in a clean venv
python -m build --wheel && python -m venv /tmp/v && /tmp/v/bin/pip install dist/*.whl && /tmp/v/bin/python -c "import xstate_statemachine, sys; assert not [m for m in sys.modules if m.split('.')[0] in {'pydantic','fastapi','django','sqlalchemy','celery'}]"
# 6. docs are executable and links resolve
python -m pytest tests/test_docs_executable.py tests/test_docs_site.py tests/test_readme.py -q
```

