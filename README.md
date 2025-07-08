# 🚦 XState StateMachine for Python

A robust, asynchronous, and feature-complete Python library for parsing and executing state machines defined in XState-compatible JSON.

This library brings the power and clarity of formal state machines and statecharts, as popularized by XState, to the Python ecosystem. It allows you to define complex application logic as a clear, traversable graph and execute it in a fully asynchronous, predictable, and debuggable way. By modeling your application's behavior as a state machine, you can prevent impossible states, eliminate a whole class of bugs, and create logic that is easier to visualize, test, and maintain.

Define your logic once in a simple JSON format, and use this library to bring it to life in your Python application.

---

## 🧭 Core Philosophy: Definition vs. Implementation

Modern applications often struggle with managing state. As features are added, the number of possible states and the transitions between them can grow exponentially, leading to tangled if/else statements and unpredictable bugs. This library solves that problem by enforcing a strict separation between your application's flow and its implementation.

**Definition (The "What")**: You define your state machine's structure, states, and transitions in a JSON file. This is your application's blueprint. It describes what can happen and is the single source of truth for your application's logic flow.

**Implementation (The "How")**: You write the business logic—the actual code that runs—in Python. This describes how actions are performed (e.g., updating a database) or services are called (e.g., making an API request).

This separation is the key to building robust and scalable systems.

---

## 🎨 Design Your Logic Visually with the Stately Editor

One of the biggest advantages of using an XState-compatible format is the ability to visualize, design, and even simulate your logic using a graphical interface. The official Stately Editor allows you to drag-and-drop states, define transitions, and export the resulting JSON directly for use with this library. This means you can design your entire application flow with your team on a visual canvas before writing a single line of implementation code.

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

## 🚀 A Visual-First Example: The Traffic Light

Let's walk through the core idea: separating your application's flow (the "what") from its actions (the "how"). You design the flow in a visual editor, which gives you a JSON file that acts as a blueprint. Your Python code then uses this blueprint to run, ensuring your application can never enter an impossible state.

### Step 1: 🚦 Design Your Logic Visually

Imagine you're drawing a flowchart for a traffic light on a whiteboard. It's simple:

