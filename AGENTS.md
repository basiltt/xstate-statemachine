# AGENTS.md - Agent Instructions for xstate-statemachine

## Project Overview

A Python library for parsing and running XState-compatible JSON state machines. This is a **published PyPI library** (`xstate-statemachine`) with daily downloads. Changes must be documented in CHANGELOG.md following the Keep a Changelog format.

**Key Facts:**
- Python 3.8+ support
- Async-first (`Interpreter`) with sync fallback (`SyncInterpreter`)
- 100% XState JSON compatible
- Actor model support with spawn actions
- Plugin architecture for extensibility
- CLI tool (`xsm`) for code generation

## Build, Test, and Lint Commands

### Setup
```bash
# Install dependencies and set up development environment
poetry install

# Install pre-commit hooks (required before first commit)
pre-commit install
```

### Testing
```bash
# Run all tests
poetry run pytest

# Run a single test file
poetry run pytest tests/test_interpreter.py

# Run a specific test
poetry run pytest tests/test_interpreter.py::TestInterpreter::test_basic_transition

# Run tests in a directory
poetry run pytest tests/tests_cli/

# Run with verbose output
poetry run pytest -v

# Run with coverage
poetry run pytest --cov=src/xstate_statemachine
```

### Linting and Formatting
```bash
# Run all pre-commit hooks on all files
pre-commit run --all-files

# Run Black formatter only
poetry run black src/ tests/ --line-length=79

# Run Flake8 only
poetry run flake8 src/ tests/

# Check specific file
poetry run flake8 src/xstate_statemachine/interpreter.py
```

### CLI Tool
```bash
# Generate boilerplate from JSON
poetry run xsm generate-template path/to/machine.json

# Using aliases
poetry run xsm gt path/to/machine.json

# Hierarchical machines (parent + children)
poetry run xsm gt -jp parent.json -jc child1.json -jc child2.json

# Sync mode with function style
poetry run xsm gt machine.json -am no -s function

# Single file output
poetry run xsm gt machine.json -fc 1
```

## Code Style Guidelines

### Imports
- **Order**: Standard library → Third-party → Project-specific
- **Format**: Use explicit imports, avoid `from module import *`
- **Group imports** with separator comments and emojis:

```python
# -------------------------------------------------------------------------
# 📦 Standard Library Imports
# -------------------------------------------------------------------------
import asyncio
import logging
from typing import Dict, List, Optional, Any

# -------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -------------------------------------------------------------------------
from .models import MachineNode, StateNode
from .events import Event
```

### Formatting
- **Line length**: 79 characters (Black)
- **Formatter**: Black 25.1.0 with Python 3.13
- **Quote style**: Double quotes
- **Trailing commas**: Use in multi-line structures

### Naming Conventions
- **Python code**:
  - Functions/variables: `snake_case`
  - Classes: `PascalCase`
  - Constants: `UPPER_SNAKE_CASE`
  - Private methods: `_leading_underscore`
  - Type variables: `TContext`, `TEvent`
- **JSON (XState config)**:
  - Actions/guards/services: `camelCase` (auto-converted from Python `snake_case`)
  - Events: `SCREAMING_SNAKE_CASE`
  - State IDs: `camelCase`

### Type Hints
- Use comprehensive type hints for all function signatures
- Use generics where appropriate: `MachineNode[TContext, TEvent]`
- Import from `typing`: `Dict`, `List`, `Optional`, `Any`, `Callable`, `Union`, etc.
- Use `-> None` for functions that don't return

### Error Handling
- **Guards**: Must return `bool`. If guard raises exception, it's treated as `False`
- **Actions**: Log errors, skip remaining actions in list, continue processing
- **Services**: Raise exceptions to trigger `onError` transition
- **Exceptions**: Use custom exception hierarchy (all inherit from `XStateMachineError`)

