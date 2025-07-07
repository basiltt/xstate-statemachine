# 🚦 XState StateMachine for Python

A robust, asynchronous, and feature-complete Python library for parsing and executing state machines defined in XState-compatible JSON.

---

This library brings the power and clarity of formal state machines and statecharts, as popularized by XState, to the Python ecosystem. It allows you to define complex application logic as a clear, traversable graph and execute it in a fully asynchronous, predictable, and debuggable way.

Define your logic once in a simple JSON format, and use this library to bring it to life in your Python application.

---

## 🧭 Core Philosophy: Definition vs. Implementation

**Definition (The "What")**: You define your state machine's structure, states, and transitions in a JSON file. This is your blueprint. It describes what can happen.

**Implementation (The "How")**: You write the business logic—the actual code that runs—in Python. This describes how actions are performed or services are called.

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
- **Automatic Logic Discovery**: Optionally, let the library find and bind your Python functions to your machine's logic automatically, reducing boilerplate.
- **Timed Events**: Use `after` for declarative, time-based transitions.
- **Asynchronous Services**: Use `invoke` to call async functions and react to their success (`onDone`) or failure (`onError`).
- **Actor Model**: Spawn child state machines from a parent machine for concurrent, isolated logic.
- **Guards**: Implement conditional transitions with simple guard functions.
- **Developer Friendly**: Full type hinting and a `LoggingInspector` plugin for easy debugging.

---

## 📦 Installation

Install the library directly from PyPI:

```bash
pip install xstate-statemachine
```

---

## 🚀 Getting Started: A Simple Example

Let's create a simple toggle switch.

### 1. Define the Machine (`toggle.json`)

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
from xstate_statemachine import create_machine, Interpreter

async def main():
    with open("toggle.json") as f:
        toggle_config = json.load(f)

    # Since there's no custom logic, we can create the machine directly.
    toggle_machine = create_machine(toggle_config)

    interpreter = await Interpreter(toggle_machine).start()
    print(f"Initial state: {interpreter.current_state_ids}")

    await interpreter.send("TOGGLE")
    await asyncio.sleep(0.01)
    print(f"New state: {interpreter.current_state_ids}")

    await interpreter.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🧠 Core Concepts

There are two primary ways to provide your Python implementations (actions, guards, services) to the state machine: Explicit Binding (the classic way) and Automatic Discovery (the new, convenient way).

### 🤖 Automatic Logic Discovery (Convention over Configuration)

This is the recommended approach for quickly wiring up your logic. Instead of manually creating a MachineLogic object, you can place your implementation functions in a Python module and tell the factory where to find them.

How it Works: The LogicLoader inspects your modules, finds your functions, and automatically binds them to the names in your JSON config.

Naming Convention: It's smart about names! A camelCase name in your JSON (like `myAction`) will automatically match a snake_case function in your Python code (`def my_action(...):`).

#### Example

1. **Your Logic** (`my_logic.py`)

    ```python
    # No MachineLogic object needed here! Just define your functions.
    def my_action(interpreter, context, event, action_def):
        print("Action executed!")
    ```

2. **Your Runner** (`main.py`)

    ```python
    from xstate_statemachine import create_machine

    # Tell the factory where to find your logic functions.
    machine = create_machine(
        config=my_config,
        logic_modules=["my_logic"]  # Pass the module path as a string
    )
    # ... or ...
    import my_logic
    machine = create_machine(
        config=my_config,
        logic_modules=[my_logic]  # Pass the imported module object
    )
    ```

---

### Actions & Context

Actions are "fire-and-forget" functions executed during transitions.

#### `drone.json`

```json
{
  "id": "drone",
  "initial": "flying",
  "context": { "battery": 100 },
  "states": {
    "flying": { "on": { "PHOTO_TAKEN": { "actions": ["decrementBattery"] } } }
  }
}
```

#### `drone_logic.py`

```python
# With Automatic Discovery, this is all you need.
def decrement_battery(interpreter, context, event, action_def):
    context["battery"] -= 1
    print(f"Battery at {context['battery']}%")
```

#### `main.py`

