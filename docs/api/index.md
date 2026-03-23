---
title: "API Reference"
description: "Complete class, function, and decorator reference for XState-StateMachine."
---

# API Reference

Complete reference for every public class, function, decorator, and exception
exported by `xstate_statemachine`. All items listed here are available as
top-level imports:

```python
from xstate_statemachine import create_machine, Interpreter, State  # etc.
```

---

## Factory Functions

### `create_machine(config, *, logic=None, logic_modules=None, logic_providers=None)`

Creates, validates, and assembles a state machine instance from an
XState-compatible JSON configuration dictionary. This is the **primary
entry point** when working with JSON/dict-based machine definitions.

The function intelligently resolves business logic (actions, guards, services)
from whichever source you provide. If an explicit `MachineLogic` instance is
passed via `logic`, it takes precedence. Otherwise, the factory delegates to
`LogicLoader` to auto-discover implementations from the specified modules or
provider objects.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `config` | `Dict[str, Any]` | Yes | -- | The machine's structural definition. Must contain top-level `"id"` (non-empty string) and `"states"` keys. Typically loaded from JSON or YAML. |
| `logic` | `MachineLogic` | No | `None` | A pre-constructed `MachineLogic` instance containing all required actions, guards, and services. When provided, auto-discovery is skipped. |
| `logic_modules` | `List[Union[str, ModuleType]]` | No | `None` | Python modules (or their dotted import-path strings, e.g. `"my_app.logic.actions"`) to scan for logic functions. |
| `logic_providers` | `List[object]` | No | `None` | Class instances whose public methods are scanned to satisfy the machine's logic requirements. Provider methods override module-level functions on name collision. |

**Returns:** `MachineNode` -- a fully constructed, validated machine ready for
an interpreter.

**Raises:**

| Exception | Condition |
|-----------|-----------|
| `InvalidConfigError` | `config` is missing `"id"`, `"states"`, or `"id"` is not a non-empty string. |
| `ImplementationMissingError` | Auto-discovery is active and a required action, guard, or service cannot be found. |

#### Example 1 -- Minimal (no logic)

```python
from xstate_statemachine import create_machine

config = {
    "id": "toggle",
    "initial": "inactive",
    "states": {
        "inactive": {"on": {"TOGGLE": "active"}},
        "active":   {"on": {"TOGGLE": "inactive"}},
    },
}
machine = create_machine(config)
```

#### Example 2 -- With explicit `MachineLogic`

```python
from xstate_statemachine import create_machine, MachineLogic

def log_toggle(interpreter, context, event, action_def):
    print(f"Toggled! Count: {context['count']}")

logic = MachineLogic(actions={"logToggle": log_toggle})

config = {
    "id": "toggle",
    "initial": "off",
    "states": {
        "off": {"on": {"FLIP": {"target": "on", "actions": "logToggle"}}},
        "on":  {"on": {"FLIP": {"target": "off", "actions": "logToggle"}}},
    },
}
machine = create_machine(config, logic=logic)
```

#### Example 3 -- With module-based auto-discovery

```python
# file: my_logic.py
def log_toggle(interpreter, context, event, action_def):
    context["count"] += 1

# file: main.py
import my_logic
from xstate_statemachine import create_machine

machine = create_machine(config, logic_modules=[my_logic])
# or by string path:
machine = create_machine(config, logic_modules=["my_logic"])
```

#### Example 4 -- With provider objects

```python
from xstate_statemachine import create_machine

class ToggleLogic:
    def log_toggle(self, interpreter, context, event, action_def):
        context["count"] += 1

machine = create_machine(config, logic_providers=[ToggleLogic()])
```

---

### `build_machine(*, id, states, transitions=None, actions=None, guards=None, services=None, context=None)`

Builds a state machine entirely from Python objects using the **functional
Pythonic API**. This is the simplest style -- define `State` objects,
`Transition` objects, and decorated callables at module level, then call this
function to produce a `MachineNode`.

Internally, `build_machine` compiles the provided objects into a JSON config
dict and a `MachineLogic` instance, then delegates to `create_machine()`.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `id` | `str` | Yes | -- | Machine identifier string. |
| `states` | `List[State]` | Yes | -- | Top-level `State` objects. Exactly one must have `initial=True` (unless a single parallel root). |
| `transitions` | `List[Union[Transition, TransitionGroup]]` | No | `None` | Explicit transitions created with `state.to()`, `transition()`, or the `\|` operator. |
| `actions` | `List[Callable]` | No | `None` | Action callables (may be decorated with `@action`). |
| `guards` | `List[Callable]` | No | `None` | Guard callables (may be decorated with `@guard`). Must be synchronous. |
| `services` | `List[Callable]` | No | `None` | Service callables (may be decorated with `@service`). |
| `context` | `Dict` | No | `None` | Initial context dictionary. |

**Returns:** `MachineNode`

**Raises:** `InvalidConfigError` on duplicate state names, missing initial
state, or invalid transition sources.

```python
from xstate_statemachine import State, build_machine, action

idle    = State("idle", initial=True)
running = State("running")
done    = State("done", final=True)

@action
def log_start(interpreter, context, event, action_def):
    print("Machine started!")

machine = build_machine(
    id="workflow",
    states=[idle, running, done],
    transitions=[
        idle.to(running, event="START", actions=["logStart"]),
        running.to(done, event="FINISH"),
    ],
    actions=[log_start],
    context={"step": 0},
)
```

---

## Core Classes

### `State`

```python
State(
    name: str = "",
    *,
    initial: bool = False,
    final: bool = False,
    parallel: bool = False,
    on: Optional[Dict[str, Any]] = None,
    entry: Optional[List[str]] = None,
    exit: Optional[List[str]] = None,
    after: Optional[Dict[int, Any]] = None,
    invoke: Optional[Union[Dict, List]] = None,
    on_done: Optional[Union[str, Dict]] = None,
    always: Optional[Union[str, Dict, List]] = None,
    context: Optional[Dict] = None,
    states: Optional[List[State]] = None,
)
```

