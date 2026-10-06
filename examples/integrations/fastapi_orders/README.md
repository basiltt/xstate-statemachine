# FastAPI orders — a statechart behind N uvicorn workers

A complete order-lifecycle service built on `xstate-statemachine[fastapi]`.
It is also a stress test for the web layer: 200 concurrent payments against
one order, across several worker processes, must produce **exactly one**
charge.

```
cart ──CHECKOUT──▶ awaitingPayment ──PAY──▶ paying ──done──▶ paid ──FULFIL──▶ fulfilment ─▶ shipped
  │                   │  after 15 min ─▶ expired      │ error                     ║ packing ∥ labelling
  └──CANCEL──▶ cancelled ◀──CANCEL──┘                 ▼
                                               retrying ──after(retryDelay)──▶ paying   (RetryPolicy, 3 attempts)
                                                    └──▶ paymentFailed ──PAY──▶ paying
```

| File | What it is |
|:--|:--|
| `machine.json` | The chart (Stately-export shape). Passes `xsm validate --plain`. |
| `machine_v2.json`, `migrations.py` | The next chart revision and the `SnapshotMigrator` step that brings v1 orders into it (see "Rolling upgrade"). |
| `models.py` | One Pydantic `EventModel` per event plus the `OrderContext` model (`context_model`). |
| `logic.py` | Actions, guards and a fake payment gateway (`invoke` + `onError`, retried by `RetryPolicy`). |
| `app.py` | The FastAPI app: `StatechartRegistry`, `StatechartRouter`, `instrument_app`, `Idempotency-Key`, the `BackgroundTasks` email bridge, SSE, `mount_inspector` and the `--role scheduler` / `--role init` modes. |
| `static/index.html` | A live view that uses a vanilla `EventSource`. |
| `loadtest.py` | Starts N workers, fires 200 concurrent PAYs, checks the result and prints a table. |
| `tests/` | Plain pytest + `TestClient` / `httpx.ASGITransport`. |
| `Dockerfile`, `docker-compose.yml` | Four workers, one scheduler and Redis. |

## What you are looking at

No worker keeps an order in memory. Each request **loads** the order's
snapshot from the store, runs **one** interpreter over it, **saves** it with
the version it loaded (`expected_version`), and **discards** the
interpreter. This is create → act → persist → discard. Two workers that race
on one order both load version *n*. The first save wins and the second gets
a `ConflictError`, which the API returns as `409`. No update is lost. This
is why `--workers 4` is safe with `SQLiteStore` on one host or with Redis
across hosts.

Timers need the same treatment. The 15-minute payment timeout and the retry
backoff are saved with the snapshot as **deadlines**. A single scheduler
process (`python app.py --role scheduler`, which runs
`DueTimerScanner.run_forever()`) wakes the orders whose deadlines have
passed. If every worker ran a scanner, all of them would race to fire the
same timer. Exactly one scheduler process should run.

Side effects follow two rules. The card charge is an `invoke`d service, so a
failure becomes an `onError` transition that the chart models and retries.
The confirmation email is sent through FastAPI `BackgroundTasks`. It is
scheduled only when the receipt says `changed and not error and not
duplicate`, which is after the save has committed. That means it fires once
per real payment, never for a replay and never for a rolled-back attempt.
`PAY` is refused on the generic `/send` route, so the email hook cannot be
bypassed.

## Run it

```bash
pip install "xstate-statemachine[fastapi,redis]" uvicorn httpx
cd examples/integrations/fastapi_orders
```

**Single process** (SQLite at `$XSM_ORDERS_DB`, default `./orders.db`):

```bash
uvicorn app:app --port 8000
```

**Four workers:** create the SQLite schema once, then start the workers and
exactly one scheduler:

```bash
python app.py --role init            # one-time: schema + WAL (N workers racing to do it see "database is locked")
uvicorn app:app --port 8000 --workers 4
python app.py --role scheduler       # in another terminal -- exactly ONE
```

**Redis** (multi-host): set `XSM_REDIS_URL=redis://localhost:6379/0` for the
web workers and for the scheduler. `RedisStore` and `RedisInbox` are then
used instead of SQLite. Redis is imported only when this variable is set.
The example's Redis tests use `fakeredis`; only Compose uses a real Redis.

