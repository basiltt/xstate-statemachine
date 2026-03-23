---
title: "Interpreters"
description: "Execute state machines with async or sync interpreters — complete guide."
---

An **interpreter** is the runtime engine that executes a state machine. It processes events, evaluates guards, runs actions, invokes services, and manages state transitions. Without an interpreter, a machine definition is just data.

Think of it this way:

- A **machine** (`MachineNode`) is the _blueprint_ — it defines states, transitions, and rules.
- An **interpreter** is the _engine_ — it brings the blueprint to life and tracks the current state.

---

## What Is an Interpreter?

The interpreter manages the full lifecycle of a running state machine:

1. **Start** — enters the initial state (runs entry actions).
2. **Receive events** — matches events against transition rules.
3. **Evaluate guards** — checks boolean conditions on transitions.
4. **Execute actions** — runs side effects (entry, exit, and transition actions).
5. **Invoke services** — starts async/sync operations and handles their results.
6. **Track state** — maintains the current state(s) and context.
7. **Stop** — exits all active states (runs exit actions) and shuts down.

This library provides two interpreter implementations:

| Interpreter | Import | Event Loop | Use Case |
|-------------|--------|:----------:|----------|
| `Interpreter` | `from xstate_statemachine import Interpreter` | `asyncio` | Web servers, async frameworks, async services |
| `SyncInterpreter` | `from xstate_statemachine import SyncInterpreter` | None | Scripts, CLI tools, Django views, testing |

Both interpreters share the same API surface — the only difference is `async`/`await` vs. synchronous calls.

---

## Async Interpreter

Use `Interpreter` for `asyncio`-based applications — web servers (FastAPI, aiohttp), async background workers, or any codebase built on `async`/`await`.

### Full Example

```python
import asyncio
from xstate_statemachine import create_machine, Interpreter, MachineLogic

config = {
    "id": "fetchMachine",
    "initial": "idle",
    "context": {"data": None, "error": None},
    "states": {
        "idle": {
            "on": {"FETCH": "loading"}
        },
        "loading": {
            "invoke": {
                "src": "fetchData",
                "onDone":  {"target": "success", "actions": "storeData"},
                "onError": {"target": "error",   "actions": "storeError"}
            }
        },
        "success": {
            "on": {"REFRESH": "loading", "RESET": "idle"}
        },
        "error": {
            "on": {"RETRY": "loading", "RESET": "idle"}
        }
    }
}

class FetchLogic(MachineLogic):
    async def fetchData(self, interpreter, context, event):
        import aiohttp
        async with aiohttp.ClientSession() as session:
            resp = await session.get("https://api.example.com/data")
            return await resp.json()

    def storeData(self, interpreter, context, event, action_def):
        context["data"] = event.data

    def storeError(self, interpreter, context, event, action_def):
        context["error"] = str(event.data)


async def main():
    machine = create_machine(config, logic=FetchLogic())
    interpreter = Interpreter(machine)

    await interpreter.start()
    print(interpreter.active_state_ids)
    # {'fetchMachine.idle'}

    await interpreter.send("FETCH")
    # idle → loading → (service runs) → success or error

    print(interpreter.active_state_ids)
    print(interpreter.context)

    await interpreter.stop()

asyncio.run(main())
```

### Key Points

- `await interpreter.start()` — enters the initial state and returns the interpreter (for chaining).
- `await interpreter.send("EVENT")` — sends an event and processes the resulting transition(s).
- `await interpreter.stop()` — exits all active states and shuts down.
- Services defined with `async def` are awaited automatically.

### Use Cases

- **FastAPI / Starlette** route handlers
- **aiohttp** web servers
- **Celery** async tasks
- **WebSocket** connection state management
- Any `asyncio.run()` or `async def` context

---

## Sync Interpreter

Use `SyncInterpreter` for synchronous code — scripts, CLI tools, Django views, Flask handlers, or test suites.

### Full Example