A state definition for use across all three Pythonic API styles (functional,
builder, and class-based).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | `""` | State name. Auto-inferred from the class attribute name in `StateMachine` subclasses. |
| `initial` | `bool` | `False` | Whether this is the initial state among its siblings. |
| `final` | `bool` | `False` | Whether this is a final (terminal) state. Cannot be combined with `parallel`. |
| `parallel` | `bool` | `False` | Whether this is a parallel state. Cannot be combined with `final`. |
| `on` | `Dict[str, Any]` | `None` | Event-to-target shorthand dict, e.g. `{"CLICK": "active"}`. |
| `entry` | `List[str]` | `None` | List of entry action names executed when the state is entered. |
| `exit` | `List[str]` | `None` | List of exit action names executed when the state is exited. |
| `after` | `Dict[int, Any]` | `None` | Delayed transition dict. Keys are milliseconds, values are target strings or transition dicts, e.g. `{3000: "timeout"}`. |
| `invoke` | `Union[Dict, List]` | `None` | Service invocation config. A single dict or list of dicts, each with `"src"`, optional `"onDone"`, `"onError"`. |
| `on_done` | `Union[str, Dict]` | `None` | Completion transition. Fired when all child states in a compound/parallel state reach a final state. |
| `always` | `Union[str, Dict, List]` | `None` | Eventless (transient) transition config. Evaluated immediately after state entry. |
| `context` | `Dict` | `None` | Initial context dict. Only meaningful at the root level. |
| `states` | `List[State]` | `None` | Child `State` objects for building hierarchical/nested machines. |

**Raises:** `InvalidConfigError` if both `final=True` and `parallel=True`.

#### Key Methods

##### `state.to(target, *, event, guard=None, actions=None, reenter=False)`

Creates an **external transition** from this state to a target state.

```python
state.to(
    target: State,
    *,
    event: Optional[str] = None,    # REQUIRED -- event name
    guard: Optional[str] = None,    # guard function name
    actions: Optional[List[str]] = None,  # action names to run
    reenter: bool = False,          # force exit/re-entry on self-transitions
) -> Transition
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `target` | `State` | Yes | The destination `State` object. |
| `event` | `str` | Yes | The event name that triggers this transition. |
| `guard` | `str` | No | Guard function name. Transition only taken if guard returns `True`. |
| `actions` | `List[str]` | No | Action names executed during the transition. |
| `reenter` | `bool` | No | If `True` and target equals source, forces exit and re-entry (runs exit/entry actions). |

**Returns:** `Transition`

**Raises:** `InvalidConfigError` if `event` is not provided.

```python
idle = State("idle", initial=True)
active = State("active")

t = idle.to(active, event="ACTIVATE", actions=["logActivation"])
```

##### `state.internal(event, *, guard=None, actions=None)`

Creates an **internal transition** -- actions execute but no state change
occurs. Entry and exit actions of the current state are **not** run.

```python
state.internal(
    event: str,
    *,
    guard: Optional[str] = None,
    actions: Optional[List[str]] = None,
) -> Transition
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `event` | `str` | Yes | The event name. |
| `guard` | `str` | No | Guard function name. |
| `actions` | `List[str]` | No | Action names to execute. |

**Returns:** `Transition` with `internal=True`.

```python
counter = State("counter", initial=True)
t = counter.internal("INCREMENT", actions=["addOne"])
```

##### `@state.enter` -- Entry action decorator

Registers a function as an entry action for this state. Only valid inside a
`StateMachine` class definition. The function name is auto-converted from
`snake_case` to `camelCase`.

```python
class MyMachine(StateMachine):
    idle = State(initial=True)

    @idle.enter
    def on_idle_entered(self, interpreter, context, event, action_def):
        print("Entered idle!")
```

**Returns:** The original function with `_xsm_type="action"` and
`_xsm_name` markers attached.

##### `@state.exit` -- Exit action decorator

Registers a function as an exit action for this state. Same semantics as
`@state.enter`.

```python
class MyMachine(StateMachine):
    active = State()

    @active.exit
    def on_active_exited(self, interpreter, context, event, action_def):
        print("Left active!")
```

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `exit_actions` | `List[str]` | Read-only list of exit action names for this state. |

#### `__init_subclass__` keyword behavior

`State` supports class-inheritance keywords for concise nested-state
definitions inside `StateMachine` subclasses:

```python
class MyMachine(StateMachine):
    class loading(State, initial=True):
        """A compound initial state defined as a class."""
        fetching = State(initial=True)
        parsing  = State()

    class done(State, final=True):
        """A final state."""
        pass

    class regions(State, parallel=True):
        """A parallel state."""
        pass
```

The keywords `initial`, `final`, and `parallel` are captured by
`__init_subclass__` and stored as `_xsm_initial`, `_xsm_final`, and
`_xsm_parallel` class attributes, respectively.

---

### `StateMachine`

Base class for defining state machines using Python class syntax. Uses a
custom metaclass (`_StateMachineMeta`) that collects `State` attributes,
`Transition`/`TransitionGroup` attributes, and `@action`/`@guard`/`@service`
decorated methods at class-definition time.

#### Class Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `machine_id` | `Optional[str]` | `None` | Machine identifier. Defaults to the class name if not set. |
| `initial_context` | `Optional[Dict]` | `None` | Initial context dictionary for the machine. |

#### Class Method

##### `StateMachine.create_machine(context=None) -> MachineNode`

Compiles the class definition into a JSON config and `MachineLogic`, then
delegates to `create_machine()`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `context` | `Dict` | No | Optional context override. If provided, replaces `initial_context`. |

**Returns:** `MachineNode`

```python
from xstate_statemachine import StateMachine, State, action

class TrafficLight(StateMachine):
    machine_id = "trafficLight"
    initial_context = {"cycle_count": 0}

    red    = State(initial=True)
    yellow = State()
    green  = State()

    cycle = (
        red.to(green, event="NEXT")
        | green.to(yellow, event="NEXT")
        | yellow.to(red, event="NEXT", actions=["countCycle"])
    )

    @action
    def count_cycle(self, interpreter, context, event, action_def):
        context["cycle_count"] += 1

machine = TrafficLight.create_machine()

# With a context override:
machine = TrafficLight.create_machine(context={"cycle_count": 10})
```

---

### `MachineBuilder`

```python
MachineBuilder(machine_id: str)
```

Fluent builder for constructing state machines step-by-step using method
chaining. Every mutating method returns `self`, enabling a fluent pipeline
that terminates with `.build()`.

| Parameter | Type | Description |
|-----------|------|-------------|
| `machine_id` | `str` | The machine's identifier string. |