![image](https://github.com/user-attachments/assets/fd3a8c61-032a-4269-b872-f876a8ff807d)


1. The light starts as **Green**.
2. After some time, it must turn **Yellow**.
3. After a short time, it must turn **Red**.
4. Finally, after a while, it goes back to **Green**.

A crucial rule is that the light can never go directly from Green to Red. Using a tool like the Stately Editor, you can create this exact flow visually by drawing boxes for each state and arrows for the transitions.

### Step 2: 📜 Get the JSON Blueprint

The JSON file exported from the editor is the "backbone" of your logic. It's a set of rules that your Python code will follow. For our traffic light, the JSON would look like this:

```json
{
  "id": "trafficLight",
  "initial": "green",
  "states": {
    "green": {
      "after": {
        "5000": {
          "target": "yellow"
        }
      }
    },
    "yellow": {
      "after": {
        "2000": {
          "target": "red"
        }
      }
    },
    "red": {
      "after": {
        "5000": {
          "target": "green"
        }
      }
    }
  }
}
```

What this JSON means:

- **"initial": "green"**: The machine always starts in the green state.
- **"after": { "5000": ... }**: This is a timed transition. When in the green state, wait 5000 milliseconds (5 seconds), and then automatically transition to the yellow state.
- The machine enforces the flow: Green can only go to Yellow, and Yellow can only go to Red. It's impossible to jump from Green to Red because there is no rule for it in the blueprint.

### Step 3: 🐍 Run the Blueprint in Python

Now, you can use this JSON file in your Python application without writing if/else statements. Your code just loads the blueprint and runs it:

```python
import asyncio
import json
import logging
from xstate_statemachine import create_machine, Interpreter, LoggingInspector

# --- Basic Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

async def run_traffic_light():
    print("--- 🚦 Traffic Light Simulation Starting ---")

    # 1. Load the JSON blueprint.
    with open("traffic_light.json", "r") as f:
        traffic_light_config = json.load(f)

    # 2. Create a machine instance from the blueprint.
    traffic_light_machine = create_machine(config=traffic_light_config)

    # 3. Create an "interpreter" to run the machine.
    interpreter = Interpreter(traffic_light_machine)
    interpreter.use(LoggingInspector())  # This will print state changes.
    await interpreter.start()

    print(f"✅ Machine started. Initial state: {interpreter.current_state_ids}")
    print("⏳ The machine will now run automatically based on the 'after' delays...")

    # Keep the script running to observe the timed transitions.
    try:
        await asyncio.sleep(20)  # Wait 20 seconds to see a few cycles.
    finally:
        await interpreter.stop()
        print("
--- 🛑 Traffic Light Simulation Stopped ---")

if __name__ == "__main__":
    asyncio.run(run_traffic_light())
```

### Why This is Powerful

- 🛡️ **Bug Prevention**: Your application is now fundamentally safer. It's impossible for a developer to accidentally write code that makes the light go from Green to Red.
- 👁️ **Clear Visualization**: Anyone on your team can look at the visual diagram or the JSON and understand the entire application flow without reading a single line of Python code.
- ✅ **Separation of Concerns**: Your Python code doesn't need to worry about the rules of the flow. It only needs to handle actions when a certain state is entered, making your codebase cleaner and more maintainable.

---

## 🧠 Core Concepts

There are two primary ways to provide your Python implementations to the state machine: Automatic Discovery and Explicit Binding.

- 🤖 **Automatic Discovery (Recommended)**: Place your implementation functions in a module and pass it via `logic_modules`.
- 🧠 **Explicit Binding (Classic)**: Manually create a `MachineLogic` object and pass it via `logic`.

---

### Actions & Context

Actions are "fire-and-forget" side effects that run on state entry, exit, or transitions. Context is the machine's memory where you store dynamic values.

#### `drone.json`

```json
{
  "id": "drone",
  "initial": "flying",
  "context": {
    "battery": 100
  },
  "states": {
    "flying": {
      "on": {
        "PHOTO_TAKEN": {
          "actions": [
            "decrementBattery"
          ]
        }
      }
    }
  }
}
```

#### `drone_logic.py`

```python
# Automatic Discovery example
def decrement_battery(interpreter, context, event, action_def):
    context["battery"] -= 5
    print(f"📸 Photo taken! Battery now at {context['battery']}%")
```

#### `run_drone.py`

```python
import asyncio
import json
from xstate_statemachine import create_machine, Interpreter

async def main():
    with open("drone.json") as f:
        drone_config = json.load(f)

    # Automatic Discovery
    drone_machine = create_machine(drone_config, logic_modules=["drone_logic"])

    interpreter = await Interpreter(drone_machine).start()
    print(f"Initial context: {interpreter.context}")

    await interpreter.send("PHOTO_TAKEN")
    await asyncio.sleep(0.01)

    print(f"Final context: {interpreter.context}")
    await interpreter.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

---

### Guards

Guards are pure functions that return `True` or `False` before a transition.

#### `checkout.json`

```json
{
  "id": "cart",
  "initial": "shopping",
  "context": {
    "items": []
  },
  "states": {
    "shopping": {
      "on": {
        "ADD_ITEM": {
          "actions": [
            "addItem"
          ]
        },
        "CHECKOUT": {
          "target": "paying",
          "guard": "cartIsNotEmpty"
        }
      }
    },
    "paying": {
      "type": "final"
    }
  }
}
```

#### `checkout_logic.py`

```python
def add_item(interpreter, context, event, action_def):
    context["items"].append(event.payload.get("item"))

def cart_is_not_empty(context, event) -> bool:
    is_not_empty = len(context.get("items", [])) > 0
    if not is_not_empty:
        print("GUARD: Cart is empty! Checkout is blocked.")
    return is_not_empty
```

#### `run_checkout.py`

```python
import asyncio
import json
from xstate_statemachine import create_machine, Interpreter

async def main():
    with open("checkout.json") as f:
        cart_config = json.load(f)

    cart_machine = create_machine(cart_config, logic_modules=["checkout_logic"])
    interpreter = await Interpreter(cart_machine).start()

    print("--- Attempting checkout with empty cart ---")
    await interpreter.send("CHECKOUT")
    await asyncio.sleep(0.01)
    print(f"State after first attempt: {interpreter.current_state_ids}")

    print("
--- Adding an item and trying again ---")
    await interpreter.send("ADD_ITEM", item="State-O's Cereal")
    await interpreter.send("CHECKOUT")
    await asyncio.sleep(0.01)
    print(f"State after second attempt: {interpreter.current_state_ids}")

    await interpreter.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

---

### Asynchronous Services (`invoke`)

Invoke long-running or async operations and react to success (`onDone`) or failure (`onError`).

#### `fetch.json`

```json
{
  "id": "fetcher",
  "initial": "loading",
  "context": {
    "user": null,
    "error": null
  },
  "states": {
    "loading": {
      "invoke": {
        "src": "fetchUserData",
        "onDone": {
          "target": "success",
          "actions": [
            "setUser"
          ]
        },
        "onError": {
          "target": "failure",
          "actions": [
            "setError"
          ]
        }
      }
    },
    "success": {
      "type": "final"
    },
    "failure": {}
  }
}
```

#### `fetch_logic.py`

```python
import asyncio
import random

def set_user(i, ctx, evt, ad):
    ctx["user"] = evt.data

def set_error(i, ctx, evt, ad):
    ctx["error"] = str(evt.data)

async def fetch_user_data(interpreter, context, event):
    print("📞 Calling external API...")
    await asyncio.sleep(1)
    if random.random() > 0.3:
        print("✅ API call successful!")
        return {"name": "David K.", "id": "dkp"}
    else:
        print("❌ API call failed!")
        raise ConnectionError("Upstream service timed out")
```

#### `run_fetch.py`

```python
import asyncio
import json
from xstate_statemachine import create_machine, Interpreter

async def main():
    with open("fetch.json") as f:
        fetch_config = json.load(f)

    fetch_machine = create_machine(fetch_config, logic_modules=["fetch_logic"])
    interpreter = await Interpreter(fetch_machine).start()

    await asyncio.sleep(1.5)
    print(f"
Final state: {interpreter.current_state_ids}")
    print(f"Final context: {interpreter.context}")
    await interpreter.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

---

### Other Core Concepts

- **Timed Events (after)**: Declaratively schedule transitions after a delay in milliseconds.
- **Parallel States**: Model independent, concurrent regions within a machine.
- **Actors (Spawning Machines)**: Spawn child machines from a parent for isolated, concurrent logic.

---

## 💡 Putting It All Together: Complex Examples

The library comes with several advanced examples in the `examples/` directory:

- **Coffee Machine**: Simulation demonstrating guards, services, and actions.
- **CI/CD Pipeline**: Deployment pipeline with parallel states and spawned actors.
- **Food Delivery**: Spawns a “delivery driver” actor and communicates with it.

---

## 🐞 Debugging with Plugins

The interpreter supports a plugin system. The built-in `LoggingInspector` is invaluable for seeing exactly what your machine is doing.

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

Contributions are welcome! Please open an issue on our [GitHub Issue Tracker](https://github.com/basiltt/xstate-statemachine/issues).

---

## 📄 License

This project is licensed under the MIT License. See the LICENSE file for details.