```python
# Guard example - pure function, returns bool
def can_retry(ctx: Dict, event: Event) -> bool:
    return ctx.get("attempts", 0) < 3

# Action example - can mutate context, no return
def increment_retry(i, ctx: Dict, e: Event, a: ActionDefinition) -> None:
    ctx["attempts"] = ctx.get("attempts", 0) + 1
    logger.info("Retry count: %d", ctx["attempts"])

# Service example - can raise exceptions
def fetch_data(i, ctx: Dict, e: Event) -> Dict:
    result = api_call()  # May raise
    return result
```

### Documentation
- **File headers**: Include module docstrings with emoji markers and description
- **Function docstrings**: Google-style with Args/Returns sections
- **Class docstrings**: Describe purpose, attributes, and usage
- **Inline comments**: Use emoji prefixes for quick visual grep:
  - `✅` Success/completion
  - `🚀` Initialization
  - `🔥` Errors/warnings
  - `💡` Tips/hints
  - `⚠️` Caution
  - `📝` Notes/explanations
  - `🏛️` Architecture decisions

```python
def process_event(self, event: Event) -> None:
    """Process an event through the state machine.
    
    Args:
        event: The event to process, containing type and payload.
        
    Returns:
        None
        
    Raises:
        StateNotFoundError: If transition target doesn't exist.
    """
    # 🚀 Start processing the event
    logger.debug("Processing event: %s", event.type)
    
    # 💡 Check if we're in a valid state to process events
    if self.status != "running":
        # ⚠️ Machine not running, drop event
        return
    
    # ... processing logic
    
    # ✅ Event processing complete
```

### Code Organization
- Each module should have a clear, single responsibility
- Use `__all__` in `__init__.py` to define public API
- Keep functions under 35 complexity (Flake8 max-complexity=35)
- Maximum file length: ~500 lines (split if larger)
- Group related classes/functions together

## Architecture Overview

### Core Components

```
MachineNode (JSON parsed structure)
    ├── StateNode (individual states)
    │   ├── transitions (on, after)
    │   ├── actions (entry, exit)
    │   ├── invoke (services)
    │   └── states (child states for compound/parallel)
    └── logic (MachineLogic with actions/guards/services)

Interpreter (async runtime)
    ├── event queue (asyncio.Queue)
    ├── task manager (asyncio.Task tracking)
    ├── plugins (Lifecycle hooks)
    └── actor registry (child interpreters)

SyncInterpreter (blocking runtime)
    ├── event queue (list)
    ├── thread manager (Timer/Thread tracking)
    └── actor registry (child interpreters in threads)
```

### Key Classes

| Class | Purpose | When to Use |
|-------|---------|-------------|
| `Interpreter` | Async state machine runtime | Web servers, async workflows |
| `SyncInterpreter` | Blocking state machine runtime | CLI tools, tests, sync workflows |
| `MachineNode` | Parsed machine definition | Direct access to state tree |
| `MachineLogic` | Container for implementations | Explicit binding of actions/guards |
| `LogicLoader` | Auto-discovery of logic | Functional/class-based auto-binding |
| `Event` | Event data structure | Creating events programmatically |
| `PluginBase` | Plugin interface | Custom telemetry, logging |
| `TaskManager` | Background task tracking | Internal use (timers, services) |

### State Types

```json
{
  "atomic": {
    "on": { "EVENT": "target" }
  },
  "compound": {
    "initial": "child1",
    "states": { "child1": {}, "child2": {} }
  },
  "parallel": {
    "type": "parallel",
    "states": { "region1": {}, "region2": {} }
  },
  "final": {
    "type": "final"
  }
}
```

## Working with State Machines

### 1. Basic Machine Creation

```python
import json
from xstate_statemachine import create_machine, Interpreter, MachineLogic

# Load JSON config
with open("machine.json") as f:
    config = json.load(f)

# Define logic
def my_action(i, ctx, e, a):
    ctx["counter"] = ctx.get("counter", 0) + 1

def my_guard(ctx, e) -> bool:
    return ctx.get("counter", 0) < 5

logic = MachineLogic(
    actions={"myAction": my_action},
    guards={"myGuard": my_guard}
)

# Create machine
machine = create_machine(config, logic=logic)

# Run async
async def main():
    interpreter = await Interpreter(machine).start()
    await interpreter.send("EVENT")
    await interpreter.stop()

# Run sync
def main_sync():
    from xstate_statemachine import SyncInterpreter
    interpreter = SyncInterpreter(machine).start()
    interpreter.send("EVENT")
    interpreter.stop()
```