```python
from xstate_statemachine import create_machine, SyncInterpreter, MachineLogic

config = {
    "id": "toggleMachine",
    "initial": "inactive",
    "context": {"toggles": 0},
    "states": {
        "inactive": {
            "on": {"ACTIVATE": {"target": "active", "actions": "logToggle"}}
        },
        "active": {
            "on": {"DEACTIVATE": {"target": "inactive", "actions": "logToggle"}}
        }
    }
}

class ToggleLogic(MachineLogic):
    def logToggle(self, interpreter, context, event, action_def):
        context["toggles"] += 1
        print(f"Toggle #{context['toggles']} → {interpreter.active_state_ids}")


machine = create_machine(config, logic=ToggleLogic())

# .start() is chainable — returns the interpreter
interp = SyncInterpreter(machine).start()

print(interp.active_state_ids)
# {'toggleMachine.inactive'}

interp.send("ACTIVATE")
# Toggle #1 → {'toggleMachine.active'}

interp.send("DEACTIVATE")
# Toggle #2 → {'toggleMachine.inactive'}

print(interp.context)
# {'toggles': 2}

interp.stop()
```

### Key Points

- `.start()` returns `self`, so you can chain: `SyncInterpreter(machine).start()`.
- `.send("EVENT")` processes the event synchronously and blocks until all actions complete.
- `.stop()` exits all active states and runs their exit actions.
- Services defined with `def` (not `async def`) are called directly.

### Use Cases

- **Scripts** and CLI tools
- **Django** views and middleware
- **Flask** route handlers
- **pytest** test suites
- Quick prototyping and REPL exploration

---

## Key Properties and Methods

| Property / Method | Type | Description |
|-------------------|------|-------------|
| `.start()` | method | Initialize the interpreter and enter the initial state. Runs entry actions. Returns the interpreter (chainable). |
| `.stop()` | method | Exit all active states (runs exit actions) and shut down. |
| `.send(event, **kwargs)` | method | Send an event to the machine. Accepts string, dict, or `Event` object. Extra kwargs become event payload. |
| `.send_events(events)` | method | Send multiple events in sequence. Each event is processed before the next. |
| `.active_state_ids` | `set[str]` | The set of currently active state IDs (e.g., `{'machine.idle'}`). |
| `.context` | `dict` | The current machine context. Mutable — actions can modify this directly. |
| `.is_running` | `bool` | `True` after `.start()`, `False` after `.stop()`. |
| `.plugins` | `list` | List of attached plugin instances. Set before `.start()`. |

---

## Sending Events — All Formats

The `.send()` method accepts events in multiple formats. Use whichever is most convenient:

### String Shorthand

The simplest form — just the event name:

```python
interp.send("CLICK")
interp.send("SUBMIT")
interp.send("TIMER")
```

### With Payload (Keyword Arguments)

Pass extra data as keyword arguments. These become accessible in actions and guards via `event.payload`:

```python
interp.send("LOGIN", username="alice", password="secret")
interp.send("UPDATE_PROFILE", name="Alice", email="alice@example.com")
interp.send("ADD_ITEM", product_id=42, quantity=3)
```

### Event Object

Create an `Event` instance directly:

```python
from xstate_statemachine import Event

event = Event(type="LOGIN", payload={"username": "alice", "password": "secret"})
interp.send(event)
```

### Dict Form

Pass a dict with a `type` key:

```python
interp.send({"type": "LOGIN", "username": "alice", "password": "secret"})
interp.send({"type": "ADD_ITEM", "product_id": 42, "quantity": 3})
```

### Multiple Events at Once

Send a list of events with `send_events()`. Each event is fully processed (including all resulting transitions, actions, and services) before the next one starts:

```python
interp.send_events(["STEP_1", "STEP_2", "STEP_3"])

# Equivalent to:
# interp.send("STEP_1")
# interp.send("STEP_2")
# interp.send("STEP_3")
```

You can mix formats in the list:

```python
interp.send_events([
    "START",
    {"type": "CONFIG", "mode": "advanced"},
    Event(type="READY", payload={}),
])
```

---

## Event Payloads — Accessing Event Data

When you send an event with payload data, actions and guards can access it through the `event` parameter:

```python
from xstate_statemachine import (
    create_machine, SyncInterpreter, MachineLogic
)

config = {
    "id": "userMachine",
    "initial": "idle",
    "context": {"user": None},
    "states": {
        "idle": {
            "on": {"LOGIN": {"target": "loggedIn", "actions": "storeUser"}}
        },
        "loggedIn": {
            "on": {"LOGOUT": {"target": "idle", "actions": "clearUser"}}
        }
    }
}

class UserLogic(MachineLogic):
    def storeUser(self, interpreter, context, event, action_def):
        # Access payload data from keyword arguments
        context["user"] = {
            "username": event.payload.get("username"),
            "role": event.payload.get("role", "user"),
        }
        print(f"Logged in as {context['user']['username']}")

    def clearUser(self, interpreter, context, event, action_def):
        context["user"] = None

machine = create_machine(config, logic=UserLogic())
interp = SyncInterpreter(machine).start()

interp.send("LOGIN", username="alice", role="admin")
# Output: Logged in as alice

print(interp.context["user"])
# {'username': 'alice', 'role': 'admin'}

interp.stop()
```

> **Note:** For service `onDone` events, the service's return value is available as `event.data`. For `onError` events, the raised exception is in `event.data`.

---

## Interpreter Lifecycle

The interpreter follows a strict lifecycle:

```
    create          start()         send()          stop()
  ───────────► [Created] ─────► [Running] ─────► [Stopped]
                                    │    ▲
                                    │    │
                                    └────┘
                                  send() / process events
```

### Step-by-Step

```python
from xstate_statemachine import create_machine, SyncInterpreter

config = {
    "id": "lifecycle",
    "initial": "idle",
    "context": {},
    "states": {
        "idle":    {"on": {"GO": "running"}, "entry": "onEnterIdle"},
        "running": {"on": {"STOP": "done"},  "entry": "onEnterRunning"},
        "done":    {"type": "final",         "entry": "onEnterDone"}
    }
}

machine = create_machine(config)

# 1. CREATE — machine is defined but not running
interp = SyncInterpreter(machine)
print(interp.is_running)        # False
print(interp.active_state_ids)  # set()

# 2. START — enters initial state, runs entry actions
interp.start()
print(interp.is_running)        # True
print(interp.active_state_ids)  # {'lifecycle.idle'}

# 3. SEND EVENTS — transitions occur
interp.send("GO")
print(interp.active_state_ids)  # {'lifecycle.running'}

interp.send("STOP")
print(interp.active_state_ids)  # {'lifecycle.done'}

# 4. STOP — exits all states, runs exit actions
interp.stop()
print(interp.is_running)        # False
```

### Idempotency and Safety

Both `start()` and `stop()` are safe to call multiple times:

- **`start()`** on an already-running interpreter is a no-op
- **`stop()`** on an already-stopped interpreter is a no-op
- **`send()`** on a stopped interpreter is silently ignored

```python
interp = SyncInterpreter(machine).start()
interp.start()  # No effect — already running

interp.stop()
interp.stop()  # No effect — already stopped

interp.send("EVENT")  # Silently ignored — interpreter is stopped
```

### Event Processing: Queue Semantics

The **async `Interpreter`** uses an internal event queue. When you call `await interp.send("EVENT")`, the event is placed on the queue and processed by a background event loop. This means:

- One `send()` call may trigger **multiple transitions** if the target state has `always` (eventless) transitions
- After processing an event, the interpreter automatically checks for and processes any matching `always` transitions until no more apply
- Timer-based `after` transitions are scheduled as background tasks

The **`SyncInterpreter`** processes events immediately and synchronously within the `send()` call — there is no background queue.

### Automatic (Eventless) Transitions

When a state has `always` transitions, the interpreter evaluates them immediately after entering the state — no event needed:

```python
config = {
    "id": "autoRouter",
    "initial": "checking",
    "context": {"role": "admin"},
    "states": {
        "checking": {
            "always": [
                {"target": "adminPanel", "guard": "isAdmin"},
                {"target": "userDashboard"}
            ]
        },
        "adminPanel": {},
        "userDashboard": {}
    }
}

class Logic(MachineLogic):
    def isAdmin(self, context, event):
        return context.get("role") == "admin"

machine = create_machine(config, logic=Logic())
interp = SyncInterpreter(machine).start()

# No send() needed — the machine automatically transitions
# through 'checking' into 'adminPanel' via the always transition
print(interp.active_state_ids)
# {'autoRouter.adminPanel'}

interp.stop()
```