#### Methods

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `.context(ctx)` | `ctx: Dict` | `MachineBuilder` | Sets the initial context dictionary. |
| `.state(name, **kwargs)` | See below | `MachineBuilder` | Adds a state to the machine. |
| `.transition(source, event, target, **kwargs)` | See below | `MachineBuilder` | Adds a transition between two named states. |
| `.child_states(parent, *, initial, states, parallel)` | See below | `MachineBuilder` | Adds child states to an existing state. |
| `.action(name, fn)` | `name: str, fn: Callable` | `MachineBuilder` | Registers an action function by name. |
| `.guard(name, fn)` | `name: str, fn: Callable` | `MachineBuilder` | Registers a guard function by name. |
| `.service(name, fn)` | `name: str, fn: Callable` | `MachineBuilder` | Registers a service function by name. |
| `.build(context=None)` | `context: Optional[Dict]` | `MachineNode` | Builds and returns the final `MachineNode`. Idempotent -- safe to call multiple times. |

##### `.state()` full parameters

```python
.state(
    name: str,
    *,
    initial: bool = False,
    final: bool = False,
    parallel: bool = False,
    on: Optional[Dict] = None,
    entry: Optional[List] = None,
    exit: Optional[List] = None,
    after: Optional[Dict] = None,
    invoke: Optional[Union[Dict, List]] = None,
    on_done: Optional[Union[str, Dict]] = None,
    always: Optional[Union[str, Dict, List]] = None,
) -> MachineBuilder
```

**Raises:** `InvalidConfigError` if the state name already exists, or if both
`final` and `parallel` are `True`.

##### `.transition()` full parameters

```python
.transition(
    source: str,
    event: str,
    target: str,
    *,
    guard: Optional[str] = None,
    actions: Optional[List[str]] = None,
    reenter: bool = False,
    internal: bool = False,
) -> MachineBuilder
```

##### `.child_states()` full parameters

```python
.child_states(
    parent: str,
    *,
    initial: Optional[str] = None,
    states: Optional[Dict[str, Dict]] = None,
    parallel: bool = False,
) -> MachineBuilder
```

**Raises:** `InvalidConfigError` if `parent` is not an already-defined state.

##### `.build()` full parameters

```python
.build(context: Optional[Dict] = None) -> MachineNode
```

Optional `context` overrides the context set by `.context()`. Deep-copies
internal state, so repeated `.build()` calls are safe.

**Raises:** `InvalidConfigError` if no initial state is defined (for
non-parallel, multi-state machines) or if a transition source is invalid.

#### Chaining example

```python
from xstate_statemachine import MachineBuilder

def log_it(interpreter, context, event, action_def):
    context["count"] += 1
    print(f"Count: {context['count']}")

machine = (
    MachineBuilder("counter")
    .context({"count": 0})
    .state("idle", initial=True)
    .state("counting")
    .state("done", final=True)
    .transition("idle", "START", "counting")
    .transition("counting", "INCREMENT", "counting",
                actions=["logIt"], reenter=True)
    .transition("counting", "FINISH", "done")
    .action("logIt", log_it)
    .build()
)
```

---

### `Transition`

Represents a transition between two states, triggered by an event. Created
by `State.to()`, `State.internal()`, or the standalone `transition()`
function. **Not typically instantiated directly by users.**

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `source` | `State` | The source `State`. |
| `target` | `Optional[State]` | The target `State`. `None` for internal transitions. |
| `event` | `str` | The event name that triggers this transition. |
| `guard` | `Optional[str]` | Guard function name. |
| `actions` | `List[str]` | Action names to execute during the transition. |
| `reenter` | `bool` | Whether to force exit/re-entry on self-transitions. |
| `internal` | `bool` | Whether this is an internal (no-state-change) transition. |

#### `|` operator

Combine multiple transitions into a `TransitionGroup` using the pipe
operator. The first transition whose guard passes wins (evaluated in order).

```python
idle = State("idle", initial=True)
premium = State("premium")
basic = State("basic")

# Multiple guarded transitions for the same event
signup = (
    idle.to(premium, event="SIGNUP", guard="isPremium")
    | idle.to(basic, event="SIGNUP")
)
# signup is a TransitionGroup with 2 transitions
```

---

### `TransitionGroup`

A collection of `Transition` objects created implicitly by the `|` operator.
Users never instantiate this directly.

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `transitions` | `List[Transition]` | The list of transitions in this group. |

#### `|` operator

`TransitionGroup` objects can be further combined with other `Transition` or
`TransitionGroup` objects:

```python
group_a = idle.to(s1, event="GO", guard="isA") | idle.to(s2, event="GO", guard="isB")
group_b = idle.to(s3, event="GO")

# Combine groups
all_transitions = group_a | group_b
# all_transitions is a TransitionGroup with 3 transitions
```

---

### `transition()` -- Standalone function

```python
transition(
    source: State,
    event: str,
    target: State,
    *,
    guard: Optional[str] = None,
    actions: Optional[List[str]] = None,
    reenter: bool = False,
    internal: bool = False,
) -> Transition
```

Functional alternative to `State.to()`. Creates a `Transition` between two
states. Useful when you prefer a function-call style over the method style.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `source` | `State` | Yes | The source state. |
| `event` | `str` | Yes | The event name (required). |
| `target` | `State` | Yes | The target state. |
| `guard` | `str` | No | Guard function name. |
| `actions` | `List[str]` | No | Action names to execute. |
| `reenter` | `bool` | No | Force exit/re-entry on self-transitions. |
| `internal` | `bool` | No | Create an internal transition (no state change). |

**Returns:** `Transition`

```python
from xstate_statemachine import State, transition

idle   = State("idle", initial=True)
active = State("active")

# These two are equivalent:
t1 = idle.to(active, event="START")
t2 = transition(idle, "START", active)

# With all options:
t3 = transition(
    idle, "START", active,
    guard="isReady",
    actions=["logStart", "initProcess"],
    reenter=False,
    internal=False,
)
```

---

## Interpreters

### `Interpreter(machine)` -- Async

```python
Interpreter(machine: MachineNode)
```

The primary **asynchronous** state machine engine. Processes events from an
`asyncio.Queue`, manages background tasks for `after` timers and `invoke`d
services, and supports spawning child actors. Recommended for I/O-bound
applications (web servers, IoT, automation scripts).

Uses a dedicated `TaskManager` to track all background `asyncio.Task` objects,
ensuring clean cancellation when states are exited.

