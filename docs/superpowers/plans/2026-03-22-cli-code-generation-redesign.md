# CLI Code Generation Redesign Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the `xsm generate-template` CLI to generate Pythonic API code from JSON configs with production-quality output, using a strategy pattern architecture.

**Architecture:** Each template type (class-json, function-json, pythonic-class, pythonic-builder, pythonic-functional) is a strategy class implementing `BaseStrategy`. A `GenerationContext` dataclass replaces long argument lists. The existing `generator.py` becomes a thin orchestrator delegating to strategies. Backward compat: `--style` still works with deprecation warnings.

**Tech Stack:** Python 3.9+, `typing` module (no PEP 604 union syntax), `unittest.TestCase`, `pytest`, `black` (line-length 79), `hatchling` build system.

**Spec:** `docs/superpowers/specs/2026-03-22-cli-code-generation-redesign.md`

---

## Chunk 1: Foundation — BaseStrategy, GenerationContext, Registry, Args

### Task 1: Create `strategies/` package with `base.py`

**Files:**
- Create: `src/xstate_statemachine/cli/strategies/__init__.py`
- Create: `src/xstate_statemachine/cli/strategies/base.py`
- Test: `tests/tests_cli/test_strategy_registry.py`

- [ ] **Step 1: Create the strategies directory**

```bash
mkdir -p src/xstate_statemachine/cli/strategies
```

- [ ] **Step 2: Write the failing test for GenerationContext**

Create `tests/tests_cli/test_strategy_registry.py`:

```python
# tests/tests_cli/test_strategy_registry.py
import logging
import unittest
from typing import Any, Dict, List, Set

logger = logging.getLogger(__name__)


class TestGenerationContext(unittest.TestCase):
    """Tests for the GenerationContext dataclass."""

    def test_context_creation_with_all_fields(self) -> None:
        """Context can be created with all required fields."""
        from src.xstate_statemachine.cli.strategies.base import (
            GenerationContext,
        )

        ctx = GenerationContext(
            actions={"act1"},
            guards={"g1"},
            services={"svc1"},
            is_async=True,
            log=True,
            machine_name="test_machine",
            machine_id="testMachine",
            machine_names=["test_machine"],
            machine_ids=["testMachine"],
            file_count=2,
            configs=[{"id": "testMachine"}],
            json_filenames=["test.json"],
            hierarchy=False,
            sleep=True,
            sleep_time=2,
            loader=True,
            style="class",
        )
        self.assertEqual(ctx.machine_name, "test_machine")
        self.assertEqual(ctx.machine_id, "testMachine")
        self.assertTrue(ctx.is_async)
        self.assertEqual(ctx.style, "class")

    def test_context_style_defaults_to_none(self) -> None:
        """Style field defaults to None when not provided."""
        from src.xstate_statemachine.cli.strategies.base import (
            GenerationContext,
        )

        ctx = GenerationContext(
            actions=set(),
            guards=set(),
            services=set(),
            is_async=False,
            log=False,
            machine_name="m",
            machine_id="m",
            machine_names=["m"],
            machine_ids=["m"],
            file_count=1,
            configs=[{}],
            json_filenames=["m.json"],
            hierarchy=False,
            sleep=False,
            sleep_time=0,
            loader=False,
        )
        self.assertIsNone(ctx.style)


class TestBaseStrategy(unittest.TestCase):
    """Tests for the BaseStrategy abstract class."""

    def test_cannot_instantiate_base_strategy(self) -> None:
        """BaseStrategy is abstract and cannot be instantiated."""
        from src.xstate_statemachine.cli.strategies.base import (
            BaseStrategy,
        )

        with self.assertRaises(TypeError):
            BaseStrategy()  # type: ignore[abstract]

    def test_concrete_strategy_must_implement_methods(
        self,
    ) -> None:
        """A subclass missing methods cannot be instantiated."""
        from src.xstate_statemachine.cli.strategies.base import (
            BaseStrategy,
        )

        class Incomplete(BaseStrategy):
            pass

        with self.assertRaises(TypeError):
            Incomplete()  # type: ignore[abstract]

    def test_concrete_strategy_works(self) -> None:
        """A fully implemented subclass can be instantiated."""
        from src.xstate_statemachine.cli.strategies.base import (
            BaseStrategy,
            GenerationContext,
        )

        class DummyStrategy(BaseStrategy):
            @property
            def name(self) -> str:
                return "dummy"

            def generate_logic(
                self, ctx: GenerationContext
            ) -> str:
                return "logic"

            def generate_runner(
                self, ctx: GenerationContext
            ) -> str:
                return "runner"

        s = DummyStrategy()
        self.assertEqual(s.name, "dummy")
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/tests_cli/test_strategy_registry.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 4: Implement base.py**

Create `src/xstate_statemachine/cli/strategies/base.py`:

```python
# src/xstate_statemachine/cli/strategies/base.py
"""Base strategy class and shared data structures."""

import dataclasses
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set


@dataclasses.dataclass
class GenerationContext:
    """All inputs needed by any strategy to generate code."""

    actions: Set[str]
    guards: Set[str]
    services: Set[str]
    is_async: bool
    log: bool
    machine_name: str
    machine_id: str
    machine_names: List[str]
    machine_ids: List[str]
    file_count: int
    configs: List[Dict[str, Any]]
    json_filenames: List[str]
    hierarchy: bool
    sleep: bool
    sleep_time: int
    loader: bool
    style: Optional[str] = None


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

- [ ] **Step 5: Create strategies/__init__.py (empty for now)**

Create `src/xstate_statemachine/cli/strategies/__init__.py`:

```python
# src/xstate_statemachine/cli/strategies/__init__.py
"""Strategy-based code generation for the CLI."""
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/tests_cli/test_strategy_registry.py -v`
Expected: 5 tests PASS

- [ ] **Step 7: Commit**

```bash
git add src/xstate_statemachine/cli/strategies/ tests/tests_cli/test_strategy_registry.py
git commit -m "feat(cli): add BaseStrategy ABC and GenerationContext dataclass"
```

---

### Task 2: Create `_shared.py` with production-quality helpers

**Files:**
- Create: `src/xstate_statemachine/cli/strategies/_shared.py`
- Test: `tests/tests_cli/test_strategy_registry.py` (append)

- [ ] **Step 1: Write failing tests for shared helpers**

Append to `tests/tests_cli/test_strategy_registry.py`:

```python
class TestSharedHelpers(unittest.TestCase):
    """Tests for the _shared.py helper functions."""

    def test_pascal_case_name(self) -> None:
        """snake_case converts to PascalCase."""
        from src.xstate_statemachine.cli.strategies._shared import (
            pascal_case_name,
        )

        self.assertEqual(
            pascal_case_name("traffic_light"), "TrafficLight"
        )
        self.assertEqual(pascal_case_name("simple"), "Simple")
        self.assertEqual(
            pascal_case_name("my_cool_machine"), "MyCoolMachine"
        )

    def test_generate_module_header(self) -> None:
        """Module header is a docstring with title."""
        from src.xstate_statemachine.cli.strategies._shared import (
            generate_module_header,
        )

        header = generate_module_header(
            "Traffic Light", "traffic_light.json"
        )
        self.assertIn('"""', header)
        self.assertIn("Traffic Light", header)
        self.assertIn("generated by xsm CLI", header)

    def test_generate_section_header(self) -> None:
        """Section header contains title and separator."""
        from src.xstate_statemachine.cli.strategies._shared import (
            generate_section_header,
        )

        header = generate_section_header("Actions")
        self.assertIn("Actions", header)
        self.assertIn("---", header)

    def test_generate_logger_setup_enabled(self) -> None:
        """Logger setup includes getLogger when enabled."""
        from src.xstate_statemachine.cli.strategies._shared import (
            generate_logger_setup,
        )

        result = generate_logger_setup(True)
        self.assertIn("logging.getLogger(__name__)", result)

    def test_generate_logger_setup_disabled(self) -> None:
        """Logger setup returns empty when disabled."""
        from src.xstate_statemachine.cli.strategies._shared import (
            generate_logger_setup,
        )

        result = generate_logger_setup(False)
        self.assertEqual(result, "")

    def test_generate_action_docstring(self) -> None:
        """Action docstring includes Args section."""
        from src.xstate_statemachine.cli.strategies._shared import (
            generate_action_docstring,
        )

        doc = generate_action_docstring("myAction", "action")
        self.assertIn("myAction", doc)
        self.assertIn("Args:", doc)
        self.assertIn("interpreter:", doc)

    def test_generate_guard_docstring(self) -> None:
        """Guard docstring includes context and event args."""
        from src.xstate_statemachine.cli.strategies._shared import (
            generate_action_docstring,
        )

        doc = generate_action_docstring("isReady", "guard")
        self.assertIn("isReady", doc)
        self.assertIn("Args:", doc)
        self.assertIn("context:", doc)

    def test_generate_error_handling(self) -> None:
        """Error handling wraps body in try/except."""
        from src.xstate_statemachine.cli.strategies._shared import (
            generate_error_handling,
        )

        result = generate_error_handling(
            "myAction",
            "action",
            ["    # TODO: implement"],
            "    ",
        )
        self.assertIn("try:", result)
        self.assertIn("except Exception:", result)
        self.assertIn("logger.exception", result)
        self.assertIn("myAction", result)

    def test_generate_imports_pythonic(self) -> None:
        """Pythonic imports include State, action, guard, typing, logging."""
        from src.xstate_statemachine.cli.strategies._shared import (
            generate_imports,
        )

        result = generate_imports(
            is_async=False,
            services=set(),
            template_type="pythonic-class",
            log=True,
        )
        self.assertIn("from xstate_statemachine import", result)
        self.assertIn("State", result)
        self.assertIn("StateMachine", result)
        self.assertIn("import logging", result)
        self.assertIn("from typing import Any, Dict", result)

    def test_generate_imports_json(self) -> None:
        """JSON imports include Interpreter, Event, logging, etc."""
        from src.xstate_statemachine.cli.strategies._shared import (
            generate_imports,
        )

        result = generate_imports(
            is_async=True,
            services=set(),
            template_type="class-json",
            log=True,
        )
        self.assertIn("from xstate_statemachine import", result)
        self.assertIn("Interpreter", result)
        self.assertIn("Event", result)
        self.assertIn("import logging", result)
        self.assertNotIn("Awaitable", result)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/tests_cli/test_strategy_registry.py::TestSharedHelpers -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement _shared.py**

Create `src/xstate_statemachine/cli/strategies/_shared.py`:

```python
# src/xstate_statemachine/cli/strategies/_shared.py
"""Shared helpers used across all code generation strategies."""

