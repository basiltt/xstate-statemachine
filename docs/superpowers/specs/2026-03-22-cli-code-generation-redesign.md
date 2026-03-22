# CLI Code Generation Redesign

> Comprehensive upgrade of the `xsm generate-template` CLI to support Pythonic API
> code generation, production-quality output, and a strategy-based architecture.

## Problem

The current CLI (`xsm gt`) only generates JSON-based boilerplate in two styles
(`class` and `function`). With the new Pythonic API (`StateMachine`, `MachineBuilder`,
`build_machine()`), the CLI cannot generate code that uses these modern APIs. The
existing generated code also lacks production-quality features like rich docstrings,
error handling, and structured logging.

## Goals

1. Generate Pythonic API code from JSON configs (JSON-to-Pythonic conversion)
2. Support all three Pythonic styles: `pythonic-class`, `pythonic-builder`, `pythonic-functional`
3. Add production-quality features to ALL templates: type hints, docstrings, error handling, logging
4. Maintain full backward compatibility with existing `--style` flag (deprecation warning)
5. Support hierarchical parent/child machine generation for Pythonic templates
6. Template-aware async defaults (JSON templates default async, Pythonic templates default sync)
7. Bump version to 0.5.0 to reflect the new feature set

## Non-Goals

- Blank scaffold generation (no JSON input) -- not in scope
- Jinja2 or external template engine -- stay dependency-free
- Removing existing `--style` flag -- deprecate only, remove in future v0.6.0

---

## CLI Interface Changes

### New `--template` / `-t` Flag

| Value                  | Description                                              | Default Async |
|------------------------|----------------------------------------------------------|---------------|
| `class-json`           | Class-based logic with JSON config loading (current)     | Yes           |
| `function-json`        | Standalone functions with JSON config loading (current)  | Yes           |
| `pythonic-class`       | `StateMachine` subclass with declarative states          | No            |
| `pythonic-builder`     | `MachineBuilder` fluent API                              | No            |
| `pythonic-functional`  | `build_machine()` functional style                       | No            |

**Default:** `class-json` (preserves current behavior).

### Backward Compatibility

- `--style class` maps to `--template class-json` and emits a deprecation
  warning via `warnings.warn()`:
  `DeprecationWarning: --style is deprecated, use --template class-json instead. Will be removed in v0.6.0`
- `--style function` maps to `--template function-json` with the same warning.
- If both `--style` and `--template` are provided: error
  `"Cannot use both --style and --template. Use --template only."`
- The `--style` flag remains in the parser with `choices=["class", "function"]`.
- The deprecation mechanism uses `warnings.warn(..., DeprecationWarning, stacklevel=2)`
  so tests can verify it with `pytest.warns(DeprecationWarning)`.

### Async Mode Defaults

The `--async-mode` argparse default changes from `"yes"` to `None`. The actual
default is resolved after template selection:

- If `--async-mode` is explicitly provided: use that value.
- If `--async-mode` is `None` (not provided):
  - JSON templates (`class-json`, `function-json`): default to async (True)
  - Pythonic templates (`pythonic-*`): default to sync (False)

### Behavior of `--file-count` with Pythonic Templates

- `--file-count 2` (default): generates separate `*_logic.py` and `*_runner.py`
  files, same as JSON templates.
- `--file-count 1`: merges logic and runner into a single file. For Pythonic
  templates, the merge uses the same import-dedup logic as JSON templates --
  the `_merge_code_for_single_file()` function in `__main__.py` handles this
  generically by extracting imports and joining bodies.

### Behavior of `--loader` with Pythonic Templates

The `--loader` flag is **ignored** for Pythonic templates. Pythonic templates use
`@action`, `@guard`, `@service` decorators which are compiled directly into
`MachineLogic` -- there is no need for a `LogicLoader` auto-discovery pass. If
the user explicitly passes `--loader yes` with a Pythonic template, the flag is
silently ignored (no warning, no error). The `loader` field in
`GenerationContext` remains for JSON strategies that use it.

### Behavior of `--force` with Pythonic Templates

The `--force` flag works identically for all templates -- it controls whether
existing files are overwritten without prompting. No template-specific behavior.

---

