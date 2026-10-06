---
title: "xstate-statemachine vs transitions"
description: "An honest comparison with pytransitions: the HierarchicalMachine extension vs native nesting, timers, persistence, typed context, XState JSON portability, a side-by-side order lifecycle, and when to choose transitions instead."
permalink: /guide/vs-transitions/
---

# xstate-statemachine vs transitions

[transitions](https://github.com/pytransitions/transitions) is the most widely used state machine library in Python. You attach a `Machine` to any object, and it adds trigger methods and a `state` attribute. Extensions add nesting (`HierarchicalMachine`), async, locking, diagrams and timeouts. It is mature and flexible, and this page tries to be fair about that.

{% assign c = site.data.comparisons.transitions %}
The table is generated from [`docs/_data/comparisons.json`](https://github.com/basiltt/xstate-statemachine/blob/main/docs/_data/comparisons.json). Every row carries a source note, and corrections are welcome as PRs against that file. It was checked against {{ c.checked }}; see [{{ c.name }}]({{ c.url }}) for the current state.

## Feature table

| Capability | xstate-statemachine | {{ c.name }} | Source |
|:--|:--|:--|:--|
{% for row in c.rows %}| {{ row.feature }} | {{ row.ours }} | {{ row.theirs }} | {{ row.source }} |
{% endfor %}

<!-- rows (kept in sync by tests/test_comparisons.py): Hierarchy (nested states); Parallel regions; Timers (`after`); Invoked services; Actors / child machines; Async; Locking / concurrent writers; Versioning / migration; Admin / UI; REST / DRF; Audit trail; Visual editor; Typed context; Persistence; XState JSON portability -->

📝 **Nesting.** In transitions, nesting is an extension: you switch from `Machine` to `HierarchicalMachine`, and nested states are addressed as `"parent_child"` strings. Here, compound and parallel states are the default model, with XState v5 semantics for entry and exit order, `done.state` events and history.

📝 **Persistence.** A transitions machine is its model object, so persisting it means pickling the object or storing `model.state` yourself, and timers (`Timeout`) live in a thread of the current process. Here, a snapshot includes the context and pending `after` deadlines, and the stores add locking, idempotency and a scanner that fires deadlines after a restart.

## The same order lifecycle

A cart is checked out, then paid within 15 minutes or it expires, then shipped. It can be cancelled before payment.

### Theirs: transitions

This is not executed here.

```text
from transitions import Machine
from transitions.extensions.states import Timeout, add_state_features

@add_state_features(Timeout)
class TimeoutMachine(Machine):
    pass

class Order:
    items = 1
    def has_items(self):
        return self.items > 0

states = ["cart",
          {"name": "awaiting_payment", "timeout": 900, "on_timeout": "expire"},
          "paid", "shipped", "expired", "cancelled"]
order = Order()
TimeoutMachine(model=order, states=states, initial="cart", transitions=[
    {"trigger": "checkout", "source": "cart", "dest": "awaiting_payment",
     "conditions": "has_items"},
    {"trigger": "pay", "source": "awaiting_payment", "dest": "paid"},
    {"trigger": "ship", "source": "paid", "dest": "shipped"},
    {"trigger": "expire", "source": "awaiting_payment", "dest": "expired"},
    {"trigger": "cancel", "source": ["cart", "awaiting_payment"], "dest": "cancelled"},
])
order.checkout(); order.pay(); order.ship()
# The 900 s timeout is a threading.Timer in this process; a restart loses it.
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
order.send("CHECKOUT")
order.send("PAY")
order.send("SHIP")
assert order.current_state_ids == {"order.shipped"}
snapshot = order.get_snapshot()          # JSON: state, context and deadlines
order.stop()
```

The `after` deadline is part of `snapshot`. With a store and `DueTimerScanner`, it fires even when no process kept the order in memory. See [Persistence](../persistence/).

## When to choose transitions instead

- You want to **add a state machine to an existing class** with the least ceremony, and trigger methods such as `order.pay()` read naturally in your code.
- Your machine is **mostly flat**, lives in one process, and never needs to survive a restart mid-timer.
- You value a very large user base, a long track record and many answered questions.
- You want in-process Graphviz or Mermaid diagrams, and you do not need a visual editor.

## When to choose xstate-statemachine

- The chart must be **portable XState JSON**, edited in Stately and shared with a TypeScript frontend.
- You need **durable timers**, snapshots and cross-process locking, not only in-memory state.
- Nesting, parallel regions, `invoke` and actors are the core of the design, not add-ons.
- You want **typed, validated context and events** (the `[pydantic]` extra) instead of free attributes on a model.

See [Integration extras](../integrations-extras/) for the web and database integrations.

New to the library? Start with the [integrations journey](../integrations/): pick your path, then a fifteen-minute tutorial.