**Docker Compose** (one web container with `--workers 4`, ONE scheduler
(`deploy.replicas: 1`) and a real Redis; built from this checkout. Redis
needs no `--role init`. The image's healthcheck probes `/_xsm/ready`.
`loadtest.py` starts its own SQLite server and does not target the
compose stack):

```bash
docker compose up --build
```

**Debug:** `XSM_DEBUG=1` mounts `mount_inspector` at `/_xsm/inspect`. Never
enable it in production.

## `curl` walkthrough

The demo identity is the `X-Customer` header (the `customer` cookie for the
SSE page). It is also the scope for `Idempotency-Key`. Replace it with your
real authentication.

```bash
H='-H content-type:application/json -H x-customer:ann'
curl -s -X POST localhost:8000/orders/o1/events/ADD_ITEM $H -d '{"sku":"tea","qty":2}'
curl -s -X POST localhost:8000/orders/o1/events/CHECKOUT $H
curl -s -X POST localhost:8000/orders/o1/events/PAY $H -H 'Idempotency-Key: pay-o1-1' -d '{"card_token":"tok_ok"}'
# the same key again: 200 with "duplicate": true and the ORIGINAL receipt -- no second charge, no second email
curl -s -X POST localhost:8000/orders/o1/events/PAY $H -H 'Idempotency-Key: pay-o1-1' -d '{"card_token":"tok_ok"}'
# PAY after paid without a key: 200 "changed": false -- the chart itself refuses it
curl -s -X POST localhost:8000/orders/o1/events/PAY $H -d '{"card_token":"tok_ok"}'
curl -s localhost:8000/orders/o1 -H x-customer:ann          # {"state": "paid", "available_events": ["FULFIL"], ...}
curl -s -X POST localhost:8000/orders/o1/send $H -d '{"type":"FULFIL"}'
curl -s -X POST localhost:8000/orders/o1/events/PACKED $H
curl -s -X POST localhost:8000/orders/o1/events/LABEL_PRINTED $H   # "state": "shipped"
curl -N localhost:8000/orders/o1/stream -H x-customer:ann   # SSE: snapshot, then one `transition` per change
```

Open `http://localhost:8000/?order=o2` in a browser and drive `o2` with
`curl`. The page updates over SSE. Card tokens: `tok_flaky` fails the first
attempt and succeeds on retry (the scheduler must be running), and
`tok_declined` fails every attempt and ends in `paymentFailed`. OpenAPI is at
`/docs`.

**`xsm simulate` parity:** the chart runs without this app. With stub logic
(every guard true, every service succeeds), the same three events reach the
same state:

```bash
xsm simulate machine.json --events ADD_ITEM,CHECKOUT,PAY --json   # "value": "paid"
```

## Load test

```bash
python loadtest.py --workers 4 --requests 200
```

A Python launcher runs `app.py --role init` and then starts
`python -m uvicorn app:app --workers N` with `subprocess.Popen`. It uses no
fork, so it also works on Windows, where uvicorn spawns its workers. It polls
`/_xsm/health` until the server answers. It then fires 200 concurrent `POST
/orders/{id}/events/PAY` at **one** order, in two rounds: without an
`Idempotency-Key`, and with one shared key. It exits `1` unless each
round has **exactly one** `changed=True` receipt, only `200`/`409`
responses, and a final state of `paid` (`2` for bad arguments). `--json`
prints the rows as JSON instead of the table, with the server's logs on
stderr.

Exactly one payment succeeds because of **two independent guards**:

* **The chart.** After `paid`, `PAY` has no handler, so a request that loads
  the saved snapshot gets `200 changed: false`. Requests that loaded the
  order *before* the winner saved lose the optimistic version check and get
  `409`. This works without any key.
* **The inbox.** With an `Idempotency-Key`, the `IdempotencyPlugin` records
  the key with the receipt in the same transaction as the snapshot. A replay
  returns the original receipt as `duplicate` and neither runs the chart nor
  saves. A replay that arrives while the original is still running gets
  `409 IdempotencyInFlightError`.

Measured on Windows 11 / Python 3.14 / SQLite (an 11th Gen Intel Core
i7-11850H laptop, 8 cores / 16 threads, local NVMe; client and server on
the same machine), 200 requests per round. Each worker count ran several
times (`python loadtest.py --workers N --json`). Every run passed. The
table gives the **range** over those runs:

