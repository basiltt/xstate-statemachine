---
title: "xstate-statemachine vs django-fsm"
description: "An honest comparison with django-fsm-2: hierarchy, parallel regions, durable timers, locking, admin, audit, XState JSON, a side-by-side order lifecycle, a migration recipe, and when to choose django-fsm instead."
permalink: /guide/vs-django-fsm/
---

# xstate-statemachine vs django-fsm

[django-fsm](https://github.com/viewflow/django-fsm), maintained today as **django-fsm-2**, is the state machine most Django projects already use. It puts a state column on your model and turns model methods into transitions with a `@transition` decorator. It is small, well understood, and has admin buttons and signals. This page compares it with xstate-statemachine and is explicit about where django-fsm is the better choice.

{% assign c = site.data.comparisons.django_fsm %}
The table is generated from [`docs/_data/comparisons.json`](https://github.com/basiltt/xstate-statemachine/blob/main/docs/_data/comparisons.json). Every row carries a source note, and corrections are welcome as PRs against that file. It was checked against {{ c.checked }}; see [{{ c.name }}]({{ c.url }}) for the current state.

⚠️ **Django status.** The `[django]` extra (model field, admin, DRF, signals) is still in development ([#280](https://github.com/basiltt/xstate-statemachine/issues/280)–[#283](https://github.com/basiltt/xstate-statemachine/issues/283)). Rows below describe what ships today, which is mostly framework-neutral, and mark Django pieces as planned.

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

The planned `xsm_migrate_fsm` management command ([#310](https://github.com/basiltt/xstate-statemachine/issues/310)) will do these steps mechanically. It is **not shipped yet**. Until then, the steps are:

1. **Extract the chart.** Each `@transition(source=..., target=...)` becomes an `on` entry of its `source` state, keyed by an event named after the method (`checkout` → `CHECKOUT`). `conditions=` become named guards, and `source="*"` becomes a transition on the root. Validate the result with `xsm validate order.json --plain`.
2. **Keep the column.** Leave the `FSMField` in place during the move. A data migration writes each row's snapshot from its current state value.
3. **Dual-read.** For one release, read the state from the snapshot and assert that it matches the old column, then drop the column.
4. **Move side effects.** Code in the transition method body becomes an action, or an `invoke`d service if it can fail. `post_transition` receivers become plugin hooks or audit-log readers.

## When to choose django-fsm instead

- Your states are a **flat list** with a handful of transitions, and you want the smallest possible dependency.
- You want Django-native pieces **today**: admin buttons (`fsm_admin`), signals, `has_transition_perm`. Our Django extra is not released yet.
- Your team thinks in model methods, not in a chart, and nobody will open the machine in a visual editor.
- You never need timers, nested or parallel states, or to share the machine with a frontend.

## When to choose xstate-statemachine

- The workflow has **nested or parallel** stages (review ∥ payment, retries inside a stage).
- **Timeouts are part of the business rule** and must fire after a restart.
- The same chart must run in a **React/TypeScript frontend** and be edited in Stately.
- You also run the workflow outside Django: in FastAPI, Flask, a worker or a CLI.

See [SQLAlchemy](../integration-sqlalchemy/) and [Persistence](../persistence/) for how a statechart lives on a database row.
