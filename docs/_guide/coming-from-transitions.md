---
title: Coming from transitions
description: Port a pytransitions Machine to xstate-statemachine. A concept map, a worked traffic light with a condition, a nested state and a timeout, what maps one to one, what differs, and what you gain.
---

pytransitions attaches a `Machine` to a model object and describes the chart as lists and dicts. Here the chart is a class: states are attributes, transitions are attributes, and callbacks are methods. This page translates one into the other. For a feature-by-feature comparison and when to stay with `transitions`, read [vs transitions](../vs-transitions/) first.

This page was checked against transitions 0.9.3.

## Concept map

| Concept | transitions | xstate-statemachine |
|:--|:--|:--|
| The machine | `Machine(model=obj, states=[...], transitions=[...], initial="a")` | `class M(StateMachine)`; the class is the machine and `with M() as sm:` runs it |
| A state | `"green"` or `{"name": "green", ...}` | `green = State(initial=True)` |
| A transition | `{"trigger": "cycle", "source": "green", "dest": "yellow"}` | `cycle = green.to(yellow)` |
| Trigger name | `cycle` (any case you like) | the attribute name, as the event `CYCLE` |
| Several sources | `"source": ["a", "b"]` | `a.to(c) \| b.to(c)` |
| Wildcard source | `"source": "*"` | a machine-level `on` ([Pythonic API](../pythonic-api/), `machine_root`) |
| Self transition | `"dest": "="` | `s.to(s)` |
| Condition | `conditions="ok"`, `unless="blocked"` | `guard="ok"` (decorate with `@guard`), `guard="!blocked"` |
| Callbacks on a transition | `before=`, `after=`, `prepare=` | `before_<event>`, `on_<event>`, `after_<event>`, or `actions=[...]` |
| Callbacks on a state | `on_enter_<state>`, `on_exit_<state>` | identical names |
| Nesting | `HierarchicalMachine`, `"children": [...]`, `red_stopped` | `class red(State.Compound)`, dotted path `red.stopped` |
| Parallel regions | `HierarchicalMachine` parallel lists | `class m(State.Parallel)` |
| Timeout | `Timeout` state feature, `"timeout": 3, "on_timeout": "cb"` | `State(after={3000: "red"})`, milliseconds |
| Invalid trigger | `MachineError`, or ignored with `ignore_invalid_triggers=True` | ignored; `strict = True` raises |
| Current state | `model.state` (`"red_walk"`) | `sm.state` (`"red.walk"`), `sm.configuration` |
| State test | `model.is_red()` | `sm.red.is_active`, `sm.matches("red.walk")` |
| Would it fire? | `model.may_cycle()` | `sm.can("CYCLE")` |
| Fire by name | `model.trigger("cycle")` | `sm.send("CYCLE")` |
| Event data | `send_event=True` and an `EventData` argument | name the argument you want: `event`, `source`, `target`, `state`, `context` or a payload field |
| Async, locks | `AsyncMachine`, `LockedMachine` | `async with` on the asyncio engine; locking in [Persistence](../persistence/) |
| Diagrams | `GraphMachine` | `M.create_machine().to_mermaid()`, `xsm diagram` ([Diagrams](../diagrams/)) |
| Build at run time | `machine.add_states(...)`, `add_transition(...)` | `MachineBuilder` ([Pythonic API](../pythonic-api/)) |
| Tags | `Tags` state feature | `State(tags=[...])` |

## A worked port: traffic light

The chart has three states. `green` moves to `yellow` on `cycle` only when a condition allows it. `yellow` is a timeout: it moves to `red` on its own. `red` is a compound state with two children, `stopped` and `walk`, and a `pedestrian` event that switches between them.

### Theirs: transitions

This is not executed here.