### 2. Auto-Discovery with LogicLoader

```python
# logic_module.py
def increment_counter(i, ctx, e, a):
    ctx["counter"] = ctx.get("counter", 0) + 1

def can_continue(ctx, e) -> bool:
    return ctx.get("counter", 0) < 10

# runner.py
import logic_module
from xstate_statemachine import create_machine

machine = create_machine(config, logic_modules=[logic_module])
```

### 3. Class-Based Logic

```python
class MyMachineLogic:
    def __init__(self):
        self.api_client = APIClient()
    
    def fetch_data(self, i, ctx, e, a):
        # Access instance state
        result = self.api_client.get()
        ctx["data"] = result
    
    def is_valid(self, ctx, e) -> bool:
        return ctx.get("data") is not None

logic = MyMachineLogic()
machine = create_machine(config, logic_providers=[logic])
```

### 4. Invoking Services

```python
# In JSON
{
  "loading": {
    "invoke": {
      "src": "fetchData",
      "onDone": {
        "target": "success",
        "actions": "storeData"
      },
      "onError": {
        "target": "error",
        "actions": "logError"
      }
    }
  }
}

# In Python
async def fetch_data(i, ctx, e):
    """Service function - can be async or sync."""
    response = await http_client.get("/api/data")
    return response.json()  # Becomes event.data in onDone

def store_data(i, ctx, e, a):
    """Action receiving service result."""
    ctx["data"] = e.data  # e.data contains service return value
```

### 5. After Timers

```python
# In JSON - multiple timers per state
{
  "retrying": {
    "after": {
      "1000": {
        "target": "fetching",
        "guard": "shouldRetry"
      },
      "5000": {
        "target": "timeout",
        "actions": "alertOps"
      }
    }
  }
}

# Guard evaluated when timer fires
def should_retry(ctx, e) -> bool:
    return ctx.get("attempts", 0) < 3
```

### 6. Actor Model (Spawn)

```python
# Parent machine spawns child
{
  "processing": {
    "entry": "spawnWorker",
    "on": {
      "WORKER_DONE": {
        "target": "complete",
        "actions": "processResult"
      }
    }
  }
}

# In Python
def spawn_worker(i, ctx, e, a):
    """Action spawning child actor."""
    # Child machine definition
    child_config = {...}
    child_logic = MachineLogic(...)
    child_machine = create_machine(child_config, logic=child_logic)
    
    # Spawn - creates new interpreter
    i._spawn_actor("worker", child_machine)

def send_result_to_parent(i, ctx, e, a):
    """In child machine - send result back."""
    i.parent.send("WORKER_DONE", result=ctx.get("result"))
```

## Testing Patterns

### 1. Basic Test Structure

```python
import unittest
from xstate_statemachine import create_machine, SyncInterpreter, MachineLogic

class TestMyMachine(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            "id": "testMachine",
            "initial": "idle",
            "states": {
                "idle": {
                    "on": {"START": "running"}
                },
                "running": {
                    "type": "final"
                }
            }
        }
        self.machine = create_machine(self.config)
    
    def test_transition(self):
        """Test basic state transition."""
        interpreter = SyncInterpreter(self.machine).start()
        
        self.assertIn("testMachine.idle", interpreter.current_state_ids)
        
        interpreter.send("START")
        
        self.assertIn("testMachine.running", interpreter.current_state_ids)
        
        interpreter.stop()
```

### 2. Async Testing

