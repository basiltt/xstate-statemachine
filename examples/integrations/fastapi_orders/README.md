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

**Docker Compose** (one web container with `--workers 4`, the scheduler and
Redis; built from this checkout):

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
`Idempotency-Key`, and with one shared key. It exits non-zero unless each
round has **exactly one** `changed=True` receipt, only `200`/`409`
responses, and a final state of `paid`.

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

Measured on an 11th Gen Intel Core i7-11850H (8 cores, 32 GB RAM), Windows 11,
Python 3.14, SQLite on a local NVMe disk. The client and the server were on
the same machine:

| Workers | Round | changed | unchanged | duplicate | 409 | p50 ms | p95 ms |
|--:|:--|--:|--:|--:|--:|--:|--:|
| 1 | no key | 1 | 123 | 0 | 76 | 1000 | 2574 |
| 1 | with key | 1 | 0 | 199 | 0 | 1052 | 2692 |
| 2 | no key | 1 | 145 | 0 | 54 | 712 | 1512 |
| 2 | with key | 1 | 0 | 143 | 56 | 467 | 972 |
| 4 | no key | 1 | 145 | 0 | 54 | 545 | 1036 |
| 4 | with key | 1 | 0 | 199 | 0 | 402 | 749 |
| 4 (compose, Redis) | no key | 1 | 135 | 0 | 64 | 909 | 1601 |
| 4 (compose, Redis) | with key | 1 | 0 | 199 | 0 | 476 | 1182 |

Latency is the time for the whole 200-request burst on one hot key, so every
request queues behind the others. It is not the latency of a single request.
The **conflict count** is the 409 column. Nothing retries a 409 for you.
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