```text
from transitions.extensions import HierarchicalMachine
from transitions.extensions.states import Timeout, add_state_features


@add_state_features(Timeout)
class TimeoutHSM(HierarchicalMachine):
    pass


class TrafficLight:
    def __init__(self):
        self.count = 0

    def can_cycle(self, amount=1):  # every callback receives the trigger's kwargs
        return amount < 10

    def count_cycle(self, amount=1):
        self.count += amount

    def on_enter_red(self, **kwargs):  # ... including this one
        print("Don't move.")


states = [
    "green",
    {"name": "yellow", "timeout": 3, "on_timeout": "expire"},
    {"name": "red", "children": ["stopped", "walk"], "initial": "stopped"},
]
light = TrafficLight()
TimeoutHSM(
    model=light,
    states=states,
    initial="green",
    transitions=[
        {
            "trigger": "cycle",
            "source": "green",
            "dest": "yellow",
            "conditions": "can_cycle",
            "before": "count_cycle",
        },
        {"trigger": "expire", "source": "yellow", "dest": "red"},
        {"trigger": "cycle", "source": "yellow", "dest": "red"},
        {"trigger": "cycle", "source": "red", "dest": "green"},
        {"trigger": "pedestrian", "source": "red_stopped", "dest": "red_walk"},
    ],
)

light.cycle(amount=99)  # False: the condition said no, still in green
light.cycle(amount=2)   # True: now in yellow
# ...three seconds later the timer thread fires `expire`: now in red_stopped
light.pedestrian()      # True: red_walk
light.cycle()           # True: back to green
```

### Ours

The same machine, as a class. The chart stopped being data you pass to a constructor and became the class body; the condition moved into a decorated method, the timeout became `after=` in milliseconds, and the counter lives in `context` instead of on the model.

```python
import time

from xstate_statemachine import State, StateMachine, guard

YELLOW_MS = 30  # 3000 in production; short here so the example finishes


class TrafficLight(StateMachine):
    initial_context = {
        "count": 0,
    }

    green = State(initial=True)
    yellow = State(
        after={
            YELLOW_MS: "red",
        }
    )  # the timeout

    class red(State.Compound):  # a nested compound state
        stopped = State(initial=True)
        walk = State()
        pedestrian = stopped.to(walk)

    cycle = (
        green.to(yellow, guard="can_cycle") | yellow.to(red) | red.to(green)
    )

    @guard
    def can_cycle(self, amount=1):
        return amount < 10

    def on_cycle(self, context, amount=1):
        context["count"] += amount
        return f"counted {amount}"

    def on_enter_red(self):
        print("Don't move.")


with TrafficLight() as light:
    print(light.state)
    print(light.cycle(amount=99), light.state)
    print(light.cycle(amount=2), light.state)

    time.sleep(0.1)  # let the timeout come due ...
    light.interpreter.tick()  # ... and fire it (see "What differs")
    print(light.state)

    light.pedestrian()
    print(light.state, light.red.is_active)
    print(light.cycle(), light.state)
    print(light.context)
```

**Output:**

```
green
None green
counted 2 yellow
Don't move.
red.stopped
red.walk True
counted 1 green
{'count': 3}
```

## What maps one to one

- **States, triggers and sources.** Every `{"trigger", "source", "dest"}` dict is one line of `source.to(dest)`. A list of sources is `a.to(c) | b.to(c)`.
- **Per-state callbacks.** `on_enter_red` and `on_exit_red` keep their names and are found by name; nothing to register.
- **Hierarchy.** `HierarchicalMachine` children become nested `State.Compound` classes, and `parallel` regions become `State.Parallel`. Entry and exit run in XState order: exit from the inside out, enter from the outside in.
- **Conditions.** `conditions="can_cycle"` becomes `guard="can_cycle"`; `unless="blocked"` becomes `guard="!blocked"`. The guard receives the trigger's keyword arguments by name, as before.
- **Introspection.** `model.state`, `may_<trigger>()` and `is_<state>()` have direct counterparts (`sm.state`, `sm.can(...)`, `sm.<state>.is_active`).

## What differs