from typing import List, Set

from ..utils import camel_to_snake


def pascal_case_name(snake_name: str) -> str:
    """Convert snake_case to PascalCase for class names."""
    return "".join(
        word.capitalize() for word in snake_name.split("_")
    )


def generate_module_header(
    title: str, json_filename: str
) -> str:
    """Generate the module docstring matching spec format."""
    return (
        f'"""{title} state machine '
        f'-- generated by xsm CLI."""\n'
    )


def generate_section_header(title: str) -> str:
    """Generate a section separator comment block."""
    return "\n".join(
        [
            "# --------------------------------------------------"
            "---------------------",
            f"# {title}",
            "# --------------------------------------------------"
            "---------------------",
            "",
        ]
    )


def generate_logger_setup(log: bool) -> str:
    """Generate logger variable line (import handled by generate_imports)."""
    if not log:
        return ""
    return "\n".join(
        [
            "logger = logging.getLogger(__name__)",
            "",
        ]
    )


def generate_action_docstring(
    original_name: str, component_type: str
) -> str:
    """Generate a rich docstring with Args section.

    Args:
        original_name: The original camelCase name from JSON.
        component_type: One of 'action', 'guard', 'service'.

    Returns:
        A multi-line docstring string (without outer quotes).
    """
    verbs = {
        "action": "Execute",
        "guard": "Evaluate",
        "service": "Run",
    }
    verb = verbs.get(component_type, "Execute")
    lines = [f'{verb} the ``{original_name}`` {component_type}.']
    lines.append("")
    lines.append("Args:")
    if component_type == "guard":
        lines.append(
            "    context: Current machine context dictionary."
        )
        lines.append("    event: The event being evaluated.")
    else:
        lines.append(
            "    interpreter: The running interpreter instance."
        )
        lines.append(
            "    context: Mutable machine context dictionary."
        )
        lines.append(
            f"    event: The event that triggered this "
            f"{component_type}."
        )
        if component_type == "action":
            lines.append(
                "    action_def: Metadata about the action "
                "being executed."
            )
    return "\n".join(lines)


def generate_error_handling(
    original_name: str,
    component_type: str,
    body_lines: List[str],
    indent: str,
) -> str:
    """Wrap body lines in try/except with logger.exception.

    Args:
        original_name: The original camelCase name from JSON.
        component_type: One of 'action', 'guard', 'service'.
        body_lines: The lines of code to wrap.
        indent: The indentation string (e.g. '    ').

    Returns:
        The wrapped code as a string.
    """
    lines = [f"{indent}try:"]
    for line in body_lines:
        lines.append(f"{indent}    {line.lstrip()}")
    lines.append(f"{indent}except Exception:")
    lines.append(
        f'{indent}    logger.exception('
        f'"{component_type.capitalize()} '
        f"'{original_name}' failed\")"
    )
    lines.append(f"{indent}    raise")
    return "\n".join(lines)


def generate_imports(
    is_async: bool,
    services: Set[str],
    template_type: str,
    log: bool = True,
) -> str:
    """Generate import statements for the template type.

    Args:
        is_async: Whether async mode is enabled.
        services: Set of service names (may affect imports).
        template_type: The template identifier string.
        log: Whether logging is enabled (adds import logging).

    Returns:
        Import block as a string.
    """
    lines = []

    if template_type.startswith("pythonic"):
        if is_async:
            lines.append("import asyncio")
        if log:
            lines.append("import logging")
        lines.append(
            "from typing import Any, Dict, Optional, Union"
        )
        lines.append("")
        interpreter = (
            "Interpreter" if is_async else "SyncInterpreter"
        )
        xsm_imports = [interpreter]
        if "class" in template_type:
            xsm_imports.extend(
                ["State", "StateMachine", "action", "guard",
                 "service", "transition"]
            )
        elif "builder" in template_type:
            xsm_imports.extend(
                ["MachineBuilder", "action", "guard", "service"]
            )
        elif "functional" in template_type:
            xsm_imports.extend(
                ["State", "action", "build_machine", "guard",
                 "service"]
            )
        xsm_imports.sort()
        imports_str = ",\n    ".join(xsm_imports)
        lines.append(
            f"from xstate_statemachine import (\n"
            f"    {imports_str},\n)"
        )
    else:
        # JSON-style imports
        if is_async:
            lines.append("import asyncio")
        if log:
            lines.append("import logging")
        if services and not is_async:
            lines.append("import time")
        lines.append("from typing import Any, Dict, Union")
        lines.append("")
        lines.append(
            "from xstate_statemachine import "
            "Interpreter, SyncInterpreter, Event, "
            "ActionDefinition"
        )

    lines.append("")
    return "\n".join(lines)


def snake_case_name(camel_name: str) -> str:
    """Convert camelCase to snake_case."""
    return camel_to_snake(camel_name)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/tests_cli/test_strategy_registry.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/xstate_statemachine/cli/strategies/_shared.py tests/tests_cli/test_strategy_registry.py
git commit -m "feat(cli): add shared helpers for production-quality code generation"
```

---

### Task 3: Add `--template` flag and deprecation logic to `args.py`

**Files:**
- Modify: `src/xstate_statemachine/cli/args.py`
- Create: `tests/tests_cli/test_args.py`

- [ ] **Step 1: Write failing tests for --template flag and deprecation**

Create `tests/tests_cli/test_args.py`:

```python
# tests/tests_cli/test_args.py
"""Tests for CLI argument parsing — --template flag and deprecation."""

import logging
import unittest
import warnings
from unittest.mock import patch

logger = logging.getLogger(__name__)


class TestTemplateFlag(unittest.TestCase):
    """Tests for the new --template / -t flag."""

    def test_template_flag_accepted(self) -> None:
        """--template with valid value is parsed correctly."""
        from src.xstate_statemachine.cli.args import get_parser

        parser = get_parser()
        args = parser.parse_args(
            ["generate-template", "f.json", "--template",
             "pythonic-class"]
        )
        self.assertEqual(args.template, "pythonic-class")

    def test_template_short_flag(self) -> None:
        """-t short flag works for --template."""
        from src.xstate_statemachine.cli.args import get_parser

        parser = get_parser()
        args = parser.parse_args(
            ["generate-template", "f.json", "-t",
             "pythonic-builder"]
        )
        self.assertEqual(args.template, "pythonic-builder")

    def test_template_default_is_none(self) -> None:
        """--template defaults to None when not provided."""
        from src.xstate_statemachine.cli.args import get_parser

        parser = get_parser()
        args = parser.parse_args(
            ["generate-template", "f.json"]
        )
        self.assertIsNone(args.template)

    def test_template_all_valid_choices(self) -> None:
        """All 5 template choices are accepted."""
        from src.xstate_statemachine.cli.args import get_parser

        valid = [
            "class-json", "function-json",
            "pythonic-class", "pythonic-builder",
            "pythonic-functional",
        ]
        parser = get_parser()
        for t in valid:
            args = parser.parse_args(
                ["generate-template", "f.json", "-t", t]
            )
            self.assertEqual(args.template, t)

    def test_template_invalid_choice_errors(self) -> None:
        """Invalid --template value causes a parser error."""
        from src.xstate_statemachine.cli.args import get_parser

        parser = get_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(
                ["generate-template", "f.json", "-t", "invalid"]
            )

    def test_async_mode_default_is_none(self) -> None:
        """--async-mode defaults to None (resolved later)."""
        from src.xstate_statemachine.cli.args import get_parser

        parser = get_parser()
        args = parser.parse_args(
            ["generate-template", "f.json"]
        )
        self.assertIsNone(args.async_mode)


