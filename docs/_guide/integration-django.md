---
title: "Django integration"
description: "A real statechart on a Django model: StatechartField, transaction + row-lock sends, signals, an audit log in the same transaction, permission guards, admin buttons, management commands and a django-fsm migration."
---

# Django

Django is where most Python state machines live, and they are usually flat: one status column, a handful of `@transition` methods, no nesting, no timers. This extra puts a **real statechart on a model**, with hierarchy, parallel regions, `after`, `invoke` and actors. `order.send("PAY")` runs in `transaction.atomic()` with a row lock. The audit row commits in the same transaction as the state change. Permissions are guards in the chart, so the admin, DRF and Channels all ask the same question: "may *this* user do it?". There is also a mechanical migration from `django-fsm-2`.

REST (`[drf]`) and WebSocket (`[channels]`) surfaces are on the [DRF & Channels](../integration-drf/) page.

## Install

```bash
pip install "xstate-statemachine[django]"
```

```python
INSTALLED_APPS = [..., "django.contrib.contenttypes", "xstate_statemachine.contrib.django"]
```

Requires Django `>=4.2`. Run `python manage.py migrate` to create the app's tables (`xsm_django_*`: deadlines, audit log, outbox, idempotency, `DjangoStore`). Tested versions are in the [compatibility table](#compatibility).

