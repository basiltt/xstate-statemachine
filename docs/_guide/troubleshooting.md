---
title: "Troubleshooting"
description: "Common errors, their causes, and how to fix them."
---

# Troubleshooting

This page covers common errors you may encounter when using XState-StateMachine, their causes, and how to fix them. It also includes CLI troubleshooting, debugging tips, and common pitfalls.

## Exception Hierarchy

XState-StateMachine provides a clean exception hierarchy so you can catch errors at the right level of specificity:

```
XStateMachineError          ← Base class for ALL library errors
├── InvalidConfigError      ← Machine configuration is structurally invalid
├── StateNotFoundError      ← Target state ID doesn't exist
├── ImplementationMissingError ← Action/guard/service function not provided
├── ActorSpawningError      ← Error creating child actor machine
└── NotSupportedError       ← Feature not available in current mode
```

### Importing Exceptions

```python
from xstate_statemachine import (
    XStateMachineError,        # Catch-all for any library error
    InvalidConfigError,        # Bad machine config
    StateNotFoundError,        # Bad transition target
    ImplementationMissingError,# Missing action/guard/service
    ActorSpawningError,        # Actor creation failed
    NotSupportedError,         # Feature not supported in current mode
)
```

### Catching Errors in Production

```python
from xstate_statemachine import (
    create_machine, SyncInterpreter, MachineLogic,
    XStateMachineError, InvalidConfigError, ImplementationMissingError
)

def safe_run_machine(config, logic=None):
    """Run a machine with proper error handling."""
    try:
        machine = create_machine(config, logic=logic)
        interp = SyncInterpreter(machine).start()
        return interp
    except InvalidConfigError as e:
        print(f"Config error: {e}")
        # Fix: check your JSON structure has 'id' and 'states'
        return None
    except ImplementationMissingError as e:
        print(f"Missing implementation: {e}")
        # Fix: provide the missing action/guard/service
        return None
    except XStateMachineError as e:
        print(f"State machine error: {e}")
        return None
```

### `StateNotFoundError` Details

`StateNotFoundError` includes extra attributes for debugging:

```python
from xstate_statemachine import StateNotFoundError

try:
    interp.send("GO_TO_NONEXISTENT")
except StateNotFoundError as e:
    print(e.target)        # 'nonexistentState' — the state that wasn't found
    print(e.reference_id)  # 'myMachine.currentState' — where it was referenced from
```

## Common Errors

### `InvalidConfigError` — Missing `id`

**What it looks like:**

```
xstate_statemachine.exceptions.InvalidConfigError: Invalid config: must be a dict with 'id' and 'states' keys.
```

**Why it happens:** Your JSON config is missing the required `"id"` field at the root level.

**How to fix it:**

```json
{
  "id": "myMachine",
  "initial": "idle",
  "states": {
    "idle": {}
  }
}
```

Every machine config must have an `"id"` string and a `"states"` object.

---

### `InvalidConfigError` — Missing `states`

**What it looks like:**

```
xstate_statemachine.exceptions.InvalidConfigError: Invalid config: must be a dict with 'id' and 'states' keys.
```

**Why it happens:** The config has an `"id"` but no `"states"` object, or `"states"` is empty.

**How to fix it:**

```python
config = {
    "id": "myMachine",
    "initial": "idle",
    "states": {
        "idle": {
            "on": { "START": "running" }
        },
        "running": {}
    }
}
machine = create_machine(config)
```

---

### `InvalidConfigError` — No Initial State

**What it looks like:**

```
xstate_statemachine.exceptions.InvalidConfigError: No initial state defined. Exactly one state must have initial=True
```

**Why it happens:** When using the Pythonic API, none of the `State` objects has `initial=True`.

**How to fix it:**

```python
from xstate_statemachine import State, build_machine

idle = State("idle", initial=True)  # Mark exactly one state as initial
running = State("running")

machine = build_machine(id="myMachine", states=[idle, running])
```

For JSON configs, ensure the root-level `"initial"` key is present:

```json
{
  "id": "myMachine",
  "initial": "idle",
  "states": { "idle": {}, "running": {} }
}
```

---

### `StateNotFoundError`

**What it looks like:**

```
xstate_statemachine.exceptions.StateNotFoundError: Could not find state with ID 'nonExistent'.
```

Or with context:

```
xstate_statemachine.exceptions.StateNotFoundError: Could not resolve target state 'runing' from state 'idle'.
```

**Why it happens:** A transition `target` references a state name that doesn't exist. This is usually a typo.

**How to fix it:** Check the spelling of your target state names:

```python
# Wrong - typo in target
config = {
    "id": "test", "initial": "idle",
    "states": {
        "idle": { "on": { "GO": "runing" } },  # Typo!
        "running": {}
    }
}

# Correct
config = {
    "id": "test", "initial": "idle",
    "states": {
        "idle": { "on": { "GO": "running" } },  # Fixed
        "running": {}
    }
}
```

---

### `ImplementationMissingError`

**What it looks like:**