| Workers | Runs | Round | changed | unchanged | duplicate | 409 (conflict retries) | p50 ms | p95 ms |
|--:|--:|:--|--:|--:|--:|--:|--:|--:|
| 1 | 3 | no key | 1 | 199 | 0 | 0 | 339–347 | 770–802 |
| 1 | 3 | with key | 1 | 0 | 199 | 0 | 222–256 | 460–512 |
| 2 | 3 | no key | 1 | 199 | 0 | 0 | 252–423 | 525–770 |
| 2 | 3 | with key | 1 | 0 | 199 | 0 | 177–242 | 325–426 |
| 4 | 5 | no key | 1 | 199 | 0 | 0 | 188–210 | 348–406 |
| 4 | 5 | with key | 1 | 0 | 199 | 0 | 152–177 | 286–326 |

Only the **changed = 1** column is a guarantee. The split of the other
199 between `unchanged`, `duplicate` and `409` depends on timing: on this
machine every loser loaded the snapshot after the winner saved, so none
lost the version check. An earlier version of this
README reported 54–76 `409`s per no-key round from an older revision
(those runs could not be reproduced). Treat `409` as normal and be
ready to retry it. Your numbers will
differ. Regenerate them with `--json`.

Latency is the time for the whole 200-request burst on one hot key, so every
request queues behind the others. It is not the latency of a single request.
The **conflict-retry count** is the 409 column (`conflict_retries` in
`--json`): the requests a client would have to retry. Nothing retries a
409 for you.
With a key, a client can safely retry with the same key and gets either the
duplicate receipt or the result of its own request. How many requests end
up `in flight` versus `duplicate` depends on timing: requests arriving while
the winner is still charging the card see `in flight`.

📝 On Windows, uvicorn `--workers N` may log `OSError: [WinError 10022]` for
a worker that fails to share the listening socket. The supervisor restarts
it and the test still passes. This is a uvicorn issue on Windows.

## Rolling upgrade: chart v2 while v1 orders are mid-flight

`machine_v2.json` is the next release of the chart: `paying` (one gateway
call) becomes `payment.authorising` → `payment.capturing` (authorise, then
capture, a second `captureCharge` service) and `context` gains `currency`.
Thousands of v1 orders are persisted when v2 ships — in the cart, checked
out with a live 15-minute timeout, in `retrying` with a live backoff
deadline, paid, shipped, and one whose worker died mid-charge. Nothing is
rewritten in bulk.

`migrations.py` registers **one `SnapshotMigrator` step** (`"1"` → `"2"`,
scoped to `machine_id="order"`) that rewrites the state ids and
`configuration` and sets the new context default. `build_registry()` puts
it on the registry, so the request path (`apersisted`) *and* the scheduler
(`DueTimerScanner`) migrate a v1 order lazily the first time a v2 process
touches it, inside the same optimistic save — two workers racing on one
stale order still produce exactly one migrated record, the other gets `409`.

```bash
XSM_ORDERS_CHART=1 uvicorn app:app --port 8000        # the v1 fleet (default)
xsm snapshots --store sqlite:///orders.db machine_v2.json --stale   # the drain list
XSM_ORDERS_CHART=2 uvicorn app:app --port 8000        # v2 workers + v2 scheduler
# ... serve traffic; each stale order migrates on its first write ...
xsm snapshots --store sqlite:///orders.db machine_v2.json --stale   # empty when done
```

What the scenario pins (`tests/test_rolling_upgrade.py`):

* a v2 worker **without** the migrator refuses a v1 order loudly
  (`MachineVersionMismatchError`, no card token in the body) and leaves the
  record untouched — the default policy;
* a **read** (`GET`, SSE connect) shows the migrated view but writes
  nothing; the first **write** re-saves at label `"2"`;
* the live retry and 15-minute timeout deadlines survive the migration and
  fire from the v2 scheduler, which re-saves at `"2"`;
* 50 concurrent `PAY`s on one stale order → one migration commits, one
  charge, the rest `409`;
* the order that crashed mid-charge lands in `payment.authorising` with its
  invoke dormant and is driven to `paid` with `restart_services=True` — the
  idempotent charge id means a real gateway would recognise the replay;
* a v2 blob into the **old** chart is refused: deploy the migrator on the
  readers before the writers emit the new label (the dual-read window).

