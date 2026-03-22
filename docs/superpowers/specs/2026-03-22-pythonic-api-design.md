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
    invoke: dict = None,     # Service invocation config
    on_done: str|dict = None,# Completion transition
    always: str|dict|list = None,  # Eventless transition
    context: dict = None,    # Only valid on root/machine-level State
    states: list = None,     # Child State objects for hierarchy
)
```

### Transition API (fluent)

```python
# Single transition
idle.to(running)                              # event name set later
idle.to(running, event="START")               # explicit event name
idle.to(running, guard="isReady")             # with guard
idle.to(running, actions=["log"])             # with actions
idle.to(running, event="GO", guard="canGo", actions=["prepare"])

# Combine transitions with |
cycle = red.to(green, event="TIMER") | green.to(yellow, event="TIMER") | yellow.to(red, event="TIMER")

# Internal transition (no target, just actions)
idle.internal("HEARTBEAT", actions=["logHeartbeat"])

# Self-transition with reenter
loading.to(loading, event="RETRY", reenter=True, actions=["incrementCount"])
```

### Hierarchy (nested states)

```python
# Via states parameter
traffic = State("traffic", initial=True, states=[
    State("red", initial=True),
    State("yellow"),
    State("green"),
])

# Via nested class in StateMachine (see Section 5)
```

### State-specific decorators

`State` provides `.enter` and `.exit` decorator shortcuts for class-based usage:

```python
@red.enter
def on_red(self, i, ctx, e, a):
    print("Stop!")

@red.exit
def leaving_red(self, i, ctx, e, a):
    print("Go!")
```

Under the hood, `@state.enter` marks the function as `_xsm_type = "action"` with an auto-generated name, and appends that name to the State's `entry` list.

### Compilation output

```python
State("idle", initial=True, on={"START": "running"})
# compiles to:
# {"idle": {"on": {"START": "running"}}}
# with initial="idle" set on the parent
```

---

## 4. `Transition` Class & Helpers

### Transition object (returned by `State.to()`)

```python
class Transition:
    source: State       # Where the transition starts
    target: State       # Where it goes
    event: str          # Event name (e.g., "CLICK")
    guard: str          # Guard name (optional)
    actions: list       # Action names (optional)
    reenter: bool       # Force exit/re-entry on self-transition
    internal: bool      # Internal transition (no state change)
```

### Combining transitions with `|`

The `|` operator creates a `TransitionGroup` -- a list of transitions that gets merged during compilation:

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

Equivalent to `source.to(target, event=event, ...)`.

### Always (eventless) transitions

```python
# On State via always parameter:
checking = State("checking", always={"target": "done", "guard": "isValid"})

# Or via Transition with no event:
checking.to(done, guard="isValid")  # event="" becomes always transition
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

**Class-based:** Decorators on methods (with `self`).
**Functional:** Decorators on module-level functions (no `self`).
**Builder:** Explicit `.action(name, fn)` registration, also accepts decorated functions.

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

1. **Collect `State` attributes** -- scans namespace for `State` instances, sets `.name` from attribute name if not set
2. **Collect `Transition`/`TransitionGroup` attributes** -- scans for transition objects
3. **Collect decorated methods** -- finds all methods with `_xsm_type` marker
4. **Attach `create_machine` classmethod** -- adds the factory method

Does NOT: instantiate anything, modify parent classes, touch existing library code, or register globally.

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
              on=None, entry=None, exit=None, after=None, invoke=None,
              on_done=None, always=None) -> "MachineBuilder": ...
    def transition(self, source, event, target, *, guard=None, actions=None,
                   reenter=False, internal=False) -> "MachineBuilder": ...

    # Hierarchy
    def child_states(self, parent, *, initial=None, states=None,
                     parallel=False) -> "MachineBuilder": ...

    # Logic registration
    def action(self, name, fn) -> "MachineBuilder": ...
    def guard(self, name, fn) -> "MachineBuilder": ...
    def service(self, name, fn) -> "MachineBuilder": ...

    # Build
    def build(self, context=None) -> MachineNode: ...
```

Every method except `build()` returns `self` for chaining.

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
    """Convert class instance methods into a MachineLogic (binds self)."""

def _snake_to_camel(name: str) -> str:
    """Convert snake_case to camelCase. Matches existing LogicLoader behavior."""
```

### `_compile_config` flow

1. Find initial state (the one with `initial=True`)
2. For each State, build its config dict (type, entry, exit, on, after, invoke, onDone, always, nested states)
3. Merge transitions into source state's `"on"` dict, grouping by `(source, event)`
4. Assemble top-level config: `{"id": ..., "initial": ..., "context": ..., "states": {...}}`

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

---

## 10. Error Handling

Errors are raised at compile time (`create_machine()` / `build()` / `build_machine()`), not at class-definition time.

| Error condition | Exception | Message |
|---|---|---|
| No `initial=True` state among siblings | `InvalidConfigError` | `"No initial state defined. Exactly one state must have initial=True"` |
| Multiple `initial=True` at same level | `InvalidConfigError` | `"Multiple initial states: {names}. Exactly one allowed"` |
| Transition references unknown state | `InvalidConfigError` | `"Transition source '{name}' is not a defined state"` |
| Duplicate state name at same level | `InvalidConfigError` | `"Duplicate state name '{name}' at the same level"` |
| Decorated function has invalid signature | `InvalidConfigError` | `"Action '{name}' has invalid signature..."` |
| `@guard` on async function | `NotSupportedError` | `"Guard '{name}' must be synchronous"` |

All other validation (missing logic, bad targets) handled by existing `create_machine()` chain.

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

TestTransition
    test_transition_basic
    test_transition_with_guard_and_actions
    test_transition_combine_with_pipe
    test_transition_internal
    test_transition_reenter
    test_transition_standalone_function

TestDecorators
    test_action_decorator_auto_name
    test_action_decorator_explicit_name
    test_guard_decorator
    test_service_decorator
    test_state_enter_exit_decorators
    test_guard_async_raises_error

TestStateMachineClassBased
    test_basic_machine_creation
    test_transitions_work_with_interpreter
    test_actions_fire_on_transition
    test_guards_block_transition
    test_hierarchical_states
    test_parallel_states
    test_invoke_service
    test_after_delayed_transition
    test_final_state_on_done
    test_always_transition
    test_context_override
    test_entry_exit_decorators

TestMachineBuilder
    test_basic_builder
    test_builder_transitions
    test_builder_with_logic
    test_builder_hierarchical
    test_builder_parallel
    test_builder_invoke
    test_builder_after
    test_builder_accepts_decorated_functions

TestBuildMachineFunctional
    test_basic_functional
    test_functional_with_transitions
    test_functional_with_decorated_actions
    test_functional_with_undecorated_functions
    test_functional_hierarchical
    test_functional_invoke
    test_functional_after
    test_functional_guards

TestCompileConfig
    test_config_output_matches_json_format
    test_snake_to_camel_conversion
    test_nested_state_dot_paths

TestErrorHandling
    test_no_initial_state_raises
    test_multiple_initial_states_raises
    test_unknown_transition_source_raises
    test_duplicate_state_name_raises
    test_async_guard_raises

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
