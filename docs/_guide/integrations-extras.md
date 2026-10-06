---
title: "Integration extras"
description: "Every optional pip extra — pydantic, redis, starlette, fastapi, litestar, flask, sqlalchemy, django, drf, channels, agents, observability, cloudevents, celery, the brokers (redis streams, kafka, rabbitmq, nats, sqs) and testing — with its status, issue and the point at which a missing dependency is reported."
---

# Integration extras

The core library has **zero runtime dependencies**, and that never changes. Everything that talks to a framework — Django models, FastAPI routers, SQLAlchemy types, Celery tasks, Kafka consumers, OpenTelemetry spans — lives in optional packages under `xstate_statemachine.contrib`, installed one **pip extra** at a time:

```bash
pip install "xstate-statemachine[fastapi]"
pip install "xstate-statemachine[django,sqlalchemy]"
pip install "xstate-statemachine[all]"
```

`import xstate_statemachine` still imports nothing third-party. Importing an integration without its extra fails **loudly and helpfully**:

```python
from xstate_statemachine import MissingExtraError
from xstate_statemachine.contrib._compat import require_extra

try:
    require_extra("fastapi", "a_module_that_is_not_installed")
except MissingExtraError as exc:
    print(exc)
    # `a_module_that_is_not_installed` is not installed. Install the extra: pip install "xstate-statemachine[fastapi]"
    assert isinstance(exc, ImportError)  # existing `except ImportError` fallbacks keep working
```

> **When the error is raised.** Importing an integration subpackage checks its pinned dependencies **at import time** (`import xstate_statemachine.contrib.fastapi`). Three things are checked later, **on first use**, because they are optional soft dependencies that no extra pins: `StructlogPlugin()` / `LoguruPlugin()` (`structlog` / `loguru`), `SentryPlugin()` (`sentry-sdk`), `LangChainCallbackPlugin()` (`langchain-core` — its module still needs `langgraph` at import, from `[agents]`), and `[testing]`'s Hypothesis helpers (`model_test`, `events_strategy`, `payload_strategy`). `xstate_statemachine.contrib.brokers` itself imports with no extra; each adapter module (`brokers.kafka`, …) checks its own. The Quart shim (`contrib.quart`) needs `pip install quart` on top of `[flask]` — the error says so.

## The extras

