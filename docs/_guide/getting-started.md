---
title: Getting Started
description: Install XState-StateMachine, verify your setup, build your first machine, and understand the full feature set.
---

## Installation

Install from PyPI with pip:

```bash
pip install xstate-statemachine
```

Or with [uv](https://docs.astral.sh/uv/) for faster installs:

```bash
uv pip install xstate-statemachine
```

Or with [Poetry](https://python-poetry.org/):

```bash
poetry add xstate-statemachine
```

## Verify Your Installation

```bash
python -c "import xstate_statemachine; print(xstate_statemachine.__version__)"
# Output: 0.5.0
```

You can also verify the CLI tool is available:

```bash
xsm --help
```

Expected output:

```
usage: xsm [-h] [-v]
           {generate-template,gt,list-templates,lt,validate,val,info} ...

XState-StateMachine CLI — Generate Python code from XState JSON.

positional arguments:
  {generate-template,gt,list-templates,lt,validate,val,info}
                        Available commands
    generate-template (gt)
                        Generate Python code from an XState JSON file.
    list-templates (lt)
                        List all available code generation templates.
    validate (val)      Validate an XState JSON config file.
    info                Show library version, Python version, and feature
                        summary.

options:
  -h, --help            show this help message and exit
  -v, --version         Show program's version number and exit.
```

## Requirements

| Requirement | Details |
|-------------|---------|
| **Python** | 3.9 or higher (tested on 3.9, 3.10, 3.11, 3.12, 3.13) |
| **Dependencies** | None — zero external dependencies beyond the standard library |
| **OS** | Windows, macOS, Linux |

> **Tip:** The library uses only the Python standard library, so it works anywhere Python runs — containers, serverless, embedded systems, CI pipelines.

## Your First State Machine (60 seconds)

Let's build a simple toggle switch. It has two states (`off` and `on`) and toggles between them:

```
  ┌─────┐  TOGGLE  ┌────┐
  │ off │ ──────►  │ on │
  └─────┘  ◄────── └────┘
            TOGGLE
```

### Using JSON (XState-compatible):

```python
from xstate_statemachine import create_machine, SyncInterpreter

config = {
    "id": "toggle",
    "initial": "off",
    "states": {
        "off": {"on": {"TOGGLE": "on"}},
        "on":  {"on": {"TOGGLE": "off"}}
    }
}

machine = create_machine(config)
interp = SyncInterpreter(machine).start()

print(interp.active_state_ids)
# {'toggle.off'}

interp.send("TOGGLE")
print(interp.active_state_ids)
# {'toggle.on'}

interp.send("TOGGLE")
print(interp.active_state_ids)
# {'toggle.off'}

interp.stop()
```

### Using Pure Python (Pythonic API):

```python
from xstate_statemachine import State, build_machine, SyncInterpreter

off = State("off", initial=True, on={"TOGGLE": "on"})
on  = State("on",  on={"TOGGLE": "off"})

machine = build_machine(id="toggle", states=[off, on])
interp = SyncInterpreter(machine).start()

interp.send("TOGGLE")
print(interp.active_state_ids)
# {'toggle.on'}

interp.stop()
```

### Using Class-Based Style:

```python
from xstate_statemachine import State, StateMachine, SyncInterpreter

class ToggleMachine(StateMachine):
    machine_id = "toggle"

    off = State("off", initial=True, on={"TOGGLE": "on"})
    on  = State("on",  on={"TOGGLE": "off"})

machine = ToggleMachine.create_machine()
interp = SyncInterpreter(machine).start()

interp.send("TOGGLE")
print(interp.active_state_ids)
# {'toggle.on'}

interp.stop()
```

### Using Builder Style:

```python
from xstate_statemachine import MachineBuilder, SyncInterpreter

machine = (
    MachineBuilder("toggle")
    .state("off", initial=True, on={"TOGGLE": "on"})
    .state("on", on={"TOGGLE": "off"})
    .build()
)

interp = SyncInterpreter(machine).start()
interp.send("TOGGLE")
print(interp.active_state_ids)
# {'toggle.on'}

interp.stop()
```

> **All four approaches produce identical runtime behavior.** Choose the style that fits your project.

## Your Second Machine: With Actions and Context

Let's add logic — a counter that tracks how many times the switch is toggled:

```python
from xstate_statemachine import create_machine, SyncInterpreter, MachineLogic

config = {
    "id": "counter",
    "initial": "active",
    "context": {"count": 0},
    "states": {
        "active": {
            "on": {
                "INCREMENT": {"actions": "increment"},
                "DECREMENT": {"actions": "decrement"},
                "RESET": {"actions": "reset"}
            }
        }
    }
}

class CounterLogic(MachineLogic):
    def increment(self, interpreter, context, event, action_def):
        context["count"] += 1

    def decrement(self, interpreter, context, event, action_def):
        context["count"] = max(0, context["count"] - 1)

    def reset(self, interpreter, context, event, action_def):
        context["count"] = 0

machine = create_machine(config, logic=CounterLogic())
interp = SyncInterpreter(machine).start()

interp.send("INCREMENT")
interp.send("INCREMENT")
interp.send("INCREMENT")
print(interp.context["count"])
# 3

interp.send("DECREMENT")
print(interp.context["count"])
# 2

interp.send("RESET")
print(interp.context["count"])
# 0

interp.stop()
```

## What's Included

| Component | Description |
|-----------|-------------|
| **Runtime Library** | Async (`Interpreter`) + Sync (`SyncInterpreter`) engines for executing state machines |
| **Pythonic API** | Define machines in pure Python — class-based, builder, or functional style |
| **JSON Support** | Full XState JSON format compatibility for cross-platform machine definitions |
| **CLI Tool (`xsm`)** | Generate production-ready Python from XState JSON with type hints and docstrings |
| **Plugin System** | Observable hooks for logging, metrics, debugging, and custom extensions |
| **Snapshot System** | Save and restore machine state for persistence, testing, and time-travel debugging |
| **Diagram Export** | Generate Mermaid, PlantUML, or ASCII diagrams from machine definitions |

## Feature Overview

Here's what XState-StateMachine supports — every feature you'd expect from a production statechart library:

### States & Transitions
- **Simple states** — flat state machines with event-driven transitions
- **Hierarchical (nested) states** — compound parent states with child substates
- **Parallel states** — orthogonal regions running concurrently
- **Final states** — terminal states that emit `done` events
- **Self-transitions** — re-enter the same state (with timer reset)

### Logic & Data
- **Context** — mutable data attached to the machine instance
- **Guards** — conditional transitions (`guard` or `cond` key)
- **Actions** — side effects on transitions (`entry`, `exit`, `on` transition)
- **Services / Invoke** — async or sync service calls with `onDone`/`onError`
- **Delayed transitions** — timer-based auto-transitions (`after`)
- **Eventless transitions** — auto-transitions based on conditions (`always`)

### Architecture
- **Actor Model** — spawn independent child machines with `spawn_` prefix
- **Plugins** — observable hooks for logging, metrics, custom extensions
- **Snapshots** — serialize/restore machine state with `take_snapshot()` / `restore_snapshot()`
- **Dual interpreters** — `Interpreter` (async) and `SyncInterpreter` (sync)

### Developer Tools
- **CLI code generator** — 5 templates from XState JSON
- **Diagram export** — Mermaid, PlantUML, ASCII
- **LoggingInspector** plugin — built-in state transition logging
- **Zero dependencies** — pure Python standard library

## Development Installation

To contribute or work from source:

```bash
git clone https://github.com/basiltt/xstate-statemachine.git
cd xstate-statemachine
uv pip install -e . --group dev --group lint --group test
```

This installs the library in editable mode with all development, linting, and testing dependencies.

### Running the Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test module
python -m pytest tests/tests_pythonic/ -v

# Run with coverage
python -m pytest tests/ --cov=xstate_statemachine --cov-report=html
```

### Project Structure

```
xstate-statemachine/
├── src/xstate_statemachine/
│   ├── __init__.py          # Public API exports
│   ├── machine.py           # MachineNode, state tree, config parser
│   ├── interpreter.py       # Interpreter (async) + SyncInterpreter
│   ├── pythonic.py           # State, StateMachine, MachineBuilder, decorators
│   ├── snapshot.py           # Snapshot save/restore
│   ├── plugin.py             # Plugin base + LoggingInspector
│   ├── diagram_exporter.py   # Mermaid, PlantUML, ASCII export
│   └── cli/                  # CLI code generator
│       ├── __main__.py       # Entry point (xsm command)
│       ├── extractor.py      # JSON feature extraction
│       └── strategies/       # 5 code generation templates
├── tests/                    # 2,403+ tests
├── docs/                     # GitHub Pages documentation
└── pyproject.toml
```

## Upgrading from Older Versions

```bash
pip install --upgrade xstate-statemachine
```

**From v0.4.x to v0.5.0:**

- The Pythonic API (`State`, `build_machine`, `StateMachine`, `MachineBuilder`) is new in v0.5.0. Existing JSON-based code continues to work unchanged.
- The `--style` CLI flag is deprecated in favor of `--template`. Both still work, but `--style` will be removed in a future release.
- All existing `create_machine()` and `MachineLogic` patterns remain fully supported.

**From v0.3.x to v0.4.x:**

- CLI tool introduced (`xsm generate-template`)
- `after` transition support added to `SyncInterpreter`
- No breaking changes

## Async Support

If your project uses `asyncio`, you can use the async `Interpreter` instead:

```python
import asyncio
from xstate_statemachine import create_machine, Interpreter

config = {
    "id": "asyncToggle",
    "initial": "off",
    "states": {
        "off": {"on": {"TOGGLE": "on"}},
        "on":  {"on": {"TOGGLE": "off"}}
    }
}

async def main():
    machine = create_machine(config)
    interp = await Interpreter(machine).start()

    await interp.send("TOGGLE")
    print(interp.active_state_ids)
    # {'asyncToggle.on'}

    await interp.stop()

asyncio.run(main())
```

> **Tip:** Use `SyncInterpreter` for scripts, CLI tools, and testing. Use `Interpreter` for web servers, event loops, and real-time applications.

## Next Steps

Now that you're set up, explore the features:

- **[Quick Start](../quick-start/)** — Build 5 different machine styles in detail
- **[Core Concepts](../core-concepts/)** — States, events, transitions, guards, actions
- **[Pythonic API](../pythonic-api/)** — Define machines in pure Python (3 styles)
- **[JSON Configuration](../json-config/)** — XState JSON format reference
- **[Context](../context/)** — Working with machine data
- **[Guards](../guards/)** — Conditional transitions
- **[Actions](../actions/)** — Side effects and state mutations
- **[CLI Generator](../cli/)** — Generate production-ready code from XState JSON
- **[Examples](../examples/)** — Real-world patterns and advanced usage