```python
import unittest
from xstate_statemachine import create_machine, Interpreter

class TestAsyncMachine(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        """Set up async test fixtures."""
        self.machine = create_machine(self.config)
        self.interpreter = await Interpreter(self.machine).start()
    
    async def asyncTearDown(self):
        """Clean up async resources."""
        await self.interpreter.stop()
    
    async def test_async_service(self):
        """Test async service invocation."""
        await self.interpreter.send("FETCH")
        
        # Wait for service to complete
        await asyncio.sleep(0.1)
        
        self.assertIn("success", self.interpreter.current_state_ids)
```

### 3. Mocking Services

```python
from unittest.mock import AsyncMock, patch

async def test_with_mocked_service(self):
    """Test with mocked external service."""
    mock_service = AsyncMock(return_value={"status": "ok"})
    
    logic = MachineLogic(
        services={"fetchData": mock_service}
    )
    machine = create_machine(self.config, logic=logic)
    
    interpreter = await Interpreter(machine).start()
    await interpreter.send("FETCH")
    
    mock_service.assert_called_once()
    self.assertIn("success", interpreter.current_state_ids)
```

### 4. Testing Guards

```python
def test_guard_blocks_transition(self):
    """Test that guard prevents transition."""
    config = {
        "initial": "idle",
        "context": {"allowed": False},
        "states": {
            "idle": {
                "on": {
                    "GO": {
                        "target": "next",
                        "guard": "isAllowed"
                    }
                }
            },
            "next": {}
        }
    }
    
    def is_allowed(ctx, e) -> bool:
        return ctx.get("allowed", False)
    
    logic = MachineLogic(guards={"isAllowed": is_allowed})
    machine = create_machine(config, logic=logic)
    
    interpreter = SyncInterpreter(machine).start()
    interpreter.send("GO")
    
    # Should still be in idle (guard blocked)
    self.assertIn("idle", interpreter.current_state_ids)
    
    # Update context and try again
    interpreter.context["allowed"] = True
    interpreter.send("GO")
    
    self.assertIn("next", interpreter.current_state_ids)
```

### 5. Snapshot Testing

```python
def test_snapshot_restore(self):
    """Test state snapshotting and restoration."""
    interpreter = SyncInterpreter(self.machine).start()
    interpreter.send("PROGRESS")
    interpreter.send("PROGRESS")
    
    # Capture snapshot
    snapshot = interpreter.get_snapshot()
    
    # Verify snapshot contains expected data
    import json
    data = json.loads(snapshot)
    self.assertEqual(data["context"]["progress"], 2)
    
    # Stop and restore (async only)
    # restored = await Interpreter.from_snapshot(snapshot, self.machine).start()
```

## Common Pitfalls and Solutions

### 1. Async in Sync Context

**Problem**: Using `async def` action with `SyncInterpreter`

**Error**: `NotSupportedError: Async actions not supported in sync mode`

**Solution**: Use sync functions for `SyncInterpreter`:

```python
# ❌ Wrong
def my_action(i, ctx, e, a):
    await asyncio.sleep(1)  # Will fail

# ✅ Correct
def my_action(i, ctx, e, a):
    time.sleep(1)  # Use blocking calls in sync mode
```

### 2. Guard Exceptions

**Problem**: Guard raises exception, transition silently fails

**Solution**: Guards must return bool, not raise:

```python
# ❌ Risky
def my_guard(ctx, e) -> bool:
    return ctx["key"]["nested"] > 5  # May raise KeyError

# ✅ Safe
def my_guard(ctx, e) -> bool:
    try:
        return ctx.get("key", {}).get("nested", 0) > 5
    except (KeyError, TypeError):
        return False
```

### 3. Event Naming

**Problem**: Events in JSON vs Python mismatch

**Solution**: Use `SCREAMING_SNAKE_CASE` in JSON, send as-is:

```json
{
  "on": {
    "USER_CLICKED": { "target": "active" }
  }
}
```

```python
interpreter.send("USER_CLICKED")
```

### 4. Context Mutation

**Problem**: Modifying context doesn't persist

**Solution**: Mutate dict in-place, don't replace:

```python
# ❌ Wrong
def bad_action(i, ctx, e, a):
    ctx = {"new": "value"}  # Replaces local reference only

# ✅ Correct
def good_action(i, ctx, e, a):
    ctx["new"] = "value"  # Mutates in-place
```

### 5. Service Error Handling

**Problem**: Service exceptions crash interpreter

**Solution**: Always use `onError` or catch in service:

```json
{
  "invoke": {
    "src": "riskyService",
    "onDone": "success",
    "onError": {
      "target": "error",
      "actions": "handleError"
    }
  }
}
```

```python
def risky_service(i, ctx, e):
    try:
        return api.call()
    except Exception as exc:
        # Will trigger onError with exc as event.data
        raise ServiceError(str(exc))
```

## Plugin Development

### Creating a Plugin

```python
from xstate_statemachine import PluginBase

class MetricsPlugin(PluginBase):
    """Collect metrics on state transitions."""
    
    def __init__(self, metrics_client):
        self.client = metrics_client
        self.transition_count = 0
    
    def on_interpreter_start(self, interpreter):
        """Called when interpreter starts."""
        self.client.increment("interpreter.start")
    
    def on_transition(self, interpreter, from_states, to_states, transition):
        """Called on every state transition."""
        self.transition_count += 1
        self.client.timing(
            "transition.duration",
            transition.duration_ms
        )
    
    def on_guard_evaluated(self, interpreter, guard_name, event, result):
        """Called after guard evaluation."""
        self.client.increment(
            f"guard.{guard_name}",
            tags={"result": str(result)}
        )
    
    def on_service_done(self, interpreter, invocation, result):
        """Called when service completes."""
        self.client.timing(
            f"service.{invocation.src}",
            invocation.duration_ms
        )
    
    def on_interpreter_stop(self, interpreter):
        """Called when interpreter stops."""
        self.client.gauge(
            "transitions.total",
            self.transition_count
        )

# Usage
interpreter = Interpreter(machine).use(MetricsPlugin(client))
```

## Workflow Guidelines

### Before Submitting Changes

1. **Run full test suite**: `poetry run pytest`
2. **Run pre-commit**: `pre-commit run --all-files`
3. **Update CHANGELOG.md** under "## [Unreleased]" (not for tiny changes)
4. **Add examples** in `examples/` if applicable
5. **Follow Conventional Commits** for messages (e.g., `feat:`, `fix:`, `docs:`)

### Branch Naming

- Format: `<type>/<short-description>`
- Examples:
  - `feat/add-actor-spawn`
  - `fix/sync-interpreter-timer`
  - `docs/update-readme`
  - `refactor/extract-base-class`

### CHANGELOG.md Format

Follow Keep a Changelog with sections:

```markdown
## [Unreleased]

### Added
- New feature X
- Support for Y

### Changed
- Improved performance of Z
- Updated dependency versions

### Fixed
- Bug where A would cause B
- Memory leak in C

### Deprecated
- Old API method D (will be removed in 0.5.0)
```

## Project Structure

```
xstate-statemachine/
├── src/xstate_statemachine/    # Main library code
│   ├── __init__.py            # Public API exports
│   ├── interpreter.py         # Async Interpreter (asyncio-based)
│   ├── sync_interpreter.py    # SyncInterpreter (blocking)
│   ├── base_interpreter.py    # Shared base class
│   ├── factory.py             # create_machine() function
│   ├── models.py              # MachineNode, StateNode, etc.
│   ├── machine_logic.py       # MachineLogic container
│   ├── logic_loader.py        # Auto-discovery of logic
│   ├── events.py              # Event, DoneEvent, AfterEvent
│   ├── exceptions.py          # Custom exception hierarchy
│   ├── task_manager.py        # Background task tracking
│   ├── plugins.py             # PluginBase, LoggingInspector
│   ├── resolver.py            # State target resolution
│   ├── logger.py              # Library logging setup
│   └── cli/                   # CLI implementation
│       ├── __main__.py        # Entry point
│       ├── args.py            # Argument parsing
│       ├── generator.py       # Code generation
│       ├── extractor.py       # JSON extraction
│       └── utils.py           # CLI utilities
├── tests/                     # Test suite
│   ├── test_interpreter.py    # Async interpreter tests
│   ├── test_sync_interpreter.py # Sync interpreter tests
│   ├── test_factory.py        # Factory tests
│   ├── test_models.py         # Model tests
│   └── tests_cli/             # CLI tests
├── examples/                  # Usage examples
│   ├── sync/                  # Sync interpreter examples
│   ├── async/                 # Async interpreter examples
│   └── hybrid/                # Mixed async/sync examples
├── pyproject.toml            # Poetry configuration
├── .pre-commit-config.yaml   # Pre-commit hooks
├── CHANGELOG.md              # Version history
├── CONTRIBUTING.md           # Full contribution guide
└── AGENTS.md                 # This file
```

