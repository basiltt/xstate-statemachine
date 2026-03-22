# Pythonic API Design Spec

**Date:** 2026-03-22
**Status:** Approved
**Scope:** Add a full Pythonic API layer to `xstate-statemachine` so users can define state machines in pure Python without writing JSON config dicts.

---

## 1. Problem Statement

The library currently requires all machine structure (states, transitions, hierarchy) to be defined as a JSON-style Python dictionary. While this ensures 100% XState compatibility, it is marked as a gap compared to the `transitions` library, which offers a Pythonic, kwargs/class/decorator-based API.

**Goal:** Provide three Pythonic API styles (class-based, builder, functional) that generate the same JSON config dict + `MachineLogic` internally, delegating to the existing `create_machine()` factory. Zero changes to existing core code. Full backward compatibility.

---

## 2. Architecture

### Integration strategy: Pure additive layer

A single new module `src/xstate_statemachine/pythonic.py` (~500-600 lines) contains all Pythonic API code. It produces `(config_dict, MachineLogic)` pairs and delegates to the existing `create_machine()`.

```
                  +----------------------+
                  |   User's code        |
                  |                      |
          +-------+--------+-----------+
          v       v        v           |
   Class-based  Builder  Functional    |
   StateMachine MachineBuilder  build_machine()
          |       |        |           |
          +-------+--------+           |
                  v                    |
          +------------------+         |
          |  _compile()      |  internal
          |  config dict  +  |<--------+
          |  MachineLogic    |
          +--------+---------+
                   v
          create_machine(config, logic=logic)   <-- existing, UNCHANGED
                   v
              MachineNode --> Interpreter / SyncInterpreter
```

### File impact

```
src/xstate_statemachine/
    __init__.py              # Add 9 new exports to __all__
    pythonic.py              # NEW -- entire Pythonic API
    factory.py               # UNCHANGED
    models.py                # UNCHANGED
    interpreter.py           # UNCHANGED
    sync_interpreter.py      # UNCHANGED
    machine_logic.py         # UNCHANGED
    logic_loader.py          # UNCHANGED
    (all other files)        # UNCHANGED
```

### New exports added to `__init__.py`

```python
"State",            # State descriptor -- works in classes AND at module level
"StateMachine",     # Base class with metaclass (class-based API)
"MachineBuilder",   # Fluent builder (builder API)
"build_machine",    # Top-level function (functional API)
"transition",       # Transition helper (functional API)
"action",           # Decorator for action functions (all styles)
"guard",            # Decorator for guard functions (all styles)
"service",          # Decorator for service functions (all styles)
```

Note: `TransitionGroup` is an internal class (not exported). Users create it
implicitly via the `|` operator on `Transition` objects.

---

## 3. `State` Class

The foundational building block shared by all three API styles. A lightweight object that holds state configuration and provides a fluent API for defining transitions.

### Constructor

```python
State(
    name: str = "",          # Auto-inferred from class attr name if empty
    *,
    initial: bool = False,   # Is this the initial state?
    final: bool = False,     # Is this a final state? (type="final")
    parallel: bool = False,  # Is this a parallel state? (type="parallel")
    on: dict = None,         # Event->target shorthand: {"CLICK": "active"}
    entry: list = None,      # Entry action names: ["logEntry"]
    exit: list = None,       # Exit action names: ["cleanup"]
    after: dict = None,      # Delayed transitions: {1000: "timeout"}
    invoke: dict|list = None,# Service invocation (single dict or list of dicts)
    on_done: str|dict = None,# Completion transition
    always: str|dict|list = None,  # Eventless transition (see compilation note)
    context: dict = None,    # Only meaningful at root level; silently ignored
                             # on non-root states
    states: list = None,     # Child State objects for hierarchy
)
```

**Mutual exclusion:** `final=True` and `parallel=True` cannot both be set.
Raises `InvalidConfigError` at compile time if both are True.

