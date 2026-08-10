---
title: "Testing & The Pure API"
description: "Test machines without an interpreter, and wait on real conditions instead of sleeping."
---

# Testing & The Pure API

Two toolkits make state machines pleasant to test: a **pure, side-effect-free
API** for asking "what would happen if…", and **waiting helpers** that replace
arbitrary `sleep()` calls with real conditions.

## The Pure API

Sometimes you want to compute the next state *without running anything* — no
timers start, no services fire, nothing mutates. That is what the pure API is
for: unit tests, planning, and "preview the next step" UI.

```python
from xstate_statemachine import (
    create_machine, initial_transition, pure_transition, get_next_snapshot,
)

config = {
    "id": "fetch",
    "initial": "idle",
    "context": {},
    "states": {
        "idle": {"on": {"GO": "done"}},
        "done": {"type": "final"},
    },
}
machine = create_machine(config)

snapshot, entry_actions = initial_transition(machine)
next_snapshot, actions = pure_transition(machine, snapshot, "GO")

print(snapshot.state_ids)          # {'fetch.idle'}
print(next_snapshot.state_ids)     # {'fetch.done'}
print(next_snapshot.status)        # 'done'
print([a.type for a in actions])   # the actions that WOULD have run
```

Both functions return a `(snapshot, actions)` tuple. If you only care about the
resulting state, `get_next_snapshot()` returns the snapshot alone:

```python
print(get_next_snapshot(machine, snapshot, "GO").state_ids)   # {'fetch.done'}
```

### `PureSnapshot`

| Member | Description |
|:--|:--|
| `.state_ids` | Set of active state ids |
| `.context` | The context dict |
| `.status` | `'running'`, `'done'` or `'error'` |
| `.output` | Machine output, once a top-level final state is reached |
| `.configuration` | The active `StateNode` objects |
| `.matches(id)` | Test a state id, supporting nested paths |

Snapshots are immutable — each transition returns a new one, so you can branch
from the same starting point repeatedly:

```python
paid = get_next_snapshot(machine, start, "PAY")
cancelled = get_next_snapshot(machine, start, "CANCEL")   # `start` is unchanged
```

> **Note:** the pure API resolves guards and computes actions, but never
> **executes** them. Actions are returned for inspection.

---

## Waiting Helpers

Tests that `sleep(0.5)` and hope are slow and flaky. These helpers poll a real
predicate with a timeout instead.

### `wait_for` — async

```python
import asyncio
from xstate_statemachine import (
    create_machine, Interpreter, MachineLogic, wait_for,
)

async def main():
    interp = await Interpreter(machine).start()
    await interp.send("FETCH")

    # Resolves as soon as the predicate is true; raises on timeout.
    await wait_for(interp, lambda s: s.matches("fetch.success"), timeout=2)

    print(interp.context["user"])
    await interp.stop()

asyncio.run(main())
```

### `wait_for_sync` — blocking

The same contract for `SyncInterpreter`, for use in Django views, Celery tasks,
CLI tools and plain tests:

```python
from xstate_statemachine import wait_for_sync

wait_for_sync(interp, lambda s: s.matches("job.done"), timeout=5)
```

Both accept `timeout` (seconds, default `10.0`) and `poll_interval`
(default `0.005`).

### `to_promise` — await completion

When you just want to run a machine to its final state and get the result:

```python
from xstate_statemachine import to_promise

interp = await Interpreter(machine).start()
await interp.send("START")

output = await to_promise(interp)    # resolves when the machine is done
```

---

## Testing with `SyncInterpreter`

For most tests the sync interpreter is the simplest option — no event loop, no
`async def`, no fixtures:

```python
def test_double_submit_cannot_double_charge():
    checkout = SyncInterpreter(create_machine(config, logic=logic)).start()

    checkout.send("SUBMIT")
    assert checkout.matches("checkout.charging")

    checkout.send("SUBMIT")                        # second click
    assert checkout.matches("checkout.charging")   # ...ignored
```

### Useful assertions

| Call | Asserts |
|:--|:--|
| `interp.matches("a.b")` | A state is active (supports nested paths) |
| `interp.can("SUBMIT")` | An event would actually do something right now |
| `interp.has_tag("busy")` | A tag is present on any active state |
| `interp.current_state_ids` | The exact active leaf set |
| `interp.context` | The live context |

> **Tip:** `can()` is the cleanest way to assert that an event is *correctly
> ignored* — it distinguishes "handled" from "silently dropped" without
> depending on state ids.

---

## See Also

- [Interpreters](../interpreters/) — sync vs async, lifecycle
- [Snapshots](../snapshots/) — persistence and crash recovery
- [Plugins](../plugins/) — observing every transition