> **Note:** A single `send()` call can trigger a chain of transitions if states along the path have `always` transitions. The interpreter keeps processing until it reaches a stable state with no pending eventless transitions.

---

## Plugin Attachment

Plugins observe machine execution without modifying behavior. Attach them before calling `.start()`:

```python
from xstate_statemachine import (
    create_machine, SyncInterpreter, LoggingInspector
)

config = {
    "id": "demo",
    "initial": "a",
    "states": {
        "a": {"on": {"GO": "b"}},
        "b": {"on": {"GO": "c"}},
        "c": {"type": "final"}
    }
}

machine = create_machine(config)
interp = SyncInterpreter(machine)

# Attach plugins BEFORE starting
interp.plugins = [LoggingInspector()]

interp.start()
interp.send("GO")    # a → b — logged by plugin
interp.send("GO")    # b → c — logged by plugin
interp.stop()
```

**Output:**

```
🕵️ [INSPECT] Transition: ['demo.a'] -> ['demo.b'] on Event 'GO'
🕵️ [INSPECT] New Context: {}
🕵️ [INSPECT] Transition: ['demo.b'] -> ['demo.c'] on Event 'GO'
🕵️ [INSPECT] New Context: {}
```

### Custom Plugin Example

```python
from xstate_statemachine import PluginBase

class MetricsPlugin(PluginBase):
    def __init__(self):
        self.transition_count = 0
        self.events_received = []

    def on_transition(self, interpreter, from_states, to_states, transition):
        self.transition_count += 1

    def on_event_received(self, interpreter, event):
        self.events_received.append(event.type)


metrics = MetricsPlugin()
interp.plugins = [metrics, LoggingInspector()]  # Multiple plugins
interp.start()
# ... use the machine ...
print(f"Total transitions: {metrics.transition_count}")
```

---

## Using with the Pythonic API

The interpreters work identically with machines built using the Pythonic API:

```python
from xstate_statemachine import (
    State, StateMachine, SyncInterpreter,
    action, guard, LoggingInspector
)

class OrderMachine(StateMachine):
    machine_id = "order"
    initial_context = {"items": [], "total": 0}

    cart      = State("cart", initial=True)
    checkout  = State("checkout")
    confirmed = State("confirmed", final=True)

    begin_checkout = cart.to(checkout, event="CHECKOUT", guard="hasItems")
    confirm        = checkout.to(confirmed, event="CONFIRM")
    back_to_cart   = checkout.to(cart, event="BACK")

    @guard
    def has_items(self, context, event):
        return len(context.get("items", [])) > 0

    @action
    def add_item(self, interpreter, context, event, action_def):
        item = event.payload.get("item", "unknown")
        context["items"].append(item)

    add = cart.internal("ADD_ITEM", actions=["addItem"])


# Build and run
machine = OrderMachine.create_machine()

interp = SyncInterpreter(machine)
interp.plugins = [LoggingInspector()]
interp.start()

interp.send("ADD_ITEM", item="Widget")
interp.send("ADD_ITEM", item="Gadget")
interp.send("CHECKOUT")

print(interp.active_state_ids)
# {'order.checkout'}

interp.send("CONFIRM")
print(interp.context["items"])
# ['Widget', 'Gadget']

interp.stop()
```

---

## Error Handling During Event Processing

If an action raises an exception, the interpreter propagates it. Wrap `.send()` calls in try/except for graceful error handling:

```python
from xstate_statemachine import create_machine, SyncInterpreter, MachineLogic

config = {
    "id": "risky",
    "initial": "idle",
    "states": {
        "idle": {"on": {"GO": {"target": "processing", "actions": "riskyAction"}}},
        "processing": {},
        "error": {}
    }
}

class RiskyLogic(MachineLogic):
    def riskyAction(self, interpreter, context, event, action_def):
        raise ValueError("Something went wrong!")


machine = create_machine(config, logic=RiskyLogic())
interp = SyncInterpreter(machine).start()

try:
    interp.send("GO")
except ValueError as e:
    print(f"Caught error: {e}")
    # Handle the error — the machine state depends on
    # when the error occurred during transition processing

interp.stop()
```

> **Tip:** For expected errors (like network failures), use `invoke`/`onError` instead of try/except. The `onError` transition is the idiomatic way to handle service errors in state machines.