```
xstate_statemachine.exceptions.ImplementationMissingError: Guard 'userIsAdmin' not implemented.
```

**Why it happens:** Your JSON config references an action, guard, or service by name, but no Python function with a matching name was provided in `MachineLogic`, `logic_providers`, or `logic_modules`.

**How to fix it:**

```python
from xstate_statemachine import create_machine, SyncInterpreter, MachineLogic

config = {
    "id": "test", "initial": "s1",
    "states": {
        "s1": { "on": { "EVENT": { "target": "s2", "guard": "userIsAdmin" } } },
        "s2": {}
    }
}

# Provide the missing guard implementation
def user_is_admin(context, event):
    return context.get("role") == "admin"

logic = MachineLogic(guards={"userIsAdmin": user_is_admin})
machine = create_machine(config, logic=logic)
```

> **Tip:** The `LogicLoader` matches `snake_case` Python function names to `camelCase` JSON names automatically. So `user_is_admin` matches `"userIsAdmin"`.

---

### `NotSupportedError` — Async Guard

**What it looks like:**

```
xstate_statemachine.exceptions.NotSupportedError: Guard 'my_guard' must be synchronous (guards cannot be async)
```

**Why it happens:** You defined a guard function with `async def`. Guards must be synchronous because they need to return a boolean immediately to decide whether a transition should proceed.

**How to fix it:**

```python
from xstate_statemachine import guard

# Wrong - guards cannot be async
@guard
async def my_guard(context, event):  # This will raise NotSupportedError
    return True

# Correct - guards must be sync
@guard
def my_guard(context, event):
    return context.get("count", 0) > 0
```

---

### `NotSupportedError` — `after` with `SyncInterpreter`

**What it looks like:**

```
xstate_statemachine.exceptions.NotSupportedError: `after` transitions are not supported by SyncInterpreter.
```

**Why it happens:** You're using `SyncInterpreter` with a machine that has `after` (delayed) transitions. Delayed transitions require an async event loop.

**How to fix it:** Use the async `Interpreter` instead:

```python
import asyncio
from xstate_statemachine import create_machine, Interpreter

config = {
    "id": "timer", "initial": "idle",
    "states": {
        "idle": { "after": { "1000": "timeout" } },
        "timeout": {}
    }
}

async def main():
    machine = create_machine(config)
    interp = Interpreter(machine)
    await interp.start()
    await asyncio.sleep(1.5)  # Wait for the delayed transition
    print(interp.current_state_ids)  # Should show 'timeout'
    await interp.stop()

asyncio.run(main())
```

---

### `ActorSpawningError`

**What it looks like:**

```
xstate_statemachine.exceptions.ActorSpawningError: Failed to spawn actor: ...
```

**Why it happens:** An `invoke` configuration references a service that should return a `MachineNode`, but the service returned something else (or failed to return).

**How to fix it:** Ensure your service function returns a valid `MachineNode`:

```python
from xstate_statemachine import create_machine

def my_actor_service(interpreter, context, event):
    child_config = {
        "id": "child", "initial": "active",
        "states": { "active": {} }
    }
    return create_machine(child_config)  # Must return a MachineNode
```

---

## CLI Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| `xsm: command not found` | Package not installed, or entry point not on PATH | Run `pip install xstate-statemachine` or use `python -m xstate_statemachine.cli` |
| Files not generated | Output directory doesn't exist, or files already exist | Use `-o ./output/` with an existing directory; use `--force` to overwrite |
| Wrong template used | Using deprecated `--style` flag | Use `--template pythonic-class` instead of `--style class` |
| Encoding errors on Windows | Console doesn't support UTF-8 emoji characters | Set `PYTHONIOENCODING=utf-8` or use `chcp 65001` in cmd |
| `--json-parent` specified twice | Validation error | Only one `--json-parent` is allowed; use `--json-child` for additional machines |
| Generated code has async but I want sync | Default async mode varies by template | Add `--async-mode no` to your command |
| `JSONDecodeError` during generation | Invalid JSON syntax in input file | Validate your JSON file with `python -m json.tool my_machine.json` |

---

## Debugging Tips

### 1. Attach `LoggingInspector`

The `LoggingInspector` plugin logs every transition, action, guard, and state change:

```python
from xstate_statemachine import create_machine, SyncInterpreter, LoggingInspector

machine = create_machine(config, logic=logic)
interp = SyncInterpreter(machine)
interp.use(LoggingInspector())  # Attach the inspector
interp.start()

interp.send("MY_EVENT")
# Console output will show the full transition trace
```

### 2. Check Active States After Each Event

```python
interp.start()
print("After start:", interp.current_state_ids)

interp.send("SUBMIT")
print("After SUBMIT:", interp.current_state_ids)

interp.send("CONFIRM")
print("After CONFIRM:", interp.current_state_ids)
```

This helps you see exactly which state the machine is in after each event.

### 3. Inspect Context

```python
interp.start()
print("Initial context:", interp.context)

interp.send("ADD_ITEM")
print("After ADD_ITEM:", interp.context)
```

Context is shared across all states — verify that your actions are modifying it correctly.