## Key Library Concepts

### State Machine Components

- **MachineNode**: Parsed machine definition from JSON - the static structure
- **Interpreter**: Async runtime engine - runs the machine in asyncio
- **SyncInterpreter**: Blocking runtime engine - runs machine synchronously
- **MachineLogic**: Container for actions/guards/services - binds Python to JSON
- **Event**: Named tuple of (type, payload) - what drives state changes
- **LogicLoader**: Auto-discovers logic from modules - reduces boilerplate
- **TaskManager**: Tracks timers and services - ensures cleanup on state exit

### Logic Binding

Python `snake_case` automatically converts to JSON `camelCase`:

```python
# Python
def increment_flips(i, ctx, e, a): ...

# JSON
{
  "actions": "incrementFlips"
}
```

This is handled by `LogicLoader._snake_to_camel()`.

### Target Resolution

State targets in JSON can use different formats:

| Format | Example | Resolves To |
|--------|---------|-------------|
| Sibling | `"target": "next"` | Peer state in same parent |
| Child | `"target": "parent.child"` | Descendant state |
| Relative | `"target": ".sibling"` | Sibling of current state |
| Absolute | `"target": "#machine.state"` | State from root |
| Parent | `"target": "."` | Parent of current state |

### Event Types

| Event Pattern | When Sent | Example |
|---------------|-----------|---------|
| User events | Manual `.send()` | `"CLICK"`, `"SUBMIT"` |
| `entry.` | State entered | `"entry.loading"` |
| `exit.` | State exited | `"exit.loading"` |
| `after.` | Timer fires | `"after.5000.loading"` |
| `done.invoke.` | Service completes | `"done.invoke.fetchData"` |
| `error.platform.` | Service errors | `"error.platform.fetchData"` |
| `done.state.` | Compound state completes | `"done.state.parent"` |

### Important Notes

- **Public library**: Changes affect daily downloads - be careful with breaking changes
- **Sync vs Async**: Both interpreters supported - don't use `async def` in sync context
- **CLI tool**: Entry point is `xsm`, not `xstate-statemachine` (legacy name deprecated)
- **Python 3.8+**: Minimum supported version
- **Error handling**: Guards that raise are treated as `False`, actions that raise skip remaining actions
- **Timers**: All timers auto-cancel when state exits (no manual cleanup needed)
- **Services**: Must raise to trigger `onError`, return value becomes `event.data` in `onDone`
- **Actors**: Spawned actors inherit parent's plugins, can communicate via `i.parent.send()`

## Performance Tips

1. **Use SyncInterpreter for CPU-bound work** - No asyncio overhead
2. **Batch events** - Send multiple events before checking state (async)
3. **Avoid deep nesting** - Flatten state machines when possible
4. **Use guards sparingly** - Complex guards slow down evaluation
5. **Snapshot strategically** - Only snapshot at stable states
6. **Disable debug logging** in production - Set level to INFO or higher

## Resources

- **Stately Editor**: https://stately.ai/editor - Visual design tool
- **XState Docs**: https://stately.ai/docs - Core concepts
- **PyPI**: https://pypi.org/project/xstate-statemachine/ - Package info
- **GitHub**: https://github.com/basiltt/xstate-statemachine - Source code
