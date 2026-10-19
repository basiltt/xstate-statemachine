---
title: Coming from python-statemachine
description: Port a python-statemachine 3.x chart to xstate-statemachine. A concept map, a worked traffic light with a guard, a nested state and a timeout, what maps one to one, what differs, and what you gain.
---

If you already write `class Light(StateChart)` with `cycle = green.to(yellow)`, you already know most of this library's class syntax: the Pythonic API deliberately uses the same spelling. This page is the short route from one to the other. For a feature-by-feature comparison and when to stay with python-statemachine, read [vs python-statemachine](../vs-python-statemachine/) first.

This page was checked against python-statemachine 3.2.x.

## Concept map

| Concept | python-statemachine 3.x | xstate-statemachine |
|:--|:--|:--|
| Machine class | `class M(StateChart)` | `class M(StateMachine)` |
| States | `State(initial=True)`, `State(final=True)` | identical |
| Nested and parallel states | `class paid(State.Compound)`, `State.Parallel` | identical spelling |
| Event from the attribute name | `cycle = green.to(yellow)` is event `cycle` | same attribute, event `CYCLE` |
| Several arms for one event | `a.to(b) \| b.to(c)` | identical |
| Guard | `cond="ok"`, `unless="blocked"` | `guard="ok"` (decorate with `@guard`), `guard="!blocked"` |
| Convention hooks | `on_enter_<state>`, `on_exit_<state>`, `before_<event>`, `on_<event>`, `after_<event>`, `on_enter_state`, `on_transition` | identical names |
| Arguments | injected by name from `send(**kwargs)` plus `event`, `source`, `target`, `state` | injected by name: payload fields plus `context`, `event`, `interpreter`, `source`, `target`, `state` |
| Start and stop | `sm = M()` | `with M() as sm:` (`async with` on the asyncio engine) |
| Send | `sm.send("cycle", amount=3)` or `sm.cycle(amount=3)` | `sm.send("CYCLE", amount=3)` or `sm.cycle(amount=3)` |
| Return value | a list of callback results | the callback result, `None`, or a list when several ran |
| Introspection | `sm.configuration`, `sm.green.is_active`, `sm.allowed_events` | `sm.configuration`, `sm.green.is_active`, `sm.allowed_events`, plus `sm.state`, `sm.can("CYCLE")`, `sm.matches("red.walk")` |
| Timeout | `State(invoke=timeout(3, on="expire"))` | `State(after={3000: "red"})`, milliseconds |
| Data | attributes on the instance or a model | `context` dict (`initial_context`); this is what snapshots store |
| Event with no enabled transition | `TransitionNotAllowed` or ignored, per `allow_event_without_transition` | ignored; `strict = True` raises `TransitionNotAllowedError` |
| Missing callback | `InvalidDefinition` when instantiated | `ImplementationMissingError` when instantiated |
| Listeners | `listeners=[...]` | `plugins=[...]` ([Plugins](../plugins/)) |
| Diagram | `f"{sm:mermaid}"` | `M.create_machine().to_mermaid()`, `xsm diagram` ([Diagrams](../diagrams/)) |
| Persist on a model | `MachineMixin`, `state_field_name` | [Persistence](../persistence/), `StatechartMixin` for [SQLAlchemy](../integration-sqlalchemy/) and [Django](../integration-django/) |
| Load from a file | `statemachine.io.load("x.yaml")` | `create_machine(config)` from XState JSON ([JSON Configuration](../json-config/)) |

## A worked port: traffic light

The chart has three states. `green` moves to `yellow` on `cycle` only when a guard allows it. `yellow` is a timeout: it moves to `red` on its own. `red` is a compound state with two children, `stopped` and `walk`, and a `pedestrian` event that switches between them.

### Theirs: python-statemachine

This is not executed here.

```text
from statemachine import State, StateChart
from statemachine.contrib.timeout import timeout


class TrafficLight(StateChart):
    green = State(initial=True)
    yellow = State(invoke=timeout(3, on="expire"))

    class red(State.Compound):
        stopped = State(initial=True)
        walk = State()
        pedestrian = stopped.to(walk)

    cycle = green.to(yellow, cond="can_cycle") | yellow.to(red) | red.to(green)
    expire = yellow.to(red)

    count = 0

    def can_cycle(self, amount=1):
        return amount < 10

    def on_cycle(self, amount=1):
        self.count += amount
        return f"counted {amount}"

    def on_enter_red(self):
        print("Don't move.")


sm = TrafficLight()
sm.send("cycle", amount=99)   # None: the guard said no, the machine stays in green
sm.send("cycle", amount=2)    # [None, 'counted 2'] in 3.x; now in yellow
# ...three seconds later the timeout fires: now in red.stopped
sm.pedestrian()               # red.walk
sm.cycle()                    # back to green
```

### Ours

The same machine. Only four things changed: the base class, `cond=` became `guard=` (with `@guard`), the timeout became `after=` in milliseconds, and the data lives in `context` instead of an instance attribute.

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

- **The class body.** `State(initial=True)`, `State(final=True)`, `a.to(b)`, `a.to(b) | b.to(c)`, and nested `State.Compound` / `State.Parallel` classes work as you wrote them. A nested class is a valid transition source and target.
- **The attribute is the event.** `pedestrian = stopped.to(walk)` declares the event and the method `light.pedestrian()` in one line. Give an explicit name with `event="WALK_NOW"` when the attribute should not be the event.
- **Convention hooks.** `on_enter_red`, `on_exit_red`, `before_cycle`, `on_cycle`, `after_cycle` and the generic `on_enter_state` / `on_transition` are found by name. Nothing to register.
- **Dependency injection by name.** A callback declares only the arguments it wants. `def can_cycle(self, amount=1)` receives the `amount` sent with the event, and a callback with no parameters receives nothing.
- **Return values.** `light.cycle(amount=2)` gives back what `on_cycle` returned.
- **Introspection.** `light.configuration`, `light.red.is_active`, `light.allowed_events`.
- **Async detection.** One `async def` callback switches the instance to the asyncio engine; `async with` and `await sm.cycle()` then work as you expect.

