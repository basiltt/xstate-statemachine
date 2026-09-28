# Handover: implement group **G2 EDA core** (#272, #293, #295), then **G3 Observability & inspector** (#273, #274) — xstate-statemachine

You are the second agent on a two-agent programme. Delivery is now **grouped**: read `docs/research/GROUPED_DELIVERY_PLAN.md` first — it defines the groups, who owns which, the two release candidates, and the **shared-file protocol** you must follow so we do not collide. Your groups are G2 then G3, each as **one PR**. The other agent (A) is on G1 (`[testing]` pytest plugin) and reviews/merges your PRs.

Sections 1–2 of `docs/research/HANDOVER_268_testing_plugin.md` (repo workflow, Python 3.9 floor, Windows notes, the twelve non-negotiable rules, guards that bite) apply verbatim; the branch names are `feat/g2-eda-core` and `feat/g3-observability`, and the PR body's checklist must end with `Closes #272, #293, #295.` (resp. `Closes #273, #274.`).

## Contracts frozen between us

You **define** these; nobody else may: `Envelope`, `BrokerAdapter`, `SyncBrokerAdapter`, `OutboxStore`, `DeadLetterStore`, `InboundDispatcher`, `OutboxPlugin`, `DeadLetterPlugin` (sink form), `asyncapi_document`, `SagaBuilder`, `ChoreographyRouter`, `PrometheusPlugin`, `OpenTelemetryPlugin`, `StructlogPlugin`, `LoguruPlugin`, `SentryPlugin`, `instrument_all`, `InspectorPlugin`, the sinks, and the CLI verbs `xsm dlq`, `xsm asyncapi`, `xsm inspect --live`, `xsm sim --record`, `xsm replay`.

You **consume** from A without redefining: the `xsm_*` pytest fixtures (`contrib/testing/pytest_plugin.py`). Inside `contrib/testing/` you may create **exactly one file**, `broker.py` (`FakeBrokerAdapter` + `replay()` helpers), and add its re-export to `contrib/testing/__init__.py` in a one-line change. If G1 has not merged when you get there, create `contrib/testing/__init__.py` with only the `require_extra` header (copy `contrib/pydantic/__init__.py`) and your export; A will merge the plugin around it.

Layout you own:

```
src/xstate_statemachine/eda/            # zero-dep core: envelope.py, broker.py (protocols), dispatcher.py, outbox.py, dead_letter.py, asyncapi.py, _asyncapi_schema.json (vendored)
src/xstate_statemachine/patterns/saga.py, choreography.py
src/xstate_statemachine/inspect/        # zero-dep core: plugin.py, sinks.py (JsonLines, SSE on http.server), protocol fixtures under tests/
src/xstate_statemachine/contrib/cloudevents/     # [cloudevents]: to/from SDK objects, HTTP binary/structured
src/xstate_statemachine/contrib/observability/   # [observability]: otel.py, prometheus.py, structlog_loguru.py, sentry.py
src/xstate_statemachine/cli/commands/{dlq,asyncapi,replay}.py + flags on inspect/simulate
tests/eda/, tests/patterns/test_saga.py, tests/inspect/, tests/contrib/{cloudevents,observability}/
docs/_guide/integration-eda.md, integration-observability.md, integration-inspector.md
scripts/verify/G2_eda_core.py, G3_observability.py
```

## G2 — EDA core (#272 → #293 → #295, in that order)

Read all three issues with `gh issue view N`; the **"Review amendments" block at the top of each supersedes the body**. Consolidated design decisions already taken (do not re-litigate):