#### Methods

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `await .start()` | `() -> Interpreter` | `Interpreter` | Starts the interpreter and its event loop. Enters the initial state(s). Returns `self` for chaining. Idempotent. |
| `await .stop()` | `() -> None` | `None` | Gracefully stops the event loop, cancels all tasks and child actors. Idempotent. |
| `await .send(event, **payload)` | `(Union[str, Dict, Event, DoneEvent, AfterEvent], **Any) -> None` | `None` | Sends an event to the queue. Accepts a string, dict, or `Event` object. Non-blocking. |
| `await .send_events(events)` | `(List[Union[str, Dict, Event]]) -> None` | `None` | Sends a list of events to the queue. Non-blocking. |
| `.use(plugin)` | `(PluginBase) -> Interpreter` | `Interpreter` | Registers a plugin. Returns `self` for chaining. |
| `.get_snapshot()` | `() -> str` | `str` | Returns a JSON string snapshot of current state, context, and status. |

#### Class Method

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `Interpreter.from_snapshot(json_str, machine)` | `(str, MachineNode) -> Interpreter` | `Interpreter` | Restores an interpreter from a snapshot. Does **not** re-run entry actions or restart timers/services. |

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `.current_state_ids` | `Set[str]` | Set of fully qualified IDs of all currently active atomic/final states. |
| `.context` | `Dict[str, Any]` | The mutable machine context. Changes made to this dict persist across transitions. |
| `.status` | `str` | One of `"uninitialized"`, `"running"`, or `"stopped"`. |
| `.id` | `str` | The interpreter's identifier (inherited from machine ID). |
| `.parent` | `Optional[BaseInterpreter]` | Reference to parent interpreter (for spawned child actors), otherwise `None`. |

#### Full async example

```python
import asyncio
from xstate_statemachine import create_machine, Interpreter, MachineLogic

config = {
    "id": "lightSwitch",
    "initial": "off",
    "context": {"flips": 0},
    "states": {
        "off": {"on": {"TOGGLE": {"target": "on", "actions": "countFlip"}}},
        "on":  {"on": {"TOGGLE": {"target": "off", "actions": "countFlip"}}},
    },
}

def count_flip(interpreter, context, event, action_def):
    context["flips"] += 1

logic = MachineLogic(actions={"countFlip": count_flip})
machine = create_machine(config, logic=logic)

async def main():
    service = await Interpreter(machine).start()

    await service.send("TOGGLE")          # off -> on
    await asyncio.sleep(0.05)             # let event loop process
    print(service.current_state_ids)      # {"lightSwitch.on"}
    print(service.context)                # {"flips": 1}

    await service.send("TOGGLE")          # on -> off
    await asyncio.sleep(0.05)
    print(service.context)                # {"flips": 2}

    await service.stop()

asyncio.run(main())
```

---

### `SyncInterpreter(machine)` -- Synchronous

```python
SyncInterpreter(machine: MachineNode)
```

A fully **synchronous** interpreter that processes events immediately within
the `send()` call. Suitable for CLI tools, desktop GUI event loops, simple
workflows, and predictable testing scenarios.

Events are handled one at a time from an internal `collections.deque`,
ensuring sequential, blocking execution. After timers are implemented using
background `threading.Thread` objects.

#### Methods

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `.start()` | `() -> SyncInterpreter` | `SyncInterpreter` | Starts the interpreter and enters the initial state(s). Returns `self` for chaining. Idempotent. |
| `.stop()` | `() -> None` | `None` | Stops the interpreter, cancels timers, stops child actors. Idempotent. |
| `.send(event, **payload)` | `(Union[str, Dict, Event, DoneEvent, AfterEvent], **Any) -> None` | `None` | Sends an event for **immediate** synchronous processing. Blocks until the event and all resulting transitions are fully processed. |
| `.send_events(events)` | `(List[Union[str, Dict, Event]]) -> None` | `None` | Sends a list of events for immediate processing. |
| `.use(plugin)` | `(PluginBase) -> SyncInterpreter` | `SyncInterpreter` | Registers a plugin. Returns `self` for chaining. |
| `.get_snapshot()` | `() -> str` | `str` | Returns a JSON string snapshot. |

#### Class Method

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `SyncInterpreter.from_snapshot(json_str, machine)` | `(str, MachineNode) -> SyncInterpreter` | `SyncInterpreter` | Restores an interpreter from a snapshot. |

#### Properties

Same as `Interpreter`:

| Property | Type | Description |
|----------|------|-------------|
| `.current_state_ids` | `Set[str]` | Active atomic/final state IDs. |
| `.context` | `Dict[str, Any]` | Mutable machine context. |
| `.status` | `str` | `"uninitialized"`, `"running"`, or `"stopped"`. |
| `.id` | `str` | Interpreter identifier. |
| `.parent` | `Optional[BaseInterpreter]` | Parent interpreter reference. |

#### Sync limitations

| Feature | Supported? | Notes |
|---------|-----------|-------|
| `after` timers | Yes | Implemented via `threading.Thread`. Fires event when delay elapses. |
| `invoke` services | Sync only | Async (`async def`) services raise `NotSupportedError`. |
| Async actions | No | `async def` actions raise `NotSupportedError`. |
| Actor spawning | Yes | Supports `spawn_` (background thread) and `spawn_blocking_` (blocking). |

#### Full sync example

```python
from xstate_statemachine import create_machine, SyncInterpreter, MachineLogic

config = {
    "id": "door",
    "initial": "closed",
    "states": {
        "closed": {"on": {"OPEN": "opened"}},
        "opened": {"on": {"CLOSE": "closed"}},
    },
}

machine = create_machine(config)
interpreter = SyncInterpreter(machine).start()

print(interpreter.current_state_ids)   # {"door.closed"}
interpreter.send("OPEN")
print(interpreter.current_state_ids)   # {"door.opened"}
interpreter.send("CLOSE")
print(interpreter.current_state_ids)   # {"door.closed"}

# Snapshot round-trip
snapshot = interpreter.get_snapshot()
restored = SyncInterpreter.from_snapshot(snapshot, machine)
print(restored.current_state_ids)      # {"door.closed"}

interpreter.stop()
```

#### Using plugins with `.use()`

```python
from xstate_statemachine import SyncInterpreter, LoggingInspector

interpreter = (
    SyncInterpreter(machine)
    .use(LoggingInspector())
    .start()
)
# All events, transitions, and actions will be logged
```