class TestStyleDeprecation(unittest.TestCase):
    """Tests for --style backward compat with deprecation."""

    def test_resolve_template_from_style_class(self) -> None:
        """--style class resolves to class-json with warning."""
        from src.xstate_statemachine.cli.args import (
            resolve_template,
        )

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = resolve_template(
                style="class", template=None
            )
            self.assertEqual(result, "class-json")
            self.assertEqual(len(w), 1)
            self.assertIn(
                "deprecated", str(w[0].message).lower()
            )
            self.assertTrue(
                issubclass(w[0].category, DeprecationWarning)
            )

    def test_resolve_template_from_style_function(self) -> None:
        """--style function resolves to function-json."""
        from src.xstate_statemachine.cli.args import (
            resolve_template,
        )

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = resolve_template(
                style="function", template=None
            )
            self.assertEqual(result, "function-json")
            self.assertEqual(len(w), 1)

    def test_resolve_template_explicit_template_wins(
        self,
    ) -> None:
        """--template takes precedence when --style not set."""
        from src.xstate_statemachine.cli.args import (
            resolve_template,
        )

        result = resolve_template(
            style=None, template="pythonic-class"
        )
        self.assertEqual(result, "pythonic-class")

    def test_resolve_template_both_raises_error(self) -> None:
        """Using both --style and --template raises ValueError."""
        from src.xstate_statemachine.cli.args import (
            resolve_template,
        )

        with self.assertRaises(ValueError) as cm:
            resolve_template(
                style="class", template="pythonic-class"
            )
        self.assertIn("Cannot use both", str(cm.exception))

    def test_resolve_template_neither_defaults(self) -> None:
        """Neither --style nor --template defaults to class-json."""
        from src.xstate_statemachine.cli.args import (
            resolve_template,
        )

        result = resolve_template(style=None, template=None)
        self.assertEqual(result, "class-json")


class TestAsyncModeResolution(unittest.TestCase):
    """Tests for template-aware async mode defaults."""

    def test_resolve_async_explicit_yes(self) -> None:
        """Explicit --async-mode yes overrides template."""
        from src.xstate_statemachine.cli.args import (
            resolve_async_mode,
        )

        result = resolve_async_mode("yes", "pythonic-class")
        self.assertTrue(result)

    def test_resolve_async_explicit_no(self) -> None:
        """Explicit --async-mode no overrides template."""
        from src.xstate_statemachine.cli.args import (
            resolve_async_mode,
        )

        result = resolve_async_mode("no", "class-json")
        self.assertFalse(result)

    def test_resolve_async_json_template_defaults_true(
        self,
    ) -> None:
        """JSON templates default to async when not specified."""
        from src.xstate_statemachine.cli.args import (
            resolve_async_mode,
        )

        result = resolve_async_mode(None, "class-json")
        self.assertTrue(result)
        result2 = resolve_async_mode(None, "function-json")
        self.assertTrue(result2)

    def test_resolve_async_pythonic_defaults_false(
        self,
    ) -> None:
        """Pythonic templates default to sync."""
        from src.xstate_statemachine.cli.args import (
            resolve_async_mode,
        )

        for t in [
            "pythonic-class",
            "pythonic-builder",
            "pythonic-functional",
        ]:
            result = resolve_async_mode(None, t)
            self.assertFalse(result)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/tests_cli/test_args.py -v`
Expected: FAIL (missing `template` attribute, missing `resolve_template`, etc.)

- [ ] **Step 3: Modify args.py — add --template flag, resolve functions, change --async-mode default**

Modify `src/xstate_statemachine/cli/args.py`:

1. Add `--template` / `-t` to `_add_generation_option_args()`:

```python
parser.add_argument(
    "-t",
    "--template",
    choices=[
        "class-json",
        "function-json",
        "pythonic-class",
        "pythonic-builder",
        "pythonic-functional",
    ],
    default=None,
    help=(
        "Code generation template. Default: class-json. "
        "Replaces --style (deprecated)."
    ),
)
```

2. Change `--style` default from `"class"` to `None` and make it optional:

```python
parser.add_argument(
    "-s",
    "--style",
    choices=["class", "function"],
    default=None,
    help=(
        "DEPRECATED: Use --template instead. "
        "Code style for logic: 'class' or 'function'."
    ),
)
```

3. Change `--async-mode` default from `"yes"` to `None`:

```python
parser.add_argument(
    "-am",
    "--async-mode",
    default=None,
    help=(
        "Generate asynchronous code: 'yes' or 'no'. "
        "Default: 'yes' for JSON templates, 'no' for "
        "Pythonic templates."
    ),
)
```

4. Add two new public functions at the end of `args.py`:

```python
def resolve_template(
    style: Optional[str],
    template: Optional[str],
) -> str:
    """Resolve the template from --style and --template flags.

    Args:
        style: Value of deprecated --style flag (or None).
        template: Value of --template flag (or None).

    Returns:
        The resolved template string.

    Raises:
        ValueError: If both --style and --template are set.
    """
    if style is not None and template is not None:
        raise ValueError(
            "Cannot use both --style and --template. "
            "Use --template only."
        )
    if template is not None:
        return template
    if style is not None:
        import warnings

        mapping = {
            "class": "class-json",
            "function": "function-json",
        }
        resolved = mapping[style]
        warnings.warn(
            f"--style is deprecated, use --template "
            f"{resolved} instead. "
            f"Will be removed in v0.6.0",
            DeprecationWarning,
            stacklevel=2,
        )
        return resolved
    return "class-json"


def resolve_async_mode(
    async_mode: Optional[str],
    template: str,
) -> bool:
    """Resolve async mode based on explicit flag and template.

    Args:
        async_mode: The raw --async-mode value (or None).
        template: The resolved template string.

    Returns:
        True for async mode, False for sync mode.
    """
    if async_mode is not None:
        return normalize_bool(async_mode)
    # Template-aware defaults
    if template.startswith("pythonic"):
        return False
    return True
```

5. Add `from typing import Optional` and ensure `normalize_bool` import at the top:

```python
from typing import Optional
from .utils import normalize_bool
```

Note: `normalize_bool` may already be imported. Verify and add only if missing.

- [ ] **Step 4: Update __main__.py to handle None defaults**

The `--async-mode` and `--style` defaults are now `None` instead of `"yes"` and `"class"`. Update `__main__.py` to handle this:

1. In `_parse_boolean_flags()`, skip `async_mode` normalization when it's `None`:

```python
if args.async_mode is not None:
    args.async_mode = normalize_bool(args.async_mode)
```

2. In `run_generation_workflow()`, when `args.style` is used for the generation call, default it:

```python
style = args.style if args.style is not None else "class"
```

This ensures existing code paths work until Task 11 wires the full strategy dispatch.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/tests_cli/test_args.py -v`
Expected: All tests PASS

- [ ] **Step 6: Run existing tests to verify backward compat**

Run: `uv run pytest tests/tests_cli/ -v`
Expected: All existing tests still PASS (the `--style` default change to `None` is handled by the `__main__.py` update in Step 4)

- [ ] **Step 7: Commit**

```bash
git add src/xstate_statemachine/cli/args.py src/xstate_statemachine/cli/__main__.py tests/tests_cli/test_args.py
git commit -m "feat(cli): add --template flag with --style deprecation and async-mode resolution"
```

---

### Task 4: Create strategy registry with `get_strategy()`

**Files:**
- Modify: `src/xstate_statemachine/cli/strategies/__init__.py`
- Test: `tests/tests_cli/test_strategy_registry.py` (append)

- [ ] **Step 1: Write failing tests for the registry**

Append to `tests/tests_cli/test_strategy_registry.py`:

```python
class TestStrategyRegistry(unittest.TestCase):
    """Tests for the strategy registry and get_strategy()."""

    def test_get_strategy_class_json(self) -> None:
        """class-json returns a ClassJsonStrategy."""
        from src.xstate_statemachine.cli.strategies import (
            get_strategy,
        )

        s = get_strategy("class-json")
        self.assertEqual(s.name, "class-json")

    def test_get_strategy_function_json(self) -> None:
        """function-json returns a FunctionJsonStrategy."""
        from src.xstate_statemachine.cli.strategies import (
            get_strategy,
        )

        s = get_strategy("function-json")
        self.assertEqual(s.name, "function-json")

    def test_get_strategy_pythonic_class(self) -> None:
        """pythonic-class returns a PythonicClassStrategy."""
        from src.xstate_statemachine.cli.strategies import (
            get_strategy,
        )

        s = get_strategy("pythonic-class")
        self.assertEqual(s.name, "pythonic-class")

    def test_get_strategy_pythonic_builder(self) -> None:
        """pythonic-builder returns correct strategy."""
        from src.xstate_statemachine.cli.strategies import (
            get_strategy,
        )

        s = get_strategy("pythonic-builder")
        self.assertEqual(s.name, "pythonic-builder")

    def test_get_strategy_pythonic_functional(self) -> None:
        """pythonic-functional returns correct strategy."""
        from src.xstate_statemachine.cli.strategies import (
            get_strategy,
        )

        s = get_strategy("pythonic-functional")
        self.assertEqual(s.name, "pythonic-functional")

    def test_get_strategy_unknown_raises(self) -> None:
        """Unknown template raises InvalidConfigError."""
        from src.xstate_statemachine.cli.strategies import (
            get_strategy,
        )
        from src.xstate_statemachine.exceptions import (
            InvalidConfigError,
        )

        with self.assertRaises(InvalidConfigError):
            get_strategy("nonexistent")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/tests_cli/test_strategy_registry.py::TestStrategyRegistry -v`