## Architecture: Strategy Pattern

### File Layout

```
src/xstate_statemachine/cli/
  __main__.py          # Entry point (modified: template routing)
  args.py              # Argument parser (modified: --template flag, deprecation)
  extractor.py         # JSON extraction (unchanged)
  utils.py             # Utilities (unchanged)
  generator.py         # Thin orchestrator (backward-compat public API delegates to strategies)
  strategies/
    __init__.py        # Exports BaseStrategy, STRATEGY_REGISTRY, get_strategy()
    base.py            # Abstract BaseStrategy + GenerationContext dataclass
    _shared.py         # Shared helpers (see _shared.py specification below)
    class_json.py      # ClassJsonStrategy (extracted from current generator.py)
    function_json.py   # FunctionJsonStrategy (extracted from current generator.py)
    pythonic_class.py      # PythonicClassStrategy (new)
    pythonic_builder.py    # PythonicBuilderStrategy (new)
    pythonic_functional.py # PythonicFunctionalStrategy (new)
```

### BaseStrategy Interface

```python
from abc import ABC, abstractmethod
import dataclasses
from typing import Any, Dict, List, Optional, Set, Type


@dataclasses.dataclass
class GenerationContext:
    """All inputs needed by any strategy to generate code."""

    actions: Set[str]
    guards: Set[str]
    services: Set[str]
    is_async: bool
    log: bool
    machine_name: str           # snake_case name for filenames
    machine_id: str             # original camelCase ID from JSON
    machine_names: List[str]    # all snake_case names (multi-machine)
    machine_ids: List[str]      # all original camelCase IDs
    file_count: int
    configs: List[Dict[str, Any]]
    json_filenames: List[str]
    hierarchy: bool
    sleep: bool
    sleep_time: int
    loader: bool
    style: Optional[str] = None  # "class"/"function" for JSON strategies


class BaseStrategy(ABC):
    """Abstract base for code generation strategies."""

    @abstractmethod
    def generate_logic(self, ctx: GenerationContext) -> str:
        """Generate the logic/implementation code."""

    @abstractmethod
    def generate_runner(self, ctx: GenerationContext) -> str:
        """Generate the runner/execution code."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable template name."""
```

### Strategy Registry

```python
from typing import Dict, Type
from .base import BaseStrategy
from .class_json import ClassJsonStrategy
from .function_json import FunctionJsonStrategy
from .pythonic_class import PythonicClassStrategy
from .pythonic_builder import PythonicBuilderStrategy
from .pythonic_functional import PythonicFunctionalStrategy

STRATEGY_REGISTRY: Dict[str, Type[BaseStrategy]] = {
    "class-json": ClassJsonStrategy,
    "function-json": FunctionJsonStrategy,
    "pythonic-class": PythonicClassStrategy,
    "pythonic-builder": PythonicBuilderStrategy,
    "pythonic-functional": PythonicFunctionalStrategy,
}


def get_strategy(template: str) -> BaseStrategy:
    """Look up and instantiate the strategy for a template name."""
    cls = STRATEGY_REGISTRY.get(template)
    if cls is None:
        raise InvalidConfigError(f"Unknown template: {template}")
    return cls()
```

### Generator Backward Compatibility

`generator.py` retains its existing public functions (`generate_logic_code`,
`generate_runner_code`) unchanged. Internally they delegate to
`ClassJsonStrategy` or `FunctionJsonStrategy` based on the `style` parameter.
Existing callers and tests work without modification.

### `_shared.py` Specification

The `_shared.py` module provides reusable helper functions used across multiple
strategies:

```python
def generate_module_header(title: str, file_count: int) -> str:
    """Generate the file header comment block."""

def generate_imports(
    is_async: bool,
    services: Set[str],
    template_type: str,
) -> str:
    """Generate import statements appropriate for the template type.

    For JSON templates: imports Interpreter/SyncInterpreter, Event, etc.
    For Pythonic templates: imports State, StateMachine/MachineBuilder/
    build_machine, action, guard, service, etc.
    """

def generate_logger_setup(log: bool) -> str:
    """Generate logger configuration lines."""

def generate_action_docstring(
    original_name: str, component_type: str
) -> str:
    """Generate a rich docstring with Args section for a callback."""

def generate_error_handling(
    original_name: str,
    component_type: str,
    body_lines: List[str],
    indent: str,
) -> str:
    """Wrap body lines in try/except with logger.exception."""

def snake_case_name(camel_name: str) -> str:
    """Convert camelCase to snake_case (delegates to utils.camel_to_snake)."""

def pascal_case_name(snake_name: str) -> str:
    """Convert snake_case to PascalCase for class names."""
```