## What differs

- **Events are `SCREAMING_SNAKE_CASE`, inferred from the attribute name.** `cycle` is `CYCLE`, `send_mail` is `SEND_MAIL`. `light.cycle()` and `light.send("CYCLE")` are the same call, but `light.send("cycle")`, your old spelling, is a different, undeclared event and is **silently ignored**. Set `strict = True` to make it raise (example below).
- **`strict` instead of an exception by default.** python-statemachine raises `TransitionNotAllowed` when no transition is enabled (depending on `allow_event_without_transition`). Here an event that declares no enabled transition is ignored, as in XState. `strict = True` on the class, or `M(strict=True)`, raises `UnknownEventError` for an undeclared event and `TransitionNotAllowedError` for a declared one that no active state can take right now.
- **Callbacks get only the arguments they name.** Same idea, different vocabulary. The injectable names here are the payload fields plus `context`, `event`, `interpreter`, `source`, `target` and `state`. There is no `model` or `machine`: `self` is the instance.
- **Data lives in `context`.** An attribute such as `self.count` works while the process lives, but only `context` is stored in a snapshot and handed to stores, receipts and plugins. Move anything that must survive a restart into `context`.
- **Guards, and actions named in a transition, need a decorator.** `guard="can_cycle"` is resolved against methods marked `@guard` (and `actions=["note"]` against `@action`); a plain method is not picked up for those. Only the naming-convention hooks (`on_enter_<state>`, `on_<event>`, `before_<event>`, `after_<event>`) are found by name alone. A missing one is reported when you instantiate the class, not at the first `send()`.
- **`send()` returns the action result, not a list.** One result comes back as itself, no result as `None`, several as a list.
- **Time is milliseconds, and it is data.** `after={3000: "red"}` replaces `invoke=timeout(3, on="expire")`, and the deadline is part of the snapshot. On the sync engine a due timer fires on the next `send()` or `tick()`, on your thread; on the asyncio engine the loop fires it. See [Delayed Transitions](../delayed-transitions/).
- **The lifecycle is a context manager.** `with TrafficLight() as light:` starts the machine and stops it on exit, exceptions included. For a machine that outlives a block, `light.interpreter.stop()` is the escape hatch. A transition named `start` or `stop` is allowed, but it gets no `sm.stop()` shortcut: send it with `sm.send("STOP")`.

### The lowercase `send()` trap

```python
from xstate_statemachine import State, StateMachine, UnknownEventError


class Switch(StateMachine):
    off = State(initial=True)
    on = State()
    toggle = off.to(on) | on.to(off)


with Switch() as switch:
    switch.send("toggle")  # your old spelling: ignored
    print(switch.state)

with Switch(strict=True) as switch:
    try:
        switch.send("toggle")
    except UnknownEventError as exc:
        print(exc)
```

**Output:**

```
off
Event 'toggle' is not declared by machine 'Switch'. Known events: TOGGLE.
```

## What you gain

The class you just wrote is a front end to a portable statechart, so everything built on the chart comes with it.

- **XState and Stately round-trip.** `TrafficLight.create_machine().to_json()` is XState JSON. Open it in [Stately](../stately-export/), edit it, load it back with `create_machine(config)`.
- **Snapshots and durable timers.** A snapshot holds the state, the context and the pending `after` deadline, so a restarted process resumes the remaining time. See [Snapshots](../snapshots/) and [Persistence](../persistence/).
- **Stores, locks and idempotency.** `persisted()`, optimistic and pessimistic locking and a replayed webhook getting its original receipt: [Persistence](../persistence/) and [Guarantees](../guarantees/).
- **Actors.** Spawned child machines that message each other: [Actors](../actors/).
- **Web and database integrations.** [FastAPI](../integration-fastapi/), [Django](../integration-django/), [SQLAlchemy](../integration-sqlalchemy/), [Flask](../integration-flask/), brokers and Celery, listed on the [integrations journey](../integrations/).
- **Testing.** A `SimulatedClock` makes timers instant and deterministic; the pytest plugin reports state and transition coverage: [Testing](../integration-testing/).

A snapshot of the machine above, taken while it is running:

```python
import json

from xstate_statemachine import State, StateMachine


class Switch(StateMachine):
    initial_context = {
        "flips": 0,
    }

    off = State(initial=True)
    on = State()
    toggle = off.to(on) | on.to(off)

    def on_toggle(self, context):
        context["flips"] += 1


with Switch() as switch:
    switch.toggle()
    snapshot = json.loads(switch.interpreter.get_snapshot())
    print(snapshot["context"], snapshot["state_ids"])
    print(sorted(json.loads(Switch.create_machine().to_json())))
```

**Output:**

```
{'flips': 1} ['Switch.on']
['context', 'id', 'initial', 'states']
```

## Next steps

- [Pythonic API](../pythonic-api/): nested states, strict mode, `after` timers and the full hook list.
- [Quick Start](../quick-start/): the same machine in two minutes, with XState JSON as the alternative route.
- [vs python-statemachine](../vs-python-statemachine/): the feature table and when python-statemachine is the better fit.