Expected: FAIL with `ImportError`

**Note:** These tests will remain failing until all 5 strategy classes are implemented (Tasks 5-9). Mark these tests as expected to fail or skip them until the strategies exist. We proceed with creating the strategy stubs.

- [ ] **Step 3: Create stub strategy files**

Create minimal stub files for all 5 strategies so the registry can import them.
Each stub implements `BaseStrategy` with placeholder `generate_logic` and `generate_runner` that return `""`.

Create `src/xstate_statemachine/cli/strategies/class_json.py`:

```python
# src/xstate_statemachine/cli/strategies/class_json.py
"""Strategy for class-based JSON code generation."""

from .base import BaseStrategy, GenerationContext


class ClassJsonStrategy(BaseStrategy):
    """Generates class-based logic with JSON config loading."""

    @property
    def name(self) -> str:
        return "class-json"

    def generate_logic(self, ctx: GenerationContext) -> str:
        return ""  # TODO: implement in Task 5

    def generate_runner(self, ctx: GenerationContext) -> str:
        return ""  # TODO: implement in Task 5
```

Create similarly for `function_json.py`, `pythonic_class.py`, `pythonic_builder.py`, `pythonic_functional.py` — each with the correct `name` property value.

- [ ] **Step 4: Wire up the registry in strategies/__init__.py**

Update `src/xstate_statemachine/cli/strategies/__init__.py`:

```python
# src/xstate_statemachine/cli/strategies/__init__.py
"""Strategy-based code generation for the CLI."""

from typing import Dict, Type

from ...exceptions import InvalidConfigError
from .base import BaseStrategy, GenerationContext
from .class_json import ClassJsonStrategy
from .function_json import FunctionJsonStrategy
from .pythonic_builder import PythonicBuilderStrategy
from .pythonic_class import PythonicClassStrategy
from .pythonic_functional import PythonicFunctionalStrategy

STRATEGY_REGISTRY: Dict[str, Type[BaseStrategy]] = {
    "class-json": ClassJsonStrategy,
    "function-json": FunctionJsonStrategy,
    "pythonic-class": PythonicClassStrategy,
    "pythonic-builder": PythonicBuilderStrategy,
    "pythonic-functional": PythonicFunctionalStrategy,
}


def get_strategy(template: str) -> BaseStrategy:
    """Look up and instantiate the strategy for a template.

    Args:
        template: Template name (e.g. 'pythonic-class').

    Returns:
        An instantiated strategy.

    Raises:
        InvalidConfigError: If template is unknown.
    """
    cls = STRATEGY_REGISTRY.get(template)
    if cls is None:
        raise InvalidConfigError(
            f"Unknown template: {template}"
        )
    return cls()


__all__ = [
    "BaseStrategy",
    "GenerationContext",
    "STRATEGY_REGISTRY",
    "get_strategy",
]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/tests_cli/test_strategy_registry.py -v`
Expected: All tests PASS (registry tests + base tests + shared helpers)

- [ ] **Step 6: Commit**

```bash
git add src/xstate_statemachine/cli/strategies/ tests/tests_cli/test_strategy_registry.py
git commit -m "feat(cli): add strategy registry with 5 stub strategies and get_strategy()"
```

---

## Chunk 2: JSON Strategy Extraction + Production Quality Upgrades

### Task 5: Implement `ClassJsonStrategy` (extract from generator.py)

**Files:**
- Modify: `src/xstate_statemachine/cli/strategies/class_json.py`
- Create: `tests/tests_cli/test_class_json_strategy.py`

- [ ] **Step 1: Write failing tests for ClassJsonStrategy**

Create `tests/tests_cli/test_class_json_strategy.py`. Use the same test fixtures and assertion patterns as the existing `test_generator.py`, but test through the strategy interface:

```python
# tests/tests_cli/test_class_json_strategy.py
"""Tests for the ClassJsonStrategy."""

import logging
import unittest
from typing import Any, Dict, List, Set

from src.xstate_statemachine.cli.strategies import (
    get_strategy,
)
from src.xstate_statemachine.cli.strategies.base import (
    GenerationContext,
)

from .fixtures import SAMPLE_CONFIG_SIMPLE

logger = logging.getLogger(__name__)

# Richer config for class-json strategy testing
CLASS_JSON_TEST_CONFIG = {
    "id": "trafficLight",
    "initial": "green",
    "context": {"count": 0},
    "states": {
        "green": {
            "entry": "logEnter",
            "on": {
                "TIMER": {
                    "target": "yellow",
                    "actions": "increment",
                }
            },
        },
        "yellow": {
            "on": {
                "TIMER": {
                    "target": "red",
                    "cond": "isReady",
                }
            },
        },
        "red": {
            "on": {"TIMER": "green"},
            "invoke": {
                "src": "fetchData",
                "onDone": "green",
            },
        },
    },
}


class TestClassJsonStrategy(unittest.TestCase):
    """Tests for class-json code generation via strategy."""

    def _make_ctx(self, **overrides: Any) -> GenerationContext:
        """Create a GenerationContext with sensible defaults."""
        defaults = dict(
            actions={"logEnter", "increment"},
            guards={"isReady"},
            services={"fetchData"},
            is_async=True,
            log=True,
            machine_name="traffic_light",
            machine_id="trafficLight",
            machine_names=["traffic_light"],
            machine_ids=["trafficLight"],
            file_count=2,
            configs=[CLASS_JSON_TEST_CONFIG],
            json_filenames=["traffic_light.json"],
            hierarchy=False,
            sleep=True,
            sleep_time=2,
            loader=True,
            style="class",
        )
        defaults.update(overrides)
        return GenerationContext(**defaults)

    def test_logic_contains_class_definition(self) -> None:
        """Generated logic contains the class header."""
        s = get_strategy("class-json")
        ctx = self._make_ctx()
        code = s.generate_logic(ctx)
        self.assertIn("class TrafficLightLogic:", code)

    def test_logic_contains_action_stubs(self) -> None:
        """Generated logic has action method stubs."""
        s = get_strategy("class-json")
        ctx = self._make_ctx()
        code = s.generate_logic(ctx)
        self.assertIn("def log_enter(", code)
        self.assertIn("def increment(", code)

    def test_logic_contains_guard_stubs(self) -> None:
        """Generated logic has guard method stubs."""
        s = get_strategy("class-json")
        ctx = self._make_ctx()
        code = s.generate_logic(ctx)
        self.assertIn("def is_ready(", code)
        self.assertIn("-> bool:", code)

    def test_logic_contains_rich_docstrings(self) -> None:
        """Generated logic has Args section in docstrings."""
        s = get_strategy("class-json")
        ctx = self._make_ctx()
        code = s.generate_logic(ctx)
        self.assertIn("Args:", code)
        self.assertIn("interpreter:", code)

    def test_logic_contains_error_handling(self) -> None:
        """Generated logic wraps actions in try/except."""
        s = get_strategy("class-json")
        ctx = self._make_ctx()
        code = s.generate_logic(ctx)
        self.assertIn("try:", code)
        self.assertIn("except Exception:", code)
        self.assertIn("logger.exception", code)

    def test_logic_no_noqa_comments(self) -> None:
        """Generated logic does not have noqa comments."""
        s = get_strategy("class-json")
        ctx = self._make_ctx()
        code = s.generate_logic(ctx)
        self.assertNotIn("# noqa", code)

    def test_logic_async_return_type_is_none(self) -> None:
        """Async actions return None, not Awaitable[None]."""
        s = get_strategy("class-json")
        ctx = self._make_ctx(is_async=True)
        code = s.generate_logic(ctx)
        self.assertIn("async def log_enter(", code)
        self.assertNotIn("Awaitable[None]", code)
        # Should have -> None:
        self.assertIn("-> None:", code)

    def test_runner_contains_interpreter(self) -> None:
        """Generated runner creates an interpreter."""
        s = get_strategy("class-json")
        ctx = self._make_ctx()
        code = s.generate_runner(ctx)
        self.assertIn("Interpreter(machine)", code)
        self.assertIn("interpreter.start()", code)

    def test_runner_sync_mode(self) -> None:
        """Sync runner uses SyncInterpreter."""
        s = get_strategy("class-json")
        ctx = self._make_ctx(is_async=False)
        code = s.generate_runner(ctx)
        self.assertIn("SyncInterpreter(machine)", code)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/tests_cli/test_class_json_strategy.py -v`
Expected: FAIL (strategy returns empty strings)

- [ ] **Step 3: Implement ClassJsonStrategy**

Fill in `src/xstate_statemachine/cli/strategies/class_json.py` by extracting the class-style logic from `generator.py`. The strategy's `generate_logic()` should call the existing `_generate_logic_header`, `_generate_logic_component` helpers (or upgraded versions) with `style="class"`. Similarly for `generate_runner()`.