### Transition API (fluent)

```python
# Single transition (event is REQUIRED -- see note below)
idle.to(running, event="START")               # explicit event name
idle.to(running, event="START", guard="isReady")  # with guard
idle.to(running, event="GO", actions=["log"]) # with actions
idle.to(running, event="GO", guard="canGo", actions=["prepare"])

# Combine transitions with |
cycle = red.to(green, event="TIMER") | green.to(yellow, event="TIMER") | yellow.to(red, event="TIMER")

# Internal transition (no target, just actions)
idle.internal("HEARTBEAT", actions=["logHeartbeat"])

# Self-transition with reenter
loading.to(loading, event="RETRY", reenter=True, actions=["incrementCount"])
```

**`event` is required on `State.to()`.** Eventless ("always") transitions are
defined via the `always` parameter on the `State` constructor, not via `.to()`
with no event. Calling `.to()` without `event` raises `InvalidConfigError`.

### Hierarchy (nested states)

```python
# Via states parameter
traffic = State("traffic", initial=True, states=[
    State("red", initial=True),
    State("yellow"),
    State("green"),
])

# Via nested class in StateMachine (see Section 6)
```

### State-specific decorators

`State` provides `.enter` and `.exit` decorator shortcuts. **These are only
valid inside a `StateMachine` class** (class-based API). Using them at module
level raises `InvalidConfigError` at compile time.

```python
# Inside a StateMachine class:
@red.enter
def on_red(self, i, ctx, e, a):
    print("Stop!")

@red.exit
def leaving_red(self, i, ctx, e, a):
    print("Go!")
```

Under the hood, `@state.enter` marks the function as `_xsm_type = "action"`
with an auto-generated name, and appends that name to the State's `entry` list.

### Compilation output examples

```python
State("idle", initial=True, on={"START": "running"})
# compiles to:
# {"idle": {"on": {"START": "running"}}}
# with initial="idle" set on the parent

State("parent", on_done="next")
# compiles to:
# {"parent": {"onDone": {"target": "next"}}}

State("loading", invoke={"src": "fetchData", "onDone": "success"})
# compiles to:
# {"loading": {"invoke": {"src": "fetchData", "onDone": "success"}}}

State("loading", invoke=[
    {"src": "svc1", "onDone": "a"},
    {"src": "svc2", "onDone": "b"},
])
# compiles to:
# {"loading": {"invoke": [{"src": "svc1", "onDone": "a"}, {"src": "svc2", "onDone": "b"}]}}
```

### `always` compilation

The `always` parameter compiles to `"on": {"": ...}` (empty-string event key),
which the existing library already supports as eventless/transient transitions.
No core changes required.

```python
State("checking", always={"target": "done", "guard": "isValid"})
# compiles to:
# {"checking": {"on": {"": {"target": "done", "guard": "isValid"}}}}

State("routing", always=[
    {"target": "admin", "guard": "isAdmin"},
    {"target": "user"},
])
# compiles to:
# {"routing": {"on": {"": [{"target": "admin", "guard": "isAdmin"}, {"target": "user"}]}}}
```

---

## 4. `Transition` Class & `TransitionGroup`

### `Transition` object (returned by `State.to()`)

```python
class Transition:
    source: State       # Where the transition starts
    target: State       # Where it goes (None for internal transitions)
    event: str          # Event name (e.g., "CLICK") -- REQUIRED
    guard: str          # Guard name (optional, default None)
    actions: list       # Action names (optional, default [])
    reenter: bool       # Force exit/re-entry on self-transition (default False)
    internal: bool      # Internal transition, no state change (default False)
```

### `TransitionGroup` (internal, not exported)

```python
class TransitionGroup:
    """A collection of Transition objects, created by the | operator."""
    transitions: List[Transition]

    def __or__(self, other: "Transition | TransitionGroup") -> "TransitionGroup":
        """Combine with another transition or group."""
```

