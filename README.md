# 🚦 XState Machine for Python

A robust, asynchronous, and feature-complete Python library for parsing and executing state machines defined in XState-compatible JSON.

---

This library brings the power and clarity of formal state machines and statecharts, as popularized by XState, to the Python ecosystem. It allows you to define complex application logic as a clear, traversable graph and execute it in a fully asynchronous, predictable, and debuggable way.

Define your logic once in a simple JSON format, and use this library to bring it to life in your Python application.

---

## 🧭 Core Philosophy: Definition vs. Implementation

**Definition (The "What")**: You define your state machine's structure, states, and transitions in a JSON file. This is your blueprint. It describes what can happen.

**Implementation (The "How")**: You write the business logic—the actual code that runs—in a Python `MachineLogic` object. This describes how actions are performed or services are called.

This separation makes your application logic easier to understand, test, and maintain.

---

## 🎨 Design Your Logic Visually with the Stately Editor

One of the biggest advantages of using an XState-compatible format is the ability to visualize, design, and even simulate your logic using a graphical interface. The official Stately Editor allows you to drag-and-drop states, define transitions, and export the resulting JSON directly for use with this library.

**Start designing at the [Stately Editor](https://stately.ai/editor) →**

---

## ✨ Key Features

- **XState Compatible**: Parses JSON configurations generated from the XState ecosystem.
- **Fully Asynchronous**: Built on `asyncio` for modern, non-blocking applications.
- **Hierarchical & Parallel States**: Model complex logic with nested and parallel states.
- **Timed Events**: Use `after` for declarative, time-based transitions.
- **Asynchronous Services**: Use `invoke` to call async functions and react to their success (`onDone`) or failure (`onError`).
- **Actor Model**: Spawn child state machines from a parent machine for concurrent, isolated logic.
- **Guards**: Implement conditional transitions with simple guard functions.
- **Developer Friendly**: Full type hinting and a `LoggingInspector` plugin for easy debugging.

---

## 📦 Installation

Install the library directly from PyPI:

```bash
pip install xstate-machine
```

---

## 🚀 Getting Started: A Simple Example

Let's create a simple toggle switch.

### 1. Define the Logic (`toggle.json`)

```json
{
  "id": "toggle",
  "initial": "inactive",
  "states": {
    "inactive": {
      "on": {
        "TOGGLE": "active"
      }
    },
    "active": {
      "on": {
        "TOGGLE": "inactive"
      }
    }
  }
}
```

### 2. Implement and Run (`main.py`)

```python
import asyncio
import json
from xstate_machine import create_machine, Interpreter

async def main():
    # Load the machine definition from the JSON file
    with open("toggle.json") as f:
        toggle_config = json.load(f)

    # Create a machine instance from the config
    toggle_machine = create_machine(toggle_config)

    # Create an interpreter to run the machine
    interpreter = await Interpreter(toggle_machine).start()
    print(f"Initial state: {interpreter.current_state_ids}")

    # Send an event to the machine
    print("Sending TOGGLE event...")
    await interpreter.send("TOGGLE")

    # Give the event loop a moment to process
    await asyncio.sleep(0.01)
    print(f"New state: {interpreter.current_state_ids}")

    await interpreter.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

### 3. See the Output

```
Initial state: {'toggle.inactive'}
Sending TOGGLE event...
New state: {'toggle.active'}
```

---

## 🧠 Core Concepts

### Actions & Context

Actions are "fire-and-forget" functions executed during a transition. They are the primary way to interact with the outside world or update the machine's internal context.

#### Example: drone.json

```json
{
  "id": "drone",
  "initial": "flying",
  "context": { "battery": 100 },
  "states": {
    "flying": {
      "on": {
        "PHOTO_TAKEN": { "actions": ["decrementBattery"] }
      }
    }
  }
}
```

#### drone.py

```python
from xstate_machine import MachineLogic

def decrement_battery(interpreter, context, event, action_def):
    context["battery"] -= 1
    print(f"Battery at {context['battery']}%")

logic = MachineLogic(
    actions={"decrementBattery": decrement_battery}
)
```

---

### Guards

Guards are conditional checks that determine if a transition should be taken. If a guard returns `False`, the transition is blocked.

#### checkout.json

```json
{
    "id": "cart",
    "context": { "items": [] },
    "on": {
        "CHECKOUT": {
            "target": "paying",
            "guard": "cartIsNotEmpty"
        }
    }
}
```

#### checkout.py

```python
from xstate_machine import MachineLogic

def cart_is_not_empty(context, event):
    return len(context.get("items", [])) > 0

logic = MachineLogic(
    guards={"cartIsNotEmpty": cart_is_not_empty}
)
```

---

### Asynchronous Services (`invoke`)

For long-running or async operations, use `invoke`. The machine will transition to different states based on the success (`onDone`) or failure (`onError`) of the invoked async function.

#### fetch.json

```json
{
    "id": "fetcher",
    "initial": "loading",
    "states": {
        "loading": {
            "invoke": {
                "src": "fetchUserData",
                "onDone": { "target": "success" },
                "onError": { "target": "failure" }
            }
        },
        "success": { "type": "final" },
        "failure": { "type": "final" }
    }
}
```

#### fetch.py

```python
import aiohttp
from xstate_machine import MachineLogic

async def fetch_user_data(interpreter, context, event):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.example.com/user") as resp:
            resp.raise_for_status()
            return await resp.json()

logic = MachineLogic(
    services={"fetchUserData": fetch_user_data}
)
```

---

### Timed Events (`after`)

Declaratively schedule transitions to occur after a certain amount of time (in milliseconds).

#### traffic_light.json

```json
{
    "id": "light",
    "initial": "green",
    "states": {
        "green": { "after": { "30000": "yellow" } },
        "yellow": { "after": { "5000": "red" } }
    }
}
```

---

### Parallel States

Model system components that operate independently at the same time. The machine is in all child states of a parallel state simultaneously. The parent `onDone` transition only fires when all child regions have reached their final state.

#### build.json

```json
{
    "id": "build",
    "initial": "running",
    "states": {
        "running": {
            "type": "parallel",
            "onDone": "success",
            "states": {
                "backend": {
                    "initial": "compiling",
                    "states": {
                        "compiling": { "after": { "5000": "done" } },
                        "done": { "type": "final" }
                    }
                },
                "frontend": {
                    "initial": "linting",
                    "states": {
                        "linting": { "after": { "3000": "done" } },
                        "done": { "type": "final" }
                    }
                }
            }
        },
        "success": { "type": "final" }
    }
}
```

---

### Actors (Spawning Machines)

For truly isolated, concurrent logic, you can spawn a child machine from a parent. The parent and child can communicate by sending events to each other.

To spawn an actor, define an entry action with the name `spawn_<serviceName>`, where `<serviceName>` corresponds to a key in your services logic that provides a `MachineNode`.

#### main_machine.py

```python
import asyncio
from xstate_machine import create_machine, MachineLogic

# Define the child machine that will be spawned
child_config = { "id": "pinger", "on": { "PING": { "actions": ["pong"] } } }
child_logic = MachineLogic(
    actions={"pong": lambda i,c,e,a: asyncio.create_task(i.parent.send("PONG"))}
)
child_machine_node = create_machine(child_config, child_logic)

# Define the parent machine
parent_config = {
    "id": "parent",
    "initial": "running",
    "states": {
        "running": {
            "entry": ["spawn_pingerService"]
        }
    },
    "on": { "PONG": "finished" }
}
parent_logic = MachineLogic(
    services={"pingerService": child_machine_node}
)

# When run, the spawned actor will be available in the parent's context:
# interpreter.context['actors'][actor_id].send("PING")
```

---

## 🐞 Debugging with Plugins

The interpreter supports a plugin system to hook into its lifecycle. A built-in `LoggingInspector` is provided for easy, detailed debugging.

```python
import logging
from xstate_machine import Interpreter, LoggingInspector

logging.basicConfig(level=logging.INFO)

interpreter = Interpreter(my_machine)
interpreter.use(LoggingInspector())

await interpreter.start()
```

Now, all events, transitions, and actions will be logged to the console.

---

## 🤝 Contributing

Contributions are welcome! If you find a bug or have a feature request, please open an issue on our [GitHub Issue Tracker](https://github.com/tt-basil/xstate-machine/issues).

---

## 📄 License

This project is licensed under the MIT License. See the LICENSE file for details.
