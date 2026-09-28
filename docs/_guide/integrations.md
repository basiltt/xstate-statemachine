---
title: "Integrations"
description: "Optional, zero-dependency-preserving integrations for Django, FastAPI, Flask, SQLAlchemy, Celery, brokers, observability, testing and LLM agents."
---

# Integrations

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

> **Status.** The integration programme is being built in phases (tracking issue [#257](https://github.com/basiltt/xstate-statemachine/issues/257)). Extras below marked *planned* already resolve in `pip install` so you can pin them today; the code arrives with the linked issue and its page appears here.

## The extras

| Extra | Gives you | Status |
|:--|:--|:--|
| `pydantic` | Typed context validated on every `assign`, typed events as discriminated unions, machine-JSON validation, JSON Schema export | **shipped** — [guide](../integration-pydantic/) · [#266](https://github.com/basiltt/xstate-statemachine/issues/266) |
| `observability` | OpenTelemetry spans, Prometheus metrics, structlog/loguru context binding, Sentry breadcrumbs — all from the plugin hooks | planned — [#273](https://github.com/basiltt/xstate-statemachine/issues/273) |
| `testing` | pytest fixtures, path generation, state/transition **coverage**, Hypothesis model-based testing generated from the chart, a fake broker | planned — [#268](https://github.com/basiltt/xstate-statemachine/issues/268) |
| `redis` | Shared snapshot store, inbox and log for multi-worker deployments | **shipped** — [guide](../integration-redis/) · [#306](https://github.com/basiltt/xstate-statemachine/issues/306) |
| `sqlalchemy` | `StatechartType`, mixin with optimistic locking, transactional outbox, stores for sync and `AsyncSession` | planned — [#284](https://github.com/basiltt/xstate-statemachine/issues/284) |
| `starlette` | Store-backed registry, `Receipt → HTTP` mapping, SSE / WebSocket transition streaming | **shipped** — [guide](../integration-starlette/) · [#275](https://github.com/basiltt/xstate-statemachine/issues/275) |
| `fastapi` | `Depends(get_interpreter)`, `StatechartRouter` with OpenAPI generated from the chart | **shipped** — [guide](../integration-fastapi/) · [#276](https://github.com/basiltt/xstate-statemachine/issues/276) |
| `litestar` | `XStatePlugin`, `Provide()` dependency, statechart controller | **shipped** — [guide](../integration-litestar/) · [#278](https://github.com/basiltt/xstate-statemachine/issues/278) |
| `flask` | `XState` extension (`init_app`), blueprint per machine, session-keyed wizards | planned — [#285](https://github.com/basiltt/xstate-statemachine/issues/285) |
| `django` | `StatechartField`, model mixin with `select_for_update`, signals, permission guards, admin transition buttons, management commands | planned — [#280](https://github.com/basiltt/xstate-statemachine/issues/280) |
| `drf` | ViewSet mixin with an `@action` per event, serializer field | planned — [#283](https://github.com/basiltt/xstate-statemachine/issues/283) |
| `channels` | WebSocket consumer broadcasting transitions | planned — [#283](https://github.com/basiltt/xstate-statemachine/issues/283) |
| `celery` | A Celery task as an `invoke` service; Celery Beat as the durable `after` scheduler | planned — [#292](https://github.com/basiltt/xstate-statemachine/issues/292) |
| `cloudevents` | CloudEvents envelope, outbox and dead-letter plugins, AsyncAPI generation | planned — [#293](https://github.com/basiltt/xstate-statemachine/issues/293) |
| `kafka` · `rabbitmq` · `nats` · `sqs` | Broker adapters: consume envelopes into machines, publish tagged transitions | planned — [#294](https://github.com/basiltt/xstate-statemachine/issues/294) |
| `agents` | Tool-use loop as a statechart, budget/safety guards, human-in-the-loop as a durable state, LangGraph / pydantic-ai interop | planned — [#287](https://github.com/basiltt/xstate-statemachine/issues/287) |
| `web` · `eda` · `all` | Umbrella extras | — |

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