**Key changes from the existing generator for production quality:**
- Remove `# noqa` comments from generated signatures
- Change `Awaitable[None]` to `None` for async actions
- Add rich docstrings with `Args:` sections (use `_shared.generate_action_docstring`)
- Wrap action/service bodies in try/except (use `_shared.generate_error_handling`)
- Keep guard bodies without try/except (guards should not swallow errors silently)

The strategy should import and reuse helpers from `_shared.py` and the existing `generator.py` internals where possible.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/tests_cli/test_class_json_strategy.py -v`
Expected: All tests PASS

- [ ] **Step 5: Run existing generator tests**

Run: `uv run pytest tests/tests_cli/test_generator.py -v`
Expected: All existing tests still PASS (we haven't changed generator.py's public API)

- [ ] **Step 6: Commit**

```bash
git add src/xstate_statemachine/cli/strategies/class_json.py tests/tests_cli/test_class_json_strategy.py
git commit -m "feat(cli): implement ClassJsonStrategy with production-quality output"
```

---

### Task 6: Implement `FunctionJsonStrategy`

**Files:**
- Modify: `src/xstate_statemachine/cli/strategies/function_json.py`
- Create: `tests/tests_cli/test_function_json_strategy.py`

Follow the same pattern as Task 5 but for function-style output:
- No class wrapper, no `self` parameter
- Module-level functions with `@action`, etc. (only in the JSON style, these are plain functions without decorators)
- Same production-quality upgrades (rich docstrings, error handling, no noqa)

- [ ] **Step 1: Write failing tests** (same pattern as Task 5 but checking function-style output)
- [ ] **Step 2: Run tests to verify they fail**
- [ ] **Step 3: Implement FunctionJsonStrategy**
- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/tests_cli/test_function_json_strategy.py -v`

- [ ] **Step 5: Run all existing tests**

Run: `uv run pytest tests/tests_cli/ -v`

- [ ] **Step 6: Commit**

```bash
git add src/xstate_statemachine/cli/strategies/function_json.py tests/tests_cli/test_function_json_strategy.py
git commit -m "feat(cli): implement FunctionJsonStrategy with production-quality output"
```

---

### Task 7: Refactor `generator.py` to delegate to strategies

**Files:**
- Modify: `src/xstate_statemachine/cli/generator.py`

- [ ] **Step 1: Refactor generate_logic_code() to delegate**

Modify `generate_logic_code()` so it internally creates a `GenerationContext`, looks up the strategy based on `style`, and calls `strategy.generate_logic(ctx)`. The function signature stays identical for backward compatibility.

```python
def generate_logic_code(
    actions, guards, services, style, log, is_async,
    machine_name, file_count,
) -> str:
    """...(keep existing docstring)..."""
    template = "class-json" if style == "class" else "function-json"
    strategy = get_strategy(template)
    ctx = GenerationContext(
        actions=actions,
        guards=guards,
        services=services,
        is_async=is_async,
        log=log,
        machine_name=machine_name,
        machine_id=machine_name,
        machine_names=[machine_name],
        machine_ids=[machine_name],
        file_count=file_count,
        configs=[{}],
        json_filenames=[""],
        hierarchy=False,
        sleep=False,
        sleep_time=0,
        loader=False,
        style=style,
    )
    return strategy.generate_logic(ctx)
```

Similarly refactor `generate_runner_code()`.

- [ ] **Step 2: Run ALL existing generator tests**

Run: `uv run pytest tests/tests_cli/test_generator.py -v`
Expected: All existing tests PASS (output is identical since strategies produce the same code)

**Note:** If any existing tests fail due to minor formatting differences in the upgraded output (e.g., missing `# noqa`), those tests need to be updated to match the new production-quality output. This is expected — the spec explicitly removes `# noqa` comments and changes `Awaitable[None]` to `None`.

- [ ] **Step 3: Run ALL CLI tests**

Run: `uv run pytest tests/tests_cli/ -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add src/xstate_statemachine/cli/generator.py
git commit -m "refactor(cli): delegate generator.py to strategy pattern"
```

---

## Chunk 3: Pythonic Strategy Implementations

### Task 8: Implement `PythonicClassStrategy`

**Files:**
- Modify: `src/xstate_statemachine/cli/strategies/pythonic_class.py`
- Create: `tests/tests_cli/test_pythonic_class_strategy.py`

- [ ] **Step 1: Write failing tests**

Create `tests/tests_cli/test_pythonic_class_strategy.py`:

```python
# tests/tests_cli/test_pythonic_class_strategy.py
"""Tests for PythonicClassStrategy."""

import logging
import unittest
from typing import Any

from src.xstate_statemachine.cli.strategies import (
    get_strategy,
)
from src.xstate_statemachine.cli.strategies.base import (
    GenerationContext,
)

from .fixtures import SAMPLE_CONFIG_SIMPLE

logger = logging.getLogger(__name__)

# A richer config for Pythonic generation testing
TRAFFIC_LIGHT_CONFIG = {
    "id": "trafficLight",
    "initial": "green",
    "context": {"count": 0},
    "states": {
        "green": {
            "entry": "logEnter",
            "on": {
                "TIMER": {
                    "target": "yellow",
                    "actions": "increment",
                }
            },
        },
        "yellow": {
            "on": {
                "TIMER": {
                    "target": "red",
                    "cond": "isReady",
                }
            },
        },
        "red": {
            "on": {"TIMER": "green"},
            "invoke": {
                "src": "fetchData",
                "onDone": "green",
            },
        },
    },
}


class TestPythonicClassStrategy(unittest.TestCase):
    """Tests for pythonic-class code generation."""

    def _make_ctx(self, **overrides: Any) -> GenerationContext:
        defaults = dict(
            actions={"logEnter", "increment"},
            guards={"isReady"},
            services={"fetchData"},
            is_async=False,
            log=True,
            machine_name="traffic_light",
            machine_id="trafficLight",
            machine_names=["traffic_light"],
            machine_ids=["trafficLight"],
            file_count=2,
            configs=[TRAFFIC_LIGHT_CONFIG],
            json_filenames=["traffic_light.json"],
            hierarchy=False,
            sleep=True,
            sleep_time=2,
            loader=False,
        )
        defaults.update(overrides)
        return GenerationContext(**defaults)

    def test_logic_contains_statemachine_subclass(
        self,
    ) -> None:
        """Generated logic has a StateMachine subclass."""
        s = get_strategy("pythonic-class")
        code = s.generate_logic(self._make_ctx())
        self.assertIn("class TrafficLightMachine(StateMachine):", code)

    def test_logic_contains_machine_id(self) -> None:
        """Generated logic sets machine_id."""
        s = get_strategy("pythonic-class")
        code = s.generate_logic(self._make_ctx())
        self.assertIn('machine_id = "trafficLight"', code)

    def test_logic_contains_initial_context(self) -> None:
        """Generated logic sets initial_context."""
        s = get_strategy("pythonic-class")
        code = s.generate_logic(self._make_ctx())
        self.assertIn("initial_context =", code)

    def test_logic_contains_state_objects(self) -> None:
        """Generated logic creates State instances."""
        s = get_strategy("pythonic-class")
        code = s.generate_logic(self._make_ctx())
        self.assertIn("green = State(", code)
        self.assertIn("yellow = State()", code)
        self.assertIn("red = State(", code)
        self.assertIn("initial=True", code)

    def test_logic_contains_transitions(self) -> None:
        """Generated logic has .to() transition calls."""
        s = get_strategy("pythonic-class")
        code = s.generate_logic(self._make_ctx())
        self.assertIn("green.to(yellow", code)
        self.assertIn('event="TIMER"', code)

    def test_logic_contains_action_decorator(self) -> None:
        """Generated logic uses @action decorator."""
        s = get_strategy("pythonic-class")
        code = s.generate_logic(self._make_ctx())
        self.assertIn("@action", code)
        self.assertIn("def log_enter(", code)
        self.assertIn("self,", code)

    def test_logic_contains_guard_decorator(self) -> None:
        """Generated logic uses @guard decorator."""
        s = get_strategy("pythonic-class")
        code = s.generate_logic(self._make_ctx())
        self.assertIn("@guard", code)
        self.assertIn("def is_ready(", code)

    def test_logic_contains_service_decorator(self) -> None:
        """Generated logic uses @service decorator."""
        s = get_strategy("pythonic-class")
        code = s.generate_logic(self._make_ctx())
        self.assertIn("@service", code)
        self.assertIn("def fetch_data(", code)

    def test_logic_contains_rich_docstrings(self) -> None:
        """Generated logic has Args section."""
        s = get_strategy("pythonic-class")
        code = s.generate_logic(self._make_ctx())
        self.assertIn("Args:", code)

    def test_logic_contains_error_handling(self) -> None:
        """Generated logic has try/except."""
        s = get_strategy("pythonic-class")
        code = s.generate_logic(self._make_ctx())
        self.assertIn("try:", code)
        self.assertIn("except Exception:", code)

    def test_logic_imports_statemachine(self) -> None:
        """Generated logic imports StateMachine."""
        s = get_strategy("pythonic-class")
        code = s.generate_logic(self._make_ctx())
        self.assertIn("from xstate_statemachine import", code)
        self.assertIn("StateMachine", code)
        self.assertIn("State", code)

    def test_runner_uses_create_machine(self) -> None:
        """Runner calls .create_machine()."""
        s = get_strategy("pythonic-class")
        code = s.generate_runner(self._make_ctx())
        self.assertIn(
            "TrafficLightMachine.create_machine()", code
        )

    def test_runner_uses_sync_interpreter(self) -> None:
        """Sync runner uses SyncInterpreter."""
        s = get_strategy("pythonic-class")
        code = s.generate_runner(self._make_ctx())
        self.assertIn("SyncInterpreter(machine)", code)

    def test_runner_async_mode(self) -> None:
        """Async runner uses Interpreter and asyncio."""
        s = get_strategy("pythonic-class")
        ctx = self._make_ctx(is_async=True)
        code = s.generate_runner(ctx)
        self.assertIn("Interpreter(machine)", code)
        self.assertIn("asyncio.run(main())", code)
        self.assertIn("await ", code)

    def test_runner_has_main_guard(self) -> None:
        """Runner has if __name__ == '__main__' block."""
        s = get_strategy("pythonic-class")
        code = s.generate_runner(self._make_ctx())
        self.assertIn('if __name__ == "__main__":', code)

    def test_runner_sends_events(self) -> None:
        """Runner simulates events from the config."""
        s = get_strategy("pythonic-class")
        code = s.generate_runner(self._make_ctx())
        self.assertIn('send("TIMER")', code)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/tests_cli/test_pythonic_class_strategy.py -v`