---

## Data Classes

### `Event(type, payload={})`

```python
@dataclass(frozen=True)
class Event:
    type: str
    payload: Dict[str, Any] = field(default_factory=dict)
```

The standard event sent to the state machine. This is a **frozen dataclass**
-- instances are immutable after creation. Each instance gets its own
`payload` dict (no shared mutable default).

| Field | Type | Description |
|-------|------|-------------|
| `type` | `str` | The event type identifier, matched against `"on"` transitions in the config. |
| `payload` | `Dict[str, Any]` | Optional event data accessible to actions and guards. Defaults to empty dict. |

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `.data` | `Dict[str, Any]` | Read-only alias for `payload`. Provided for compatibility. Raises `TypeError` if payload is not a dict. |

#### Type-checking behavior

Because `Event` is frozen, attempts to mutate fields after creation raise
`FrozenInstanceError`:

```python
e = Event(type="CLICK", payload={"x": 10})
e.type = "OTHER"  # Raises dataclasses.FrozenInstanceError
```

However, the `payload` dict itself is mutable (only the reference is frozen):

```python
e.payload["y"] = 20  # This works -- dict mutation, not field reassignment
```

#### Creating events

```python
from xstate_statemachine import Event

# Simple event
click = Event(type="CLICK")

# Event with payload
login = Event(type="LOGIN", payload={"username": "alice", "role": "admin"})

# Access payload via .data alias
print(login.data["username"])  # "alice"
```

The `send()` method on interpreters also accepts strings and dicts, which are
internally converted to `Event` objects:

```python
interpreter.send("CLICK")                          # Event(type="CLICK")
interpreter.send("LOGIN", username="alice")         # Event(type="LOGIN", payload={"username": "alice"})
interpreter.send({"type": "CLICK", "x": 10})       # Event(type="CLICK", payload={"x": 10})
```

---

### `ActionDefinition(config)`

```python
class ActionDefinition:
    def __init__(self, config: Union[str, Dict[str, Any]]): ...
```

Represents a single action to be executed, standardizing both shorthand
string definitions and detailed object definitions from the JSON config.

| Field | Type | Description |
|-------|------|-------------|
| `.type` | `str` | The action name/identifier. |
| `.params` | `Optional[Dict[str, Any]]` | Static parameters from the JSON config, or `None` if none were specified. |

**Construction from string:**

```python
ad = ActionDefinition("myAction")
# ad.type == "myAction", ad.params == None
```

**Construction from dict:**

```python
ad = ActionDefinition({"type": "myAction", "params": {"delay": 100}})
# ad.type == "myAction", ad.params == {"delay": 100}
```

**Raises:** `InvalidConfigError` if `config` is not a string or dictionary.

---

### `DoneEvent(type, data, src)`

```python
class DoneEvent(NamedTuple):
    type: str
    data: Any
    src: str
```

An internal event generated by the interpreter when:

1. An `invoke`d service completes successfully (`done.invoke.<service_id>`).
2. An `invoke`d service fails (`error.platform.<service_id>`).
3. A compound/parallel state reaches its final state (`done.state.<state_id>`).

| Field | Type | Description |
|-------|------|-------------|
| `type` | `str` | Event name following the convention: `"done.invoke.<id>"`, `"done.state.<id>"`, or `"error.platform.<id>"`. |
| `data` | `Any` | The data returned by the completed service, the child actor's final context, or the `Exception` on error. |
| `src` | `str` | The unique identifier of the service or state that generated this event. |

#### When it's generated

| Scenario | Event `type` | `data` contains |
|----------|-------------|----------------|
| Service completes | `done.invoke.<invocation_id>` | Return value of the service function |
| Service fails | `error.platform.<invocation_id>` | The `Exception` raised by the service |
| Final state reached | `done.state.<state_id>` | (Typically empty) |

#### Accessing data in handlers

```python
def save_result(interpreter, context, event, action_def):
    # event is a DoneEvent when handling onDone
    context["result"] = event.data
```

---

### `AfterEvent(type)`

```python
class AfterEvent(NamedTuple):
    type: str
```

An internal event for delayed (`after`) transitions. Created and sent
automatically by the interpreter when entering a state with `"after"`
configuration. **Users never create this event manually.**

| Field | Type | Description |
|-------|------|-------------|
| `type` | `str` | Internally generated name in the format `"after.<delay>.<machineId>.<stateId>"`. |

#### Format examples

| Config | Generated `AfterEvent.type` |
|--------|---------------------------|
| `"after": {"3000": "timeout"}` on state `pending` in machine `myApp` | `"after.3000.myApp.pending"` |
| `"after": {"500": "retry"}` on state `loading` in machine `fetch` | `"after.500.fetch.loading"` |

---

## Decorators

### `@action` / `@action("name")`

Marks a function as a state machine **action**. Actions are side-effect
functions that run during transitions, on state entry, or on state exit.

```python
@action
def my_action_name(interpreter, context, event, action_def):
    ...

@action("customActionName")
def whatever(interpreter, context, event, action_def):
    ...
```

#### Signature target

```python
(interpreter: BaseInterpreter, context: Dict, event: Event, action_def: ActionDefinition) -> None
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `interpreter` | `Interpreter` or `SyncInterpreter` | The running interpreter instance. |
| `context` | `Dict[str, Any]` | The mutable machine context. Modify this dict to update state data. |
| `event` | `Event` | The event that triggered this action. |
| `action_def` | `ActionDefinition` | The action definition, including `.type` and `.params`. |

#### Auto-naming

When used without arguments (`@action`), the function name is auto-converted
from `snake_case` to `camelCase`:

| Python function name | Registered as |
|---------------------|---------------|
| `increment_counter` | `"incrementCounter"` |
| `log_event` | `"logEvent"` |
| `reset` | `"reset"` |

When used with an explicit name (`@action("myName")`), the provided string is
used exactly as-is.

#### Examples

```python
from xstate_statemachine import action

# Auto-named: registered as "incrementCounter"
@action
def increment_counter(interpreter, context, event, action_def):
    context["count"] += 1

# Explicitly named: registered as "logIt"
@action("logIt")
def my_logger(interpreter, context, event, action_def):
    print(f"Event: {event.type}, Context: {context}")