- **The class is the machine, not an add-on.** `Machine(model=obj, ...)` bolts triggers onto an existing object. Here your logic lives on the `StateMachine` subclass. To drive a domain object, keep it in `context`, or hold the machine as an attribute of your object; for stored records, the [SQLAlchemy](../integration-sqlalchemy/) and [Django](../integration-django/) mixins give a model a persisted machine.
- **Events are `SCREAMING_SNAKE_CASE`, inferred from the attribute name.** The trigger `cycle` becomes the attribute `cycle` and the event `CYCLE`. `light.cycle()` and `light.send("CYCLE")` are the same call. `light.send("cycle")`, the lowercase trigger name, is a different, undeclared event and is silently ignored unless `strict` is on (below). Override the name with `event="..."`.
- **Callbacks get only the arguments they name.** In `transitions`, the trigger's arguments are passed to **every** callback in the chain, so `on_enter_red` had to become `on_enter_red(self, **kwargs)` just because `cycle(amount=2)` was called; the alternative is `send_event=True` and an `EventData` parameter. Here `on_enter_red(self)` receives nothing, and `can_cycle(self, amount=1)` receives `amount`.
- **`send()` returns the action results, not a bool.** A `transitions` trigger returns `True` or `False`: did the transition happen. Here the call returns what the callbacks returned (`"counted 2"`), `None` when nothing returned, or a list when several did. To know whether the machine moved, read `light.state` or ask `light.can("CYCLE")` first.
- **`strict` instead of `MachineError`.** `transitions` raises `MachineError` for a trigger that is invalid in the current state, unless `ignore_invalid_triggers=True`. Here such an event is ignored, as in XState. `strict = True` on the class (or `TrafficLight(strict=True)`) raises `TransitionNotAllowedError` for a declared event no active state can take, and `UnknownEventError` for one the chart never declared.
- **Nested names use dots.** `red_stopped` is `red.stopped`, and `light.state` returns the dotted path.
- **A timeout is a deadline, not a thread.** `Timeout` starts a `threading.Timer` in the current process. `after={3000: "red"}` is a deadline recorded in the machine and in its snapshot. On the sync engine a due timer fires on the next `send()` or `tick()` on your thread; on the asyncio engine the loop fires it. See [Delayed Transitions](../delayed-transitions/).
- **Guards need a decorator.** `guard="can_cycle"` is resolved against methods marked `@guard` (and `actions=["..."]` against `@action`). Only the naming-convention hooks (`on_enter_<state>`, `on_<event>`, `before_<event>`, `after_<event>`) are found by name alone. A missing one is reported when you instantiate the class.
- **The lifecycle is a context manager.** `with TrafficLight() as light:` starts the machine and stops it on exit, exceptions included. For a machine that outlives a block, `light.interpreter.stop()` is the escape hatch.
- **The chart is fixed when the class is defined.** There is no `add_states()` at run time; build dynamic charts with `MachineBuilder`.

## What you gain

- **XState and Stately round-trip.** `TrafficLight.create_machine().to_json()` is XState JSON; edit it in [Stately](../stately-export/) and load it back with `create_machine(config)`. A `transitions` machine has no portable definition.
- **Snapshots and durable timers.** The state, the context and the pending `after` deadline are one JSON snapshot, so a restart resumes the remaining time instead of losing a thread: [Snapshots](../snapshots/), [Persistence](../persistence/).
- **Stores, locks and idempotency.** Optimistic and pessimistic locking and replay-safe webhooks: [Persistence](../persistence/) and [Guarantees](../guarantees/).
- **Actors.** Spawned child machines that message each other: [Actors](../actors/).
- **Web and database integrations.** [FastAPI](../integration-fastapi/), [Django](../integration-django/), [SQLAlchemy](../integration-sqlalchemy/), [Flask](../integration-flask/), brokers and Celery, on the [integrations journey](../integrations/).
- **Typed, validated context.** The [Pydantic](../integration-pydantic/) extra validates the context on every change instead of leaving free attributes on a model.
- **Testing.** A `SimulatedClock` makes timers instant and deterministic, and the pytest plugin reports state and transition coverage: [Testing](../integration-testing/).

A strict machine shows the difference in the failure mode:

```python
from xstate_statemachine import (
    State,
    StateMachine,
    TransitionNotAllowedError,
)


class Door(StateMachine):
    strict = True  # the counterpart of transitions' default MachineError

    closed = State(initial=True)
    opened = State()
    open = closed.to(opened)
    close = opened.to(closed)


with Door() as door:
    door.open()
    try:
        door.open()  # already open
    except TransitionNotAllowedError as exc:
        print(exc)
    print(door.state)
```

**Output:**

```
Can't 'OPEN' when in 'opened': no enabled transition for this event (strict mode).
opened
```

## Next steps

- [Pythonic API](../pythonic-api/): nested states, strict mode, `after` timers and the full hook list.
- [Quick Start](../quick-start/): the same machine in two minutes, with XState JSON as the alternative route.
- [vs transitions](../vs-transitions/): the feature table and when `transitions` is the better fit.