---

## Generated Code: Pythonic Templates

All three Pythonic templates convert JSON state machine configs into pure-Python
code using the Pythonic API. They share these production-quality features:

- Full type hints using the `typing` module (Python 3.9+ compatible)
- Docstrings on every class, function, and method (with `Args:` sections)
- Logging setup with a named module logger
- `# TODO: implement` markers in action/guard/service stubs
- `snake_case` function names auto-converted from `camelCase` JSON names
- Error handling with try/except + `logger.exception()` + re-raise
- `if __name__ == "__main__":` runner guard

### JSON-to-Pythonic Conversion Algorithm

The core conversion from JSON config to Pythonic API code follows these rules:

1. **States**: Each key in `config["states"]` becomes a `State()` instance.
   - `"initial"` key -> `State(initial=True)` on the matching state
   - `"type": "final"` -> `State(final=True)`
   - `"type": "parallel"` -> `State(parallel=True)`
   - `"entry"` -> `State(entry=[...])`
   - `"exit"` -> `State(exit_actions=[...])`
   - `"invoke"` -> `State(invoke={...})`
   - `"after"` -> `State(after={...})`
   - `"always"` -> `State(always=[...])`
   - `"states"` (nested) -> `State(states={...})` for child states
   - `"onDone"` -> `State(on_done=...)` for compound states

2. **Transitions**: Each `"on"` event in the JSON becomes a `.to()` call:
   - `"on": {"EVENT": "target"}` -> `source.to(target_state, event="EVENT")`
   - `"on": {"EVENT": {"target": "t", "actions": "a"}}` ->
     `source.to(target_state, event="EVENT", actions="a")`
   - `"on": {"EVENT": {"target": "t", "cond": "g"}}` ->
     `source.to(target_state, event="EVENT", guard="g")`
   - `"on": {"EVENT": [trans1, trans2]}` -> multiple `.to()` calls combined
     with `|` operator into a `TransitionGroup`
   - Self-transitions (no target or target == source) -> `state.to(state, ...)`

3. **Actions/Guards/Services**: Each unique name from the JSON becomes a
   decorated function stub:
   - camelCase JSON name -> snake_case Python function name
   - `@action` / `@guard` / `@service` decorator applied
   - Full type-annotated signature with docstring and error handling

### pythonic-class (StateMachine subclass)

Generates a `StateMachine` subclass with:
- `machine_id` class attribute set to the JSON `id`
- `initial_context` class attribute set to the JSON `context`
- `State` instances as class attributes (one per state)
- Transition definitions via `state.to(target, event=..., ...)` combined with `|`
- `@action`, `@guard`, `@service` decorated methods with `self` parameter
- `.create_machine()` classmethod call in the runner section

**Complete example output** (from the traffic light JSON config):

