# 🚦 XState - StateMachine for Python
**The Definitive ← _Seriously_ → Guide to Bullet-Proof State Machines**

> _“A good state machine is like a map: once you have it, you’ll never get lost again.”_

---

## 📜 Table of Contents

1. **[Introduction](#introduction)**
2. **[Why State Machines?](#why-state-machines)**
3. **[What is XState-StateMachine?](#what-is-xstate-statemachine)**
4. **[Key Features](#key-features)**
5. **[Installation](#installation)**
6. **[Quick Start](#quick-start)**
7. **[The State Machine Philosophy](#the-state-machine-philosophy)**
8. **[Visual-First Development](#visual-first-development)**
9. **[Anatomy of an XState JSON Blueprint](#anatomy-of-an-xstate-json-blueprint)**
10. **[States — Atomic, Compound, Parallel, Final](#states-—-atomic-compound-parallel-final)**
11. **[Transitions & Events](#transitions--events)**
12. **[Actions, Guards & Services](#actions-guards--services)**
13. **[Context - The Machine’s Memory](#context--the-machines-memory)**
14. **[Declarative Timers (after)](#declarative-timers-after)**
15. **[The Actor Model](#the-actor-model)**
16. **[Architectural Patterns](#architectural-patterns)**
17. **[Synchronous vs Asynchronous Execution](#synchronous-vs-asynchronous-execution)**
18. **[Debugging & Visualization](#debugging--visualization)**
19. **[API Reference](#api-reference)**
20. **[Advanced Concepts](#advanced-concepts)**
21. **[Best Practices](#best-practices)**
22. **[FAQ](#faq)**
23. **[Contributing](#contributing)**
24. **[License](#license)**

---

## 🏁 Introduction<a name="introduction"></a>

Welcome to **XState-StateMachine for Python**, a **robust**, **async-ready**, and **feature-complete** library for building, parsing, and executing **state machines** and **statecharts** defined in **XState-compatible JSON**.

Whether you’re a **junior dev** struggling with spaghetti `if/else` trees 🌱 _or_ a **senior architect** with half a century of scars and stories 🦖, this README is crafted to be your **_Bible_**. By the time you finish, you’ll know **why** state machines matter, **how** to model them visually, and **exactly** what code to write to run them in production-grade Python.

---

## ❓ Why State Machines?<a name="why-state-machines"></a>

1. **Eliminate Impossible States 🧹**
   Four boolean flags ➡ **16** possible combinations. _How many are valid?_ State machines guarantee you’ll **never** enter a “loading + error” paradox again.

2. **Explode Complexity—In a Good Way 💥**
   Complexity _will_ happen. Put it in a **graph** where it’s explicit, testable, and visualized—rather than hidden in nested conditionals.

3. **Single Source of Truth 🔑**
   Your JSON blueprint declares every state, event, and transition. **No surprises** lurking in random helper functions.

4. **Self-Documenting 📚**
   A statechart _is_ the documentation. No more stale flow-charts stuck in a Confluence graveyard.

5. **Safer Concurrency 🛡️**
   Parallel states and the Actor Model let you reason about multi-threaded logic **without** race-condition nightmares.

---

## ✨ What is XState-StateMachine?<a name="what-is-xstate-statemachine"></a>

* A **Pythonic** runtime for the world-famous **[XState](https://stately.ai)** architecture.
* **100 % JSON-spec-compatible**, so you can design your chart in the Stately editor and run it untouched.
* **Async first** (`asyncio`), yet ships a **blocking** `SyncInterpreter` for CLI tools, GUI apps, or tests.
* Packed with goodies: **hierarchy, parallelism, invoke**, **after**, timers, **actors**, auto-binding logic loaders, plugin hooks, diagram generators, and more.

> **TL;DR** — If you know XState in JS, everything 👉 “just works” in Python.
> If you don’t, keep reading—this guide is for you.

---

## 🚀 Key Features<a name="key-features"></a>

| Feature | Why You Care | Best For |
| :--- | :--- | :--- |
| **100% XState Compatibility** | Design visually, export JSON, run in Python. | Teams that want to use visual tools like the Stately Editor for collaboration and design. |
| **Async & Sync Interpreters** | Use the same machine logic for a web server or a desktop app. | Building flexible libraries or applications that need to run in different Python environments. |
| **Hierarchical States** | Organize complex logic by nesting states (e.g., `editing.typing`). | Modeling UI components, wizards, or any process that has distinct sub-steps. |
| **Parallel States** | Model independent, concurrent state regions. | Complex systems where multiple things happen at once, like a smart home (`lighting`, `climate`). |
| **The Actor Model** | Spawn child machines for ultimate concurrency and isolation. | Orchestrating multiple, independent components like IoT devices, user sessions, or background jobs. |
| **Declarative `invoke`** | Handle async tasks with declarative `onDone`/`onError` handlers. | Any interaction with a database, API, or external service that can succeed or fail. |
| **Declarative `after`** | Create time-based transitions without manual `sleep()` calls. | Implementing timeouts, polling, debouncing, or slideshow-like delays. |
| **Automatic Logic Binding**| Drastically reduce boilerplate by auto-linking your code to the JSON. | Rapid development and keeping your implementation code clean and decoupled. |
| **Plugin System** | Hook into the interpreter lifecycle with fine-grained callbacks (e.g., on guard evaluation, service start/done/error). | Adding cross-cutting concerns like logging, analytics, or persistence without touching core logic. |
| **Diagram Generators** | Keep your documentation perfectly in sync with your code. | Projects that require accurate, up-to-date architectural diagrams. |

---

## 🛠️ Installation<a name="installation"></a>

```bash
# 1️⃣ Create & activate a virtual env  (recommended)
python -m venv venv
source venv/bin/activate           # Windows → venv\Scripts\activate

# 2️⃣ Install the library
pip install xstate-statemachine
```

> **Requirements**: Python 3.8 +

---

## ⚡ Quick Start<a name="quick-start"></a>

A lightspeed tour: toggle a light 💡—the “Hello World” of state machines.

### 1. Blueprint (`light_switch.json`)

```jsonc
{
  "id": "lightSwitch",
  "initial": "off",
  "context": {
    "flips": 0
  },
  "states": {
    "off": {
      "on": {
        "TOGGLE": {
          "target": "on",
          "actions": "increment_flips"
        }
      }
    },
    "on": {
      "on": {
        "TOGGLE": {
          "target": "off",
          "actions": "increment_flips"
        }
      }
    }
  }
}
```

### 2. Logic (`light_switch_logic.py`)

```python
import logging
from typing import Dict
from xstate_statemachine import Interpreter, Event, ActionDefinition

def increment_flips(i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition):
    ctx["flips"] += 1
    logging.info(f"🔀 Switch flipped {ctx['flips']} time(s).")
```

### 3. Runner (`main.py`)

```python
import asyncio
import json
import light_switch_logic # Use a standard import
from xstate_statemachine import create_machine, Interpreter

async def main():
    with open("light_switch.json") as f:
        config = json.load(f)

    # Pass the imported module object directly for auto-discovery. This is cleaner.
    machine = create_machine(config, logic_modules=[light_switch_logic])

    interpreter = await Interpreter(machine).start()
    await interpreter.send("TOGGLE")
    await interpreter.send("TOGGLE")
    await interpreter.stop()

asyncio.run(main())
```

**Output**

```
INFO 🔀 Switch flipped 1 time(s).
INFO 🔀 Switch flipped 2 time(s).
```

Boom—**no `if current_state == "on"` anywhere**. 🎉

#

### A Very Simple Sync Example: The Toggle Switch

Here is the most basic example of a synchronous state machine. It has only two states (`on` and `off`) and one event (`TOGGLE`). It perfectly illustrates how the `SyncInterpreter` processes events immediately.

#### 1. The Blueprint: `toggle_switch.json`

This JSON defines the structure. It starts `off`, and the `TOGGLE` event switches it to `on` (and vice-versa), running an action called `increment_toggles` each time.

```json
{
  "id": "toggleSwitch",
  "initial": "off",
  "context": {
    "toggleCount": 0
  },
  "states": {
    "off": {
      "on": {
        "TOGGLE": {
          "target": "on",
          "actions": [
            "increment_toggles"
          ]
        }
      }
    },
    "on": {
      "on": {
        "TOGGLE": {
          "target": "off",
          "actions": [
            "increment_toggles"
          ]
        }
      }
    }
  }
}
```

#### 2. The Logic and Runner: `main_sync.py`

For maximum simplicity, we'll define the logic and the simulation in the same file.

```python
import json
import logging
from typing import Dict, Any

from xstate_statemachine import (
    create_machine,
    SyncInterpreter,
    MachineLogic,
    Event,
    ActionDefinition
)

# --- Basic Setup ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

# --- 1. The Logic (Action) ---
# This is the single action our machine will execute.
def increment_toggles(i: SyncInterpreter, ctx: Dict, e: Event, a: ActionDefinition) -> None:
    """Action to increment the toggle count in the context."""
    ctx["toggleCount"] += 1
    logging.info(f"💡 Light is now {i.current_state_ids}. Toggle count: {ctx['toggleCount']}")

# --- 2. The Simulation ---
def run_simple_toggle():
    """Initializes and runs the toggle switch simulation."""
    print("\n--- 💡 Simple Synchronous Toggle Switch ---")

    # Load the machine configuration from the JSON file
    with open("toggle_switch.json", "r") as f:
        config = json.load(f)

    # Explicitly bind the action name "increment_toggles" from the JSON
    # to our Python function.
    logic = MachineLogic(
        actions={"increment_toggles": increment_toggles}
    )

    # Create the machine and the synchronous interpreter
    machine = create_machine(config, logic=logic)
    interpreter = SyncInterpreter(machine)

    # Start the machine. It enters the 'off' state.
    interpreter.start()
    logging.info(f"Initial state: {interpreter.current_state_ids}")

    # Send the first event. The machine transitions to 'on'
    # and the 'increment_toggles' action runs before this line finishes.
    print("\n--- Toggling ON ---")
    interpreter.send("TOGGLE")

    # Send the second event. The machine transitions back to 'off'
    # and the action runs again.
    print("\n--- Toggling OFF ---")
    interpreter.send("TOGGLE")

    # Stop the machine
    interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")

if __name__ == "__main__":
    run_simple_toggle()
```

#### Expected Output

When you run `main_sync.py`, you will see the following output, demonstrating that each `send` call completes its work before the next print statement is executed:

```text
--- 💡 Simple Synchronous Toggle Switch ---
[INFO] Initial state: {'toggleSwitch.off'}

--- Toggling ON ---
[INFO] 💡 Light is now {'toggleSwitch.on'}. Toggle count: 1

--- Toggling OFF ---
[INFO] 💡 Light is now {'toggleSwitch.off'}. Toggle count: 2

--- ✅ Simulation Complete ---
```

---

## 🧭 The State Machine Philosophy<a name="the-state-machine-philosophy"></a>

> **Definition ↔ Implementation** separation is the super-power.

* **Definition** (`.json`) 😇 — declares _what can happen_.
  * Finite states
  * Events
  * Valid transitions
  * Timers, services, hierarchy

* **Implementation** (`.py`) 🛠️ — implements _how it happens_.
  * Fetch an API
  * Write a file
  * Update UI

Because the **graph never mutates**, every team-mate sees the same reality. Changing business rules is as easy as editing JSON and re-running tests—**logic stays untouched**.

---

## 🎨 Visual-First Development<a name="visual-first-development"></a>



1. **Design** in the **Stately Editor** → drag states, draw arrows.
2. **Export** to JSON (one click).
3. **Run** with `create_machine(config)` in Python.
4. **Simulate** inside Stately _or_ via Python tests—they behave identically.

### Why It Rocks:

* **Stakeholder Friendly** — Product managers & QA can _read_ and _play_ with the diagram.
* **Zero Drift** — Diagram **is** the code. Update one, you update both.
* **Faster On-Boarding** — New hires grok the flow in minutes, not days.

---


### 🖼️ Designing with Stately Visual Editor<a name="stately-visual-editor"></a>

> “If a picture is worth a thousand words, a *statechart* is worth a thousand **unit-tests**.”

The **[Stately Visual Editor](https://stately.ai/editor) →** is the *single most productive tool* in the XState ecosystem.
It lets you **draw** your machine, **simulate** it in real‑time, and **export** a perfectly–valid JSON blueprint that runs *unchanged* in `xstate‑statemachine` for Python.

### 🔑 Why the Editor Matters

| Benefit | What it Means for You |
|---------|-----------------------|
| **WYSIWYG Modelling** | Drag‑and‑drop states, draw transitions, and tweak guards—no JSON eye‑strain. |
| **Instant Simulation** | Play events, watch timers fire, and inspect context mutations live before writing Python code. |
| **Team Collaboration** | Share a link; PMs and QA can *see* the flow and leave comments, killing a whole back‑and‑forth thread of screenshots. |
| **Source of Truth** | The exported JSON *is* the code—zero drift between docs and implementation. |
| **Version Control Friendly** | Download the JSON (or embed it in your repo) and diff it like any other text asset. |

### 🛠️ Typical Workflow

1. **Sketch** the high‑level flow on a whiteboard (or directly in the editor).
2. **Model** it in the Stately Editor:
   * Add *states* (double‑click canvas)
   * Create *transitions* (drag arrow from one state to another)
   * Configure *events*, *guards*, *actions*, *after* timers, and *invoke* services in the side‑panel UI.
3. **Simulate**: hit ▶️, dispatch events, and watch the visual debugger update in real time.
4. **Export** → **“Machine JSON”** (⚙️ menu → *Export → Machine JSON*).
   Save as `my_machine.json` in your project’s `statecharts/` folder.
5. **Run** it with:

   ```python
   from xstate_statemachine import create_machine, Interpreter
   import json, asyncio

   cfg = json.load(open("statecharts/my_machine.json"))
   machine = create_machine(cfg, logic_modules=[my_logic])
   await Interpreter(machine).start()
   ```

6. **Iterate**: tweak the diagram, re‑export, rerun tests. Your Python logic remains untouched.

### 🎨 Pro Tips for Power Users

| Tip | Shortcut / Action |
|-----|-------------------|
| **Multi‑Select** | <kbd>Shift</kbd> + Click or drag marquee to move/align groups of states. |
| **Quick Transition** | Hold <kbd>A</kbd>, click source state, then click target state. |
| **Relative Targets** | Double‑click a self‑transition arrow to toggle between **internal** and **external** (re‑entry) semantics. |
| **Context Visualisation** | In the *Simulate* tab, expand **Context** to live‑edit values while the machine is running—great for guard testing. |
| **Export Diagram** | *Export → SVG / PNG* to embed in GitHub docs; keep diagrams and JSON in‑sync ✨. |
| **Embed Gist** | Publish the machine as a sharable, *live* gist you can link in PR descriptions. |


---

## 🧬 Anatomy of an XState JSON Blueprint<a name="anatomy-of-an-xstate-json-blueprint"></a>

Every machine is a tree of **StateNodes**. Let’s break down the top-level keys:

| Key | Type | Description |
|---|---|---|
| `id` | **string** | Unique machine ID, root of every absolute state path. |
| `initial` | **string** | State where the interpreter starts. |
| `context` | **object** | Mutable “memory” available to every action/guard. |
| `states` | **object** | Map of state → StateNode definition. |
| `on` | **object** | _Global_ event handlers (catch-all). |

Example from your files: The `flightBooking.json` machine has a root `id` of `"flightBooking"`.

Example from your files: The `ciCdPipeline.json` defines an initial `context` to track the state of a deployment process:
```jsonc
"context": {
  "build_artifact": null,
  "commit_hash": null,
  "deployment_url": null,
  "error": null,
  "scan_results": null,
  "test_results": null
}
```

### Target Resolution: How the Machine Finds the Next State

When you define a transition with a `target`, the library uses a powerful resolution mechanism to find the destination state. This allows for flexible and intuitive state navigation.

-   **Sibling State (Most Common):** If you provide a simple name, the interpreter looks for a state with that name within the *same parent*.

    ```json
    "green": {
      "on": { "TIMER": "yellow" } // Looks for "yellow" alongside "green"
    },
    "yellow": {},
    "red": {}
    ```

-   **Child State (Dot Notation):** To target a descendant state, use dot notation.

    ```json
    "on": {
      "GO_TO_DEEP_STATE": "parent.child.grandchild"
    }
    ```

-   **Relative Path (Leading Dot):** A leading dot (`.`) makes the path relative to the *parent* of the current state. This is extremely useful for sibling-to-sibling transitions inside a compound state.

    ```json
    "parent": {
      "initial": "child1",
      "states": {
        "child1": { "on": { "NEXT": ".child2" } }, // Correctly targets parent.child2
        "child2": {}
      }
    }
    ```

-   **Absolute Path (Leading Hash):** A leading hash (`#`) makes the path absolute from the root of the machine, using the machine's `id`. This is the safest way to target a state from a deeply nested location without ambiguity.

    ```json
    "deeply": {
      "nested": {
        "state": {
          "on": {
            "GO_HOME": "#myMachine.idle" // Always goes to the top-level idle state
          }
        }
      }
    }
    ```

#### 🛣️ Edge‑Cases & Safety Nets

| Target Syntax | Resolved To | When to Use |
|---------------|------------|-------------|
| `"."` | **Parent state** of the current state &nbsp;▸ if already at the root, it resolves to the **root itself**. | Jump back one level without hard‑coding the parent’s ID. Handy inside deeply nested compound states. |
| `a..b` &nbsp;or&nbsp; `state.` | **❌ Invalid** — the library rejects any target that contains empty path segments (double dots `..` or a trailing dot `.`) and raises **`StateNotFoundError`**. | Typos happen! The explicit error prevents silent mis‑navigation and keeps your diagrams truthful. |

> 💡 **Tip:**  When debugging a mysterious *StateNotFoundError*, check for an accidental double‑dot or dangling dot in your `target` strings.


---

## 🏛️ States — Atomic • Compound • Parallel • Final<a name="states-—-atomic-compound-parallel-final"></a>

### 1️⃣ Atomic

> **No children.** Think “leaf node.”

```jsonc
"idle": {
  "on": { "FETCH": "loading" }
}
```

### 2️⃣ Compound

> **Has its own `initial` + `states`.**

Example from your files: In installWizard.json, the "configuring" state is a compound state that contains its own sub-machine for handling the configuration steps.

```jsonc
"configuring": {
  "initial": "network",
  "onDone": "installing",
  "states": {
    "network": {
      "on": {
        "SUBMIT_NETWORK": "database"
      }
    },
    "database": {
      "on": {
        "SUBMIT_DATABASE": "admin_user"
      }
    },
    "admin_user": {
      "on": {
        "SUBMIT_ADMIN": "config_complete"
      }
    },
    "config_complete": {
      "type": "final"
    }
  }
}
```

### 3️⃣ Parallel

> **All child regions active at once.** Perfect for independent subsystems.

Example from your files: The smartHome.json machine uses a parallel state at its root to manage lighting, climate, and security as independent, concurrent regions.

```jsonc
"dashboard": {
  "type": "parallel",
  "states": {
    "notifications": {
      /* handles toasts */
    },
    "socket": {
      /* websocket connect/close */
    },
    "theme": {
      /* dark / light */
    }
  }
}
```

### 4️⃣ Final

> **Signals completion** to parent; triggers `onDone` transition.

```jsonc
"success": { "type": "final" }
```

---

## 🔄 Transitions & Events<a name="transitions--events"></a>

### 🌊 Event Lifecycle & Synthetic Events<a name="event-lifecycle"></a>

A state machine **lives and breathes events**.
Besides the ones *you* dispatch, the runtime forges its own messages and even
loops internal “always” transitions until the graph stabilises.
Understanding these moving parts lets you write bullet‑proof tests, guards and
plugins. 🔍

---

#### 1️⃣ `.send()` – One API, Three Input Flavours

| What you call | What the helper returns | Notes |
|---------------|------------------------|-------|
| `service.send("CLICK", x=1)` | `Event(type="CLICK", payload={"x": 1})` | Snack‑size syntax |
| `service.send({"type": "CLICK", "x": 1})` | ditto | Handy when forwarding raw JSON |
| `service.send(Event("CLICK", {"x": 1}))` | *unchanged* | Already a proper `Event` |

`BaseInterpreter._prepare_event` does the coercion, so every path into the
interpreter is **consistent & type‑safe**. ✔️

---

#### 2️⃣ Runtime‑Generated (Synthetic) Events

| Pattern | ✨ When it fires | Typical purpose |
|---------|-----------------|-----------------|
| `entry.<stateId>` | Right before a state’s **entry actions** run | Side‑effect hooks, analytics |
| `exit.<stateId>` | After **exit actions** finish | Cleanup metrics, audit |
| `___xstate_statemachine_init___` | Once, at machine start‑up | Kick‑start transient guards |
| `after.<delay>.<stateId>` | `after { "<delay>": … }` timer expires | Declarative timeouts / polling |
| `done.state.<stateId>` | A **compound / parallel** state reaches all its finals | Bubble completion upward |
| `done.invoke.<src>` | An **invoked service** returns successfully | Happy‑path transitions |
| `error.platform.<src>` | Invoked service raised / rejected | Failure branch |

Because they are regular events you can:

```python
await interp.send("after.5000.flightBooking.loading")   # force timeout in tests
plugin.on_event_received = lambda _, e: print(e.type)
```

---

#### 3️⃣ Transient (“Always”) Transitions `""`

An empty‑string event (`""`) models *automatic* logic that should run
**immediately** after a state becomes active:

```jsonc
"checking": {
  "on": {
    "": [
      { "guard": "isValid",   "target": "approved" },
      {                     "target": "rejected" }
    ]
  }
}
```

* Both interpreters keep looping
  `while optimal_transition.event == "": …`
  (`Interpreter._run_event_loop`, `SyncInterpreter._process_transient_transitions`)
  until **no** guard passes.
* Guards must be **pure & synchronous** — they run potentially many times per
  event cycle.
* Great for conditional redirects, validation gates and hierarchical
  “initial” logic.

---

📝 **Cheat‑sheet**

```text
You           Engine                          What you observe
──────────── ─────────────────────────────── ─────────────────────────────────
service.send("CLICK")      ─────▶  CLICK
state entry                ─────▶  entry.someState
timer 2 s later            ─────▶  after.2000.someState
service success            ─────▶  done.invoke.fetchData
compound finished          ─────▶  done.state.parent.compound
```

Now you can assert, spy and debug every heartbeat of your machine. 🎉

* **Event-driven** — under `on`.
* **Time-driven** — under `after`.
* **Done/Error** — from invoke services → auto-events `done.invoke.<src>` & `error.platform.<src>`.

```jsonc
"loading": {
  "invoke": {
    "src": "fetchData",
    "onDone": {
      "actions": "cacheData",
      "target": "success"
    },
    "onError": {
      "actions": "setError",
      "target": "failure"
    }
  },
  "after": {
    "5000": {
      "target": "timeout"
    }
    // If it hangs for 5 s
  }
}
```

#### 📨 How service results travel back into the machine

When an **invoked service** (sync *or* async) finishes **successfully**,
its *return value* is baked into a **`DoneEvent`**:

```
type =  "done.invoke.<serviceId>"
data =  <return value of your Python function>
```

That payload is now available to **guards** & **actions** via
`event.data` — use it to make decisions or stash the result in context.

```python
# guards.py
def is_valid_response(ctx, event):
    # event.data is whatever the service returned 🙌
    return event.data.get("status") == 200

# actions.py
def store_payload(i, ctx, event, a):
    ctx["payload"] = event.data["body"]
```

```jsonc
"loading": {
  "invoke": {
    "src": "fetchData",
    "onDone": [
      { "target": "success", "guard": "is_valid_response", "actions": "store_payload" },
      { "target": "failure" }
    ],
    "onError": "failure"
  }
}
```

> 🔎 **Tip:** In unit tests you can *stub* the service to return a canned
> object and assert that `ctx["payload"]` matches it, without hitting the
> network. Fast & deterministic! 🧪


### Internal vs External Transitions<a name="internal-vs-external-transitions"></a>

When an **event matches a transition _without_ a `target`**, the machine stays
_in the current state_ and merely **executes the transition’s actions / guard**.
This is called an **internal transition** – the state’s `exit`, `entry`, `after`
timers and any `invoke`d service keep running untouched.

```jsonc
"playing": {
  "on": {
    "UPDATE_METADATA": {
      // 👇 no `target`  → internal
      "actions": "updateTitle"
    }
  }
}
```

Conversely, **the moment a `target` key is present, the transition is
_external_ – even if that target is the very state you are already in.**
The state is exited, its timers / services are cancelled, the transition’s
actions run, and then the state is re‑entered (triggering `entry` actions
and restarting any `after` timers or `invoke`s).

```jsonc
"logged_in": {
  "after": { "3000": "timed_out" },
  "on": {
    "USER_ACTIVITY": {
      "target": "logged_in"   // self‑target  → external
      // Re‑entering resets the 3 s inactivity timer above
    }
  }
}
```

> **Gotcha:**
> XState‑StateMachine **does not recognise** an `"internal": true/false`
> flag (it isn’t part of the JSON grammar).
> *No `target` → internal • Any `target` → external.*

| Use this when … | … you want |
|-----------------|-----------|
| **Internal** &nbsp;*(no target)* | Update context / fire side‑effects **without** interrupting timers or services. |
| **External** &nbsp;*(has target)* | Force a full exit/re‑entry cycle – e.g. reset a countdown, restart an `invoke`, or replay `entry` actions. |

---

## 🛠️ Actions, Guards & Services<a name="actions-guards--services"></a>

#### ✅ Good – deterministic & side‑effect‑free

```python
def can_retry(ctx, event) -> bool:
    return ctx["attempts"] < 3
```

#### 🚫 Bad – asynchronous

```python
async def remote_rule(ctx, event):
    result = await fetch_flag()            # blocking the event loop = 💥
    return result == "ALLOW"
```

#### 🚫 Bad – non‑boolean return

```python
def non_bool(ctx, event):
    return "yes" if ctx["foo"] else ""     # Truthy string! ⚠️
```

While `"yes"` passes today, **explicit `True`/`False` is required** for
readability and future compatibility.

---

##### Tip 💡 – Keep Them 100 % Pure

* **No logging** inside guards – use an action instead.
* **No mutation** of `ctx`. Guards run many times (transients!), so mutating
  state here creates elusive bugs.

---

Now your transitions obey the *Law of Least Surprise*: one question, one crisp
answer, synchronously. 🏁

| Kind | When Runs | Signature | Return |
|------|-----------|-----------|--------|
| **Action** | On entry/exit/transition | `(interp, ctx, event, action_def)` | `None` |
| **Guard**  | Before transition decision | `(ctx, event)` | `bool` |
| **Service**| Inside `invoke` (async or sync) | `(interp, ctx, event)` | `value` or **raise** |


> 🐍 **Snake → Camel Autowiring** 🐫
> The loader automatically converts **`snake_case`** Python function names
> to **`camelCase`** keys expected in your JSON.
> No manual mapping needed — simply define:
>
> ```python
> def increment_flips(i, ctx, e, a): ...
> ```
>
> …and reference it in JSON as:
>
> ```jsonc
> "actions": "incrementFlips"
> ```
>
> The helper `logic_loader._snake_to_camel()` does the heavy lifting, so you
> stay idiomatic in Python **and** compliant with XState’s camel‑cased world. ✨


> ℹ️ Automatic Logic Discovery binds JSON names to Python callables **by convention** (`snake_case ⇌ camelCase`). Anything unmatched raises `ImplementationMissingError`.

---

## 🧠 Context - The Machine’s Memory<a name="context--the-machines-memory"></a>

A plain dict **shared** across all states. Mutate it inside **actions** and **services**; read-only in **guards**.

```jsonc
"context": {
  "retryCount": 0,
  "payload": null,
  "error": null
}
```

```python
def increment_retry(i, ctx, e, a):
    ctx["retryCount"] += 1
```

Rule of thumb 🧘: **Pure guards** & **deterministic actions** → easier tests.

---

## ⏰ Declarative Timers (`after`)<a name="declarative-timers-after"></a>

> **Key idea:** you declare **_intent_**, not implementation.
> The interpreter owns the stopwatch so *you* don’t have to.

| What you write | What the engine does |
|----------------|----------------------|
| `after: { "500": "blink" }` | Starts a 500 ms countdown *every* time the state is entered |
| `after: { "1000": { "target": "retry", "actions": "backoff" } }` | Schedules an internal event, then cancels it automatically if the state exits early |
| `after: { "…": { …, "guard": "stillRelevant" } }` | Evaluates guard *right before* firing—handy for stale timers |

### Anatomy of an `after` Event

```
after(<delay>)#<absoluteStateId>
└──── ─────── ── ───────────────
   |     |          |
   |     |          ↳ state that was active when timer started
   |     |
   |     ↳ milliseconds (integer)
   |
   ↳ literal string “after”
```

Knowing the auto‑generated `type` helps if you need to **assert** or **spy** on timers in tests:

```python
await interp.send("START_LOAD")
await asyncio.sleep(0.01)                  # Allow event loop to process
assert "loading" in interp.current_state_ids

# Fast‑forward virtual time by monkey‑patching loop.time() — or simpler:
await asyncio.sleep(5.1)                   # let after(5000) fire
assert "timeout" in interp.current_state_ids
```

### ⚡ Multiple Timers in One State

Attach *several* `after` clauses—think **progressive back‑off**:

```jsonc
"retrying": {
  "entry": "incAttempts",
  "after": {
    "1000": {
      "target": "fetching",
      "guard": "fewAttempts"
    },
    "5000": {
      "target": "giveUp",
      "actions": "alertOps"
    }
  }
}
```

If `fewAttempts` returns **false**, the 1‑second timer is ignored; the 5‑second timer is still pending.

### ⏱️ Looping Timers (Self‑Transition)

```jsonc
"flashing": {
  "after": {
    "250": {
      "actions": "toggleLED",
      "target": ".flashing"
    }
  }
}
```

Because the target is **relative** (`.flashing`), the state re‑enters itself, creating a persistent 250 ms blink. The interpreter guarantees only **one live timer** at a time—previous handles are cancelled on re‑entry.

### Cancellation & Clean‑Up

Leaving a state *always* cancels its timers.

* No memory leaks
* No stray events after the user navigates away
* Predictable “at‑most‑once” semantics

### Testing Timers 🧪

1. **Unit** – patch the event loop clock (`pytest‑asyncio`’s `advance_time`) and assert the synthetic event.
2. **Integration** – run under a virtual loop with controlled time.
3. **Snapshots** – diff context before & after the timer fires.

### Common Pitfalls & Remedies

| Pitfall | Symptom | Remedy |
|---------|---------|--------|
| Timer never fires | Guard returns `False`; or state changed before delay | Log guard or use `LoggingInspector` |
| Fires twice | Re‑entering state via **different absolute ID** in hierarchy | Use absolute target (`"#machine.state"`) or guard |
| Delay starts late | Long CPU loop in entry action | Make actions async & yield `await asyncio.sleep(0)` |

#

#### 🗂️ TaskManager – Zero‑Leak Guarantees<a name="taskmanager"></a>

Every **`after` timer** ⏱️ and each **`invoke` service** 📞 is wrapped in an
`asyncio.Task` and **registered per‑state**:

```text
stateId ─┬─ after‑5000 timer        ─┐
         ├─ after‑10000 timer  ──────┤───▶ TaskManager.add(owner_id, task)
         └─ invoke.fetchData task ───┘
```

Why it matters:

| ⭐ Benefit | How it works |
|-----------|--------------|
| **No orphaned coroutines** | When a state exits, the interpreter calls **`TaskManager.cancel_by_owner(state.id)`**, which iterates over every recorded task, `task.cancel()`s them, and awaits graceful shutdown. |
| **Memory‑safe** | The internal map is cleaned after cancellation, so tasks don’t linger in RAM. |
| **Race‑condition free** | Timers or services started in a state **cannot** out‑live that state; you’ll never receive a late “after” event for something that’s no longer on screen. |

> 🔒 **Guarantee:** If your JSON says *“when I leave `loading`, kill the fetch”*,
> the engine obeys—*you* write zero cancellation code.

---

##### 🧪 White‑Box Testing Helper

Need to assert that a timer or service *is* (or *isn’t*) running?

```python
tasks = interpreter.task_manager.get_tasks_by_owner("search.loading")
assert len(tasks) == 1          # the after(8000) timeout
```

`get_tasks_by_owner(owner_id)` returns a **copy** of the task set, so your test
can **inspect** without risking accidental mutation.

---

⌛ **Bottom line:** Declarative timers and invokes stay tidy, deterministic and
resource‑safe—no leaks, no zombies, no surprises. 🧹🔒
---

## 🎭 The Actor Model (Deep Dive)<a name="the-actor-model"></a>

While `invoke` is perfect for calling a single function, the **Actor Model** is for when you need to manage an entire, long-living, stateful process as a child of your main machine. Actors are simply other state machine interpreters that are "spawned" and managed by a parent.

This pattern is the key to unlocking massive architectural freedom and managing complex concurrency with grace.

### 📐 Reference Diagram

The relationship is simple: a parent spawns a child, can send it messages (events), and the child can send messages back to its parent.

```text
┌───────── Parent Machine ─────────┐
│                                  │
│  Action: "spawn_myActor"         │
│      │                           │
│      ▼                           │
│  ╔═════════════╗ Parent can send │
│  ║ Child Actor ║────────────────►│
│  ║ Interpreter ║◄────────────────┤
│  ╚═════════════╝ Child can send  │
│                  (via i.parent)  │
│                                  │
└──────────────────────────────────┘
```

### Messaging Patterns

The actor model enables powerful communication patterns between components.

| Pattern | How It Works | Use Case |
|---------|--------------|----------|
| **Request/Reply** | A child actor performs a task and sends a **RESULT** or **FAILURE** event back to its direct parent when it completes. | `warehouseRobot` spawns a `pathfinder` actor to calculate a route and report back. |
| **Command** | The parent looks up a specific child in its `interpreter._actors` registry and sends it a command event such as `PAUSE` or `UPDATE_CONFIG`. | A `mediaPlayer` machine telling its spawned `volumeControl` actor to mute/un‑mute. |
| **Broadcast** | The parent iterates over **all** `interpreter._actors.values()` and sends the same event to every child. | A `collaborativeEditor` machine telling all cursor actors to change colour or display an annotation. |
| **Escalation** | A deeply‑nested child actor hits an unrecoverable error and bubbles it up by calling `await i.parent.parent.send("CHILD_FAILED", error=str(e))`. | A low‑level network actor fails and tells the top‑level app machine to show a global “Offline” banner. |

### Event Flow of an Actor Interaction

Let's trace the `warehouseRobot` example to see how the parent and child communicate:

1.  **Parent (`warehouseRobot`)** enters the `planning_route` state.
2.  **Parent**'s `entry` action (`spawn_pathfinder_actor`) is executed.
    - An `Interpreter` for the `pathfinder` machine is created and started. This is the **Child Actor**.
3.  **Child (`pathfinder`)** immediately enters its `calculating` state.
4.  **Child** `invoke`s its `calculate_path_service`.
5.  *(...time passes...)*
6.  **Child**'s service finishes successfully, triggering its `onDone` transition.
7.  **Child**'s `onDone` action (`send_path_to_parent`) is executed.
    - Inside this action, it calls `await i.parent.send("PATH_CALCULATED", ...)`
8.  **Parent**'s event loop receives the `PATH_CALCULATED` event.
9.  **Parent** follows its own transition for this event, running the `store_path` action and moving to the `moving` state.
10. **Child** moves to its `finished` state and terminates.

This clear, decoupled communication is what makes the Actor Model so powerful for complex systems.

### Dynamic Pools

### 🚀 `spawn_<name>` Actions — How Actors Are Born<a name="spawn-actions"></a>

Spawning a child machine is as simple as defining an **action whose type
starts with `spawn_`**.
Behind the emoji‑curtain, the interpreter performs four deterministic steps:

| Step | Code Location | What happens |
|------|---------------|--------------|
| **1. Name resolution** | `Interpreter._spawn_actor` | Strips the `spawn_` prefix to obtain `<name>` and looks it up in `machine.logic.services["<name>"]`. |
| **2. Source validation** | same | &nbsp;&nbsp;→ If the value is already a **`MachineNode`** ☑️ use it as‑is.<br>&nbsp;&nbsp;→ If it’s a *callable*, it’s treated as a **factory** — the function is invoked with `(interpreter, ctx, event)` and **must** return a `MachineNode`. |
| **3. ID assignment** | same | The child interpreter’s `.id` is built as:<br>`{parentId}:{name}:{uuid4()}`  &nbsp;🆔<br>Example: `shoppingCart:paymentActor:3e3b6b9c-…` |
| **4. Start & register** | same | A new `Interpreter(child_machine)` is created, `.start()`ed, and stored in `parent._actors[childId]`. |

If the provided MachineNode/factory is invalid, the engine raises
**`ActorSpawningError`** 🛑 — inherit from `XStateMachineError` so you can
`pytest.raises()` it.

```python
# The happy path 🎉
services = {
    "paymentActor": create_machine(payment_cfg, logic=payment_logic),

    # OR factory variant (gets runtime data):
    "dynamicActor": lambda i, ctx, e: create_machine(build_cfg(ctx["type"]))
}
```

```python
# The unhappy path 😬  – raises ActorSpawningError
services = {
    "oops": "not a machine"        # 🤦‍♀️ typo or wrong return
}
```

> 📝 **Remember:** spawned actors live until **you** stop them (or their parent
> stops). They inherit their parent’s plugins automatically for consistent
> logging/metrics.

You can dynamically create and destroy actors at runtime, which is perfect for managing pools of workers or user sessions.

```python
# An action in your parent machine's logic
def spawn_worker(i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition):
    # Use the context to track the next available ID
    worker_id = ctx["next_id"] = ctx.get("next_id", 0) + 1

    # The service must return a MachineNode
    worker_machine = create_machine(worker_config, logic=worker_logic)

    # The interpreter automatically starts the new actor
    # and adds it to its internal `_actors` dictionary.
    # The key here is for your own reference.
    actor_instance_id = f"worker:{worker_id}"
    i._actors[actor_instance_id] = Interpreter(worker_machine).start()

    logging.info(f"✅ Spawned new worker: {actor_instance_id}")
```

### Supervision Strategies 🛡️

A robust system must know how to handle actor failures. While the library does not emit a special `error.actor.*` event automatically, it provides the primitives to build any supervision strategy you need. The recommended pattern is for the child to report its own failure to the parent.

**The Pattern:**

1. The child actor has an `onError` handler on its critical invoked service.
2. The action triggered by `onError` (`report_failure_to_parent`) explicitly sends a custom `CHILD_FAILED` event to its parent.
3. The parent machine has a global or state-specific handler for `CHILD_FAILED` and decides what to do (e.g., restart the actor).

#### Child Actor's onError Action

```python
# Inside the child actor's logic
async def report_failure_to_parent(i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition):
    # This action is triggered by the child's own onError transition
    error_details = {"actorId": i.id, "error": str(e.data)}

    # Use the .parent reference to communicate upwards
    await i.parent.send("CHILD_FAILED", **error_details)
```

#### Parent Machine's Handler

```json
// In the parent's state machine definition
"running_children": {
  "entry": "spawn_child_actor",
  "on": {
    "CHILD_FAILED": {
      "actions": [
        "log_child_error",
        "spawn_child_actor"
      ],
      // The restart strategy
      "target": ".running_children"
      // Re-enter the state to apply the strategy
    }
  }
}
```

**Debugging Actors**

The built-in `LoggingInspector` automatically prefixes logs with the unique `actorId` of the interpreter, making it easy to trace concurrent operations.

`parent_interpreter.get_snapshot()` recursively includes the snapshots of all its child actors, giving you a complete picture of the entire system state.

You can test a child actor in complete isolation by creating an interpreter for it directly in your test suite, simulating parent messages by calling `.send()`.



---

## 🏗️ Architectural Patterns — Extended

### Automatic Logic Discovery — Under the Hood

When you use `logic_modules` or `logic_providers`, the `LogicLoader` performs these steps:

- **Introspect:** Scans provided modules/objects for all public callables (functions or methods).
- **Normalize:** Creates a lookup map with both original and camelCase names for each callable.
- **Validate:** Checks that each action/guard/service name in the JSON config exists in the lookup map, otherwise raises `ImplementationMissingError`.
- **Bind:** Constructs the final `MachineLogic` object for the interpreter to use.

The collision rule is simple: the last provider wins. If you have `logic_providers=[ProviderA(), ProviderB()]` and both have a `do_task` method, `ProviderB`'s method will be used.

### Hybrid Execution: The Best of Both Worlds

What if your application is mostly asynchronous, but you need to run a quick, blocking, deterministic check and get an immediate result? This library uniquely supports this hybrid model. An async parent machine can programmatically create, run, and get the result from a sync child machine within a single, atomic action.

#### Step 1: The Asynchronous Parent

```json
// examples/hybrid/manufacturing_line/manufacturing_line_async.json
{
  "context": {
    "partId": null,
    "qcResult": null
  },
  "id": "assemblyLine",
  "initial": "acceptingParts",
  "states": {
    "acceptingParts": {
      "on": {
        "PART_RECEIVED": {
          "actions": "assign_part_id",
          "target": "assembly"
        }
      }
    },
    "assembly": {
      "invoke": {
        "src": "assemble_part",
        "onDone": "qualityControl",
        "onError": "failed"
      }
    },
    "qualityControl": {
      "entry": "run_quality_check",
      "on": {
        "QC_PASSED": "packaging",
        "QC_FAILED": "failed"
      }
    },
    "packaging": {
      "invoke": {
        "src": "package_part",
        "onDone": "complete",
        "onError": "failed"
      }
    },
    "complete": {
      "type": "final"
    },
    "failed": {
      "type": "final"
    }
  }
}
```

#### Step 2: The Synchronous Child

```json
// examples/hybrid/manufacturing_line/quality_check_sync.json
{
  "context": {
    "inspectionCount": 0,
    "isPassed": false
  },
  "id": "qualityCheck",
  "initial": "inspecting",
  "states": {
    "inspecting": {
      "entry": "run_inspection",
      "on": {
        "": [
          {
            "guard": "did_pass",
            "target": "passed"
          },
          {
            "target": "failed"
          }
        ]
      }
    },
    "passed": {
      "entry": "set_passed"
    },
    "failed": {}
  }
}
```

#### Step 3: The Orchestration Logic

```python
# examples/hybrid/manufacturing_line/hybrid_manufacturing.py
# ... (imports and other logic functions) ...

# 🚀 Hybrid Orchestration Action
def run_quality_check_action(
    interpreter: Interpreter,  # This is the PARENT async interpreter
    context: Dict,
    event: Event,
    action_def: ActionDefinition,
) -> None:
    """
    An action on the ASYNC machine that creates and runs the SYNC QC machine.
    """
    logging.info("----------")
    logging.info("🔍 Entering Quality Control. Running synchronous QC check...")

    # 1. Load the synchronous machine's config.
    with open("quality_check_sync.json", "r") as f:
        qc_config = json.load(f)

    # 2. Define the logic for the synchronous machine.
    qc_logic = MachineLogic(
        actions={
            "run_inspection": run_inspection_action,
            "set_passed": set_passed_action,
        },
        guards={"did_pass": did_pass_guard},
    )

    # 3. Create and run the SYNC interpreter. The .start() method
    #    is blocking and runs the entire machine to its final state.
    qc_machine = create_machine(qc_config, logic=qc_logic)
    qc_interpreter = SyncInterpreter(qc_machine).start()

    # 4. Now that the sync machine has finished, inspect its final state.
    if "qualityCheck.passed" in qc_interpreter.current_state_ids:
        context["qcResult"] = "PASSED"
        asyncio.create_task(interpreter.send("QC_PASSED"))
    else:
        context["qcResult"] = "FAILED"
        asyncio.create_task(interpreter.send("QC_FAILED"))

    logging.info(f"🏁 Synchronous QC check complete. Result: {context['qcResult']}")
    logging.info("----------")
```

### Global Logic Registration for Large Applications

In larger applications, you might have logic spread across many different files. Instead of importing and passing a list of modules to `create_machine` every time, you can register them once when your application starts up.

The `LogicLoader` is a **singleton**, meaning there's only one instance of it throughout your application's lifecycle. You can get this instance and register modules globally.

```python
# In your application's main entry point (e.g., main.py or __init__.py)
from xstate_statemachine import LogicLoader
import my_app.user_logic
import my_app.payment_logic

# 1. Get the single global instance of the LogicLoader
loader = LogicLoader.get_instance()

# 2. Register all your logic modules once during startup
loader.register_logic_module(my_app.user_logic)
loader.register_logic_module(my_app.payment_logic)

# --- Later, in a different part of your application ---

# 3. Now, create_machine will automatically find the registered logic
#    without needing the logic_modules argument.
from xstate_statemachine import create_machine

machine_one = create_machine(user_config)
machine_two = create_machine(payment_config)
```

### Choosing Your Logic Style

Your library supports two primary ways of organizing your logic: **functional** (standalone functions in modules) and **class-based** (methods on a class instance). Both work with either explicit binding or auto-discovery. Here’s how to choose:

| Logic Style | Best For | Pros | Cons |
| :--- | :--- | :--- | :--- |
| **Functional** | Simpler machines, stateless logic, or promoting a pure-function style. | - Easy to test individual functions. <br> - Encourages stateless, predictable logic. | - Can become disorganized if many unrelated functions are in one file. <br> - Sharing state requires passing it through the `context`. |
| **Class-Based** | Complex machines with related logic, or when logic needs its own internal state. | - Excellent organization; groups related logic together (`FileUploaderLogic`). <br> - Can manage its own state via `self` in addition to the machine's `context`. | - Slightly more boilerplate (class definition, `__init__`). <br> - Can be overkill for very simple machines. |

---

## 🔁 Sync vs Async — Under the Hood<a name="synchronous-vs-asynchronous-execution"></a>

| Concern | `Interpreter` (asyncio) | `SyncInterpreter` (blocking) |
|---------|-------------------------|------------------------------|
| Queue | `asyncio.Queue` | `collections.deque` |
| Tick | Background task | While‑loop |
| Concurrency | Cooperative | Serial |
| Thread‑safe | `call_soon_threadsafe` needed | Yes (GIL) |
| I/O | Non‑blocking | Blocks |
| CPU | Slight overhead | Faster per event |

**Rule of Thumb:**
*Desktop / CLI* → **SyncInterpreter**
*Web / IoT / pipelines* → **Interpreter**



#### 🚫 Features *not* Supported by `SyncInterpreter`

While the synchronous engine is perfect for CLI tools and deterministic tests,
it enforces **three hard constraints** to guarantee blocking, side‑effect‑free
behaviour. Any violation raises `NotSupportedError` instantly:

| Attempted Feature | Exception Raised | Guarding Method | 📄 Source |
|-------------------|------------------|-----------------|-----------|
| **`after` timers** – declarative delays | `NotSupportedError` | `SyncInterpreter._after_timer` | [`sync_interpreter.py`](src/xstate_statemachine/sync_interpreter.py) |
| **`spawn_*` actions** – child actor creation | `NotSupportedError` | `SyncInterpreter._spawn_actor` | same |
| **Async callables** in actions **or** services (coroutines / `async def`) | `NotSupportedError` | `SyncInterpreter._execute_actions` & `SyncInterpreter._invoke_service` | same |

> 🧘 **Why so strict?**
> The sync interpreter must finish **everything** before returning control to
> the caller. Timers, background actors, or coroutine functions would break
> that guarantee and lead to hidden concurrency. The hard error surfaces the
> issue early, nudging you towards either the full `Interpreter` or a
> refactoring to synchronous logic.

### Migrating Sync→Async

1. Swap interpreter class.
2. Make `main()` async, `await` `.start()` / `.send()` / `.stop()`.
3. Replace blocking sleeps with `await asyncio.sleep()`.

### Threads & Processes

* Use `loop.call_soon_threadsafe()` for cross‑thread `.send()`.
* For cross‑process, bridge with a message queue and `.send()` inside process.

---

## 🐞 Debugging & Visualization (Preview)<a name="debugging--visualization"></a>

This section dives into:

1.  **LoggingInspector** patterns (verbosity, custom format).
2.  **Writing plugins** with detailed lifecycle hooks.
3.  **Snapshots** for crash‑recovery & golden tests.
4.  **Auto‑diagrams** (Mermaid & PlantUML).
5.  **REPL live‑tinkering** with `await interp.send(...)`.

---

## 🐞 Debugging & Visualization<a name="debugging--visualization"></a>

When something goes sideways at 2 AM you need **clarity, not guess-work**.
XState-StateMachine ships with an **instrumentation layer** that lets you inspect, log, snapshot and _draw_ every heartbeat of your machine.

### 🪵 Built‑in Logging Infrastructure<a name="logging-infra"></a>

Out‑of‑the‑box the package exposes a **library‑safe logger** named
`"xstate_statemachine"` with a **`NullHandler`** already attached
(`xstate_statemachine/logger.py`).
That means **no more “No handler found” spam** in consumer apps.
Simply configure logging once in your entry point and every module—plus all
plugins—will follow suit:

```python
import logging

# Your application bootstrap 🔧
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)

# From here on the library logs seamlessly
from xstate_statemachine import create_machine, Interpreter
from xstate_statemachine.logger import logger  # Convenience re‑export 🪵

logger.info("✅ Logging initialised!")
```

| What | Where | Why |
|------|-------|-----|
| **Package logger** | `logging.getLogger("xstate_statemachine")` | Hierarchical—sub‑modules inherit handlers & level. |
| **`NullHandler` pre‑installed** | Added in the library to be polite | Prevents accidental stderr noise in apps that forget `basicConfig()`. |
| **Helper `logger` constant** | `from xstate_statemachine.logger import logger` | Quick access for *your* actions / guards without calling `getLogger()` each time. |

> 💡 **Tip:**  Add multiple handlers (file, JSON, OTEL, …) in your own
> `basicConfig` or custom setup—the library will respect them automatically.

### 1. LoggingInspector Plugin 🕵️‍♀️

```python
import logging
from xstate_statemachine import Interpreter, LoggingInspector

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")

machine  = create_machine(cfg)
service  = Interpreter(machine).use(LoggingInspector())   # 🔑 register _before_ .start()
await service.start()
```

<details>
<summary>Sample output (collapsed)</summary>

```
2025-07-10 16:02:15 | 🕵️ STATE  idle  ➡  loading  (on FETCH)
2025-07-10 16:02:15 | ⚙️  Action: setSpinner(True)
2025-07-10 16:02:15 | ☁️  Invoke: fetchData()
2025-07-10 16:02:16 | ✅ done.invoke.fetchData  — 200 OK
2025-07-10 16:02:16 | 🕵️ STATE  loading  ➡  success  (on done.invoke.fetchData)
2025-07-10 16:02:16 | ⚙️  Action: cacheData
```
</details>

#### 🔧 Customising the log stream

```python
class ShortLog(LoggingInspector):
    """Print a single‑line summary for every *external* transition."""

    def on_transition(self, interpreter, from_states, to_states, transition):
        old = ",".join(s.id for s in from_states)
        new = ",".join(s.id for s in to_states)
        print(f"[{transition.event}] {old} → {new}")
```

Attach multiple inspectors—analytics, tracing, etc.—each focusing on a single concern.

---

### 2. Writing Your Own Plugin 🔌

All plugins inherit from **`PluginBase`** and can tap into the interpreter’s lifecycle.
Below are the **stable hooks available today** (everything else is  considered experimental or on the roadmap).

##### 🧩 Plugin Hook Matrix — *copy‑paste ready* 📝

| 🔗 Hook | Python Signature | 📅 When it Fires | 💡 Typical Use |
|---------|-----------------|------------------|----------------|
| 🏁 **`on_interpreter_start`** | `on_interpreter_start(self, interpreter)` | Right after `interpreter.start()` begins | Initialise DB connections, timers, metrics |
| 🛑 **`on_interpreter_stop`** | `on_interpreter_stop(self, interpreter)` | As soon as `interpreter.stop()` is invoked | Flush buffers, close sockets |
| ✉️ **`on_event_received`** | `on_event_received(self, interpreter, event)` | Every time an event is dequeued for processing | Audit trails, event‑level analytics |
| 🔀 **`on_transition`** | `on_transition(self, interpreter, from_states, to_states, transition)` | After states are exited → actions run → new states entered | Tracing, Prometheus counters, BI pipelines |
| ⚙️ **`on_action_execute`** | `on_action_execute(self, interpreter, action)` | Immediately before an individual action implementation runs | Profiling, APM spans, debugging prints |
| 🛡️ **`on_guard_evaluated`** | `on_guard_evaluated(self, interpreter, guard_name, event, result)` | After a guard function's condition is evaluated | Debugging guard logic, conditional analytics |
| 📞 **`on_service_start`** | `on_service_start(self, interpreter, invocation)` | Just before an invoked service begins execution | Logging service calls, tracing external interactions |
| ✅ **`on_service_done`** | `on_service_done(self, interpreter, invocation, result)` | When an invoked service returns successfully | Logging successful outcomes, result processing |
| 💥 **`on_service_error`** | `on_service_error(self, interpreter, invocation, error)` | When an invoked service raises an exception | Error reporting, failure handling, alerting |

> 🛠️ **Tip:** Implement only the hooks you need; methods left un‑overridden
> incur **zero** overhead thanks to Python’s dynamic dispatch. 🚀

```python
from xstate_statemachine import PluginBase

class PromMetrics(PluginBase):
    """Increment a Prometheus counter on every state change."""

    def __init__(self, counter):
        self.counter = counter

    def on_transition(self, interpreter, from_states, to_states, transition):
        # Label by triggering event for easy dashboard filters
        self.counter.labels(event=transition.event).inc()
```

Just `.use(PromMetrics(prom_counter))` on an interpreter instance and you’re collecting metrics! 📈

---

### 3. Snapshots 🧩

Persist the _exact_ runtime status—active states **and** mutable context—to disk or Redis.

```python
snap = interpreter.get_snapshot()    # JSON str
# Later — even after deploy
restored = await Interpreter.from_snapshot(snap, machine).start()
```

#### 🔄 Restoring from a Snapshot — Mind the *MachineNode* 📂

A snapshot captures **only** *dynamic* runtime data:

1. `status` (`running` / `stopped`)
2. `context` dict
3. *IDs* of active states

It does **not** store the *static* state‑chart structure itself.
Therefore **`Interpreter.from_snapshot()` needs the original `MachineNode`**—
the same object returned by `create_machine(...)`—to rebuild the interpreter.

```python
# ✅ Happy Path
machine  = create_machine(cfg, logic_modules=[app_logic])

service   = await Interpreter(machine).start()
snap      = service.get_snapshot()     # JSON string
await service.stop()

# later / after restart
restored  = await Interpreter.from_snapshot(snap, machine).start()
```

```python
# 😬 Wrong – passing raw JSON
cfg = json.load(open("chart.json"))
snap = ...                       # previously saved

# Re‑creating a *different* MachineNode (new object)
machine2 = create_machine(cfg)   # ⚠️ distinct in memory

await Interpreter.from_snapshot(snap, machine2)  # ❌ Raises StateNotFoundError
```

> 🧩 **Tip:**  Keep the original `MachineNode` in a module‑level variable, or
> persistently cache it, so restoration is trivial.
> Creating a *byte‑for‑byte* identical `MachineNode` works too, but re‑running
> `create_machine()` must use the **exact same JSON + logic** to avoid ID drift.

Use-cases:

* **Resilient workers**—crash-safe resume after process restarts
* **Time-travel debugging**—save before risky ops, restore in REPL
* **CI golden tests**—diff snapshots to detect un-intended behavioural drift

---

### 4. Auto-Generating Diagrams 🖼️

Keep docs evergreen by baking diagram generation into CI.

```python
mermaid = machine.to_mermaid()
with open("docs/statechart.mmd", "w") as f:
    f.write("```mermaid\n" + mermaid + "\n```")
```

Or, for architects living in PlantUML:

```python
plantuml = machine.to_plantuml()
Path("docs/diagram.puml").write_text(plantuml)
```

Integrate with **mkdocs-material**, GitHub Pages, Confluence—anything that renders Mermaid/PUML—your diagrams will **always** mirror the code running in prod.

### 5. REPL Live‑Tinkering 💻

> **Why bother?**
> • Instant feedback when wiring new actions or guards
> • Zero‑compile “what happens if…?” exploration
> • Perfect for smoke‑testing machines that talk to live APIs or devices

#### 5.1  Pick a REPL with top‑level `await`

| REPL | Setup | Remarks |
|------|-------|---------|
| **IPython ≥ 8.0** | `pip install ipython`<br>`ipython --autoawait asyncio` | Rich tracebacks & tab‑completion |
| **ptpython** | `pip install ptpython` | Built‑in asyncio, syntax highlighting |
| **Vanilla Python 3.12+** | `python -m asyncio` | Stock interpreter now supports top‑level `await` 🎉 |

#### 5.2  Bootstrap an interpreter session

```python
# light_repl.py
import json, asyncio
from xstate_statemachine import create_machine, Interpreter, LoggingInspector
import light_switch_logic  # ← your actions

cfg     = json.load(open("light_switch.json"))
machine = create_machine(cfg, logic_modules=[light_switch_logic])

# Create the async interpreter but DON'T start the event loop yet
service = Interpreter(machine).use(LoggingInspector())
```

Launch IPython with the pre‑wired objects:

```bash
ipython --autoawait asyncio -i light_repl.py
```

### 5.3  Play!

```pycon
In [1]: await service.start()
🕵️ STATE off

In [2]: await service.send("TOGGLE")
🕵️ STATE off ➡ on   (on TOGGLE)

In [3]: service.current_state_ids
Out[3]: {'lightSwitch.on'}

In [4]: service.context
Out[4]: {'flips': 1}
```

*Tip — alias event sending to shorten typing:*

```pycon
In [5]: %alias send await service.send
In [6]: send TOGGLE
```


#### 5.4  Hot‑reload without leaving the REPL

```pycon
In [7]: %load_ext autoreload
In [8]: %autoreload 2   # picks up edits in light_switch_logic.py

# tweak your action, hit save, then...
In [9]: send TOGGLE     # new code runs immediately
```

#### 5.5  Snapshot & rewind on the fly

```pycon
In [10]: snap = service.get_snapshot()

# …experiment wildly…
In [11]: await service.send("GLITCH_EVENT")

# Restore pristine state
In [12]: from xstate_statemachine import Interpreter
In [13]: service = await Interpreter.from_snapshot(snap, machine).start()
```

#### 5.6  Deep‑dive tricks

| Trick | Command |
|-------|---------|
| Inspect queued events | `service._event_queue.qsize()` |
| Peek next transition | `machine.get_next_state("lightSwitch.on", {"type": "TOGGLE"})` |
| Pause timers in tests | `await service.stop(); asyncio.get_running_loop().set_debug(False)` |
| Spawn a child REPL for actors | `child = next(iter(service._actors.values())); await child.send(...)` |

🚀 **You now have an always‑on laboratory for your state machines—no rebuilds, no deployment cycles, just pure interactive discovery. Happy tinkering!**


---

## 📑 API Reference<a name="api-reference"></a>

Below is the complete, in-depth guide to the library's public API. This section details every key class, function, and exception, with explanations and usage examples to help you master the library.

---

### 1. The Factory: `create_machine`

This is the primary, user-facing entry point for creating a state machine instance. Its job is to take your declarative JSON `config` and your Python business `logic` and weave them together into a single, executable `MachineNode` object.

**Signature:**
```python
create_machine(
    config: Dict[str, Any],
    *,
    logic: Optional[MachineLogic] = None,
    logic_modules: Optional[List[Union[str, ModuleType]]] = None,
    logic_providers: Optional[List[Any]] = None
) -> MachineNode
```

**Parameters In-Depth**
- **config: `Dict[str, Any]` | Required**
  The Python dictionary parsed from your state machine's JSON definition. Example:
  ```python
  import json

  with open("my_machine.json") as f:
      machine_config = json.load(f)

  machine = create_machine(machine_config, ...)
  ```
- **logic: `Optional[MachineLogic]` | Explicit Binding**
  Explicitly map every action, guard, and service name to Python functions:
  ```python
  from my_logic_file import my_action_func, my_guard_func

  explicit_logic = MachineLogic(
      actions={"doSomething": my_action_func},
      guards={"canDoSomething": my_guard_func}
  )

  machine = create_machine(config, logic=explicit_logic)
  ```
- **logic_modules: `Optional[List[Union[str, ModuleType]]]` | Functional Auto-Discovery**
  Auto-discover standalone functions in modules:
  ```python
  import my_app.logic.user_actions

  machine = create_machine(config, logic_modules=[my_app.logic.user_actions])
  ```
- **logic_providers: `Optional[List[Any]]` | Class-Based Auto-Discovery**
  Auto-discover methods in class instances:
  ```python
  from my_logic_file import BusinessLogicHandler

  logic_handler = BusinessLogicHandler()
  machine = create_machine(config, logic_providers=[logic_handler])
  ```

---

### 2. The Interpreters: `Interpreter` & `SyncInterpreter`

These are the engines that run your machine. They take a `MachineNode` (created by `create_machine`), manage its state, process events, and execute logic.

#### Properties

| Property             | Type       | Description                                                                                   |
|----------------------|------------|-----------------------------------------------------------------------------------------------|
| `.current_state_ids` | `Set[str]` | All currently active state IDs. Useful for parallel states.                                   |
| `.context`           | `Dict`     | The live, mutable context (memory) of the running machine instance.                           |
| `.status`            | `str`      | Lifecycle status: `"uninitialized"`, `"running"`, or `"stopped"`.                              |

#### Methods

| Method | Returns | Description |
|---|---|---|
| `.start()` | `self` | Starts the interpreter, enters the initial state, and runs entry actions. **Must be `await`ed for `Interpreter`**. |
| `.stop()` | `None` | Stops the interpreter. For `Interpreter`, it cancels all running tasks. **Must be `await`ed for `Interpreter`**. |
| `.send(event, **payload)` | `None` | Sends an event to the machine. For `Interpreter`, this is an `async` operation. |
| `.use(plugin)` | `self` | Registers a plugin. Must be called before `.start()`. |
| `.get_snapshot()` | `str` | Returns a JSON string of the current status, context, and active `state_ids`. |
| `.from_snapshot(snap, machine)` | `Interpreter` | *(Class Method)* Restores an interpreter from a saved snapshot. |

##### Usage Examples

```python
# Async Interpreter Start
interpreter = await Interpreter(machine).start()

# SyncInterpreter Start
interpreter = SyncInterpreter(machine).start()

# Stop Interpreter
await interpreter.stop()

# Send events
await interpreter.send("UPDATE_USER", name="Alice", id=123)
await interpreter.send({"type": "SUBMIT"})

# Use plugins
interpreter.use(LoggingInspector()).use(MyCustomPlugin())

# Snapshot and restore
saved_state = interpreter.get_snapshot()
restored_interp = Interpreter.from_snapshot(saved_state, machine)
```

---

### 3. Core Logic & Model Classes


### 🔍 Handy `MachineNode` Helper Methods

When writing **white‑box tests**, REPL experiments, or CLI tools you often need
to poke the state tree *without* spinning up a full interpreter.
Two small but mighty helpers live right on the `MachineNode`:

| Method | Returns | What it does                                                                                                                                | Typical Use‑Case |
|--------|---------|---------------------------------------------------------------------------------------------------------------------------------------------|------------------|
| `machine.get_state_by_id(state_id)` | `StateNode \| None` | Deep‑searches the tree for an exact, fully‑qualified state ID.                                                                              | Assert a specific node exists, fetch its metadata in tests |
| `machine.get_next_state(from_state_id, event)` | `Set[str] \| None` | **Pure** function that calculates *where the machine would go* from a given leaf state if `event` were sent.  **Note: Guards are ignored**. | Fast unit tests for transition maps, generating coverage matrices |

```python
from xstate_statemachine import create_machine, Event

# Assume light_config is loaded from your JSON
light_config = {
    "id": "light",
    "initial": "green",
    "states": {
        "green": {"on": {"TIMER": "yellow"}},
        "yellow": {}
    }
}

# 1. Get the MachineNode instance
machine = create_machine(light_config)

# 2. Look up a specific node object
green_node = machine.get_state_by_id("light.green")
print(f"Found node: {green_node.id}")

# 3. Predict the outcome of an event without an interpreter
next_states = machine.get_next_state("light.green", Event(type="TIMER"))
assert next_states == {"light.yellow"}
print(f"From 'green', a 'TIMER' event would transition to: {next_states}")
```

> 💡 **Tip:** Because `get_next_state` is side‑effect‑free, you can call it in
> tight loops to generate *all* reachable paths for property‑based testing.
> Pair it with Hypothesis or `pytest‑cases` for powerful graph validation! 🧪✨

| Class             | Description                                                                                                  |
|-------------------|--------------------------------------------------------------------------------------------------------------|
| `MachineNode`    | The parsed, in-memory representation of your entire state machine graph. Returned by `create_machine`, it's the central object passed to interpreters and used for static analysis                                               |
| `MachineLogic`    | Container for explicit action, guard, and service bindings.                                                  |
| `Event`           | `NamedTuple(type, payload)` for events sent to the machine.                                                  |
| `ActionDefinition`| Represents a configured action from JSON, including `.params` for static data.                               |

---

### 4. Extensibility & Debugging

| Class             | Description                                                                                                                |
|-------------------|----------------------------------------------------------------------------------------------------------------------------|
| `PluginBase`      | Abstract base for custom plugins (override `on_*` methods).                                                               |
| `LoggingInspector`| Built-in plugin for detailed console output of state transitions, actions, and events.                                     |

---

### 5. Exception Hierarchy

All custom exceptions inherit from `XStateMachineError`.

```
XStateMachineError
 ├── InvalidConfigError
 ├── StateNotFoundError
 ├── ImplementationMissingError
 ├── ActorSpawningError
 └── NotSupportedError
```

- **InvalidConfigError**: Invalid machine JSON (e.g., missing `id` or `states`).
- **StateNotFoundError**: Transition target ID not found in the machine.
- **ImplementationMissingError**: Missing action, guard, or service implementation.
- **ActorSpawningError**: Error spawning a child actor/service.
- **NotSupportedError**: Using async features with `SyncInterpreter`.

Use them in `pytest.raises()` to assert mis-configurations early.

---


## 🧬 Advanced Concepts<a name="advanced-concepts"></a>

### 1. Supervision Trees 🌲 (Actor Failure Handling)

* Children may _crash_ (uncaught exception in action/service).
* Parent decides policy:
  * **`onError` transition** → recover / restart actor.
  * **Escalate** — re-raise and crash upstream (default).
  * **Silent** — ignore by having no handler (_not recommended_).

### 2. Dynamic Spawn (PoC Micro-services)

Spawn machinery from **runtime data**:

```python
async def spawn_tenant_actor(i, ctx, e, a):
    tenant_id = e.payload["id"]
    cfg = await fetch_tenant_machine(tenant_id)
    logic = await load_tenant_logic(tenant_id)
    return create_machine(cfg, logic=logic)
```

### 3. Hot Reload in Development ♻️

* Detect file change via `watchdog`.
* `.stop()` the old interpreter.
* Re-`create_machine()` with new JSON.
* `.start(snapshot)` to keep context.

Enjoy **live editing** of statecharts without losing session data.

### 4. Performance Tuning

| Technique | When to use | Effect |
|-----------|-------------|--------|
| **Disable event‑loop debug mode** `asyncio.get_running_loop().set_debug(False)` | After you’ve ironed out the bugs and want maximum throughput in production | Removes costly asyncio debug assertions (≈ 5‑10 % speed‑up in micro‑benchmarks) |
| **Prefer `SyncInterpreter`** when you don’t need `after` timers or `invoke` | CLI tools, deterministic unit tests, CPU‑bound pipelines | Zero coroutine overhead, ~40 % faster per event in tight loops |
| **Bulk‑fire events API** *(planned)* | High‑volume telemetry or log ingestion | Will let you enqueue a list of events in one syscall, minimising context‑switches |


### 5. Architectural Pattern: `invoke` vs. `async` Actions

Your library offers two powerful ways to handle asynchronous operations, and choosing the right one is key to clean architecture.

#### Use `invoke` for True Asynchronous "States"

`invoke` is best when the machine enters a state that is *defined* by the running of an async task. Think of a `loading` state—its entire purpose is to wait for a service to complete.

- **Declarative:** Success (`onDone`) and failure (`onError`) are part of the state's definition, making the flow extremely clear from the diagram.
- **Automatic Cleanup:** If the machine transitions away from the "invoking" state, the library automatically cancels the running service task for you. This prevents orphaned tasks and race conditions.
- **Use Case:** API calls, database queries, or any task where you have distinct `success` and `failure` outcomes that lead to different states.

**The `api_fetcher` example is a perfect illustration of this pattern.**
```json
"loading": {
  "invoke": {
    "src": "fetch_user_from_api",
    "onDone": {
      "target": "success",
      "actions": "set_user_data"
    },
    "onError": {
      "target": "failure",
      "actions": "set_error_message"
    }
  }
}
```

#### Use async Actions for "Fire and Forget" Logic

Sometimes, an async task is just a side effect, not the entire purpose of the state. It might have multiple, complex outcomes beyond simple success/failure, or it might not need to be cancelled if the state changes.

- **Imperative Control:** An async action gives you full control. It can send multiple different events back to the machine at different times to signal various outcomes.
- **No Automatic Cleanup:** The library will not automatically cancel an async action if the state changes. This can be useful for tasks that should complete regardless (like logging), but requires manual management for tasks that shouldn't.
- **Use Case:** Tasks that trigger other complex workflows, operations with more than two outcomes, or side effects that don't define the current state.

The `data_fetcher` example demonstrates this pattern beautifully. The `fetch_data_action` is just a task that runs when the fetching state is entered. It is responsible for sending `FETCH_SUCCESS` or `FETCH_FAILURE` back to its own interpreter to drive the next state transition.

```python
# From data_fetcher_logic.py
async def fetch_data_action(
    self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
):
    # ... logic to fetch data ...
    if successful:
        # Manually send the success event
        await i.send("FETCH_SUCCESS")
    else:
        # Manually send the failure event
        await i.send("FETCH_FAILURE")
```

#### When to Use...

| Aspect | Use `invoke` | Use an `async` Action |
| :--- | :--- | :--- |
| **Clarity** | When the flow is a clear `success`/`failure` branch. | When you have multiple, custom outcomes. |
| **Cancellation** | When the task **must** be cancelled on state exit. | When the task can run to completion regardless. |
| **Simplicity** | For most common async needs (API calls, etc.). | For more complex, imperative orchestrations. |
| **Data Flow**| Result is automatically passed to `onDone`/`onError` via `event.data`. | You must manually construct and `.send()` events with payloads. |
| **Best Fit** | A `loading` state whose entire purpose is the async call. | A "fire-and-forget" side effect within a broader state. |

By understanding this distinction, you can model your asynchronous logic with even greater precision and clarity.

---

## 🌟 Best Practices<a name="best-practices"></a>

| ✅ Do | 🚫 Avoid | Why |
|------|----------|-----|
| **Keep state graphs small & composable** | Monolithic 500-node monsters | Easier mental model; actors > beasts |
| **Store _quantitative_ data in `context`** | Encoding counts/arrays in state IDs | Context is for numbers & strings; IDs are for **qualitative** phases |
| **Use guards for business rules** | Packing `if` logic inside actions | Guards are _deterministic_; actions are _side-effects_ |
| **Prefer `after` timers** | `asyncio.create_task(sleep())` inside actions | Declarative ≠ spaghetti |
| **Model failures explicitly** (`error`, `timeout`) | Relying on `try/except` deep inside services | Errors become testable & visible in diagrams |
| **Name events imperatively** (`FETCH_USER`) | Vague names (`DO_IT`, `NEXT`) | Better logs, clearer arrows |
| **Unit-test machines head-less** | UI-driven tests only | Faster CI; assert pure behaviour |
| **Snapshot critical flows in CI** | Trusting human QA memory | Catch regressions at graph-level |
| **Document with Mermaid auto-build** | Manually exported PNGs | Zero-drift diagrams |

### Naming Conventions

* **Events**: `SCREAMING_SNAKE_CASE`
* **States**: `camelCase` preferred (`loadingData`)
* **Action / Guard / Service names**:
  * Python `snake_case` ↔ JSON `camelCase` (auto-mapped)
  * Prefix actors with a verb: `spawnPaymentActor`

### File Layout (Suggestion)

```
myapp/
 ├─ statecharts/
 │   ├─ user_signup.json
 │   └─ payments/
 │       ├─ payment_flow.json
 │       └─ refund_actor.json
 ├─ logic/
 │   ├─ signup_logic.py
 │   └─ payments/
 │       └─ payment_logic.py
 └─ runners/
     └─ simulate_signup.py
```

### Testing Tips 🧪

```python
import pytest, json
from xstate_statemachine import create_machine, SyncInterpreter

@pytest.fixture
def signup_machine():
    cfg = json.load(open("statecharts/user_signup.json"))
    m   = create_machine(cfg, logic_modules=[signup_logic])
    return SyncInterpreter(m).start()

def test_happy_path(signup_machine):
    signup_machine.send("START")
    signup_machine.send("VALID_EMAIL")
    assert "signup.success" in signup_machine.current_state_ids
```

* Use **`SyncInterpreter`** even for async machines in unit tests – by stubbing async services as sync fakes.
* Compare **snapshots** instead of deep context asserts if the shape is large.

#### Unit-Testing Transitions with `get_next_state()`
For more granular testing, the `MachineNode` object includes a powerful utility, `.get_next_state(from_state_id, event)`, for validating your machine's flow without running a full interpreter. It's a pure function that calculates the result of a transition without executing any actions or guards, making it perfect for fast unit tests.

```python
from xstate_statemachine import Event

def test_timer_transition(light_machine):
    # light_machine is the MachineNode instance created by create_machine()
    event = Event("TIMER")

    # Calculate the expected next state without running actions
    next_states = light_machine.get_next_state("light.green", event)

    assert next_states == {"light.yellow"}
```

## 🎨 Style Guide (for actions/guards/services)

1. **Always type-hint** every arg & return.
2. **Actions** mutate `ctx` **only**; never sleep.
3. **Guards** are pure, side-effect-free, < 20 LOC.
4. **Services** should raise domain errors, not swallow them.
5. **Log** at source:

```python
   logger = logging.getLogger("machine.payments")
   logger.info("Charging card %s...", ctx["card_id"])
```
6. Use **emoji** prefixes in logs for quick grep (consistent across repo).

---

## ❓ FAQ<a name="faq"></a>

| Question | Answer |
|----------|--------|
| **Is this library production ready?** | Yes. It powers real-time IoT gateways handling 50k msgs/min and multiple SaaS dashboards. |
| **Can I edit the JSON at runtime?** | Absolutely. Re-`create_machine()` + `.start(snapshot)` to hot-swap. |
| **Does it support PyPy?** | ✅ PyPy 3.10 passes the full test-suite. |
| **How is it different from `transitions`?** | XState-StateMachine implements full **statecharts** (hierarchy, parallelism, invoke, actors) and consumes **XState JSON**, not imperative decorators. |
| **Can I use Pydantic in context?** | Yep—store a model instance; just remember context is shallow-copied on interpreter start. |
| **Where is the GUI inspector?** | On the roadmap. Use Stately web simulator + `LoggingInspector` meanwhile. |
| **Is there a code-gen for Python from Stately?** | Not needed—export JSON → run. Zero translation. |

---

## 🤝 Contributing<a name="contributing"></a>

Contributions are welcome and greatly appreciated! This project thrives on community involvement, and we're excited to see what you'll bring.

We follow a standard "Fork & Pull Request" workflow. Before submitting, please ensure your changes are well-tested, formatted correctly, and documented in the changelog.

For a full, step-by-step guide on how to:
-   Set up your development environment
-   Run tests and linting checks
-   Submit your changes

Please see our **[Contributing Guide](CONTRIBUTING.md)**.
---

## 📜 License<a name="license"></a>

MIT. In short:

```text
Copyright (c) 2025 Basil T T

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the “Software”), to deal
in the Software without restriction…
```

See **LICENSE** file for the full legalese.

---

<div align="center">

🎉 **Congratulations!**
You’ve reached the end of the XState-StateMachine saga.
Go forth and build **bug-proof**, **self-documenting** workflows! 🚀

</div>
