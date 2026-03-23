---
title: Quick Start
description: Build your first state machine in 5 minutes with five different approaches.
---

Pick the style that fits your project. All five approaches produce the same result — a running state machine.

| Option | Best For | Lines of Code |
|--------|----------|:---:|
| [A: Pure Python (Functional)](#option-a-pure-python-functional) | New projects, simple machines | ~20 |
| [B: JSON Configuration](#option-b-json-configuration-xstate-compatible) | XState interop, visual editors | ~25 |
| [C: CLI Code Generation](#option-c-generate-boilerplate-with-cli) | Rapid prototyping from JSON | 1 command |
| [D: Class-Based Style](#option-d-class-based-style) | Large machines, OOP teams | ~30 |
| [E: Builder Style](#option-e-builder-style) | Fluent chaining, dynamic assembly | ~20 |

---

## Option A: Pure Python (Functional)

> **Recommended for new projects.** No JSON, no boilerplate — just Python.

```python
from xstate_statemachine import (
    State, build_machine, SyncInterpreter, action
)

# 1. Define states
off = State("off", initial=True)
on  = State("on")

# 2. Define transitions
off.to(on,  event="TOGGLE")
on.to(off, event="TOGGLE")

# 3. Define actions
@action
def log_toggle(interpreter, context, event, action_def):
    print(f"Light is now: {interpreter.active_state_ids}")

# 4. Build the machine
machine = build_machine(
    id="lightSwitch",
    states=[off, on],
    actions=[log_toggle],
)

# 5. Run it
interpreter = SyncInterpreter(machine).start()
interpreter.send("TOGGLE")  # off -> on
interpreter.send("TOGGLE")  # on -> off
interpreter.stop()
```

**Output:**

```
Light is now: {'lightSwitch.on'}
Light is now: {'lightSwitch.off'}
```

---

## Option B: JSON Configuration (XState Compatible)

Use this approach when you have an existing XState JSON file, or when you want to share machine definitions across JavaScript and Python.

**Step 1 — Create `light_switch.json`:**

```json
{
  "id": "lightSwitch",
  "initial": "off",
  "context": { "flips": 0 },
  "states": {
    "off": {
      "on": {
        "TOGGLE": {
          "target": "on",
          "actions": "incrementFlips"
        }
      }
    },
    "on": {
      "on": {
        "TOGGLE": {
          "target": "off",
          "actions": "incrementFlips"
        }
      }
    }
  }
}
```

**Step 2 — Create `light_switch_logic.py`:**

```python
from xstate_statemachine import MachineLogic

class LightSwitchLogic(MachineLogic):
    def incrementFlips(self, interpreter, context, event, action_def):
        context["flips"] += 1
        print(f"Flipped! Total: {context['flips']}")
```

**Step 3 — Run it:**

```python
import json
from xstate_statemachine import create_machine, SyncInterpreter
from light_switch_logic import LightSwitchLogic

config = json.load(open("light_switch.json"))
machine = create_machine(config, logic=LightSwitchLogic())

interpreter = SyncInterpreter(machine).start()
interpreter.send("TOGGLE")  # off -> on
interpreter.send("TOGGLE")  # on -> off
interpreter.stop()

print(f"Total flips: {interpreter.context['flips']}")
```

**Output:**

```
Flipped! Total: 1
Flipped! Total: 2
Total flips: 2
```

---

## Option C: Generate Boilerplate with CLI

Already have an XState JSON file? Generate production-ready Python in one command:

```bash
xsm generate-template light_switch.json --template pythonic-class --force
```

This creates two files:

| File | Contents |
|------|----------|
| `light_switch_logic.py` | Action, guard, and service stubs with full type hints |
| `light_switch_runner.py` | Interpreter bootstrap code, ready to execute |

You can also use the short alias:

```bash
xsm gt light_switch.json -t pythonic-class -f
```

**Available templates:**

```bash
xsm gt machine.json --template pythonic-class        # Class-based OOP
xsm gt machine.json --template pythonic-builder       # Fluent builder
xsm gt machine.json --template pythonic-functional    # Functional style
xsm gt machine.json --template class-json             # Class-based with JSON
xsm gt machine.json --template function-json          # Functions with JSON
```

> **Tip:** Add `--async-mode no` for synchronous code, or `--file-count 1` to merge logic and runner into a single file.

---

## Option D: Class-Based Style

Best for larger machines where you want everything organized in a single class:

```python
from xstate_statemachine import (
    State, StateMachine, SyncInterpreter, action, guard
)

class TrafficLight(StateMachine):
    machine_id = "trafficLight"
    initial_context = {"cycle_count": 0}

    # States
    green  = State("green",  initial=True)
    yellow = State("yellow")
    red    = State("red")

    # Transitions
    slow_down = green.to(yellow, event="TIMER")
    caution   = yellow.to(red,   event="TIMER")
    go        = red.to(green,    event="TIMER", actions="countCycle")

    # Actions
    @action
    def count_cycle(self, interpreter, context, event, action_def):
        context["cycle_count"] += 1
        print(f"Cycle {context['cycle_count']} complete")

    @action
    def log_change(self, interpreter, context, event, action_def):
        print(f"Light: {interpreter.active_state_ids}")

    # Entry/Exit actions
    @red.enter
    def on_enter_red(self, interpreter, context, event, action_def):
        print("STOP! Red light.")

    @green.enter
    def on_enter_green(self, interpreter, context, event, action_def):
        print("GO! Green light.")

# Run it
machine = TrafficLight.create_machine()
interp = SyncInterpreter(machine).start()

interp.send("TIMER")  # green -> yellow
interp.send("TIMER")  # yellow -> red
interp.send("TIMER")  # red -> green (cycle complete)
interp.stop()
```

**Output:**

```
STOP! Red light.
Cycle 1 complete
GO! Green light.
```

---

## Option E: Builder Style

Fluent API for dynamic or programmatic machine construction:

```python
from xstate_statemachine import MachineBuilder, SyncInterpreter, action

@action
def log_state(interpreter, context, event, action_def):
    print(f"State: {interpreter.active_state_ids}")

machine = (
    MachineBuilder("doorLock")
    .context({"attempts": 0})
    .state("locked",   initial=True)
    .state("unlocked")
    .state("blocked")
    .transition("locked", "UNLOCK", "unlocked", guard="hasKey")
    .transition("locked", "UNLOCK", "blocked")
    .transition("unlocked", "LOCK", "locked")
    .transition("blocked", "RESET", "locked")
    .action("logState", log_state)
    .guard("hasKey", lambda ctx, evt: ctx.get("has_key", False))
    .build()
)

interp = SyncInterpreter(machine).start()

# Without a key -> blocked
interp.send("UNLOCK")
print(f"Locked out: {interp.active_state_ids}")

interp.send("RESET")

# Give them the key
interp.context["has_key"] = True
interp.send("UNLOCK")
print(f"Unlocked: {interp.active_state_ids}")

interp.stop()
```

---

## What Just Happened?

In every example above, the same pattern plays out:

1. **Define states** — the distinct modes your system can be in (`off`, `on`, `green`, `red`)
2. **Define transitions** — rules that say _"when event X happens in state A, go to state B"_
3. **Define actions** — side effects that run during transitions (logging, updating data)
4. **Build the machine** — compile your definition into a runnable `MachineNode`
5. **Create an interpreter** — the engine that processes events and manages state
6. **Send events** — drive the machine by sending events like `"TOGGLE"` or `"TIMER"`

> **Key insight:** The machine definition is _data_. The interpreter is the _engine_. This separation means you can serialize machines, visualize them, test them in isolation, and swap interpreters (async vs sync) without changing your machine logic.

---

## Next Steps

- [Core Concepts](../core-concepts/) — Understand states, events, transitions, guards, and actions in depth
- [Pythonic API](../pythonic-api/) — Full reference for all three Python styles
- [Actions](../actions/) — Entry, exit, and transition actions
- [Guards](../guards/) — Conditional transitions
- [Context](../context/) — Mutable data across transitions
- [CLI Generator](../cli/) — Generate code from XState JSON
- [Interpreters](../interpreters/) — Async vs sync execution