```

---

### `@guard` / `@guard("name")`

Marks a function as a state machine **guard**. Guards are boolean predicate
functions that control whether a transition is taken. **Guards MUST be
synchronous** -- async guards raise `NotSupportedError` at decoration time.

```python
@guard
def is_valid(context, event):
    return context.get("valid", False)

@guard("canProceed")
def check_proceed(context, event):
    return context["step"] > 0
```

#### Signature target

```python
(context: Dict, event: Event) -> bool
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `context` | `Dict[str, Any]` | The current machine context (read-only by convention). |
| `event` | `Event` | The event being evaluated. |

**Must return:** `bool` -- `True` to allow the transition, `False` to block it.

#### Auto-naming

Same `snake_case` to `camelCase` conversion as `@action`.

#### Examples

```python
from xstate_statemachine import guard

# Auto-named: registered as "hasBalance"
@guard
def has_balance(context, event):
    return context["balance"] > 0

# Explicitly named
@guard("isAdmin")
def check_admin(context, event):
    return event.payload.get("role") == "admin"

# INVALID -- raises NotSupportedError immediately:
# @guard
# async def async_guard(context, event):
#     return True
```

---

### `@service` / `@service("name")`

Marks a function as a state machine **service**. Services are long-running
operations invoked when a state is entered (via the `invoke` config). They
can be synchronous or asynchronous.

```python
@service
def fetch_user(interpreter, context, event):
    return {"name": "Alice", "id": 42}

@service("loadData")
async def load(interpreter, context, event):
    # async services only work with the async Interpreter
    data = await some_api_call()
    return data
```

#### Signature target

```python
(interpreter: BaseInterpreter, context: Dict, event: Event) -> Any
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `interpreter` | `Interpreter` or `SyncInterpreter` | The running interpreter. |
| `context` | `Dict[str, Any]` | The current machine context. |
| `event` | `Event` | A synthetic event with invocation metadata in the payload. |

**Returns:** Any value. The return value becomes the `data` field on the
resulting `DoneEvent`.

#### Auto-naming

Same `snake_case` to `camelCase` conversion as `@action`.

#### Examples

```python
from xstate_statemachine import service

# Auto-named: registered as "fetchData"
@service
def fetch_data(interpreter, context, event):
    import requests
    return requests.get("https://api.example.com/data").json()

# Explicitly named, async
@service("processOrder")
async def process(interpreter, context, event):
    await asyncio.sleep(1)  # simulate work
    return {"status": "processed", "order_id": context["order_id"]}
```

---

## Logic Binding

### `MachineLogic(actions=None, guards=None, services=None)`

```python
class MachineLogic(Generic[TContext, TEvent]):
    def __init__(
        self,
        actions: Optional[Dict[str, Callable[..., Any]]] = None,
        guards: Optional[Dict[str, Callable[..., bool]]] = None,
        services: Optional[Dict[str, Union[Callable[..., Any], MachineNode]]] = None,
    ) -> None: ...
```

A container ("registry") for the implementation logic of a state machine.
Separates the declarative machine definition (JSON) from the imperative
implementation (Python functions).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `actions` | `Dict[str, Callable]` | `{}` | Map of action name to its callable implementation. Signature: `(interpreter, context, event, action_def) -> None`. |
| `guards` | `Dict[str, Callable]` | `{}` | Map of guard name to its callable. Signature: `(context, event) -> bool`. Must be synchronous. |
| `services` | `Dict[str, Union[Callable, MachineNode]]` | `{}` | Map of service name to callable or `MachineNode` (for actor spawning). Service signature: `(interpreter, context, event) -> Any`. |

#### Subclass example

```python
from xstate_statemachine import MachineLogic

class MyLogic(MachineLogic):
    def __init__(self):
        super().__init__(
            actions={
                "logEvent":  self._log_event,
                "increment": self._increment,
            },
            guards={
                "isReady": self._is_ready,
            },
        )

    def _log_event(self, interpreter, context, event, action_def):
        print(f"Event: {event.type}")

    def _increment(self, interpreter, context, event, action_def):
        context["count"] += 1

    @staticmethod
    def _is_ready(context, event):
        return context.get("ready", False)
```

#### Dict-based example

```python
from xstate_statemachine import MachineLogic

logic = MachineLogic(
    actions={
        "increment": lambda i, ctx, e, a: ctx.update({"count": ctx["count"] + 1}),
    },
    guards={
        "isPositive": lambda ctx, e: ctx["count"] > 0,
    },
    services={
        "fetchData": my_fetch_function,
    },
)
```

---

### `LogicLoader`

Singleton class that manages automatic discovery of actions, guards, and
services from Python modules and provider class instances. Implements the
**Convention over Configuration** principle.

#### Singleton access

```python
LogicLoader.get_instance() -> LogicLoader
```

Returns the single shared instance of `LogicLoader`. Creates it on first
call.

#### `register_logic_module(module)`

```python
loader = LogicLoader.get_instance()
loader.register_logic_module(my_module)
```

Registers a Python module for **global** logic discovery. Registered modules
are automatically included in every subsequent `create_machine()` call that
uses auto-discovery. Useful for large applications where logic is spread
across many files.

| Parameter | Type | Description |
|-----------|------|-------------|
| `module` | `ModuleType` | A Python module object to register. |

#### Discovery rules

1. **Underscore prefix ignored**: Functions/methods starting with `_` are
   skipped during discovery.
2. **Auto camelCase conversion**: Every discovered function is registered
   under both its original `snake_case` name *and* its `camelCase` equivalent.
   For example, `increment_counter` is available as both `"increment_counter"`
   and `"incrementCounter"`.
3. **Provider methods override modules**: When the same name appears in both
   a module and a provider instance, the provider's method takes precedence.
4. **Fail-fast**: If a required implementation cannot be found,
   `ImplementationMissingError` is raised immediately.

#### Usage with `create_machine()`

```python
from xstate_statemachine import create_machine, LogicLoader
import my_actions_module

# Option A: Register globally (affects all future create_machine calls)
loader = LogicLoader.get_instance()
loader.register_logic_module(my_actions_module)
machine = create_machine(config)  # auto-discovers from registered modules

# Option B: Pass modules per-call
machine = create_machine(config, logic_modules=[my_actions_module])

# Option C: Pass by import string
machine = create_machine(config, logic_modules=["my_app.actions"])