- **#272 defines, #293 extends.** `Envelope` is CloudEvents-shaped from day one (`specversion, id, type, source, subject, time, datacontenttype, data` + extensions `correlationid, causationid, machineid, machineversion`); `subject` = machine key = partition key. `id` is sortable (uuid7-style: 48-bit ms timestamp + random; stdlib only). `Envelope.new(...)`, `.to_event()`, `.from_transition(...)`, `.to_json()/.from_json()`. **Schema-validate before `to_event()`**: wrong shape → `EnvelopeCorruptError` (subclass of `XStateMachineError`); unknown `type` → dead-lettered as `unknown_event`, never raised into the consumer loop; **size cap** reuses `DEFAULT_MAX_SNAPSHOT_BYTES` semantics (X0.4); `traceparent` extension validated against the W3C regex; **no** `authorization`/cookie headers ever copied into extensions (X0.8).
- `BrokerAdapter` (async) and `SyncBrokerAdapter` protocols: `publish(topic, envelope)`, `subscribe(topic) → async iterator of (envelope, ack)`, `ack()`, `nack(requeue: bool)`. **`FakeBrokerAdapter` lives in core `eda/fake.py`** (stdlib only — a fake that needs nothing is not an extra, and `tests/eda/` must run in the default job); `contrib/testing/broker.py` merely re-exports it next to the `replay()` helpers so the issue's import path `from xstate_statemachine.contrib.testing import FakeBrokerAdapter` also works.
- `InboundDispatcher(store, machine_for_type, *, lock=OptimisticLock(), plugins=(), inbox=None, max_in_flight=…)` = envelope → `persisted(store, key=subject, machine)` → `send(envelope.to_event())`. Dedup via `IdempotencyPlugin` on `envelope.id` when an `inbox` is given (`principal` = `envelope.source`). **Per-subject ordering**: one subject processed at a time; different subjects may interleave up to `max_in_flight`. **Poison handling (X0.8)**: an attempt counter in the envelope extensions; after `max_attempts` → `DeadLetterStore.put()` + `ack`, never an infinite redelivery loop. `run_once(broker, topic)` and `run_forever(...)` with a stop event.
- `OutboxPlugin(sink)`: publishes only transitions the chart tags — `tags: ["publish"]` on a state or `meta.publish` on a transition (both spellings already parse; `StateNode.tags/meta` exist). Sinks: a `BrokerAdapter` (documented as at-most-once-ish) or an `OutboxStore`. Ship a **zero-dep `SQLiteOutboxStore`** sharing `SQLiteStore`'s connection so a rollback drops the outbox row with the snapshot (test with a forced failure after the write). The SQLAlchemy outbox (G6) implements the same protocol later.
- `DeadLetterPlugin` from `patterns/` gains a store/broker sink; `DeadLetterStore` protocol with `SQLiteDeadLetterStore` (default) and `MemoryDeadLetterStore`. CLI `xsm dlq list|show|replay|purge`: `replay` defaults to `--dry-run`, requires `--yes` and `--reason`, reuses the envelope id (so the inbox dedups a double replay), refuses on machine hash/version mismatch without `--force`, writes an audit record. Redaction (`redact()`) before anything is written.
- `asyncapi_document(machine, *, server=…)` → dict; validated in tests against a **vendored** AsyncAPI 3 JSON Schema (`eda/_asyncapi_schema.json`, provenance + version in a header comment of the loader; offline). `[cloudevents]` extra only adds SDK interop.
- **#295**: `SagaBuilder("name").step(name, invoke=…, compensate=…, timeout_ms=…).build()` emits plain JSON a human could have written (`steps.<n>` with `invoke` + `after` timeout → `onError`; failure at k → `compensating.<k-1> … .0 → failed`; every step transition tagged `publish`); strict-config clean. Tests on `SimulatedClock`: happy path, failure at step 2 compensates in reverse exactly once, timeout → retry → compensate, idempotent completion via inbox on `causationid`. `ChoreographyRouter` = `InboundDispatcher` + `type → machine` mapping; the Order+Payment test over `FakeBrokerAdapter` asserts the causation chain. `xsm asyncapi machine.json [-o]`; `xsm docs` embeds published/consumed events.
- Docs: one page `integration-eda.md` (§Envelope, §Broker adapters, §Inbound dispatcher, §Outbox, §Dead letters, §Sagas, §Choreography, §AsyncAPI) — from the template, with Guarantees (at-least-once + inbox = effectively-once transitions; outbox transactional only via `OutboxStore`; no exactly-once publish) and Threat model (X0.4 size caps, X0.8 no secrets in extensions/labels, DLQ replay requires `--yes --reason`, files 0600). Link the Guarantees page's order-of-operations diagram — the outbox/ack steps are already drawn there as "later phase"; update that page's two bullets to say "shipped".

## G3 — Observability & inspector (#273, #274)