Users never instantiate `TransitionGroup` directly. It is created implicitly:

```python
# | creates a TransitionGroup
group = idle.to(a, event="GO") | idle.to(b, event="GO", guard="check")
# type(group) == TransitionGroup
# group.transitions == [Transition(..., target=a), Transition(..., target=b)]
```

### Combining transitions with `|`

```python
# Independent transitions (different events or sources)
cycle = (
    red.to(green, event="TIMER")
    | green.to(yellow, event="TIMER")
    | yellow.to(red, event="TIMER")
)

# Conditional transitions (same source+event, different guards)
resolve = (
    pending.to(approved, event="REVIEW", guard="isApproved")
    | pending.to(rejected, event="REVIEW", guard="isRejected")
    | pending.to(needs_info, event="REVIEW")  # fallback
)
```

Compiler groups by `(source, event)`:
- Single transition: `"EVENT": {"target": "x", "guard": "g"}`
- Multiple for same source+event: `"EVENT": [{"target": "x", "guard": "g1"}, {"target": "y"}]`

### The `transition()` standalone function (functional API)

```python
def transition(
    source: State,
    event: str,
    target: State,
    *,
    guard: str = None,
    actions: list = None,
    reenter: bool = False,
    internal: bool = False,
) -> Transition:
```

`event` is a required positional argument (not optional).
Equivalent to `source.to(target, event=event, ...)`.

### Compilation rules for special transition types

**Internal transitions** (`internal=True` or `State.internal()`):
The compiled config **omits the `target` key**. The `target` attribute on the
Transition object is ignored.

```python
idle.internal("HEARTBEAT", actions=["logHeartbeat"])
# compiles to: "HEARTBEAT": {"actions": ["logHeartbeat"]}
# (no "target" key)
```

**Reenter transitions** (`reenter=True`):
The compiled config includes `"reenter": true`.

```python
loading.to(loading, event="RETRY", reenter=True, actions=["inc"])
# compiles to: "RETRY": {"target": "loading", "reenter": true, "actions": ["inc"]}
```

---

## 5. Decorators: `@action`, `@guard`, `@service`

### Mechanism

Each decorator attaches `_xsm_type` and `_xsm_name` attributes to the function. The function itself remains unchanged and callable with the existing library signatures.

```python
@action
def increment_counter(i, ctx, e, a):
    ctx["counter"] += 1

# increment_counter._xsm_type == "action"
# increment_counter._xsm_name == "incrementCounter"  (auto snake->camel)
```

### Explicit name override

```python
@action("customName")
def my_func(i, ctx, e, a): ...
# Registered as "customName"
```

### All three decorators

```python
# Actions -- signature: (interpreter, ctx, event, action_def) -> None
@action
def log_entry(i, ctx, e, a):
    print(f"Entered with {ctx}")

# Guards -- signature: (ctx, event) -> bool (MUST be synchronous)
@guard
def can_retry(ctx, e) -> bool:
    return ctx.get("attempts", 0) < 3

# Services -- signature: (interpreter, ctx, event) -> Any (can be async)
@service
async def fetch_data(i, ctx, e):
    return await http_client.get("/api/data")
```

### Usage across all three styles

**Class-based:** Decorators on methods (with `self`). The `self` parameter is
bound during compilation (see Section 9).

**Functional:** Decorators on module-level functions (no `self`).

**Builder:** Explicit `.action(name, fn)` registration, also accepts decorated
functions.

### Collection during compilation

| Style | How decorators are found |
|---|---|
| Class-based | Metaclass iterates class namespace, finds callables with `_xsm_type` |
| Functional | User passes decorated functions in `actions=`, `guards=`, `services=` lists |
| Builder | Explicit `.action()`, `.guard()`, `.service()` registration |

No implicit module scanning. Everything is explicit.

---

## 6. `StateMachine` Base Class (Class-Based API)

### Basic usage