```python
"""Traffic Light state machine -- generated by xsm CLI."""

import logging
from typing import Any, Dict, Optional, Union

from xstate_statemachine import (
    State,
    StateMachine,
    SyncInterpreter,
    action,
    guard,
    service,
    transition,
)

logger = logging.getLogger(__name__)


class TrafficLightMachine(StateMachine):
    """Traffic Light state machine using the declarative class-based API.

    Generated from: traffic_light.json
    """

    machine_id = "trafficLight"
    initial_context = {"count": 0}

    green = State(initial=True, entry=["logEnter"])
    yellow = State()
    red = State(invoke={"src": "fetchData", "onDone": "green"})

    # Transitions
    TIMER = (
        green.to(yellow, event="TIMER", actions="increment")
        | yellow.to(red, event="TIMER", guard="isReady")
        | red.to(green, event="TIMER")
    )

    # -----------------------------------------------------------------------
    # Actions
    # -----------------------------------------------------------------------
    @action
    def log_enter(
        self,
        interpreter: SyncInterpreter,
        context: Dict[str, Any],
        event: Any,
        action_def: Any,
    ) -> None:
        """Execute the ``logEnter`` action.

        Args:
            interpreter: The running interpreter instance.
            context: Mutable machine context dictionary.
            event: The event that triggered this action.
            action_def: Metadata about the action being executed.
        """
        logger.info("Executing action: logEnter")
        try:
            # TODO: implement action logic
            pass
        except Exception:
            logger.exception("Action 'logEnter' failed")
            raise

    @action
    def increment(
        self,
        interpreter: SyncInterpreter,
        context: Dict[str, Any],
        event: Any,
        action_def: Any,
    ) -> None:
        """Execute the ``increment`` action.

        Args:
            interpreter: The running interpreter instance.
            context: Mutable machine context dictionary.
            event: The event that triggered this action.
            action_def: Metadata about the action being executed.
        """
        logger.info("Executing action: increment")
        try:
            # TODO: implement action logic
            pass
        except Exception:
            logger.exception("Action 'increment' failed")
            raise

    # -----------------------------------------------------------------------
    # Guards
    # -----------------------------------------------------------------------
    @guard
    def is_ready(
        self,
        context: Dict[str, Any],
        event: Any,
    ) -> bool:
        """Evaluate the ``isReady`` guard.

        Args:
            context: Current machine context dictionary.
            event: The event being evaluated.
        """
        logger.info("Evaluating guard: isReady")
        # TODO: implement guard logic
        return True

    # -----------------------------------------------------------------------
    # Services
    # -----------------------------------------------------------------------
    @service
    def fetch_data(
        self,
        interpreter: SyncInterpreter,
        context: Dict[str, Any],
        event: Any,
    ) -> Dict[str, Any]:
        """Run the ``fetchData`` service.

        Args:
            interpreter: The running interpreter instance.
            context: Mutable machine context dictionary.
            event: The event that triggered this service.
        """
        logger.info("Running service: fetchData")
        try:
            # TODO: implement service logic
            return {"result": "done"}
        except Exception:
            logger.exception("Service 'fetchData' failed")
            raise


if __name__ == "__main__":
    machine = TrafficLightMachine.create_machine()
    interpreter = SyncInterpreter(machine)
    interpreter.start()

    logger.info(
        f"Initial state: {interpreter.current_state_ids}"
    )

    # Simulate events
    interpreter.send("TIMER")

    interpreter.stop()
```

### pythonic-builder (MachineBuilder fluent API)

The `MachineBuilder` API uses a fluent `.state(name, **kwargs).transition()`
chain -- it does **not** accept `State` objects. Transitions are added via
`.transition(source, event, target, ...)`.

**Complete example output:**