Expected: FAIL (strategy returns empty strings)

- [ ] **Step 3: Implement PythonicClassStrategy**

Fill in `src/xstate_statemachine/cli/strategies/pythonic_class.py` following the spec's complete example output. The strategy needs to:

1. **`generate_logic()`**: Convert JSON config to a `StateMachine` subclass:
   - Parse `config["states"]` to create `State()` instances
   - Parse `config["on"]` events to create `.to()` transitions
   - Parse `config["initial"]` to mark the initial state
   - Parse `config["context"]` for `initial_context`
   - Generate `@action`/`@guard`/`@service` decorated methods
   - Use `_shared` helpers for docstrings, error handling, imports

2. **`generate_runner()`**: Generate runner with `.create_machine()` call

**Key conversion functions to implement within the strategy:**
- `_json_states_to_pythonic(config)` — walks states dict, returns State constructor args
- `_json_transitions_to_pythonic(config)` — extracts `on` events into `.to()` calls
- `_generate_decorated_methods(actions, guards, services)` — generates method stubs

Use `_shared.py` helpers: `pascal_case_name`, `snake_case_name`, `generate_action_docstring`, `generate_error_handling`, `generate_imports`, `generate_logger_setup`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/tests_cli/test_pythonic_class_strategy.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/xstate_statemachine/cli/strategies/pythonic_class.py tests/tests_cli/test_pythonic_class_strategy.py
git commit -m "feat(cli): implement PythonicClassStrategy for StateMachine code generation"
```

---

### Task 9: Implement `PythonicBuilderStrategy`

**Files:**
- Modify: `src/xstate_statemachine/cli/strategies/pythonic_builder.py`
- Create: `tests/tests_cli/test_pythonic_builder_strategy.py`

- [ ] **Step 1: Write failing tests**

Create `tests/tests_cli/test_pythonic_builder_strategy.py` following the same pattern as Task 8. Key assertions:

```python
class TestPythonicBuilderStrategy(unittest.TestCase):
    """Tests for pythonic-builder code generation."""

    # ... _make_ctx helper with TRAFFIC_LIGHT_CONFIG ...

    def test_logic_contains_machine_builder(self) -> None:
        s = get_strategy("pythonic-builder")
        code = s.generate_logic(self._make_ctx())
        self.assertIn('MachineBuilder("trafficLight")', code)

    def test_logic_contains_fluent_state_calls(self) -> None:
        s = get_strategy("pythonic-builder")
        code = s.generate_logic(self._make_ctx())
        self.assertIn('.state("green"', code)
        self.assertIn("initial=True", code)
        self.assertIn('.state("yellow")', code)

    def test_logic_contains_transition_calls(self) -> None:
        s = get_strategy("pythonic-builder")
        code = s.generate_logic(self._make_ctx())
        self.assertIn(
            '.transition("green", "TIMER", "yellow"', code
        )

    def test_logic_contains_action_registration(self) -> None:
        s = get_strategy("pythonic-builder")
        code = s.generate_logic(self._make_ctx())
        self.assertIn('.action("logEnter", log_enter)', code)
        self.assertIn('.action("increment", increment)', code)

    def test_logic_contains_guard_registration(self) -> None:
        s = get_strategy("pythonic-builder")
        code = s.generate_logic(self._make_ctx())
        self.assertIn('.guard("isReady", is_ready)', code)

    def test_logic_contains_service_registration(self) -> None:
        s = get_strategy("pythonic-builder")
        code = s.generate_logic(self._make_ctx())
        self.assertIn(
            '.service("fetchData", fetch_data)', code
        )

    def test_logic_contains_build_call(self) -> None:
        s = get_strategy("pythonic-builder")
        code = s.generate_logic(self._make_ctx())
        self.assertIn(".build()", code)

    def test_logic_has_decorated_functions(self) -> None:
        s = get_strategy("pythonic-builder")
        code = s.generate_logic(self._make_ctx())
        self.assertIn("@action", code)
        self.assertIn("@guard", code)
        self.assertIn("@service", code)
        # Module-level functions — no self parameter
        self.assertNotIn("self,", code)

    def test_logic_imports_machine_builder(self) -> None:
        s = get_strategy("pythonic-builder")
        code = s.generate_logic(self._make_ctx())
        self.assertIn("MachineBuilder", code)

    def test_runner_calls_build(self) -> None:
        s = get_strategy("pythonic-builder")
        code = s.generate_runner(self._make_ctx())
        self.assertIn("build()", code)
        self.assertIn("SyncInterpreter(machine)", code)
```

- [ ] **Step 2: Run tests to verify they fail**
- [ ] **Step 3: Implement PythonicBuilderStrategy**

Key difference from pythonic-class: uses `MachineBuilder` fluent API. The `generate_logic()` method produces:
- Module-level `@action`/`@guard`/`@service` decorated functions (no `self`)
- A `def build()` function with `MachineBuilder("id").context({}).state("name", ...).transition(...).action(...).build()` chain

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/tests_cli/test_pythonic_builder_strategy.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/xstate_statemachine/cli/strategies/pythonic_builder.py tests/tests_cli/test_pythonic_builder_strategy.py
git commit -m "feat(cli): implement PythonicBuilderStrategy for MachineBuilder code generation"
```

---

### Task 10: Implement `PythonicFunctionalStrategy`

**Files:**
- Modify: `src/xstate_statemachine/cli/strategies/pythonic_functional.py`
- Create: `tests/tests_cli/test_pythonic_functional_strategy.py`

- [ ] **Step 1: Write failing tests**

Create `tests/tests_cli/test_pythonic_functional_strategy.py`. Key assertions:

```python
class TestPythonicFunctionalStrategy(unittest.TestCase):
    """Tests for pythonic-functional code generation."""

    # ... _make_ctx helper ...

    def test_logic_contains_state_objects(self) -> None:
        s = get_strategy("pythonic-functional")
        code = s.generate_logic(self._make_ctx())
        self.assertIn('green = State(', code)
        self.assertIn('"green"', code)
        self.assertIn("initial=True", code)

    def test_logic_contains_to_transitions(self) -> None:
        s = get_strategy("pythonic-functional")
        code = s.generate_logic(self._make_ctx())
        self.assertIn("green.to(yellow", code)

    def test_logic_contains_build_machine_call(self) -> None:
        s = get_strategy("pythonic-functional")
        code = s.generate_logic(self._make_ctx())
        self.assertIn("build_machine(", code)
        self.assertIn('id="trafficLight"', code)
        self.assertIn("states=[", code)

    def test_logic_states_is_list(self) -> None:
        """build_machine receives states as a List[State]."""
        s = get_strategy("pythonic-functional")
        code = s.generate_logic(self._make_ctx())
        self.assertIn("states=[", code)
        # Verify list contains the state variables (not a dict)
        self.assertNotIn("states={", code)

    def test_logic_imports_build_machine(self) -> None:
        s = get_strategy("pythonic-functional")
        code = s.generate_logic(self._make_ctx())
        self.assertIn("build_machine", code)

    def test_logic_has_decorated_functions(self) -> None:
        s = get_strategy("pythonic-functional")
        code = s.generate_logic(self._make_ctx())
        self.assertIn("@action", code)
        self.assertIn("@guard", code)
        self.assertIn("@service", code)
```

- [ ] **Step 2: Run tests to verify they fail**
- [ ] **Step 3: Implement PythonicFunctionalStrategy**