```python
class TrafficLight(StateMachine):
    machine_id = "trafficLight"        # optional, defaults to class name
    initial_context = {"count": 0}     # optional

    red = State(initial=True)
    yellow = State()
    green = State()

    timer = red.to(green, event="TIMER") | green.to(yellow, event="TIMER") | yellow.to(red, event="TIMER")

    @action
    def increment_count(self, i, ctx, e, a):
        ctx["count"] += 1

    @guard
    def is_enabled(self, ctx, e) -> bool:
        return ctx.get("enabled", True)

    @red.enter
    def on_red(self, i, ctx, e, a):
        print("Stop!")
```

### Creating and running

```python
machine = TrafficLight.create_machine()
machine = TrafficLight.create_machine(context={"count": 10})

# Works with both interpreters
interp = SyncInterpreter(machine).start()
interp.send("TIMER")
```

### Metaclass responsibilities (`_StateMachineMeta`)

Runs at class-definition time. Does exactly four things:

1. **Collect `State` instances** -- scans namespace for `State` instances, sets
   `.name` from attribute name if not set.
2. **Collect nested `State` subclasses** -- scans for inner classes that
   inherit from `State`. These are treated as compound/parallel parent states.
   Their class-level `State` attributes become child states (collected
   recursively using the same logic). The inner class itself is replaced with a
   `State` instance whose `states` list contains the collected children.
3. **Collect `Transition`/`TransitionGroup` attributes** -- scans for
   transition objects.
4. **Collect decorated methods** -- finds all methods with `_xsm_type` marker,
   stores them in `cls._xsm_decorated`.

Does NOT: instantiate anything, modify parent classes, touch existing library
code, or register globally.

### How nested `State` subclasses work

When the metaclass encounters an inner class like:

```python
class moving(State):
    up = State(initial=True)
    down = State()
```

It processes it as follows:

1. Detects `moving` is a class (not a `State` instance) that inherits from
   `State`.
2. Scans `moving`'s namespace for `State` instances (`up`, `down`) and
   collects them as children.
3. Replaces the `moving` class attribute with a `State` instance:
   `State("moving", states=[up_state, down_state])` where child initial/type
   flags are preserved.
4. This means `moving.up` in transition expressions like
   `idle.to(moving.up, event="CALL_UP")` works because `moving` is the class
   at class-definition time (when the transition expression is evaluated),
   and `up` is a class attribute on it.

### `State.__init_subclass__` for keyword arguments

To support `class monitoring(State, parallel=True):`, `State` implements
`__init_subclass__`:

```python
class State:
    def __init_subclass__(cls, *, initial=False, final=False,
                          parallel=False, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._xsm_initial = initial
        cls._xsm_final = final
        cls._xsm_parallel = parallel
```

The metaclass reads these class-level flags when converting the nested class
into a `State` instance.

### `create_machine()` classmethod flow

```python
@classmethod
def create_machine(cls, context=None) -> MachineNode:
    # 1. Build config dict from collected States + Transitions
    config = _compile_config(
        machine_id=cls.machine_id or cls.__name__,
        states=cls._xsm_states,
        transitions=cls._xsm_transitions,
        context=context or cls.initial_context,
    )
    # 2. Build MachineLogic from decorated methods
    instance = cls()
    logic = _compile_logic_from_instance(
        instance=instance,
        decorated=cls._xsm_decorated,
    )
    # 3. Delegate to existing factory
    return create_machine(config, logic=logic)
```

### Hierarchical states (nested classes)

```python
class Elevator(StateMachine):
    idle = State(initial=True)
    stopped = State(final=True)

    class moving(State):
        up = State(initial=True)
        down = State()

    go_up = idle.to(moving.up, event="CALL_UP")
    arrive = moving.to(stopped, event="ARRIVED")
```

### Parallel states