```python
"""Traffic Light state machine -- generated by xsm CLI."""

import logging
from typing import Any, Dict, Union

from xstate_statemachine import (
    MachineBuilder,
    SyncInterpreter,
    action,
    guard,
    service,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------
@action
def log_enter(
    interpreter: SyncInterpreter,
    context: Dict[str, Any],
    event: Any,
    action_def: Any,
) -> None:
    """Execute the ``logEnter`` action.

    Args:
        interpreter: The running interpreter instance.
        context: Mutable machine context dictionary.
        event: The event that triggered this action.
        action_def: Metadata about the action being executed.
    """
    logger.info("Executing action: logEnter")
    try:
        # TODO: implement action logic
        pass
    except Exception:
        logger.exception("Action 'logEnter' failed")
        raise


@action
def increment(
    interpreter: SyncInterpreter,
    context: Dict[str, Any],
    event: Any,
    action_def: Any,
) -> None:
    """Execute the ``increment`` action.

    Args:
        interpreter: The running interpreter instance.
        context: Mutable machine context dictionary.
        event: The event that triggered this action.
        action_def: Metadata about the action being executed.
    """
    logger.info("Executing action: increment")
    try:
        # TODO: implement action logic
        pass
    except Exception:
        logger.exception("Action 'increment' failed")
        raise


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------
@guard
def is_ready(context: Dict[str, Any], event: Any) -> bool:
    """Evaluate the ``isReady`` guard.

    Args:
        context: Current machine context dictionary.
        event: The event being evaluated.
    """
    logger.info("Evaluating guard: isReady")
    # TODO: implement guard logic
    return True


# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------
@service
def fetch_data(
    interpreter: SyncInterpreter,
    context: Dict[str, Any],
    event: Any,
) -> Dict[str, Any]:
    """Run the ``fetchData`` service.

    Args:
        interpreter: The running interpreter instance.
        context: Mutable machine context dictionary.
        event: The event that triggered this service.
    """
    logger.info("Running service: fetchData")
    try:
        # TODO: implement service logic
        return {"result": "done"}
    except Exception:
        logger.exception("Service 'fetchData' failed")
        raise


def build() -> Any:
    """Build the trafficLight machine using MachineBuilder."""
    machine = (
        MachineBuilder("trafficLight")
        .context({"count": 0})
        .state("green", initial=True, entry=["logEnter"])
        .state("yellow")
        .state(
            "red",
            invoke={"src": "fetchData", "onDone": "green"},
        )
        .transition(
            "green", "TIMER", "yellow", actions=["increment"]
        )
        .transition(
            "yellow", "TIMER", "red", guard="isReady"
        )
        .transition("red", "TIMER", "green")
        .action("logEnter", log_enter)
        .action("increment", increment)
        .guard("isReady", is_ready)
        .service("fetchData", fetch_data)
        .build()
    )
    return machine


if __name__ == "__main__":
    machine = build()
    interpreter = SyncInterpreter(machine)
    interpreter.start()

    logger.info(
        f"Initial state: {interpreter.current_state_ids}"
    )

    # Simulate events
    interpreter.send("TIMER")

    interpreter.stop()
```

### pythonic-functional (build_machine function)

The `build_machine()` API accepts `states` as a `List[State]` (not a dict).
Transitions are defined via `state.to()` calls before passing states to
`build_machine()`.

**Complete example output:**

```python
"""Traffic Light state machine -- generated by xsm CLI."""

import logging
from typing import Any, Dict, Union

from xstate_statemachine import (
    State,
    SyncInterpreter,
    action,
    build_machine,
    guard,
    service,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------
@action
def log_enter(
    interpreter: SyncInterpreter,
    context: Dict[str, Any],
    event: Any,
    action_def: Any,
) -> None:
    """Execute the ``logEnter`` action.

    Args:
        interpreter: The running interpreter instance.
        context: Mutable machine context dictionary.
        event: The event that triggered this action.
        action_def: Metadata about the action being executed.
    """
    logger.info("Executing action: logEnter")
    try:
        # TODO: implement action logic
        pass
    except Exception:
        logger.exception("Action 'logEnter' failed")
        raise


@action
def increment(
    interpreter: SyncInterpreter,
    context: Dict[str, Any],
    event: Any,
    action_def: Any,
) -> None:
    """Execute the ``increment`` action.

    Args:
        interpreter: The running interpreter instance.
        context: Mutable machine context dictionary.
        event: The event that triggered this action.
        action_def: Metadata about the action being executed.
    """
    logger.info("Executing action: increment")
    try:
        # TODO: implement action logic
        pass
    except Exception:
        logger.exception("Action 'increment' failed")
        raise


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------
@guard
def is_ready(context: Dict[str, Any], event: Any) -> bool:
    """Evaluate the ``isReady`` guard.

    Args:
        context: Current machine context dictionary.
        event: The event being evaluated.
    """
    logger.info("Evaluating guard: isReady")
    # TODO: implement guard logic
    return True


# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------
@service
def fetch_data(
    interpreter: SyncInterpreter,
    context: Dict[str, Any],
    event: Any,
) -> Dict[str, Any]:
    """Run the ``fetchData`` service.

    Args:
        interpreter: The running interpreter instance.
        context: Mutable machine context dictionary.
        event: The event that triggered this service.
    """
    logger.info("Running service: fetchData")
    try:
        # TODO: implement service logic
        return {"result": "done"}
    except Exception:
        logger.exception("Service 'fetchData' failed")
        raise


def build() -> Any:
    """Build the trafficLight machine using build_machine()."""
    green = State(
        "green", initial=True, entry=["logEnter"]
    )
    yellow = State("yellow")
    red = State(
        "red",
        invoke={"src": "fetchData", "onDone": "green"},
    )

    green.to(yellow, event="TIMER", actions="increment")
    yellow.to(red, event="TIMER", guard="isReady")
    red.to(green, event="TIMER")

    machine = build_machine(
        id="trafficLight",
        states=[green, yellow, red],
        context={"count": 0},
        actions=[log_enter, increment],
        guards=[is_ready],
        services=[fetch_data],
    )
    return machine


if __name__ == "__main__":
    machine = build()
    interpreter = SyncInterpreter(machine)
    interpreter.start()

    logger.info(
        f"Initial state: {interpreter.current_state_ids}"
    )

    # Simulate events
    interpreter.send("TIMER")

    interpreter.stop()
```