What is faked: the gateway (`logic.py`) and time (the scanner is driven
with an injected `now`). Going live: the same `migrations.py`, a real
gateway behind `chargeCard` / `captureCharge`, and `xsm snapshots --stale`
in your deploy pipeline as the gate between "v2 deployed" and "v1 workers
retired".

Two library defects this scenario found on its first run, both fixed in
0.11.0: `apersisted()` snapshotted a machine still mid-step on any chart
with two plain `def` invokes in a row (`SnapshotMidStepError` → `500`; the
block now settles first), and the registries' read paths (`peek`) ignored
the migrator, so a v2 deployment answered `409` to every `GET` on a v1
order until something wrote to it.

## The scheduler is down for three hours

The second battle scenario (`tests/test_scheduler_outage.py`). Four hundred
orders check out over an afternoon, each arming a 15-minute payment
timeout; forty pay with a flaky card and arm a retry backoff. The one
scheduler process dies at 14:00 and comes back at 17:00 with a backlog of
hundreds of overdue deadlines. What it must do, and what the test pins:

* **drain oldest-first, in batches** — `limit=100` means four ticks; each
  tick wakes the 100 *earliest* matured deadlines (the retry backoffs,
  seconds old at 14:00, go before any timeout), never the first 100 keys
  by name, and the drain converges;
* **report the lag** — `ScanResult.max_lag_s` on the first tick is the
  whole outage (≈ 3 h): that number is your alert;
* **leave live timers alone** — an order that checked out at 16:50 is
  still `awaitingPayment` at 17:00;
* **exactly once per deadline** — `on_transition` counted per key, every
  count is 1, and a second drain at the same instant is a no-op;
* **two schedulers by accident** — an operator starts a second one against
  the same store; under `OptimisticLock` the loser's save is a
  `ConflictError` the scanner counts as `skipped_stale`, under
  `PessimisticLock` the re-read under the lock finds the deadline gone.
  No double fire, no `errors` noise — "run exactly one" is operational
  advice, not a correctness requirement;
* **at-least-once across a crash** — the save after a fire fails once
  (the process "died"); the record is untouched and still due; the next
  tick fires again and commits. The transition fired twice in memory and
  once on disk — make timer transitions idempotent or pair them with the
  inbox.

Two scanner defects this scenario found: `limit=` capped the keys
*scanned* (always the same first N by key order), so with a backlog
larger than the limit the rest never fired; and the lost side of an
optimistic race was filed under `errors` (an ERROR log per overlap)
instead of `skipped_stale`.

## The payment provider is down for ten minutes

The third battle scenario (`tests/test_gateway_outage.py`). Black Friday,
14:00: the card gateway starts timing out on every call. `logic.py` now
puts **one `CircuitBreaker` per process** in front of the gateway
(`GATEWAY_BREAKER`, `failure_threshold=3`, `cooldown_ms=5000`, counting
only `GatewayDown` — a *decline* is not a provider failure), and
`machine.json` tags `paymentFailed` as `dead-letter` so the registry's
`DeadLetterPlugin` writes a record into the same SQLite file the snapshots
live in (`build_dead_letter_store`). What the test pins:

* **the breaker spares the provider** — 60 orders try to pay during the
  outage; the gateway is hit exactly 3 times. Every further charge fails
  in microseconds with `CircuitOpenError`, and each order still takes the
  chart's `onError → retrying` path and backs off (the breaker and the
  retry loop compose: the breaker protects the *provider*, the retry loop
  protects the *order*);
* **32 threads on a dark gateway** — only the threshold reaches it, the
  rest are refused, none hang the worker pool;
* **retries exhausted while open → `paymentFailed`** — the dead letter's
  error chain names the outage (`GatewayDown`, then `CircuitOpenError`),
  `attempts=3`, the card token is **redacted** in the snapshot and the
  payload, and `xsm dlq --dlq sqlite:///orders.db list` shows it without
  the secret;
* **half-open admits one probe** — when the cooldown ends with the
  provider still dark, the scheduler's next wake lets exactly one call
  through; it fails and the circuit re-opens (no herd). When the provider
  is back the probe succeeds, the circuit closes, and the scheduler drains
  the retrying orders to `paid`;
* **probing is demand-driven** — if all traffic has given up before the
  cooldown ends, the breaker sits half-open until the next caller; no
  timer thread probes on its own;
