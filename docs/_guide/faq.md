---
title: "FAQ"
description: "Frequently asked questions about XState-StateMachine for Python."
---

# Frequently Asked Questions

## General

### Is this compatible with XState v5?

Yes. This library is compatible with XState JSON format and supports most XState v4/v5 features, including:

- Hierarchical (nested) states
- Parallel states
- `invoke` (services / actors)
- Guards (`guard` and legacy `cond` keys)
- Actions (entry, exit, and transition actions)
- `after` (delayed transitions)
- `always` (eventless transitions)
- Final states
- Context (extended state)

The JSON format exported from [Stately.ai](https://stately.ai) works directly with this library.

---

### Can I use this without JSON?

Yes! The Pythonic API (introduced in v0.5.0) lets you define machines entirely in Python without any JSON. There are three styles:

**Class-based:**

```python
from xstate_statemachine import StateMachine, State, action, guard

class TrafficLight(StateMachine):
    green = State(initial=True)
    yellow = State()
    red = State()

    next_event = (
        green.to(yellow, event="NEXT")
        | yellow.to(red, event="NEXT")
        | red.to(green, event="NEXT")
    )

    @action
    def log_transition(self, interpreter, context, event, action_def):
        print(f"Transitioned on {event}")

machine = TrafficLight.create_machine()
```

**Builder:**

```python
from xstate_statemachine import MachineBuilder

machine = (
    MachineBuilder("trafficLight")
    .state("green", initial=True)
    .state("yellow")
    .state("red")
    .transition("green", "NEXT", "yellow")
    .transition("yellow", "NEXT", "red")
    .transition("red", "NEXT", "green")
    .build()
)
```

**Functional:**

```python
from xstate_statemachine import State, build_machine

green = State("green", initial=True)
yellow = State("yellow")
red = State("red")

green.to(yellow, event="NEXT")
yellow.to(red, event="NEXT")
red.to(green, event="NEXT")

machine = build_machine(id="trafficLight", states=[green, yellow, red])
```

---

### Which interpreter should I use?

| Use case | Interpreter | Why |
|----------|-------------|-----|
| Web servers (FastAPI, aiohttp) | `Interpreter` (async) | Works with async event loops |
| `invoke` with async services | `Interpreter` (async) | Services need `await` |
| `after` (delayed transitions) | `Interpreter` (async) | Timers need an event loop |
| CLI tools and scripts | `SyncInterpreter` | No event loop needed |
| Django/Flask views | `SyncInterpreter` | Synchronous web frameworks |
| Unit testing | `SyncInterpreter` | Deterministic, no timing issues |
| Simple prototyping | `SyncInterpreter` | Easier to reason about |

**Async example:**

```python
import asyncio
from xstate_statemachine import create_machine, Interpreter

async def main():
    machine = create_machine(config)
    interp = Interpreter(machine)
    await interp.start()
    await interp.send("EVENT")
    await interp.stop()

asyncio.run(main())
```

**Sync example:**

```python
from xstate_statemachine import create_machine, SyncInterpreter

machine = create_machine(config)
interp = SyncInterpreter(machine)
interp.start()
interp.send("EVENT")
interp.stop()
```

---

### Can I use the CLI with machines from Stately.ai?

Yes! Export your machine as JSON from [stately.ai](https://stately.ai), then generate Python code:

```bash
xsm gt your_machine.json --template pythonic-class --async-mode no
```

The CLI reads the XState JSON format that Stately.ai exports and generates complete, runnable Python code.

---

## State Machine Behavior

### How do I handle nested state transitions?

Nested (hierarchical) states are fully supported. A transition defined on a parent state automatically catches events from all its children:

```json
{
  "id": "app",
  "initial": "auth",
  "states": {
    "auth": {
      "initial": "login",
      "states": {
        "login": {
          "on": { "SUBMIT": "verifying" }
        },
        "verifying": {
          "on": { "SUCCESS": "#app.dashboard" }
        }
      },
      "on": {
        "CANCEL": "auth.login"
      }
    },
    "dashboard": {}
  }
}
```

Use `#machineId.stateName` syntax for absolute state references, or relative names for sibling states.

---

### What happens if a guard raises an exception?

If a guard function raises an exception, the transition is **blocked** (treated as if the guard returned `False`). If `LoggingInspector` is attached, the exception is logged:

```python
def risky_guard(context, event):
    # If this raises, the transition won't fire
    return context["user"]["role"] == "admin"  # KeyError if "user" not in context
```

> **Tip:** Write guards defensively using `.get()` or try/except to avoid unexpected blocked transitions.

---

### Can I have multiple machines?

Yes! Create separate `MachineNode` instances and run them with separate interpreters:

```python
from xstate_statemachine import create_machine, SyncInterpreter

machine_a = create_machine(config_a)
machine_b = create_machine(config_b)

interp_a = SyncInterpreter(machine_a)
interp_b = SyncInterpreter(machine_b)

interp_a.start()
interp_b.start()

interp_a.send("EVENT_FOR_A")
interp_b.send("EVENT_FOR_B")

interp_a.stop()
interp_b.stop()
```

For parent-child relationships (actor model), use `invoke` in the parent machine's config to spawn child machines.

---

### What's the difference between actions and guards?

| | Actions | Guards |
|---|---------|--------|
| **Purpose** | Execute side effects (mutate context, call APIs, log) | Decide whether a transition should happen |
| **Return value** | None (actions don't return) | `bool` — `True` to allow, `False` to block |
| **Parameters** | `(interpreter, context, event, action_def)` | `(context, event)` |
| **Async allowed?** | Yes (with `Interpreter`) | No — always synchronous |
| **When called** | After the transition is decided | Before the transition is decided |

---

## Testing

### How do I test state machines?

Use `SyncInterpreter` in tests for synchronous, deterministic execution:

```python
import pytest
from xstate_statemachine import create_machine, SyncInterpreter, MachineLogic

def test_light_switch_toggle():
    """Test that toggling switches between on and off."""
    config = {
        "id": "lightSwitch",
        "initial": "off",
        "context": {"flips": 0},
        "states": {
            "off": {"on": {"TOGGLE": {"target": "on", "actions": "increment"}}},
            "on": {"on": {"TOGGLE": {"target": "off", "actions": "increment"}}}
        }
    }

    def increment(interpreter, context, event, action_def):
        context["flips"] += 1

    logic = MachineLogic(actions={"increment": increment})
    machine = create_machine(config, logic=logic)
    interp = SyncInterpreter(machine)
    interp.start()

    # Initially off
    assert "lightSwitch.off" in interp.current_state_ids

    # Toggle to on
    interp.send("TOGGLE")
    assert "lightSwitch.on" in interp.current_state_ids
    assert interp.context["flips"] == 1

    # Toggle back to off
    interp.send("TOGGLE")
    assert "lightSwitch.off" in interp.current_state_ids
    assert interp.context["flips"] == 2

    interp.stop()


def test_guard_blocks_transition():
    """Test that a guard can prevent a transition."""
    config = {
        "id": "door",
        "initial": "locked",
        "context": {"hasKey": False},
        "states": {
            "locked": {
                "on": {"UNLOCK": {"target": "unlocked", "guard": "hasKey"}}
            },
            "unlocked": {}
        }
    }

    def has_key(context, event):
        return context.get("hasKey", False)

    logic = MachineLogic(guards={"hasKey": has_key})
    machine = create_machine(config, logic=logic)
    interp = SyncInterpreter(machine)
    interp.start()

    # Guard blocks: no key
    interp.send("UNLOCK")
    assert "door.locked" in interp.current_state_ids

    # Give the key and try again
    interp.context["hasKey"] = True
    interp.send("UNLOCK")
    assert "door.unlocked" in interp.current_state_ids

    interp.stop()
```

---

## Environment & Setup

### What Python versions are supported?

Python **3.9** through **3.14**, with full test coverage across all versions. The library uses no features beyond Python 3.9, ensuring broad compatibility.

---

### Are there any dependencies?

**No.** Zero external dependencies. The library is pure standard-library Python. You can install it in any environment without dependency conflicts.

---

### How do I persist machine state?

Use the snapshot system to serialize and restore interpreter state:

```python
from xstate_statemachine import create_machine, SyncInterpreter
import json

# Save state
machine = create_machine(config)
interp = SyncInterpreter(machine)
interp.start()
interp.send("SOME_EVENT")

snapshot = interp.get_snapshot()
serialized = json.dumps(snapshot)

# ... store `serialized` in a database, file, or cache ...

# Restore state later
saved_snapshot = json.loads(serialized)
machine2 = create_machine(config)
interp2 = SyncInterpreter(machine2)
interp2.start(snapshot=saved_snapshot)

print(interp2.current_state_ids)  # Restored to the saved state
```

---

### Can I use this with Django/Flask/FastAPI?

Yes!

**Django / Flask** (synchronous): Use `SyncInterpreter`:

```python
# Django view example
from xstate_statemachine import create_machine, SyncInterpreter

def checkout_view(request):
    machine = create_machine(checkout_config, logic=checkout_logic)
    interp = SyncInterpreter(machine)
    interp.start()
    interp.send("SUBMIT")
    return JsonResponse({"state": list(interp.current_state_ids)})
```

**FastAPI** (async): Use `Interpreter`:

```python
# FastAPI endpoint example
from xstate_statemachine import create_machine, Interpreter

@app.post("/checkout")
async def checkout():
    machine = create_machine(checkout_config, logic=checkout_logic)
    interp = Interpreter(machine)
    await interp.start()
    await interp.send("SUBMIT")
    state = list(interp.current_state_ids)
    await interp.stop()
    return {"state": state}
```

---

## Advanced

### How do I handle timeouts?

Use `after` (delayed transitions) with the async `Interpreter`:

```python
import asyncio
from xstate_statemachine import create_machine, Interpreter

config = {
    "id": "session",
    "initial": "active",
    "states": {
        "active": {
            "after": {
                "30000": "timed_out"
            },
            "on": { "ACTIVITY": "active" }
        },
        "timed_out": { "type": "final" }
    }
}

async def main():
    machine = create_machine(config)
    interp = Interpreter(machine)
    await interp.start()
    # Machine will transition to "timed_out" after 30 seconds of inactivity
    # Sending "ACTIVITY" resets the timer by re-entering "active"
```

> **Warning:** `after` transitions are not supported by `SyncInterpreter`. Use the async `Interpreter` for delayed transitions.

---

### Can I use this for UI state management?

Yes. State machines are excellent for managing UI state — form wizards, modals, navigation flows, loading states, etc. While this is a Python library (not JavaScript), it works well for:

- Server-side rendered UI state (Django templates, Jinja2)
- API-driven UI state (send state to frontend via JSON)
- Desktop apps (Tkinter, PyQt, etc.)

---

### How do I debug my state machine?

See the [Troubleshooting page](./troubleshooting.md#debugging-tips) for detailed debugging strategies. Quick summary:

1. Attach `LoggingInspector` to see all transitions
2. Print `interp.current_state_ids` after each event
3. Print `interp.context` to verify data flow
4. Use `machine.to_mermaid()` to visualize the machine
5. Use `SyncInterpreter` for deterministic, step-by-step debugging

---

### Is there a visual editor?

Yes — [Stately.ai](https://stately.ai) is the visual editor for XState machines. Design your machine visually, export as JSON, and use the `xsm` CLI to generate Python code:

```bash
xsm gt exported_machine.json --template pythonic-class
```

---

### What's the performance overhead?

The library is lightweight with minimal overhead:

- Machine creation: microseconds for typical configs
- Event processing: microseconds per transition
- Memory: proportional to the number of states and transitions
- No background threads or event loops (unless using `Interpreter` with `after`)

For most applications, the state machine overhead is negligible compared to your business logic (database queries, API calls, etc.).

---

### Can I extend the library?

Yes. The plugin system allows you to hook into the interpreter lifecycle:

```python
from xstate_statemachine import PluginBase

class MetricsPlugin(PluginBase):
    def on_transition(self, event, source, target):
        metrics.increment(f"transition.{source}.{target}")

    def on_event(self, event):
        metrics.increment(f"event.{event.type}")

interp.use(MetricsPlugin())
```

You can also subclass `MachineLogic` for custom logic loading, or create your own `LogicLoader` subclass for alternative discovery strategies.