Key difference: uses `build_machine(id=..., states=[...])`. The `generate_logic()` method produces:
- Module-level `@action`/`@guard`/`@service` decorated functions
- A `def build()` function that creates named `State` objects, calls `.to()` for transitions, then calls `build_machine(id=..., states=[list], ...)`

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/tests_cli/test_pythonic_functional_strategy.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/xstate_statemachine/cli/strategies/pythonic_functional.py tests/tests_cli/test_pythonic_functional_strategy.py
git commit -m "feat(cli): implement PythonicFunctionalStrategy for build_machine code generation"
```

---

## Chunk 4: Integration, Hierarchy, and Final Wiring

### Task 11: Wire `__main__.py` to use strategy registry

**Files:**
- Modify: `src/xstate_statemachine/cli/__main__.py`

- [ ] **Step 1: Modify `run_generation_workflow()` in `__main__.py`**

The key changes:
1. Import `resolve_template`, `resolve_async_mode` from `args.py`
2. Import `get_strategy`, `GenerationContext` from `strategies`
3. After parsing args, resolve template and async mode:

```python
from .args import resolve_template, resolve_async_mode
from .strategies import get_strategy, GenerationContext

# In run_generation_workflow(), after parsing args:
try:
    template = resolve_template(
        getattr(args, 'style', None),
        getattr(args, 'template', None),
    )
except ValueError as e:
    parser.error(str(e))

is_async = resolve_async_mode(args.async_mode, template)
```

4. Build a `GenerationContext` and use the strategy:

```python
strategy = get_strategy(template)
ctx = GenerationContext(
    actions=actions,
    guards=guards,
    services=services,
    is_async=is_async,
    log=log,
    machine_name=machine_name,
    machine_id=machine_id,
    machine_names=machine_names,
    machine_ids=machine_ids,
    file_count=file_count,
    configs=configs,
    json_filenames=json_filenames,
    hierarchy=hierarchy,
    sleep=sleep,
    sleep_time=sleep_time,
    loader=loader,
    style=getattr(args, 'style', None),
)
logic_code = strategy.generate_logic(ctx)
runner_code = strategy.generate_runner(ctx)
```

5. Remove the old `generate_logic_code()` / `generate_runner_code()` calls and replace with strategy calls above.
6. The `_parse_boolean_flags()` function should be updated to skip `async_mode` normalization entirely (remove it from that function — `resolve_async_mode()` handles it now).

- [ ] **Step 2: Run all existing CLI tests**

Run: `uv run pytest tests/tests_cli/ -v`
Expected: All tests PASS

**Note:** If any existing tests fail due to minor formatting differences in the upgraded output (e.g., missing `# noqa`), update those assertions in this task rather than waiting for Task 14.

- [ ] **Step 3: Commit**

```bash
git add src/xstate_statemachine/cli/__main__.py
git commit -m "refactor(cli): wire __main__.py to use strategy registry and template resolution"
```

---

### Task 12: Add hierarchical support for Pythonic templates

**Files:**
- Modify: `src/xstate_statemachine/cli/strategies/pythonic_class.py` (add hierarchy handling to `generate_runner`)
- Modify: `src/xstate_statemachine/cli/strategies/pythonic_builder.py` (same)
- Modify: `src/xstate_statemachine/cli/strategies/pythonic_functional.py` (same)
- Create: `tests/tests_cli/test_hierarchy_pythonic.py`

- [ ] **Step 1: Write failing tests for hierarchical Pythonic generation**

Create `tests/tests_cli/test_hierarchy_pythonic.py`:

```python
# tests/tests_cli/test_hierarchy_pythonic.py
"""Tests for hierarchical machine generation with Pythonic templates."""

import logging
import unittest
from typing import Any

from src.xstate_statemachine.cli.strategies import (
    get_strategy,
)
from src.xstate_statemachine.cli.strategies.base import (
    GenerationContext,
)

from .fixtures import (
    HIERARCHY_CHILD_CONFIG,
    HIERARCHY_PARENT_CONFIG,
)

logger = logging.getLogger(__name__)


class TestHierarchyPythonicClass(unittest.TestCase):
    """Tests for pythonic-class hierarchical generation."""

    def _make_ctx(self, **overrides: Any) -> GenerationContext:
        defaults = dict(
            actions=set(),
            guards=set(),
            services={"childMachine"},
            is_async=False,
            log=True,
            machine_name="parent_machine",
            machine_id="parentMachine",
            machine_names=["parent_machine", "child_machine"],
            machine_ids=["parentMachine", "childMachine"],
            file_count=2,
            configs=[
                HIERARCHY_PARENT_CONFIG,
                HIERARCHY_CHILD_CONFIG,
            ],
            json_filenames=[
                "parent.json", "child.json"
            ],
            hierarchy=True,
            sleep=True,
            sleep_time=2,
            loader=False,
        )
        defaults.update(overrides)
        return GenerationContext(**defaults)

    def test_runner_loads_child_from_json(self) -> None:
        """Hierarchical runner loads child configs from JSON."""
        s = get_strategy("pythonic-class")
        code = s.generate_runner(self._make_ctx())
        self.assertIn("json.loads", code)
        self.assertIn("child.json", code)

    def test_runner_creates_parent_pythonic(self) -> None:
        """Parent is created via Pythonic API."""
        s = get_strategy("pythonic-class")
        code = s.generate_runner(self._make_ctx())
        self.assertIn("create_machine()", code)

    def test_runner_creates_child_interpreter(self) -> None:
        """Runner creates interpreter for child machine."""
        s = get_strategy("pythonic-class")
        code = s.generate_runner(self._make_ctx())
        self.assertIn("SyncInterpreter(", code)

    def test_runner_stops_children_before_parent(self) -> None:
        """Shutdown order: children first, then parent."""
        s = get_strategy("pythonic-class")
        code = s.generate_runner(self._make_ctx())
        # Find specific stop calls
        child_stop = code.find(".stop()")
        parent_stop = code.rfind(".stop()")
        # Both should exist and child stop should be first
        self.assertNotEqual(child_stop, -1)
        self.assertNotEqual(parent_stop, -1)
        self.assertLess(child_stop, parent_stop)
```

- [ ] **Step 2: Run tests to verify they fail**
- [ ] **Step 3: Add hierarchy support to Pythonic strategy runners**

For each Pythonic strategy, update `generate_runner()` to handle `ctx.hierarchy=True`:
- Parent machine is created via the Pythonic API
- Child machines are loaded from JSON and created via `create_machine()`
- Interpreters for all are created, started, event-simulated, and stopped

**Template-specific parent creation in hierarchical runner:**
- `pythonic-class`: `parent_machine = ParentMachine.create_machine()`
- `pythonic-builder`: `parent_machine = build()` (calls the `build()` function)
- `pythonic-functional`: `parent_machine = build()` (calls the `build()` function)

All three share the same child loading logic:
```python
child_cfg = json.loads((root_dir / "child.json").read_text())
child_machine = create_machine(child_cfg)
```