### 4. Export Diagrams to Visualize

```python
# Generate a Mermaid diagram of your machine
print(machine.to_mermaid())
```

Paste the output into [mermaid.live](https://mermaid.live) to see a visual representation of your state machine.

### 5. Use `SyncInterpreter` for Deterministic Debugging

When debugging, prefer `SyncInterpreter` over `Interpreter` because:
- Events are processed immediately (no event loop timing issues)
- State changes happen synchronously
- Easier to inspect state after each operation

```python
from xstate_statemachine import create_machine, SyncInterpreter

machine = create_machine(config)
interp = SyncInterpreter(machine)
interp.start()

# Everything is synchronous — easy to step through
interp.send("EVENT_A")
assert "myMachine.stateB" in interp.current_state_ids
```

---

## Common Pitfalls

### Guards Must Return `bool`

Guards must return `True` or `False`. If a guard returns a non-boolean truthy/falsy value, it may work but leads to confusing behavior. Always be explicit:

```python
# Bad - returns an int
def has_items(context, event):
    return len(context["items"])  # Returns 0 or N, not True/False

# Good - returns a bool
def has_items(context, event):
    return len(context["items"]) > 0
```

### Guards Must Be Synchronous

Guards cannot be `async def`. This is enforced by the library:

```python
# This will raise NotSupportedError
@guard
async def check_something(context, event):
    return True

# Use sync instead
@guard
def check_something(context, event):
    return True
```

### Action Signature Has 4 Parameters, Guard Has 2

Action functions receive `(interpreter, context, event, action_def)` — four parameters. Guard functions receive `(context, event)` — two parameters. Mixing them up causes `TypeError`:

```python
# Action: 4 params (5 with self in a class)
def my_action(interpreter, context, event, action_def):
    context["count"] += 1

# Guard: 2 params (3 with self in a class)
def my_guard(context, event):
    return context["count"] > 0

# Service: 3 params (4 with self in a class)
def my_service(interpreter, context, event):
    return {"result": "done"}
```

### Context Is Shared (Not Per-State)

The context dict is a single object shared across all states. Any action in any state can read and modify it:

```python
config = {
    "id": "test", "initial": "a",
    "states": {
        "a": {
            "entry": "setFlagA",
            "on": { "GO": "b" }
        },
        "b": {
            "entry": "readFlagA"  # Can access context["flagA"] set by state "a"
        }
    }
}
```

### Event Names Are Case-Sensitive

`"SUBMIT"`, `"submit"`, and `"Submit"` are three different events:

```python
# This will NOT trigger the transition
interp.send("submit")  # Wrong case!

# This will trigger it
interp.send("SUBMIT")  # Correct
```

> **Tip:** By convention, XState uses UPPER_SNAKE_CASE for event names (e.g., `SUBMIT`, `ADD_ITEM`, `PAYMENT_DONE`).

---

## FAQ-Style Troubleshooting

### "My transition isn't firing"

Check these in order:

1. **Event name case:** Event names are case-sensitive. `"SUBMIT"` is not `"submit"`.
2. **Guard returning False:** If a guard is attached to the transition, it may be returning `False`. Add logging to your guard to verify.
3. **Wrong source state:** The machine must be in the state where the transition's `on` block is defined. Check `interp.current_state_ids`.
4. **Final state:** If the machine is in a `final` state, no more transitions can occur.

```python
# Debug: Print current state before sending event
print(f"Current state: {interp.current_state_ids}")
interp.send("MY_EVENT")
print(f"After event: {interp.current_state_ids}")
```

### "My action isn't running"

1. **Name mismatch:** The function name in Python must match the action name in JSON. With `LogicLoader`, `snake_case` auto-maps to `camelCase` (e.g., `calculate_total` → `calculateTotal`).
2. **Not registered:** If using `MachineLogic`, make sure the action is in the `actions` dict. If using `logic_providers`, make sure the method exists on the class.
3. **Transition didn't happen:** The action only runs if the transition actually fires. Check that the transition isn't blocked by a guard.

```python
# Verify your action is discoverable
logic = MachineLogic(actions={"calculateTotal": my_action_fn})
machine = create_machine(config, logic=logic)
```

### "My service result isn't being used"

Services invoked via `invoke` produce `onDone` events when they return. Make sure:

1. The service returns a dict: `return {"result": "done"}`
2. The `onDone` transition is defined in the invoke config
3. You're using the async `Interpreter` if the service is async

### "I get `TypeError` when my function is called"

Your function signature doesn't match what the interpreter expects:

```python
# Actions: (interpreter, context, event, action_def)
# Guards:  (context, event)
# Services: (interpreter, context, event)

# In a class (add self):
# Actions: (self, interpreter, context, event, action_def)
# Guards:  (self, context, event)
# Services: (self, interpreter, context, event)
```

### "My generated code imports fail"

Make sure `xstate_statemachine` is installed in your Python environment:

```bash
pip install xstate-statemachine
```

If using generated files with separate logic/runner, both files must be in the same directory (or on the Python path).