| Extra | Gives you | Status |
|:--|:--|:--|
| `pydantic` | Typed context validated on every `assign`, typed events as discriminated unions, machine-JSON validation, JSON Schema export | **shipped** — [guide](../integration-pydantic/) · [#266](https://github.com/basiltt/xstate-statemachine/issues/266) |
| `observability` | `OpenTelemetryPlugin` spans, `PrometheusPlugin` metrics, `StructlogPlugin` / `LoguruPlugin` context binding, `SentryPlugin` breadcrumbs, `instrument_all()` — all from the plugin hooks, with an X0.6 label allow-list | **shipped** — [guide](../integration-observability/) · [#273](https://github.com/basiltt/xstate-statemachine/issues/273) |
| `testing` | pytest plugin: `xstate_machine` marker → `xsm_interp` / `xsm_ainterp` / `xsm_clock` / `xsm_ran` / `xsm_store` fixtures, `xstate_guards_false`, `xsm_send_all`, file-backed `xsm_snapshot` assertions; path generation, coverage and Hypothesis model-based testing follow in B2–B4 | **shipped** (plugin) — [guide](../integration-testing/) · [#268](https://github.com/basiltt/xstate-statemachine/issues/268) |
| `redis` | Shared snapshot store, inbox and log for multi-worker deployments | **shipped** — [guide](../integration-redis/) · [#306](https://github.com/basiltt/xstate-statemachine/issues/306) |
| `sqlalchemy` | `StatechartType`, mixin with optimistic locking, stores for sync and `AsyncSession`, inbox + log, transactional outbox (`SQLAlchemyOutboxStore`) | **shipped** — [guide](../integration-sqlalchemy/) · [#284](https://github.com/basiltt/xstate-statemachine/issues/284) |
| `starlette` | Store-backed registry, `Receipt → HTTP` mapping, SSE / WebSocket transition streaming | **shipped** — [guide](../integration-starlette/) · [#275](https://github.com/basiltt/xstate-statemachine/issues/275) |
| `fastapi` | `Depends(get_interpreter)`, `StatechartRouter` with OpenAPI generated from the chart | **shipped** — [guide](../integration-fastapi/) · [#276](https://github.com/basiltt/xstate-statemachine/issues/276) |
| `litestar` | `XStatePlugin`, `Provide()` dependency, statechart controller | **shipped** — [guide](../integration-litestar/) · [#278](https://github.com/basiltt/xstate-statemachine/issues/278) |
| `flask` | `XState` extension (`init_app`), blueprint per machine, session-keyed wizards, `flask xsm` CLI, Quart shim | **shipped** — [guide](../integration-flask/) · [#285](https://github.com/basiltt/xstate-statemachine/issues/285) |
| `django` | `StatechartField` (queryable sibling columns, `in_state()`), model mixin with `transaction.atomic()` + `select_for_update` or optimistic `send_with_retry`, signals, `TransitionLog` audit in the same transaction, `PermissionGuard`, admin transition buttons, `xsm_*` management commands, `DjangoStore`, `xsm_deadlines`, `xsm_migrate_fsm` from django-fsm-2 | **shipped** — [guide](../integration-django/) · [#280](https://github.com/basiltt/xstate-statemachine/issues/280)–[#282](https://github.com/basiltt/xstate-statemachine/issues/282) · [#310](https://github.com/basiltt/xstate-statemachine/issues/310) |
| `drf` | `StatechartViewSetMixin` with an `@action` per event, receipt → status, `Idempotency-Key`, drf-spectacular schema, `StatechartSerializerField` | **shipped** — [guide](../integration-drf/) · [#283](https://github.com/basiltt/xstate-statemachine/issues/283) |
| `channels` | `StatechartConsumer`: snapshot on connect, transition broadcast to every connection on the row, auth on connect (close 1008) | **shipped** — [guide](../integration-drf/#statechartconsumer-channels) · [#283](https://github.com/basiltt/xstate-statemachine/issues/283) |
| `celery` | A Celery task as an `invoke` service; `@statechart_task` worker act-loop; Celery Beat as the durable `after` scheduler | ✅ shipped — [Celery](../integration-celery/) ([#292](https://github.com/basiltt/xstate-statemachine/issues/292)) |
| `cloudevents` | CloudEvents SDK objects and HTTP binary / structured interop for the core `Envelope` (the envelope, dispatcher, outbox, dead letters, sagas and AsyncAPI are core and need no extra) | **shipped** — [guide](../integration-eda/) · [#293](https://github.com/basiltt/xstate-statemachine/issues/293) |
| `kafka` · `rabbitmq` · `nats` · `sqs` | Broker adapters (plus Redis Streams in `[redis]`): consume envelopes into machines, publish tagged transitions | ✅ shipped — [Brokers](../integration-brokers/) ([#294](https://github.com/basiltt/xstate-statemachine/issues/294)) |
| `agents` | `TOOL_LOOP` chart, tool registry with per-state allow-lists enforced in `run_tool`, budgets, timeouts, durable human-in-the-loop, structured output, OpenAI/Anthropic adapters (soft imports), `spawn_agent` + `BudgetPlugin` multi-agent recipes | **shipped** — [guide](../integration-agents/) · [#287](https://github.com/basiltt/xstate-statemachine/issues/287) · [#290](https://github.com/basiltt/xstate-statemachine/issues/290) |
| `web` · `eda` · `all` | Umbrella extras: `web` = fastapi + django + drf + flask + sqlalchemy; `eda` = celery + redis + kafka + rabbitmq + cloudevents + observability; `all` = every extra above | — |

The framework versions each shipped extra is tested against (oldest and newest, one CI cell each) are on the [Compatibility](../compatibility/) page. All `contrib` APIs are **provisional** under the [Deprecation Policy](../deprecation-policy/).

## What every integration promises — and does not

Each integration page carries two boxes. They are not boilerplate; they are the contract.

> **Guarantees.** *What this does:* the specific, testable behaviour (for example: "a transition and its audit row are written in one transaction"). *What this does not do:* the honest limits (for example: "at-least-once — pair with the idempotency inbox; never exactly-once").
>
> **Threat model.** Who can call this surface, what it exposes (state only, never raw context, unless you opt in), and what you must configure (an `authorize=` callable is required on every generated HTTP route).

The rules every integration follows are collected in the programme's [security & operability baseline](https://github.com/basiltt/xstate-statemachine/issues/303).

## Design rules (for contributors)

- A subpackage's `__init__.py` starts with `require_extra("<extra>", "<module>")`. Core never imports `contrib`; CI proves it with an import-blocking guard.
- The single table of extras is `xstate_statemachine.contrib._registry.EXTRAS`; `pyproject.toml`, the CI matrix and the tests are checked against it.
- Every contrib module type-checks with its dependency absent (`TYPE_CHECKING` guards) and installed.
- Each extra has its own CI cell that installs **only** that extra, so an integration can never pass because another one happened to be present.