```python
class Dashboard(StateMachine):
    class monitoring(State, parallel=True):
        class cpu(State):
            idle = State(initial=True)
            alert = State()
        class memory(State):
            normal = State(initial=True)
            warning = State()
```

### Services and invoke

```python
class DataFetcher(StateMachine):
    idle = State(initial=True)
    loading = State(invoke={
        "src": "fetchData",
        "onDone": "success",
        "onError": "error",
    })
    success = State(final=True)
    error = State()

    retry = error.to(loading, event="RETRY")

    @service
    async def fetch_data(self, i, ctx, e):
        return await http_client.get(ctx["url"])
```

### After (delayed transitions)

```python
class SessionTimeout(StateMachine):
    active = State(initial=True, after={
        30000: {"target": "warning", "actions": ["notifyUser"]},
    })
    warning = State(after={5000: "expired"})
    expired = State(final=True)

    @action
    def notify_user(self, i, ctx, e, a):
        print("Session expiring soon!")
```

---

## 7. `MachineBuilder` (Fluent Builder API)

### Basic usage

```python
machine = (
    MachineBuilder("trafficLight")
    .context({"count": 0})
    .state("red", initial=True, entry=["logStop"])
    .state("yellow")
    .state("green")
    .transition("red", "TIMER", "green")
    .transition("green", "TIMER", "yellow")
    .transition("yellow", "TIMER", "red")
    .action("logStop", lambda i, ctx, e, a: print("Stop!"))
    .guard("isEnabled", lambda ctx, e: ctx.get("enabled", True))
    .build()
)
```

### Full method API

```python
class MachineBuilder:
    def __init__(self, machine_id: str): ...

    # Structure
    def context(self, ctx: dict) -> "MachineBuilder": ...
    def state(self, name, *, initial=False, final=False, parallel=False,
              on=None, entry=None, exit=None, after=None,
              invoke=None,       # dict or list of dicts
              on_done=None, always=None) -> "MachineBuilder": ...
    def transition(self, source, event, target, *, guard=None, actions=None,
                   reenter=False, internal=False) -> "MachineBuilder": ...

    # Hierarchy
    def child_states(
        self,
        parent: str,             # Name of a previously added state
        *,
        initial: str = None,     # Name of the initial child state
        states: dict = None,     # {"childName": {**state_kwargs}} or list of State objects
        parallel: bool = False,  # Whether the parent is parallel
    ) -> "MachineBuilder": ...

    # Logic registration
    def action(self, name: str, fn: Callable) -> "MachineBuilder": ...
    def guard(self, name: str, fn: Callable) -> "MachineBuilder": ...
    def service(self, name: str, fn: Callable) -> "MachineBuilder": ...

    # Build
    def build(self, context: dict = None) -> MachineNode: ...
```

Every method except `build()` returns `self` for chaining.

### `child_states()` usage example

```python
machine = (
    MachineBuilder("elevator")
    .context({"floor": 1})
    .state("idle", initial=True)
    .state("moving")
    .child_states("moving", initial="up", states={
        "up": {},
        "down": {},
    })
    .state("stopped", final=True)
    .transition("idle", "CALL_UP", "moving.up")
    .transition("moving", "ARRIVED", "stopped")
    .build()
)
```

`parent` must reference a state name already added via `.state()`. If `parent`
is not found, `InvalidConfigError` is raised at `.child_states()` call time.

### `build()` internals

```python
def build(self, context=None) -> MachineNode:
    config = {
        "id": self._machine_id,
        "initial": self._initial_state,
        "context": context or self._context,
        "states": self._compile_states(),
    }
    logic = MachineLogic(
        actions=self._actions,
        guards=self._guards,
        services=self._services,
    )
    return create_machine(config, logic=logic)
```

---

## 8. `build_machine()` (Functional API)

### Basic usage

