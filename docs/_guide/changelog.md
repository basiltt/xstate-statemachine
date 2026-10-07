---
title: "Changelog"
description: "Release history and what changed in each version."
---

# Changelog

All notable changes to XState-StateMachine for Python are documented here.

For the full changelog with commit history, see [CHANGELOG.md on GitHub](https://github.com/basiltt/xstate-statemachine/blob/main/CHANGELOG.md).

This project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html) for the core and persistence APIs; `contrib` extras are provisional. See the [Deprecation Policy](../deprecation-policy/) for how deprecated APIs are warned about and removed.

---

## [Unreleased]

_No unreleased changes yet._

## [0.11.0] - 2026-10-01

### Brokers & Celery (Phase F) -- #294, #292

- **Broker adapters (#294), `xstate_statemachine.contrib.brokers`.**
  `RedisStreamsBroker` / `SyncRedisStreamsBroker` (`[redis]`: consumer
  groups, `XACK`, `XAUTOCLAIM` of a dead consumer's pending entries after
  `min_idle_ms`, optional subject-hashed shards), `KafkaBroker`
  (`[kafka]`, aiokafka: key = subject, commits only the contiguous acked
  prefix), `RabbitMQBroker` (`[rabbitmq]`, aio-pika: durable queues,
  persistent messages, optional consistent-hash exchange routed on
  subject), `NatsBroker` (`[nats]`, JetStream: `<topic>.<subject>`,
  `Nats-Msg-Id` dedup) and `SqsBroker` / `SyncSqsBroker` (`[sqs]`,
  boto3: FIFO `MessageGroupId` = subject, `MessageDeduplicationId` =
  envelope id, `extend_visibility`). One shared core gives every adapter
  local requeue-to-head, settle-once, broker redelivery counts stamped as
  envelope attempts (so poison reaches the DLQ across restarts, X0.8),
  the size cap before parsing (X0.4), undecodable messages dropped never
  looped, and `healthy` / `on_disconnect` / `on_reconnect`. Every adapter
  passes `AsyncBrokerContract` in CI (fakeredis, moto, in-memory client
  stand-ins) and, opt-in (`XSM_CONTAINERS=1`, manual `live-brokers` CI
  job), on real brokers in testcontainers with 1,000 envelopes / 10
  subjects and a broker restart mid-consume. Registered under the
  `xstate_statemachine.brokers` entry-point group (`xsm plugins`).
  Pins: `aiokafka>=0.10`, `aio-pika>=9`, `nats-py>=2`, `boto3>=1.28`;
  `[eda]` umbrella filled. Guide: Brokers.
- **`[celery]` (#292), `xstate_statemachine.contrib.celery`.**
  `celery_service(task, *, args_from, timeout_s, queue)` makes a Celery
  task an `invoke` service: `onDone` from the result, `onError` on
  failure or timeout, `revoke()` on state exit (best effort). Completion
  is delivered through the engine's own actor-logic path (a forged
  `done.invoke` is still refused): live through a result-backend watcher,
  durably through `deliver_result` from `task_success` / `task_failure`
  signal handlers (`connect_signals`) or `poll_results`. Task headers are
  trusted only after the persisted instance confirms the invocation is
  still active with that task id; stale completions are ignored and
  reported to `on_event_dropped`. `@statechart_task(app, store, machine)`
  runs the `persisted()` act-loop on a worker and retries `ConflictError`
  through `autoretry_for`; it refuses a non-JSON / pickle-accepting app.
  `poll_results` is the durable delivery path; a signal-path
  completion that beats the caller's save is parked
  (`MemoryPendingResults`) and retried there, never dropped. Every
  entry point refuses pickle / YAML (by name or MIME type) for task
  and result deserialisation (`assert_json_serializer`).
  `DurableTimerScheduler` runs `DueTimerScanner.run_once` from Celery
  Beat (`xsm_deadlines_every`) plus `eta` jobs that carry the
  state-entry generation (X0.9); `outbox_relay_task` drains the outbox.
  Pin: `celery>=5.3`. Guide: Celery.

### Django, DRF & Channels (Phase D) -- #280, #281, #282, #283, #310

- **`[django]`: a real statechart on a Django model (#280).**
  `StatechartField` stores the snapshot as JSON. Sibling columns
  (`<name>_state` indexed, `_state_ids`, `_version`, `_machine_version`)
  are added in `contribute_to_class`, so `makemigrations` works normally
  and a second run is clean. `filter(statechart__state=...)`,
  `__state__in` and `objects.in_state("order.review")` (whole-segment
  match, bound parameters) are indexed queries. The snapshot is
  size-capped on write and read (X0.4). `StatechartModelMixin.send()` runs
  in `transaction.atomic()` with `select_for_update()` by default (on
  SQLite a write lock first). `lock="optimistic"` fences on the version
  column and raises `ConflictError` (`send_with_retry`). Sixteen threads x
  100 sends is exactly 1600 in both modes. A writer that waits out the
  database's busy timeout (SQLite `database is locked`, Postgres `lock
  timeout`) raises the retryable `LockTimeoutError` -- `send_with_retry`
  retries it -- never a bare driver `OperationalError`. Also added: `can` /
  `available_events` / `machine` / `matches`, `asend` for async views,
  `forget_statechart()` (X0.5), and `save()` that never rolls the state
  back. `DjangoStore` passes the A2 `StateStore` contract suite.
  Persisted `after` deadlines live in an indexed table that
  `manage.py xsm_deadlines` (`DueTimerScanner` over `DjangoModelStore`)
  fires. New: `refresh_statechart_columns` and the
  `refresh_statechart_columns_op` migration helper.
- **Signals, audit and permissions (#281).** `pre_transition` (raise
  `TransitionVetoed` → `denied`, no change, no audit row),
  `post_transition` (inside the transaction: a raising receiver rolls back
  the state and its audit row; `connect(..., on_commit=True)` defers to
  `transaction.on_commit`), and `statechart_error`. `TransitionLog` rows
  are written in the same transaction as the state change, with a
  redacted payload and `actor` / `reason`. `forget` redacts by default.
  `PermissionGuard` (object-level `has_perm`), `RoleGuard`, `AnyOf`,
  `AllOf`. `has_event_permission(user, obj, event)` answers "may this user
  do it" once for the admin, DRF and Channels. `DjangoOutboxStore` (EDA
  `OutboxStore`) rows join the open `atomic()`, so a rollback leaves no
  row.
- **Admin and management commands (#282).** `StatechartAdminMixin` renders
  one button per event this user may send. Each button is a
  **CSRF-protected POST form**, and the permission is re-checked on POST.
  A GET changes nothing. `meta.confirm` events get a confirmation page
  with a reason that is stored in the audit row. Also added: a history
  inline, a state filter, bulk actions (`n changed / m denied`) and a
  Mermaid diagram view. `manage.py xsm_inspect / xsm_diagram / xsm_docs /
  xsm_simulate` match `xsm` byte for byte. New: `xsm_snapshots --stale`.
- **`[drf]` and `[channels]` (#283).** `StatechartViewSetMixin` generates
  one `@action` per declared event plus `send/`, `events/`, `history/`
  (the view's pagination and filters, with a separate permission) and
  `stream/`. The receipt maps to 200/202/409/422 through the core
  `receipts` table, and a permission-guard refusal is 403. A viewset
  without explicit `permission_classes` does not build (closed by
  default, X0.1). `Idempotency-Key` is scoped to `request.user` through
  the new `DjangoInbox` (X0.2). New: `StatechartSerializerField` (the
  FastAPI `GET /{id}` shape, shared golden fixture) and a drf-spectacular
  schema with typed 403/409/422 responses, validated in CI.
  `StatechartConsumer` requires `AuthMiddlewareStack` (close 1008
  otherwise), sends a snapshot on connect, broadcasts each transition to
  every connection on the row, and has a heartbeat. 100
  connect/disconnect cycles leave nothing behind.
- **Migrating from django-fsm-2 (#310).**
  `manage.py xsm_migrate_fsm app.Model --field state` extracts XState
  JSON from the `@transition` decorators (`--dry-run` / `--write-chart`;
  conditions and permissions become guard names). It then fills
  snapshots from the FSM column, batched, resumable and idempotent.
  `FSMDualWriteMixin` keeps the old column in sync for the dual-read
  release. New core primitive: `persistence.from_state_ids(machine, ids,
  context)` builds a snapshot for a configuration without running
  anything, and loudly refuses illegal configurations.
- **Packaging.** The `[django]`, `[drf]` and `[channels]` extras now pin
  `django>=4.2`, `djangorestframework>=3.14` and `channels>=4`, and join
  `[all]`. The Django classifiers are added. The three CI cells install
  pytest-django (+ drf-spectacular / daphne / django-fsm-2). The oldest
  proven set on Python 3.9 is Django 4.2, DRF 3.14 and Channels 4.0.
- **Docs.** New pages: [Django](../integration-django/) and
  [DRF & Channels](../integration-drf/). The
  [vs django-fsm](../comparisons/vs-django-fsm/) migration recipe now
  describes the shipped command. New example:
  `examples/integrations/django_approvals`.
### Event-driven architecture (Phase F core) -- #272, #293, #295

- **`xstate_statemachine.eda` (#272, #293).** A zero-dependency core
  package (not loaded by `import xstate_statemachine`). `Envelope` is a
  frozen CloudEvents 1.0 event with the `correlationid` / `causationid` /
  `machineid` / `machineversion` extensions; `subject` is the instance key
  and the partition key; ids are sortable UUIDv7-style values. It is
  validated before `to_event()` (`EnvelopeCorruptError`), size-capped
  before parsing (`EnvelopeTooLargeError`, X0.4), refuses
  credential-bearing extensions and validates `traceparent` (X0.8).
- **`BrokerAdapter` / `SyncBrokerAdapter` protocols (#272)** with a
  contract suite (`tests/eda/contract.py`) the #294 adapters will run, and
  in-memory `FakeBrokerAdapter` / `SyncFakeBrokerAdapter` (failure
  injection, `deliver()`, `drain()`), also importable from
  `xstate_statemachine.contrib.testing` next to `replay()` and the new
  `assert_replay_consistent()`.
- **`InboundDispatcher` (#293)**: envelope → `persisted(key=subject)` →
  `send(envelope.to_event())`, with inbox dedup on the envelope id,
  per-subject ordering with `max_in_flight` concurrency, and poison
  handling (X0.8): a failed delivery is not committed and is requeued; at
  `max_attempts` it is dead-lettered and acked. Unknown types and corrupt
  envelopes are dead-lettered, never raised into the loop.
- **Transactional outbox (#293, #284 part 3).** `OutboxPlugin` publishes
  what the chart declares: `meta.publish` on a transition (now parsed as
  `TransitionDefinition.meta`) or a `publish`-tagged state. Its sinks are
  an `OutboxStore` (zero-dep `SQLiteOutboxStore`, or
  `SQLAlchemyOutboxStore` in `[sqlalchemy]`) that commits with the
  snapshot under `PessimisticLock` and is drained by `OutboxRelay`, or a
  broker directly. `causationid` is the inbound envelope that caused the
  transition.
- **Dead letters (#293).** `patterns.DeadLetter` / `DeadLetterPlugin` are
  extended, not forked. Records gain `id`, `reason`, `envelope`, `topic`,
  `machine_hash`, `machine_version` and `resolved_at`. Stores gain `put`,
  `get`, `list`, `mark_resolved` and `delete`. New:
  `SQLiteDeadLetterStore` (redacted, audited) and `BrokerDeadLetterSink`
  (publishes to `<topic>.dlq`). The plugin also accepts any object with
  `put()`.
- **`xsm dlq list|show|replay|purge` (#293).** `replay` is a dry run
  unless `--no-dry-run --yes --reason`, reuses the envelope id (the inbox
  dedups a double replay), refuses a changed machine without `--force`,
  and writes an audit row, as does `purge`.
- **AsyncAPI (#293, #295).** `asyncapi_document(machine)` renders consumed
  and published events as an AsyncAPI 3.0.0 document with CloudEvents
  messages, validated offline against a vendored schema
  (`validate_asyncapi`). New `xsm asyncapi machine.json [-o] [--validate]`;
  `xsm docs` gains an "Integration events" section.
- **`patterns.SagaBuilder` (#295)** emits plain, `strictConfig`-clean
  chart JSON for an orchestrated saga: per-step invoke, timeout and
  optional `RetryPolicy`, reverse compensation exactly once, and
  `compensationFailed` dead-lettered. Every step transition is published.
  **`patterns.ChoreographyRouter`** routes `type → (machine, EVENT)` over
  `InboundDispatcher`, and the causation chain ties the conversation
  together.
- **`[cloudevents]` extra (#293)** (`cloudevents>=1.10`, 1.x and 2.x):
  `to_cloudevent` / `from_cloudevent` and HTTP `to_binary` /
  `to_structured` / `from_http`, which reads only `ce-*` headers and drops
  credential-bearing ones. Added to `[all]`, the compat matrix and the CI
  extras cell.
- Docs: new [Event-driven architecture](https://basiltt.github.io/xstate-statemachine/guide/integration-eda/)
  page; the Guarantees page's outbox and ack steps are now shipped.
- Also in `xstate_statemachine.eda`: the `OutboxRecord` row type and
  in-memory `MemoryOutboxStore`, the `DispatchResult` returned by the
  dispatcher, `BrokerPublishError`, `ReplayRefusedError` / `ReplayResult` /
  `replay_dead_letter`, `redact_record`, `load_asyncapi_schema`, and the
  constants `PUBLISH_TAG`, `ATTEMPT_EXTENSION`, `DEFAULT_MAX_ATTEMPTS` and
  `DEFAULT_MAX_IN_FLIGHT`.
- **Example: `examples/integrations/eda_fulfilment`.** An order chart and a
  warehouse chart that talk only through events (`ChoreographyRouter`),
  with the SQLite outbox committed with the snapshot, inbox dedup, poison
  -> dead letters and `xsm dlq`, the Celery bridge in eager mode, and
  Prometheus / OpenTelemetry / inspector sinks in memory. The same demo
  runs on all five real broker adapters -- Redis Streams, Kafka,
  RabbitMQ, NATS JetStream and SQS -- offline over in-process stand-ins
  (fakeredis, fake aiokafka / aio-pika / nats-py clients, moto) or
  against a live server when `REDIS_URL` / `XSM_KAFKA_BOOTSTRAP` /
  `XSM_RABBITMQ_URL` / `XSM_NATS_URL` / `XSM_SQS_ENDPOINT` is set, with a
  parametrised suite (order, outbox == published, poison -> DLQ,
  redelivery carries the attempt). It needs no running service:
  `python -m eda_fulfilment --broker kafka`.
- **Fixed: `[sqlalchemy]` on SQLite: a newly created snapshot could survive a
  rollback of its `PessimisticLock` block (#293).** pysqlite emits no
  `BEGIN` before a `SAVEPOINT`, so when the create-only INSERT was the
  first write of the lease, its savepoint's `RELEASE` committed. The inbox,
  log and outbox rows in the same block rolled back while the snapshot did
  not. The savepoint now nests inside an explicit transaction.
- **Fixed: `persisted()` / `apersisted()` restore `buffer_marks` on exit and
  key post-save buffers by block (#293).** A plugin shared by concurrent
  blocks (worker threads, interleaved `apersisted` tasks) can no longer
  flush another block's rows, and one reused outside `persisted()`
  writes immediately again. Markers flush inbox-first and all run even
  if one fails.

### Added

- **`StoreUnavailableError` (`StoreError` subclass) and typed Redis errors
  (battle-test #306).** A Redis failover surfaced as a raw
  `redis.exceptions.ConnectionError` past `except StoreError`: every web
  route answered `500 "ConnectionError"` with a traceback per request. The
  `[redis]` store, inbox and log now map `redis.RedisError` the way
  `SQLiteStore` has since #259 -- connection-class failures are
  `StoreUnavailableError`, which the Starlette/FastAPI, Flask and Django
  adapters answer with **503 Store unavailable** (one WARNING line per
  request, no exception text; `/_xsm/health` stays 200, `/_xsm/ready` is
  503). `IdempotencyPlugin(on_inbox_error="refuse")` refuses on it.
  Clients `RedisStore`, `RedisInbox` and `RedisLog` build from a URL get
  `DEFAULT_SOCKET_TIMEOUT_S` /
  `DEFAULT_SOCKET_CONNECT_TIMEOUT_S` (5 s; URL query overrides), so a
  server that accepts TCP and never answers is a bounded
  `StoreUnavailableError`, not a hang (a client you pass in keeps its
  own settings). `RedisStore.due_keys` /
  `AsyncRedisStore.due_keys` read the sorted-set index for the scanner.

- **`StreamEvent`, `drain_pending_cleanups(timeout=)`,
  `DEFAULT_CLEANUP_TIMEOUT` (battle-test #267).** `StreamEvent` is the
  `Event` subclass a stream actor (`from_async_iterator` / `from_iterator`)
  delivers: **`event.data` is the item** (the `DoneEvent` precedent and
  what the #267 verification script read), `event.payload` stays
  `{"data": item}` so dict / JSON code keeps working. It round-trips
  through `persist_event` / `restore_event` (a `"stream": true` flag in
  the record; a record without it is a plain `Event`), so a pending stream
  item in a snapshot restores as the same shape on both engines.
  `drain_pending_cleanups(timeout=30.0)` bounds how long the async
  `stop()` waits for `async def` cleanups: a cleanup still running after
  the timeout is cancelled and logged (`None` waits without bound).
  `StreamEvent`, `RunningLogic`, `drain_pending_cleanups` and
  `DEFAULT_CLEANUP_TIMEOUT` are exported from the top-level package.

- **`PRIVATE_CONTEXT_PREFIX` (`"_xsm_"`), `is_private_context_key()`,
  `public_context()` (battle-test #265).** A reserved prefix for library
  bookkeeping that must survive the process and therefore rides in the
  snapshot's `context`. `context_model(...)` validates the user's keys
  only (a model with `extra="forbid"` is unaffected); the Starlette /
  FastAPI / Litestar / Flask / Channels state bodies hand the
  `context_serializer` the public view. The first such key is the
  dead-letter error chain, `patterns.ERRORS_CONTEXT_KEY` (`"_xsm_errors"`,
  now exported).
- **`DeadLetterPlugin(max_errors=20)`** -- the chain keeps the newest N
  entries; messages are cut at 1 000 characters and secret context values
  are masked inside them. **`ScanResult.locked`** (#264 follow-through)
  and the `circuit_breaker_call_closed` benchmark row.
- **`examples/integrations/fastapi_orders` gateway-outage scenario** -- one
  `CircuitBreaker` per process in front of the payment gateway
  (`registry.breaker`), `paymentFailed` tagged `dead-letter`, a
  `DeadLetterPlugin` on the registry writing into the orders SQLite file
  (`registry.dead_letters`, visible via `xsm dlq`). 60 orders during an
  outage hit the gateway 3 times; 32 threads on a dark gateway are
  refused, not hung; half-open admits exactly one probe; a dead-lettered
  order recovers by paying again.

- **`SQLiteStore.due_keys(until_wall, *, limit=1000)` and
  `MemoryStore.due_keys(...)` (battle-test #264).** `(key, earliest
  due_at_wall)` for keys with a matured deadline, earliest first -- one
  query on the `deadlines_due` index (SQLite) or a dict walk (Memory),
  the shape the `[sqlalchemy]`, `[redis]` and `[django]` stores already
  had. `DueTimerScanner` uses it when present: 100 000 records / 100 due
  went from 3.5 s and 100 000 record loads to 0.023 s and none.
- **`examples/integrations/fastapi_orders` scheduler-outage scenario** --
  400 orders arm timeouts and retry backoffs over an afternoon; the one
  scheduler is down for three hours. The backlog drains oldest-first in
  `limit=100` batches, `max_lag_s` reports the outage, live timers are
  left alone, two schedulers started by accident still commit each
  deadline once (both locks), and a crash between fire and save re-fires
  without a torn record. `build_scanner()` accepts overrides.

- **`Interpreter.await_settled(timeout)`, `apersisted(settle_timeout=)`,
  `DEFAULT_SETTLE_TIMEOUT` (battle-test #263).** `await send(..., wait=True)`
  resolves at the end of the *event's* macrostep; a service completion is
  the *next* macrostep, which the run loop starts at once. On a chart with
  two plain `def` invokes in a row (authorise → capture) the machine was
  therefore mid-step exactly when an `apersisted()` block exited, and the
  snapshot was refused (`SnapshotMidStepError` → HTTP 500) -- while the
  sync engine's `send()` drains the chain and `persisted()` never saw it.
  `await_settled` waits, bounded, until no step is in flight and no engine
  completion is queued or owed (plain `def` futures *and* `async def`
  tasks); a live `after` timer is not owed work. `apersisted()` and the
  Starlette / FastAPI / Litestar / Quart registries settle before the
  snapshot and before the receipt body, so the `200` a caller reads is
  what the store holds. `settle_timeout=0` restores the old loud refusal.
- **`BaseStore.list_versions(prefix=, limit=)` and
  `MAX_MACHINE_VERSION_LENGTH` (255) (battle-test #263).** `(key, label)`
  pairs without loading the blobs: one `SELECT` on SQLite, a header read
  on `FileStore`, a dict walk on `MemoryStore`; third-party stores fall
  back to `list_keys` + `load`. What `xsm snapshots --stale` uses.
- **`xsm snapshots --fail-if-stale`** -- exit **1** when stale keys exist
  (implies `--stale`): the deploy gate between "v2 rolled out" and "v1
  workers retired". Exit **2** for bad input (not a machine, missing or
  unreadable store, a nesting bomb). `--json` reports `total` and
  `truncated` when `--limit` cut the list; the table title says "N of M".
- **`examples/integrations/fastapi_orders` rolling-upgrade scenario** --
  `machine_v2.json` (authorise → capture, a `currency` key) and
  `migrations.py` (one scoped `SnapshotMigrator` step); v1 orders at every
  interesting point are migrated lazily, once, by v2 workers *and* the v2
  scheduler; 50 concurrent `PAY`s on one stale order commit exactly one
  migration; `xsm snapshots --stale` is the drain list before and after.

- **`IdempotencyPlugin(on_inbox_error="refuse" | "admit")` and
  `InboxUnavailableError` (HTTP 503) (battle-test #261).** What a keyed
  event gets when the inbox *backend* fails. `"refuse"` is the default --
  the receipt carries the typed, retryable error and the action never
  runs; `"admit"` opts into availability (the event runs undeduplicated
  and `on_plugin_error` fires) for webhooks whose sender retries anyway.
  `receipt_to_status` maps the new error to **503**; `STATUS_UNAVAILABLE`
  exported from `receipts`.

- **Observability & live inspector (Phase B) -- `[observability]` extra
  (#273).** `OpenTelemetryPlugin` opens one `statechart.transition` span per
  processed event and closes it in `on_event_processed` with the outcome
  (`statechart.from` / `.to` / `.changed` / `.denied` / `.deferred` /
  `.actions`); guard evaluations are span events, action / guard / service
  errors and chain trips are `record_exception`, each invoked service is a
  child span, and a `traceparent` payload header becomes a span link.
  `PrometheusPlugin` exports transitions, event dispositions, guard
  evaluations and errors, action errors, service duration and errors,
  chain trips, active interpreters and a polled `queue_depth`.
  `StructlogPlugin` / `LoguruPlugin` bind `machine_id`, `state`, `event`
  (and `correlation_id`) around each event so log lines inside actions
  carry them; `SentryPlugin` adds breadcrumbs and, opt-in, captures
  errors. `instrument_all()` attaches them to every interpreter built
  afterwards (global registry), to one interpreter, or to a registry's
  `plugins` list; `discovered=True` goes through
  `plugins.attach_discovered`. X0.6 telemetry hygiene: event labels come
  from the chart allow-list (`unknown` fallback), every label dimension is
  capped (`max_label_values` -> `other`), and payloads, instance keys and
  correlation ids are never labels. The extra pins `opentelemetry-api>=1.20`
  and `prometheus-client>=0.17`; structlog, loguru and sentry-sdk are soft
  imports. `AgentTracePlugin(on_span="otel")` emits real `gen_ai.*` spans.
  The `plugins_*` performance rows now include `PrometheusPlugin`. Guide:
  *Integrations -> Observability*.
- **Observability & live inspector (Phase B) -- live inspector (#274).**
  `xstate_statemachine.inspect` (stdlib only) speaks the
  `@statelyai/inspect` wire protocol (`@xstate.actor` / `.event` /
  `.snapshot`), pinned against fixtures recorded from the real npm package.
  `InspectorPlugin(sink, context_allowlist=...)` with `MemorySink`,
  `JsonLinesSink` (files 0600), `SseSink` (SSE over `http.server`, own
  fallback page plus the hosted Stately UI) and `replay_messages()`. CLI:
  `xsm inspect machine.json --live [--port] [--open]`,
  `xsm sim --record session.jsonl`, `xsm replay session.jsonl [--live]`.
  New plugin hook `on_event_sent(interpreter, target_id, event)` fires on
  the sender of `sendTo` / `sendParent` / `forwardTo` on both engines.
  `MachineNode.source_config` keeps the config the machine was built
  from. X0.7: per-run `secrets.token_urlsafe(32)` compared with
  `hmac.compare_digest`, the token in the URL only on first load (then an
  `HttpOnly; SameSite=Strict` cookie), loopback bind with `Host` and
  `Origin` checks, a non-loopback host requires `--token`, strict CSP,
  context deny-by-default. `[starlette]` / `[fastapi]`:
  `mount_inspector(app, registry, debug=True)` now serves the stream over
  WebSocket (`WebSocketSink`) instead of answering 501. Guide:
  *Integrations -> Live inspector*; `xsm` guide section "Live inspector".
- **`[testing]`: generated path tests (#269).** Request the `xsm_path`
  fixture under an `xstate_machine` marker and the test is parametrised
  over `graph.shortest_paths(machine)` -- one case per reachable
  configuration, with ids like `path[editing->authenticating3DS->challenge]`.
  `xsm_path.replay(xsm_interp, xsm_clock)` drives the interpreter there.
  `--xsm-full-paths` switches to `simple_paths` (`--xsm-max-paths`,
  `--xsm-max-depth`); `--xsm-path-guards true|false|both` also reaches the
  configurations that only a False guard or a failing service leads to.
- **State & transition coverage (#270).** Core
  `xstate_statemachine.coverage.CoverageCollector` is a `PluginBase` that
  records every configuration entered and every chart transition taken.
  Parallel configurations mark all leaves and their ancestors, history
  restores mark what was re-entered, and restored interpreters count at
  `start()`. `report(machine)` returns `CoverageReport(states_visited,
  states_total, unvisited, transitions_hit, transitions_total, unhit)`,
  using `graph.transition_coverage_targets` as the denominator. Machines
  are keyed by `id@structure_hash`. The collector is thread-safe. It
  renders to a stable `{"version": 1, ...}` JSON document, a single
  self-contained HTML file, or a terminal summary. In pytest,
  `--xsm-coverage` registers one collector through the existing
  `plugins.register_global` for the whole session (unregistered at the
  end), so interpreters a test builds itself are counted as well as the
  fixtures' ones. Related options: `--xsm-coverage-report=term|json[:PATH]|html[:PATH]`,
  `--xsm-fail-under-state-coverage=N` and
  `--xsm-fail-under-transition-coverage=N`. The new
  `xsm coverage report.json [--fail-under N] [--plain] [--json]` renders the
  report in CI.
  Hardened in the #270 battle -- see "Coverage gates, as battle-tested"
  under Changed. New benchmark row `coverage_collector_overhead`
  (unbudgeted).
- **Hypothesis model-based testing (#271).**
  `xstate_statemachine.contrib.testing.model_test(chart, *, logic=,
  invariants=, state_assertions=, payloads=, clock=True, max_steps=50,
  settings=, allow_denied=False, snapshot_roundtrip=True, guard_flip=False)`
  generates a Hypothesis `RuleBasedStateMachine` that pytest collects
  (`TestX = model_test(...)`). There is one rule per declared event. Each
  rule draws its payload first and sends only when
  `can(Event(type, payload))` is true, so only legal sequences are
  generated. `can()` runs real guards when you pass real logic, so keep
  guards pure. Further rules advance the clock over the declared `after`
  delays, round-trip a snapshot mid-sequence, and flip stub guards.
  Payloads are inferred from `event_schemas` / pydantic `EventModel`
  fields. When an invariant fails, Hypothesis shrinks the run to a minimal
  sequence and `model_test` writes it as an `xsm simulate --script` file
  (`failing.json`, or into `--xsm-failing-dir`). `events_strategy(chart,
  length=)` is a plain strategy of legal event sequences. `hypothesis` is
  imported lazily: without it, `model_test` raises `MissingExtraError`
  naming `[testing]`, which already pins `hypothesis>=6.100`.
- **Entry-point plugin discovery (#296).** Third-party packages can ship
  plugins, stores and brokers without a core change by declaring entry
  points in the `xstate_statemachine.plugins` / `.stores` / `.brokers`
  groups. `xstate_statemachine.plugins.discover(group=, allow=, strict=)`
  returns `DiscoveredPlugin(name, distribution, version, obj, hooks,
  group)`, and `attach_discovered(interp, allow=)` constructs each plugin
  and `.use()`s it (the hook that `instrument_all(discovered=True)` in
  `[observability]` builds on). Discovery is **never implicit**: nothing
  loads on import, `allow=` filters before import,
  `XSM_DISABLE_PLUGIN_DISCOVERY=1` turns it off, and a loader that raises
  is logged and skipped unless `strict=True`. Python 3.9's dict-shaped
  `entry_points()` is shimmed.
- **`xsm plugins [--json]` (#296)** lists name, distribution, version,
  group and the `PluginBase` hooks each discovered plugin implements.
- **`xstate_statemachine.deprecations` (#296).** `deprecated(what, since=,
  removal=, alternative=)` emits a `DeprecationWarning` **once per call
  site**, and `deprecations()` is the registry the policy page renders.
  `ErrorEvent.data`, `--style` and the `events.engine_*` aliases now go
  through it.
- **Compatibility matrix (#296).** `tests/contrib/compat_matrix.json`
  records, per shipped extra, the declared floor, the oldest release proven
  on Python 3.9 and the newest release. A new `Compat` workflow runs both
  cells for every extra (weekly, on demand, and on PRs that touch
  `pyproject.toml` or the matrix), and the docs table is generated from
  the same file.
- **`[all]` wheel smoke on Linux, macOS and Windows (#296).** CI installs
  the built wheel with `[all]` into a clean venv, imports every `contrib`
  subpackage, runs each extra's docs Quick start, and re-checks that
  `import xstate_statemachine` alone loads no third-party module.

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
- **`examples/recipes/` (#308).** Eight runnable recipe folders
  (`stripe_webhooks`, `apscheduler_timers`, `task_queue_workers`,
  `form_wizard`, `slot_filling`, `feature_flag_rollout`,
  `websocket_reconnect`, `circuit_breaker_retry`), each with a
  `machine.json` that passes `xsm validate`. Third-party libraries
  (FastAPI, Flask, APScheduler, Streamlit, Gradio, Dramatiq, the Stripe
  SDK) are imported softly, and no dependency is added to the package.

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
  generation"; CLI &sect; "Paths". The traversal never modifies the
  caller's machine (it explores a private copy, so concurrent calls and
  live interpreters are unaffected); `max_configs=100_000` bounds a
  combinatorial chart with `ExplorationLimitError` (partial result on
  `.found`); wildcard (`"*"`, `"mouse.*"`) handlers are explored.
- **`[testing]` extra: a pytest plugin** (#268; both engines). Registered
  through a `pytest11` entry point, so `pip install
  "xstate-statemachine[testing]"` is the whole setup; the plugin imports
  only pytest + core, is a no-op without the marker, and `-p
  no:xstate_statemachine` disables it. `@pytest.mark.xstate_machine(
  source, logic=, strict_config=, strict=)` builds the machine from a JSON
  path (relative to the test file, then rootdir), a dict or a `MachineNode`
  -- on `stub_logic` unless `logic="pkg.module:callable"` -- and serves the
  `xsm_`-prefixed fixtures: `xsm_machine`, `xsm_clock` (`SimulatedClock`),
  `xsm_interp` (started `SyncInterpreter`, stopped at teardown),
  `xsm_ainterp` (async twin; skips naming `pytest-asyncio` when it is
  absent), `xsm_ran` (stub actions that ran), `xsm_guards` (the live
  stub-guard table), `xsm_store` (`MemoryStore`), `xsm_send_all` /
  `xsm_asend_all` (the `xsm simulate --events` grammar, `+N` advances the
  clock) and `xsm_snapshot` (file-backed assertion on `state_ids` /
  `value` / `context` / `status`; `--xsm-update-snapshots` records,
  a mismatch is a unified diff, files are byte-identical across runs).
  `@pytest.mark.xstate_guards_false("g")` forces stub guards; with real
  logic it is a `pytest.UsageError`, as is every malformed marker.
  `pytest --xsm-version` prints the library version. `xsm gt -t pytest
  --fixtures` emits the recorded-trajectory scaffold on the plugin's
  marker and fixtures (default output unchanged). Guide page *pytest*.
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
  set the scanner reads directly. `RedisInbox` computes and compares
  every expiry on the **Redis server clock** (hosts with skewed clocks
  agree on whether a key is live). `RedisLog` uses the record's `seq` as
  the stream id with a compare-and-append script, so concurrent writers
  never mint the same `seq`, `append_next` is atomic across hosts and
  `read(after_seq=)` is a ranged `XRANGE`; its `maxlen` defaults to
  unbounded (it was 10 000 -- a silently trimmed audit head). Guide page
  *Redis* with guarantees and threat-model boxes; the boxes state that
  snapshot, inbox mark and log record are three atomic writes, not one
  transaction.
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

### Documentation

- **Deprecation Policy page (#296).** SemVer covers the core and the
  persistence layer; `contrib` APIs are **provisional**. A deprecated API
  warns for at least one minor release and is removed no earlier than the
  next major. The page includes a current-deprecations table that a test
  keeps in sync with the registry. It is linked from this changelog's
  header and from the README's new "Versioning & support" section, which
  also states the supported Python range.
- **Compatibility page (#296)**, generated from the matrix. Five declared
  floors do not pass on Python 3.9, and the page shows declared vs oldest
  tested with the reason for each: `[fastapi]` 0.100 -> 0.106.0,
  `[litestar]` 2.0 -> 2.14.0, `[sqlalchemy]` 2.0.0 -> 2.0.2, and
  `[starlette]` 0.27 -> 0.45.3. For `[flask]`, 2.3.0 passes, but its Quart
  shim needs Werkzeug 3.
- **Plugins guide: "Third-party plugins: discovery" and "Writing a
  third-party plugin" (#296).** SECURITY.md gains the plugin trust model
  (discovered plugins run in-process with full privileges), and the
  security page's X0.14 row covers discovery.

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

- **Recipes pack (#308).** A new *Recipes* section (index page, linked
  from the README Cookbook and the Integrations journey) with eight worked
  recipes. Each has a Stately-importable chart, 30–60 lines of Python, an
  `xsm simulate --events …` line that a test replays, and a test under
  `tests/recipes/`:
  - **Stripe webhooks**: subscription lifecycle (`incomplete → active ↔
    past_due → canceled`), with FastAPI and Flask endpoints. They verify
    `Stripe-Signature` with a stdlib constant-time HMAC and a 300 s
    timestamp window (`stripe.Webhook.construct_event` when the SDK is
    importable), map `event.type` to machine events, deduplicate on
    `event.id` via `IdempotencyPlugin`, and persist via `persisted()`.
    Tested with recorded fixtures: a forged signature, a tampered body and
    a stale timestamp are rejected, and a replayed `event.id` is applied
    once. The Guarantees box cites X0.2 and X0.7.
  - **APScheduler durable timers**: `DueTimerScanner.run_once` as a cron
    or interval job (`max_instances=1`, `coalesce=True`), with 7-day and
    14-day `after` follow-ups and `--role scheduler` parity with the
    FastAPI example.
  - **RQ / arq / Dramatiq workers**: load → send → persist with an
    optimistic retry on `ConflictError`, written by hand for each queue
    and tested through a `FakeQueue` (8 threads on one key lose no update).
  - **Streamlit / Gradio wizard**: back/forward as events and guarded
    validation, with only the JSON snapshot kept in `st.session_state` /
    `gr.State` and the diagram embedded. Smoke-tested against stub `st` /
    `gr` modules.
  - **Chatbot slot filling**, **feature-flag rollout** and **WebSocket
    reconnect** (`RetryPolicy` jitter + `from_callback`) are pure engine,
    tested on both interpreters with a `SimulatedClock`.
  - **Circuit breaker & retry**: an HTTP client over stdlib `urllib` that
    retries 5xx/429/timeouts but never other 4xx, behind a shared
    `CircuitBreaker` that fails fast. Tested with a fake transport.
- **vs AWS Step Functions** comparison page: an ASL workflow and the same
  workflow in XState JSON side by side, the local-testing story (pytest +
  `SimulatedClock`, no emulator), and when Step Functions is still the
  right call. Its table is generated from a new `workflow_rows` set in
  `docs/_data/comparisons.json`, covered by `tests/test_comparisons.py`.
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

- **Actor logic helpers, as battle-tested (#267) -- a market-data feed
  that flaps for an hour (20 000 ticks pushed from the socket's own
  thread across 50 drop/reconnect cycles, both engines) and two
  adversary suites:**
  - **A `send_back` from an exited invocation is dropped.** A producer
    thread does not know the machine left the state; its late event used
    to land in whatever state came next -- and on the *next* socket's
    counter. It is now dropped with a debug log once the invocation's
    cleanup ran (SCXML's rule for a cancelled invocation).
  - **`send_back` refuses `internal` / `wait` / `priority` as payload
    keys** (`TypeError`). They reached the async engine's
    `send_threadsafe(internal=...)` as a *control* and the sync engine's
    as payload -- the same call meant two things. Send a dict event to
    carry such a key.
  - **A `send_back` that races `stop()`** on the async engine (status
    still `running`, loop already closing) is dropped with a warning
    instead of raising `RuntimeError` on the producer's thread.
  - **`drain_pending_cleanups` drains only the current loop's
    cleanups** and forgets tasks whose loop is closed; a cleanup left
    behind by a finished `asyncio.run()` no longer breaks the next one
    with `ValueError("different loop")`, and the module-global registry
    cannot grow with abandoned loops.
  - **A delayed `sendTo` whose target invocation exited** before the
    delay elapsed is dropped and reported via
    `on_event_dropped(reason="unresolved_target")`, not delivered to
    torn-down logic (both engines). If the state was re-entered and a
    new invocation runs under the same id, that live one receives it.
    The drop happens between steps, so it is reported but never
    attached as the *next* unrelated event's receipt error.
  - **`from_iterator` is honest about a blocked `next()`.** A sync
    iterator stuck in a blocking read cannot be interrupted; it stops at
    its next item, and the cleanup logs a warning naming the invocation
    when its thread is still alive (the 100 ms grace wait is skipped on
    an asyncio loop thread, so N blocked iterators cannot stall the
    loop). Give blocking iterators a timeout, or use `from_callback` and
    let the client's own thread push.
  - `tests/recipes` `Driver.close()` is idempotent (a scenario may stop
    the machine itself before the fixture does).

- **Patterns, as battle-tested (#265) -- behaviour changes you can hit:**
  - **The dead-letter error chain now lives in the snapshot** under
    `context["_xsm_errors"]`. In production (create → act → persist →
    discard: a request, then `DueTimerScanner` wakes, each in a fresh
    interpreter) the plugin's in-memory chain died with every block, and
    the record arrived with `attempts=3, errors=[]`. It is cleared on a
    clean `on_service_done`, by `retryReset`, and after capture;
    `on_interpreter_stop` no longer clears it. The chain is per
    **instance** (so machines sharing an id no longer mix) and per
    machine, not per parallel region. A start-time dead-letter state
    writes no record; the sink runs inside the step; children do not
    inherit the plugin.
  - `DeadLetterPlugin(sink)` raises `TypeError` at construction for a
    sink that is neither callable nor has `put()` (it used to fail at the
    first dead letter, losing it). A raising sink is logged at ERROR with
    the record id, then re-raised so `on_plugin_error` fires.
  - `DeadLetterStore.purge_older_than(NaN)` and `list(limit<0)` raise
    `ValueError` (NaN **erased the whole store**; a negative limit
    silently dropped the newest record).
  - `RetryPolicy`: an rng draw outside `[0, 1]` or NaN raises
    `ValueError` (it produced NaN / negative / over-cap delays silently);
    NaN parameters and non-finite `base_ms` / `factor` are refused;
    `max_ms=inf` remains "no cap". `retryReset` also clears the error
    chain.
  - `CircuitBreaker`: `call()` / `acall()` after `close()` raise
    `InterpreterStoppedError` (the target ran **unprotected**);
    `cooldown_ms` must be finite and ≥ 0 (NaN / inf kept the circuit
    open for ever, negative half-opened instantly); `reset()` keeps
    `opened_count` as a lifetime counter; the `circuit_breaker` decorator
    refuses generator / async-generator functions (`TypeError`) and no
    longer leaks the first function's name onto later breakers.

- **Durable timers, as battle-tested (#264) -- behaviour changes a
  0.11.0-RC user can hit:**
  - `DueTimerScanner(limit=)` caps machines **woken per tick, earliest
    deadline first**. It capped the keys *scanned* in name order, so a
    scheduler that came back to a backlog larger than the limit woke the
    same first N keys every tick and the rest never fired.
    `ScanResult.scanned` now means keys inspected (all of them on an
    indexed store). `FileStore` has no index: a tick reads every record
    (~2.4 ms each) -- use SQLite / SQLAlchemy / Redis beyond a few
    thousand records.
  - A lost optimistic race (`ConflictError` on the fire-save) and a
    `LockTimeoutError` (another scanner or request holds the key) count
    as `skipped_stale`, not `errors`. An operator alerting on `errors`
    was paged every time two schedulers overlapped. New
    `ScanResult.locked` counts the lock-timeout subset separately, so a
    permanently stuck holder is visible (`locked` climbing while `due`
    does not fall).
  - `skew_tolerance_s < 0` or `limit < 1` raise `ValueError` (both were
    silently accepted).
  - On `"resume"` / `"fire_due"` the remaining time is clamped to
    `[0, the delay the deadline was armed with]` (the persisted
    `delay_ms`): a wall clock stepped back between arm and restore made
    a 5 s timer wait 2 h 5 s; a `due_at_wall` of 1e308 re-persisted as
    `inf` and the next load refused the blob. The bound is the ARMED
    delay, not today's declared one, so a chart redeployed with a shorter
    `after` cannot fire an old deadline early (review H2).
  - Duplicate deadline records for one `(state, event)` resolve to the
    **newest `entry_seq`** (earliest due breaks ties). The last record in
    the list used to win, and a stale record from an earlier visit could
    fire the current visit early.
  - A delay resolver returning NaN / ±inf is "unresolvable" (logged, that
    timer skipped) instead of a bare `ValueError` on state entry; a
    negative delay arms at 0 instead of persisting `delay_ms < 0` that
    the next load refused.
  - `entry_seq` or `delay_ms` of 2**63 or more in a blob is
    `SnapshotCorruptError` (a 200-digit seq used to be adopted as the
    machine's counter).
  - Both engines fire matured deadlines **inside `start()`** under
    `"fire_due"`; a restored inbox drains before them. A delayed
    `raise(delay=)` self-send keeps *relative* remaining time (#213) and
    does not shift with the outage the way an `after` does.
  - Child actors: `restart_timers`, `clock` and `restart_services` are
    forwarded to child restores, and the sync engine's `start()` starts
    restored children as the async one did -- so with
    `restart_services=True` a restored child's dormant invoke re-runs
    too. A child restored as done / error / stopped is left alone on
    both engines; a resumed child's `sendParent` is processed by the
    same `start()`. The root's deadlines are the only ones the store
    indexes: a child-only timer cannot wake its parent.

- **Versioning, as battle-tested (#263) -- behaviour changes a 0.10.x
  user can hit on upgrade:**
  - `save(..., machine_version=)` longer than **255 characters** or
    containing **NUL** raises `ValueError` on every store. Memory / File /
    SQLite accepted both; the SQLAlchemy and Django columns are
    `VARCHAR(255)` and Postgres rejects NUL, so the rule is now the same
    everywhere and fails at the call site, not in a driver.
  - `"machine_version": null` in a blob is treated as **unlabelled** (like
    an absent key): restores with the once-per-process warning. It was a
    mismatch (`"None" != "1.0"`) even though the library itself writes
    `null` for a chart with no `"version"`, so adding a label to a chart
    refused every blob it had already written.
  - `xsm snapshots --stale` and `manage.py xsm_snapshots --stale` agree
    with restore: an **unlabelled record is not stale** (restore warns, it
    does not refuse) and a chart with **no `"version"` has nothing stale**.
    Both counted them before, so the drain list over-reported.
  - `sqlite:///relative.db` in `xsm snapshots` **and `xsm dlq`** is now
    **relative to the working directory** (SQLAlchemy's rule); four slashes
    is absolute, `sqlite:///C:/...` still works. `/x.db` at the filesystem
    root was never what the guide's own example meant. A missing SQLite
    file or `FileStore` directory is **refused** (exit 2) instead of being
    silently created empty and reported as "store is empty"; `memory://`
    is refused as meaningless.
  - `FileStore` writes `machine_version` **before** `snapshot` in the
    record so `list_versions` reads 8 KB per file instead of the blob;
    older records are read in full and still load. A write failure
    (ENOSPC, EACCES) raises a `StoreError` that is **also** an `OSError`
    with `errno`, so `except OSError` keeps working; the old record stays
    and no temp file is left.
  - The "carries no machine_version" warning is logged **once per
    (machine id, expected label) per process**, not once per restore
    (10 000 stale orders used to log 10 000 lines per deploy).
  - A migration step that **rewrites `state_ids` only** now restores: the
    `configuration` (leaves + ancestors) is re-derived from the new
    machine when the step leaves it untouched or `None`. The issue's own
    recipe was refused ("the two fields contradict each other"). A step
    that sets the two to disagree is `SnapshotCorruptError` naming the hop.
  - A step that **raises** surfaces as `SnapshotCorruptError` (the
    original chained as `__cause__`) naming the hop; one that returns a
    non-dict is a `SnapshotCorruptError` that is also a `TypeError`.
    Library errors raised inside a step pass through unchanged.
  - Requests on charts with chained `def` invokes take as long as the
    chain (they used to fail): see `apersisted(settle_timeout=)` above.

- **`JSONLinesLog.next_seq` is O(1) in steady state (battle-test #262).**
  It scanned the whole file on EVERY send (79 ms at 10 000 records -- a
  run with a JSONL log was quadratic). The last seq per machine is cached
  while the file size is unchanged; a foreign append, a purge or an
  external edit forces a rescan (0.012 ms at 10 000). `read()` still scans
  the file; use `SQLiteLog` beyond a few thousand records.

- **`SQLiteStore` schema v2: index on `deadlines(key)` (battle-test #259,
  found on CI by the #262 integration).** Schema v1 had no index on
  `deadlines(key)`, so every `load`, `save` and `delete` (the FK cascade)
  did a full scan of `deadlines` -- O(n) in the store's deadline count:
  save+delete read 114 µs → 308 µs → 1.1 ms at 100 / 2 000 / 10 000 keys
  with one deadline each. A database written by 0.11.0 is upgraded in
  place on open (one `CREATE INDEX IF NOT EXISTS`); the scaling test now
  saves snapshots WITH deadlines so it exercises that table.


- **Performance budgets now gate on every nightly, whatever the CPU
  (battle-test #307).** Three consecutive nightlies landed on three CPU
  models (AMD EPYC 9V74 / 7763 / 9V45, up to 2.4x apart on identical
  code) and the absolute-microsecond gate skipped every row on two of
  them -- it was enforced one night in three. Each row is now compared
  with a cross-CPU reference scaled by the run's own *speed factor* (the
  median of measured/reference over the core rows) and fails above x1.25;
  cold `import_*` rows scale as the square root of that factor. The
  absolute table stays as a same-CPU report (and as the only catch for a
  regression that slows *every* row equally -- stated on the Production
  Characteristics page). `tests/test_perf_gate.py` pins, untimed, that
  every recorded CPU passes, a uniform 0.5-2.4x shift passes and a 1.5x
  single-row regression fails. New report-only `benchmarks/scaling.py`
  big-O sweeps run nightly and upload `scaling.json`; finding:
  `shortest_paths` cost per configuration grows with path depth
  (2.3 -> 6.5 ms from depth 3 to 6 on an 8-region chart). Harness noise
  fixed: `persisted_*` rows had a CV up to 47 % (GC debt between rows,
  SQLite rows too short); now under 7 %. The Coverage job fetches depth 2
  so the budget ratchet (baselines only go down unless a note names a perf
  run) is enforced on every PR.

- **Idempotency inbox scopes are escaped (battle-test #303).** Scope parts
  (`principal`, `machine.id`, `instance_key`) now escape `%` and `/` so the
  join is injective. Parts without either character are byte-identical to
  before, so existing rows keep their scope. **If a principal, machine id
  or instance key in your deployment contains `%` or `/`**, inbox rows
  written before the upgrade resolve to a *different* scope afterwards:
  their cached receipts are unreachable, a retry inside the TTL
  re-executes once, and `inbox.forget(old_scope)` no longer matches. Let
  the TTL window elapse before relying on deduplication for such keys, or
  purge the inbox at deploy time.
- **A principal must identify a caller.** `IdempotencyPlugin.scope_for`
  and every web adapter (`StatechartRegistry.act`, the Starlette / FastAPI
  / Litestar / Flask / Quart HTTP helpers, DRF) route the principal through
  `validate_principal`: a value that is not a non-empty `str`, or is one
  of the literal placeholders `"None"` / `"null"` / `"anonymous"`, is
  refused -- `ValueError` from a direct `act()` call, **401
  `UnauthenticatedError`** from the HTTP helpers, 401 from DRF when an
  `Idempotency-Key` arrives from an unauthenticated user. Previously the
  adapters `str()`-coerced the value, so `None` became `"None"` and every
  anonymous caller shared one scope. Code that relied on an anonymous
  caller being deduplicated must authenticate it first.

- **Plugin hook dispatch is ~2x cheaper (battle-test #304).** `_SafePlugin`
  built a fresh `functools.wraps` closure on every hook lookup -- four per
  event -- which cProfile put at ~30 % of a plugin-equipped `send()`. The
  guarded wrapper is now cached per hook, keyed on the underlying function
  so rebinding a hook on a live plugin still takes effect at once. Measured
  (Windows, 3.14, 10 000 sends): sync 5-plugin overhead 5.74x -> 3.14x of a
  bare send; async 3.88x -> 1.49x. Behaviour is unchanged.

- **Deprecation targets now follow the policy (#296).** `ErrorEvent.data`
  said "removed in 0.9" and `--style` said "removed in v0.8.0", but both
  still work. Their warnings now name 1.0, the next major, and share the
  helper's message shape (what / since / removal / alternative). They warn
  once per call site instead of on every access.

- **`SyncInterpreter.send_events()` now applies the same admission checks as `send()`** — `strict` / `event_schemas` (`UnknownEventError` / `InvalidEventPayloadError` at the call site) and the reserved-payload-key warning — and both engines' `send_events()` run the new `on_before_send` interception (#304). Previously a batched send on the sync engine bypassed `strict` entirely.
- AGENTS.md now states the real Python floor, **3.9** (it said 3.8+;
  `requires-python` and CI have been 3.9 since 0.9).

### Fixed

- **Flask integration, as battle-tested (#285).** The onboarding wizard
  as browsers use it -- a 50-POST double-click on one wizard, fifty
  browsers walking every step at once on one SQLite file, two apps from
  one extension, back-button form replay, a stale cookie, the cookie cap,
  CSRF, a real `flask run` subprocess driven with httpx (+ `flask xsm
  inspect`), the Quart shim with concurrent clients, 16 SSE subscribers
  on a threaded server (`tests/contrib/flask/test_battle_285_{scenario,
  a,b}.py`, `examples/integrations/flask_wizard/tests/
  test_readme_commands.py`). Found and fixed: a double-click on the
  SQLite wizard was an HTML 500 (a raw `ConflictError`) and a re-posted
  earlier step's form was APPLIED to the current step, advancing the
  wizard with empty answers -- the example serialises writers per key
  (`PessimisticLock`), every form names its step and a stale one is
  refused under the lock via `g.xsm.skip_save()` (which the documented
  `g.xsm` handle did not expose). Library errors raised in your OWN
  views -- a lost optimistic race, `act()` in a GET view, an oversized
  session -- are RFC 9457 problems (409 / 405 / 413) instead of 500s:
  `init_app` registers the handlers (`error_handlers=False` opts out)
  and `SnapshotTooLargeError` maps to 413. `SessionStore`'s cap now
  covers every machine in one session together (two wizards made a
  4.3 KB cookie browsers silently drop; the wizard reset). The Quart
  shim: `/stream` checks `Origin`; `QuartXState.init_app` accepts
  `allowed_origins`, `max_connections_per_key`, `clock`, `migrator`,
  `error_handlers`; `act()` passes the request principal to the inbox.
  Docs: the guide's Guarantees box claimed losers "retry" -- nothing
  retried; it now documents `PessimisticLock()` and `persisted_retry`
  with runnable blocks, the exact CSRF recipe for the JSON blueprint
  (`X-CSRFToken` + the token's session cookie), `g.xsm.skip_save`, the
  shared cookie cap, a `flask xsm` reference in the CLI guide with a
  tested transcript, every `contrib.flask` / `contrib.quart` name in the
  API index; the example gained `WIZARD_STORE=sqlalchemy`, its README
  commands run literally from a fresh copy, and the `xsm new` flask
  scaffold stays file-for-file identical to it.
- **SQLAlchemy integration, as battle-tested (#284).** An orders service
  on SQLAlchemy 2.0 as a team runs it -- a 16x25 writer fleet on one row
  (gapless audit `seq`), 200 orders with two concurrent `DueTimerScanner`s
  (then 2000 rows / 4 scanners, one crashing: every key woken once), the
  outbox transactional WITH the mixin row, a relay crashing mid-batch that
  re-sends the same envelope id, `forget()` cascades, Alembic `upgrade
  head` from empty / demo / autogenerate no-diff / a team's next migration
  / `downgrade base` -- on SQLite always and on Postgres 16 (a
  testcontainer; CI's Linux `[sqlalchemy]` cell runs it)
  (`tests/contrib/sqlalchemy/test_battle_284_{scenario,a,b}.py`,
  `examples/integrations/sqlalchemy_orders/tests/test_outbox_and_readme.py`).
  Found and fixed: `StatechartMixin.send(plugins=[OutboxPlugin(
  SQLAlchemyOutboxStore)])` -- and `IdempotencyPlugin(SQLAlchemyInbox)` /
  `AuditPlugin(SQLAlchemyLog)` -- wrote their rows on a connection of
  their OWN, so an outbox row (or an inbox mark that then answered the
  redelivery as a duplicate) survived the caller's rollback; the sinks'
  store is now bound to the row's session for the send
  (`SQLAlchemyStore.bound_to`), a send inside an open
  `store.transaction()` is refused (`RuntimeError`) and a plugin store on
  another database is refused (`ValueError`). Postgres/MySQL lock
  timeouts, deadlocks and serialization failures (SQLSTATE 55P03 / 40P01 /
  40001), including on the `FOR UPDATE` refresh of `lock="pessimistic"`,
  are `LockTimeoutError` and retried by `send_with_retry` (they escaped as
  raw `OperationalError`). `statechart_state` is `Text` (was
  `String(512)`: Postgres raised `StringDataRightTruncation` on a
  12-region parallel chart while SQLite stored it silently; existing
  schemas need an `ALTER COLUMN ... TYPE TEXT` migration). Alembic
  autogenerate reported a permanent `statechart` type diff on Postgres
  (`create_all` emits JSONB, the documented `render_item` wrote
  `sa.JSON()`): `StatechartType.compare_against_backend` + the new
  `render_statechart_type` hook render the JSONB variant. `xsm_outbox` is
  part of `xsm_sqlalchemy_ddl()` (autogenerate wanted to DROP it with its
  pending events). `StatechartType` raises `SnapshotTooLargeError`
  unwrapped (not SQLAlchemy's `StatementError`) and a corrupt column is
  `SnapshotCorruptError` (not a bare `JSONDecodeError`).
  `SQLAlchemyStore(create_tables=False)` on an empty database says "run
  your migrations" instead of "no such table: xsm_schema". The example
  publishes `order.paid` through the outbox (`sync_app.py relay`,
  migration `0002`), its README commands run literally on both dialects,
  and the guide documents the outbox (at-least-once), the Alembic hook,
  the async store's lack of a shared transaction, the refusals and
  per-connection `lock_timeout`.
- **Adoption kit, as battle-tested (#309).** The first fifteen minutes
  as a newcomer has them -- the built wheel installed into a FRESH venv
  (3.9 and current), the journey page's blocks run in order against the
  installed package, `xsm new` scaffolds tested, the GitHub Action's and
  pre-commit hooks' exact command lines executed (incl. drift and a
  broken chart), the decision tree's leaves resolved, the schema and
  PyPI metadata checked (`tests/test_battle_309_adoption.py`,
  `tests/test_battle_309_docs_truth.py`; CI's `[fastapi]` cell runs the
  venv test). Found and fixed: the journey's install line omitted
  `fakeredis[lua]`, so step 5 died with a raw `unknown command 'evalsha'`
  -- the page says so and `RedisStore` now names the cure; `xsm new
  --template flask` ships (the `flask_wizard` example, file-for-file)
  and `--template django` points at the `django_approvals` example
  instead of a closed issue; the `Next: cd ...` hint quotes a path with
  spaces; `action.yml`, `.pre-commit-hooks.yaml` and the CLI guide
  pinned a `v0.14.0` that does not exist (now the shipped version, pinned
  by test); PyPI metadata gained Documentation / Changelog / Source links
  and the README's relative links are absolute; eleven stale docs
  claims corrected (the coverage gate, `meta.tools`, `meta.publish` and
  the SQLAlchemy outbox are shipped; `**[0.12.0]**` labels are 0.11.0;
  residents are ASGI-only; the Celery leaf of the tree continues; the
  operational limits box names real limits) and no guide page is an
  orphan. Touching `pyproject.toml` (the project URLs) also ran the
  weekly compat matrix on this PR, which was red on its oldest cells:
  the FastAPI OpenAPI golden now normalises what FastAPI 0.106 /
  pydantic 2.5 render differently, and the `[testing]` plugin tests
  survive pytest-asyncio 0.23 and hypothesis 6.100.
- **Codegen companions, as battle-tested (#279).** `xsm gt --with-api
  --with-models` across the whole 104-chart corpus, in-process: every
  chart that generates yields a router and models that parse, import,
  mount and document one route per event; regeneration is byte-stable;
  `--check` / `--diff` detect drift; odd event names slug into unique
  routes and `operationId`s; output dirs with spaces / unicode / `#` /
  `'`; bounded time. Found and fixed: **the generated router was weaker
  than the library's `StatechartRouter` in six ways** -- a 2 MB body was
  200 (not 413), `text/plain` was 422 (not 415), `{"wait": false}` was a
  500, `{"priority": true}` was accepted and jumped the queue, the 422
  error list was uncapped, and an idempotent replay was SAVED every time
  (three retries took the version from 1 to 3, so the original writer
  lost with 409); a per-event `authorize` denial was answered as a 403
  problem from inside the handler so the enclosing `get_interpreter`
  saved and the version bumped for a refused request -- the generated
  handlers now call `registry.send_event` under `bounded_route_class`,
  exactly the library's path (a parity table of 11 cases is pinned;
  **regenerating an older router replaces its `get_interpreter`
  handlers -- `--diff` shows it**); a payload field named `wait`,
  `priority` or `type` could never be sent (`wait`/`priority` are send
  options the registry refuses; `type` is the discriminator and silently
  took the event's name) -- refused at generation with one line; a bare
  JSON-Schema `{"type": "object"}` payload was read as a field called
  `type`; the router's `Regenerate with::` command omitted
  `--with-models` and did not quote paths with spaces, so following it
  did not reproduce the file; the header told users to call a
  `build_<name>_machine()` that no template generates; a generation
  refusal reached only the logger; `--check` / `--diff` stopped at a
  stale logic file and never reported stale companions; `--check` /
  `--diff` CREATED the output directory and imported + mounted every web
  companion (a FastAPI build per chart -- it compares text now and
  writes nothing, pinned by an mtime/bytes comparison and by a test that
  makes the web verification raise); a payload schema whose root type is
  a list (`{"type": ["object", "null"]}`) was read as a field map with a
  field named `type` and refused (a JSON-Schema root is recognised by its
  type keyword; a non-object root is refused for the right reason); `-o FILE` crashed with a traceback (exit 2,
  one line); an unrequested leftover companion (`--with-api` dropped)
  was invisible to `--check` (named in a warning); two charts with the
  same `id` silently overwrote each other's output (a warning names the
  other source); `gt` with several JSON paths hung on the "Is this
  correct?" prompt in a non-interactive run (EOF accepts the detected
  parent; `-jp/-jc` is the prompt-free path). Confirmed: odd context
  keys (`order-id`, `class`, `1st`, `model_config`) become aliased
  fields that round-trip; chart ids that clash with stdlib modules get a
  `_machine` suffix; hierarchical runs emit the parent's companions
  only; provenance banners carry basenames, never a local path.
- **Litestar integration, as battle-tested (#278).** The orders chart
  served through `create_statechart_controller` + `XStatePlugin`, driven
  the way the #275 / #276 battles drove the FastAPI surface, so every
  hardening of the shared registry is pinned here too (honest
  idempotency, gates on `authorize`, body rules that never echo, 50
  concurrent `PAY`s charge once, streams over a raw ASGI driver). Found
  and fixed: **`contrib.litestar` re-exported Starlette's
  `ReceiptResponse`, which a Litestar handler cannot return -- the
  documented `Provide` recipe answered 500** (a Litestar-native
  `ReceiptResponse` now); **`get_interpreter` answered 500 whenever it
  sat next to another dependency** -- Litestar resolves and cleans up
  generator dependencies in separate tasks, so `act()` was entered in
  one task and exited in another and the commit-scope `ContextVar`
  reset raised "Token was created in a different Context" (the whole
  `act()` now runs in one owning task; the save happens when the handler
  finishes, the change is discarded when it raises); two `Provide`s for
  one key opened two `act()`s (one interpreter per key per request, as
  in FastAPI); `Idempotency-Key` was ignored on `Provide` routes (400 /
  501 / stamped on the first send, as in FastAPI); `to_starlette` lost a
  body Litestar had already read -- `send_event` without a payload hung
  on the spent stream (the cached body is copied); `_json_guard` read a
  chunked body with no `content-length` fully into memory before 413
  (streams and stops past the limit); with `create_if_missing=False`
  `/stream` opened an endless SSE and the WebSocket accepted a missing
  key -- 404 / 1008 now, and the same gap fixed in the FastAPI router;
  registering `XStatePlugin` twice ran the registry lifespan twice;
  `dependencies=True` silently replaced a user dependency of the same
  name (`ValueError`); Litestar refuses two handlers on one path, so an
  app could not own a per-event route (the payment hook) -- new
  `exclude_events=` / `guards=` / `dependencies=` on the controller,
  with `/send` refusing excluded events; **the served OpenAPI document
  changed on every start** (random msgspec examples in `Problem`) and
  listed only 200 / 400 for every route; colliding event names
  (`ORDER.PAID` / `ORDER_PAID` / `get`) made `/schema/openapi.json`
  answer **500** and one handler overwrote the other -- the FastAPI
  battle's stable `operationId` rule now lives in `contrib/_openapi.py`
  and both routers use it; aliased event fields were 422; every 200 was
  `schema: {}` (typed `StateBody` / `ReceiptBody` / `EventsBody`); two
  machines named `a_b` / `aB` shared one body schema; 422 problems named
  the whole body instead of the unknown key and were uncapped (50 +
  `errors_total`). Parity table: the same requests through the FastAPI
  router and the Litestar controller over one registry give identical
  status codes and problem titles. `TestClient.stream` buffers SSE
  (documented: use a raw ASGI driver or `httpx.ASGITransport`).
- **Multi-worker deployment, as battle-tested (#277).** The guide's and
  the `fastapi_orders` README's claims, run against REAL `uvicorn
  --workers 4` processes plus a separate `--role scheduler` process
  sharing only the store: 200 concurrent `PAY`s charge exactly once with
  or without a shared `Idempotency-Key` (the fake gateway logs every call
  across processes: one line); 100 `ADD_ITEM`s from 4 workers converge
  after client 409 retries and the stored version equals the successful
  sends; web workers never fire timers -- the scheduler process fires
  the payment timeout exactly once, and two schedulers started by
  accident still fire each deadline once; a rolling restart leaves the
  store consistent; the README's load test reruns green. Found and
  fixed: **the Docker image could not start** (`app.py` imports
  `migrations`; the Dockerfile copied neither `migrations.py` nor
  `machine_v2.json`), its healthcheck probed `/_xsm/health` instead of
  `/_xsm/ready`, and nothing pinned the scheduler to one replica; the
  guide's "54 `409`s" and the README's "Redis" load-test rows were one
  run's number and SQLite numbers respectively (`loadtest.py` dropped
  `XSM_REDIS_URL` silently) -- replaced by measured ranges over 3–5 runs
  per worker count, a `--redis URL` flag, `--json` output with the
  `conflict_retries` the issue asked for; a request whose client sent
  headers and then stalled held a handler forever -- new
  `StatechartRegistry(body_timeout_s=30)` → `408` `RequestTimeoutError`
  (the example sets `XSM_BODY_TIMEOUT_S`); **N workers racing an empty
  SQLite file to switch it to WAL**: the loser's `database is locked`
  was instant (SQLite's busy handler does not wait for that lock) and
  the worker silently kept rollback-journal mode for its whole life --
  `SQLiteStore` retries for `busy_timeout` and re-reads the mode another
  process set; the issue's promised `/metrics` endpoint was missing
  (added; `PROMETHEUS_MULTIPROC_DIR` combines workers); the `[testing]`
  "TestClient fixtures" and the cookie-keyed wizard block in the guide
  were a promise and a fragment (corrected, executable). **Diagnosed,
  not ours:** on Windows, `uvicorn --workers N` sometimes freezes a
  worker inside `accept()` on the shared listening socket until the next
  connection arrives -- one request in a burst stalls for the whole
  client timeout while p95 is ~0.3 s; reproduced with a do-nothing ASGI
  app (7 of 25 fleets, never with one process), so no server-side
  timeout can bound it; documented in the Troubleshooting table with the
  recommendation (Linux / Docker for multi-worker; N single-worker
  processes behind a proxy on Windows), and the process-spawning fleet
  tests skip their stall-sensitive assertions on win32 and run on the
  Linux / macOS cells.
- **FastAPI integration, as battle-tested (#276).** The order service's
  FastAPI surface under misuse. Pinned on `fastapi_orders`: an
  `Idempotency-Key` dedups across retries with an inbox (replay
  `duplicate`, a different body 422 with no echoed value); a handler
  that raises after a send persists nothing and leaks no exception
  text; a `BackgroundTasks` closure holding the request's interpreter
  finds it stopped (open a fresh `act()`); `PAY` is gated on the
  registry's `authorize`, so `/send` is 403 and a second router on
  another prefix is no backdoor to the email hook; body rules (422 /
  413 / 415) never echo the value; the OpenAPI document generates in
  bounded time with unique `operationId`s and no response schema
  promising `card_token`; 50 concurrent `PAY`s under one key charge
  once. Defects found and fixed: **an `Idempotency-Key` on a registry
  without an inbox was silently ignored** -- 200, `duplicate: false`,
  three retries ran the event three times (`IdempotencyNotConfiguredError`
  → 501 on `send_event` and `get_interpreter`, which validates the
  header and hands it to `act(idempotency_key=)` so the handler's first
  send is deduped with no handler code -- also on
  `request.state.xsm_idempotency_key`); event-route `operationId`s are
  stable when an event is added later (plain names claim the unsuffixed
  id; folded names such as `ORDER.PAID` take the suffix); two
  `get_interpreter` parameters on the same key in one route gave a
  self-inflicted 409 (one interpreter per (machine, key) per request);
  `instrument_app` called twice duplicated the probe routes and nested
  the lifespan (idempotent); a `per_event_dependencies` entry for an
  event the machine does not declare was silently dropped -- a typo
  left an event ungated (`ValueError` at router build); a 10 000-item
  validation failure produced a 499 KB 422 (at most 50 errors +
  `errors_total`); **duplicate `operationId`s made the document
  invalid** (`ORDER.PAID` / `ORDER_PAID`, an event named `GET` /
  `send`; non-ASCII ids) -- ASCII-folded with deterministic suffixes;
  an `EventModel` field with an `alias` was 422 on a valid body on
  `/send`, `/events/X` and `send(Model(...))` (`by_alias=True` -- actions
  now read aliased fields under the ALIAS key in `event.payload`;
  `contrib.pydantic` is unreleased, so no published user is affected);
  fallback body schema names collided for machines named `a_b` / `aB`;
  400 / 401 / 501 / 503 problem responses were undocumented. Added: an
  OpenAPI golden (`tests/contrib/fastapi/openapi_golden.json`,
  regenerate with `XSM_UPDATE_GOLDEN=1`). Confirmed: the save commits
  BEFORE the response is sent (no acknowledged-but-lost write);
  `GET /{id}/events` evaluates guards against the live instance --
  guards must be pure (documented). Deferred from the issue, documented:
  `GET /{id}/history` (needs a log store on the registry) and the
  `/schema/*` routes (covered by `/{id}/diagram.mmd`, `/{id}/events`
  and `/openapi.json`).
- **Starlette integration, as battle-tested (#275).** The order service's
  `StatechartRegistry` under real web load. Pinned on `fastapi_orders`:
  50 concurrent `ADD_ITEM` POSTs to one order on SQLite lose nothing
  (409s retry to convergence; stored version == successful sends); 4
  `EventSource` readers plus a stalled subscriber -- the stalled one is
  cut at `MAX_BACKLOG`, the writers never wait; streams are isolated per
  order; 5 000 orders leave no per-topic state; a resident handle kept
  after LRU eviction is refused, not a silent sink; `lifespan` exit with
  a stream open and a POST in flight never hangs past `drain_timeout_s`.
  Defects found and fixed: the fan-out's per-topic `seq` lived forever
  (freed with the last subscriber); a stream opened during shutdown was
  429 (now 503); **`peek()` ran the initial state's entry actions on
  every GET / stream connect** (a pure probe now); a no-op send (an
  undeclared event, an event to a finished instance) still saved and
  bumped the version, so a concurrent real writer lost with a 409
  (skipped only when no action ran either -- a targetless
  action-only transition is saved so its outbox / audit marks flush --
  and unless an `Idempotency-Key` must be recorded or the blob needs
  the current `machine_version`); an empty instance key was
  accepted (400); a malformed `Idempotency-Key` (> 255 chars /
  non-ASCII) gave a silent 200 with the event never run (400);
  `receipt_to_status` accepted `600` / `"200"` (`ValueError`);
  `release_resident` swallowed a fenced save -- the resident's work was
  lost with a log line (raises `ConflictError`; background eviction
  still only logs); `resident()` while draining was a bare
  `RuntimeError` → 500 (new `ShuttingDownError` → 503); residents
  abandoned on drain timeout kept running (stopped); `run_timers=True`
  with an async store failed inside `lifespan` (`TypeError` at
  construction); `heartbeat_s` 0 / negative / nan made the SSE loop
  busy-spin (refused); **dead SSE clients held their connection slot
  under ASGI spec ≥ 2.4** (Starlette raises `ClientDisconnect` without
  closing the generator) -- released exactly once, and a disconnect is
  noticed immediately, not at the next 15 s heartbeat; **timer
  (`after`) transitions fired by the registry's scanner never reached
  open streams** (the scanner saves through `persisted()` in its
  thread) -- a `TimerPublisher` on the scanner's plugin list publishes
  committed receipts onto the serving loop; malformed WebSocket frames
  closed the session with 1003 and a non-UTF-8 binary frame crashed it
  (an error frame now; oversized frames close 1009); WebSocket close
  codes: 1001 on shutdown (was 1013), 1013 when cut for lagging (was
  1000), 1011 on a snapshot-load or encode failure; a peer that vanished
  during `accept()` kept its slot; an unserialisable frame killed the
  SSE stream with a traceback (logged, stream ends, slot freed). The
  SSE / WebSocket **wire contract** (frames, reconnect = fresh snapshot
  with no replay, close codes) and the per-process fan-out rule are
  documented; `registry.py` split (`_act_helpers`, `_probes`,
  `_scanner`).
- **Live inspector, as battle-tested (#274).** The fulfilment team
  watches the pipeline in the Stately Inspector and records sessions for
  post-mortems. Pinned on `eda_fulfilment`: 20 orders are 20 distinct
  sessions each ending in its own `shipped` snapshot; only allow-listed
  context leaves and the chart `definition`'s initial context is
  filtered the same way; a browser tab that never reads is bounded, cut
  and counted while a reading tab keeps receiving; a sink that raises
  never reaches the machine; a recording survives a crash mid-write; 3
  readers over 300 orders see every frame in the same order; 8 router
  threads over one sink. Defects found and fixed: the session id was
  `interp.id` -- the **chart** id -- so every persisted instance of one
  chart shared a session and the Inspector drew one actor named `order`
  with 20 orders' snapshots interleaved -- `session_id_of()` uses the
  persisted `store_key` (children re-rooted under the parent's session);
  `SseSink` kept an **unbounded** per-client queue (≈11 MB per 20 000
  events for a stalled tab) -- `max_queue=10_000`, a lagging client is
  cut (reconnect replays `history`), `dropped` / `sent` / `clients`
  exposed, `send()` never blocks; the same for the `[starlette]`
  `WebSocketSink` (`max_queue=`, close code 1013); the loopback `Host`
  check accepted `127.0.0.1.evil.com` (`startswith("127.")`) -- the
  DNS-rebinding guard now parses `host[:port]` / `[v6][:port]` strictly
  with `ipaddress`; a sink that raised produced one contained error per
  message -- reported once, then inert; `read_jsonl` raised on a
  recording whose last line was cut by a crash -- the truncated last
  line is skipped (a corrupt line in the middle still raises);
  `include_payloads=True` sent free-text payload fields through
  key-name redaction -- a card number in `PAYMENT_FAILED.reason` left
  the process -- `payload_allowlist=` (deny by default, like
  `context_allowlist`; `include_payloads=True` without it sends only
  `type` and warns once); `MemorySink(maxlen=)`; the
  pending-sends table grew with unique target ids (capped at 1 024);
  `replay_messages(Path(...))` raised `TypeError` (`os.PathLike`
  accepted); a negative / NaN `speed` was accepted (`ValueError`; the
  CLI exits 2); **`xsm sim --record` appended to an existing file** --
  two unrelated sessions replayed as one; it now refuses a non-empty
  file unless `--append` (behaviour change); `xsm replay` loaded the
  whole recording before printing (streams); `--open` on a headless box
  crashed the server (warns); Ctrl-C during `--live` could not interrupt
  the wait on Windows (slices); `JsonLinesSink.send()` after `close()`
  raised an opaque I/O error (clear `ValueError`); `SseSink(keepalive=)`
  is injectable. Documented gaps: `historyValue` is always `{}`, a
  not-started run reports `active`, no `Secure` cookie flag over http,
  HEAD/POST/OPTIONS answer 501; a `store_key` shared by two different
  charts shares a session -- keys must be unique across charts.
- **Observability, as battle-tested (#273).** The fulfilment pipeline on a
  dashboard an SRE can trust: Prometheus + OpenTelemetry on every
  interpreter the choreography router builds. Pinned on `eda_fulfilment`:
  every counter equals the audit log after clean orders, a cancel
  mid-flight and a dead-lettered poison command; 1 000 undeclared event
  types × 1 000 subjects mint one `unknown` series and the scrape stays
  under 64 KB with no order id / payload / envelope id as a label or span
  attribute; a span exporter that is down never reaches the machine and
  spans flow again when it recovers; service spans are children of the
  transition span that entered the invoking state; 8 router threads over
  one registry / one tracer sum exactly; 700 orders leave the plugins'
  bookkeeping empty. Defects found and fixed: `xstatemachine_active_interpreters`
  only decremented in `on_interpreter_stop`, so machines that finished
  (`done`), failed (`error`) or were garbage-collected pinned it forever
  (30 shipped orders → gauge 30) -- it is now **polled at scrape time**
  (count of `status == "running"`, like `queue_depth`; the two polled
  gauges are per-process and do not appear in prometheus_client
  multiprocess mode); a **cancelled invocation** (state exited while the
  service ran) fired no hook, so its OTel span never ended and a
  re-entered state restarting the same invoke `id` lost the earlier span
  until process exit -- spans of services whose owning state left the
  configuration are ended after each event (and on `on_done` /
  `on_error`) with `statechart.cancelled=true`; a tracer / Sentry SDK
  that raised produced one contained error per event -- both plugins now
  go inert after one warning; two `PrometheusPlugin`s with different
  base label sets on one registry hit `DuplicateTimeseries` --
  `ValueError` naming the conflict; `record_context=True` wrote the
  `repr()` / bytes of non-JSON context values into the span (a
  `Session(password=...)` repr leaked past `redact()`, which matches
  keys) -- opaque values are written as type tags; a context dict with
  mixed key types made the sorted dump raise after the span left the
  stack, so the event's span was never exported -- ended in `finally`;
  `StructlogPlugin` / `LoguruPlugin` kept the in-flight stack in a
  `threading.local`, which every asyncio task on one loop shares -- two
  interpreters interleaving corrupted and leaked each other's fields;
  the stack is a per-task `ContextVar`; `correlation_id` had no size cap
  (128 chars now); `LoguruPlugin(logger=<stdlib logger>)` was accepted
  and failed on every event (`TypeError` at construction);
  `instrument_all(interp)` on a running interpreter missed
  `on_interpreter_start` (replayed). **Engine:** a plugin instance
  registered globally *and* attached with `.use()` (or `.use()`-d twice)
  fired every hook twice -- the limitation documented in #305 -- and
  every metric doubled; `use()` now dedupes by identity on both engines.
  Overhead, measured once on a two-state chart (Windows, CPython 3.14;
  not a budgeted benchmark): roughly 3× with `PrometheusPlugin`, 4–5×
  with `OpenTelemetryPlugin` (SDK, no exporter), about 40 % of it the
  engine's per-event receipt.
- **Test doubles, as battle-tested (#272).** The fulfilment team runs its
  two-chart EDA pipeline with no broker. The #272 acceptance criteria
  promised `given(machine).in_state(...).when(...).then_state(...)` and
  it never shipped: `contrib.testing.given()` / `Scenario` exist now (sync
  engine, `SimulatedClock`, `from_state_ids` for the starting
  configuration; `in_state` / `with_context` / `when` / `after` /
  `then_state` / `then_not_state` / `then_context` / `then_changed` /
  `then_denied` / `then_error` / `then_no_error` / `then_done`; every
  failure names the step trail, the expectation and what was active).
  Pinned on `eda_fulfilment` with `SyncFakeBrokerAdapter`: an injected
  publish failure leaves the outbox row pending and the relay raises to
  its caller -- the next tick publishes it once (at-least-once, no
  duplicate); a four-publish partition delays but never reorders a
  subject's `OrderPaid → OrderPacked → OrderShipped`; a raising handler
  nacks without requeue and the exception reaches the test; a poison
  command is attempted exactly `MAX_ATTEMPTS` times, then dead-lettered
  and acked with nothing committed or pending; 50 interleaved orders keep
  per-subject order and every published event's `causationid` names its
  inbound cause; 8 producer threads lose nothing and the fake's counters
  balance; `assert_replay_consistent` holds for every order and a
  tampered log raises `ReplayDivergenceError`; 10 000 envelopes through
  the fake stay ordered per subject with linear memory.
  **The adversary suites then found:** the fake redelivered a
  `nack(requeue=True)` with `attempt` still 0 while every real adapter
  adds 1 -- poison tests passed on the fake for a different reason than
  on a real broker; `subscribe(timeout=)` was a TOTAL limit in the fake
  and an IDLE limit in the adapters, so a trickling producer ended the
  iterator mid-backlog; the fake handed out the SAME `Envelope` object it
  stored -- a consumer mutating `data` rewrote the `published` record and
  a nack redelivered the mutated payload (copy-on-wire through
  `to_json(max_bytes)` / `from_json` now, which also enforces the X0.4
  size cap on `publish` and `deliver`); `fail_next_publish` accepted
  `KeyboardInterrupt`, an exception CLASS and `times=0`; a handler that
  republished to its own topic made `drain()` loop forever
  (`limit=DEFAULT_DRAIN_LIMIT`); `assert_replay_consistent` read the
  store with the default `limit=1000` -- a log tampered at record 1 200
  was "consistent" (every page is read now); `upto=-1` silently replayed
  nothing (`ValueError`; `upto` is inclusive, `0` is the initial state).
  The contract suite existed only for async; `SyncBrokerContract` now runs
  against the sync fake and the real `SyncBroker` base. New: `clear()` on
  both fakes, `ReplayDivergenceError` exported from `contrib.testing`,
  `eda.DEFAULT_DRAIN_LIMIT`. In `given()`: a history id gave a misleading
  `InvalidConfigError`, `in_state()` with no ids passed through, a
  top-level final start stayed `running`, `after(nan)` was accepted,
  `when()` after `stop()` was a silent no-op, and the step trail omitted
  the given steps. pytest-bdd recipe
  (`tests/contrib/testing/bdd_order_specs/`, skipped without
  `pytest-bdd`); benchmark rows `fake_broker_10k_envelopes` and
  `given_when_then_spec` (no wall-clock budget; run `benchmarks/` to
  measure on your hardware).
- **Model-based testing, as battle-tested (#271).** The orders team's
  path tests (#269) and coverage gate (#270) were green and a refund still
  drove `total_cents` negative after a specific interleaving. `model_test`
  on the orders chart with the real `logic.build_logic` finds the planted
  bug, shrinks it to ≤ 6 steps, writes a `failing.json` that `xsm
  simulate --script` replays, and writes the same bytes twice under a
  fixed seed. The bug it found in itself: a logic **factory** was called
  once per class, so real logic with state (a gateway stub counting
  calls, a retry counter, a breaker) was shared across examples --
  Hypothesis reported `FlakyStrategyDefinition` and the planted bug
  reproduced only on the first run. The factory is now called once per
  example (`None` / a bare `MachineLogic` instance keep one build); the
  `MachineLogic` check is duck-typed so an example app importing the
  installed package pairs with a `src.` test. Pinned: 500 examples with
  `allow_denied=False` generate no engine-refused send; a payload-
  dependent guard is gated on the generated payload; `state_assertions`
  run per active parallel region; `snapshot_roundtrip` names a `set` in
  context; `clock=True` reaches the 15-minute `expired` state (coverage
  sees the `after`); 200 examples on `addressFields` and the orders chart
  finish within budget; a 12-chart corpus smoke raises no false failure
  (an `always`-looping export is the engine's `RunawayChainError`, not the
  model's).
  **The adversary suites then found:** two events whose names differ
  only in punctuation (`A.B` / `A_B`) became ONE rule name -- one event
  was silently never generated; a `raise` / `sendTo` with `delay` or a
  child's timer never enabled the clock rule (it looked only at active
  `after` keys), and with no `after` at all the rule did not exist -- it
  now advances to the next pending timer of any kind; a
  `state_assertions` key naming no state was silently ignored
  (`ValueError`); an assert-style check returning `None` failed as
  "violated" while a check raising `KeyError` escaped with no script
  written -- `None` passes, any other falsy value fails, any exception
  fails through the artefact writer; payload inference raised "cannot
  infer" for `Decimal` / `datetime` / `date` / nested models and ignored
  field constraints (`Field(ge=1)` → every send refused); a `payloads=`
  strategy producing non-dicts or a `type` key failed obscurely
  (`TypeError`). `xsm simulate --script`: a malformed script (a step
  without `send` / `clock` / `guard`, a list payload, a negative /
  infinite / non-numeric `clock`, a missing file) printed a traceback, a
  non-boolean guard `value` (`"false"`) silently INVERTED the flip, and
  `--script` with `--events` ran both so the replayed artefact was not
  the recorded run -- one-line errors, exit 2. Pinned: the file left
  after shrinking is the minimal sequence; three planted bugs
  (sequence-, payload-, time-dependent) shrink to minimal sequences
  (≤ 5 / 1 / 2 steps; exact lengths vary by Hypothesis version); 200
  examples on the orders chart with real logic take a few seconds; a
  `Decimal` in context fails `snapshot_roundtrip` on purpose, with a
  hint. **Independent review then found:** `assume()` inside an
  invariant raised `UnsatisfiedAssumption` -- an `Exception` -- and was
  reported as a failure with a script written and a non-bug shrunk;
  Hypothesis control exceptions now pass through. Field bounds
  (`Field(ge=1000, le=1001)`, `min_length`) are read into the integer /
  text strategies instead of filtering a default range that could never
  pass (`Unsatisfiable`). New benchmark row `model_test_200_examples`;
  `failing.json` is gitignored.
- **Coverage gates, as battle-tested (#270).** The orders team gates CI
  on state & transition coverage: `--xsm-fail-under-state-coverage=nan`
  was accepted (`type=float`) and every `percent < nan` is False -- the
  gate silently PASSED at any coverage; `inf`, `-1` and `101` were
  accepted too. Thresholds are now a finite percentage in `[0, 100]`
  (`argparse` error otherwise). Pinned on the shipped chart: a suite
  that only pays names `paymentFailed` and the `awaitingPayment --CANCEL`
  / `retryDelay` edges and fails the gate; `term` / `json:` / `html:`
  agree; the JSON is `version: 1` and byte-identical across runs; the
  HTML is one self-contained file; `xsm coverage` renders it and
  `--fail-under` exits 1; restored, directly-built and rebuilt
  interpreters all count (one row per structure key); parallel
  configurations mark leaves and ancestors; history pseudo-states are
  not in the denominator; nothing is registered without the flag; `-n 2`
  matches serial.
  **The adversary suites then found:** the collector kept EVERY machine
  build and its transition index alive for its lifetime -- a session that
  rebuilds a chart per test grew without bound (3 000 builds → 3 000
  entries); one representative build per key is kept, later builds are
  held weakly, and a recycled `id()` can never land in a stale index. The terminal summary put every unvisited state /
  unhit edge on one line (500 edges → a 20 kB line); lists are capped at
  `TEXT_LIST_LIMIT` (20) with "... and N more" (JSON / HTML keep the full
  lists). `below()` accepted NaN (the gate silently off) -- `ValueError`
  outside `[0, 100]`. Report options / thresholds without
  `--xsm-coverage` were silently ignored (usage error now); a set
  threshold PASSED when no machine was observed (`-k` matched nothing) --
  it fails; an unwritable report path was an INTERNALERROR traceback;
  `--collect-only` wrote files and gated; a run stopped by `-x` gave no
  sign the numbers were partial; a crashed xdist worker is now named in
  the summary (not a `warnings.warn` that `-W error` turns into an
  INTERNALERROR). Honest numbers: the denominator is
  *statically declared* -- on 30 corpus charts 105 of 731 targets can
  never be hit (shadowed `always` alternatives, inline-actor invoke
  outcomes the stubs cannot drive, named `after` delays with no
  implementation, states no event sequence reaches, self-target `on`
  handlers that generated paths skip), so 100 % transition coverage may
  be unattainable on a real chart -- gate on states, or on a transition
  threshold below 100; and the session collector costs ≈1.4-1.7× on
  `send()` throughput, about three quarters of it the engine's generic
  plugin dispatch (a no-op plugin costs ≈34 %), the collector's own share
  ≈10 %.
- **The pytest plugin, as battle-tested (#268).** A team adopting
  `[testing]` for the orders chart (real logic through the dotted
  factory, snapshot files in git, `pytest -n 4`): `xsm gt -t pytest
  --fixtures` emitted a `CONFIG_PATH` with a bare `with_name()` while the
  plain variant already fell back to the parent directory -- the
  generated module could never find its chart from the documented
  `-o generated/` layout; a misspelt name in `xstate_guards_false` was
  silently accepted (the test exercised the True branch while claiming to
  force False) -- unknown guard names are a usage error naming the known
  ones; `--xsm-update-snapshots` wrote wherever a relative path with
  enough `..` pointed -- snapshot paths outside the rootdir are refused
  (X0.10). Pinned: snapshot files are byte-identical across update runs
  and under `-n 4`, a `Decimal` / tz-aware `datetime` context renders
  deterministically, `"+nan"` / `"+-5"` / `"+inf"` in `xsm_send_all` are
  errors not hangs, `-p no:xstate_statemachine` leaves a marker-less
  module untouched.
  **The adversary suites then found:** `--xsm-coverage` under
  pytest-xdist always PASSED -- workers collected, the controller printed
  "(no machines observed)" and gated nothing; workers now ship reports to
  the controller, which merges, prints, writes and gates once (same JSON
  as a serial run). `model_test` failed falsely on a chart whose root
  reaches a final state (event rules stayed enabled after `done` →
  `InterpreterStoppedError`) and on an `always` that returns to the same
  configuration ("generated a denied event" after `can()` accepted it).
  `FakeBrokerAdapter.deliver()` accepted a non-`Envelope` and failed later
  inside the consumer (`TypeError` at the call now); `SyncFakeBrokerAdapter`
  / `BrokerPublishError` are exported from `contrib.testing`. In the
  plugin: a logic module raising anything but `ImportError` escaped as a
  traceback (one usage error naming file:line); `logic=` now also takes a
  `MachineLogic` instance or a zero-arg callable; context **sets** rendered
  in hash order so a snapshot recorded under one `PYTHONHASHSEED` failed
  under another (sorted lists); two tests writing different content to
  one snapshot path silently last-won (refused); Windows `\?\` resolved
  paths were intermittently refused as "outside the project"; snapshot
  writes are atomic (temp + `os.replace`, LF). `xsm_send_all` /
  `xsm_asend_all` gain a payload form (`Event`, `{"type": ...}` dict,
  `("TYPE", {...})` tuple) and refuse `""`, `"A,B"` and `"++5"` (the empty
  string sent nothing, the comma sent two events, `++5` advanced 5 ms).
  `xsm gt -t pytest` on a chart the engine rejects exits 1 with one line
  instead of a traceback. `pytest_plugin.py` split into `_marker.py` /
  `_snapshots.py` (public import path unchanged). Perf row
  `pytest_plugin_per_test` (p50 ≈ 1.1 ms); testing guide gains a Fake
  broker section, coverage-under-xdist, `model_test` invariants/deadline
  notes, `--xsm-failing-dir`, threat-model notes (a marker's `logic=` is
  code; diffs print context unredacted) and six Troubleshooting rows.
  **Independent review then found:** the same-path-different-content
  snapshot refusal lived in a per-process stash, so under `-n 4` two
  WORKERS writing one file still last-won silently -- a file written
  this session that already differs on disk is now the same refusal; a
  crashed xdist worker's coverage vanished without a word (one
  `RuntimeWarning` names the worker); the marker help and the guide still
  said `logic=` must be a dotted string; the guide now lists what a
  snapshot deliberately does NOT record (history, actors, pending /
  scheduled events, deadlines).
- **Path generation, as battle-tested (#269).** The explorer replayed
  the WHOLE prefix for every candidate edge -- O(depth) engine runs per
  edge: the 35-state parallel `addressFields` chart (3 456
  configurations) took 60 s and a 53-state / 78-guard chart under
  `guards="both"` 137 s. Prefix end-states are now cached as snapshots
  and restored per candidate (`restart_timers="resume"` on a clock that
  shares the original's wall origin -- the default leaves `after`
  deadlines dormant; restored under the last step's forced assumptions
  -- `start()` re-runs `always`, so a configuration stable only while a
  guard is forced False moved on under the all-True stubs), and guard
  flips are scoped to the candidate's own event (a guard on `on 'X'`
  cannot change `send('Y')`). Results are byte-identical on 100 corpus
  charts in every mode; the two charts run in 34 s and 39 s. A forced
  `service:<name>=error` step no longer logs an ERROR traceback per
  generated test under `xsm_path`.
  **The adversary suites then found:** the cache stored a snapshot per
  EDGE (19 000 on `addressFields`), overflowed its cap and fell back to
  replay -- 77 % hit rate; BFS now caches the first path into each
  configuration (≈100 %, 35 s → 19 s). Wildcard handlers (`"*"`,
  `"mouse.*"`) were skipped, so a state reachable only through one was
  "unreachable". No bound on configurations: `max_configs=100_000`
  (`ExplorationLimitError`, partial result on `.found`); negative
  `max_depth` / `max_paths` / `max_configs` are `ValueError`. `stubbed()`
  swapped `machine.logic` on the CALLER's machine -- a live interpreter on
  it took a transition its real guard forbids while a traversal ran; the
  explorer now works on a private copy, and the logger-level guard is
  re-entrant (two overlapping traversals could leave the library logger
  muted). `xsm_path`: a chart that cannot start aborted the whole
  collection with a traceback (now one `path[error]` case per test);
  two functions on one chart explored it twice (cached per session);
  negative `--xsm-max-*` are usage errors. `xsm paths`: a chart that
  cannot be explored exits 1 with one line; `--weight steps|time` added;
  negative bounds exit 2; every printed path's `event_string()` fed to
  `xsm simulate --events` lands on the same states (102 corpus charts).
  `xsm simulate --events`/`--clock`: `+-5`, `+abc` crashed, `+inf` /
  `+nan` / `+1e309` printed invalid JSON -- all exit 2. `xsm inspect` /
  `validate` called entered states "unreachable": the static pass marked
  only a transition's target, not the ancestors (and parallel siblings) a
  deep `#id` / history target enters -- 16 false warnings removed, none
  added. Docs: an UNDEFINED named delay is skipped (only one in
  `logic.delays` yields `delay:<name>=unknown`).
  **Independent review then found:** the cache-parity tests patched a
  re-exported copy of the cache cap, not the one the explorer reads --
  every "cache ≡ replay" assertion compared the cache with itself (the
  parity claim above was re-established after the fix); a named `after`
  delay advanced the clock a fixed 10⁹ ms and fired every later timer in
  the same step, so `a --after slow--> b --after 300--> c` reported only
  `{a, c}` -- it now advances to the earliest pending deadline; a step the
  engine refused or contained (`maxIterations`) vanished silently -- one
  `RuntimeWarning` per traversal names it; `reachable_states` gains
  `max_configs`; `graph.py` split into `graph` / `_graph_model` /
  `_graph_explorer`.
- **Typed boundary, as battle-tested (#266).** A chart whose static
  `context` the `context_model` refuses **built and started** -- the
  `TypedContextPlugin` raise is contained by the plugin system -- and then
  rolled back every mutating action forever. `create_machine` now refuses
  it (`InvalidConfigError`, field path, never the value) when the
  validator is a model validator (a plain callable keeps the #305
  "after mutations only" contract); a bad *restored* context puts the
  machine in `status == "error"` with the `ContextValidationError` as
  `interpreter.error`. `{"type": 1}` actions and list / non-string
  transition targets escaped the parser as a bare `AttributeError`; both
  the static gate (`ActionObject`, `TransitionConfig.target: str`) and
  the parser report `InvalidConfigError` with a path (multi-target lists
  are not implemented and now say so). `contrib.fastapi.instrument_app`
  maps **every** `RequestValidationError` -- including routes the app
  adds beside the generated router -- to the 422 problem shape (field
  path + error type, never the offending `input`; X0.7).
  **The adversary suites then found:** `context_model(write_back=True)`
  put nested model INSTANCES into the dict, so `get_snapshot()` stored
  `"sku='a' qty=2"` -- an unrestorable snapshot; write-back now uses
  `model_dump(mode="python")` (plain dicts, `Decimal` / `datetime`
  kept). A rejected value -- a card token failing validation -- rode in
  pydantic's error text (`input_value=`) into `logger.exception` and
  `InvalidEventPayloadError`'s message; `ContextValidationError` and the
  payload error are now rebuilt value-free (path, type, message; X0.5).
  `persisted()` / `apersisted()` / `persisted_retry` ran the block and
  then **saved** a terminal `status: "error"` snapshot over the record
  when `TypedContextPlugin` had just failed a restored machine; they now
  raise the `ContextValidationError` before the block and write nothing.
  `PydanticCodec` stored a context the model refuses silently; it still
  stores it (refusing would lose state) but emits a `RuntimeWarning`
  naming the field paths. `create_machine`: a non-numeric
  `maxIterations` / `spawnBlockingTimeout`, a non-object `states` on an
  initial-less compound, and a chart nested ~600 deep are
  `InvalidConfigError` (were bare `ValueError` / `TypeError` /
  `AttributeError` / `RecursionError`). `validate_machine_json` refuses
  what the engine refuses -- a non-object `context`, duplicate custom
  state `id`s, string `strict*` flags (the parser read `"false"` as
  true) -- takes `bytes` and a BOM, reports malformed JSON and duplicate
  JSON keys as `InvalidConfigError`, prints list paths as `PAY[0].target`,
  and names its ~95-level nesting cap; gate ⇔ parser parity holds in
  BOTH directions on all 168 shipped charts and a seeded 600-mutation
  fuzz. `machine_json_schema`: same-named nested models in the event and
  context schemas no longer overwrite each other's `$defs`;
  `x-leaf-states` omits history pseudo-states; a union member without a
  `Literal` `type` is a `TypeError`. `[fastapi]` gains
  `bounded_route_class(registry)` -- the router's 413 / 415 / value-free
  422 for routes added beside `StatechartRouter` (the orders example's
  `PAY` route parsed a 1 MB body and answered 422). `event_type_of`,
  `ActionObject` / `ActionSpec` are exported from `contrib.pydantic`.
  **Independent review then found:** the scrubbed error still carried
  the value through `ctx["error"]` (a `ValueError` from a
  `field_validator`) and a `PydanticCustomError`'s interpolated message;
  `ctx` is now allow-listed to rule keys (`max_length`, `expected`, ...)
  and free-text error types get a fixed message. Write-back raised
  `KeyError` on a field with `exclude=True`. And a machine failed by a
  start hook still **entered its initial states** -- entry actions,
  services and timers ran on the refused context (the async run loop
  stayed alive); both engines now return from `start()` without
  entering anything. `instrument_app` no longer replaces a
  `RequestValidationError` handler the app registered first.
- **`FileStore.lock()` is fair within a process (battle-test #306, CI).**
  Sixteen threads spinning on the OS file lock with sleeps was a lottery:
  one waiter could lose every draw for the whole `timeout` (4 of 16 hit
  `LockTimeoutError` at 30 s on the Windows runner). Same-process waiters
  now queue on a per-key `threading.Lock` first; the OS lock arbitrates
  only across processes. `LockTimeoutError` still names the holder.
- **`RedisStore` / `AsyncRedisStore` (battle-test #306, the store).**
  A key containing `|` woke the wrong instance from `due_keys` (the
  deadline-index member was `key|field`, split on the first `|`);
  members are now JSON arrays and the namespace schema marker is **2**
  (a namespace written by a pre-release build is upgraded in place and
  its members still read; the `[redis]` extra has not shipped, so no
  released version is affected). Snapshots expired by `ttl_s`
  left their index members behind and, `limit` of them, starved every
  live due key -- they are now pruned atomically. A Redis outage while
  *taking* a lock escaped as a raw `redis.ConnectionError`; it is now
  `StoreUnavailableError`. A damaged record or schema marker raised a
  bare `KeyError` / `ValueError`; now `SnapshotCorruptError` /
  `StoreError`. `lock_ttl_ms=0` and sub-millisecond / negative `ttl_s`
  are refused at construction. URL-built clients get 5 s socket
  timeouts (`DEFAULT_SOCKET_TIMEOUT_S`), overridable in the URL.
  `AsyncRedisStore` had drifted from the sync store: it now checks the
  schema marker, refuses a non-`str` snapshot / negative
  `expected_version` / negative `limit`, wraps codec failures, hides
  planted invalid keys from `list_keys`, validates `lock()` arguments,
  and gains `due_keys`. `health()` never raises.
- **`RedisInbox` / `RedisLog` (battle-test #306).** Found by a two-host
  fleet attack before the extra shipped: inbox expiry used each worker's
  `time.time()` (a slow host wrote an already-expired claim and a peer
  re-admitted the key -- a second charge); `mark(ttl_s=None)` after a
  TTL'd claim left the claim's expiry in the index, so `purge_expired`
  deleted a permanent receipt; a scope containing `|` was never purged;
  `forget(scope)` and `len()` were not atomic / glob-safe. The log let 32
  concurrent appenders mint 640 records with 37 distinct `seq`s, accepted
  a duplicate `append`, raised a bare `JSONDecodeError` / `AttributeError`
  instead of `LogCorruptError` / `TypeError`, accepted `limit=-1` and a
  NaN purge cutoff, and scanned the whole stream for every page.
- **Flask: one WARNING line per request for a store outage (battle-test
  #306).** `problem_response` logged a full traceback for every `503
  StoreUnavailableError` -- thousands per second during a Redis failover;
  the Starlette registry already logged one line. An unknown `500` still
  logs the traceback.

- **A circuit breaker could close without a probe (battle-test #265).** A
  call admitted while *closed* that reported SUCCESS after the circuit
  had opened and half-opened closed it; a late FAILURE likewise re-opened
  it. Every admission now carries a window token and an outcome from an
  earlier window (or from before `reset()`) is dropped. Exactly
  `half_open_max_calls` probes are admitted under 32 / 128 / 512 threads
  and 500 async tasks.
- **`RetryPolicy.exponential_ms` overflowed** with `OverflowError` for
  `factor=1e6` or `attempt=10**6`; it returns the cap. Decorrelated jitter
  with a NaN or negative previous delay is guarded.
- **`DeadLetterStore.put` was O(n)** per insert; 100 000 records are now
  bounded. One plugin shared by many never-stopped interpreters leaked
  their chains; the in-memory fallback is weakly keyed.

- **`PessimisticLock` + `DueTimerScanner` timed out on its own lock
  (battle-test #264).** The scanner takes the strategy's lock, then
  `persisted()` inside the wake tried to take it again -- on Memory,
  File, Django and SQLAlchemy stores (whose locks are not re-entrant)
  every key, every tick, was a `LockTimeoutError`. The inner block now
  reuses the held lock.
- **A scanner could count a phantom wake (battle-test #264).** Under
  `OptimisticLock` another scanner could fire the key *after* our re-check
  but *before* `persisted()`'s own load; we then loaded a record with
  nothing due, saved a no-op `version + 1` and reported `woken`. The save
  is now fenced on the version the re-check saw: `ConflictError` ->
  `skipped_stale`. Exactly-once per deadline is asserted under 8 threads
  and 4 processes on every store, both locks.
- **`restart_timers=False` left an orphan deadline (battle-test #264).** A
  parked deadline whose state was then exited stayed in
  `pending_deadlines()`, was re-persisted, and every scanner tick on that
  key raised `StateNotFoundError`. Exiting a state drops its parked
  record too.
- **Child actors lost their persisted timers (battle-test #264).** Child
  restores received `restart_services` only: a child's `after` never
  re-armed, and a restored child ran on the real clock under a parent on
  a `SimulatedClock`. The sync engine never started restored children at
  all.
- **Building machines from one config in several threads raised a false
  `InvalidConfigError` (battle-test #264).** The #136 "aliased cycle"
  guard was one module-level set shared across threads; 1 035 of 2 400
  parallel `create_machine` calls tripped it. The guard is per build.
- **`DjangoModelStore.save` maps "database is locked" to
  `LockTimeoutError`** as `DjangoStore` already did; a raising fence in
  `persisted()` now releases the idempotency-inbox claims it was holding.

- **The web registries' READ paths ignored the migrator (battle-test
  #263).** `StatechartRegistry.peek()` (GET, SSE connect, WebSocket
  snapshot) and both Flask / Quart `peek`s restored without
  `migrator=`, so a v2 deployment that carried the migrator still
  answered **409** to every read of a v1 instance until something *wrote*
  to it. Reads now migrate like writes and stay read-only (the next write
  re-saves at the new label). Found by the `fastapi_orders` rolling
  upgrade on its first run.
- **`apersisted()` saved a torn state -- or refused to save -- on charts
  with chained services (battle-test #263).** See `await_settled` under
  Added: two plain `def` invokes in a row were `SnapshotMidStepError`; an
  `async def` invoke armed by the block's last event was *saved with the
  task in flight* and restored dormant (review H1).
- **`xsm snapshots --stale` was wrong and O(n · blob) (battle-test
  #263).** `--limit` capped the keys *scanned*, so stale keys past the
  first 1 000 were silently missing from the drain list; every key's full
  snapshot was loaded to read a label the store has as a column. Now:
  the label index is scanned for every key and the limit caps output;
  10 000 keys with 100 stale on SQLite take 0.10 s (was 1 000 loads and
  wrong). A key containing a newline no longer splits a table row (control
  characters are escaped; `--json` keeps them verbatim); a non-machine
  JSON, an unreadable store or a 200 000-deep `[[[[` are a one-line error
  and exit 2, not a traceback; `--json` never includes `context`.
- **Typed errors on the versioned restore path (battle-test #263).** An
  `actors` record without `snapshot` was a bare `KeyError`; a `deadlines`
  record with a NaN / ±inf `due_at_wall` escaped as `ValueError` /
  `OverflowError`; both are `SnapshotCorruptError`. `register(1, "1")`
  stored a self-loop that matched nothing and int labels never matched
  (`can_migrate("o", 1, 2)` was `False`): labels compare as strings.
  `AsyncSQLAlchemyStore` and `AsyncRedisStore` skipped the label type
  checks the sync stores apply.

- **Audit records could land for steps that never committed (battle-test
  #262; a crash-consistency guarantee).** Records were appended as each
  event settled, BEFORE the snapshot save -- so a lost optimistic attempt,
  a block that raised, or a writer killed before the save all left audit
  rows the snapshot did not have. Records are now buffered per
  `persisted()` block and released at the save: inside the same
  transaction when `SQLiteLog` shares the store under `PessimisticLock`,
  via `after_commit` otherwise. Killed-child tests pin that log and
  snapshot agree (or the snapshot is one step ahead, never behind).
  `apersisted` + `PessimisticLock` + a shared `SQLiteLog` wrote NO records
  at all (the flush ran on the loop thread while the adapter's worker held
  the transaction -> `LockTimeoutError`): the flush now runs on the
  adapter's thread.
- **`seq` is assigned atomically by the log store (battle-test #262).**
  `NoLock` with 8 threads hit `UNIQUE constraint failed` and the plugin's
  error handling swallowed it -- audit rows silently went missing (the
  handover's listed limitation). New `TransitionLogStore.append_next()`
  mints `MAX(seq)+1` and inserts in one statement; gap-free under every
  lock and across two processes.
- **`replay()` was not faithful (battle-test #262).** `raise` chains,
  events an action sent to itself and re-released deferred events were
  re-sent, so steps ran twice; a top-level `final` was never reached; seq
  gaps, a purged head and mixed instance keys were accepted silently; a
  `machine_version` mismatch was ignored; checks ran per group, not per
  record; real services ran again under `logic=`; `after` timers never
  fired when called from async code. New `TransitionRecord.origin`
  (external / internal -- only external records are re-sent), per-record
  verification with `ReplayDivergenceError.field`, `key=` and `snapshot=`
  parameters, services always replayed from the record, timers drained
  synchronously. An action raising under `actionErrorPolicy: "continue"`
  is now recorded as `"error"`, not `"transition"`.
- **Log stores raised bare exceptions on damaged records (battle-test
  #262).** A torn last line (writer killed mid-write), a non-record line,
  non-UTF-8 bytes, a string `seq` silently coerced, NaN `ts` accepted, a
  `from_states` string split into characters -- `json.JSONDecodeError`,
  `KeyError`, `TypeError`, `UnicodeDecodeError`, `sqlite3.*` escaping
  `read()` and `replay()`. Every one is now `LogCorruptError` (a
  `StoreError`) naming `path:line`, never a skip: a replay over a hole
  would succeed to a wrong state.
- **`purge_older_than(NaN)` erased the whole log (battle-test #262)** --
  every `ts >= NaN` comparison is false. NaN / -inf / non-numbers / bools
  now raise `ValueError` and delete nothing. `read(limit=-1)` dropped the
  last row on Memory/JSONL and meant "unlimited" on SQLite -> uniform
  `ValueError`. A failed JSONL purge rewrite stranded a `.tmp` and never
  fsynced -> atomic, fsynced, cleaned up. `append()` rejects a non-record /
  `seq < 1` / non-finite `ts` at the call site.


- **The idempotency inbox's exactly-once claim did not hold under crash and
  concurrency (battle-test #261; four of these broke a stated guarantee).**
  - Mark buffers were ONE list shared by every `persisted()` block using
    the plugin: block A sent `ka` and crashed before saving while block B
    exited cleanly in between -- B's flush wrote A's mark, and every
    redelivery of `ka` got "duplicate" for an effect that was never saved.
    Buffers and the `buffer_marks` switch are now per session (thread AND
    asyncio task).
  - With `MemoryInbox`, a kill after the save left the restart with an
    empty inbox; the redelivery ran the action a second time on a
    committed save. The snapshot now carries, for each key in its ring,
    *when* it was processed and with which fingerprint; within `ttl_s`
    that answers the same payload as a duplicate and a different one as
    422, and repairs the inbox. Old snapshots keep the old behaviour.
  - `on_before_send` was fail-open: an un-fingerprintable payload, a
    hand-edited cached receipt, an inbox that raised, or a SQLite lock
    timeout (always the case for `apersisted` + `PessimisticLock` + a
    shared `SQLiteInbox`) ADMITTED the event with no claim, so every
    redelivery ran again. Each now refuses with a typed receipt; a
    malformed cached receipt becomes a conservative duplicate with a
    warning.
  - A TTL purge between claim and mark made SQLite's mark an `UPDATE`
    that matched nothing (redelivery ran again) and `MemoryInbox` write
    a row with an empty fingerprint (bogus 422). The mark re-claims with
    the real fingerprint.
  - `on_interpreter_stop` released EVERY pending claim on the plugin,
    other interpreters' live claims included. Claims are tagged with
    their interpreter.
  - A plugin registered AFTER the inbox that refused the event in
    `on_before_send` (a rate limiter, maintenance mode) left the inbox's
    claim in flight -- **409 for the whole TTL** (7 days) for an event
    the machine never saw (independent review H1). New `PluginBase.
    on_event_refused(interpreter, event, receipt)` fires on the plugins
    that had already said "proceed"; the inbox releases its claim there.
  - `ttl_s=-1`, `nan`, `"7"` and `True` were accepted silently (negative /
    NaN made every key expire instantly -- dedup off with no error).
    `ValueError` at construction.

- **`persisted()` / `apersisted()` could not restore a compatibly-drifted
  snapshot (battle-test #260).** The docs listed `verify_machine_hash` and
  `expected_machine_hash` as pass-through to `from_snapshot`, but neither
  was in the signatures -- `persisted(..., verify_machine_hash=False)`
  raised `TypeError`. Both are now accepted by `persisted`, `apersisted`,
  every `LockStrategy.run()` and forwarded. A different *machine id* is
  still always refused (identity, not hash).
- **`after_commit` dropped later callbacks when one raised (battle-test
  #260).** An outbox publish registered after a raising callback silently
  never ran. Every callback now runs; the first error is re-raised; the
  save is already durable. `async def` callbacks are awaited inside
  `apersisted()` and refused with `TypeError` under `persisted()` -- before,
  they were created and never awaited. A nested `persisted()` on a
  **different** key now runs its callbacks at its own exit (its save is
  its own commit); they used to wait for the outermost block and were
  dropped if that block later failed -- a committed state change with no
  published event (independent review M2).
- **`apersisted()` leaked a worker thread per call on a sync store
  (battle-test #260).** The `as_async` adapter it created was never
  closed; each cycle left an `xsm-store` thread alive until GC. Closed on
  exit, success or error -- off the loop, since `close()` is a blocking
  executor join that would otherwise stall every other task (review M1).
  The default `OptimisticLock.run` also forwarded only three of the five
  restore arguments, dropping `verify_machine_hash` /
  `expected_machine_hash` it had just accepted (review H1) -- fixed.
- **`lock=` validation (battle-test #260).** A non-strategy (`"none"`,
  `5`) failed mid-block with `AttributeError: 'str' object has no
  attribute 'acquire'`; now `ValueError` naming `OptimisticLock` /
  `PessimisticLock` / `NoLock` before anything runs. `OptimisticLock`
  rejects a non-int `retries` (bool included) and a non-`RetryPolicy`
  `backoff` with `TypeError`, and a negative `retries` with `ValueError`
  (`1.5` used to be silently truncated to `1`).

- **Two stores could report a successful save that was lost (battle-test
  #259; both break the "never a lost update" guarantee).**
  `SQLiteStore`: a failed `COMMIT` (disk full, `database is locked`) left
  the connection mid-transaction, so every *later* save on that thread
  joined the dead transaction, returned a version, and was never
  committed. `as_async`: a task calling `save()` while another task held
  the adapter's pessimistic lock ran *inside* the holder's transaction and
  was rolled back with it -- `save` returned 1, `load` returned `None`.
  Fixes: `_commit_or_rollback` with typed errors; calls from other tasks
  wait while a lock is held on that adapter. Regression tests inject the
  failed commit and the interleaving.
- **`as_async` pessimistic locks did not exclude** (battle-test #259):
  five concurrent `apersisted(..., PessimisticLock)` tasks on Memory/File
  got four `LockTimeoutError`s and an 8 s stall; on SQLite no exclusion at
  all. Lock holders now queue on the loop, one per adapter, bounded by
  `timeout`.
- **`FileStore` lock waits could spin forever** (battle-test #259): a live
  holder slower than `stale_lock_after` skipped the deadline check, so
  waiters ran at 100 % CPU and ignored `timeout`. Deadline first.
- **A legal 200-character key crashed `FileStore`** (battle-test #259):
  CJK or `"A"*200` percent-encodes to 600-1 800 characters -> raw
  `OSError`. Encoded names over 200 chars now use `~<sha256>`; `list_keys`
  recovers the key from the record.
- **`FileStore` readers blocked writers on Windows** (battle-test #259):
  the store's own `open()` held a share lock, so a reader in a loop
  exhausted the writer's retry budget -> `PermissionError`. Readers use
  `FILE_SHARE_DELETE`; a refused rename falls back to POSIX-semantics
  rename.
- **Damaged store records raised bare exceptions** (battle-test #259): a
  text or negative `version`, NaN `updated_at`, malformed deadline row, a
  BLOB snapshot, a directory where the record file should be, a non-SQLite
  file, a foreign `statecharts` table -- `ValueError` / `TypeError` /
  `OSError` / `sqlite3.DatabaseError`, all escaping `except StoreError`.
  Every one is now `SnapshotCorruptError` or `StoreError` (the SQLite
  constructor included). Codec failures, lone-surrogate keys/snapshots and
  bad `save()` arguments are typed identically on all three backends;
  `list_keys` skips keys `load` would refuse; a crashed writer's `.tmp-*`
  files are swept at construction.

- **The `[web]` extra was empty (battle-test #258).** `pip install
  "xstate-statemachine[web]"` installed nothing, although every member it
  was documented to bundle (FastAPI, Django, DRF, Flask, SQLAlchemy) had
  shipped. It now equals that union; a test pins `[web]`, `[eda]` and
  `[all]` to the unions their comments name. Also from the same pass:
  the `[format]` floor said `black>=24.0`, a version PyPI never published
  (Black 24 starts at 24.1.0); the `contrib` registry listed only
  `litestar` for the Litestar extra although the package also requires
  `starlette`, so the extras-matrix blocking test never blocked it;
  `xstate_statemachine.exceptions` had no `__all__`; the Integrations
  pages still called the shipped broker adapters "planned" and never said
  *when* `MissingExtraError` is raised (at import for subpackages; on
  first use for the structlog / loguru / Sentry / LangChain plugins and
  the Hypothesis helpers). Every extra's floor is now checked against PyPI
  for existence and a 3.9-compatible file, and `[all]` is dry-run
  installed as one set.

- **Competitor benchmark numbers were not like-for-like (battle-test
  #307).** Our parallel-regions adapter sent one event per iteration where
  every other adapter sent two, inflating the published "7.5x" over
  `transitions` to exactly double its true value -- it is **3.8x**.
  python-statemachine's nested adapter sent three events per iteration
  where the others send two, understating it by 1.5x -- our "10.3x" is
  **7.0x**. Construction and 1 000-instance rows, published as 1.19x and
  1.10x wins, are a **tie** within +/-3 % over six interleaved runs on
  0.11.0. README, landing page, `benchmarks/competitors/README.md` and
  `results.json` carry the corrected numbers.

- **Security (battle-test #303, X0 baseline).** An adversarial pass over
  every X0 row, both engines, with the attacks pinned as tests in
  `tests/test_battle_303_x0_core.py` and
  `tests/test_battle_303_x0_integrations.py` (named in the X0 table on the
  Security page). Findings, most severe first:
  - **Idempotency scope pooled unauthenticated callers (HIGH, X0.1/X0.2).**
    A `principal=` callable returning `None` or `""` became the shared
    scope `"None"` / `""`, so every such caller could replay every other's
    receipt. The principal must now be a non-empty `str`; anything else is
    refused with a receipt, never pooled. The independent review found the
    web adapters `str()`-coerced the principal first (`None` -> `"None"`),
    so the rule is enforced at the adapters too -- see Changed.
  - **Idempotency scope join was not injective (HIGH, X0.2).** Principal
    `alice/c` + machine `c` collided with principal `alice` + machine
    `c/c`. Each scope part now escapes `%` and `/`; parts without them are
    unchanged, so existing inbox rows keep their scope.
  - **`send()` options accepted from a client JSON body (HIGH, X0.7).**
    `{"priority": true}` posted to the Starlette / FastAPI / Litestar /
    Flask / Quart / WebSocket send routes really did jump the queue, and
    `{"wait": false}` produced a 500 `TypeError`. A body naming a reserved
    `send()` key is now 422 `ReservedKeyError`; Django's
    `RESERVED_PAYLOAD_KEYS` gains `priority`.
  - **`FileStore` parsed before it checked the size cap (X0.4).** The read
    is now bounded before `json.loads`; an 8 MB file of spaces is refused
    in well under a second without ever being parsed.
  - **Deep nesting / non-UTF-8 escaped as bare exceptions (X0.4).** A
    100 000-deep `[[[...]]]` raised `RecursionError`, non-UTF-8 bytes
    `UnicodeDecodeError`, a BLOB row `AttributeError` -- all from inside
    `except XStateMachineError`. Each is now `SnapshotCorruptError`.
  - **`SQLiteStore.forget()` left a co-located transition log (X0.5).**
    Log rows for the key are now deleted in the same transaction; the
    result dict gains `log_entries`.
  - **`redact()` missed hyphenated header keys (X0.5).** `x-api-key` and
    `Api-Key` passed through because the denylist is spelled with `_`;
    keys are now normalised before matching.

- **A context that cannot be deep-copied no longer kills the run loop
  (battle-test #305).** Receipts, `on_event_processed` and the
  `context_validator` dirty check all took a raw `copy.deepcopy(context)`
  before-image. A context holding a lock, socket or client made the async
  `send(wait=True)` hang forever (the exception killed the loop, status
  went `"stopped"`, the receipt never resolved), made the sync
  `send(wait=True)` raise `TypeError`, and made *every* action raise once
  any `context_validator` was configured. Both engines now go through
  `_context_before_image()` / `_context_changed()`: an uncopyable context
  is treated as "changed", so receipts resolve and the validator runs.
  `actionErrorPolicy: "rollback"` / `"fail"` still need the copy and still
  raise -- documented on the Context page.
- **`SyncInterpreter.send_threadsafe()` can no longer lose an event
  silently (battle-test #305).** Three cases were silent: an event posted
  after `stop()` sat in the mailbox forever; events still queued when
  `stop()` ran were discarded; events queued *behind* one that drove the
  machine to `final` in the same drain were thrown away by the finished
  machine. Each now fires `on_event_dropped` (`"not_running"` /
  `"stopped"`) and logs a warning. A producer's event is always either
  run or reported.
- **A snapshot whose `version` is `Infinity` raised a bare `OverflowError`
  (battle-test #305).** `json.loads` accepts `Infinity`/`NaN`; `int(inf)`
  overflows. `check_version` now maps it to `SnapshotCorruptError`, closing
  the last gap found by flipping, truncating and inserting every byte of a
  v4 blob on both engines.

- **`stub_logic()` missed composite guards written in `children` form
  (battle-test #304).** `{"type": "and", "children": ["c1", ...]}` is
  accepted by the engine, but the stub read names from the raw dict with
  the CLI extractor, which only knows `params.guards` -- so the leaf guards
  were unstubbed and the first send raised `ImplementationMissingError`.
  Names are now read from the parsed `MachineNode`. In the same change an
  invalid config passed to `stub_logic` raises the exact `InvalidConfigError`
  `create_machine` would, instead of a misleading `TypeError` from
  `dict(...)` or a silent empty stub.

- **The nightly perf job went red on a runner with a different CPU model.**
  Hosted `ubuntu-24.04` runners are not pinned to one CPU: a run that
  landed on an EPYC 7763 measured every row a uniform ~1.33x over a
  baseline recorded on an EPYC 9V74 -- different silicon, not a
  regression. `tests/test_perf_budgets.py` now skips the budget rows
  (naming both CPUs) when the runner's model differs from the reference,
  so a red nightly is always a same-hardware regression.
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
- **Opening a second `SQLiteStore` handle on a file another connection was
  reading failed with `database is locked`.** `PRAGMA journal_mode = WAL`
  is persistent in the file but issuing it needs an exclusive lock, so a
  CLI (`xsm dlq`) or a second process opening a live store could not even
  connect. The mode is now switched only when it differs from the file's,
  and a switch refused by a lock keeps the file's mode with a
  `RuntimeWarning` instead of failing to open.
- **One `after` delay with several guarded candidates armed one timer per
  candidate.** All candidates under `"1000": [...]` share the event
  `after.1000.<state>` and guard selection happens when it is processed,
  so N identical events were queued at the same instant; when the winner
  re-entered its own state the extra copy fired against the freshly
  re-entered state in the same pump -- a `nudge` re-entry counted twice
  per second. One timer per delay now, on both engines. Found by the
  slot-filling recipe (#308).
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

### Tests

- **The `raise(delay=)` / `after` heartbeat parity tests no longer depend
  on wall time.** `TestDelayedSelfSendIsATimer` ran a 30 ms heartbeat for
  1.0 s of real time on a `RealClock` and asserted a tolerance band on the
  beat counts, which flaked once on a box running two other suites. Both
  engines now run on a `SimulatedClock` advanced in 10 ms steps, so the
  counts are exact (34 / 11 / 5 beats for 30 / 100 / 250 ms over 1000 ms)
  and the two idioms are asserted **equal**, not close. A sync-engine
  parity case was added on the same clock. The `RunawayChainError` case is
  unchanged -- it never depended on time.

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