For a complete, runnable project -- parallel legal/finance review, `PermissionGuard` with two roles, admin transition buttons with an audit inline, a DRF viewset with schema, a Channels status page, an `after` escalation through the deadlines table and a test suite -- see the [`django_approvals` example](https://github.com/basiltt/xstate-statemachine/tree/main/examples/integrations/django_approvals).

## Quick start

<!-- doc-requires: django -->
```python
import django
from django.conf import settings

settings.configure(
    INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth",
                    "xstate_statemachine.contrib.django"],
    DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
    DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
)
django.setup()

from django.core.management import call_command
from django.db import connection, models
from xstate_statemachine import MachineLogic
from xstate_statemachine.contrib.django import StatechartField, StatechartModelMixin

def record(i, ctx, e, a):
    ctx["paid"] = e.payload["amount"]

class Order(StatechartModelMixin, models.Model):
    statechart_machine = {
        "id": "order", "initial": "cart", "context": {"paid": 0},
        "states": {
            "cart": {"on": {"CHECKOUT": "review"}},
            "review": {"type": "parallel", "onDone": "approved", "states": {
                "legal": {"initial": "pending", "states": {
                    "pending": {"on": {"LEGAL_OK": "ok"}}, "ok": {"type": "final"}}},
                "finance": {"initial": "pending", "states": {
                    "pending": {"on": {"FINANCE_OK": "ok"}}, "ok": {"type": "final"}}}}},
            "approved": {"after": {"86400000": "expired"},
                         "on": {"PAY": {"target": "paid", "actions": "record"}}},
            "expired": {}, "paid": {"type": "final"}}}
    statechart_logic = MachineLogic(actions={"record": record})
    statechart = StatechartField()      # + statechart_state / _state_ids / _version ...

    class Meta:
        app_label = "shop"

call_command("migrate", verbosity=0)
with connection.schema_editor() as editor:     # in a project: makemigrations
    editor.create_model(Order)

order = Order.objects.create()                 # initial snapshot built on insert
order.send("CHECKOUT")                         # atomic() + select_for_update()
assert Order.objects.in_state("order.review").get() == order
order.send("LEGAL_OK")
order.send("FINANCE_OK")
assert order.state == "order.approved" and order.can("PAY")
assert order.send("PAY", amount=42).changed
assert Order.objects.filter(statechart__state="order.paid").count() == 1
assert order.machine.context["paid"] == 42
assert [h.event for h in order.history] == [       # the audit trail, same transaction
    "CHECKOUT", "LEGAL_OK", "FINANCE_OK", "done.state.order.review", "PAY"]
```

## Reference

### `StatechartField`

```text
StatechartField(*, max_snapshot_bytes=1 MiB, state_max_length=512, denormalize=True)
```

A `JSONField` holding the snapshot dict. `contribute_to_class` adds four ordinary sibling fields, so `makemigrations` works normally (and a second run finds nothing):

| Column | Type | Meaning |
|:--|:--|:--|
| `<name>_state` | `CharField`, indexed | sorted, comma-joined active leaf ids (`order.review.finance.pending,order.review.legal.pending`) |
| `<name>_state_ids` | `JSONField` | the leaf ids as a list |
| `<name>_version` | `PositiveIntegerField` | bumped on every write; the optimistic fence |
| `<name>_machine_version` | `CharField` | the chart's `version` when last written |

Lookups: `filter(statechart__state="order.paid")` and `statechart__state__in=[...]` compile to the indexed column. The snapshot is size-checked on write **and** read (X0.4, `SnapshotTooLargeError`). The column layout matches the [SQLAlchemy](../integration-sqlalchemy/) extra, so one schema serves both ORMs.

### `StatechartModelMixin`

| Class attribute | Default | Meaning |
|:--|:--|:--|
| `statechart_machine` | — | JSON path (relative to the model module or `BASE_DIR`), config dict, `MachineNode`, or a dotted callable `"shop.charts:order"` |
| `statechart_logic` | `None` | `MachineLogic`, a dotted callable returning one, or a dotted module bound by name (`LogicLoader`) |
| `statechart_lock` | `"pessimistic"` | default lock mode for `send()` |
| `statechart_audit` | `None` | write `TransitionLog` rows (on when the app and `contenttypes` are installed) |
| `statechart_plugins` | `()` | extra plugins per send: a list, or `(row) -> list` |
| `statechart_migrator` / `statechart_on_version_mismatch` | `None` | forwarded to `from_snapshot` (#263) |
| `statechart_initialize` | `True` | build the initial snapshot on insert (entry actions run once, at creation) |
| `statechart_forget_log` | `"redact"` | X0.5 choice for the audit trail on `forget_statechart()` |

Methods and properties:

- **`send(event, *, lock=None, actor=None, reason=None, plugins=(), using=None, **payload) -> Receipt`**. Apply the event and write the row. `lock="pessimistic"` locks the row first (`select_for_update()`; on SQLite a no-op `UPDATE` takes the write lock, because SQLite has no row locks). `"optimistic"` writes `UPDATE ... WHERE <field>_version = expected` and raises `ConflictError` when it loses. `"none"` means last writer wins. `actor` travels as `actor_id` in the payload and is visible to `PermissionGuard`. `reason` goes to the audit row.
- **Lock errors and deleted rows.** Lock errors are recognised by SQLSTATE (`55P03` lock timeout, `40P01` deadlock, `40001` serialization failure) or, for drivers without one, an anchored phrase (`database is locked`, `Lock wait timeout exceeded`) -- a table named `locked_orders` is never a lock error. On Postgres `LockTimeoutError.timeout` reports the session's `lock_timeout` (0 means *wait forever*: set `SET lock_timeout = '2s'` per connection for pessimistic sends from web code; a deadlock still aborts one side and is retryable). A row **deleted** while `send()` ran raises `Model.DoesNotExist`, never a `ConflictError` that `send_with_retry` would retry. `lock="none"` is last-writer-wins for the snapshot, but `<field>_version` still only moves forward.
- **`QuerySet.update(statechart=...)` / `bulk_update`** bypass the mixin: the denormalised columns are NOT recomputed. Run `manage.py xsm_refresh_columns app.Model` (or `refresh_statechart_columns` in a data migration) afterwards.
- **`asend(...)`**. For async views. The whole locked section runs in one `sync_to_async(thread_sensitive=True)` call. There is no native async `select_for_update`, so never split the ORM calls across awaits.
- **`can(event, *, actor=None, **payload)`**, **`available_events`**, **`available_events_for(actor)`**. Guards run. Nothing is written.
- **`machine`** (an unstarted interpreter restored from the snapshot), **`state`**, **`state_ids`**, **`matches(state_id)`**, **`history`** (`TransitionLog` rows by `seq`).
- **`forget_statechart()`**. X0.5: clears the snapshot and its deadline rows, and redacts (or deletes) the audit rows. Returns counts.
- **`save()`**. An `UPDATE` never rewrites the statechart columns unless you name them in `update_fields`. Only `send()` moves the state, so saving a stale instance for another field cannot roll the state back.
- **`Model.objects.in_state(*ids)`**. Rows where any id is active, as a leaf or as an ancestor (`in_state("order.review")` matches `order.review.legal.pending`). It matches whole id segments with bound parameters (no `LIKE`, no SQL built from the id).

**`send_with_retry(row, event, *, retries=10, backoff=None, lock="optimistic", **kw)`** reloads the statechart columns and re-applies the event on `ConflictError` (the optimistic fence was lost) or `LockTimeoutError` (a pessimistic writer waited out the database's busy timeout -- the driver's `OperationalError` is mapped, never leaked). When the retries run out, the last error is raised with `attempts` set. Under retry, actions may run once per attempt (X0.3).

### Durable timers and `xsm_deadlines`

Every armed `after` timer is a row in `xsm_django_statechartdeadline` (`source` = the model's table, `key` = pk). The row is written in the send's transaction and cleared when the state is exited. `python manage.py xsm_deadlines [app.Model ...] [--forever] [--interval 1] [--limit 1000] [--now EPOCH]` runs `DueTimerScanner` over that index: one pass by default (cron), or a loop with `--forever` that finishes its current pass and exits 0 on `SIGINT` / `SIGTERM`. A matured timer fires in an interpreter restored from the row, and the result is written back under the `<field>_version` fence, so a request racing the scanner cannot lose an update. `DjangoModelStore(Model)` is that `StateStore` view if you drive the scanner yourself.

### `DjangoStore`

`DjangoStore(namespace="default", *, using="default", lock_ttl_s=60, codec=None, max_snapshot_bytes=1 MiB)` is the A2 `StateStore` on the ORM. It passes the same contract suite as `SQLiteStore`. `lock()` is a lease row that is portable across databases. Calls inside a `transaction.atomic()` (or `store.transaction()`) join it. `due_keys()` feeds `DueTimerScanner` from the index.

### Migrations

The app ships its migrations (`migrate xsm_django zero` reverses them). Your own model's sibling columns are ordinary fields in **your** migrations; a field named `workflow` gets `workflow_state`, `workflow_state_ids`, ... and the index on `workflow_state`.

**Renaming a `StatechartField`:** `makemigrations` asks once per column ("Was doc.workflow renamed to doc.flow?", then `workflow_state` → `flow_state`, ...). Answer **yes to all five**. Answering no to a sibling drops that column and adds an empty one, which loses the denormalised state until you refresh it (below).

`refresh_statechart_columns(Model, "statechart", *, batch=1000, migrate=None, dry_run=False)` recomputes the sibling columns after a chart change, a bulk import or a raw SQL edit. It reads rows in primary-key batches (bounded memory), skips rows that are already right, and returns how many it changed. With `migrate=`, it rewrites each snapshot first (on a deep copy) and bumps its version. In a migration:

```text
operations = [refresh_statechart_columns_op("shop", "Order", migrate=rename_state)]
```

From the shell: `python manage.py xsm_refresh_columns shop.Order [--batch 1000] [--dry-run]`.

### Signals

`from xstate_statemachine.contrib.django.signals import pre_transition, post_transition, statechart_error`

| Signal | Arguments | Notes |
|:--|:--|:--|
| `pre_transition` | `instance, event, from_states, actor, using` | raise `TransitionVetoed` to answer `Receipt(denied=True)`: no state change, no audit row |
| `post_transition` | `instance, event, receipt, from_states, to_states, actions, actor, using` | inside the transaction: a receiver that raises rolls back the state **and** its audit row. `post_transition.connect(fn, on_commit=True)` defers `fn` to `transaction.on_commit`, which is **the only safe place for external side effects** |
| `statechart_error` | `instance, kind, error` | `kind` is `"action"`, `"service"` or `"chain_budget"` |

### Audit

`TransitionLog` stores `content_type`/`object_id`, `seq`, `event`, a redacted `payload`, `from_states`, `to_states`, `actions`, `disposition` (`transition` / `denied` / `unhandled` / ...), an `actor` FK, `reason`, `correlation_id`, `machine_version` and `created`. `DjangoAuditPlugin` buffers records while the machine runs. The mixin writes them after the fenced `UPDATE` and before `post_transition`, so a failed insert cannot be swallowed by the engine's plugin containment. Refused attempts are recorded too.

### Permissions

```text
guards={"canApprove": PermissionGuard("shop.approve_order"),
        "isManager":  RoleGuard("managers"),
        "either":     AnyOf(PermissionGuard("shop.approve_order"), RoleGuard("managers"))}
```

- **`PermissionGuard(*perms, object_level=True, fallback_global=True)`** checks `user.has_perm(perm, obj=row)`. Object-level permissions apply when the backend supports them, with a fallback to the global permission. With no actor the guard is `False`.
- **`RoleGuard(*groups, allow_superuser=True)`**, **`AnyOf(...)`**, **`AllOf(...)`**.
- **`has_event_permission(user, instance, event, *, require_enabled=True)`** means `can(event)` as *user* **and** every permission guard on the event passes. Anonymous and inactive users get `False`. The admin, DRF and Channels all call this. **`permitted_events(user, instance)`** lists the events it allows.
- **`StatechartPermission`** is a framework-neutral policy base to subclass.

### Outbox and idempotency

`DjangoOutboxStore()` implements the EDA `OutboxStore` (#293). Its rows join the open `atomic()`, so if a transition rolls back, its outbox row goes with it. Wire it with `statechart_plugins = lambda row: [OutboxPlugin(DjangoOutboxStore())]` and publish with `OutboxRelay`. `DjangoInbox()` is the idempotency `InboxStore`: its claim and mark join the send's transaction.

### Admin

```text
@admin.register(Order)
class OrderAdmin(StatechartAdminMixin, admin.ModelAdmin):
    xsm_confirm_events = ("CANCEL",)
```

The change form shows **one button per event this user may send now**, computed with `has_event_permission`. Each button is its own **CSRF-protected POST form**, rendered after the admin's form. Buttons need no JavaScript. Events tagged `meta.confirm` (or listed in `xsm_confirm_events`) go through a confirmation page with a **reason** field. The reason and `actor=request.user` land in the audit row. The page also gets a `TransitionLogInline` (read-only, newest first, the latest `max_rows = 50`; visible to anyone who may view the row), a state badge with a link to a Mermaid diagram view (active state highlighted, needs `view` permission), a `StateListFilter`, and one bulk action per event that reports `n changed / m denied`. Labels come from `meta.title`, then `description`, then the event id. UI strings use `gettext_lazy`.

A change form looks like this, rendered as text:

```text
Change order                                         [History]
  Title: [ Order 17        ]
  State: legal ✓ · finance pending   (diagram)
  [ Save ] [ Save and continue editing ]
  ── Statechart: order.review.finance.pending ──
  ( Finance OK )  ( Reset… )
  ── Transition history ──
  #2  LEGAL_OK   transition  review.legal.pending → review.legal.ok   alice
  #1  CHECKOUT   transition  cart → review.*                          alice
```

Templates (override in your project): `admin/xsm/change_form.html` (blocks `xsm_badge`, `xsm_transitions`), `admin/xsm/confirm_transition.html` (block `xsm_confirm_form`), `admin/xsm/diagram.html` (block `xsm_mermaid_script` loads Mermaid if you want it rendered; add its origin to your CSP).

### Management commands

| Command | Same output as |
|:--|:--|
| `xsm_inspect app.Model [pk] [--json] [--no-events] [--plain]` | `xsm inspect <chart.json>` (plus the row's state with *pk*) |
| `xsm_diagram app.Model [-f mermaid\|plantuml\|ascii] [-o out]` | `xsm diagram` |
| `xsm_docs app.Model [-o dir]` | `xsm docs` |
| `xsm_simulate app.Model [-e A,B,+500] [--json]` | `xsm simulate` (stub logic, no database) |
| `xsm_deadlines [app.Model ...] [--forever] [--interval S] [--limit N]` | the durable-timer scanner |
| `xsm_refresh_columns app.Model [--batch N] [--dry-run]` | `refresh_statechart_columns` |
| `xsm_snapshots app.Model [--stale] [--json]` | rows and their `machine_version` |
| `xsm_migrate_fsm app.Model --field state [--dry-run] [--write-chart P]` | see below |

The output of the first four matches `xsm` byte for byte, and the tests pin that. A bad label or option, or an unmigrated database, is a `CommandError` (exit status 1), not a traceback. Charts given as a dict or a callable are written to a temporary JSON file first.

## Coming from django-fsm-2

| django-fsm-2 | here |
|:--|:--|
| `state = FSMField(default="new")` | `statechart = StatechartField()` + `statechart_machine = "machines/order.json"` |
| `@transition(field=state, source="new", target="paid")` | `"new": {"on": {"PAY": "paid"}}` in the chart |
| `conditions=[is_paid]` | a named guard: `"guard": "isPaid"` |
| `permission="shop.pay"` | `PermissionGuard("shop.pay")` |
| `can_proceed(order.pay)` | `order.can("PAY")` |
| `get_available_user_state_transitions(user)` | `permitted_events(user, order)` |
| `order.pay(); order.save()` | `order.send("PAY", actor=user)` (one transaction) |
| `ConcurrentTransitionMixin` | `lock="optimistic"` + `send_with_retry` (or the default row lock) |
| `pre_transition` / `post_transition` | the same names, inside the transaction; `on_commit=True` for side effects |
| django-fsm-log | `TransitionLog`, written in the same transaction |
| fsm_admin buttons | `StatechartAdminMixin` |

`python manage.py xsm_migrate_fsm shop.Order --field state --dry-run` extracts the chart from your `@transition` decorators. The same command without `--dry-run` fills the snapshots, batched and resumable, and `FSMDualWriteMixin` keeps the old column in sync for one release. The four steps are on [vs django-fsm](../comparisons/vs-django-fsm/#migration-recipe). `from_state_ids(machine, ids, context)` in `xstate_statemachine.persistence` is the generic "adopt an existing record" primitive underneath, and it works for plain dicts and SQLAlchemy too.

## Guarantees

> **What this does:** a model `send()` is atomic. The snapshot, sibling columns, deadline rows, audit rows, outbox rows and idempotency mark commit together or not at all. By default concurrent sends on one row serialise (16 threads × 100 sends = exactly 1600, pinned on SQLite, and on Postgres with `DATABASE_URL`). The optimistic mode never loses an update: it raises `ConflictError`. A `pre_transition` veto changes nothing. A `post_transition` failure rolls back. Snapshots are size-capped on write and read (X0.4). `forget_statechart()` erases the snapshot and its deadlines and redacts the audit trail (X0.5).
>
> **What this does not do:** it does not make actions exactly-once. Under `send_with_retry`, an action may run once per attempt (X0.3), so put external effects in services, the outbox, or `post_transition(on_commit=True)`. It does not arm in-process timers: `after` fires when `xsm_deadlines` (or the next `send()`) runs. It does not provide a native async row lock (use `asend`). It does not authenticate snapshots edited directly in the database.
>
> See the programme-wide [Guarantees](../guarantees/) and [Security](../security/) pages ([#303](https://github.com/basiltt/xstate-statemachine/issues/303)).

## Threat model

> **Who can call this:** any code holding a model instance can `send()` events. Guards, not the ORM, decide what a *user* may do, so put a `PermissionGuard` / `RoleGuard` on every event that needs one and pass `actor=request.user`. In the admin, anyone with the model's **change** permission sees the buttons that `has_event_permission` allows. Each press is **re-checked on POST**; a POST from a user without the change permission is a 403.
>
> **What it exposes:** the admin transition view is a **POST form with Django's CSRF token** (the admin amendment to X0.7). A GET renders the confirmation form and changes nothing. A POST without the token is 403 (`CsrfViewMiddleware` plus `csrf_protect` on the view). The diagram view needs the **view** permission. The audit log stores the actor, the reason and a **redacted** payload (`password`, `token`, `secret`... masked). Management commands run with the caller's shell rights.
>
> **You must configure:** a permission guard (or your own guard) on every event a user must not send, and `actor=` on every user-driven `send()`. Keep `CsrfViewMiddleware` enabled. Run `xsm_deadlines` if charts use `after`. For external side effects, use `post_transition.connect(..., on_commit=True)` or the outbox.

## Compatibility

| Django | Python | Tested in CI |
|:--|:--|:--|
| 4.2 – 6.1 | 3.9 – 3.14 | ✅ (oldest: Django 4.2 on Python 3.9) |

See the generated [compatibility table](../compatibility/). SQLite runs everywhere. The same suite runs on Postgres when `DATABASE_URL=postgres://...` is set.

## Troubleshooting

| Symptom | Cause | Fix |
|:--|:--|:--|
| `MissingExtraError: ... pip install "xstate-statemachine[django]"` | extra not installed | run the command |
| `no such table: xsm_django_...` | app not migrated | add `"xstate_statemachine.contrib.django"` to `INSTALLED_APPS` and `migrate` |
| `ConflictError` from `send(lock="optimistic")` | another writer won the version fence | use `send_with_retry`, or the default pessimistic lock |
| `LockTimeoutError` from `send()` (SQLite `database is locked`, Postgres `lock timeout`, MySQL `Lock wait timeout`) | a writer waited out the database's busy/lock timeout | retryable -- `send_with_retry` retries it; keep sends short; raise `OPTIONS["timeout"]`; use Postgres for real concurrency |
| `SynchronousOnlyOperation` in an async view | the ORM was called on the event loop | `await order.asend(...)` |
| `SnapshotDriftError` / `MachineVersionMismatchError` after a chart change | stored snapshots predate the chart | register a `SnapshotMigrator` step (`statechart_migrator`), then `xsm_snapshots --stale` and `refresh_statechart_columns` |
| `DoesNotExist` from `send()` | the row was deleted while the send ran | nothing to retry; the caller decides |
| Columns out of step with the snapshot after `QuerySet.update()` / `bulk_update()` | the ORM write bypassed the mixin | `manage.py xsm_refresh_columns app.Model` |
| Admin shows no buttons | the user lacks change permission, or every guard refuses | check `permitted_events(user, obj)` |