The conversion algorithm should handle both `"cond"` and `"guard"` as the guard key in JSON configs (XState v4 uses `"cond"`, v5 uses `"guard"`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/tests_cli/test_hierarchy_pythonic.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/xstate_statemachine/cli/strategies/ tests/tests_cli/test_hierarchy_pythonic.py
git commit -m "feat(cli): add hierarchical machine support for Pythonic templates"
```

---

### Task 13: Production quality assertion tests

**Files:**
- Create: `tests/tests_cli/test_production_quality.py`

- [ ] **Step 1: Write cross-template production quality tests**

Create `tests/tests_cli/test_production_quality.py`:

```python
# tests/tests_cli/test_production_quality.py
"""Cross-template tests for production quality features."""

import logging
import unittest
from typing import Any

from src.xstate_statemachine.cli.strategies import (
    get_strategy,
)
from src.xstate_statemachine.cli.strategies.base import (
    GenerationContext,
)

logger = logging.getLogger(__name__)

SAMPLE = {
    "id": "testMachine",
    "initial": "idle",
    "context": {},
    "states": {
        "idle": {
            "on": {
                "GO": {
                    "target": "active",
                    "actions": "doSomething",
                    "guard": "isAllowed",
                }
            }
        },
        "active": {
            "invoke": {"src": "loadData"},
        },
    },
}


class TestProductionQuality(unittest.TestCase):
    """Verify production features across all templates."""

    TEMPLATES = [
        "class-json",
        "function-json",
        "pythonic-class",
        "pythonic-builder",
        "pythonic-functional",
    ]

    def _make_ctx(
        self, template: str
    ) -> GenerationContext:
        style = None
        if template == "class-json":
            style = "class"
        elif template == "function-json":
            style = "function"
        return GenerationContext(
            actions={"doSomething"},
            guards={"isAllowed"},
            services={"loadData"},
            is_async=False,
            log=True,
            machine_name="test_machine",
            machine_id="testMachine",
            machine_names=["test_machine"],
            machine_ids=["testMachine"],
            file_count=2,
            configs=[SAMPLE],
            json_filenames=["test.json"],
            hierarchy=False,
            sleep=False,
            sleep_time=0,
            loader=False,
            style=style,
        )

    def test_all_templates_have_type_hints(self) -> None:
        """All templates generate type-annotated action functions."""
        for t in self.TEMPLATES:
            with self.subTest(template=t):
                s = get_strategy(t)
                code = s.generate_logic(self._make_ctx(t))
                self.assertIn("-> None:", code)

    def test_all_templates_have_guard_return_type(self) -> None:
        """All templates generate guards with -> bool return."""
        for t in self.TEMPLATES:
            with self.subTest(template=t):
                s = get_strategy(t)
                code = s.generate_logic(self._make_ctx(t))
                self.assertIn("-> bool:", code)

    def test_all_templates_have_docstrings(self) -> None:
        """All templates generate docstrings."""
        for t in self.TEMPLATES:
            with self.subTest(template=t):
                s = get_strategy(t)
                code = s.generate_logic(self._make_ctx(t))
                self.assertIn('"""', code)

    def test_all_templates_have_logging(self) -> None:
        """All templates include logging calls."""
        for t in self.TEMPLATES:
            with self.subTest(template=t):
                s = get_strategy(t)
                code = s.generate_logic(self._make_ctx(t))
                self.assertIn("logger.info(", code)

    def test_all_templates_have_error_handling(self) -> None:
        """All templates wrap actions in try/except."""
        for t in self.TEMPLATES:
            with self.subTest(template=t):
                s = get_strategy(t)
                code = s.generate_logic(self._make_ctx(t))
                self.assertIn("try:", code)
                self.assertIn("except Exception:", code)
```

- [ ] **Step 2: Run tests**

Run: `uv run pytest tests/tests_cli/test_production_quality.py -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/tests_cli/test_production_quality.py
git commit -m "test(cli): add cross-template production quality assertion tests"
```

---

### Task 14: Update existing test assertions for production quality changes

**Files:**
- Modify: `tests/tests_cli/test_generator.py`
- Modify: `tests/tests_cli/test_main_execution.py`

- [ ] **Step 1: Run existing tests and identify failures**

Run: `uv run pytest tests/tests_cli/test_generator.py tests/tests_cli/test_main_execution.py -v`

The production quality upgrades change the generated output:
- `# noqa` comments are removed
- `Awaitable[None]` becomes `None` for async actions
- Docstrings now have `Args:` sections
- Actions/services are wrapped in try/except

Some existing test assertions may now fail. Fix them by updating the expected strings to match the new output.

- [ ] **Step 2: Update failing assertions**

For each failing test:
- If it asserts `"# noqa"` presence → change to `assertNotIn("# noqa", ...)`
- If it asserts `"Awaitable[None]"` → change to `"-> None:"`
- If it asserts specific docstring format → update to match new format
- If it asserts exact generated code → update to match new output

- [ ] **Step 3: Run all tests**

Run: `uv run pytest tests/tests_cli/ -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add tests/tests_cli/test_generator.py tests/tests_cli/test_main_execution.py
git commit -m "test(cli): update existing tests for production-quality output changes"
```

---

### Task 15: Version bump and CHANGELOG update

**Files:**
- Modify: `src/xstate_statemachine/__init__.py` (version bump)
- Modify: `pyproject.toml` (version bump)
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Bump version to 0.5.0**

In `src/xstate_statemachine/__init__.py`, change:
```python
__version__ = "0.5.0"
```

In `pyproject.toml`, change:
```toml
version = "0.5.0"
```

- [ ] **Step 2: Update CHANGELOG.md**

Add a new `## [0.5.0] - 2026-03-22` section. Move existing `[Unreleased]` content into this new section and reset `[Unreleased]` to empty. Add:
- **Added**: CLI `--template` flag with 5 template types, Pythonic code generation, strategy pattern architecture
- **Changed**: Generated code now includes rich docstrings, error handling, type hints; `--async-mode` defaults are template-aware
- **Deprecated**: `--style` flag (use `--template` instead, will be removed in v0.6.0)

- [ ] **Step 3: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: ALL tests PASS

- [ ] **Step 4: Commit**

```bash
git add src/xstate_statemachine/__init__.py pyproject.toml CHANGELOG.md
git commit -m "chore: bump version to 0.5.0 and update CHANGELOG"
```

---

### Task 16: Final integration test — end-to-end CLI with Pythonic templates

**Files:**
- Modify: `tests/tests_cli/test_main_execution.py` (append new test class)

- [ ] **Step 1: Write end-to-end tests for new CLI flow**

Append to `tests/tests_cli/test_main_execution.py`:

```python
class TestPythonicTemplateExecution(CLITestCaseBase):
    """End-to-end tests for Pythonic template CLI execution."""

    def setUp(self) -> None:
        super().setUp()
        self.json_path = create_temp_json(
            SAMPLE_CONFIG_SIMPLE
        )

    def test_pythonic_class_generates_files(self) -> None:
        """--template pythonic-class generates output files."""
        with patch("sys.argv", [
            "cli.py", "generate-template",
            str(self.json_path),
            "--template", "pythonic-class",
            "--force",
        ]):
            main()
        logic = Path("simple_logic.py")
        runner = Path("simple_runner.py")
        self.assertTrue(logic.exists())
        self.assertTrue(runner.exists())
        content = logic.read_text()
        self.assertIn("StateMachine", content)
        self.assertIn("State(", content)

    def test_pythonic_builder_generates_files(self) -> None:
        """--template pythonic-builder generates output files."""
        with patch("sys.argv", [
            "cli.py", "generate-template",
            str(self.json_path),
            "--template", "pythonic-builder",
            "--force",
        ]):
            main()
        logic = Path("simple_logic.py")
        self.assertTrue(logic.exists())
        content = logic.read_text()
        self.assertIn("MachineBuilder", content)

    def test_pythonic_functional_generates_files(self) -> None:
        """--template pythonic-functional generates output."""
        with patch("sys.argv", [
            "cli.py", "generate-template",
            str(self.json_path),
            "--template", "pythonic-functional",
            "--force",
        ]):
            main()
        logic = Path("simple_logic.py")
        self.assertTrue(logic.exists())
        content = logic.read_text()
        self.assertIn("build_machine(", content)

    def test_style_class_shows_deprecation(self) -> None:
        """--style class triggers DeprecationWarning."""
        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            with patch("sys.argv", [
                "cli.py", "generate-template",
                str(self.json_path),
                "--style", "class",
                "--force",
            ]):
                main()
            deprecation_warnings = [
                x for x in w
                if issubclass(
                    x.category, DeprecationWarning
                )
            ]
            self.assertGreater(len(deprecation_warnings), 0)

    def test_style_and_template_conflict(self) -> None:
        """Using both --style and --template errors."""
        with patch("sys.argv", [
            "cli.py", "generate-template",
            str(self.json_path),
            "--style", "class",
            "--template", "pythonic-class",
        ]):
            with self.assertRaises(SystemExit):
                main()
```

- [ ] **Step 2: Run the end-to-end tests**

Run: `uv run pytest tests/tests_cli/test_main_execution.py::TestPythonicTemplateExecution -v`
Expected: All tests PASS

- [ ] **Step 3: Run FULL test suite**

Run: `uv run pytest tests/ -v`
Expected: ALL tests PASS (including all 143 pythonic tests, all CLI tests, all existing tests)

- [ ] **Step 4: Commit**

```bash
git add tests/tests_cli/test_main_execution.py
git commit -m "test(cli): add end-to-end integration tests for Pythonic template CLI flow"
```

---

## Final Summary

| Task | Description | New Files | Modified Files |
|------|-------------|-----------|----------------|
| 1 | BaseStrategy + GenerationContext | `strategies/base.py`, `strategies/__init__.py`, `test_strategy_registry.py` | - |
| 2 | _shared.py helpers | `strategies/_shared.py` | `test_strategy_registry.py` |
| 3 | --template flag + deprecation | `test_args.py` | `args.py` |
| 4 | Strategy registry + stubs | `class_json.py`, `function_json.py`, `pythonic_class.py`, `pythonic_builder.py`, `pythonic_functional.py` | `strategies/__init__.py` |
| 5 | ClassJsonStrategy | - | `class_json.py`, `test_class_json_strategy.py` |
| 6 | FunctionJsonStrategy | `test_function_json_strategy.py` | `function_json.py` |
| 7 | Refactor generator.py | - | `generator.py` |
| 8 | PythonicClassStrategy | `test_pythonic_class_strategy.py` | `pythonic_class.py` |
| 9 | PythonicBuilderStrategy | `test_pythonic_builder_strategy.py` | `pythonic_builder.py` |
| 10 | PythonicFunctionalStrategy | `test_pythonic_functional_strategy.py` | `pythonic_functional.py` |
| 11 | Wire __main__.py | - | `__main__.py` |
| 12 | Hierarchy support | `test_hierarchy_pythonic.py` | 3 Pythonic strategies |
| 13 | Production quality tests | `test_production_quality.py` | - |
| 14 | Update existing test assertions | - | `test_generator.py`, `test_main_execution.py` |
| 15 | Version bump + CHANGELOG | - | `__init__.py`, `pyproject.toml`, `CHANGELOG.md` |
| 16 | End-to-end integration tests | - | `test_main_execution.py` |