---

## Production Quality Upgrades for JSON Templates

The existing `class-json` and `function-json` templates receive these upgrades:

1. **Richer docstrings** -- `Args:` section with parameter descriptions
2. **Error handling** -- try/except with `logger.exception()` and re-raise
3. **Clean signatures** -- remove `# noqa` comments from generated code
4. **Correct return types** -- `None` instead of `Awaitable[None]` for async defs
5. **Consistent formatting** -- follows Black style (project's formatter)

### Before (current generated action):

```python
async def increment(  # noqa: ignore IDE static method warning,
    self,
    interpreter: Union[Interpreter, SyncInterpreter],
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa: D401 - lib callback
) -> Awaitable[None]:  # noqa : ignore IDE return type hint warning
    """Action: `increment`."""
    logger.info("Executing action increment")
    await asyncio.sleep(0.1)  # placeholder
    # TODO: implement
```

### After (upgraded generated action):

```python
async def increment(
    self,
    interpreter: Union[Interpreter, SyncInterpreter],
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,
) -> None:
    """Execute the ``increment`` action.

    Args:
        interpreter: The running interpreter instance.
        context: Mutable machine context dictionary.
        event: The event that triggered this action.
        action_def: Metadata about the action being executed.
    """
    logger.info("Executing action: increment")
    try:
        # TODO: implement action logic
        await asyncio.sleep(0.1)  # placeholder
    except Exception:
        logger.exception("Action 'increment' failed")
        raise
```

---

## Hierarchical Machine Support (Pythonic Templates)

When `--json-parent` and `--json-child` are used with a Pythonic template:

1. **Parent machine** -- generated in the chosen Pythonic style with `invoke`
   references to child machine IDs intact in the generated State objects.
2. **Child machines** -- each child is loaded from its JSON config file at
   runtime via `create_machine()`. The child JSON configs are NOT converted
   to Pythonic code -- they remain as runtime JSON loading. This is consistent
   with how `xstate_statemachine` actors work internally (parent spawns child
   interpreters from configs).
3. **Logic stubs** -- actions, guards, and services from ALL machines (parent
   and children) are extracted and generated as stubs in the logic file, so
   the user has a complete set of callbacks to implement.
4. **Runner** -- creates the parent machine via the Pythonic API, loads child
   configs from JSON, creates interpreters for all, wires and starts them,
   simulates events for parent then each child, shuts down in reverse order
   (children first, then parent).

**Example runner snippet (pythonic-class, hierarchical):**

```python
def main() -> None:
    """Run the parent machine and spawn actor machines."""
    # Parent machine (Pythonic API)
    parent_machine = ParentMachine.create_machine()

    # Child machines (from JSON configs)
    root_dir = Path(__file__).parent
    child_cfg = json.loads(
        (root_dir / "child.json").read_text()
    )
    child_machine = create_machine(child_cfg)

    parent = SyncInterpreter(parent_machine)
    child_interp = SyncInterpreter(child_machine)

    parent.start()
    child_interp.start()

    # ... simulation events ...

    child_interp.stop()
    parent.stop()
```

---

## Testing Strategy

### Test File Structure

```
tests/tests_cli/
  test_generator.py               # Existing (kept, updated for refactor)
  test_main_execution.py           # Existing integration tests (kept)
  test_extractor.py                # Existing (kept, unchanged)
  test_args.py                     # New: --template flag, deprecation, backward compat
  test_strategy_registry.py        # New: registry lookup, unknown template errors
  test_class_json_strategy.py      # New: extracted from test_generator + upgrades
  test_function_json_strategy.py   # New: extracted from test_generator + upgrades
  test_pythonic_class_strategy.py      # New: StateMachine generation
  test_pythonic_builder_strategy.py    # New: MachineBuilder generation
  test_pythonic_functional_strategy.py # New: build_machine generation
  test_hierarchy_pythonic.py       # New: hierarchical with Pythonic templates
  test_production_quality.py       # New: type hints, docstrings, error handling in output
```

### Test Categories

1. **Backward compatibility** -- existing tests in `test_generator.py` and
   `test_main_execution.py` must pass unchanged
2. **Deprecation warnings** -- `--style class` and `--style function` emit
   `DeprecationWarning`, verified via `pytest.warns(DeprecationWarning)`
3. **Flag conflicts** -- `--style` + `--template` together produces an error
4. **Strategy registry** -- correct strategy returned for each template name,
   `InvalidConfigError` for unknown templates
5. **Pythonic output correctness** -- generated code contains correct imports,
   class/function definitions, State objects, transitions, decorators
6. **Production quality assertions** -- generated code contains docstrings with
   Args sections, try/except blocks, logger calls, type hints
7. **Hierarchy** -- parent/child generation produces correct wiring code
8. **Async/sync mode** -- Pythonic defaults to sync, JSON defaults to async,
   `--async-mode` overrides both

### Test Approach

Each strategy test uses a standard sample JSON config (traffic light machine)
and asserts the generated output contains expected code patterns via `assertIn`
checks on the generated string output. This is consistent with the existing
`unittest.TestCase` style used throughout the `tests_cli` directory.

---

## Migration Path

| Version | Behavior |
|---------|----------|
| 0.4.3 (current) | `--style class\|function` only |
| 0.5.0 (this release) | `--template` added, `--style` works with deprecation warning |
| 0.6.0 (future) | `--style` removed, `--template` only |

The version bump to 0.5.0 is part of this change to signal the new feature set.

---

## Summary of Changes by File

| File | Change |
|------|--------|
| `cli/args.py` | Add `--template`/`-t`, deprecation logic for `--style`, `--async-mode` default to `None` |
| `cli/__main__.py` | Route through strategy registry, build `GenerationContext`, resolve async default |
| `cli/generator.py` | Refactor to thin orchestrator delegating to strategies |
| `cli/strategies/__init__.py` | Registry, `get_strategy()`, exports |
| `cli/strategies/base.py` | `BaseStrategy` ABC, `GenerationContext` dataclass |
| `cli/strategies/_shared.py` | Shared helpers (imports, logging, docstrings, error handling) |
| `cli/strategies/class_json.py` | Extracted from current generator (class style) |
| `cli/strategies/function_json.py` | Extracted from current generator (function style) |
| `cli/strategies/pythonic_class.py` | New: StateMachine generation |
| `cli/strategies/pythonic_builder.py` | New: MachineBuilder generation |
| `cli/strategies/pythonic_functional.py` | New: build_machine generation |
| `__init__.py` | Version bump to 0.5.0 |
| `tests/tests_cli/test_args.py` | New: template flag tests |
| `tests/tests_cli/test_strategy_registry.py` | New: registry tests |
| `tests/tests_cli/test_class_json_strategy.py` | New: class-json strategy tests |
| `tests/tests_cli/test_function_json_strategy.py` | New: function-json strategy tests |
| `tests/tests_cli/test_pythonic_class_strategy.py` | New: pythonic-class tests |
| `tests/tests_cli/test_pythonic_builder_strategy.py` | New: pythonic-builder tests |
| `tests/tests_cli/test_pythonic_functional_strategy.py` | New: pythonic-functional tests |
| `tests/tests_cli/test_hierarchy_pythonic.py` | New: hierarchy + Pythonic tests |
| `tests/tests_cli/test_production_quality.py` | New: production quality assertions |
