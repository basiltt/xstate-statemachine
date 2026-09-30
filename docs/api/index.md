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

### `create_machine(config, *, context_type=None, logic=None, logic_modules=None, logic_providers=None, strict_targets=True, event_schemas=None, strict_config=None, context_validator=None)`

Creates, validates, and assembles a state machine instance from an
XState-compatible JSON configuration dictionary. This is the **primary
entry point** when working with JSON/dict-based machine definitions.

The function intelligently resolves business logic (actions, guards, services)
from whichever source you provide. If an explicit `MachineLogic` instance is
passed via `logic`, it takes precedence. Otherwise, the factory delegates to
`LogicLoader` to auto-discover implementations from the specified modules or
provider objects.

`create_machine()` also validates the fully built tree: every transition
target must resolve, and no `always` self-target may be a permanent dead end.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `config` | `Dict[str, Any]` | Yes | -- | The machine's structural definition. Must contain top-level `"id"` (non-empty string) and `"states"` keys. Typically loaded from JSON or YAML. |
| `context_type` | `Type[TContext]` | No | `None` | **[wave 3]** Type-only: the class (usually a `TypedDict`) that describes the context shape. The returned `MachineNode[TContext]` carries it to every interpreter, so `interp.context` is typed. No runtime effect. |
| `logic` | `MachineLogic` | No | `None` | A pre-constructed `MachineLogic` instance containing all required actions, guards, and services. When provided, auto-discovery is skipped. |
| `logic_modules` | `List[Union[str, ModuleType]]` | No | `None` | Python modules (or their dotted import-path strings, e.g. `"my_app.logic.actions"`) to scan for logic functions. |
| `logic_providers` | `List[object]` | No | `None` | Class instances whose public methods are scanned to satisfy the machine's logic requirements. Provider methods override module-level functions on name collision. |
| `strict_config` | `Optional[bool]` | No | `None` | **[0.9.0]** (#216, #220) `True` refuses an unrecognised config key — at the root **and in every state, transition and invoke** — with `InvalidConfigError` naming the path (a misspelled `actionErrorPolicyy` / `onUnhandledEvent` / `Strict` otherwise passes a clean build and the policy silently reverts to its permissive default). `None` reads the config's own `strictConfig` key, else `False`: unknown keys are logged at WARNING with a "did you mean" hint. `x-`-prefixed keys and `meta` / `description` / `tags` / `version` are always accepted. |
| `strict_targets` | `bool` | No | `True` | When `True`, an unresolvable transition target raises `InvalidConfigError` at build time. When `False`, it downgrades to a `DeprecationWarning` (0.7.x behavior; removed in 1.0). |
| `event_schemas` | `Optional[Dict[str, Any]]` | No | `None` | Opt-in payload validation. Maps an event type to a validator -- a callable, a dataclass, or anything with a `model_validate`/`parse_obj`-style constructor -- that the event's `payload`/data is passed through before a transition runs. A validation failure raises `InvalidEventPayloadError` (#51). |
| `context_validator` | `Optional[Callable[[Any], None]]` | No | `None` | **[0.11.0]** (#305) A callable that **raises** when the context is invalid. Both engines call it after any action that *changed* `context` (never when nothing changed) and treat a raise as that action's failure, so `actionErrorPolicy` applies: `"rollback"` restores the pre-transition context, `"continue"` keeps the change but reports it (`Receipt.error`, `last_error`, `on_action_error`), `"fail"` stops the machine. The seam the pydantic extra (#266) plugs a model into; core takes no dependency. Non-callable → `InvalidConfigError`. Stored on `MachineNode.context_validator`. |

**Returns:** `MachineNode` -- a fully constructed, validated machine ready for
an interpreter.

**Raises:**

| Exception | Condition |
|-----------|-----------|
| `InvalidConfigError` | `config` is missing `"id"`, `"states"`, or `"id"` is not a non-empty string; a transition target does not resolve (when `strict_targets=True`); an `always` self-target can never make progress; or a built-in action is missing a required `params` key. |
| `ImplementationMissingError` | Auto-discovery is active and a required action, guard, or service cannot be found. |
| `InvalidEventPayloadError` | Raised later, at send-time (not by `create_machine()` itself), when `event_schemas` is set and an incoming event's payload fails its declared schema. Listed here because it is a direct consequence of the `event_schemas` parameter. |

### Machine-level policy keys

These keys go at the root of the JSON `config` (alongside `"id"` and `"states"`). Every one preserves 0.7.x behavior at its default; nothing changes on upgrade unless you opt in.

| Key | Allowed values | Default | Effect |
|-----|-----------------|---------|--------|
| `actionErrorPolicy` | `"continue"` \| `"rollback"` \| `"fail"` | `"continue"` | What happens when an action raises during a transition. `"continue"` emits a one-shot `DeprecationWarning`; flips to `"rollback"` in 1.0. |
| `guardErrorPolicy` | `"false"` \| `"true"` \| `"raise"` | `"false"` | What a raising guard is treated as. |
| `onUnhandled` | `"ignore"` \| `"defer"` \| `"error"` | `"ignore"` | What happens to an event that matches no transition. |
| `strictTargets` | `true` \| `false` | `false` | Disables the sibling-reading fallback for leading-dot (`.child`) targets. |
| `spawnBlockingTimeout` | number (ms) | `30000` | Upper bound a `spawn_blocking_<key>` action waits for the child to reach a terminal status. Never unbounded (a child with no final state would otherwise wedge its parent); on timeout the parent logs a warning and continues (does not raise). |


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

### `build_machine(*, id, states, transitions=None, actions=None, guards=None, services=None, context=None, root=None)`

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
| `root` | `State` | No | `None` | A `State` carrying MACHINE-LEVEL properties: `on`, `always`, `entry`, `exit`, `after`, `invoke`, `on_done`, `tags`, `meta`, and `parallel=True`. Use it for a global escape transition such as `on={"EMERGENCY": "halted"}`, which is live from every state. *Added in v0.7.0.* |
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
    history: Optional[str] = None,
    on: Optional[Dict[str, Any]] = None,
    entry: Optional[List[str]] = None,
    exit: Optional[List[str]] = None,
    after: Optional[Dict[Union[int, str], Any]] = None,
    invoke: Optional[Union[Dict, List]] = None,
    on_done: Optional[Union[str, Dict]] = None,
    always: Optional[Union[str, Dict, List]] = None,
    context: Optional[Dict] = None,
    states: Optional[List[State]] = None,
    tags: Optional[List[str]] = None,
    meta: Optional[Dict[str, Any]] = None,
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
| `history` | `str` | `None` | Marks this as a history pseudo-state. Pass `"shallow"` or `"deep"`. *Added in v0.7.0.* |
| `on` | `Dict[str, Any]` | `None` | Event-to-target shorthand dict, e.g. `{"CLICK": "active"}`. |
| `entry` | `List[str]` | `None` | List of entry action names executed when the state is entered. |
| `exit` | `List[str]` | `None` | List of exit action names executed when the state is exited. |
| `after` | `Dict[int, Any]` | `None` | Delayed transition dict. Keys are milliseconds, values are target strings or transition dicts, e.g. `{3000: "timeout"}`. |
| `invoke` | `Union[Dict, List]` | `None` | Service invocation config. A single dict or list of dicts, each with `"src"`, optional `"onDone"`, `"onError"`. |
| `on_done` | `Union[str, Dict]` | `None` | Completion transition. Fired when all child states in a compound/parallel state reach a final state. |
| `always` | `Union[str, Dict, List]` | `None` | Eventless (transient) transition config. Evaluated immediately after state entry. |
| `context` | `Dict` | `None` | Initial context dict. Only meaningful at the root level. |
| `states` | `List[State]` | `None` | Child `State` objects for building hierarchical/nested machines. |
| `tags` | `List[str]` | `None` | Tags for this state. Query with `interpreter.has_tag(...)` / `.tags`. *Added in v0.7.0.* |
| `meta` | `Dict[str, Any]` | `None` | Arbitrary metadata. Read merged values with `interpreter.get_meta()`. *Added in v0.7.0.* |

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
| `machine_root` | `Optional[State]` | `None` | A `State` carrying MACHINE-LEVEL properties (`on`, `entry`, `exit`, `tags`, `parallel=True`). Give it an empty name. `machine_root` is **reserved** — a state genuinely named `machine_root` raises `InvalidConfigError` rather than being silently dropped. *Added in v0.7.0.* |

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
| `.root(**properties)` | JSON key spellings | `MachineBuilder` | Sets MACHINE-LEVEL properties: `on`, `entry`, `exit`, `after`, `invoke`, `onDone`, `tags`, `meta`, `type="parallel"`. Use for a global escape transition live from every state. Note the JSON spelling `onDone`, not `on_done`. *Added in v0.7.0.* |
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
    history: Optional[str] = None,
    tags: Optional[List[str]] = None,
    meta: Optional[Dict[str, Any]] = None,
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
Interpreter(
    machine: MachineNode,
    input: Optional[Any] = None,
    clock: Optional[Clock] = None,
    max_queue_size: Optional[int] = None,
    overflow_policy: OverflowPolicy = OverflowPolicy.RAISE,
    strict: Optional[bool] = None,
    service_executor: Optional[concurrent.futures.Executor] = None,
    service_pool_size: int = DEFAULT_SERVICE_POOL_SIZE,
)
```

The primary **asynchronous** state machine engine. Processes events from an
`asyncio.Queue`, manages background tasks for `after` timers and `invoke`d
services, and supports spawning child actors. Recommended for I/O-bound
applications (web servers, IoT, automation scripts).

Uses a dedicated `TaskManager` to track all background `asyncio.Task` objects,
ensuring clean cancellation when states are exited.

#### Constructor parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `machine` | `MachineNode` | -- | The machine to run. |
| `input` | `Optional[Any]` | `None` | Creation input for a `context` factory. |
| `clock` | `Optional[Clock]` | `None` | Source of time. Defaults to `RealClock`. Pass a `SimulatedClock` for deterministic virtual-time tests **[wave 3]** (#49). |
| `max_queue_size` | `Optional[int]` | `None` | Bound on the inbox. `None` keeps the unbounded queue; when set, `overflow_policy` decides what a full inbox does to `send()` **[wave 3]** (#38). |
| `overflow_policy` | `OverflowPolicy` | `OverflowPolicy.RAISE` | `RAISE` / `BLOCK` / `DROP_NEWEST`; ignored when no `max_queue_size` is set. The priority lane (`send(priority=True)`) is never bounded **[wave 3]** (#38). |
| `strict` | `Optional[bool]` | `None` | When `True`, an event type not declared anywhere in the machine raises `UnknownEventError` at the `send()` call site instead of silently no-opping **[wave 3]** (#51). |
| `service_executor` | `Optional[concurrent.futures.Executor]` | `None` | **[0.9.0]** (#149) Where a plain (non-coroutine) `invoke` service runs. `None` lazily creates a small `ThreadPoolExecutor` owned by the interpreter and shut down with it; pass a shared / bounded pool or a `ProcessPoolExecutor` for CPU-bound work. The entering macrostep still *awaits* the result — so a plain service's `done.invoke` lands ahead of any event already in the inbox exactly as on the sync engine (#116) — but the event loop is free for the duration. |
| `service_pool_size` | `int` | `DEFAULT_SERVICE_POOL_SIZE` (= 4) | **[0.9.0]** (#173) Worker count of the executor created when `service_executor` is `None`. The (N+1)-th concurrently-running plain service waits for a worker, and because the entering macrostep awaits its result that wait also blocks the macrostep — size it to the number of plain services one configuration can have in flight (a parallel machine with 9 invoking regions wants 9). Ignored when an executor is supplied. Must be ≥ 1. |

#### Methods

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `await .start(*, children_timeout=DEFAULT_CHILDREN_TIMEOUT)` | `(Optional[float]) -> Interpreter` | `Interpreter` | Starts the interpreter and its event loop. Enters the initial state(s), settles `always` transitions, and waits for the initial configuration's invoked child actors to finish their bring-up so they are addressable on return (#171). **[0.9.0]** That wait is bounded by `children_timeout` seconds **per child** (default `DEFAULT_CHILDREN_TIMEOUT` = 2.0; `None` = unbounded) because a child's bring-up runs its entry actions — user code (#181, #194): N children each awaiting D seconds settle in ~D, not N×D. On timeout a WARNING is logged and `start()` returns with the machine running and the child still starting. What the bound *cannot* do is pre-empt a plain-`def` entry action that never yields — it holds the event-loop thread until it returns, like every blocking action in the process — so `start()` returns when it does, and the WARNING still reports the overrun. The initial descent counts as a macrostep: a snapshot from an initial entry action is refused (#182). Returns `self` for chaining. Idempotent. |
| `await .stop(drain=False, timeout=None)` | `(bool, Optional[float]) -> None` | `None` | Gracefully stops the event loop, cancels all tasks and child actors. `drain=True` processes the inbox to empty first, bounded by `timeout` seconds (`None` waits until empty). Idempotent; a no-op on an already-`"done"`/`"stopped"` interpreter. |
| `await .send(event, *, wait=False, priority=False, **payload)` | `(Union[str, Dict, Event, DoneEvent, AfterEvent, ErrorEvent], bool, bool, **Any) -> Optional[Receipt]` | `Optional[Receipt]` | Sends an event to the queue. Accepts a string, dict, or `Event` object. Non-blocking unless `overflow_policy=OverflowPolicy.BLOCK`. `wait=True` **[wave 3]** (#39) makes the returned awaitable resolve to a `Receipt` once the event's macrostep has fully run; `False` (default) resolves immediately to `None`. `priority=True` **[wave 3]** (#39) delivers the event ahead of every already-queued external event and exempts it from `max_queue_size`. Raises `WrongThreadError` when called from a thread other than the one whose event loop owns this interpreter, and `QueueOverflowError` when the inbox is bounded, full, and the policy is `RAISE` **[wave 3]** (#38). |
| `await .send_priority(event, **payload)` | `(Union[str, Dict, Event, DoneEvent, AfterEvent, ErrorEvent], **Any) -> Optional[Receipt]` | `Optional[Receipt]` | Shorthand for `send(event, wait=True, priority=True, **payload)` (#39) -- ask an urgent question and get a `Receipt` back once it settles, jumping ahead of any backlog. Pass `wait=False` for a fire-and-forget priority send. |
| `.send_threadsafe(event, *, internal=None, **payload)` | `(Union[str, Dict, Event, DoneEvent, AfterEvent, ErrorEvent], Optional[bool], **Any) -> concurrent.futures.Future[None]` | `concurrent.futures.Future[None]` | Sends an event from **any** thread by routing the enqueue through the interpreter's owning event loop. Returns a `Future` you may `.result()` on to block until the event is queued (not processed). **[0.9.0]** Under a bounded inbox with `OverflowPolicy.RAISE`, a full inbox raises `QueueOverflowError` **on the calling thread** (#157) — backpressure at the call site, not on a future a fire-and-forget producer never reads. That call-site check is optimistic: a concurrent producer may still be refused **on the loop**, in which case the returned future carries the `QueueOverflowError` *and* — so a fire-and-forget producer's shed rate is never hidden — the interpreter logs a WARNING and fires `on_event_dropped(reason="queue_full")` (#157 reopen). `internal` (#150): `None` classifies the send by context — issued from inside one of this interpreter's own actions (or a thread/executor that inherited that `contextvars` context) it is a self-send charged to `maxIterations`; a plain `threading.Thread` does *not* inherit the context, so an action handing its own re-trigger to one must pass `internal=True` (or start the thread with `contextvars.copy_context().run`). |
| `await .send_events(events)` | `(List[Union[str, Dict, Event]]) -> None` | `None` | Sends a list of events to the queue. Non-blocking. |
| `.matches(state)` | `(Union[str, Dict[str, Any]]) -> bool` | `bool` | Reports whether *state* is part of the active configuration. Accepts a string id (fully-qualified, `#`-prefixed, or trailing partial path) or a partial `.value` dict. |
| `.can(event)` | `(Union[str, Event, Dict[str, Any]]) -> bool` | `bool` | Reports whether sending *event* right now would cause a transition. Guards are evaluated, so this predicts accurately rather than checking structure only; has no side effects. |
| `.has_tag(tag)` | `(str) -> bool` | `bool` | Reports whether any currently active state declares the given tag. |
| `.get_meta()` | `() -> Dict[str, Any]` | `Dict[str, Any]` | Collects the `meta` of every active state, keyed by state id. |
| `.subscribe(listener)` | `(Callable[[BaseInterpreter], None]) -> Callable[[], None]` | `Callable[[], None]` | Registers a listener invoked after every settled change; mirrors XState's `actor.subscribe()`. The listener receives the interpreter itself. Returns an unsubscribe function. |
| `.on(event_type, listener)` | `(str, Callable[[Event], None]) -> Callable[[], None]` | `Callable[[], None]` | Registers a listener for events published via the `emit` action. `event_type` may be `"*"` to catch every emitted event. Returns an unsubscribe function. |
| `.use(plugin)` | `(PluginBase) -> Interpreter` | `Interpreter` | Registers a plugin. Returns `self` for chaining. |
| `.get_snapshot()` | `() -> str` | `str` | Returns a JSON string snapshot of current state, context, and status. |
| `.get_persisted_snapshot()` | `() -> Dict[str, Any]` | `Dict[str, Any]` | Returns a deep, JSON-serialisable snapshot as a dict, including the full actor hierarchy (child actors, history, output) and every accepted-but-unprocessed event, fired timers included (#107). Mirrors XState's `actor.getPersistedSnapshot()`; `get_snapshot()` above is the JSON-string convenience wrapper around this. Raises `SnapshotMidStepError` **[0.9.0]** (#102) if called while a macrostep is in flight (e.g. from inside an action) — snapshot after `send(wait=True)` resolves, from an `on_transition` hook, or after `stop(drain=True)`. Raises `SnapshotSerializationError` **[0.9.0]** (#131) if a pending event carries non-JSON-native data (`Decimal`, `datetime`, …) instead of silently stringifying it. |
| `await .drain_pending()` | `() -> List[Union[Event, DoneEvent, AfterEvent, ErrorEvent]]` | `list` | Removes and returns every accepted-but-unprocessed event from **both** lanes — priority lane first (fired timers, engine completions, `send_priority()`), then the inbox — without processing any. A `wait=True` receipt on a drained event is failed with `InterpreterStoppedError`. **[0.9.1]** Before #239 the priority lane was omitted and then cleared by `stop()`. |
| `await .wait_done()` | `() -> asyncio.Future[str]` | `Future[str]` | Resolves to `"done"`/`"error"` the instant the machine reaches a terminal status. Already-resolved if the machine is terminal now. |
| `.pending_invocations()` | `() -> List[PendingInvocation]` | `list` | Invokes in the active configuration that have NO live service -- the truthful list of what a static `from_snapshot()` restore left dormant **[wave 3]** (#44). Empty on a live machine and after `restart_services=True`. |
| `.clear_chain_error()` | `() -> None` | `None` | **[0.9.0]** Acknowledge the latched `last_chain_error` (#222). `chain_trips` keeps counting. |

#### Class Method

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `Interpreter.from_snapshot(json_str, machine, *, verify_machine_hash=True, restart_services=False, restart_timers=None, clock=None, minimum_version=0, expected_machine_hash=None, plugins=None)` | `(str, MachineNode, bool, bool, Optional[bool], Optional[Clock], int, Optional[str], Optional[Iterable[PluginBase]]) -> Interpreter` | `Interpreter` | **Trust boundary (#205):** a snapshot is trusted input — `state_ids`/`configuration` and `context` are applied verbatim; the shape/identity/drift checks catch corruption and accidental drift, they are *not* authentication (`machine_hash` is a fingerprint, not a MAC). Authenticate a payload that crosses a trust boundary *outside* the library (HMAC/signature over the JSON), and use `minimum_version=1` (refuse version-0 payloads, which carry no hash, with `SnapshotVersionError`) and `expected_machine_hash=<the fingerprint you recorded>` (compared against a value *you* hold, `SnapshotDriftError` on mismatch/absence regardless of version) so the payload cannot choose its own level of checking. Restores an interpreter from a snapshot. Does **not** re-run entry actions, and by default restarts neither services nor timers. Raises `SnapshotVersionError` for a snapshot newer than this library supports, `SnapshotDriftError` on a machine id or structural-hash mismatch (skip the hash check with `verify_machine_hash=False`), and `SnapshotCorruptError` **[0.9.0]** (#110) for a malformed blob (missing key, non-object `context`, unknown `status`, `running` with an empty configuration). `restart_services=True` **[wave 3]** (#44) makes the restored interpreter's `start()` re-invoke every `invoke` in the restored configuration from scratch (not resumed) -- opt in only when the service is safe to run again. `restart_timers` **[0.9.0]** (#128) does the same for dormant `after` timers, re-armed **from zero**; `None` (default) follows `restart_services`. `clock` **[0.9.0]** (#117) is the `Clock` the restored interpreter runs on (default `RealClock`); pass the `SimulatedClock` you mean for deterministic replay. After a static restore `.status` reports the persisted value immediately and is **not a liveness signal** — consult `.has_dormant_invocations` / `.has_dormant_timers` (#135). **`plugins=`** (#230): registered before persisted events are admitted, so a restore-time `strict` / schema refusal reaches `on_invalid_event`; without it the refusal is visible only on `last_error`. Restored `scheduled_sends` are checked too (#227); the priority lane restores as a lane on both engines (#233). |

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `.current_state_ids` | `Set[str]` | Set of fully qualified IDs of all currently active atomic/final states. |
| `.active_state_ids` | `Set[str]` | Alias of `.current_state_ids`, kept for compatibility with docs/README examples that predate the canonical name. |
| `.context` | `Dict[str, Any]` | The mutable machine context. Changes made to this dict persist across transitions. |
| `.status` | `str` | One of `"uninitialized"`, `"running"`, `"done"`, `"error"`, or `"stopped"`. |
| `.is_running` | `bool` | `True` between a successful `start()` and a `stop()`; a convenience wrapper over `.status == "running"`. |
| `.id` | `str` | The interpreter's identifier (inherited from machine ID). |
| `.parent` | `Optional[BaseInterpreter]` | Reference to parent interpreter (for spawned child actors), otherwise `None`. |
| `.system` | `ActorSystem` | The actor system this interpreter belongs to; exposes `.get(id)` and `.get_all()` for looking up sibling/child actors registered under a `systemId`. |
| `.task_manager` | `TaskManager` | **Async only.** The registry of `asyncio.Task`s the interpreter owns, grouped by owner (a state id for its services and `after` timers), so exiting a state cancels exactly its tasks and `stop()` leaves nothing orphaned. Read-only for callers; useful in tests to assert nothing is left running. |
| `.plugins` | `List[PluginBase]` | The list of plugin instances attached to this interpreter. Assigning a new list replaces the whole set (the form `.use()` builds on). |
| `.last_transition_ok` | `bool` | Whether the most recently processed transition's actions all ran to completion, given `actionErrorPolicy`. Also `False` after a settle-budget trip (#112) or a `sendTo` with no live target (#133). |
| `.last_error` | `Optional[BaseException]` | The exception behind the most recent `last_transition_ok=False` — an action's exception, a `RunawayChainError`, an `ActorSpawningError` for an unresolved `sendTo` — or `None`. A **per-step read, not a latch**: the next cleanly handled event clears it (#222). For "has this machine ever cut work?" use `chain_trips` / `last_chain_error`. |
| `.chain_trips` | `int` | **[0.9.0]** Monotonic count of chain-budget and settle-budget trips (#222). Never resets — a snapshot field since #226, so it stays monotonic across a restart too; a supervisor samples it at any interval and diffs. |
| `.last_chain_error` | `Optional[BaseException]` | **[0.9.0]** The `RunawayChainError` of the most recent trip, latched: it survives every later event and a snapshot round-trip (restored as a `RestoredError`, #226), and is cleared only by `.clear_chain_error()` (#222). |
| `.last_plugin_error` | `Optional[Tuple[str, str, BaseException]]` | **[0.9.0]** `(plugin_class_name, hook_name, error)` for the most recent plugin hook that raised or was an un-awaitable `async def` (#127). Plugin failures never stop the machine; this is where they surface, alongside `on_plugin_error`. |
| `.has_dormant_invocations` | `bool` | **[wave 3]** `True` when an active state declares an `invoke` that has no live service — the state of a static `from_snapshot()` restore before `start()`, or after it without `restart_services=True` (#44). |
| `.has_dormant_timers` | `bool` | **[0.9.0]** `True` when an active state declares an `after` timer that is not armed — the timer counterpart of `has_dormant_invocations`; cleared by `start()` with `restart_timers=True` (#128). |
| `.deferred_count` | `int` | Number of events currently buffered under `onUnhandled: "defer"`. |
| `.dropped_receipts` | `int` | **[0.9.1]** How many `send(wait=True)` receipts issued from inside an action were dropped without being awaited or handed out (#244). The deterministic form of the #232 `RuntimeWarning`; async engine only. |
| `.restored_from_snapshot` | `bool` | **[0.9.1]** `True` if this instance was built by `from_snapshot()` (#240). Read it in `on_interpreter_start` to tell bring-up from resume. |
| `Interpreter.DEFER_MAX` | `int` | Class attribute bounding the deferral buffer's size; oldest entries are evicted once full. |
| `Interpreter.MAX_ACTION_DEPTH` | `int` | Class attribute (default `50`) bounding nested action expansion (`pure` / `choose` / `enqueueActions` returning further actions), guarding against a callback that re-enqueues itself. |
| `.value` | `str \| Dict[str, Any]` | The active configuration in hierarchical form: a string for an atomic state, `{parent: child}` for compound, one key per region for parallel, `{}` before `start()`. |
| `.pending_events` | `Sequence[Union[Event, DoneEvent, AfterEvent, ErrorEvent]]` | Events accepted by `send()` but not yet processed, FIFO order. |
| `.queue_depth` | `int` | Number of events accepted but not yet processed; `len(.pending_events)`. Read-only. |
| `.tags` | `Set[str]` | The union of tags across every currently active state. |

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
SyncInterpreter(
    machine: MachineNode,
    input: Optional[Any] = None,
    clock: Optional[Clock] = None,
    strict: Optional[bool] = None,
    max_queue_size: Optional[int] = None,   # parity only; non-None raises ValueError (#245)
    overflow_policy: Optional[OverflowPolicy] = None,
)
```

A fully **synchronous** interpreter that processes events immediately within
the `send()` call. Suitable for CLI tools, desktop GUI event loops, simple
workflows, and predictable testing scenarios.

Events are handled one at a time from an internal `collections.deque`,
ensuring sequential, blocking execution. `after` timers are scheduled on the
injected `Clock` (thread-free; #49/#50) rather than a background thread.

#### Constructor parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `machine` | `MachineNode` | -- | The state machine definition to run. |
| `input` | `Optional[Any]` | `None` | Creation input for a `context` factory. |
| `clock` | `Optional[Clock]` | `None` | Source of time. Defaults to `RealClock`, whose sync-side timers are a thread-free deadline list drained by `.tick()` / `.send()` **[wave 3]** (#49, #50). Pass a `SimulatedClock` for deterministic virtual-time tests. |
| `strict` | `Optional[bool]` | `None` | When `True`, an event type not declared anywhere in the machine raises `UnknownEventError` at the `send()` call site **[wave 3]** (#51). |
| `max_queue_size` / `overflow_policy` | `Optional[int]` / `Optional[OverflowPolicy]` | `None` | **[0.9.1]** Accepted for signature parity with `Interpreter` (#245). The sync engine has **no inbox bound by design**: `send()` runs each event to completion on the caller's thread before returning, so there is no backlog to cap. A non-`None` `max_queue_size` raises `ValueError`; a sync caller under bursty or untrusted input applies admission control in its own wrapper around `send()`. |

#### Methods

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `.start()` | `() -> SyncInterpreter` | `SyncInterpreter` | Starts the interpreter and enters the initial state(s). Returns `self` for chaining. Idempotent. |
| `.stop(drain=False, timeout=None)` | `(bool, Optional[float]) -> None` | `None` | Stops the interpreter, cancels timers, stops child actors. `drain=True` processes the inbox to empty first. Idempotent; a no-op on an already-`"done"`/`"stopped"` interpreter. |
| `.send(event, *, wait=False, priority=False, **payload)` | `(Union[str, Dict, Event, DoneEvent, AfterEvent, ErrorEvent], bool, bool, **Any) -> Optional[Receipt]` | `Optional[Receipt]` | Sends an event for **immediate** synchronous processing. Blocks until the event and all resulting transitions are fully processed. `wait=True` **[wave 3]** (#39) returns a `Receipt` for API symmetry with the async engine's `send(wait=True)` (the sync engine already processes inline by the time `send()` returns). `priority` is accepted for signature symmetry but has no effect -- there is no backlog to jump. |
| `.send_events(events)` | `(List[Union[str, Dict, Event]]) -> None` | `None` | Sends a list of events for immediate processing. |
| `.send_threadsafe(event, **payload)` | `(Union[str, Dict, Event, Any], **Any) -> None` | `None` | **[0.11.0]** (#305) Queue an event from **any thread**. `send()` is not thread-safe (it processes on the caller's thread with no lock); this is the only legal cross-thread entry to a sync machine. The event is normalised on the sender's thread (a malformed one raises `InvalidEventError` there) and put in a locked mailbox; the thread that **owns** the machine delivers it — as its own macrostep, with the same `strict` / `event_schemas` / `on_before_send` checks — the next time it calls `send()` or `tick()`, *ahead* of its own event. FIFO per sending thread; nothing lost; no receipt (nothing runs on the caller). An admission refusal at drain time surfaces on the owner as `on_event_dropped(…, "invalid")` + `last_error`, never as an exception on a thread that has moved on. |
| `.matches(state)` | `(Union[str, Dict[str, Any]]) -> bool` | `bool` | Reports whether *state* is part of the active configuration. Accepts a string id or a partial `.value` dict. |
| `.can(event)` | `(Union[str, Event, Dict[str, Any]]) -> bool` | `bool` | Reports whether sending *event* right now would cause a transition, per `Interpreter.can()` above. |
| `.has_tag(tag)` | `(str) -> bool` | `bool` | Reports whether any currently active state declares the given tag. |
| `.get_meta()` | `() -> Dict[str, Any]` | `Dict[str, Any]` | Collects the `meta` of every active state, keyed by state id. |
| `.subscribe(listener)` | `(Callable[[BaseInterpreter], None]) -> Callable[[], None]` | `Callable[[], None]` | Registers a listener invoked after every settled change. Returns an unsubscribe function. |
| `.on(event_type, listener)` | `(str, Callable[[Event], None]) -> Callable[[], None]` | `Callable[[], None]` | Registers a listener for events published via the `emit` action; `"*"` catches every emitted event. Returns an unsubscribe function. |
| `.use(plugin)` | `(PluginBase) -> SyncInterpreter` | `SyncInterpreter` | Registers a plugin. Returns `self` for chaining. |
| `.get_snapshot()` | `() -> str` | `str` | Returns a JSON string snapshot. |
| `.get_persisted_snapshot()` | `() -> Dict[str, Any]` | `Dict[str, Any]` | Returns a deep, JSON-serialisable snapshot as a dict, including the full actor hierarchy, per `Interpreter.get_persisted_snapshot()` above. |
| `.drain_pending()` | `() -> List[Union[Event, DoneEvent, AfterEvent, ErrorEvent]]` | `list` | Removes and returns every accepted-but-unprocessed event, without processing it. |
| `.pending_invocations()` | `() -> List[PendingInvocation]` | `list` | Invokes in the active configuration that have NO live service, per `Interpreter.pending_invocations()` above **[wave 3]** (#44). |
| `.pending_deadlines()` | `() -> List[Deadline]` | `list` | **[0.11.0]** (#264) Every armed `after` timer as a wall-clock `Deadline` (soonest first) — what the snapshot's `deadlines` key holds. Both engines. |
| `.clear_chain_error()` | `() -> None` | `None` | **[0.9.0]** Per `Interpreter.clear_chain_error()` (#222). |

#### Class Method

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `SyncInterpreter.from_snapshot(json_str, machine, *, verify_machine_hash=True, restart_services=False, restart_timers=None, clock=None, minimum_version=0, expected_machine_hash=None, plugins=None, on_version_mismatch=None, migrator=None)` | `(str, MachineNode, bool, bool, Optional[bool], Optional[Clock], int, Optional[str], Optional[Iterable[PluginBase]], Optional[str], Optional[SnapshotMigrator]) -> SyncInterpreter` | `SyncInterpreter` | Restores an interpreter from a snapshot. Raises `SnapshotVersionError`/`SnapshotDriftError` as described for `Interpreter.from_snapshot` above. **[0.11.0]** `on_version_mismatch` (`"error"` default · `"warn"` · `"migrate"`) and `migrator` (#263) apply the chart-version label check; see `SnapshotMigrator`. `restart_services=True` **[wave 3]** (#44) re-invokes every dormant `invoke` from scratch when the restored interpreter starts. `restart_timers` **[0.11.0]** (#264) is `False` · `True`/`"restart"` (from zero) · `"resume"` (remaining wall time from the persisted deadlines) · `"fire_due"` (resume + fire matured ones during `start()`). |

#### Properties

Same as `Interpreter`:

| Property | Type | Description |
|----------|------|-------------|
| `.current_state_ids` | `Set[str]` | Active atomic/final state IDs. |
| `.active_state_ids` | `Set[str]` | Alias of `.current_state_ids`, per `Interpreter.active_state_ids` above. |
| `.context` | `Dict[str, Any]` | Mutable machine context. |
| `.status` | `str` | `"uninitialized"`, `"running"`, `"done"`, `"error"`, or `"stopped"`. |
| `.is_running` | `bool` | `True` between a successful `start()` and a `stop()`. |
| `.id` | `str` | Interpreter identifier. |
| `.parent` | `Optional[BaseInterpreter]` | Parent interpreter reference. |
| `.system` | `ActorSystem` | The actor system this interpreter belongs to, per `Interpreter.system` above. |
| `.plugins` | `List[PluginBase]` | The list of plugin instances attached to this interpreter. |
| `.value` | `str \| Dict[str, Any]` | The active configuration in hierarchical form. |
| `.pending_events` | `Sequence[Union[Event, DoneEvent, AfterEvent, ErrorEvent]]` | Events accepted but not yet processed. |
| `.queue_depth` | `int` | Number of events accepted but not yet processed. Read-only. |
| `.tags` | `Set[str]` | The union of tags across every currently active state. |

#### Sync limitations

| Feature | Supported? | Notes |
|---------|-----------|-------|
| `after` timers | Yes | Scheduled on the injected `Clock` (no background thread; #49/#50). Fires event when delay elapses. |
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

## Clock **[wave 3]**

Time as an injectable dependency (#48, #49, #50). A `Clock` schedules
**callbacks**; the interpreter decides what a fired callback means. The same
`Clock` object may serve both engines at once, so a parent and its invoked
children (which may be either engine) share one timeline.

### `Clock` (Protocol)

```python
@runtime_checkable
class Clock(Protocol):
    def now(self) -> float: ...
    def set_timeout(self, fn, delay_sec: float, *, owner: Any = None, sync: bool | None = None) -> Any: ...
    def clear_timeout(self, handle: Any) -> None: ...
    def pump(self) -> int: ...
```

| Method | Signature | Description |
|--------|-----------|-------------|
| `.now()` | `() -> float` | Current time in seconds (monotonic; origin is clock-specific). |
| `.set_timeout(fn, delay_sec, *, owner=None, sync=None)` | `(Callable[[], Any], float, Any, bool \| None) -> Any` | Schedule `fn` after `delay_sec`; returns a cancellation handle. Engines pass `sync=True` (`SyncInterpreter`) or `sync=False` (`Interpreter`) so the clock picks the lane the caller can drain (0.9.0, #76); `RealClock` falls back to the ambient-loop heuristic when `sync` is `None`. A clock written against the 0.8.0 protocol (no `sync` parameter) is still accepted — the engine retries without it. |
| `.clear_timeout(handle)` | `(Any) -> None` | Cancel a scheduled callback. Idempotent. |
| `.pump()` | `() -> int` | Run every callback whose deadline has passed; returns how many fired. |
| `.wall_now()` *(optional, 0.11.0)* | `() -> float` | Seconds since the Unix epoch. Not part of the protocol a custom clock **must** provide; `interpreter.wall_now()` uses it when present and falls back to `time.time()`. Durable timers (#264) and audit rows (#262) anchor to this, never to `.now()`, whose origin is process-specific (#305). |

### `RealClock()`

Wall-clock time and the default for both engines when no `clock` is passed to
`Interpreter`/`SyncInterpreter`. Inside a running asyncio loop, a timeout is
`loop.call_later` (the same primitive `asyncio.sleep` uses). Outside a loop
(the sync engine), a timeout is a record in a deadline heap and no thread is
started -- due callbacks run when `SyncInterpreter.send()` / `.tick()` calls
`.pump()`.

| Property | Type | Description |
|----------|------|-------------|
| `.pending` | `int` | Deadlines waiting in the heap (sync-engine timers only). |
| `.wall_now()` | `float` | `time.time()` (#305). |

### `SimulatedClock(*, wall_start=None)`

Virtual time for deterministic tests, mirroring XState's `SimulatedClock`.
Time does not pass on its own -- `.increment()` advances virtual time and
fires every timer that became due, in due order.

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `.increment(ms)` | `(float) -> Union[None, Awaitable[None]]` | `None` or an awaitable | Advances virtual time by `ms` milliseconds and fires what became due, one timer at a time (so an `after` chain scheduled inside the same window fires in order). Returns an **awaitable** when called inside a running event loop (`await clock.increment(ms)`) and `None` otherwise; a forgotten `await` inside a loop raises a `RuntimeWarning` at garbage-collection time instead of silently racing. |
| `.set(ms)` | `(float) -> Union[None, Awaitable[None]]` | Same as `.increment()` | Jumps to absolute virtual time `ms`; raises `ValueError` if that would move backwards. |
| `.pending` | `int` | -- | Property: number of live (uncancelled) timers. |
| `.wall_now()` | `() -> float` | `float` | `wall_start + elapsed virtual seconds` (#305). `wall_start` defaults to the real epoch instant the clock was built; pass an explicit one to express *"the process restarted an hour later"*: `SimulatedClock(wall_start=1_000_000.0)` then `.increment(3_600_000)` → `.wall_now() == 1_003_600.0` while `.now()` is still `3600.0`. |

```python
from xstate_statemachine import Interpreter, SyncInterpreter, SimulatedClock

# Sync engine
clock = SimulatedClock()
interp = SyncInterpreter(machine, clock=clock).start()
clock.increment(30_000)   # fires a 30s `after` transition synchronously

# Async engine
async def main():
    clock = SimulatedClock()
    service = await Interpreter(machine, clock=clock).start()
    await clock.increment(30_000)   # fires the 30s `after`, settles the loop
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

### The `__xstate_event__` adapter protocol **[0.11.0]**

Any object can say how it becomes an event by implementing `__xstate_event__(self) -> str | dict | Event` — the way `__fspath__` lets any object be a path (#305). Every send path on both engines (`send`, `send_events`, `send_threadsafe`, `sendTo` specs, `can()`) normalises through one function, so the adapter works everywhere a `str` / `dict` / `Event` does. The result is normalised by the **same rules** as a direct argument (one level: an adapter returning another adapter is `InvalidEventError`, not a recursion). Keyword payload merges *over* an adapter's dict, so a call site can annotate: `interp.send(order, source="retry")`. Native `Event` / `DoneEvent` / `AfterEvent` / `ErrorEvent` instances are never adapted, even if a subclass defines the method.

```python
from xstate_statemachine import SyncInterpreter, create_machine, MachineLogic

class OrderPlaced:
    def __init__(self, order_id: int) -> None:
        self.order_id = order_id
    def __xstate_event__(self) -> dict:
        return {"type": "PLACE", "order_id": self.order_id}

cfg = {"id": "shop", "initial": "idle", "context": {},
       "states": {"idle": {"on": {"PLACE": {"target": "placed", "actions": "remember"}}},
                  "placed": {}}}
def remember(i, ctx, e, a):
    ctx["order_id"] = e.payload["order_id"]

interp = SyncInterpreter(create_machine(cfg, logic=MachineLogic(actions={"remember": remember}))).start()
interp.send(OrderPlaced(42))            # no translation at the call site
assert interp.context["order_id"] == 42 and interp.matches("shop.placed")
```

### `DoneEvent(type, data, src)`

```python
class DoneEvent(NamedTuple):
    type: str
    data: Any
    src: str
```

> **Provenance (#195).** Only a `DoneEvent` the *engine* minted is a completion. One you construct yourself is an ordinary user event with an engine-shaped name: under `strict=True` it is refused (`UnknownEventError`, "engine-generated name"), otherwise it reaches `onUnhandled` like any undeclared event. It never drives `onDone`. The same holds for `ErrorEvent` and `AfterEvent`.

An internal **success** event generated by the interpreter when:

1. An `invoke`d service completes successfully (`done.invoke.<service_id>`).
2. A compound/parallel state reaches its final state (`done.state.<state_id>`).

Failures are delivered as an [`ErrorEvent`](#erroreventtype-error-src) since 0.9.0 (#80).

| Field | Type | Description |
|-------|------|-------------|
| `type` | `str` | `"done.invoke.<id>"` or `"done.state.<id>"`. |
| `data` | `Any` | The service's return value, the child actor's final context, or a final state's `output`. |
| `src` | `str` | The unique identifier of the service or state that generated this event. |

#### Accessing data in handlers

```python
def save_result(interpreter, context, event, action_def):
    # event is a DoneEvent when handling onDone
    context["result"] = event.data
```

---

### `ErrorEvent(type, error, src)` **[0.9.0]**

```python
class ErrorEvent(NamedTuple):
    type: str
    error: BaseException
    src: str
```

Delivered when an `invoke`d service raises, a child actor's bring-up fails, or a child machine ends in the `error` status (#80). A distinct type from `DoneEvent`, so `onError` handlers branch on `isinstance(event, ErrorEvent)` or read `event.error` instead of string-prefixing `event.type` — the shape XState v5 uses for `xstate.error.actor.*`.

| Field | Type | Description |
|-------|------|-------------|
| `type` | `str` | `"error.platform.<invocation_id>"` (v4 naming, kept for config compatibility). |
| `error` | `BaseException` | The exception the service or child raised. |
| `src` | `str` | The `id` of the invoke that failed. |

`event.data` still returns `error` with a `DeprecationWarning` so 0.8.0-era `onError` actions keep working; it is removed in 0.9.

```python
from xstate_statemachine import ErrorEvent

def store_error(interpreter, context, event, action_def):
    assert isinstance(event, ErrorEvent)
    context["error"] = str(event.error)
```

---

### `AfterEvent(type, scheduled_for=0.0, fired_at=0.0)`

```python
class AfterEvent(NamedTuple):
    type: str
    scheduled_for: float = 0.0   # clock time the deadline was set for
    fired_at: float = 0.0        # clock time the timer actually fired

    @property
    def lateness_ms(self) -> float: ...
```

An internal event for delayed (`after`) transitions. Created and sent
automatically by the interpreter when entering a state with `"after"`
configuration. **Users never create this event manually.**

| Field | Type | Description |
|-------|------|-------------|
| `type` | `str` | Internally generated name in the format `"after.<delay>.<machineId>.<stateId>"`. |
| `scheduled_for` | `float` | The `Clock` reading the deadline was armed for. |
| `fired_at` | `float` | The `Clock` reading when it actually fired. |
| `lateness_ms` | `float` (property) | `max(0, fired_at - scheduled_for) * 1000` — how late the timer ran, the figure behind [Production Characteristics § 2](../guide/production-characteristics/#2-after-timers-are-best-effort-and-starve-under-load). Both timestamps survive a snapshot round-trip (#118). |

#### Format examples

| Config | Generated `AfterEvent.type` |
|--------|---------------------------|
| `"after": {"3000": "timeout"}` on state `pending` in machine `myApp` | `"after.3000.myApp.pending"` |
| `"after": {"500": "retry"}` on state `loading` in machine `fetch` | `"after.500.fetch.loading"` |

---

### Engine provenance: `is_system_event`, `system_event`, `ENGINE_EVENT_SHAPES` **[0.9.0]**

```python
def is_system_event(event: Any) -> bool: ...
def system_event(event_type: str, **payload: Any) -> Event: ...

ENGINE_EVENT_SHAPES: Tuple[str, ...]   # ("done.invoke.", "done.state.", "error.platform.", "after.", "xstate.", "___xstate")
SYSTEM_EVENT_PREFIXES: Tuple[str, ...]  # coarser legacy prefixes, kept for compatibility
```

Three behaviours — wildcard matching (`"*"` / `"prefix.*"`), `onUnhandled: "error"` / `"defer"`, and `strict=True` — treat events *minted by the engine* differently from yours. Since 0.9.0 (#79, #137) that decision is made by **provenance**, not by name — and, since #195, not by *type* either: `is_system_event` is the single predicate all three consult, and `system_event(...)` is the only way to mint a plain `Event` that satisfies it. A `DoneEvent` / `ErrorEvent` / `AfterEvent` **you construct by hand is user traffic**: it does not drive `onDone` / `onError` / `after`, `strict` refuses it as an engine-generated name, and `onUnhandled` applies. The engine mints its own completions through private subclasses (identical to the public class under `isinstance`, equality, `_replace`, pickle and `deepcopy`); a persisted engine completion round-trips through `persist_event` / `restore_event` with its provenance intact (`"engine": true` on the record), while a hand-written record restores as user traffic. An event you name `done.review` is user traffic. The marker survives `deepcopy`, `pickle`, `send(wait=True)` and a snapshot round-trip (#111, #138). `ENGINE_EVENT_SHAPES` lists the name shapes the engine produces, for build-time checks and documentation only.

```python
from xstate_statemachine import Event, is_system_event, system_event

is_system_event(Event("done.review"))                            # False
is_system_event(system_event("___xstate_statemachine_init___"))  # True
```

#### `re_mint(original, **fields)` **[0.9.1]**

```python
def re_mint(original: DoneEvent | ErrorEvent | AfterEvent, **fields: Any) -> DoneEvent | ErrorEvent | AfterEvent: ...
```

The sanctioned way to change a field of an **engine-minted** event and keep its provenance (#248). `_replace()` on an engine event deliberately returns the public class (#235) — a caller-chosen variant is user traffic — which left no route for the legitimate case: a plugin that redacts `data` before re-emitting a completion. `re_mint` is safe because it is gated on the *input*: `original` must already satisfy `is_system_event`, so provenance can only be carried forward from an event the engine produced, never created. A hand-built event, a plain `Event`, or a `_replace()`-demoted value raises `TypeError`. The original is untouched.

```python
from xstate_statemachine import re_mint, is_system_event

def on_event_received(self, interp, event):
    if event.type.startswith("done.invoke."):
        safe = re_mint(event, data={"redacted": True})
        assert is_system_event(safe)
```

#### `event_kind`, `persist_event`, `restore_event` (module `xstate_statemachine.events`)

The record format a snapshot uses for one pending / deferred / scheduled event. Importable for tooling that reads or rewrites journals; the engine's own `get_persisted_snapshot()` / `from_snapshot()` go through them.

| Function | Signature | Description |
|:--|:--|:--|
| `event_kind(event)` | `(Any) -> str` | The discriminator persisted with an event: `"event"` (user traffic), `"system"` (an engine-minted plain `Event`), `"done"` / `"error"` / `"after"` (the NamedTuple engine events). |
| `persist_event(event, *, lane=None)` | `(Any, Optional[str]) -> Dict[str, Any]` | JSON-safe record: `kind`, `type`, `payload` / `data` / `error` / `src` / `scheduled_for` / `fired_at` as the kind requires, `"engine": true` when the event is engine-minted (#195), and `lane` (`"priority"` or absent, #214). Raises `SnapshotSerializationError` for non-JSON-native data. |
| `restore_event(record)` | `(Dict[str, Any]) -> Any` | Inverse of `persist_event`. Provenance comes from the record's `engine` flag (v3) — a hand-written record without it restores as user traffic; a v2 `done` / `error` / `after` record is trusted because only the engine could have written one (#214). |

---

### `Receipt(state_ids, changed, error=None, deferred=False, denied=False, duplicate=False)` **[wave 3, 0.9.0]**

```python
class Receipt(NamedTuple):
    state_ids: FrozenSet[str]
    changed: bool
    error: Optional[BaseException] = None
    deferred: bool = False
    denied: bool = False
    duplicate: bool = False
```

What `send(..., wait=True)` resolves to once the event's macrostep has run to
completion (#39).

| Field | Type | Description |
|-------|------|-------------|
| `state_ids` | `FrozenSet[str]` | The active leaf ids the instant processing finished. |
| `changed` | `bool` | `True` if a transition was taken (configuration or context changed) for THIS event. |
| `error` | `Optional[BaseException]` | The exception raised while processing this event -- an action that raised, an unresolvable target, a `sendTo` with no live target -- or `None`. The machine may still be `"running"` (per `actionErrorPolicy`); the receipt tells the caller its request did not run cleanly. |
| `deferred` | `bool` | **[0.9.0]** `True` when this event selected no transition and was parked under `onUnhandled: "defer"` (#84). It will be replayed, as its own macrostep, after the next event that changes the configuration; the replay does not fold into that event's receipt (#125, both engines). |
| `denied` | `bool` | **[0.9.0]** `True` when the active state *declared* a handler for this event but every candidate's guard returned `False` (#153). Distinguishes "a business rule refused it" from "this event does not apply here" (`denied=False`, `changed=False`), which are otherwise identical receipts. A guard that *crashed* under `guardErrorPolicy: "raise"` is a third case: `denied=False` and `error` carries the exception (#170). `(denied, error is None)` therefore discriminates all three. Note that under `onUnhandled: "defer"` a denied event enters the defer buffer (`deferred=True` too) and is re-evaluated after the next state change. |
| `duplicate` | `bool` | **[0.11.0]** `True` when a plugin short-circuited the send from `on_before_send` because it had already seen this event (the idempotency inbox, #261/#304). The other fields then describe the *original* delivery's outcome, so a redelivered webhook gets the same answer the first delivery did. Appended last, so positional unpacking of the five older fields still works. |

> ⚠️ **Arity changes.** `Receipt` grew from three fields to five in 0.9.0 (`deferred`, then `denied`) and to six in 0.11.0 (`duplicate`). A positional destructure written for an older width raises `ValueError`; read fields by attribute (#119, #153, #304).

```python
receipt = await interpreter.send("SUBMIT", wait=True)
if receipt.error is not None:
    print(f"SUBMIT did not run cleanly: {receipt.error}")
```

---

### `OverflowPolicy` **[wave 3]**

```python
class OverflowPolicy(str, Enum):
    RAISE = "raise"
    BLOCK = "block"
    DROP_NEWEST = "drop_newest"
```

What `send()` does when a bounded inbox (`max_queue_size` on `Interpreter`) is
full (#38).

| Member | Value | Behavior |
|--------|-------|----------|
| `OverflowPolicy.RAISE` | `"raise"` | Default once `max_queue_size` is set. `send()` raises `QueueOverflowError`; the gateway sheds load and alarms. |
| `OverflowPolicy.BLOCK` | `"block"` | `await send()` suspends until the consumer frees a slot. For trusted in-process producers that can be slowed. |
| `OverflowPolicy.DROP_NEWEST` | `"drop_newest"` | The incoming event is discarded with a WARNING log and `PluginBase.on_event_dropped`. The only policy that can lose an event; never the default. For telemetry where staleness beats backlog. |

`OverflowPolicy` is a `str` subclass, so plain strings (`"raise"`, `"block"`,
`"drop_newest"`) are also accepted anywhere it is expected.

```python
from xstate_statemachine import Interpreter, OverflowPolicy

service = await Interpreter(
    machine, max_queue_size=1000, overflow_policy=OverflowPolicy.DROP_NEWEST
).start()
```

---

### `PendingInvocation(state_id, invoke_id, src)` **[wave 3]**

```python
class PendingInvocation(NamedTuple):
    state_id: str
    invoke_id: str
    src: str
```

An `invoke` that is part of the active configuration but has no live task --
what `.pending_invocations()` returns (#44).

| Field | Type | Description |
|-------|------|-------------|
| `state_id` | `str` | The state that owns the invoke. |
| `invoke_id` | `str` | The invoke's id (explicit, or the parser default). |
| `src` | `str` | The service key. |

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
class MachineLogic(Generic[TContext]):
    def __init__(
        self,
        actions: Optional[Mapping[str, ActionCallable]] = None,
        guards: Optional[Mapping[str, GuardCallable]] = None,
        services: Optional[Mapping[str, Union[ServiceCallable, MachineNode]]] = None,
        delays: Optional[Mapping[str, Union[int, float, DelayCallable]]] = None,
    ) -> None: ...

# The callable blueprints pin ARITY and the guard's bool return:
ActionCallable  = Callable[[Any, Any, Any, ActionDefinition], Union[None, Awaitable[None]]]
GuardCallable   = Callable[[Any, Any], bool]
ServiceCallable = Callable[[Any, Any, Any], Any]
DelayCallable   = Callable[[Any, Any], Union[int, float]]
```

**[wave 3]** A two-argument action or a guard returning `str` is now a type
error at the `MachineLogic(...)` call. The interpreter/context/event slots are
`Any` on purpose: annotate them as narrowly as you like on your own functions
(`interp: SyncInterpreter[MyCtx]`) and they still fit.

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

### `MachineNode.version` **[0.11.0]**

`Optional[str]` — the chart's own `"version"` label from the root of the config, coerced to `str`; `None` when the chart declares none. Before 0.11.0 the key was accepted and silently ignored (#305). It is **not** part of `structure_hash` — re-labelling a chart does not invalidate stored snapshots — and is written to every snapshot as `machine_version`. `xsm inspect` shows it in the header.

```python
machine = create_machine({"id": "m", "version": 7, "initial": "a", "states": {"a": {}}})
assert machine.version == "7"
```

### `MachineNode.structure_hash`

```python
machine.structure_hash -> str
```

A 16-hex-character structural fingerprint of the machine's behavior: states, transitions, guard/action **names**, invokes, and `after` delays. Stable across `meta`/`description` edits and key reordering; changes when a state, transition, guard, action, invoke, or delay is added, removed, or renamed. Lazily computed and cached on first access. Written into every snapshot as `machine_hash` and checked on restore — see [Snapshots — Snapshot Envelope](../guide/snapshots/#snapshot-envelope).

```python
print(machine.structure_hash)  # e.g. "f21b173044383a6d"
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

### `MachineNode.is_known_event(event_type) -> bool` **[wave 3]**

```python
machine.is_known_event(event_type: str) -> bool
```

True if *event_type* matches a descriptor declared anywhere in the machine
(#51) -- the check `strict` mode runs against a sent event. Honours the same
matching rules as dispatch: an exact `on` key, a partial `"prefix.*"` whose
prefix matches by dot-segment, or the bare `"*"` wildcard, which makes every
event known. Engine-synthesised events (`done.*`, `error.*`, `after.*`,
`xstate.*`, the init sentinel) are always known.

Backed by the `machine.known_events` property (`FrozenSet[str]`), which is
built once, lazily, from every state's `on` keys, every `after` delay's
generated type, and every `invoke`'s generated `done.invoke.<id>` /
`error.platform.<id>`.

```python
machine = create_machine(config)
assert machine.is_known_event("OPEN")
assert not machine.is_known_event("TYPO_EVENT")
```

---

## `xstate_statemachine.persistence`

The package that owns the snapshot format contract — used internally by `get_snapshot()` / `from_snapshot()`, and importable directly for tooling that needs to inspect or migrate snapshots. Since 0.11 it is a **package** (`persistence/snapshot.py` holds the envelope; stores, locking, idempotency and durable timers are being added under it — see [Integrations](../guide/integrations/)). Every name below is re-exported from `xstate_statemachine.persistence`, so imports written against the old module keep working.

```python
from xstate_statemachine.persistence import SNAPSHOT_VERSION, structure_hash
```

| Member | Description |
|--------|-------------|
| `check_version(snapshot)` | `(Dict) -> int` — returns the blob's declared layout version; `SnapshotVersionError` if newer than `SNAPSHOT_VERSION`, `SnapshotCorruptError` if not an integer. |
| `check_minimum_version(version, minimum)` | `(int, int) -> None` — `SnapshotVersionError` if the blob is older than the caller's floor (#205); the `minimum_version=` half of `from_snapshot`. |
| `check_identity(snapshot, machine, *, verify_hash, version=None, expected_hash=None)` | Refuses a blob from a different machine id, or (when `verify_hash`) a different `machine_hash`; `expected_hash=` pins the fingerprint the caller holds instead of trusting the blob's own (#185, #205). |
| `check_shape(snapshot, *, version=0)` | `(Dict, int) -> None` — the structural validator: required keys, `status` in the five known values, `context` an object, `state_ids` / `configuration` lists of strings that agree, event-record lists well-formed, `chain_trips` a non-negative integer and `last_chain_error` a string or null (#241), `machine_version` a string or null and `deadlines` a list of well-formed `Deadline` records (#305). Raises `SnapshotCorruptError`. |
| `upcast(snapshot, version)` | `(Dict, int) -> Dict` — brings a v0 / v1 / v2 payload up to the current layout in place (pure layout migrations: v2 engine records gain `engine: true`, absent v3 keys take their defaults, a v3 blob gains `machine_version: null` and `deadlines: []`). |
| `SNAPSHOT_VERSION` | `int` constant — the current snapshot payload layout version (**4** since 0.11.0, #305). Bumped only when the layout changes, never on an ordinary package release. A v4 blob is refused by 0.10.x with `SnapshotVersionError` — see the rolling-deploy note in the [snapshots guide](../guide/snapshots/#rolling-deploys-a-v4-blob-does-not-load-on-010x). |
| `Deadline` | Frozen dataclass — a durable `after` timer anchored to the wall clock (#305, for #264): `state_id`, `entry_seq` (state-entry generation, so a stale deadline from an earlier visit is ignored), `due_at_wall` (epoch seconds), `delay_ms`, `event_type`. `to_dict()` / `from_dict()` round-trip JSON; `remaining_ms(now_wall)` clamps at 0. |
| `check_deadline_record(rec)` | `(Any) -> Optional[str]` — shape validator for one `Deadline` record; returns what is wrong or `None`. `check_shape` calls it for every entry of `deadlines`. |
| `structure_hash(machine)` | `(MachineNode) -> str` — computes the 16-hex-char structural fingerprint backing `MachineNode.structure_hash`. |

### Stores **[0.11.0]**

The create → act → persist → discard contract (#259). Guide: [Persistence Stores](../guide/persistence/). Every backend passes `tests/persistence/test_store_contract.py`.

| Member | Description |
|--------|-------------|
| `StateStore` (Protocol) | `load(key) -> Optional[StoredSnapshot]`; `save(key, snapshot, *, expected_version=None, machine_version="", deadlines=()) -> int` (new version; `ConflictError` if `expected_version` mismatches — `0` means "must not exist yet"); `delete(key) -> bool`; `forget(key) -> dict[str, int]` (record + auxiliaries, X0.5); `list_keys(*, prefix="", limit=1000)`; `lock(key, *, timeout=10.0)` (context manager; `LockTimeoutError`); `health() -> dict`. Thread-safe. |
| `StoredSnapshot` | Frozen dataclass: `key`, `snapshot` (JSON str), `version`, `machine_version`, `updated_at`, `deadlines: tuple[Deadline, ...]`. |
| `MemoryStore(*, codec=None, max_snapshot_bytes=1 MiB)` | Dict + lock; per-key lock. Tests and single-process apps. |
| `FileStore(directory, *, stale_lock_after=60.0, fsync=True, codec=None, max_snapshot_bytes=…)` | One `<encoded-key>.xsm.json` per key; atomic temp-file + `os.replace` writes; advisory lock file per key (`fcntl.flock` / `msvcrt.locking`, pid+timestamp, stale reclaim); keys percent-encoded (`encode_key` / `decode_key`, reversible, case-preserving, Windows device names prefixed); dir `0700` / files `0600`. **Not for network shares.** |
| `SQLiteStore(path, *, busy_timeout=5.0, journal_mode="WAL", codec=None, max_snapshot_bytes=…)` | Tables `statecharts`, `deadlines`, `xsm_schema(version)` with upgrade steps; optimistic `UPDATE … WHERE version = ?`; `lock()` = `BEGIN IMMEDIATE` on a dedicated connection (database-wide); `database is locked` → `LockTimeoutError`; connection per thread; DB / `-wal` / `-shm` created `0600`; UNC path → warning + `DELETE` journal; `":memory:"` supported; `close()`. |
| `BaseStore` | Optional base for custom backends: implements key validation, the size cap and the codec once around `_load_raw` / `_save_raw` / `_delete_raw` / `_forget_raw` / `_list_keys_raw` / `_lock_raw`. |
| `SnapshotCodec` (Protocol) | `encode(str) -> str` / `decode(str) -> str`; applied on save / undone on load. Compression or encryption at rest. |
| `AsyncStateStore` (Protocol) / `as_async(store)` / `AsyncStoreAdapter` | The same surface with `await`; `lock()` is `async with`, acquired and released on one dedicated worker thread. |
| `load_interpreter(store, key, machine, *, clock=None, plugins=(), create_if_missing=True, verify_machine_hash=True, **from_snapshot_kwargs) -> (SyncInterpreter, int)` | A **started** sync interpreter and the record version (`0` if freshly created). `KeyNotFoundError` when missing and `create_if_missing=False`. |
| `aload_interpreter(...) -> (Interpreter, int)` | Async twin; the returned `Interpreter` is started. |
| `save_interpreter(store, key, interpreter, *, expected_version=None) -> int` | `store.save` of `get_snapshot()` with `machine.version` and the engine's persisted deadlines. |
| `validate_key(key)` / `MAX_KEY_LENGTH` (200) / `DEFAULT_MAX_SNAPSHOT_BYTES` (1 MiB) | The shared key and size rules. |
| `persisted(store, key, machine, *, lock=OptimisticLock(), clock=None, plugins=(), create_if_missing=True, migrator=None, on_version_mismatch=None, restart_timers="resume")` **(#260)** | Context manager: yields a **started** `SyncInterpreter`; persists on clean exit with the strategy's fence; **an exception inside writes nothing**; stops the interpreter either way. Under `OptimisticLock` a concurrent write makes the exit raise `ConflictError` (the block cannot be re-run — the caller retries, or uses `persisted_retry`). |
| `apersisted(...)` | Async twin; yields a started `Interpreter`. *store* may be sync (executor) or an `as_async()` adapter. |
| `persisted_retry(store, key, machine, fn, *, lock=OptimisticLock(), **kw) -> T` | `lock.run(...)`: the retrying form. *fn(interp)* may run up to `retries + 1` times under `OptimisticLock`. |
| `LockStrategy` (Protocol) | `run(store, key, machine, fn, *, clock, plugins, create_if_missing) -> T`; `acquire(store, key)` (CM held for a `persisted` block); `fence(version) -> Optional[int]` (the `expected_version` to save with). |
| `OptimisticLock(*, retries=5, backoff=DEFAULT_BACKOFF, rng=None)` | load → act → `save(expected_version)` → on conflict reload + re-apply with jittered backoff (`RetryPolicy`); gives up with `ConflictError` carrying `.attempts`. Stateless; the shared default instance. |
| `PessimisticLock(*, timeout=10.0)` | `with store.lock(key, timeout)` around load → act → save; `LockTimeoutError`; released on exception; saves **with** `expected_version` as a fence (an expired lock → `ConflictError`, never a lost update). |
| `NoLock()` | Unconditional save; last writer wins. Single-writer-per-key only. |
| `DEFAULT_BACKOFF` | `RetryPolicy(max_attempts=6, base_ms=2, factor=2, max_ms=100, jitter="full")`. |
| `IdempotencyPlugin(inbox, *, principal, key=default_key, instance_key=None, ttl_s=7 days, key_fields=("idempotency_key", "id"))` **(#261)** | `PluginBase`: on `on_before_send` claims an unseen key, short-circuits a seen one with the **original** receipt (`duplicate=True`), refuses a fingerprint mismatch (`error=IdempotencyMismatchError` → 422) or an in-flight key (`IdempotencyInFlightError` → 409) **as a receipt**; marks the real receipt from `on_event_processed`; releases the claim if the delivery did not take effect. Scope = `principal(event) / machine.id / instance_key(interp)` (default instance key: `interp.store_key` or `interp.id`). Buffers marks for `persisted()` to commit after the save (`flush_marks()` / `discard_marks()`); keeps a 64-entry `processed_ids` ring inside `context` for the save→mark crash window. |
| `InboxStore` (Protocol) | `get(scope, key) -> Optional[InboxEntry]`; `claim(scope, key, fp, *, ttl_s) -> bool` (atomic first-wins); `mark(scope, key, receipt_json, *, ttl_s)`; `release(scope, key)`; `purge_expired(*, now=None) -> int`; `forget(scope) -> int`. |
| `InboxEntry(fingerprint, receipt_json, expires_at)` | Frozen dataclass; `receipt_json is None` while in flight. |
| `MemoryInbox()` / `SQLiteInbox(store_or_path)` | Backends. `SQLiteInbox(SQLiteStore)` shares the store's file **and per-thread connection**, so a mark written inside `store.lock()` joins the snapshot's transaction. |
| `default_key(event)` / `fingerprint(event, *, key_fields)` / `validate_idempotency_key(key)` / `DEFAULT_TTL_S` | Helpers: `payload["idempotency_key"]` or `payload["id"]`; sha256 of type + canonical payload minus the key; ≤ 255 printable ASCII; `7 * 86400`. |
| `IdempotencyMismatchError(key)` / `IdempotencyInFlightError(key)` | `StoreError`s carried in the refusal receipt's `error`; `receipt_to_status` maps them (by class name, so the JSON codec preserves the mapping) to **422** / **409**. |
| `TransitionLogPlugin(log, *, include_non_transitions=True, redact_keys=DEFAULT_REDACT_KEYS, machine_id=None)` **(#262)** | `PluginBase`: one `TransitionRecord` per processed event, built from `on_event_processed` (outcome) + `on_event_received` / `on_action_execute` (before-image, actions). Non-transitions (denied / unhandled / deferred / error) are recorded with `to_states == from_states` and a `disposition`. Both engines. |
| `AuditPlugin(log, *, actor_key="actor", reason_key="reason", correlation_key="correlation_id", **kw)` | `TransitionLogPlugin` that fills `actor` / `reason` from the payload and `correlation_id` from the payload or `correlation_id_var`. |
| `TransitionRecord` | Frozen dataclass: `machine_id`, `seq` (gap-free per key), `ts`, `event_type`, `event_payload` (redacted; engine events carry `{kind, src, data|error}`), `from_states`, `to_states`, `actions`, `disposition`, `actor`, `reason`, `correlation_id`, `machine_version`, `engine`, `error`. `to_dict()` / `from_dict()`. |
| `TransitionLogStore` (Protocol) | `append(rec, *, connection=None)` (the transaction seam), `next_seq(machine_id)`, `read(machine_id, *, after_seq=0, limit=1000)`, `purge_older_than(cutoff_ts)`, `forget(machine_id)`. |
| `MemoryLog()` / `JSONLinesLog(path)` / `SQLiteLog(store_or_path)` | Backends. `SQLiteLog(SQLiteStore)` shares the store's file and per-thread connection. |
| `replay(machine, records, *, upto=None, logic=None, verify=True) -> SyncInterpreter` | Re-runs user events on a `SimulatedClock`; `after` steps advance the clock, service completions come from stub services replaying the recorded `done` / `error`; actions and services stubbed but the machine's real guards kept, unless `logic=` is given. `ReplayDivergenceError(seq, expected, actual)` on the first mismatch. The caller's machine is not mutated. |
| `correlation_id_var` | `ContextVar[Optional[str]]` a request middleware sets for `AuditPlugin`. |
| `SnapshotMigrator()` **(#263)** | Registry of `(from_version, to_version) -> fn(blob) -> blob` upcast steps: `register(from, to, *, machine_id=None)` (decorator) / `add(...)`; `path(machine_id, found, target)` (shortest chain, `NoMigrationPathError`); `can_migrate(...)`; `migrate(blob, target, *, machine_id=None)` returns a COPY with `machine_version` rewritten and `machine_hash` dropped. Scoped steps (`machine_id=`) win over unscoped. |
| `MachineVersionMismatchError(machine_id, expected, found)` | Is-a `SnapshotDriftError`. The blob's `machine_version` label differs from `machine.version` and no migration applies. Distinct from `SnapshotVersionError` (layout). |
| `NoMigrationPathError(machine_id, found, target)` | No chain of registered steps bridges the two labels. |
| `DueTimerScanner(store, machine_for_key, *, lock=None, plugins=(), now=None, skew_tolerance_s=0.0, prefix="", limit=1000, migrator=None, on_version_mismatch=None)` **(#264)** | `due_keys(now)`; `run_once(now) -> int` (woken); `scan(now) -> ScanResult`; `run_forever(interval_s)` / `stop()`. Wakes each due key with `persisted(..., restart_timers="fire_due")` under the lock, re-reading first so a machine another worker advanced is skipped. |
| `ScanResult` | `scanned`, `due`, `woken`, `skipped_stale`, `errors: [(key, exc)]`, `max_lag_s`. |
| `DEFAULT_RESTART_TIMERS` | `"resume"` — what `persisted()` / `load_interpreter()` pass to `from_snapshot`. |
| `StoreError` → `ConflictError(key, expected, actual)`, `LockTimeoutError(key, timeout)`, `SnapshotTooLargeError(key, size, limit)`, `InvalidKeyError`, `KeyNotFoundError` | The store exception family; `except StoreError` covers the layer. |

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
| `UnhandledEventError` | An event selected no transition and `onUnhandled` is `"error"`. | Sending an event no active state (or its ancestors) handles. |
| `TransitionFailedError` | An action raised and `actionErrorPolicy` is `"fail"`. | An action raises during a transition on a machine configured with `actionErrorPolicy: "fail"`. |
| `WrongThreadError` | A loop-affine `Interpreter` method was called from a foreign thread. | Calling `interpreter.send()` from a thread other than the one that started the interpreter; use `send_threadsafe()` instead. |
| `SnapshotVersionError` | A snapshot's `version` is newer than this library's `SNAPSHOT_VERSION`. | Restoring a snapshot written by a newer release of the library. |
| `SnapshotDriftError` | A snapshot doesn't belong to the machine restoring it, or can no longer be checked: a `version >= 1` payload whose `machine_hash` is `null`/absent is refused under `verify_machine_hash=True` (#185) — the fingerprint was lost in transit, not omitted by design; only version-0 payloads are exempt. | The snapshot's `machine_id` differs from the target machine's, or (when `verify_machine_hash=True`) `machine_hash` no longer matches `machine.structure_hash`. |
| `QueueOverflowError` **[wave 3]** | `send()` refused an event because the bounded inbox is full. | `max_queue_size` is set, `overflow_policy=OverflowPolicy.RAISE` (the default once a bound is set), and the inbox is at capacity (#38). |
| `UnknownEventError` **[wave 3]** | `send()` was called with an event type not declared anywhere in the machine. | `strict=True` on the interpreter and the event type matches no `on` key, `after` delay, or `invoke` completion descriptor (#51). |
| `InvalidEventPayloadError` **[wave 3]** | An event's payload failed its declared schema. | `event_schemas` is set on `create_machine()` and an incoming event's payload does not satisfy the validator registered for its type (#51). |
| `InterpreterStoppedError` **[wave 3]** | A `send(wait=True)` receipt cannot resolve because the interpreter stopped, or dropped the event, before it was processed. | `interpreter.send(event, wait=True)` is awaited/blocked on and the interpreter is stopped, or the event is dropped by an overflow policy, before that event is processed (#39). |
| `ReentrantWaitError` **[0.9.0]** | An action awaited `send(..., wait=True)` on its **own** interpreter (#219). The receipt resolves only when the run loop processes the event, and the loop cannot advance until the action returns — a deadlock, refused eagerly at the call site. Refused only for an await performed by the action's own task while it runs (#225): a task the action spawns — the `ensure_future` hand-out, or a long-lived helper — is ordinary external traffic. A plain `def` action that drops the `wait=True` result gets a `RuntimeWarning` instead (#232). The sync engine raises it for a `send(wait=True)` from inside an action (its receipt would describe the running step, not the event's). | `async def act(i, c, e, a): await i.send("GO", wait=True)` as an `entry` action. |
| `RestoredChainError` **[0.9.1]** | The restored chain-trip latch (#243): a `RestoredError` *and* a `RunawayChainError`, so a live-machine `isinstance(last_chain_error, RunawayChainError)` guard keeps working across a restart. `.limit` / `.dropped` are `None`; `.stranded` is empty. | `from_snapshot()` of a machine whose `last_chain_error` was set. |
| `RestoredError` | Carries the error *message* recovered from a snapshot persisted in the `error` status; the original type cannot survive JSON. | `from_snapshot()` of a machine that had failed; `interpreter.last_error` is a `RestoredError`. |
| `RunawayChainError` **[0.9.0]** | A self-generated event chain exceeded `maxIterations` and was cut (#77, #103). The machine stays `running`; the trip is reported here. **Self-generated** is decided by *provenance*, not timing (#179, #180): every engine completion — a service's `done.invoke` / `error.platform` whether the service is `def` or `async def`, an invoked child's terminal, a due `after` — is charged when it continues a chain; a caller's `send()` on either lane (`priority=True` included) never is. | An action `raise`s the event that triggers it, an `invoke.onDone` ping-pong (`a -> done -> b -> done -> a`), a `rollback` that re-arms an invoke, or a cross-region `always` keeps re-arming an invoke. Surfaces as `receipt.error` / `last_error`, never as a raised exception. |
| `SnapshotMidStepError` **[0.9.0]** | `get_persisted_snapshot()` was called while a macrostep is in flight (#102, #169) — including the initial descent inside `start()` (#182) and any `on_action_execute` hook (#187). `.child` is `True` when the root was settled but an invoked **child** was mid-step (#183): its half-applied context would have been harvested into the parent's blob. A child stepping on *another thread* (a non-blocking sync actor) is waited for briefly first; one on the caller's own thread cannot settle while the caller holds it and is refused at once (#184). | Snapshotting from inside an action or an action hook, or while a child is mid-step. Snapshot after `send(wait=True)`, from `on_transition`, or after `stop(drain=True)`. |
| `SnapshotCorruptError` **[0.9.0]** | A snapshot is structurally unusable (#110). | Missing key, non-object `context`, unknown `status`, or `status="running"` with an empty configuration. |
| `MissingExtraError` **[0.11.0]** | An optional integration under `xstate_statemachine.contrib` was imported without its pip extra. Also an `ImportError`; `.extra` / `.module` attributes. | `from xstate_statemachine.contrib.fastapi import …` without `pip install "xstate-statemachine[fastapi]"` — the message is that command. |
| `StoreError` **[0.11.0]** | Base for every `StateStore` failure (#259); `except StoreError` covers the persistence layer. | -- |
| `ConflictError` **[0.11.0]** | Optimistic-locking conflict: `save(expected_version=n)` found a different version; nothing was written. `.key` / `.expected` / `.actual`. | Two workers loaded the same record; the slower one's save. Reload and retry. |
| `LockTimeoutError` **[0.11.0]** | `store.lock(key, timeout=…)` could not acquire in time (another holder, or SQLite's `database is locked`). Retryable. | A long-running step holds the key; a busy SQLite writer. |
| `SnapshotTooLargeError` **[0.11.0]** | A snapshot exceeds the store's `max_snapshot_bytes` (default 1 MiB), on save or load. `.size` / `.limit`. | A context that has grown into a document; a poisoned record. |
| `InvalidKeyError` **[0.11.0]** | A store key is unusable: empty, > 200 chars, NUL, or (FileStore) path-like. Also a `ValueError`. | `store.save("../etc", …)`. |
| `MachineVersionMismatchError` **[0.11.0]** | The snapshot's `machine_version` label differs from `machine.version` and no `SnapshotMigrator` path applies (#263). A `SnapshotDriftError`. `.machine_id` / `.expected` / `.found`. | Restoring a v1 order into the v2 chart without a registered upcaster. |
| `NoMigrationPathError` **[0.11.0]** | A `SnapshotMigrator` has no chain of steps from the blob's label to the target. | A missing hop (`1.0 → 3.0` registered only as `2.0 → 3.0`). |
| `KeyNotFoundError` **[0.11.0]** | `load_interpreter(create_if_missing=False)` found no record. Also a `KeyError`. Lives in `persistence`. | Reading a workflow id that was never created. |
| `SnapshotSerializationError` **[0.9.0]** | A pending event's data is not JSON-native (#131). | `Decimal` / `datetime` in a queued `DoneEvent.data` when `get_snapshot()` runs. |
| `InvalidEventError` **[0.9.0]** | `send()` was given something that is not an event: a non-`str` type, a dict without `"type"`, … (#113). Also a `TypeError`, so pre-0.9.0 handlers still catch it. | `send(123)`, `send({"kind": "X"})`. |
| `RootTargetError` **[0.9.0]** | A transition targets the machine root, which would empty the configuration (#108). Subclass of `InvalidConfigError`. Raised regardless of `strict_targets` — the escape hatch downgrades *unresolvable* targets only, never this (#147). | `"always": "#machine"` or `"on": {"X": "#machine"}` at `create_machine()`. |

### `QueueOverflowError` attributes **[wave 3]**

| Attribute | Type | Description |
|-----------|------|-------------|
| `interpreter_id` | `str` | Which machine refused the event. |
| `depth` | `int` | Events queued at the moment of refusal. |
| `maxsize` | `int` | The configured `max_queue_size` bound. |

### `UnknownEventError` attributes **[wave 3]**

| Attribute | Type | Description |
|-----------|------|-------------|
| `event_type` | `str` | The offending type. |
| `machine_id` | `str` | The machine that refused it. |
| `known` | `list[str]` | The declared descriptor set, sorted. |

### `InvalidEventPayloadError` attributes **[wave 3]**

| Attribute | Type | Description |
|-----------|------|-------------|
| `event_type` | `str` | The event whose payload was rejected. |
| `cause` | `BaseException` | The exception the validator raised. |

### `StateNotFoundError` attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `target` | `str` | The state ID that could not be found. |
| `reference_id` | `Optional[str]` | The source state ID from which the lookup was attempted. |

### Exception hierarchy

```
Exception
 +-- XStateMachineError
      +-- StateNotFoundError
      +-- ImplementationMissingError
      +-- ActorSpawningError
      +-- NotSupportedError
      +-- UnhandledEventError
      +-- TransitionFailedError
      +-- WrongThreadError
      +-- SnapshotVersionError
      +-- SnapshotDriftError
      +-- QueueOverflowError
      +-- UnknownEventError
      +-- InvalidEventPayloadError
      +-- InterpreterStoppedError
      +-- RestoredError
      |     +-- RestoredChainError      [0.9.1] (also a RunawayChainError)
      +-- RunawayChainError            [0.9.0]
      +-- ReentrantWaitError           [0.9.0]
      +-- SnapshotMidStepError         [0.9.0]
      +-- SnapshotCorruptError         [0.9.0]
      +-- SnapshotSerializationError   [0.9.0]
      +-- InvalidEventError            [0.9.0]  (also a TypeError)
      +-- InvalidConfigError
           +-- RootTargetError         [0.9.0]
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

### Global registry **[0.11.0]**

Process-wide plugins (#305). Attached — with the same `_SafePlugin` containment as `.use()` — to every interpreter constructed **after** registration: both engines, `from_snapshot`, and engine-spawned children. Interpreters that already exist are not touched. Opt-in only: the library never populates the registry itself. See [Global Plugins](../guide/plugins/#global-plugins-every-interpreter-in-the-process).

| Function | Signature | Description |
|----------|-----------|-------------|
| `register_global(plugin)` | `(Any) -> None` | Add to the registry. Identity-deduplicated; thread-safe. |
| `unregister_global(plugin)` | `(Any) -> bool` | Remove; returns whether it was registered. Existing interpreters keep their copy. |
| `global_plugins()` | `() -> List[Any]` | A copy of the registry in registration order. |
| `plugins.clear_global_plugins()` | `() -> None` | Empty the registry (test teardown). Not exported at top level. |

### Entry-point discovery **[1.0]**

Third-party plugins declared under the `xstate_statemachine.plugins` / `.stores` / `.brokers` entry-point groups (#296). **Never implicit**: nothing loads until you call one of these. See [Third-party plugins: discovery](../guide/plugins/#third-party-plugins-discovery).

| Name (`xstate_statemachine.plugins`) | Signature | Description |
|----------|-----------|-------------|
| `discover(*, group=PLUGINS_GROUP, allow=None, strict=False)` | `-> List[DiscoveredPlugin]` | Load the entry points in *group*. `allow` names entry points or distributions (others are not imported); a raising loader is logged and skipped unless `strict`. `[]` under `XSM_DISABLE_PLUGIN_DISCOVERY=1`. |
| `attach_discovered(interpreter, *, allow=None, strict=False)` | `-> List[Any]` | Discover `PLUGINS_GROUP`, construct each plugin (no arguments), and `.use()` it. Returns the instances. `instrument_all(discovered=True)` in `[observability]` calls this. |
| `DiscoveredPlugin` | `NamedTuple(name, distribution, version, obj, hooks, group)` | One loaded entry point. `hooks` lists the `PluginBase` hooks the class overrides. |
| `PLUGINS_GROUP` / `STORES_GROUP` / `BROKERS_GROUP` | `str` | `"xstate_statemachine.plugins"` / `".stores"` / `".brokers"`. Stores and brokers are discovered, never instantiated. |

CLI: `xsm plugins [--json] [--plain]` lists name, distribution, version, group and hooks.

### Deprecations **[1.0]**

`xstate_statemachine.deprecations`: see the [deprecation policy](../guide/deprecation-policy/).

| Name | Signature | Description |
|------|-----------|-------------|
| `deprecated(what, *, since, removal, alternative, detail=None, stacklevel=2)` | `-> bool` | Emit a `DeprecationWarning` **once per call site** (keyed by `what` + caller file + line). Returns whether it warned. |
| `deprecations()` | `-> List[Deprecation]` | Every registered deprecation (`what`, `since`, `removal`, `alternative`). |
| `register(what, *, since, removal, alternative)` | `-> Deprecation` | Record without warning. |
| `reset_deprecation_warnings()` | `-> None` | Forget which call sites warned (tests). |
| `Deprecation` | `NamedTuple` | A registry row. |
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
| `on_before_send` | `(self, interpreter: TInterpreter, event: AnyEvent) -> Optional[Receipt]` | **[0.11.0]** Interception before queueing (after `strict`/`event_schemas`). Return a `Receipt` to short-circuit -- not queued, caller gets it, no `on_event_received`/`on_event_processed`. First plugin wins. Fail-open: a raising interceptor is reported via `on_plugin_error` and the event is admitted. Not fired for engine-minted events (#304). |
| `on_event_processed` | `(self, interpreter: TInterpreter, event: AnyEvent, receipt: Receipt) -> None` | **[0.11.0]** Once per event that entered the machine (user and engine-minted), after it settled or was denied/unhandled/deferred/dropped, with the same `Receipt` a `wait=True` caller gets. Not fired for short-circuited events (#304). |
| `on_transition` | `(self, interpreter: TInterpreter, from_states: Set[StateNode], to_states: Set[StateNode], transition: TransitionDefinition) -> None` | After a state transition completes (both external and internal). |
| `on_action_execute` | `(self, interpreter: TInterpreter, action: ActionDefinition) -> None` | Right before an action's implementation is executed. |
| `on_guard_evaluated` | `(self, interpreter: TInterpreter, guard_name: str, event: Event, result: bool) -> None` | After a guard condition is evaluated. |
| `on_service_start` | `(self, interpreter: TInterpreter, invocation: InvokeDefinition) -> None` | An invoked service is about to start. |
| `on_service_done` | `(self, interpreter: TInterpreter, invocation: InvokeDefinition, result: Any) -> None` | A service completes successfully. |
| `on_action_error` | `(self, interpreter: TInterpreter, action: ActionDefinition, error: BaseException) -> None` | A user action or built-in action creator raised; the error was contained per `actionErrorPolicy`. |
| `on_service_error` | `(self, interpreter: TInterpreter, invocation: InvokeDefinition, error: Exception) -> None` | A service fails with an error. |
| `on_transition_failed` | `(self, interpreter: TInterpreter, transition: TransitionDefinition, failed_actions: List[Tuple[ActionDefinition, BaseException]]) -> None` | A transition's action list did not run to completion (`actionErrorPolicy` `"rollback"`/`"fail"`). |
| `on_guard_error` | `(self, interpreter: TInterpreter, guard_name: str, event: Event, error: BaseException) -> None` | A guard raised instead of returning, before the substituted result (per `guardErrorPolicy`) is reported. |
| `on_unhandled_event` | `(self, interpreter: TInterpreter, event: Event, active_state_ids: Set[str], disposition: str) -> None` | An event selects no transition. `disposition` is `"ignored"` (no handler declared), `"guard_denied"` **[0.9.0]** (a handler was declared but every guard refused — #153), `"deferred"`, `"errored"`, or `"dropped"`. |
| `on_invalid_event` **[0.9.0]** | `(self, interpreter: TInterpreter, error: BaseException, raw_event: Any) -> None` | `send()` refused a malformed event; fires immediately before the `InvalidEventError` propagates to the caller (#159). Observability, not containment. |
| `on_snapshot_error` **[0.9.0]** | `(self, interpreter: TInterpreter, error: BaseException) -> None` | A snapshot was refused — `SnapshotMidStepError` or `SnapshotSerializationError` — fires immediately before it propagates (#159). |
| `on_chain_budget_exceeded` **[0.9.0]** | `(self, interpreter: TInterpreter, error: BaseException, event: AnyEvent) -> None` | Once per chain-budget or settle-budget trip (#222): `maxIterations` cut the machine's self-generated work. `error` is the `RunawayChainError`; `event` the first event cut (`Event("")` for a settle trip). Pairs with the sticky `chain_trips` / `last_chain_error`; `on_event_dropped(..., "chain_budget")` still fires per discarded event. |
| `on_invocation_stranded` **[0.9.0]** | `(self, interpreter: TInterpreter, state_id: str, invoke_id: str, error: BaseException) -> None` | A chain-budget cut discarded the `done.invoke`/`error.platform` of an invocation whose state is still active (#207). Nothing is running for it and no completion will arrive: the machine rests in a state that declares `invoke`. `error` is the `RunawayChainError`, whose `.stranded` tuple names the same ids; `has_dormant_invocations` / `pending_invocations()` answer the question on demand. Distinguishes "the storm settled" from "the storm was cut and the machine is parked". |
| `on_receipt_dropped` **[0.9.1]** | `(self, interpreter: TInterpreter, event_type: str) -> None` | A `send(wait=True)` receipt issued from inside an action was dropped without ever being awaited or handed out (#232, #244). The `RuntimeWarning` for the same event fires from a finaliser and is invisible to `-W error`; this hook and `interpreter.dropped_receipts` are the deterministic signal. Async engine only. |
| `on_event_dropped` **[wave 3, 0.9.0]** | `(self, interpreter: TInterpreter, event: Event, reason: str) -> None` | An event was discarded unprocessed. `reason` is one of `"queue_full"` (bounded inbox, `DROP_NEWEST`), `"not_running"` (sent to a stopped/done/errored machine), `"chain_budget"` (`maxIterations` cut), `"stopped"` (abandoned by `stop()`, including producers parked on a full `BLOCK` inbox), `"unresolved_target"` (`sendTo` to no live actor). Fires on **both** engines for every loss site (#38, #123, #129, #133). Also logged at WARNING. |
| `on_resolve_error` **[0.9.0]** | `(self, interpreter: TInterpreter, error: BaseException, event: Event) -> None` | A transition's target could not be resolved at runtime (`strict_targets=False` only). The third per-transition failure category alongside `on_action_error` / `on_guard_error` (#134). |
| `on_plugin_error` **[0.9.0]** | `(self, interpreter: TInterpreter, plugin: PluginBase, hook: str, error: BaseException) -> None` | **Another** plugin's hook raised, or was `async def` and could not be awaited. Never fires for the plugin that failed. The same triple is on `interpreter.last_plugin_error` (#127). |
| `on_error` | `(self, interpreter: TInterpreter, error: BaseException) -> None` | The interpreter enters the terminal `"error"` status. |
| `on_done` | `(self, interpreter: TInterpreter, output: Any) -> None` | The machine reaches a top-level final state. |

`LoggingInspector` implements all five of these hooks in addition to the ones above.

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

### `LoggingInspector(*, redact_keys=DEFAULT_REDACT_KEYS, log_context=True)`

```python
class LoggingInspector(PluginBase[Any]):
    def __init__(
        self,
        *,
        redact_keys: Tuple[str, ...] = DEFAULT_REDACT_KEYS,
        log_context: bool = True,
    ) -> None: ...
```

A built-in plugin for detailed, real-time inspection of machine execution.
Works with both `Interpreter` and `SyncInterpreter`. All messages are
emitted through Python's standard `logging` module at `INFO` level.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `redact_keys` | `DEFAULT_REDACT_KEYS` | **[0.9.0]** (#126) Substrings matched case-insensitively against every key in a logged context or payload, recursively; matches are written as `"***"`. The default list covers `password`, `secret`, `token`, `api_key`, `authorization`, `credential`, `card`, `cvv`, …. Extend with `(*DEFAULT_REDACT_KEYS, "ssn")`; pass `()` to opt out explicitly. |
| `log_context` | `True` | Set `False` to skip the per-transition context dump on machines with a large context. |

The standalone `redact(value, keys=DEFAULT_REDACT_KEYS)` helper is exported for your own plugins.

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
| `.strict` / `.strict_targets` | `bool` | The machine's `strict` and `strictTargets` config keys. |
| `.event_schemas` | `Dict[str, Any]` | The validators passed to `create_machine(event_schemas=)`, by event type. |
| `.max_iterations` | `int` | The `maxIterations` chain / settle budget (default 1000). |
| `.action_error_policy` / `.guard_error_policy` / `.on_unhandled` | `str` | The three per-machine policies, validated at build time. |
| `.spawn_blocking_timeout_ms` | `Optional[float]` | The `spawnBlockingTimeout` key. |
| `.known_events` | `FrozenSet[str]` | Every event type the machine declares anywhere — what `strict` checks against. |
| `.structure_hash` | `str` | 16-hex-char fingerprint of the machine's structure; see `MachineNode.structure_hash` above. |
| `.context_is_immutable` | `bool` | `True` when no state or transition declares any action, so nothing the engine does can mutate `context`; a `Receipt` then skips the deep-copy it needs to decide `changed`. Lazily computed, cached. |
| `.state_ids_by_bare_name(bare)` | `(str) -> List[str]` | Every state id whose last segment is `bare` — the lookup behind the "did you mean" hint when a relative target does not resolve (#132). |

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
| `.input` | `Any` | Static value, or a callable resolved per spawn by `.resolve_input()`. |
| `.on_done` | `List[TransitionDefinition]` | Transitions on success. |
| `.on_error` | `List[TransitionDefinition]` | Transitions on failure. |

#### `InvokeDefinition.resolve_input(context, event) -> Any`

Resolves this invoke's `input` against the parent's live state, per spawn. `input` may be:

- a static value — returned as-is (deep-copied);
- `fn(context, event)` — the two-positional form;
- `fn(args)` — one mapping `{"context": ..., "event": ...}` (XState form).

Returns a **deep copy** of the resolved value so the child never aliases the parent's context; returns `None` when no `input` is declared.

---

## Type Aliases

The library defines several callable type aliases for documentation purposes:

| Alias | Signature | Used for |
|-------|-----------|----------|
| `ActionCallable` | `(BaseInterpreter, TContext, Event, ActionDefinition) -> Union[None, Awaitable[None]]` | Action functions |
| `GuardCallable` | `(TContext, Event) -> bool` | Guard functions (sync only) |
| `ServiceCallable` | `(BaseInterpreter, TContext, Event) -> Union[Any, Awaitable[Any]]` | Service functions |

---

## Module Map

Everything above is importable from the package root (`from xstate_statemachine import …`; `__all__` has 83 names). The modules exist for readers of the source and for the few tooling imports that are deliberately not re-exported:

| Module | Owns | Import directly for |
|:--|:--|:--|
| `factory` | `create_machine` | — |
| `models` | `MachineNode`, `StateNode`, `TransitionDefinition`, `InvokeDefinition`, `ActionDefinition`, `GuardDefinition` | — |
| `machine_logic` | `MachineLogic`, the `@action` / `@guard` / `@service` decorators | — |
| `logic_loader` | `LogicLoader` — auto-discovery by name, snake↔camel matching | — |
| `interpreter` / `sync_interpreter` / `base_interpreter` | The two engines and their shared base | — |
| `events` | `Event`, `DoneEvent`, `ErrorEvent`, `AfterEvent`, `Receipt`, provenance (`is_system_event`, `system_event`, `re_mint`), `ENGINE_EVENT_SHAPES` | `event_kind` / `persist_event` / `restore_event` for journal tooling |
| `persistence` | The snapshot contract | `SNAPSHOT_VERSION`, `structure_hash`, `check_*`, `upcast` |
| `validation` | Build-time checks | `KNOWN_ROOT_KEYS`, `KNOWN_STATE_KEYS`, `KNOWN_TRANSITION_KEYS`, `KNOWN_INVOKE_KEYS` — the per-level known-key sets (#220) |
| `actions` | The builtin action creators, `BUILTIN_ACTION_ALIASES`, `BUILTIN_ACTION_PARAM_SPEC` | — |
| `clock` | `Clock`, `RealClock`, `SimulatedClock` | — |
| `plugins` | `PluginBase`, `LoggingInspector`, `DEFAULT_REDACT_KEYS`, `redact()`, entry-point `discover()` / `attach_discovered()` | `discover`, `attach_discovered`, `DiscoveredPlugin` |
| `plugin_discovery` | The implementation behind `plugins.discover` (3.9 shim, `XSM_DISABLE_PLUGIN_DISCOVERY`) | — |
| `deprecations` | `deprecated()`, the `deprecations()` registry | Policy tooling |
| `helpers` | The pure API (`PureSnapshot`, `initial_transition`, `pure_transition`, `get_*_snapshot`) and the waiting helpers | — |
| `pythonic` | `State`, `StateMachine`, `MachineBuilder`, `Transition`, `build_machine` | — |
| `resolver` | Transition-target resolution (`#id`, `.child`, sibling fallback + its `DeprecationWarning`) | — |
| `task_manager` | `TaskManager` (async engine's owned-task registry) | — |
| `exceptions` | Every exception class | — |
| `logger` | The package logger, `logging.getLogger("xstate_statemachine")` | — |
| `cli` | The `xsm` command | — |
| `persistence` (package) | Stores, locks, inbox, log, migrator, timers — see its own section | `from xstate_statemachine.persistence import …` |
| `patterns` / `graph` / `actor_logic` / `testing_utils` | Resilience patterns, graph algorithms, actor logic helpers, stub logic — see their sections | — |
| `contrib.*` | The optional extras (table below) | `from xstate_statemachine.contrib.<extra> import …` |

---

## Built-in Action Creators

Added in v0.6.0. Each returns a plain action-definition dict, so they can be
used directly in a config or written as raw JSON. See the
[Actions guide](../guide/actions/#built-in-action-creators-v060).

| Function | Signature |
|:--|:--|
| `assign` | `assign(assignment: dict \| Callable) -> dict` |
| `choose` | `choose(conditions: list[dict]) -> dict` |
| `pure` | `pure(fn: Callable) -> dict` |
| `enqueue_actions` | `enqueue_actions(fn: Callable) -> dict` |
| `raise_` | `raise_(event, *, delay=None) -> dict` |
| `send_to` | `send_to(target, event, *, delay=None, send_id=None) -> dict` |
| `send_parent` | `send_parent(event, *, delay=None) -> dict` |
| `spawn_child` | `spawn_child(src, *, actor_id=None, system_id=None, input=None) -> dict` |
| `stop_child` | `stop_child(actor_id) -> dict` |
| `cancel` | `cancel(send_id: str) -> dict` |
| `emit` | `emit(event) -> dict` |
| `escalate` | `escalate(error) -> dict` |
| `forward_to` | `forward_to(target: str) -> dict` |
| `log` | `log(expr='', *, label=None) -> dict` |

#### Canonical action types and accepted spellings

Every creator produces `{"type": "<canonical>", "params": {...}}`. In raw JSON the canonical `xstate.*` name, the XState camelCase name and the Python snake_case name are all accepted (`BUILTIN_ACTION_ALIASES`), and the parameters **must** be nested under `params` — a missing required key is an `InvalidConfigError` at build time naming the action and the keys (`BUILTIN_ACTION_PARAM_SPEC`).

| Canonical type | Also accepted as | Required params | Optional params |
|:--|:--|:--|:--|
| `xstate.raise` | `raise`, `raise_` | `event` | `delay`, `id` |
| `xstate.sendTo` | `sendTo`, `send_to` | `event`, `to` | `delay`, `id` |
| `xstate.sendParent` | `sendParent`, `send_parent` | `event` | `delay`, `id` |
| `xstate.forwardTo` | `forwardTo`, `forward_to` | `to` | — |
| `xstate.escalate` | `escalate` | `error` | — |
| `xstate.cancel` | `cancel` | `sendId` | — |
| `xstate.stopChild` | `stopChild`, `stop_child`, `stop` | `id` | — |
| `xstate.spawnChild` | `spawnChild` | `src` | `id`, `systemId`, `input` |
| `xstate.emit` | `emit` | `event` | — |
| `xstate.log` | `log` | — | `expr`, `label` |
| `xstate.assign` | `assign` | *(assignment is the params object itself)* | |
| `xstate.pure` / `xstate.choose` / `xstate.enqueueActions` | `pure` / `choose` / `enqueueActions`, `enqueue_actions` | *(callable-only: not expressible in JSON)* | |

A `raise` / `sendTo` / `sendParent` with a `delay` is a **timer** with the standing of `after`: it is never counted by `maxIterations`, it is persisted in `scheduled_sends` with its remaining delay, and `cancel(sendId)` disarms it (#212, #213, #218).

### `ActionEnqueuer`

The object passed as `enqueue` to an `enqueue_actions` callback. Methods:
`assign`, `raise_`, `send_to`, `send_parent`, `spawn_child`, `stop_child`,
`emit`, `log`, `cancel`.

```python
from xstate_statemachine import enqueue_actions

def build(args):
    enqueue = args["enqueue"]          # ActionEnqueuer
    enqueue.assign({"n": lambda x: x["context"]["n"] + 1})
    enqueue.raise_({"type": "NEXT"})

{"actions": enqueue_actions(build)}
```

> **Note:** the callback receives a **single mapping** containing `context`,
> `event`, `enqueue`, `check` and `self` — not separate positional arguments.

---

## Pure API

Compute transitions with no side effects: no timers start, no services fire,
nothing mutates. See [Testing & The Pure API](../guide/testing-and-pure-api/).

| Function | Returns |
|:--|:--|
| `initial_transition(machine, *, input=None)` | `(PureSnapshot, list[ActionDefinition])` |
| `pure_transition(machine, snapshot, event)` | `(PureSnapshot, list[ActionDefinition])` |
| `get_initial_snapshot(machine, *, input=None)` | `PureSnapshot` |
| `get_next_snapshot(machine, snapshot, event)` | `PureSnapshot` |

### `PureSnapshot`

| Member | Description |
|:--|:--|
| `.state_ids` | Set of active state ids |
| `.context` | The context dict |
| `.status` | `'active'`, `'done'` or `'error'` |
| `.output` | Machine output once a top-level final state is reached |
| `.configuration` | `Set[str]` of every active state id, ancestors included (`state_ids` is the leaves only) |
| `.matches(id)` | Test a state id, supporting nested paths |

```python
from xstate_statemachine import initial_transition, pure_transition

snapshot, entry_actions = initial_transition(machine)
next_snapshot, actions = pure_transition(machine, snapshot, "GO")
```

---

## Waiting Helpers

Poll a real predicate with a timeout instead of sleeping.

| Function | Description |
|:--|:--|
| `wait_for(interp, predicate, *, timeout=10.0, poll_interval=0.005)` | Async; resolves when the predicate is true |
| `wait_for_sync(interp, predicate, *, timeout=10.0, poll_interval=0.005)` | Blocking equivalent for `SyncInterpreter` |
| `to_promise(interp)` | Async; resolves with the machine output when it reaches a final state |

```python
await wait_for(interp, lambda s: s.matches("fetch.success"), timeout=2)
wait_for_sync(interp, lambda s: s.matches("job.done"), timeout=5)
output = await to_promise(interp)
```

Both waiters raise on timeout rather than returning silently.

---

## Testing Utilities **[0.11.0]**

Drive any chart without owning its business logic. A machine that declares actions, guards or services refuses to build without them (`ImplementationMissingError` — "silent acceptance is a bug"); these stand-ins let tools, tests and scripts exercise the *structure* anyway. Promoted from the CLI's internal trace recorder (#304); used by `xsm simulate`, the `pytest` codegen template and the testing plugin.

| Function | Description |
|:--|:--|
| `stub_logic(config_or_machine, *, ran=None, guards=True, service_results=None)` | A `MachineLogic` satisfying every declared name. Actions append their name to `ran`; `guards` is a bool for all or a **live** mapping of name → bool (mutate it between sends to flip a guard); services complete synchronously returning `service_results[name]` (→ `event.data` on `onDone`). |
| `logic_names(config_or_machine)` | `(actions, guards, services)` sets the chart references — from the raw JSON (via the CLI extractor) or from a built `MachineNode` (walking entry/exit/transition actions, leaf guards inside composites, invoke `src`). Built-in actions are excluded. |

```python
from xstate_statemachine import SyncInterpreter, create_machine, stub_logic

cfg = {"id": "m", "initial": "a", "states": {
    "a": {"on": {"GO": {"target": "b", "guard": "ok", "actions": "log"}}}, "b": {}}}
ran: list = []
guards = {"ok": False}
interp = SyncInterpreter(create_machine(cfg, logic=stub_logic(cfg, ran=ran, guards=guards))).start()
assert interp.send("GO", wait=True).denied
guards["ok"] = True                      # live: no rebuild needed
assert interp.send("GO", wait=True).changed and ran == ["log"]
```

---

## Graph Algorithms **[0.12.0]**

`from xstate_statemachine import shortest_paths, simple_paths, reachable_states, transition_coverage_targets, Path, Step` (#269). The Python counterpart of `@xstate/graph`. Every candidate step is **executed by the real engine** (`SyncInterpreter` + `SimulatedClock` + `stub_logic`), so what comes back is what the engine does. `guards` is `"true"` (default), `"false"` or `"both"`; anything else is `ValueError`.

| Name | Description |
|:--|:--|
| `Step` | Frozen dataclass: `event` (`None` for a clock advance), `delay_ms`, `from_states`, `to_states` (frozensets of leaf ids), `assumptions` -- tuple of `guard:<name>=False` / `service:<name>=error` / `delay:<name>=unknown` the step relies on. |
| `Path` | Frozen dataclass: `steps`, `final_states`. `replay(interp, clock)` drives a `SyncInterpreter` (starting it if needed) and lands on `final_states`; `event_string()` is the `xsm simulate --events` grammar (`SUBMIT,+2000`); `total_delay_ms`. |
| `shortest_paths(machine, *, guards="true", max_depth=50, weight="steps")` | `{configuration: Path}` -- one shortest path per reachable configuration; the initial configuration maps to an empty path. `weight="time"` is Dijkstra over `after` delays (events weigh 0). |
| `simple_paths(machine, *, guards="true", max_paths=1000, max_depth=50)` | Every acyclic path (DFS, no configuration revisited on a path), capped. |
| `reachable_states(machine, *, guards="true", max_depth=50)` | Leaf ids reached plus their ancestors. |
| `transition_coverage_targets(machine)` | Static `{(from_id, label, to_id)}` for every transition (targetless -> `to_id == from_id`); the denominator for a coverage report. |

`from xstate_statemachine.coverage import CoverageCollector, CoverageReport` (#270). `CoverageCollector()` is a `PluginBase`: `.use()` it or `plugins.register_global` it; `report(machine) -> CoverageReport(machine_id, key, states_visited, states_total, unvisited, transitions_hit, transitions_total, unhit)` with `state_percent` / `transition_percent` and `to_json()` / `to_text()` / `to_html()`; `reports()`, `machines()`, `merge(other)`. Module functions: `reports_to_json` (the stable `{"version": 1, "machines": [...]}` document), `reports_from_json` (rejects other versions with `ValueError`), `reports_to_text`, `reports_to_html`, `below(reports, state=, transition=)`, `machine_key(machine)` (`id@structure_hash`), `format_edge`. See [State & transition coverage](../guide/integration-testing/#state-transition-coverage).

Named `after` delays fire only when `logic.delays` defines them; otherwise the step is skipped (`delay:<name>=unknown`). Machines that cannot start raise as they would at runtime. CLI: `xsm paths`.
## `xstate_statemachine.patterns` **[0.11.0]**

Resilience building blocks, each a small statechart (#265). Zero-dependency, both engines. Guide: [Resilience Patterns](../guide/patterns/).

```python
from xstate_statemachine.patterns import RetryPolicy, DeadLetterPlugin, CircuitBreaker
```

| Member | Description |
|--------|-------------|
| `RetryPolicy(max_attempts=5, base_ms=200, factor=2.0, max_ms=30_000, jitter="full", rng=random.random)` | Frozen dataclass. `delay_ms(attempt, *, previous_ms=None)` — delay after the 1-based failed *attempt*, per the AWS `none` / `full` / `equal` / `decorrelated` jitter formulas, capped at `max_ms`. `exponential_ms(attempt)` is the un-jittered value. `as_delay(attempt_key)` / `guard_can_retry()` / `action_bump()` / `action_reset()` are the individual logic pieces; `logic(prefix="retry", attempt_key="attempt")` bundles them as a `MachineLogic` with `{prefix}Delay` (named delay), `{prefix}CanRetry` (guard), `{prefix}Bump` / `{prefix}Reset` (actions). Invalid arguments raise `ValueError`. |
| `DeadLetterPlugin(sink, *, state_ids=(), attempt_key="attempt", redact_keys=DEFAULT_REDACT_KEYS, include_snapshot=True)` | `PluginBase` that emits a `DeadLetter` to `sink(record)` when the machine enters a state tagged `"dead-letter"` (or one of `state_ids`). Collects the error chain from `on_service_error` / `on_action_error` (cleared by a `done.invoke`), writes the record from `on_event_processed` once the step has settled, and passes it through `redact()` first. |
| `DeadLetter` | Frozen dataclass: `machine_id`, `state_id`, `event` (`{type, payload}`, redacted), `attempts`, `errors` (list of `{source, name, type, message}` strings), `snapshot` (redacted persisted snapshot or `{}`), `taken_at` (epoch seconds). `to_dict()` / `to_json()`. |
| `DeadLetterStore()` | Thread-safe in-memory sink: callable, `all()`, `len()`, `purge_older_than(cutoff_wall)`, `clear()`. |
| `DEAD_LETTER_TAG` | `"dead-letter"`. |
| `CircuitBreaker(*, failure_threshold=5, cooldown_ms=30_000, half_open_max_calls=1, clock=None, plugins=(), name=None, exceptions=(Exception,))` | Nygard's breaker run as `CIRCUIT_BREAKER_CONFIG` on a `SyncInterpreter` behind an `RLock`. `call(fn, *a, **kw)` / `await acall(fn, *a, **kw)` admit-or-raise `CircuitOpenError` (target **not** invoked), then record the outcome; `state` (ticks the clock first) / `failures` / `opened_count` / `interpreter`; `reset()`; `close()`. Half-open admits exactly `half_open_max_calls` probes across any number of threads. |
| `circuit_breaker(**kw)` | Decorator; one breaker per function (sync or `async def`), exposed as `fn.breaker`. |
| `CircuitOpenError(name, state)` | `XStateMachineError`; `.breaker`, `.state`. |
| `CIRCUIT_BREAKER_CONFIG` / `circuit_breaker_logic(cooldown_ms)` | The chart (`closed` → `open` → `half_open`; one `cooldown` named delay; `version: "1"`) and the `MachineLogic` it needs. |

### `MachineLogic.merge(*others) -> MachineLogic` **[0.11.0]**

Returns a **new** `MachineLogic` combining the receiver with `others` (later wins on a name clash; nothing is mutated). The way a pattern's logic joins yours: `policy.logic().merge(MachineLogic(services={"work": work}))`.

---

## Actor Logic Helpers **[0.11.0]**

`xstate_statemachine.actor_logic` (also top-level) — XState v5 `fromPromise` / `fromCallback` / `fromObservable` / `fromActor` parity (#267). Each returns an ordinary service for `MachineLogic(services=…)`. Guide: [Actor logic helpers](../guide/services/#actor-logic-helpers).

| Function | Engine | Description |
|----------|--------|-------------|
| `from_coroutine(async_fn)` | async | Today's `async def (interp, ctx, event)` service under its parity name; `onDone` with the return value. `TypeError` for a plain `def`. |
| `from_callable(fn)` | both | A plain `def` service, run inline; `onDone` with the return value. |
| `from_callback(setup)` | both | `setup(send_back, receive, ctx, event) -> cleanup \| None` runs once on entry. `send_back(type, **payload)` / `send_back(Event)` is **thread-safe** (routes through `send_threadsafe`); `receive(handler)` subscribes to events the parent `sendTo`s this invocation's id. Never `onDone` on its own; an exception in `setup` (or a non-callable return) is `onError`. Cleanup runs exactly once on state exit / `stop()` / error; an `async def` cleanup is awaited by the async `stop()`. |
| `from_async_iterator(factory, *, event_type="STREAM")` | async | `factory(interp, ctx, event)` returns an async iterator (or a coroutine returning one). Each item → `Event(event_type, {"data": item})`, applied before the next is pulled; exhaustion → `onDone` with the last item; exception → `onError`; state exit → task cancelled + `aclose()`. |
| `from_iterator(factory, *, event_type="STREAM")` | both | Sync twin: the iterator is consumed on a daemon thread; items arrive via `send_threadsafe` (the sync mailbox, drained on the owner's next `send()` / `tick()`); exit stops it at the next item and `close()`s the generator. |
| `from_interpreter(interp)` | both | The interpreter's `machine`, to use as an `invoke` `src` (`fromActor` parity). The engine starts a fresh actor of that machine under the invocation id. |
| `RunningLogic` | — | The handle a callback / iterator service returns to the engine: `cleanup()` (idempotent), `subscribe(handler)`, `receive(event)`, `finished`. `sendTo(<invocation id>)` resolves to it while it runs. |

## Receipt Codec **[0.11.0]**

`xstate_statemachine.receipts` — one JSON shape and one HTTP-status mapping for a `Receipt`, in core (#305), so every web adapter (Django, Flask, Starlette, …) returns the same response and the idempotency inbox (#261) can cache a receipt in a defined form. The three functions are also exported from the top-level package.

| Function | Signature | Description |
|----------|-----------|-------------|
| `receipt_to_status(receipt)` | `(Receipt) -> int` | `error` is an `IdempotencyMismatchError` → **422**, an `IdempotencyInFlightError` → **409** (matched by class name); any other `error` → **500**; else `deferred` → **202**; else `denied` → **409**; else **200** (taken *or* a clean no-op). `duplicate` never changes the status — the cached receipt already describes the original outcome, so a retry gets the same answer. |
| `receipt_to_json(receipt)` | `(Receipt) -> Dict` | `{"state_ids": [sorted…], "changed", "error", "deferred", "denied", "duplicate"}`. `error` is `null` or `{"type": <class name>, "message": str(exc)}` — never a pickle, never a `repr` (X0 baseline #303). `state_ids` is sorted so identical outcomes serialise identically (ETag / cache key friendly). |
| `receipt_from_json(data)` | `(Mapping) -> Receipt` | Inverse. A stored `error` comes back as a `ReceiptError(type, message)` (an `Exception`), so `receipt.error is not None` keeps meaning "did not run cleanly". Raises `ValueError` on a malformed record instead of leaking a bare `KeyError`. |
| `ReceiptError` | `Exception` | `.type` (original class name) and `.message`. Re-encodes to the same JSON. |
| `STATUS_OK` / `STATUS_ACCEPTED` / `STATUS_CONFLICT` / `STATUS_UNPROCESSABLE` / `STATUS_ERROR` | `int` | `200` / `202` / `409` / `422` / `500` — named so adapters and tests cite the rule, not the number. |

```python
import json
from xstate_statemachine import SyncInterpreter, create_machine
from xstate_statemachine import receipt_to_json, receipt_from_json, receipt_to_status

cfg = {"id": "m", "initial": "a", "states": {"a": {"on": {"GO": "b"}}, "b": {}}}
interp = SyncInterpreter(create_machine(cfg)).start()
receipt = interp.send("GO", wait=True)

assert receipt_to_status(receipt) == 200
wire = json.dumps(receipt_to_json(receipt))
assert receipt_from_json(json.loads(wire)) == receipt
```

### `interpreter.wall_now() -> float` **[0.11.0]**

Both engines. Seconds since the Unix epoch, delegated to `clock.wall_now()` when the clock provides one (`RealClock` → `time.time()`, `SimulatedClock` → `wall_start + virtual elapsed`) and falling back to `time.time()` for a custom clock that lacks it. Use it for anything that must survive the process — durable deadlines, audit timestamps — instead of `clock.now()`, whose origin is process-specific (#305).

---

## `xstate_statemachine.contrib` — the extras **[0.11.0]**

Every integration is an optional extra you install explicitly (`pip install "xstate-statemachine[fastapi]"`). Importing a subpackage without its dependency raises `MissingExtraError` naming the exact `pip install` command. The core never imports any of these. Each has a guide page with **Guarantees** and **Threat model** boxes; the table lists every public name so you can grep for it.

| Extra | Import | Public names | Guide |
|:--|:--|:--|:--|
| `[pydantic]` | `xstate_statemachine.contrib.pydantic` | `context_model`, `typed_context`, `TypedContextPlugin`, `ContextValidationError`, `EventModel`, `events_union`, `models_of`, `context_of`, `validate_machine_json`, `machine_json_schema`, `MachineConfig` / `StateConfig` / `TransitionConfig` / `InvokeConfig`, `PydanticCodec` | [Pydantic](../guide/integration-pydantic/) |
| `[redis]` | `xstate_statemachine.contrib.redis` | `RedisStore`, `AsyncRedisStore`, `RedisInbox`, `RedisLog`, `escape_glob` | [Redis](../guide/integration-redis/) |
| `[sqlalchemy]` | `xstate_statemachine.contrib.sqlalchemy` | `StatechartType`, `StatechartMixin`, `send_with_retry`, `xsm_sqlalchemy_ddl`, `SQLAlchemyStore`, `AsyncSQLAlchemyStore`, `SQLAlchemyInbox`, `SQLAlchemyLog`, `ModelStore`, `SCHEMA_VERSION` | [SQLAlchemy](../guide/integration-sqlalchemy/) |
| `[flask]` | `xstate_statemachine.contrib.flask` (+ `contrib.quart`) | `XState`, `create_statechart_blueprint`, `receipt_response`, `problem_response`, `SessionStore`, `SessionStoreTooLargeError`, `DEFAULT_SESSION_LIMIT`, `allow_all`, `REQUIRED`, HTTP problem errors (incl. `MethodNotAllowedError`, `UnprocessableBodyError`); Quart: `QuartXState`, `create_quart_statechart_blueprint` | [Flask](../guide/integration-flask/) |
| `[starlette]` | `xstate_statemachine.contrib.starlette` | `StatechartRegistry` (`register`, `act`, `send_event`, `resident`, `lifespan`, `health_route`, `ready_route`), `allow_all`, `receipt_to_status`, `receipt_body`, `ReceiptResponse`, `problem`, `problem_for_exception`, `status_for_exception`, `HTTPProblemError` (+ `BadRequestError`, `ForbiddenError`, `PayloadTooLargeError`, `UnsupportedMediaTypeError`), `idempotency_key_from`, `json_body`, `transition_stream`, `websocket_endpoint`, `mount_inspector` | [Starlette](../guide/integration-starlette/) |
| `[fastapi]` | `xstate_statemachine.contrib.fastapi` | `StatechartRouter`, `get_interpreter`, `instrument_app`, `compose_lifespan`, `StateModel`, `ReceiptModel`, `Problem`; re-exports `StatechartRegistry`, `allow_all`, `ReceiptResponse`, `receipt_to_status`, `problem`, `problem_for_exception` | [FastAPI](../guide/integration-fastapi/) |
| `[litestar]` | `xstate_statemachine.contrib.litestar` | `XStatePlugin`, `create_statechart_controller`, `get_interpreter`; re-exports as above | [Litestar](../guide/integration-litestar/) |
| `[agents]` | `xstate_statemachine.contrib.agents` | `TOOL_LOOP`, `load_chart`, `CHARTS_DIR`, `agent_logic`, `budget_guards`, `Budget`, `state_tools`, `validate_agent_chart`, `tool_registry`, `tool`, `Tool`, `ToolRegistry`, `ALL_TOOLS`, `DEFAULT_TOOL_TIMEOUT_S`, `DEFAULT_MAX_OUTPUT_CHARS`, `AGENT_REDACT_KEYS`, `run_agent`, `run_agent_sync`, `AgentResult`, `WAITING_STATES`, `FakeModel`, `ModelCall`, `ModelResponse`, `ToolCall`, `Usage`, `AgentTracePlugin`, `spawn_agent`, `BudgetPlugin`, `handoff_guard`, `AgentError`, `AgentConfigError`, `ToolDeniedError`, `ToolTimeoutError`, `pending_approval`, `scrub`, `structured_output`, `validate_structured`; `providers.openai.openai_model`, `providers.anthropic.anthropic_model` | [LLM agents](../guide/integration-agents/) |
| `[testing]` | `xstate_statemachine.contrib.testing` (pytest plugin, auto-loaded via the `pytest11` entry point) | `PLUGIN_NAME`, `SnapshotMismatchError`, `normalize_snapshot`, `parse_marker`, `render_snapshot`, `model_test`, `events_strategy`, `payload_strategy` (the last three need `hypothesis`, imported lazily); fixtures `xsm_*` (incl. the parametrised `xsm_path`), the `xstate_machine` marker, `--xsm-coverage` | [Testing](../guide/integration-testing/) |

The `xsm` CLI grows with them: `xsm gt --with-api --with-models` emits a FastAPI router and Pydantic event models you own ([templates](../guide/cli-templates/)); `xsm new --template fastapi` scaffolds a project from the example app; `xsm paths` lists a path to every reachable configuration ([CLI](../guide/cli/)).

---
## Version

```python
from xstate_statemachine import __version__
print(__version__)  # "0.10.5"
```