# Option D: Use provider instances
class MyProvider:
    def increment_counter(self, interpreter, context, event, action_def):
        context["count"] += 1

machine = create_machine(config, logic_providers=[MyProvider()])
```

---

## Machine Inspection

### `MachineNode.get_state_by_id(state_id) -> StateNode | None`

```python
machine.get_state_by_id(state_id: str) -> Optional[StateNode]
```

Finds a state node by its fully qualified ID by traversing the state tree.

| Parameter | Type | Description |
|-----------|------|-------------|
| `state_id` | `str` | The fully qualified state ID, e.g. `"myMachine.parent.child"`. Must start with the machine's root ID. |

**Returns:** The `StateNode` if found, otherwise `None`.

```python
machine = create_machine(config)
node = machine.get_state_by_id("myMachine.active.loading")
if node:
    print(f"Found: {node.id}, type: {node.type}")
```

---

### `MachineNode.get_next_state(from_state_id, event) -> Set[str] | None`

```python
machine.get_next_state(from_state_id: str, event: Event) -> Optional[Set[str]]
```

Calculates the target state(s) for an event **without side effects**. A pure
function intended for **testing** your machine's flow logic. Finds the first
valid transition by bubbling up the state hierarchy.

> **Note:** This utility does **not** evaluate guards. It assumes any guard
> would pass to show the potential transition target.

| Parameter | Type | Description |
|-----------|------|-------------|
| `from_state_id` | `str` | The fully qualified ID of the starting state. |
| `event` | `Event` | The `Event` object to process. |

**Returns:** A `Set[str]` containing the target state ID(s), or `None` if no
transition is found.

```python
from xstate_statemachine import Event

targets = machine.get_next_state("myMachine.idle", Event(type="START"))
assert targets == {"myMachine.running"}
```

---

### `MachineNode.to_plantuml() -> str`

Generates a [PlantUML](https://plantuml.com/) state diagram string from the
machine definition. Useful for auto-generating documentation diagrams.

```python
puml = machine.to_plantuml()
print(puml)
# @startuml
# hide empty description
# state "off" as toggle_off
# state "on" as toggle_on
# [*] --> toggle_off
# toggle_off --> toggle_on : TOGGLE
# toggle_on --> toggle_off : TOGGLE
# @enduml
```

---

### `MachineNode.to_mermaid() -> str`

Generates a [Mermaid.js](https://mermaid.js.org/) state diagram string.
Renders directly in GitHub markdown, MkDocs, and other tools that support
Mermaid.

```python
mmd = machine.to_mermaid()
print(mmd)
# stateDiagram-v2
# [*] --> off
# off --> on : TOGGLE
# on --> off : TOGGLE
```

---

## Exceptions

All exceptions inherit from `XStateMachineError`, enabling broad error
handling with a single `except` clause, or fine-grained handling with
specific exception types.

| Exception | Description | Common trigger |
|-----------|-------------|----------------|
| `XStateMachineError` | Base exception for all library errors. Catch this to handle any library error. | -- |
| `InvalidConfigError` | The machine configuration is structurally invalid. | Missing `"id"` or `"states"` in config; malformed transition; duplicate state names; `final=True` combined with `parallel=True`. |
| `StateNotFoundError` | A target state ID cannot be found in the machine definition. | Transition targets a non-existent state; snapshot restoration with an outdated state ID. |
| `ImplementationMissingError` | A referenced action, guard, or service has no Python implementation. | Config references `"actions": ["doSomething"]` but no function named `doSomething` is provided. |
| `ActorSpawningError` | Error spawning a child actor machine. | Service registered for `spawn_` action is not a valid `MachineNode` or factory function. |
| `NotSupportedError` | An unsupported operation was attempted for the current interpreter mode. | Async action/service used with `SyncInterpreter`; async guard function. |

### `StateNotFoundError` attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `target` | `str` | The state ID that could not be found. |
| `reference_id` | `Optional[str]` | The source state ID from which the lookup was attempted. |

### Exception hierarchy

```
Exception
 +-- XStateMachineError
      +-- InvalidConfigError
      +-- StateNotFoundError
      +-- ImplementationMissingError
      +-- ActorSpawningError
      +-- NotSupportedError
```

### Error handling example

```python
from xstate_statemachine import (
    create_machine,
    SyncInterpreter,
    XStateMachineError,
    InvalidConfigError,
    ImplementationMissingError,
)

try:
    machine = create_machine(config, logic=logic)
    interp = SyncInterpreter(machine).start()
    interp.send("SOME_EVENT")
except InvalidConfigError as e:
    print(f"Config problem: {e}")
except ImplementationMissingError as e:
    print(f"Missing logic: {e}")
except XStateMachineError as e:
    print(f"General machine error: {e}")
```

---

## Plugins

### `PluginBase`

```python
class PluginBase(Generic[TInterpreter]):
    ...
```

Abstract base class for creating interpreter plugins using the **Observer
pattern**. Plugins hook into the interpreter's lifecycle to add cross-cutting
concerns (logging, analytics, persistence) without modifying core interpreter
code.

`PluginBase` is generic over `TInterpreter`, enabling plugins that are
type-safe with a specific interpreter subclass:

```python
from xstate_statemachine import PluginBase, Interpreter

class AsyncOnlyPlugin(PluginBase[Interpreter]):
    def on_event_received(self, interpreter: Interpreter, event):
        # `interpreter` is correctly typed as async Interpreter
        print(f"Event: {event.type}")
```

#### Hook signatures

All hooks have empty default implementations -- override only those you need.

| Hook | Signature | Called when |
|------|-----------|------------|
| `on_interpreter_start` | `(self, interpreter: TInterpreter) -> None` | `start()` begins. |
| `on_interpreter_stop` | `(self, interpreter: TInterpreter) -> None` | `stop()` begins. |
| `on_event_received` | `(self, interpreter: TInterpreter, event: Event) -> None` | An event is passed to the interpreter, before processing. |
| `on_transition` | `(self, interpreter: TInterpreter, from_states: Set[StateNode], to_states: Set[StateNode], transition: TransitionDefinition) -> None` | After a state transition completes (both external and internal). |
| `on_action_execute` | `(self, interpreter: TInterpreter, action: ActionDefinition) -> None` | Right before an action's implementation is executed. |
| `on_guard_evaluated` | `(self, interpreter: TInterpreter, guard_name: str, event: Event, result: bool) -> None` | After a guard condition is evaluated. |
| `on_service_start` | `(self, interpreter: TInterpreter, invocation: InvokeDefinition) -> None` | An invoked service is about to start. |
| `on_service_done` | `(self, interpreter: TInterpreter, invocation: InvokeDefinition, result: Any) -> None` | A service completes successfully. |
| `on_service_error` | `(self, interpreter: TInterpreter, invocation: InvokeDefinition, error: Exception) -> None` | A service fails with an error. |

#### Custom plugin example

```python
from xstate_statemachine import PluginBase, SyncInterpreter