* **recovery is the chart's own path** — a dead-lettered order pays again
  with the customer's card: `paid`, `attempt` reset.

What is faked: the gateway (`logic.GATEWAY.up`) and time (one
`SimulatedClock` shared by the breaker, the registry and the scanner).
Going live: the same wiring; tune `XSM_ORDERS_CB_THRESHOLD` /
`XSM_ORDERS_CB_COOLDOWN_MS` to your provider's SLA, and for Redis
deployments point `dead_letters=` at a `BrokerDeadLetterSink` or your
queue instead of the in-memory default.

## Four workers on two hosts share one Redis

The fourth battle scenario (`tests/test_redis_fleet.py`, #306). The first
question every web user asks -- "I have 4 uvicorn workers on 2 machines,
where does the snapshot live?" -- answered with `RedisStore` + `RedisInbox`
(`XSM_REDIS_URL`) and then attacked the way production attacks it. Four
registries stand in for four worker processes: each has its own breaker and
its own memory, nothing shared but Redis. What the test pins:

* **one hot order, 200 `PAY`s over four workers** -- exactly one charge,
  only `200` / `409`, and with an `Idempotency-Key` the inbox is shared:
  a replay on *another* host returns the original receipt as `duplicate`;
* **the lock expires under a slow worker** -- `PessimisticLock` with a
  `lock_ttl_ms` shorter than the gateway call: worker B takes the expired
  lock and pays; worker A's late save hits the version fence and answers
  `409`. One charge, one email, nothing overwritten (X0.3, end to end
  through HTTP);
* **Redis goes away for a failover** -- every request during the outage is
  a `503 Store unavailable` problem (no `500`, no exception text in the
  body, one WARNING line per request in the log instead of a traceback);
  `/_xsm/health` stays `200` (the process is alive), `/_xsm/ready` is
  `503`; the first request after it comes back finds the order byte-for-byte
  as it was;
* **the scheduler on Redis** -- 120 orders, 20 retry backoffs:
  `due_keys()` reads the sorted-set index (no record is loaded to decide
  what is due), the backoffs drain before any 15-minute timeout, four
  ticks of `limit=50` converge;
* **`forget()` is total and namespace-safe** -- no key with the order's
  name survives in the prefix; a lookalike prefix (`orders-x-other`) is
  untouched;
* **nothing leaks** -- 2 000 create → act → persist → discard cycles: the
  connection pool, the thread count and tracemalloc (N/2 vs N) are flat.

Offline by default: one `fakeredis.FakeServer` shared by every worker. Set
`XSM_REDIS_URL=redis://localhost:6379/15` to run it against a live Redis.
The multi-**process** proof is the load test with `--redis` (it ignores
`XSM_REDIS_URL` in your shell, so a stray variable never switches the
store; before #277-b it always ran SQLite):

```bash
docker run -d --rm -p 6379:6379 redis:7-alpine
python loadtest.py --workers 4 --requests 200 --redis redis://localhost:6379/3
```

| Workers | Round | changed | unchanged | duplicate | 409 | p50 ms | p95 ms |
|--:|:--|--:|--:|--:|--:|--:|--:|
| 4 (Redis, local) | no key | 1 | 154 | 0 | 45 | 192 | 344 |
| 4 (Redis, local) | with key | 1 | 0 | 199 | 0 | 192 | 339 |

⚠️ These two rows are **not Redis numbers**. Before #277-b, `loadtest.py`
dropped `XSM_REDIS_URL` from the workers' environment, so this run used
SQLite. No live-Redis load test has been measured for this README. Run the
`--redis` command above and record the result here.

One library defect this scenario found: a Redis connection error escaped
the store as a raw `redis.exceptions.ConnectionError` -- past
`except StoreError`, so every route answered `500 "ConnectionError"` for a
dependency outage and wrote a traceback per request. Redis errors are now
typed (`StoreUnavailableError` for the connection class → `503`,
`StoreError` otherwise), the same mapping `SQLiteStore` has had since #259.

The seams between hosts (`tests/test_redis_fleet_b.py`):

* **host A is mid-charge when host B replays the key** -- B answers
  `409 IdempotencyInFlightError` and charges nothing; once A commits, a
  replay on any host is the original receipt (`duplicate`), and a different
  body under the same key is `422`. One gateway call, one email.
* **SSE is per process** -- a stream on host B does not see a commit made on
  host A; reconnecting (the `snapshot` event is a fresh read of Redis) does.
  Use sticky sessions, or let `EventSource` reconnect.
* **two schedulers by accident, on Redis** -- every deadline is committed
  exactly once (version +1); optimistic losers are `skipped_stale`, under
  `PessimisticLock` nothing runs twice.
* **dead letters are per process here** -- with `XSM_REDIS_URL` set,
  `build_dead_letter_store` falls back to a `MemoryDeadLetterStore`: only
  the worker that exhausted the retries holds the record, its peers do not,
  and `xsm dlq` cannot read it. In production pass `dead_letters=` a shared
  sink (`BrokerDeadLetterSink`, or a `SQLiteDeadLetterStore` on a volume
  the operator can reach).

A second round of defects, in `RedisInbox` / `RedisLog` (agent B): inbox
expiry used each worker's clock (two hosts 5 minutes apart could both
admit one key), a permanent receipt was purged with its claim's TTL, a
scope containing `|` was never purged; the log let 32 concurrent writers
mint duplicate `seq`s (640 records, 37 distinct) and read every page by
scanning the whole stream. All fixed; see the CHANGELOG.

## A typed boundary under hostile traffic

The fifth battle scenario (`tests/test_pydantic_boundary.py`, #266). The
order service is the only thing between a browser and the chart: every
payload is an `EventModel`, the context is `OrderContext` after every
action, the chart passes `validate_machine_json(strict=True)` in the deploy
pipeline, and the JSON Schema from `machine_json_schema` is what the
frontend team codes against. Each is attacked:

* **hostile payloads** -- 30+ malformed `PAY` / `ADD_ITEM` / `CANCEL`
  bodies (wrong types, extra keys, nested objects, 1 MB strings, NUL,
  `type` overrides, reserved `send()` kwargs, `__class__` /
  `model_config` keys, non-object bodies): every one is `422` with a
  field *path* and an error *type*, never a `500`, never the offending
  value echoed, and the stored order is byte-identical afterwards;
* **a mutating action that breaks the model** under
  `actionErrorPolicy: rollback`, 64 threads × 50 events on the sync
  engine and 200 awaited events on the async one: the context is never
  observed invalid, every refusal is a `ContextValidationError` on the
  receipt, `n` and `total` equal the clean events exactly;
* **money through the persistence loop** -- a `Decimal` total through
  `persisted()` on Memory / File / SQLite with `PydanticCodec` +
  `TypedContextPlugin`: `"14.00"` at rest (never a float), a `Decimal`
  in the restored machine's first action; the same *without* the plugin
  is pinned as the documented pitfall (a `str` total, a visible error);
* **the deploy gate** -- the shipped chart passes `strict=True`; 12
  single-key corruptions are each refused *with the path*; the gate never
  refuses a corpus chart (104) the engine accepts;
* **the schema** -- every client-sendable event is a `oneOf` branch with
  a `discriminator.mapping`, the `state` enum is the chart, the document
  round-trips through `json`, and `x-machine-hash` changes with the chart.

Four defects it found, all fixed in 0.11.0: a chart whose static
`context` the model refuses **built and started** (the plugin's raise is
contained) and then rolled back every mutating action forever -- it is
now `InvalidConfigError` at `create_machine`, and a bad *restored* context
puts the machine in `status == "error"`; `{"type": 1}` actions and list
transition targets crashed the parser with a bare `AttributeError`; and a
route the app adds beside the generated router (`PAY` with
`BackgroundTasks`) fell back to FastAPI's default 422 body, which echoes
the offending `input` -- `instrument_app` now maps every
`RequestValidationError` to the problem shape.

## Tests

```bash
python -m pytest tests -q
```

The tests cover the happy path through `shipped`, payment failure → retry →
paid, retries exhausted → `paymentFailed`, the `after` timeout through the
scanner with an injected `now`, `Idempotency-Key` duplicates and mismatches,
200 concurrent PAYs in-process with one winner (with and without a key), one
SSE `transition` per change, an email only on success, probes, OpenAPI, the
inspector gate, `stub_logic` parity, and the rolling upgrade above. The
repository's `tests/test_examples_integrations.py` runs this suite in CI
(in the `[fastapi]` cell).

See the [FastAPI guide](../../../docs/_guide/integration-fastapi.md) for the
design discussion.