```python
from xstate_statemachine import create_machine, MachineLogic

# 🤖 Option 1: Automatic Discovery (Recommended)
machine = create_machine(drone_config, logic_modules=["drone_logic"])

# 🧠 Option 2: Explicit Binding (Classic)
from drone_logic import decrement_battery
logic = MachineLogic(actions={"decrementBattery": decrement_battery})
machine = create_machine(drone_config, logic=logic)
```

---

### Guards

Guards are conditions that must return `True` for a transition to be taken.

#### `checkout.json`

```json
{
  "id": "cart",
  "context": { "items": [] },
  "on": { "CHECKOUT": { "target": "paying", "guard": "cartIsNotEmpty" } }
}
```

#### `checkout_logic.py`

```python
# With Automatic Discovery, this is all you need.
def cart_is_not_empty(context, event):
    return len(context.get("items", [])) > 0
```

#### `main.py`

```python
from xstate_statemachine import create_machine, MachineLogic

# 🤖 Option 1: Automatic Discovery (Recommended)
machine = create_machine(cart_config, logic_modules=["checkout_logic"])

# 🧠 Option 2: Explicit Binding (Classic)
from checkout_logic import cart_is_not_empty
logic = MachineLogic(guards={"cartIsNotEmpty": cart_is_not_empty})
machine = create_machine(cart_config, logic=logic)
```

---

### Asynchronous Services (`invoke`)

Use `invoke` for long-running or async operations. The machine will transition based on the success (`onDone`) or failure (`onError`) of the invoked async function.

#### `fetch.json`

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
    "success": {}, "failure": {}
  }
}
```

#### `fetch_logic.py`

```python
import aiohttp

# With Automatic Discovery, this is all you need.
async def fetch_user_data(interpreter, context, event):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.example.com/user") as resp:
            resp.raise_for_status()
            return await resp.json()
```

#### `main.py`

```python
from xstate_statemachine import create_machine, MachineLogic

# 🤖 Option 1: Automatic Discovery (Recommended)
machine = create_machine(fetch_config, logic_modules=["fetch_logic"])

# 🧠 Option 2: Explicit Binding (Classic)
from fetch_logic import fetch_user_data
logic = MachineLogic(services={"fetchUserData": fetch_user_data})
machine = create_machine(fetch_config, logic=logic)
```

---

### Timed Events (`after`)

Declaratively schedule transitions after a delay (in milliseconds).

#### `traffic_light.json`

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

Model independent, concurrent regions within a machine. The parent `onDone` fires when all child regions finish.

#### `build.json`

```json
{
  "id": "build",
  "type": "parallel",
  "onDone": "success",
  "states": {
    "backend": { /* ... */ },
    "frontend": { /* ... */ }
  }
}
```

---

### Actors (Spawning Machines)

Spawn child machines from a parent for isolated, concurrent logic. Entry actions use `spawn_<serviceName>`.

#### `main_machine.py`

```python
import asyncio
from xstate_statemachine import create_machine, MachineLogic

# 1. Child machine
child_config = { "id": "pinger", "on": { "PING": { "actions": ["pong"] } } }
child_logic = MachineLogic(
    actions={"pong": lambda i,c,e,a: asyncio.create_task(i.parent.send("PONG"))}
)
child_node = create_machine(child_config, child_logic)

# 2. Parent machine
parent_config = {
    "id": "parent", "initial": "running",
    "states": { "running": { "entry": ["spawn_pingerService"] } },
    "on": { "PONG": "finished" }
}
parent_logic = MachineLogic(services={"pingerService": child_node})

parent_machine = create_machine(parent_config, logic=parent_logic)
```

---

## 🐞 Debugging with Plugins

Use plugins to hook into the interpreter lifecycle. The built-in `LoggingInspector` is great for detailed logs.

```python
import logging
from xstate_statemachine import Interpreter, LoggingInspector

logging.basicConfig(level=logging.INFO)

interpreter = Interpreter(my_machine)
interpreter.use(LoggingInspector())

await interpreter.start()
```

---

## 🤝 Contributing

Contributions are welcome! Open an issue on our [GitHub Issue Tracker](https://github.com/basiltt/xstate-statemachine/issues).

---

## 📄 License

This project is licensed under the MIT License. See the LICENSE file for details.
