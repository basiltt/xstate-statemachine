---
title: "xstate-statemachine vs python-statemachine"
description: "An honest comparison with python-statemachine: its declarative class API and diagrams, statecharts on both sides, timers, persistence, locking, XState JSON, a side-by-side order lifecycle, and when to choose python-statemachine instead."
permalink: /guide/vs-python-statemachine/
---

# xstate-statemachine vs python-statemachine

[python-statemachine](https://github.com/fgmacedo/python-statemachine) has a clean, declarative, very Pythonic API: states and transitions are class attributes, and callbacks are found by naming convention. Since version 3 its `StateChart` supports compound, parallel and history states and `invoke`, and it has excellent diagram and documentation tooling. It is a real alternative, and on ergonomics it is ahead of us.

{% assign c = site.data.comparisons.python_statemachine %}
The table is generated from [`docs/_data/comparisons.json`](https://github.com/basiltt/xstate-statemachine/blob/main/docs/_data/comparisons.json). Every row carries a source note, and corrections are welcome as PRs against that file. It was checked against {{ c.checked }}; see [{{ c.name }}]({{ c.url }}) for the current state.

## Feature table

| Capability | xstate-statemachine | {{ c.name }} | Source |
|:--|:--|:--|:--|
{% for row in c.rows %}| {{ row.feature }} | {{ row.ours }} | {{ row.theirs }} | {{ row.source }} |
{% endfor %}

<!-- rows (kept in sync by tests/test_comparisons.py): Hierarchy (nested states); Parallel regions; Timers (`after`); Invoked services; Actors / child machines; Async; Locking / concurrent writers; Versioning / migration; Admin / UI; REST / DRF; Audit trail; Visual editor; Typed context; Persistence; XState JSON portability -->

📝 **Where the two really differ.** Both libraries implement statecharts. The difference is where the machine lives and what happens around it. python-statemachine defines the machine as a Python class and keeps it in memory. xstate-statemachine treats the chart as portable XState JSON, and its surrounding pieces (stores, locks, persisted deadlines, web routers) assume that the machine is loaded, changed and saved on each request.

## The same order lifecycle

A cart is checked out, then paid within 15 minutes or it expires, then shipped. It can be cancelled before payment.

### Theirs: python-statemachine

This is not executed here.

```text
from statemachine import State, StateChart
from statemachine.contrib.timeout import timeout

class Order(StateChart):
    cart = State(initial=True)
    awaiting_payment = State(invoke=timeout(900, on="expire"))
    paid = State()
    shipped = State(final=True)
    expired = State(final=True)
    cancelled = State(final=True)

    checkout = cart.to(awaiting_payment, cond="has_items")
    pay = awaiting_payment.to(paid)
    ship = paid.to(shipped)
    expire = awaiting_payment.to(expired)
    cancel = cart.to(cancelled) | awaiting_payment.to(cancelled)

    items = 1
    def has_items(self):
        return self.items > 0

order = Order()
order.send("checkout"); order.send("pay"); order.send("ship")
# The timeout runs in this process; persisting it is up to you.
```

### Ours

The same chart as JSON, run here with `stub_logic`, which satisfies the `hasItems` guard:

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
for event in ("CHECKOUT", "PAY", "SHIP"):
    order.send(event)
assert order.current_state_ids == {"order.shipped"}
order.stop()
```

If you prefer classes to JSON, the [Pythonic API](../pythonic-api/) builds the same chart from Python, and it stays exportable to XState JSON.

## When to choose python-statemachine instead

- You want the **nicest declarative class API** in Python, with strong IDE support for states and events, and you do not need JSON.
- **Diagrams and generated documentation** matter to you: its Graphviz and Mermaid output and its Sphinx extension are excellent.
- The machine lives **in one process**, and persistence is "store the current state on a model field" (`MachineMixin`).
- You want SCXML or YAML import rather than XState JSON.

## When to choose xstate-statemachine

- The chart must round-trip with **XState / Stately**, or run the same in a TypeScript frontend and a Python backend.
- You need **durable `after` deadlines**, snapshots, cross-process locking and idempotency, not only in-memory state.
- You want the web and database plumbing already done: routers for FastAPI, Flask and Litestar, and a [SQLAlchemy](../integration-sqlalchemy/) mixin.
- You need an **actor system** (spawned children that message each other), not only invoked child machines.

See [Integration extras](../integrations-extras/) for everything that ships today.

New to the library? Start with the [integrations journey](../integrations/): pick your path, then a fifteen-minute tutorial.