```python
from xstate_statemachine import State, transition, action, guard, build_machine

idle = State("idle", initial=True)
loading = State("loading")
success = State("success", final=True)
error = State("error")

fetch = idle.to(loading, event="FETCH")
retry = error.to(loading, event="RETRY", guard="canRetry")

@action
def store_data(i, ctx, e, a):
    ctx["data"] = e.data

@guard
def can_retry(ctx, e) -> bool:
    return ctx.get("attempts", 0) < 3

machine = build_machine(
    id="dataFetcher",
    states=[idle, loading, success, error],
    transitions=[fetch, retry],
    actions=[store_data],
    guards=[can_retry],
    context={"attempts": 0, "data": None},
)
```

### Function signature

```python
def build_machine(
    *,
    id: str,
    states: List[State],
    transitions: List[Transition | TransitionGroup] = None,
    actions: List[Callable] = None,
    guards: List[Callable] = None,
    services: List[Callable] = None,
    context: dict = None,
) -> MachineNode:
```

All parameters are keyword-only.

### Undecorated functions supported

Functions without decorators are auto-registered using snake_case to camelCase name conversion (same as existing `LogicLoader`):

```python
def increment_counter(i, ctx, e, a):
    ctx["counter"] += 1

machine = build_machine(
    id="myMachine",
    states=[idle, running],
    transitions=[idle.to(running, event="GO", actions=["incrementCounter"])],
    actions=[increment_counter],  # auto-registered as "incrementCounter"
)
```

### Internals

```python
def build_machine(*, id, states, transitions=None, actions=None,
                  guards=None, services=None, context=None) -> MachineNode:
    config = _compile_config(
        machine_id=id,
        states=states,
        transitions=transitions or [],
        context=context,
    )
    logic = _compile_logic_from_functions(
        actions=actions or [],
        guards=guards or [],
        services=services or [],
    )
    return create_machine(config, logic=logic)
```

---

## 9. Shared Compiler Internals

### Internal functions

```python
def _compile_config(
    machine_id: str,
    states: List[State],
    transitions: List[Transition | TransitionGroup],
    context: dict | None,
) -> Dict[str, Any]:
    """Convert State/Transition objects into a JSON-equivalent config dict."""

def _compile_logic_from_functions(
    actions: List[Callable],
    guards: List[Callable],
    services: List[Callable],
) -> MachineLogic:
    """Convert decorated/raw callables into a MachineLogic instance."""

def _compile_logic_from_instance(
    instance: object,
    decorated: List[Callable],
) -> MachineLogic:
    """Convert class instance methods into a MachineLogic instance.

    Uses functools.partial(method, instance) to bind `self`, so the resulting
    callable matches the existing signatures expected by the interpreter:
      - Actions:  (interpreter, ctx, event, action_def) -> None
      - Guards:   (ctx, event) -> bool
      - Services: (interpreter, ctx, event) -> Any
    """

def _snake_to_camel(name: str) -> str:
    """Convert snake_case to camelCase. Matches existing LogicLoader behavior."""
```

### `_compile_config` flow

1. Find initial state (the one with `initial=True`)
2. For each State, build its config dict:
   - `"type"` -> `"final"` | `"parallel"` | omitted (auto-detected by models.py)
   - `"entry"` -> from state.entry
   - `"exit"` -> from state.exit
   - `"on"` -> from state.on dict (if any), then merge Transition objects (see merge rule below)
   - `"after"` -> from state.after (keys coerced to int-castable strings)
   - `"invoke"` -> from state.invoke (dict or list, passed through as-is)
   - `"onDone"` -> from state.on_done, compiled as `{"target": value}` if string
   - `"always"` -> compiled into `"on": {"": ...}` (empty-string event key)
   - `"states"` -> recurse for child states (if any)
3. Merge transitions into source state's `"on"` dict, grouping by `(source, event)`
4. Assemble top-level config: `{"id": ..., "initial": ..., "context": ..., "states": {...}}`

### Merge rule: `State.on` dict vs `Transition` objects