class MetricsPlugin(PluginBase[SyncInterpreter]):
    def __init__(self):
        self.event_count = 0
        self.transition_count = 0

    def on_event_received(self, interpreter, event):
        self.event_count += 1

    def on_transition(self, interpreter, from_states, to_states, transition):
        self.transition_count += 1

    def report(self):
        print(f"Events: {self.event_count}, Transitions: {self.transition_count}")

# Usage
metrics = MetricsPlugin()
interpreter = SyncInterpreter(machine).use(metrics).start()
interpreter.send("GO")
metrics.report()  # Events: 1, Transitions: 1
```

---

### `LoggingInspector`

```python
class LoggingInspector(PluginBase[Any]):
    ...
```

A built-in plugin for detailed, real-time inspection of machine execution.
Works with both `Interpreter` and `SyncInterpreter`. All messages are
emitted through Python's standard `logging` module at `INFO` level.

#### Output format

All log messages are prefixed with a distinctive marker for easy filtering:

| Hook | Log format |
|------|-----------|
| Event received | `🕵️ [INSPECT] Event Received: <type> \| Data: <payload>` |
| External transition | `🕵️ [INSPECT] Transition: [from_ids] -> [to_ids] on Event '<event>'` |
| Internal transition | `🕵️ [INSPECT] Internal transition on Event '<event>'` |
| Context update | `🕵️ [INSPECT] New Context: <context_dict>` |
| Action execute | `🕵️ [INSPECT] Executing Action: <action_type>` |
| Guard evaluated | `🕵️ [INSPECT] Guard '<name>' evaluated for event '<event>' -> ✅ Passed / ❌ Failed` |
| Service start | `🚀 [INSPECT] Service '<src>' (ID: <id>) starting...` |
| Service done | `✅ [INSPECT] Service '<src>' (ID: <id>) completed. Result: <result>` |
| Service error | `❌ [INSPECT] Service '<src>' (ID: <id>) failed. Error: <error>` (with traceback) |

#### Usage

```python
import logging
from xstate_statemachine import SyncInterpreter, LoggingInspector

# Enable logging output
logging.basicConfig(level=logging.INFO)

interpreter = (
    SyncInterpreter(machine)
    .use(LoggingInspector())
    .start()
)

interpreter.send("START")
# Output:
# INFO: 🕵️ [INSPECT] Event Received: START
# INFO: 🕵️ [INSPECT] Executing Action: logStart
# INFO: 🕵️ [INSPECT] Transition: ['myMachine.idle'] -> ['myMachine.running'] on Event 'START'
# INFO: 🕵️ [INSPECT] New Context: {'count': 0}
```

---

## Internal Model Classes

These classes are part of the internal model layer. Users typically interact
with them indirectly, but they appear in plugin hook signatures and
interpreter properties.

### `StateNode`

Represents a single state in the parsed machine graph. Created by
`MachineNode` during config parsing. Implements the Composite design pattern.

| Property | Type | Description |
|----------|------|-------------|
| `.id` | `str` | Fully qualified state ID (e.g. `"myMachine.parent.child"`). |
| `.key` | `str` | Local state name within its parent. |
| `.type` | `str` | One of `"atomic"`, `"compound"`, `"parallel"`, `"final"`. |
| `.parent` | `Optional[StateNode]` | Parent state node, or `None` for the root. |
| `.states` | `Dict[str, StateNode]` | Child states dictionary. |
| `.initial` | `Optional[str]` | Key of the initial child state (compound states only). |
| `.on` | `Dict[str, List[TransitionDefinition]]` | Event-to-transitions mapping. |
| `.entry` | `List[ActionDefinition]` | Entry action definitions. |
| `.exit` | `List[ActionDefinition]` | Exit action definitions. |
| `.is_atomic` | `bool` | `True` if the state has no children. |
| `.is_final` | `bool` | `True` if the state is a final state. |

### `MachineNode`

The root node of a state machine. Extends `StateNode` with machine-wide
utilities. Created by `create_machine()`.

| Attribute | Type | Description |
|-----------|------|-------------|
| `.logic` | `MachineLogic` | The bound logic instance. |
| `.initial_context` | `Dict` | The initial context (deep-copied for each interpreter). |

### `TransitionDefinition`

Represents a parsed transition from the JSON config (internal model).

| Attribute | Type | Description |
|-----------|------|-------------|
| `.event` | `str` | Triggering event name. |
| `.source` | `StateNode` | Source state node. |
| `.target_str` | `Optional[str]` | Target state string (may be `None` for internal transitions). |
| `.actions` | `List[ActionDefinition]` | Actions to execute. |
| `.guard` | `Optional[str]` | Guard name. |
| `.reenter` | `bool` | Whether to re-enter the source state. |

### `InvokeDefinition`

Represents an invoked service within a state.

| Attribute | Type | Description |
|-----------|------|-------------|
| `.id` | `str` | Unique invocation ID. |
| `.src` | `Optional[str]` | Service name from the logic registry. |
| `.input` | `Optional[Dict]` | Static input data. |
| `.on_done` | `List[TransitionDefinition]` | Transitions on success. |
| `.on_error` | `List[TransitionDefinition]` | Transitions on failure. |

---

## Type Aliases

The library defines several callable type aliases for documentation purposes:

| Alias | Signature | Used for |
|-------|-----------|----------|
| `ActionCallable` | `(BaseInterpreter, TContext, Event, ActionDefinition) -> Union[None, Awaitable[None]]` | Action functions |
| `GuardCallable` | `(TContext, Event) -> bool` | Guard functions (sync only) |
| `ServiceCallable` | `(BaseInterpreter, TContext, Event) -> Union[Any, Awaitable[Any]]` | Service functions |

---

## Version

```python
from xstate_statemachine import __version__
print(__version__)  # "0.5.0"
```
