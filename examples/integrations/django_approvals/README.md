# Django approvals — parallel review, two roles, admin, DRF, Channels

An expense-approval app on `xstate-statemachine[django,drf,channels]`.
Legal and finance review **in parallel**. Each region needs its own role,
and the chart states the rule once. The admin, the REST API and the
WebSocket all ask it the same question.

```
draft ──SUBMIT──▶ review ═══════════════════════════════╗ ──onDone──▶ approved (publish)
                  ║ legal:   pending ──LEGAL_APPROVE [isLegal]──▶ approved   ║
                  ║ finance: pending ──FINANCE_APPROVE [isFinance]──▶ approved║
                  ║ after 48 h: escalate (xsm_deadlines)                     ║
                  ╚══ REJECT [isReviewer] (confirm + reason) ──▶ rejected ═══╝
```

| File | What it is |
|:--|:--|
| `machine.json` | The chart. It passes `xsm validate --plain`. |
| `approvals/models.py` | `Expense(StatechartModelMixin)`. Two roles as `RoleGuard`s (the `legal` and `finance` groups), `AnyOf` for REJECT, and the `escalate` action. |
| `approvals/management/commands/relay_outbox.py` | Drains the outbox with `OutboxRelay`. The stand-in broker prints one CloudEvents JSON line per event; swap in your own adapter. |
| `approvals/admin.py` | `StatechartAdminMixin`. Transition buttons are CSRF-protected POST forms, computed for the logged-in user. REJECT asks for a reason. The audit history is inline. |
| `approvals/api.py` | `StatechartViewSetMixin`: one `@action` per event (`/api/expenses/{id}/legal-approve/`), with the drf-spectacular schema at `/api/schema/`. |
| `approvals/ws.py`, `config/asgi.py` | `StatechartConsumer` at `/ws/expenses/<id>/`, behind `AuthMiddlewareStack` and the origin validator. |
| `approvals/templates/approvals/status.html` | A status page that shows the live state over the WebSocket. |
| `tests/` | pytest with pytest-django. It covers both roles, the admin, DRF + schema, Channels and the escalation. |

## Run it

```bash
pip install "xstate-statemachine[django,drf,channels]" drf-spectacular daphne pytest-django
cd examples/integrations/django_approvals
python manage.py migrate
DJANGO_SUPERUSER_PASSWORD=change-me python manage.py createsuperuser --noinput --username admin --email admin@example.com
python manage.py runserver 8000                    # daphne: HTTP + WebSocket; admin at http://127.0.0.1:8000/admin/
python manage.py xsm_deadlines --forever           # in another shell: fires the 48 h escalation (Ctrl+C stops it)
python manage.py xsm_deadlines                     # or one pass, from cron
python manage.py xsm_inspect approvals.Expense     # the chart, same output as `xsm inspect`
python manage.py xsm_diagram approvals.Expense -f mermaid   # the chart as Mermaid
python manage.py xsm_snapshots approvals.Expense   # every row, its state and chart version
python manage.py xsm_refresh_columns approvals.Expense --dry-run   # rows whose state columns drifted
python manage.py relay_outbox                      # publish pending integration events (one JSON line each)
python -m pytest tests -q
```

`createsuperuser` without `--noinput` asks for the password interactively
instead. The commands above are run, literally, by
`tests/test_readme_commands.py`.

**Database.** SQLite by default (`approvals.sqlite3` next to `manage.py`;
`APPROVALS_DB=/path/file.sqlite3` moves it). Set
`DATABASE_URL=postgresql://user:password@host:5432/dbname` to use Postgres
instead (install `psycopg`); every command above, the test suite included,
then runs against it. On Postgres the default row lock is a real
`SELECT ... FOR UPDATE`; on SQLite it serialises writers on the database
write lock.

In the admin, create the groups `legal` and `finance` and put a user in
each. Open an expense as either user: you only see the buttons your role
can press. A request that forges another event is refused on POST. Watch
`/expenses/<id>/` in a second tab while you approve.
The page updates whether the approval came from the admin, the REST
API or another socket: every committed transition is pushed to the
row's subscribers.

**Windows.** `runserver` is daphne (the `daphne` app is installed). On
Windows, daphne stalls authenticated DRF requests: the request never
returns. Linux and macOS are not affected, and this is not caused by
this library. On Windows, serve the app with uvicorn instead:
`uvicorn config.asgi:application --port 8000` (`pip install uvicorn`).
The end-to-end test does the same.

## What it shows

- **Parallel regions**: the expense is approved only when both regions
  reach their final state (`onDone`).
- **Permissions in the chart**: `RoleGuard` / `AnyOf`, enforced the same
  way by `send()`, the admin buttons, the API (403) and the WebSocket.
- **Audit in the same transaction**: every attempt is recorded in
  `TransitionLog`, refused ones included, with the actor and the reason.
- **Durable timers**: the 48 h `after` is a row in the deadlines table;
  `xsm_deadlines` fires it even if nobody touches the expense.
- **Integration event (transactional outbox)**: `approved` is tagged
  `publish`. `Expense.statechart_plugins` attaches
  `OutboxPlugin(DjangoOutboxStore(), topic="approvals")`, so the outbox
  row is written in the same transaction as the approval. Either both
  commit or neither does: if the outbox `INSERT` fails, the `send()`
  raises and the approval rolls back. `manage.py relay_outbox` publishes
  pending rows. Delivery is **at-least-once**: a row is marked sent only
  after `publish()` returns, so a crash between the two re-sends the
  *same* envelope `id`, and consumers dedup on it.
- **Audit changelist**: `/admin/xsm_django/transitionlog/` lists every
  attempt and filters by disposition, event and actor. It is read-only
  for everyone, superusers included.

## What it does not do

- **No production settings.** `DEBUG`, the hard-coded `SECRET_KEY`,
  `ALLOWED_HOSTS` and the in-memory channel layer are for a laptop. Use
  your own settings, and a Redis channel layer for more than one process.
- **No real broker.** `relay_outbox` writes to stdout. Give
  `OutboxRelay` your Kafka / NATS / SQS adapter (anything with
  `publish(topic, envelope)`), and run `relay_outbox --forever` under
  your process manager. Purge old sent rows with
  `DjangoOutboxStore().purge_sent(older_than_s=...)`.
- **No service for the deadlines.** `xsm_deadlines --forever` is a
  foreground loop; run it under your process manager (systemd, a
  container). With Celery, schedule the same scan instead:
  `DurableTimerScheduler(app, DjangoModelStore(Expense), machine_for_key)`
  plus `app.conf.beat_schedule = xsm_deadlines_every(scheduler)`
  (`xstate_statemachine.contrib.celery`); that runs the scanner as a
  Beat task, not this command.
- **No user or group setup.** The `legal` / `finance` groups and their
  members are created by you in the admin (or by the tests).
- **No separate frontend origin.** The WebSocket is wrapped in
  `AllowedHostsOriginValidator`, which reads `ALLOWED_HOSTS`. A frontend
  served from another origin needs `OriginValidator(app, [origin])`.
  Note that `ALLOWED_HOSTS = ["*"]` accepts every origin.
- **No login page of its own.** The status page and the API use the
  admin's session login.