When both `State.on` and `Transition` objects define transitions for the same
`(source, event)`:

**Transition objects take precedence and override `State.on` entries for the
same event.** This is because `.to()` is the more specific/intentional API.

```python
idle = State("idle", initial=True, on={"START": "running"})
go = idle.to(active, event="START", guard="isReady")

# Result: "START" uses the Transition object (with guard), NOT the on= dict entry.
# compiles to: "START": {"target": "active", "guard": "isReady"}
```

If no Transition object exists for an event, the `State.on` dict entry is used
as-is (it's already in the correct JSON config format).

### Name resolution

The compiler uses state names (strings) for target resolution, matching how `resolver.py` works. For nested states, dot-paths are generated automatically:

```python
parent = State("parent", states=[State("child1", initial=True), State("child2")])
# Transition targeting child2 compiles to: "GO": {"target": "parent.child2"}
```

### snake_case to camelCase

The compiler applies the same conversion as `LogicLoader._snake_to_camel()`:

```python
@action
def increment_counter(i, ctx, e, a): ...
# _xsm_name = "incrementCounter"
# Config uses: "actions": ["incrementCounter"]
# MachineLogic uses: {"incrementCounter": increment_counter}
```

### Transition target validation

The compiler validates that every `Transition.source` references a `State`
object present in the `states` list. If not, `InvalidConfigError` is raised.

**Target validation** (whether the target state exists) is **deferred** to the
existing `create_machine()` -> resolver chain. This is intentional: targets may
reference states in parent/sibling machines (actor model), and the Pythonic
layer does not have visibility into the full machine tree.

---

## 10. Error Handling

Errors are raised at compile time (`create_machine()` / `build()` / `build_machine()`), not at class-definition time.

| Error condition | Exception | Message |
|---|---|---|
| No `initial=True` state among non-parallel siblings | `InvalidConfigError` | `"No initial state defined. Exactly one state must have initial=True"` |
| Multiple `initial=True` at same level | `InvalidConfigError` | `"Multiple initial states: {names}. Exactly one allowed"` |
| `initial=True` on a child of a parallel parent | `InvalidConfigError` | `"State '{name}' is a child of parallel state '{parent}' and should not have initial=True. All parallel regions are active simultaneously."` |
| `final=True` and `parallel=True` both set | `InvalidConfigError` | `"State '{name}' cannot be both final and parallel"` |
| `final=True` state has `on` transitions or child states | `InvalidConfigError` | `"Final state '{name}' cannot have outgoing transitions or child states"` |
| Transition source not in states list | `InvalidConfigError` | `"Transition source '{name}' is not a defined state"` |
| Duplicate state name at same level | `InvalidConfigError` | `"Duplicate state name '{name}' at the same level"` |
| `@guard` on async function | `NotSupportedError` | `"Guard '{name}' must be synchronous (guards cannot be async)"` |
| `State.to()` called without `event` | `InvalidConfigError` | `"State.to() requires an 'event' argument. For eventless transitions, use the 'always' parameter on State()"` |
| `@state.enter` / `@state.exit` used outside StateMachine class | `InvalidConfigError` | `"@{state}.enter decorator is only valid inside a StateMachine class"` |
| `child_states()` references unknown parent | `InvalidConfigError` | `"Parent state '{name}' not found. Add it with .state() first"` |

All other validation (missing logic implementations, bad target resolution,
etc.) is handled by the existing `create_machine()` -> `MachineNode` ->
`LogicLoader` chain unchanged.

---

## 11. Testing Strategy

New file: `tests/test_pythonic.py`

### Test structure

```
TestState
    test_state_basic_attributes
    test_state_initial_flag
    test_state_final_type
    test_state_parallel_type
    test_state_name_auto_from_attribute
    test_state_nested_children
    test_state_final_and_parallel_raises
    test_state_on_done_compilation
    test_state_invoke_single_dict
    test_state_invoke_list_of_dicts

TestTransition
    test_transition_basic
    test_transition_with_guard_and_actions
    test_transition_combine_with_pipe
    test_transition_group_passed_to_build_machine
    test_transition_internal_omits_target
    test_transition_reenter_compiles_flag
    test_transition_standalone_function
    test_transition_without_event_raises

TestAlwaysTransitions
    test_always_string_compiles_to_empty_event
    test_always_dict_compiles_to_empty_event
    test_always_list_compiles_to_empty_event
    test_always_works_with_sync_interpreter
    test_always_in_builder
    test_always_in_functional

TestDecorators
    test_action_decorator_auto_name
    test_action_decorator_explicit_name
    test_guard_decorator
    test_service_decorator
    test_state_enter_exit_decorators_in_class
    test_state_enter_outside_class_raises
    test_guard_async_raises_error
    test_invalid_action_signature_raises

TestStateMachineClassBased
    test_basic_machine_creation
    test_transitions_work_with_interpreter
    test_actions_fire_on_transition
    test_guards_block_transition
    test_hierarchical_states_nested_class
    test_parallel_states_nested_class
    test_invoke_service
    test_after_delayed_transition
    test_final_state_on_done
    test_always_transition
    test_context_override
    test_entry_exit_decorators
    test_self_binding_with_functools_partial
    test_final_state_with_transitions_raises
    test_parallel_child_with_initial_raises

TestMachineBuilder
    test_basic_builder
    test_builder_transitions
    test_builder_with_logic
    test_builder_hierarchical_child_states
    test_builder_child_states_unknown_parent_raises
    test_builder_parallel
    test_builder_invoke
    test_builder_after
    test_builder_always
    test_builder_accepts_decorated_functions
    test_builder_context_override
    test_builder_on_done

TestBuildMachineFunctional
    test_basic_functional
    test_functional_with_transitions
    test_functional_with_transition_group
    test_functional_with_decorated_actions
    test_functional_with_undecorated_functions
    test_functional_hierarchical
    test_functional_invoke
    test_functional_after
    test_functional_always
    test_functional_guards
    test_functional_on_done

TestMergeRules
    test_transition_overrides_state_on_for_same_event
    test_state_on_preserved_when_no_transition_conflict
    test_mixed_on_and_transitions_different_events

TestCompileConfig
    test_config_output_matches_json_format
    test_snake_to_camel_conversion
    test_nested_state_dot_paths
    test_always_compiles_to_empty_string_event

TestErrorHandling
    test_no_initial_state_raises
    test_multiple_initial_states_raises
    test_unknown_transition_source_raises
    test_duplicate_state_name_raises
    test_async_guard_raises
    test_final_and_parallel_raises
    test_final_with_transitions_raises
    test_parallel_child_initial_raises
    test_to_without_event_raises
    test_enter_decorator_outside_class_raises
    test_invalid_action_signature_raises

TestBackwardCompatibility
    test_json_api_still_works_unchanged
    test_pythonic_machine_works_with_sync_interpreter
    test_pythonic_machine_works_with_async_interpreter
    test_pythonic_machine_works_with_plugins
    test_pythonic_machine_snapshot_restore
```

---

## 12. Documentation Updates

- **README.md**: Add "Pythonic API" section after "Quick Start" with examples of all three styles
- **CHANGELOG.md**: Entry under `## [Unreleased]` -> `### Added`
- **AGENTS.md**: Add Pythonic API to architecture overview and working examples

---

## 13. Style guide for which API to use

| Use case | Recommended style |
|---|---|
| Static, known-at-import-time machine | Class-based `StateMachine` |
| Machine generated from config/DB at runtime | `MachineBuilder` |
| Machine shape depends on runtime conditions | `MachineBuilder` |
| Quick script / notebook prototype | Functional `build_machine()` |
| Composing machines from reusable fragments | `MachineBuilder` |
| Teaching / examples | Functional (simplest) |
