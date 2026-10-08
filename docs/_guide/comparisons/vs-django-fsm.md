---
title: "xstate-statemachine vs django-fsm"
description: "An honest comparison with django-fsm-2: hierarchy, parallel regions, durable timers, locking, admin, audit, XState JSON, a side-by-side order lifecycle, a migration recipe, and when to choose django-fsm instead."
permalink: /guide/vs-django-fsm/
---

# xstate-statemachine vs django-fsm

[django-fsm](https://github.com/viewflow/django-fsm), maintained today as **django-fsm-2**, is the state machine most Django projects already use. It puts a state column on your model and turns model methods into transitions with a `@transition` decorator. It is small, well understood, and has admin buttons and signals. This page compares it with xstate-statemachine and is explicit about where django-fsm is the better choice.

{% assign c = site.data.comparisons.django_fsm %}
The table is generated from [`docs/_data/comparisons.json`](https://github.com/basiltt/xstate-statemachine/blob/main/docs/_data/comparisons.json). Every row carries a source note, and corrections are welcome as PRs against that file. It was checked against {{ c.checked }}; see [{{ c.name }}]({{ c.url }}) for the current state.

✅ **Django status.** The `[django]` extra ships the model field, locking, signals, audit, permissions and the admin ([#280](https://github.com/basiltt/xstate-statemachine/issues/280)–[#282](https://github.com/basiltt/xstate-statemachine/issues/282)); `[drf]` and `[channels]` ship the REST and WebSocket surfaces ([#283](https://github.com/basiltt/xstate-statemachine/issues/283)); `xsm_migrate_fsm` does the migration below ([#310](https://github.com/basiltt/xstate-statemachine/issues/310)). See the [Django integration](../integration-django/) page.

## Feature table

| Capability | xstate-statemachine | {{ c.name }} | Source |
|:--|:--|:--|:--|
{% for row in c.rows %}| {{ row.feature }} | {{ row.ours }} | {{ row.theirs }} | {{ row.source }} |
{% endfor %}

<!-- rows (kept in sync by tests/test_comparisons.py): Hierarchy (nested states); Parallel regions; Timers (`after`); Invoked services; Actors / child machines; Async; Locking / concurrent writers; Versioning / migration; Admin / UI; REST / DRF; Audit trail; Visual editor; Typed context; Persistence; XState JSON portability -->

## The same order lifecycle

A cart is checked out, then paid within 15 minutes or it expires, then shipped. It can be cancelled before payment.

### Theirs: django-fsm

This is not executed here; it needs a Django project.

```text
from django.db import models
from django_fsm import FSMField, transition

class Order(models.Model):
    state = FSMField(default="cart", protected=True)
    items = models.PositiveIntegerField(default=0)

    def has_items(self):
        return self.items > 0

    @transition(field=state, source="cart", target="awaiting_payment",
                conditions=[has_items])
    def checkout(self): ...

    @transition(field=state, source="awaiting_payment", target="paid")
    def pay(self): ...

    @transition(field=state, source="paid", target="shipped")
    def ship(self): ...

    @transition(field=state, source=["cart", "awaiting_payment"],
                target="cancelled")
    def cancel(self): ...

    # The 15-minute expiry is not expressible: schedule a Celery task that
    # calls a hypothetical expire() transition, and cancel it on pay().
```

### Ours

The chart is data, so the timeout lives in it. Here it runs with `stub_logic`, which satisfies the `hasItems` guard:

```python
from xstate_statemachine import SyncInterpreter, create_machine, stub_logic

chart = {
    "id": "order", "initial": "cart",
    "states": {
        "cart": {"on": {"CHECKOUT": {"target": "awaitingPayment", "guard": "hasItems"},
                        "CANCEL": "cancelled"}},
        "awaitingPayment": {"after": {"900000": "expired"},           # 15 minutes
                            "on": {"PAY": "paid", "CANCEL": "cancelled"}},
        "paid": {"on": {"SHIP": "shipped"}},
        "shipped": {"type": "final"},
        "expired": {"type": "final"},
        "cancelled": {"type": "final"},
    },
}
order = SyncInterpreter(create_machine(chart, logic=stub_logic(chart))).start()
order.send("CHECKOUT")
assert order.can("PAY") and not order.can("SHIP")
order.send("PAY")
order.send("SHIP")
assert order.current_state_ids == {"order.shipped"}
order.stop()
```

On a database row, the [sqlalchemy_orders example](https://github.com/basiltt/xstate-statemachine/tree/main/examples/integrations/sqlalchemy_orders) runs this chart with optimistic locking, and the `after` deadline is fired by `DueTimerScanner` for orders nobody touches.

## Migration recipe

The `xsm_migrate_fsm` management command ([#310](https://github.com/basiltt/xstate-statemachine/issues/310)) does these steps mechanically and reversibly:

1. **Extract the chart.** `python manage.py xsm_migrate_fsm shop.Order --field state --dry-run` reads the `@transition` decorators and prints XState JSON on stdout (the recipe goes to stderr, so `--dry-run > order.json` or `| python -m json.tool` works): each `@transition(source=..., target=...)` becomes an `on` entry of its `source` state, keyed by an event named after the method (`checkout` → `CHECKOUT`, with `meta.method` recording the original name); `conditions=` and `permission=` become named guards (implement a permission with `PermissionGuard`); `source="*"` / `"+"` fan out over the states. Review it, then `--write-chart shop/machines/order.json`. Without `manage.py`, `DJANGO_SETTINGS_MODULE=mysite.settings xsm gt --from-django-fsm shop.Order -o shop/machines` writes the same chart as `order.json` (no database access) and generates the logic and runner skeleton from it.
2. **Keep the column.** Add `statechart = StatechartField()` **beside** the `FSMField`, point `statechart_machine` at the chart, and run `makemigrations` / `migrate`.
3. **Fill the snapshots.** `python manage.py xsm_migrate_fsm shop.Order --field state` writes each row's snapshot from its current state value with `from_state_ids()` (nothing runs: no entry actions, no services). It is batched (`--batch 1000`), resumable (only rows with an empty snapshot are touched), idempotent (a second run changes nothing) and safe with the site up (a row a live writer moved meanwhile is left for the next run). A value the chart does not know (a renamed legacy state, a typo, an empty string) is **skipped and reported per value with its row count**, never a traceback halfway; fold renames in with `--map open=new` (repeatable) and run again. A `--map` to a state the chart lacks is refused before any row is touched, and a `--map` whose old value no row holds is flagged as a likely typo.
4. **Dual-read for one release.** Mix `FSMDualWriteMixin` into the model. It is **two-way**: every `send()` also writes the old column, so code that still reads `order.state` keeps working, and old code that still calls an FSM `@transition` method and then `save()` re-adopts the snapshot at the column's new value, so the next `send()` starts from the right state. Then drop the `FSMField`.

**What the extracted chart records.** An FSM value that is not a valid XState key (`"in-progress"`, `"état"`, an `FSMIntegerField`'s `3`) gets a safe key (`in_progress`, `état`, `s_3`; `_2`, `_3` on a clash) and the original value in that state's `meta.fsm_value` -- the data migration and the dual write map back through it exactly, so **regenerate charts written before 0.11.0 with `--write-chart`**. `RETURN_VALUE` / `GET_STATE` targets become one guarded transition per allowed state (guard `<method>Returns` with `params.value`; a dynamic target that lists no states is refused). `on_error` targets are states (`meta.on_error`), `custom={...}` lands in `meta.custom`, and guard names are stable across runs (a lambda is named after its method, e.g. `goPermission`; same-named conditions from different modules get a module prefix). A row adopted into a state with an `after` timer gets a scanner deadline due one delay after the migration (the legacy entry time is unknown). A `context()` hook that raises for a row leaves that row empty and names its pk; the rest of the batch and the run continue.

Code in the transition method body becomes an action, or an `invoke`d service if it can fail; `post_transition` receivers keep working through our own `post_transition` signal (use `on_commit=True` for external side effects).
## When to choose django-fsm instead

- Your states are a **flat list** with a handful of transitions, and you want the smallest possible dependency.
- Your team thinks in model methods, not in a chart, and nobody will open the machine in a visual editor.
- You never need timers, nested or parallel states, or to share the machine with a frontend.

## When to choose xstate-statemachine

- The workflow has **nested or parallel** stages (review ∥ payment, retries inside a stage).
- **Timeouts are part of the business rule** and must fire after a restart.
- The same chart must run in a **React/TypeScript frontend** and be edited in Stately.
- You also run the workflow outside Django: in FastAPI, Flask, a worker or a CLI.

See [SQLAlchemy](../integration-sqlalchemy/) and [Persistence](../persistence/) for how a statechart lives on a database row.

New to the library? Start with the [integrations journey](../integrations/): pick your path, then a fifteen-minute tutorial.