---

## Testing with SyncInterpreter

`SyncInterpreter` is ideal for testing — no async boilerplate, no event loops:

```python
import pytest
from xstate_statemachine import (
    State, StateMachine, SyncInterpreter, guard, action
)


class LoginMachine(StateMachine):
    machine_id = "login"
    initial_context = {"username": "", "authenticated": False}

    idle         = State("idle", initial=True)
    authenticating = State("authenticating")
    logged_in    = State("loggedIn")
    error        = State("error")

    attempt = idle.to(authenticating, event="LOGIN")
    success = authenticating.to(logged_in, event="SUCCESS", actions=["setAuthenticated"])
    failure = authenticating.to(error, event="FAILURE")
    retry   = error.to(idle, event="RETRY")
    logout  = logged_in.to(idle, event="LOGOUT", actions=["clearAuth"])

    @action
    def set_authenticated(self, interpreter, context, event, action_def):
        context["authenticated"] = True
        context["username"] = event.payload.get("username", "")

    @action
    def clear_auth(self, interpreter, context, event, action_def):
        context["authenticated"] = False
        context["username"] = ""


class TestLoginMachine:
    def setup_method(self):
        """Create a fresh interpreter for each test."""
        machine = LoginMachine.create_machine()
        self.interp = SyncInterpreter(machine).start()

    def teardown_method(self):
        """Clean up the interpreter."""
        self.interp.stop()

    def test_starts_in_idle(self):
        assert "login.idle" in self.interp.active_state_ids

    def test_login_flow(self):
        self.interp.send("LOGIN")
        assert "login.authenticating" in self.interp.active_state_ids

        self.interp.send("SUCCESS", username="alice")
        assert "login.loggedIn" in self.interp.active_state_ids
        assert self.interp.context["authenticated"] is True
        assert self.interp.context["username"] == "alice"

    def test_login_failure_and_retry(self):
        self.interp.send("LOGIN")
        self.interp.send("FAILURE")
        assert "login.error" in self.interp.active_state_ids

        self.interp.send("RETRY")
        assert "login.idle" in self.interp.active_state_ids

    def test_logout_clears_auth(self):
        self.interp.send("LOGIN")
        self.interp.send("SUCCESS", username="bob")
        assert self.interp.context["authenticated"] is True

        self.interp.send("LOGOUT")
        assert "login.idle" in self.interp.active_state_ids
        assert self.interp.context["authenticated"] is False
        assert self.interp.context["username"] == ""

    def test_ignores_invalid_events(self):
        """Events that don't match any transition are silently ignored."""
        self.interp.send("NONEXISTENT_EVENT")
        assert "login.idle" in self.interp.active_state_ids

    def test_send_events_batch(self):
        """send_events processes events in sequence."""
        self.interp.send_events(["LOGIN", "FAILURE", "RETRY"])
        assert "login.idle" in self.interp.active_state_ids
```

Run tests with:

```bash
pytest test_login.py -v
```

---

## Async vs. Sync Comparison

| Feature | `Interpreter` (async) | `SyncInterpreter` (sync) |
|---------|:---------------------:|:------------------------:|
| Start | `await interp.start()` | `interp.start()` |
| Send | `await interp.send("E")` | `interp.send("E")` |
| Stop | `await interp.stop()` | `interp.stop()` |
| Chainable start | `await Interpreter(m).start()` | `SyncInterpreter(m).start()` |
| Services | `async def` (awaited) | `def` (called directly) |
| Actions | Sync (same for both) | Sync (same for both) |
| Guards | Sync (same for both) | Sync (same for both) |
| Event loop | Requires `asyncio` | No event loop needed |
| Plugins | Same API | Same API |
| Context access | `interp.context` | `interp.context` |
| Active states | `interp.active_state_ids` | `interp.active_state_ids` |
| Thread safety | Single-threaded (asyncio) | Single-threaded |

> **Tip:** Use `SyncInterpreter` for **testing** even if your production code uses `Interpreter`. It eliminates async boilerplate in tests and makes assertions straightforward.

> **Tip:** If you're unsure which to use, start with `SyncInterpreter`. You can always switch to `Interpreter` later — the machine definition doesn't change, only the interpreter and service implementations.
