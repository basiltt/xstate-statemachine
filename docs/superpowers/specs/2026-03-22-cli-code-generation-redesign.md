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

## Non-Goals

- Blank scaffold generation (no JSON input) — not in scope
- Jinja2 or external template engine — stay dependency-free
- Removing existing `--style` flag — deprecate only, remove in future v0.6.0

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

- `--style class` maps to `--template class-json` and emits:
  `DeprecationWarning: --style is deprecated, use --template class-json instead. Will be removed in v0.6.0`
- `--style function` maps to `--template function-json` with the same warning.
- If both `--style` and `--template` are provided: error
  `"Cannot use both --style and --template. Use --template only."`
- The `--style` flag remains in the parser with `choices=["class", "function"]`.

### Async Mode Defaults

- JSON templates (`class-json`, `function-json`): default `--async-mode yes`
- Pythonic templates (`pythonic-*`): default `--async-mode no` (sync)
- Explicit `--async-mode yes/no` overrides the template default in all cases.

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
    _shared.py         # Shared helpers: imports, logging setup, docstring builders
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
from typing import Any, Dict, List, Set


@dataclasses.dataclass
class GenerationContext:
    """All inputs needed by any strategy to generate code."""

    actions: Set[str]
    guards: Set[str]
    services: Set[str]
    is_async: bool
    log: bool
    machine_name: str
    machine_names: List[str]
    file_count: int
    configs: List[Dict[str, Any]]
    json_filenames: List[str]
    hierarchy: bool
    sleep: bool
    sleep_time: int
    loader: bool


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
from .class_json import ClassJsonStrategy
from .function_json import FunctionJsonStrategy
from .pythonic_class import PythonicClassStrategy
from .pythonic_builder import PythonicBuilderStrategy
from .pythonic_functional import PythonicFunctionalStrategy

STRATEGY_REGISTRY: Dict[str, type] = {
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

### pythonic-class (StateMachine subclass)

Generates a `StateMachine` subclass with:
- Class-level `id` and `context` attributes
- `State` instances as class attributes
- Transition definitions via `state.to(target, event=..., ...)`
- `@action`, `@guard`, `@service` decorated methods with `self` parameter
- `.create()` classmethod call in the runner section

### pythonic-builder (MachineBuilder fluent API)

Generates:
- Module-level `@action`, `@guard`, `@service` decorated functions (no `self`)
- A `build()` function that creates `State` objects, defines transitions, and
  uses `MachineBuilder("id").context({...}).state("name", state).build(...)` chain
- Runner calls `build()` then creates an interpreter

### pythonic-functional (build_machine function)

Generates:
- Module-level `@action`, `@guard`, `@service` decorated functions (no `self`)
- A `build()` function that creates `State` objects, defines transitions, and
  calls `build_machine(id=..., states={...}, context={...}, actions=[...], ...)`
- Runner calls `build()` then creates an interpreter

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
   references to child machine IDs
2. **Child machines** -- each child gets its own class/build function within
   the same logic file, clearly separated with section comments
3. **Runner** -- creates parent via Pythonic API, loads child configs from JSON,
   creates interpreters for all, wires and starts them, simulates events, shuts
   down in reverse order (children first, then parent)
4. **Actor spawning** -- child machines are loaded from JSON configs at runtime
   (consistent with how `xstate_statemachine` actors work internally)

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
   `DeprecationWarning` with the correct message
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
checks on the generated string output.

---

## Migration Path

| Version | Behavior |
|---------|----------|
| Current (0.4.3) | `--style class\|function` only |
| This release (0.5.0) | `--template` added, `--style` works with deprecation warning |
| Future (0.6.0) | `--style` removed, `--template` only |

---

## Summary of Changes by File

| File | Change |
|------|--------|
| `cli/args.py` | Add `--template`/`-t`, deprecation logic for `--style`, async default resolution |
| `cli/__main__.py` | Route through strategy registry, build `GenerationContext` |
| `cli/generator.py` | Refactor to thin orchestrator delegating to strategies |
| `cli/strategies/__init__.py` | Registry, `get_strategy()`, exports |
| `cli/strategies/base.py` | `BaseStrategy` ABC, `GenerationContext` dataclass |
| `cli/strategies/_shared.py` | Shared helpers for imports, logging, docstrings |
| `cli/strategies/class_json.py` | Extracted from current generator (class style) |
| `cli/strategies/function_json.py` | Extracted from current generator (function style) |
| `cli/strategies/pythonic_class.py` | New: StateMachine generation |
| `cli/strategies/pythonic_builder.py` | New: MachineBuilder generation |
| `cli/strategies/pythonic_functional.py` | New: build_machine generation |
| `tests/tests_cli/test_args.py` | New: template flag tests |
| `tests/tests_cli/test_strategy_registry.py` | New: registry tests |
| `tests/tests_cli/test_class_json_strategy.py` | New: class-json strategy tests |
| `tests/tests_cli/test_function_json_strategy.py` | New: function-json strategy tests |
| `tests/tests_cli/test_pythonic_class_strategy.py` | New: pythonic-class tests |
| `tests/tests_cli/test_pythonic_builder_strategy.py` | New: pythonic-builder tests |
| `tests/tests_cli/test_pythonic_functional_strategy.py` | New: pythonic-functional tests |
| `tests/tests_cli/test_hierarchy_pythonic.py` | New: hierarchy + Pythonic tests |
| `tests/tests_cli/test_production_quality.py` | New: production quality assertions |