- **#273** amendments: depends on `on_event_processed` (#304, shipped) for span outcome + context unbinding, and `plugins.register_global` (#305, shipped) for `instrument_all()`. **Telemetry hygiene (X0.6/X0.8)**: label allow-list with `unknown` fallback; no payloads, instance keys or correlation ids as labels/attributes by default; `queue_depth` via a polling collector. Split the PR's commits into OTel+Prometheus and structlog/loguru/Sentry, but ship them in the one G3 PR. `[observability]` = `opentelemetry-api>=1.20`, `prometheus-client>=0.17`; structlog/loguru/sentry are soft imports (detected, not pinned; registry `modules` tuple lists only the two hard ones). The `PrometheusPlugin` row in `benchmarks/budgets.json` is currently Idempotency+Audit with a note — **re-record it** with the real plugin via the `perf` job (`workflow_dispatch`, `--from-json last_run.json --record-baseline`) and update the note + docs table (see `HANDOVER_307_perf_budgets.md` for the mechanics).
- **#274** amendments: **spike first** — the `@statelyai/inspect` wire protocol is not formally documented; record fixtures from the real npm package (commit the JSON with provenance + regeneration steps under `tests/inspect/fixtures/`), keep a minimal own HTML page as fallback. Core is stdlib only: SSE over `http.server`, WebSocket only when `[starlette]` is present (G4 will wire `GET /_xsm/inspect`; leave a documented hook). Security (X0.7): `secrets.token_urlsafe(32)`, `hmac.compare_digest`, token via header/cookie after first page load (not a persistent query string), loopback `Host` and `Origin` checks, `--host 0.0.0.0` requires `--token`, deny-by-default `context_allowlist`, JSONL sink files 0600. `sendTo` between actors has no sender hook — add `on_event_sent(interp, target_id, event)` to `PluginBase` (both engines; `_SafePlugin`-wrapped; document in `plugins.md` and the API reference) rather than deriving it. CLI: `xsm inspect --live [--port] [--open]`, `xsm sim --record path.jsonl`, `xsm replay path.jsonl --live`.
- Docs: `integration-observability.md` and `integration-inspector.md` from the template; `cli.md` §"Live inspector"; XState parity row.

## Things that will save you time

- `persisted(store, key, machine, lock=…)` / `apersisted` in `xstate_statemachine.persistence` are the act-loop; `IdempotencyPlugin(inbox, principal=…)`, `MemoryInbox`, `SQLiteInbox(store)`, `AuditPlugin`, `MemoryLog`, `redact()`, `DEFAULT_MAX_SNAPSHOT_BYTES`, `SQLiteStore` (connection-per-thread; see `sqlite_store.py` for how `SQLiteInbox` shares its transaction — copy that for the outbox).
- `patterns/` already has `RetryPolicy`, `dead_letter` transition helper, `CircuitBreaker`; extend `dead_letter`, don't fork it.
- Plugin hooks: `on_interpreter_start/stop`, `on_event_received`, `on_transition`, `on_guard_evaluated`, `on_action_execute`, `on_service_start/done/error`, `on_unhandled_event`, `on_snapshot_error`, `on_before_send`, `on_event_processed`. `_wants_event_processed` means the engine only pays for `on_event_processed` if a plugin overrides it — keep that true for your plugins' hot path.
- `StateNode.tags`, `.meta` are parsed; `TransitionDefinition.meta` — check `models.py` before assuming transition-level meta exists; if it does not, add it (strict-config aware) as a small core change and say so.
- CLI shape: `cli/commands/<verb>.py`, args in `cli/args.py`, tests in `tests/tests_cli/`; `parse_events_arg` in `commands/simulate.py`; the rich/plain output split via `get_console()` and `--plain`.
- Verification scripts must be Windows-safe (no `/tmp`, no heredocs; use `tempfile`, `subprocess.run([sys.executable, ...])`).
- Full suite ≈ 13 min; run before each PR. Coverage gate 90 %, never lowered. `tests/test_security_baseline.py` will fail your PR if a new extra's requirements are not also in `[all]`, or an Action is not SHA-pinned.

## Definition of done (per group)

- [ ] Everything in the issues' acceptance criteria, as amended above; deviations explained in the PR body.
- [ ] Both engines; zero-dep core (`test_zero_dependency`, `test_import_surface` green); extras matrix cells added (`cloudevents`, `observability`); `[all]` updated.
- [ ] Docs pages with both boxes, in nav + `INTEGRATION_PAGES` + search index; changelog ×2 as one group block; verify script → `ALL OK`.
- [ ] Full suite green locally and on CI; PR opened against `main`, **not merged**; hand-back comment with deviations and the verify output.
- [ ] Then start the next group on a fresh branch from `main`, without waiting for review.
