# Pythonic API Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Pythonic API layer (`State`, `StateMachine`, `MachineBuilder`, `build_machine`, decorators) to `xstate-statemachine` that compiles to the existing JSON config + `MachineLogic` contract.

**Architecture:** A single new file `src/xstate_statemachine/pythonic.py` contains all code. It produces `(config_dict, MachineLogic)` pairs and delegates to the existing `create_machine()`. Zero changes to existing core files. New exports added to `__init__.py`.

**Tech Stack:** Python 3.9+, `functools.partial` for self-binding, `asyncio.iscoroutinefunction` for guard validation, existing `MachineLogic` / `create_machine` / `InvalidConfigError` / `NotSupportedError`.

**Spec:** `docs/superpowers/specs/2026-03-22-pythonic-api-design.md`

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `src/xstate_statemachine/pythonic.py` | CREATE | All Pythonic API classes and functions |
| `src/xstate_statemachine/__init__.py` | MODIFY | Add 8 new exports to `__all__` and import them |
| `tests/test_pythonic.py` | CREATE | All tests for Pythonic API (~75 test cases) |
| `CHANGELOG.md` | MODIFY | Add entry under `## [Unreleased]` |

Existing files are NOT modified: `factory.py`, `models.py`, `interpreter.py`, `sync_interpreter.py`, `machine_logic.py`, `logic_loader.py`.

---

## Chunk 1: Foundation — `_snake_to_camel`, `State`, `Transition`, `TransitionGroup`

### Task 1: `_snake_to_camel` helper and `State` class basics

**Files:**
- Create: `src/xstate_statemachine/pythonic.py`
- Create: `tests/test_pythonic.py`

- [ ] **Step 1: Write failing tests for `_snake_to_camel` and basic `State`**

```python
# tests/test_pythonic.py
"""Tests for the Pythonic API layer."""

# -------------------------------------------------------------------------
# 📦 Standard Library Imports
# -------------------------------------------------------------------------
import unittest

# -------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -------------------------------------------------------------------------
from xstate_statemachine.pythonic import _snake_to_camel, State


class TestSnakeToCamel(unittest.TestCase):
    """Tests for the _snake_to_camel helper."""

    def test_simple_conversion(self):
        self.assertEqual(_snake_to_camel("hello_world"), "helloWorld")

    def test_single_word(self):
        self.assertEqual(_snake_to_camel("hello"), "hello")

    def test_multiple_underscores(self):
        self.assertEqual(_snake_to_camel("a_b_c"), "aBC")

    def test_already_camel(self):
        self.assertEqual(_snake_to_camel("helloWorld"), "helloWorld")


class TestState(unittest.TestCase):
    """Tests for the State class."""

    def test_state_basic_attributes(self):
        s = State("idle")
        self.assertEqual(s.name, "idle")
        self.assertFalse(s.initial)
        self.assertFalse(s.final)
        self.assertFalse(s.parallel)

    def test_state_initial_flag(self):
        s = State("idle", initial=True)
        self.assertTrue(s.initial)

    def test_state_final_type(self):
        s = State("done", final=True)
        self.assertTrue(s.final)

    def test_state_parallel_type(self):
        s = State("regions", parallel=True)
        self.assertTrue(s.parallel)

    def test_state_final_and_parallel_raises(self):
        with self.assertRaises(Exception):
            State("bad", final=True, parallel=True)

    def test_state_name_defaults_to_empty(self):
        s = State()
        self.assertEqual(s.name, "")

    def test_state_nested_children(self):
        child1 = State("a", initial=True)
        child2 = State("b")
        parent = State("parent", states=[child1, child2])
        self.assertEqual(len(parent.states), 2)
        self.assertEqual(parent.states[0].name, "a")

    def test_state_on_dict(self):
        s = State("idle", on={"CLICK": "active"})
        self.assertEqual(s.on, {"CLICK": "active"})

    def test_state_entry_exit(self):
        s = State("idle", entry=["logEntry"], exit=["cleanup"])
        self.assertEqual(s.entry, ["logEntry"])
        self.assertEqual(s.exit, ["cleanup"])

    def test_state_after(self):
        s = State("waiting", after={1000: "timeout"})
        self.assertEqual(s.after, {1000: "timeout"})

    def test_state_invoke_single(self):
        s = State("loading", invoke={"src": "fetchData"})
        self.assertEqual(s.invoke, {"src": "fetchData"})

    def test_state_invoke_list(self):
        inv = [{"src": "svc1"}, {"src": "svc2"}]
        s = State("loading", invoke=inv)
        self.assertEqual(s.invoke, inv)

    def test_state_on_done(self):
        s = State("parent", on_done="next")
        self.assertEqual(s.on_done, "next")

    def test_state_always(self):
        s = State("check", always={"target": "done"})
        self.assertEqual(s.always, {"target": "done"})

    def test_state_context(self):
        s = State("root", context={"count": 0})
        self.assertEqual(s.context, {"count": 0})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_pythonic.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'xstate_statemachine.pythonic'`

- [ ] **Step 3: Write minimal `_snake_to_camel` and `State` implementation**

```python
# src/xstate_statemachine/pythonic.py
"""
🐍 Pythonic API for xstate-statemachine.

This module provides three API styles for defining state machines in pure
Python, without writing JSON config dicts:

1. **Class-based** — ``StateMachine`` base class with metaclass
2. **Builder** — ``MachineBuilder`` fluent API
3. **Functional** — ``build_machine()`` with module-level helpers

All three styles compile to the same JSON config dict + ``MachineLogic``
pair and delegate to the existing ``create_machine()`` factory.
"""

# -------------------------------------------------------------------------
# 📦 Standard Library Imports
# -------------------------------------------------------------------------
import asyncio
import functools
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Union,
)

# -------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -------------------------------------------------------------------------
from .exceptions import InvalidConfigError, NotSupportedError
from .factory import create_machine as _original_create_machine
from .machine_logic import MachineLogic


# -------------------------------------------------------------------------
# 🛠️ Internal Helpers
# -------------------------------------------------------------------------


def _snake_to_camel(snake_str: str) -> str:
    """Convert snake_case to camelCase.

    Matches the behavior of ``LogicLoader._snake_to_camel`` in
    ``logic_loader.py`` so that function names auto-map consistently.

    Args:
        snake_str: A snake_case string (e.g., ``"my_action_name"``).

    Returns:
        The camelCase equivalent (e.g., ``"myActionName"``).
    """
    components = snake_str.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


# -------------------------------------------------------------------------
# 🏗️ State
# -------------------------------------------------------------------------


class State:
    """A state definition for use in all three Pythonic API styles.

    Args:
        name: State name. Auto-inferred from the class attribute name
            in ``StateMachine`` subclasses if left empty.
        initial: Whether this is the initial state among its siblings.
        final: Whether this is a final (terminal) state.
        parallel: Whether this is a parallel state.
        on: Event-to-target shorthand dict, e.g. ``{"CLICK": "active"}``.
        entry: List of entry action names.
        exit: List of exit action names.
        after: Delayed transition dict, e.g. ``{1000: "timeout"}``.
        invoke: Service invocation config (dict or list of dicts).
        on_done: Completion transition (string target or dict).
        always: Eventless transition config.
        context: Initial context dict (only meaningful at root level).
        states: List of child ``State`` objects for hierarchy.

    Raises:
        InvalidConfigError: If ``final`` and ``parallel`` are both True.
    """

    def __init__(
        self,
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
        states: Optional[List["State"]] = None,
    ) -> None:
        if final and parallel:
            raise InvalidConfigError(
                f"State '{name}' cannot be both final and parallel"
            )
        self.name = name
        self.initial = initial
        self.final = final
        self.parallel = parallel
        self.on = on
        self.entry = entry or []
        self.exit = exit or []
        self.after = after
        self.invoke = invoke
        self.on_done = on_done
        self.always = always
        self.context = context
        self.states = states or []
        # 📝 Internal: tracks functions registered via @state.enter/@state.exit
        self._enter_decorators: List[Callable] = []
        self._exit_decorators: List[Callable] = []

    def __init_subclass__(
        cls,
        *,
        initial: bool = False,
        final: bool = False,
        parallel: bool = False,
        **kwargs: Any,
    ) -> None:
        """Support ``class MyState(State, parallel=True):`` syntax."""
        super().__init_subclass__(**kwargs)
        cls._xsm_initial = initial
        cls._xsm_final = final
        cls._xsm_parallel = parallel

    def to(
        self,
        target: "State",
        *,
        event: Optional[str] = None,
        guard: Optional[str] = None,
        actions: Optional[List[str]] = None,
        reenter: bool = False,
    ) -> "Transition":
        """Create a transition from this state to a target state.

        Args:
            target: The destination ``State`` object.
            event: The event name that triggers this transition (REQUIRED).
            guard: Optional guard function name.
            actions: Optional list of action names.
            reenter: Force exit/re-entry on self-transitions.

        Returns:
            A ``Transition`` object.

        Raises:
            InvalidConfigError: If ``event`` is not provided.
        """
        if event is None:
            raise InvalidConfigError(
                "State.to() requires an 'event' argument. "
                "For eventless transitions, use the 'always' "
                "parameter on State()"
            )
        return Transition(
            source=self,
            target=target,
            event=event,
            guard=guard,
            actions=actions or [],
            reenter=reenter,
            internal=False,
        )

    def internal(
        self,
        event: str,
        *,
        guard: Optional[str] = None,
        actions: Optional[List[str]] = None,
    ) -> "Transition":
        """Create an internal transition (no state change).

        Args:
            event: The event name.
            guard: Optional guard function name.
            actions: Optional list of action names.

        Returns:
            A ``Transition`` object with ``internal=True``.
        """
        return Transition(
            source=self,
            target=None,
            event=event,
            guard=guard,
            actions=actions or [],
            reenter=False,
            internal=True,
        )

    def enter(self, fn: Callable) -> Callable:
        """Decorator to register a function as an entry action.

        Only valid inside a ``StateMachine`` class definition.

        Args:
            fn: The function to register.

        Returns:
            The original function, with ``_xsm_type`` and ``_xsm_name``
            markers attached.
        """
        name = _snake_to_camel(fn.__name__)
        fn._xsm_type = "action"
        fn._xsm_name = name
        fn._xsm_state_enter = self
        self._enter_decorators.append(fn)
        if name not in self.entry:
            self.entry.append(name)
        return fn

    def exit(self, fn: Callable) -> Callable:
        """Decorator to register a function as an exit action.

        Only valid inside a ``StateMachine`` class definition.

        Args:
            fn: The function to register.

        Returns:
            The original function, with ``_xsm_type`` and ``_xsm_name``
            markers attached.
        """
        name = _snake_to_camel(fn.__name__)
        fn._xsm_type = "action"
        fn._xsm_name = name
        fn._xsm_state_exit = self
        self._exit_decorators.append(fn)
        if name not in self.exit:
            self.exit.append(name)
        return fn
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_pythonic.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/xstate_statemachine/pythonic.py tests/test_pythonic.py
git commit -m "feat(pythonic): add _snake_to_camel helper and State class"
```

---

### Task 2: `Transition`, `TransitionGroup`, and `transition()` function

**Files:**
- Modify: `src/xstate_statemachine/pythonic.py`
- Modify: `tests/test_pythonic.py`

- [ ] **Step 1: Write failing tests for Transition and TransitionGroup**

Append to `tests/test_pythonic.py`:

```python
from xstate_statemachine.pythonic import (
    State,
    Transition,
    TransitionGroup,
    transition,
)


class TestTransition(unittest.TestCase):
    """Tests for the Transition class."""

    def setUp(self):
        self.idle = State("idle", initial=True)
        self.running = State("running")

    def test_transition_basic(self):
        t = self.idle.to(self.running, event="START")
        self.assertIsInstance(t, Transition)
        self.assertEqual(t.source, self.idle)
        self.assertEqual(t.target, self.running)
        self.assertEqual(t.event, "START")
        self.assertIsNone(t.guard)
        self.assertEqual(t.actions, [])

    def test_transition_with_guard_and_actions(self):
        t = self.idle.to(
            self.running,
            event="GO",
            guard="isReady",
            actions=["prepare", "log"],
        )
        self.assertEqual(t.guard, "isReady")
        self.assertEqual(t.actions, ["prepare", "log"])

    def test_transition_reenter(self):
        t = self.idle.to(
            self.idle, event="RETRY", reenter=True
        )
        self.assertTrue(t.reenter)

    def test_transition_internal(self):
        t = self.idle.internal("HEARTBEAT", actions=["logHb"])
        self.assertTrue(t.internal)
        self.assertIsNone(t.target)
        self.assertEqual(t.actions, ["logHb"])

    def test_transition_without_event_raises(self):
        with self.assertRaises(Exception):
            self.idle.to(self.running)

    def test_transition_combine_with_pipe(self):
        a = State("a", initial=True)
        b = State("b")
        c = State("c")
        group = a.to(b, event="GO") | b.to(c, event="GO")
        self.assertIsInstance(group, TransitionGroup)
        self.assertEqual(len(group.transitions), 2)

    def test_transition_group_pipe_chain(self):
        a = State("a", initial=True)
        b = State("b")
        c = State("c")
        group = (
            a.to(b, event="X")
            | b.to(c, event="X")
            | c.to(a, event="X")
        )
        self.assertEqual(len(group.transitions), 3)

    def test_transition_standalone_function(self):
        t = transition(self.idle, "START", self.running)
        self.assertIsInstance(t, Transition)
        self.assertEqual(t.event, "START")
        self.assertEqual(t.source, self.idle)
        self.assertEqual(t.target, self.running)

    def test_transition_standalone_with_kwargs(self):
        t = transition(
            self.idle,
            "GO",
            self.running,
            guard="ok",
            actions=["log"],
        )
        self.assertEqual(t.guard, "ok")
        self.assertEqual(t.actions, ["log"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_pythonic.py::TestTransition -v`
Expected: FAIL — `ImportError: cannot import name 'Transition'`

- [ ] **Step 3: Write `Transition`, `TransitionGroup`, and `transition()` implementations**

Append to `src/xstate_statemachine/pythonic.py`:

```python
# -------------------------------------------------------------------------
# 🔀 Transition & TransitionGroup
# -------------------------------------------------------------------------


class Transition:
    """A transition between two states, triggered by an event.

    Created by ``State.to()`` or the ``transition()`` function.
    Not typically instantiated directly by users.

    Attributes:
        source: The source ``State``.
        target: The target ``State`` (``None`` for internal transitions).
        event: The event name that triggers this transition.
        guard: Optional guard function name.
        actions: List of action names to execute.
        reenter: Whether to force exit/re-entry on self-transitions.
        internal: Whether this is an internal transition.
    """

    def __init__(
        self,
        source: State,
        target: Optional[State],
        event: str,
        guard: Optional[str] = None,
        actions: Optional[List[str]] = None,
        reenter: bool = False,
        internal: bool = False,
    ) -> None:
        self.source = source
        self.target = target
        self.event = event
        self.guard = guard
        self.actions = actions or []
        self.reenter = reenter
        self.internal = internal

    def __or__(
        self, other: "Union[Transition, TransitionGroup]"
    ) -> "TransitionGroup":
        """Combine transitions with the ``|`` operator."""
        if isinstance(other, TransitionGroup):
            return TransitionGroup([self] + other.transitions)
        return TransitionGroup([self, other])


class TransitionGroup:
    """A collection of ``Transition`` objects, created by the ``|`` operator.

    Users never instantiate this directly. It is created implicitly
    when combining transitions with ``|``.

    Attributes:
        transitions: The list of ``Transition`` objects in this group.
    """

    def __init__(self, transitions: List[Transition]) -> None:
        self.transitions = transitions

    def __or__(
        self, other: "Union[Transition, TransitionGroup]"
    ) -> "TransitionGroup":
        """Combine with another transition or group."""
        if isinstance(other, TransitionGroup):
            return TransitionGroup(
                self.transitions + other.transitions
            )
        return TransitionGroup(self.transitions + [other])


def transition(
    source: State,
    event: str,
    target: State,
    *,
    guard: Optional[str] = None,
    actions: Optional[List[str]] = None,
    reenter: bool = False,
    internal: bool = False,
) -> Transition:
    """Create a transition between two states (functional API).

    Equivalent to ``source.to(target, event=event, ...)``.

    Args:
        source: The source ``State``.
        event: The event name (required).
        target: The target ``State``.
        guard: Optional guard function name.
        actions: Optional list of action names.
        reenter: Whether to force exit/re-entry.
        internal: Whether this is an internal transition.

    Returns:
        A ``Transition`` object.
    """
    return Transition(
        source=source,
        target=target,
        event=event,
        guard=guard,
        actions=actions or [],
        reenter=reenter,
        internal=internal,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_pythonic.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/xstate_statemachine/pythonic.py tests/test_pythonic.py
git commit -m "feat(pythonic): add Transition, TransitionGroup, and transition()"
```

---

### Task 3: Decorators — `@action`, `@guard`, `@service`

**Files:**
- Modify: `src/xstate_statemachine/pythonic.py`
- Modify: `tests/test_pythonic.py`

- [ ] **Step 1: Write failing tests for decorators**

Append to `tests/test_pythonic.py`:

```python
from xstate_statemachine.pythonic import action, guard, service


class TestDecorators(unittest.TestCase):
    """Tests for @action, @guard, @service decorators."""

    def test_action_decorator_auto_name(self):
        @action
        def increment_counter(i, ctx, e, a):
            pass

        self.assertEqual(increment_counter._xsm_type, "action")
        self.assertEqual(
            increment_counter._xsm_name, "incrementCounter"
        )

    def test_action_decorator_explicit_name(self):
        @action("customName")
        def my_func(i, ctx, e, a):
            pass

        self.assertEqual(my_func._xsm_name, "customName")

    def test_guard_decorator(self):
        @guard
        def can_retry(ctx, e):
            return True

        self.assertEqual(can_retry._xsm_type, "guard")
        self.assertEqual(can_retry._xsm_name, "canRetry")

    def test_service_decorator(self):
        @service
        def fetch_data(i, ctx, e):
            pass

        self.assertEqual(fetch_data._xsm_type, "service")
        self.assertEqual(fetch_data._xsm_name, "fetchData")

    def test_guard_async_raises_error(self):
        with self.assertRaises(NotSupportedError):

            @guard
            async def bad_guard(ctx, e):
                return True

    def test_action_decorator_preserves_function(self):
        @action
        def my_action(i, ctx, e, a):
            return 42

        self.assertEqual(my_action(None, None, None, None), 42)

    def test_guard_explicit_name(self):
        @guard("myGuard")
        def some_guard(ctx, e):
            return True

        self.assertEqual(some_guard._xsm_name, "myGuard")

    def test_service_explicit_name(self):
        @service("myService")
        def some_service(i, ctx, e):
            pass

        self.assertEqual(some_service._xsm_name, "myService")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_pythonic.py::TestDecorators -v`
Expected: FAIL — `ImportError: cannot import name 'action'`

- [ ] **Step 3: Write decorator implementations**

Append to `src/xstate_statemachine/pythonic.py`:

```python
# -------------------------------------------------------------------------
# 🏷️ Decorators
# -------------------------------------------------------------------------


def action(fn_or_name=None):
    """Decorator to mark a function as a state machine action.

    Can be used with or without arguments:
        - ``@action`` — auto-generates name from function name
        - ``@action("customName")`` — uses explicit name

    Args:
        fn_or_name: Either the function (when used as ``@action``)
            or a string name (when used as ``@action("name")``).

    Returns:
        The decorated function with ``_xsm_type`` and ``_xsm_name``
        attributes set.
    """
    if callable(fn_or_name):
        # 📝 Used as @action (no parentheses)
        fn = fn_or_name
        fn._xsm_type = "action"
        fn._xsm_name = _snake_to_camel(fn.__name__)
        return fn
    else:
        # 📝 Used as @action("customName")
        name = fn_or_name

        def decorator(fn):
            fn._xsm_type = "action"
            fn._xsm_name = name
            return fn

        return decorator


def guard(fn_or_name=None):
    """Decorator to mark a function as a state machine guard.

    Guards MUST be synchronous. Async guards raise ``NotSupportedError``.

    Can be used with or without arguments:
        - ``@guard`` — auto-generates name from function name
        - ``@guard("customName")`` — uses explicit name

    Args:
        fn_or_name: Either the function or a string name.

    Returns:
        The decorated function with ``_xsm_type`` and ``_xsm_name``
        attributes set.

    Raises:
        NotSupportedError: If the function is async.
    """
    if callable(fn_or_name):
        fn = fn_or_name
        if asyncio.iscoroutinefunction(fn):
            raise NotSupportedError(
                f"Guard '{fn.__name__}' must be synchronous "
                f"(guards cannot be async)"
            )
        fn._xsm_type = "guard"
        fn._xsm_name = _snake_to_camel(fn.__name__)
        return fn
    else:
        name = fn_or_name

        def decorator(fn):
            if asyncio.iscoroutinefunction(fn):
                raise NotSupportedError(
                    f"Guard '{fn.__name__}' must be synchronous "
                    f"(guards cannot be async)"
                )
            fn._xsm_type = "guard"
            fn._xsm_name = name
            return fn

        return decorator


def service(fn_or_name=None):
    """Decorator to mark a function as a state machine service.

    Services can be sync or async.

    Can be used with or without arguments:
        - ``@service`` — auto-generates name from function name
        - ``@service("customName")`` — uses explicit name

    Args:
        fn_or_name: Either the function or a string name.

    Returns:
        The decorated function with ``_xsm_type`` and ``_xsm_name``
        attributes set.
    """
    if callable(fn_or_name):
        fn = fn_or_name
        fn._xsm_type = "service"
        fn._xsm_name = _snake_to_camel(fn.__name__)
        return fn
    else:
        name = fn_or_name

        def decorator(fn):
            fn._xsm_type = "service"
            fn._xsm_name = name
            return fn

        return decorator
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_pythonic.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/xstate_statemachine/pythonic.py tests/test_pythonic.py
git commit -m "feat(pythonic): add @action, @guard, @service decorators"
```

---

## Chunk 2: Compiler — `_compile_config` and `_compile_logic`

### Task 4: `_compile_state` and `_compile_config`

**Files:**
- Modify: `src/xstate_statemachine/pythonic.py`
- Modify: `tests/test_pythonic.py`

- [ ] **Step 1: Write failing tests for config compilation**

Append to `tests/test_pythonic.py`:

```python
from xstate_statemachine.pythonic import _compile_config


class TestCompileConfig(unittest.TestCase):
    """Tests for _compile_config internal function."""

    def test_basic_two_state_machine(self):
        idle = State("idle", initial=True)
        running = State("running")
        t = idle.to(running, event="START")
        config = _compile_config(
            machine_id="test",
            states=[idle, running],
            transitions=[t],
            context=None,
        )
        self.assertEqual(config["id"], "test")
        self.assertEqual(config["initial"], "idle")
        self.assertIn("idle", config["states"])
        self.assertIn("running", config["states"])
        self.assertEqual(
            config["states"]["idle"]["on"]["START"],
            {"target": "running"},
        )

    def test_transition_with_guard_and_actions(self):
        a = State("a", initial=True)
        b = State("b")
        t = a.to(b, event="GO", guard="ok", actions=["log"])
        config = _compile_config(
            machine_id="t", states=[a, b], transitions=[t], context=None
        )
        on_go = config["states"]["a"]["on"]["GO"]
        self.assertEqual(on_go["target"], "b")
        self.assertEqual(on_go["guard"], "ok")
        self.assertEqual(on_go["actions"], ["log"])

    def test_internal_transition_omits_target(self):
        a = State("a", initial=True)
        t = a.internal("HB", actions=["logHb"])
        config = _compile_config(
            machine_id="t", states=[a], transitions=[t], context=None
        )
        on_hb = config["states"]["a"]["on"]["HB"]
        self.assertNotIn("target", on_hb)
        self.assertEqual(on_hb["actions"], ["logHb"])

    def test_reenter_compiles_flag(self):
        a = State("a", initial=True)
        t = a.to(a, event="R", reenter=True)
        config = _compile_config(
            machine_id="t", states=[a], transitions=[t], context=None
        )
        self.assertTrue(config["states"]["a"]["on"]["R"]["reenter"])

    def test_conditional_transitions_same_event(self):
        a = State("a", initial=True)
        b = State("b")
        c = State("c")
        group = (
            a.to(b, event="GO", guard="g1")
            | a.to(c, event="GO")
        )
        config = _compile_config(
            machine_id="t",
            states=[a, b, c],
            transitions=[group],
            context=None,
        )
        on_go = config["states"]["a"]["on"]["GO"]
        self.assertIsInstance(on_go, list)
        self.assertEqual(len(on_go), 2)

    def test_final_state_type(self):
        a = State("a", initial=True)
        done = State("done", final=True)
        config = _compile_config(
            machine_id="t", states=[a, done], transitions=[], context=None
        )
        self.assertEqual(config["states"]["done"]["type"], "final")

    def test_parallel_state_type(self):
        r1 = State("r1", states=[State("a", initial=True)])
        r2 = State("r2", states=[State("b", initial=True)])
        p = State("p", parallel=True, states=[r1, r2])
        config = _compile_config(
            machine_id="t",
            states=[p],
            transitions=[],
            context=None,
        )
        self.assertEqual(config["states"]["p"]["type"], "parallel")

    def test_nested_states(self):
        child1 = State("c1", initial=True)
        child2 = State("c2")
        parent = State("parent", initial=True, states=[child1, child2])
        config = _compile_config(
            machine_id="t",
            states=[parent],
            transitions=[],
            context=None,
        )
        p_config = config["states"]["parent"]
        self.assertEqual(p_config["initial"], "c1")
        self.assertIn("c1", p_config["states"])
        self.assertIn("c2", p_config["states"])

    def test_context_passed_through(self):
        a = State("a", initial=True)
        config = _compile_config(
            machine_id="t",
            states=[a],
            transitions=[],
            context={"count": 0},
        )
        self.assertEqual(config["context"], {"count": 0})

    def test_state_on_dict_used_when_no_transition(self):
        a = State("a", initial=True, on={"CLICK": "b"})
        b = State("b")
        config = _compile_config(
            machine_id="t", states=[a, b], transitions=[], context=None
        )
        self.assertEqual(
            config["states"]["a"]["on"]["CLICK"], "b"
        )

    def test_transition_overrides_state_on(self):
        a = State("a", initial=True, on={"GO": "b"})
        b = State("b")
        c = State("c")
        t = a.to(c, event="GO", guard="check")
        config = _compile_config(
            machine_id="t",
            states=[a, b, c],
            transitions=[t],
            context=None,
        )
        on_go = config["states"]["a"]["on"]["GO"]
        self.assertEqual(on_go["target"], "c")
        self.assertEqual(on_go["guard"], "check")

    def test_always_string_compiles_to_empty_event(self):
        a = State("a", initial=True, always="done")
        done = State("done")
        config = _compile_config(
            machine_id="t", states=[a, done], transitions=[], context=None
        )
        self.assertEqual(config["states"]["a"]["on"][""], "done")

    def test_always_dict_compiles_to_empty_event(self):
        a = State(
            "a",
            initial=True,
            always={"target": "done", "guard": "isOk"},
        )
        done = State("done")
        config = _compile_config(
            machine_id="t", states=[a, done], transitions=[], context=None
        )
        self.assertEqual(
            config["states"]["a"]["on"][""],
            {"target": "done", "guard": "isOk"},
        )

    def test_on_done_string_compiles(self):
        child = State("child", initial=True, final=True)
        parent = State(
            "parent", initial=True, on_done="next", states=[child]
        )
        nxt = State("next")
        config = _compile_config(
            machine_id="t",
            states=[parent, nxt],
            transitions=[],
            context=None,
        )
        self.assertEqual(
            config["states"]["parent"]["onDone"],
            {"target": "next"},
        )

    def test_after_passed_through(self):
        a = State("a", initial=True, after={1000: "b"})
        b = State("b")
        config = _compile_config(
            machine_id="t", states=[a, b], transitions=[], context=None
        )
        self.assertEqual(config["states"]["a"]["after"], {1000: "b"})

    def test_invoke_passed_through(self):
        a = State(
            "a",
            initial=True,
            invoke={"src": "svc", "onDone": "b"},
        )
        b = State("b")
        config = _compile_config(
            machine_id="t", states=[a, b], transitions=[], context=None
        )
        self.assertEqual(
            config["states"]["a"]["invoke"],
            {"src": "svc", "onDone": "b"},
        )

    def test_entry_exit_in_config(self):
        a = State("a", initial=True, entry=["logIn"], exit=["logOut"])
        config = _compile_config(
            machine_id="t", states=[a], transitions=[], context=None
        )
        self.assertEqual(config["states"]["a"]["entry"], ["logIn"])
        self.assertEqual(config["states"]["a"]["exit"], ["logOut"])

    def test_no_initial_state_raises(self):
        a = State("a")
        b = State("b")
        with self.assertRaises(InvalidConfigError):
            _compile_config(
                machine_id="t",
                states=[a, b],
                transitions=[],
                context=None,
            )

    def test_multiple_initial_states_raises(self):
        a = State("a", initial=True)
        b = State("b", initial=True)
        with self.assertRaises(InvalidConfigError):
            _compile_config(
                machine_id="t",
                states=[a, b],
                transitions=[],
                context=None,
            )

    def test_duplicate_state_name_raises(self):
        a = State("a", initial=True)
        a2 = State("a")
        with self.assertRaises(InvalidConfigError):
            _compile_config(
                machine_id="t",
                states=[a, a2],
                transitions=[],
                context=None,
            )

    def test_unknown_transition_source_raises(self):
        a = State("a", initial=True)
        b = State("b")
        orphan = State("orphan")
        t = orphan.to(a, event="GO")
        with self.assertRaises(InvalidConfigError):
            _compile_config(
                machine_id="t",
                states=[a, b],
                transitions=[t],
                context=None,
            )

    def test_nested_state_dot_paths(self):
        child = State("c1", initial=True)
        parent = State("parent", initial=True, states=[child])
        other = State("other")
        t = child.to(other, event="GO")
        config = _compile_config(
            machine_id="t",
            states=[parent, other],
            transitions=[t],
            context=None,
        )
        on_go = config["states"]["parent"]["states"]["c1"]["on"]["GO"]
        self.assertEqual(on_go["target"], "other")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_pythonic.py::TestCompileConfig -v`
Expected: FAIL — `ImportError: cannot import name '_compile_config'`

- [ ] **Step 3: Write `_compile_state` and `_compile_config` implementation**

Append to `src/xstate_statemachine/pythonic.py`:

```python
# -------------------------------------------------------------------------
# ⚙️ Config Compiler
# -------------------------------------------------------------------------


def _compile_state(
    state: State,
    all_states_by_name: Dict[str, State],
) -> Dict[str, Any]:
    """Compile a single State object into a JSON config dict entry.

    Args:
        state: The ``State`` to compile.
        all_states_by_name: Flat lookup of all states by name (for
            transition target resolution).

    Returns:
        A dict representing this state's config (the value side of
        ``"states": {"name": <this dict>}``).
    """
    config: Dict[str, Any] = {}

    # 📝 Type
    if state.final:
        config["type"] = "final"
    elif state.parallel:
        config["type"] = "parallel"

    # 📝 Entry / Exit actions
    if state.entry:
        config["entry"] = (
            state.entry[0] if len(state.entry) == 1 else state.entry
        )
    if state.exit:
        config["exit"] = (
            state.exit[0] if len(state.exit) == 1 else state.exit
        )

    # 📝 On (event transitions from State.on dict)
    if state.on:
        config["on"] = dict(state.on)

    # 📝 Always → compiled to "on": {"": ...}
    if state.always is not None:
        if "on" not in config:
            config["on"] = {}
        config["on"][""] = state.always

    # 📝 After (delayed transitions)
    if state.after:
        config["after"] = state.after

    # 📝 Invoke (services)
    if state.invoke:
        config["invoke"] = state.invoke

    # 📝 onDone (completion transition)
    if state.on_done is not None:
        if isinstance(state.on_done, str):
            config["onDone"] = {"target": state.on_done}
        else:
            config["onDone"] = state.on_done

    # 📝 Child states (recurse)
    if state.states:
        child_configs = {}
        initial_child = None
        child_names = set()
        for child in state.states:
            if child.name in child_names:
                raise InvalidConfigError(
                    f"Duplicate state name '{child.name}' "
                    f"at the same level"
                )
            child_names.add(child.name)
            child_configs[child.name] = _compile_state(
                child, all_states_by_name
            )
            if child.initial:
                if initial_child is not None:
                    raise InvalidConfigError(
                        f"Multiple initial states: "
                        f"{initial_child}, {child.name}. "
                        f"Exactly one allowed"
                    )
                initial_child = child.name
        config["states"] = child_configs
        if not state.parallel and initial_child:
            config["initial"] = initial_child
        elif not state.parallel and not initial_child and state.states:
            raise InvalidConfigError(
                "No initial state defined. Exactly one state "
                "must have initial=True"
            )

    return config


def _compile_config(
    machine_id: str,
    states: List[State],
    transitions: List[Union[Transition, TransitionGroup]],
    context: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Compile State and Transition objects into a JSON config dict.

    This is the shared compiler used by all three API styles.

    Args:
        machine_id: The machine's ID string.
        states: List of top-level ``State`` objects.
        transitions: List of ``Transition`` and/or ``TransitionGroup``
            objects.
        context: Optional initial context dict.

    Returns:
        A config dict compatible with ``create_machine()``.

    Raises:
        InvalidConfigError: On validation failures.
    """
    # 🔍 Build flat lookup of all states by name (including nested)
    all_states_by_name: Dict[str, State] = {}

    def _register_states(state_list: List[State]) -> None:
        for s in state_list:
            all_states_by_name[s.name] = s
            if s.states:
                _register_states(s.states)

    _register_states(states)

    # 🔍 Validate top-level: duplicates, initial
    top_names = set()
    initial_state = None
    has_parallel_root = (
        len(states) == 1 and states[0].parallel
    )

    for s in states:
        if s.name in top_names:
            raise InvalidConfigError(
                f"Duplicate state name '{s.name}' at the same level"
            )
        top_names.add(s.name)
        if s.initial:
            if initial_state is not None:
                raise InvalidConfigError(
                    f"Multiple initial states: "
                    f"{initial_state}, {s.name}. Exactly one allowed"
                )
            initial_state = s.name

    if not has_parallel_root and initial_state is None and len(states) > 0:
        raise InvalidConfigError(
            "No initial state defined. Exactly one state "
            "must have initial=True"
        )

    # 🔍 Flatten all transitions
    flat_transitions: List[Transition] = []
    for t in transitions:
        if isinstance(t, TransitionGroup):
            flat_transitions.extend(t.transitions)
        else:
            flat_transitions.append(t)

    # 🔍 Validate transition sources exist
    for t in flat_transitions:
        if t.source.name not in all_states_by_name:
            raise InvalidConfigError(
                f"Transition source '{t.source.name}' "
                f"is not a defined state"
            )

    # ⚙️ Compile each top-level state
    state_configs: Dict[str, Any] = {}
    for s in states:
        state_configs[s.name] = _compile_state(
            s, all_states_by_name
        )

    # ⚙️ Merge transitions into state configs
    # Group by (source_name, event)
    from collections import defaultdict

    trans_by_source_event: Dict[
        str, Dict[str, List[Transition]]
    ] = defaultdict(lambda: defaultdict(list))

    for t in flat_transitions:
        trans_by_source_event[t.source.name][t.event].append(t)

    def _merge_transitions_into(
        state_name: str, state_config: Dict[str, Any]
    ) -> None:
        if state_name in trans_by_source_event:
            if "on" not in state_config:
                state_config["on"] = {}
            for event, t_list in trans_by_source_event[
                state_name
            ].items():
                compiled = []
                for t in t_list:
                    entry: Dict[str, Any] = {}
                    if not t.internal and t.target is not None:
                        entry["target"] = t.target.name
                    if t.guard:
                        entry["guard"] = t.guard
                    if t.actions:
                        entry["actions"] = t.actions
                    if t.reenter:
                        entry["reenter"] = True
                    compiled.append(entry)
                if len(compiled) == 1:
                    state_config["on"][event] = compiled[0]
                else:
                    state_config["on"][event] = compiled
        # 📝 Recurse into child states
        if "states" in state_config:
            for child_name, child_config in state_config[
                "states"
            ].items():
                _merge_transitions_into(child_name, child_config)

    for sname, sconfig in state_configs.items():
        _merge_transitions_into(sname, sconfig)

    # ⚙️ Assemble top-level config
    result: Dict[str, Any] = {
        "id": machine_id,
        "states": state_configs,
    }
    if initial_state:
        result["initial"] = initial_state
    if context:
        result["context"] = context

    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_pythonic.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/xstate_statemachine/pythonic.py tests/test_pythonic.py
git commit -m "feat(pythonic): add _compile_config for State->JSON compilation"
```

---

### Task 5: `_compile_logic_from_functions` and `_compile_logic_from_instance`

**Files:**
- Modify: `src/xstate_statemachine/pythonic.py`
- Modify: `tests/test_pythonic.py`

- [ ] **Step 1: Write failing tests for logic compilation**

Append to `tests/test_pythonic.py`:

```python
from xstate_statemachine.pythonic import (
    _compile_logic_from_functions,
    _compile_logic_from_instance,
)
from xstate_statemachine import MachineLogic


class TestCompileLogic(unittest.TestCase):
    """Tests for logic compilation functions."""

    def test_compile_from_decorated_functions(self):
        @action
        def my_action(i, ctx, e, a):
            pass

        @guard
        def my_guard(ctx, e):
            return True

        @service
        def my_service(i, ctx, e):
            pass

        logic = _compile_logic_from_functions(
            actions=[my_action],
            guards=[my_guard],
            services=[my_service],
        )
        self.assertIsInstance(logic, MachineLogic)
        self.assertIn("myAction", logic.actions)
        self.assertIn("myGuard", logic.guards)
        self.assertIn("myService", logic.services)

    def test_compile_from_undecorated_functions(self):
        def increment_counter(i, ctx, e, a):
            pass

        logic = _compile_logic_from_functions(
            actions=[increment_counter], guards=[], services=[]
        )
        self.assertIn("incrementCounter", logic.actions)

    def test_compile_from_instance_binds_self(self):
        class MyLogic:
            def __init__(self):
                self.called = False

            @action
            def do_thing(self, i, ctx, e, a):
                self.called = True

        instance = MyLogic()
        decorated = [
            v
            for v in vars(MyLogic).values()
            if hasattr(v, "_xsm_type")
        ]
        logic = _compile_logic_from_instance(
            instance=instance, decorated=decorated
        )
        # ✅ The bound function should work without `self`
        bound_fn = logic.actions["doThing"]
        bound_fn(None, {}, None, None)
        self.assertTrue(instance.called)

    def test_compile_guard_from_instance(self):
        class MyLogic:
            @guard
            def is_ready(self, ctx, e):
                return True

        instance = MyLogic()
        decorated = [
            v
            for v in vars(MyLogic).values()
            if hasattr(v, "_xsm_type")
        ]
        logic = _compile_logic_from_instance(
            instance=instance, decorated=decorated
        )
        bound_fn = logic.guards["isReady"]
        self.assertTrue(bound_fn({}, None))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_pythonic.py::TestCompileLogic -v`
Expected: FAIL — `ImportError: cannot import name '_compile_logic_from_functions'`

- [ ] **Step 3: Write logic compilation implementations**

Append to `src/xstate_statemachine/pythonic.py`:

```python
# -------------------------------------------------------------------------
# ⚙️ Logic Compiler
# -------------------------------------------------------------------------


def _compile_logic_from_functions(
    actions: List[Callable],
    guards: List[Callable],
    services: List[Callable],
) -> MachineLogic:
    """Compile decorated/raw callables into a MachineLogic instance.

    For each function:
    - If it has ``_xsm_name``, use that as the registry key.
    - Otherwise, convert ``fn.__name__`` from snake_case to camelCase.

    Args:
        actions: List of action callables.
        guards: List of guard callables.
        services: List of service callables.

    Returns:
        A ``MachineLogic`` instance.
    """
    action_dict: Dict[str, Callable] = {}
    guard_dict: Dict[str, Callable] = {}
    service_dict: Dict[str, Callable] = {}

    for fn in actions:
        name = getattr(fn, "_xsm_name", _snake_to_camel(fn.__name__))
        action_dict[name] = fn
    for fn in guards:
        name = getattr(fn, "_xsm_name", _snake_to_camel(fn.__name__))
        guard_dict[name] = fn
    for fn in services:
        name = getattr(fn, "_xsm_name", _snake_to_camel(fn.__name__))
        service_dict[name] = fn

    return MachineLogic(
        actions=action_dict,
        guards=guard_dict,
        services=service_dict,
    )


def _compile_logic_from_instance(
    instance: object,
    decorated: List[Callable],
) -> MachineLogic:
    """Compile class instance methods into a MachineLogic instance.

    Uses ``functools.partial(method, instance)`` to bind ``self``, so the
    resulting callable matches the signatures expected by the interpreter:
    - Actions:  ``(interpreter, ctx, event, action_def) -> None``
    - Guards:   ``(ctx, event) -> bool``
    - Services: ``(interpreter, ctx, event) -> Any``

    Args:
        instance: The class instance whose methods to bind.
        decorated: List of unbound methods with ``_xsm_type`` markers.

    Returns:
        A ``MachineLogic`` instance with bound callables.
    """
    action_dict: Dict[str, Callable] = {}
    guard_dict: Dict[str, Callable] = {}
    service_dict: Dict[str, Callable] = {}

    for fn in decorated:
        name = fn._xsm_name
        xsm_type = fn._xsm_type
        bound = functools.partial(fn, instance)
        if xsm_type == "action":
            action_dict[name] = bound
        elif xsm_type == "guard":
            guard_dict[name] = bound
        elif xsm_type == "service":
            service_dict[name] = bound

    return MachineLogic(
        actions=action_dict,
        guards=guard_dict,
        services=service_dict,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_pythonic.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/xstate_statemachine/pythonic.py tests/test_pythonic.py
git commit -m "feat(pythonic): add logic compilers for functions and instances"
```

---

## Chunk 3: Public APIs — `build_machine`, `MachineBuilder`, `StateMachine`

### Task 6: `build_machine()` functional API

**Files:**
- Modify: `src/xstate_statemachine/pythonic.py`
- Modify: `tests/test_pythonic.py`

- [ ] **Step 1: Write failing tests for `build_machine`**

Append to `tests/test_pythonic.py`:

```python
from xstate_statemachine.pythonic import build_machine
from xstate_statemachine import SyncInterpreter


class TestBuildMachineFunctional(unittest.TestCase):
    """Tests for the build_machine() functional API."""

    def test_basic_functional(self):
        idle = State("idle", initial=True)
        running = State("running")
        t = idle.to(running, event="START")
        machine = build_machine(
            id="test", states=[idle, running], transitions=[t]
        )
        interp = SyncInterpreter(machine).start()
        self.assertIn("test.idle", interp.current_state_ids)
        interp.send("START")
        self.assertIn("test.running", interp.current_state_ids)
        interp.stop()

    def test_functional_with_decorated_actions(self):
        idle = State("idle", initial=True)
        active = State("active")
        result = {}

        @action
        def log_start(i, ctx, e, a):
            result["called"] = True

        t = idle.to(active, event="GO", actions=["logStart"])
        machine = build_machine(
            id="test",
            states=[idle, active],
            transitions=[t],
            actions=[log_start],
        )
        interp = SyncInterpreter(machine).start()
        interp.send("GO")
        interp.stop()
        self.assertTrue(result["called"])

    def test_functional_with_guards(self):
        idle = State("idle", initial=True)
        active = State("active")

        @guard
        def is_ready(ctx, e):
            return ctx.get("ready", False)

        t = idle.to(active, event="GO", guard="isReady")
        machine = build_machine(
            id="test",
            states=[idle, active],
            transitions=[t],
            guards=[is_ready],
            context={"ready": False},
        )
        interp = SyncInterpreter(machine).start()
        interp.send("GO")
        # ⚠️ Guard blocks — still in idle
        self.assertIn("test.idle", interp.current_state_ids)
        interp.stop()

    def test_functional_with_undecorated_functions(self):
        idle = State("idle", initial=True)
        active = State("active")
        result = {}

        def log_start(i, ctx, e, a):
            result["called"] = True

        t = idle.to(active, event="GO", actions=["logStart"])
        machine = build_machine(
            id="test",
            states=[idle, active],
            transitions=[t],
            actions=[log_start],
        )
        interp = SyncInterpreter(machine).start()
        interp.send("GO")
        interp.stop()
        self.assertTrue(result["called"])

    def test_functional_with_transition_group(self):
        a = State("a", initial=True)
        b = State("b")
        c = State("c")
        group = a.to(b, event="X") | b.to(c, event="X")
        machine = build_machine(
            id="test", states=[a, b, c], transitions=[group]
        )
        interp = SyncInterpreter(machine).start()
        interp.send("X")
        self.assertIn("test.b", interp.current_state_ids)
        interp.send("X")
        self.assertIn("test.c", interp.current_state_ids)
        interp.stop()

    def test_functional_context(self):
        idle = State("idle", initial=True)
        machine = build_machine(
            id="test",
            states=[idle],
            context={"count": 42},
        )
        interp = SyncInterpreter(machine).start()
        self.assertEqual(interp.context["count"], 42)
        interp.stop()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_pythonic.py::TestBuildMachineFunctional -v`
Expected: FAIL — `ImportError: cannot import name 'build_machine'`

- [ ] **Step 3: Write `build_machine` implementation**

Append to `src/xstate_statemachine/pythonic.py`:

```python
# -------------------------------------------------------------------------
# 🏗️ Functional API: build_machine()
# -------------------------------------------------------------------------


def build_machine(
    *,
    id: str,
    states: List[State],
    transitions: Optional[
        List[Union[Transition, TransitionGroup]]
    ] = None,
    actions: Optional[List[Callable]] = None,
    guards: Optional[List[Callable]] = None,
    services: Optional[List[Callable]] = None,
    context: Optional[Dict] = None,
) -> "MachineNode":
    """Build a state machine from Python objects (functional API).

    This is the simplest API style — define ``State`` objects and
    ``Transition`` objects at module level, then call this function.

    Args:
        id: Machine ID string.
        states: List of ``State`` objects.
        transitions: Optional list of ``Transition`` / ``TransitionGroup``.
        actions: Optional list of action callables (decorated or plain).
        guards: Optional list of guard callables (decorated or plain).
        services: Optional list of service callables (decorated or plain).
        context: Optional initial context dict.

    Returns:
        A ``MachineNode`` ready for use with ``Interpreter`` or
        ``SyncInterpreter``.
    """
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
    return _original_create_machine(config, logic=logic)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_pythonic.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/xstate_statemachine/pythonic.py tests/test_pythonic.py
git commit -m "feat(pythonic): add build_machine() functional API"
```

---

### Task 7: `MachineBuilder` fluent API

**Files:**
- Modify: `src/xstate_statemachine/pythonic.py`
- Modify: `tests/test_pythonic.py`

- [ ] **Step 1: Write failing tests for MachineBuilder**

Append to `tests/test_pythonic.py`:

```python
from xstate_statemachine.pythonic import MachineBuilder


class TestMachineBuilder(unittest.TestCase):
    """Tests for MachineBuilder fluent API."""

    def test_basic_builder(self):
        machine = (
            MachineBuilder("test")
            .state("idle", initial=True)
            .state("running")
            .transition("idle", "START", "running")
            .build()
        )
        interp = SyncInterpreter(machine).start()
        self.assertIn("test.idle", interp.current_state_ids)
        interp.send("START")
        self.assertIn("test.running", interp.current_state_ids)
        interp.stop()

    def test_builder_with_logic(self):
        result = {}
        machine = (
            MachineBuilder("test")
            .state("idle", initial=True)
            .state("active")
            .transition(
                "idle", "GO", "active", actions=["logIt"]
            )
            .action(
                "logIt", lambda i, ctx, e, a: result.update({"ok": True})
            )
            .build()
        )
        interp = SyncInterpreter(machine).start()
        interp.send("GO")
        interp.stop()
        self.assertTrue(result["ok"])

    def test_builder_context(self):
        machine = (
            MachineBuilder("test")
            .context({"x": 1})
            .state("idle", initial=True)
            .build()
        )
        interp = SyncInterpreter(machine).start()
        self.assertEqual(interp.context["x"], 1)
        interp.stop()

    def test_builder_context_override(self):
        machine = (
            MachineBuilder("test")
            .context({"x": 1})
            .state("idle", initial=True)
            .build(context={"x": 99})
        )
        interp = SyncInterpreter(machine).start()
        self.assertEqual(interp.context["x"], 99)
        interp.stop()

    def test_builder_guard(self):
        machine = (
            MachineBuilder("test")
            .state("idle", initial=True)
            .state("active")
            .transition(
                "idle", "GO", "active", guard="isOk"
            )
            .guard("isOk", lambda ctx, e: False)
            .build()
        )
        interp = SyncInterpreter(machine).start()
        interp.send("GO")
        self.assertIn("test.idle", interp.current_state_ids)
        interp.stop()

    def test_builder_child_states(self):
        machine = (
            MachineBuilder("test")
            .state("idle", initial=True)
            .state("moving")
            .child_states(
                "moving", initial="up", states={"up": {}, "down": {}}
            )
            .transition("idle", "GO", "moving")
            .build()
        )
        interp = SyncInterpreter(machine).start()
        interp.send("GO")
        self.assertIn(
            "test.moving.up", interp.current_state_ids
        )
        interp.stop()

    def test_builder_child_states_unknown_parent_raises(self):
        builder = MachineBuilder("test").state("idle", initial=True)
        with self.assertRaises(InvalidConfigError):
            builder.child_states(
                "nonexistent", initial="x", states={"x": {}}
            )

    def test_builder_final_state(self):
        machine = (
            MachineBuilder("test")
            .state("idle", initial=True)
            .state("done", final=True)
            .transition("idle", "FINISH", "done")
            .build()
        )
        interp = SyncInterpreter(machine).start()
        interp.send("FINISH")
        self.assertIn("test.done", interp.current_state_ids)
        interp.stop()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_pythonic.py::TestMachineBuilder -v`
Expected: FAIL — `ImportError: cannot import name 'MachineBuilder'`

- [ ] **Step 3: Write `MachineBuilder` implementation**

Append to `src/xstate_statemachine/pythonic.py`:

```python
# -------------------------------------------------------------------------
# 🏗️ Builder API: MachineBuilder
# -------------------------------------------------------------------------


class MachineBuilder:
    """Fluent builder for constructing state machines programmatically.

    Example::

        machine = (
            MachineBuilder("myMachine")
            .context({"count": 0})
            .state("idle", initial=True)
            .state("running")
            .transition("idle", "START", "running")
            .action("logIt", my_action_fn)
            .build()
        )

    Args:
        machine_id: The machine's ID string.
    """

    def __init__(self, machine_id: str) -> None:
        self._machine_id = machine_id
        self._context: Optional[Dict] = None
        self._states: Dict[str, Dict[str, Any]] = {}
        self._initial_state: Optional[str] = None
        self._transitions: List[Dict[str, Any]] = []
        self._actions: Dict[str, Callable] = {}
        self._guards: Dict[str, Callable] = {}
        self._services: Dict[str, Callable] = {}

    def context(self, ctx: Dict) -> "MachineBuilder":
        """Set the initial context."""
        self._context = ctx
        return self

    def state(
        self,
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
    ) -> "MachineBuilder":
        """Add a state to the machine."""
        if final and parallel:
            raise InvalidConfigError(
                f"State '{name}' cannot be both final and parallel"
            )
        config: Dict[str, Any] = {}
        if final:
            config["type"] = "final"
        if parallel:
            config["type"] = "parallel"
        if on:
            config["on"] = on
        if entry:
            config["entry"] = entry
        if exit:
            config["exit"] = exit
        if after:
            config["after"] = after
        if invoke:
            config["invoke"] = invoke
        if on_done is not None:
            if isinstance(on_done, str):
                config["onDone"] = {"target": on_done}
            else:
                config["onDone"] = on_done
        if always is not None:
            if "on" not in config:
                config["on"] = {}
            config["on"][""] = always
        if initial:
            self._initial_state = name
        self._states[name] = config
        return self

    def transition(
        self,
        source: str,
        event: str,
        target: str,
        *,
        guard: Optional[str] = None,
        actions: Optional[List[str]] = None,
        reenter: bool = False,
        internal: bool = False,
    ) -> "MachineBuilder":
        """Add a transition between states."""
        self._transitions.append(
            {
                "source": source,
                "event": event,
                "target": target,
                "guard": guard,
                "actions": actions,
                "reenter": reenter,
                "internal": internal,
            }
        )
        return self

    def child_states(
        self,
        parent: str,
        *,
        initial: Optional[str] = None,
        states: Optional[Dict[str, Dict]] = None,
        parallel: bool = False,
    ) -> "MachineBuilder":
        """Add child states to an existing state."""
        if parent not in self._states:
            raise InvalidConfigError(
                f"Parent state '{parent}' not found. "
                f"Add it with .state() first"
            )
        parent_config = self._states[parent]
        if parallel:
            parent_config["type"] = "parallel"
        if states:
            parent_config["states"] = states
        if initial and not parallel:
            parent_config["initial"] = initial
        return self

    def action(
        self, name: str, fn: Callable
    ) -> "MachineBuilder":
        """Register an action function."""
        reg_name = getattr(fn, "_xsm_name", name)
        self._actions[reg_name] = fn
        return self

    def guard(
        self, name: str, fn: Callable
    ) -> "MachineBuilder":
        """Register a guard function."""
        reg_name = getattr(fn, "_xsm_name", name)
        self._guards[reg_name] = fn
        return self

    def service(
        self, name: str, fn: Callable
    ) -> "MachineBuilder":
        """Register a service function."""
        reg_name = getattr(fn, "_xsm_name", name)
        self._services[reg_name] = fn
        return self

    def build(
        self, context: Optional[Dict] = None
    ) -> "MachineNode":
        """Build and return the MachineNode.

        Args:
            context: Optional context override.

        Returns:
            A ``MachineNode`` ready for interpreter use.
        """
        # ⚙️ Merge transitions into state configs
        for t in self._transitions:
            source = t["source"]
            if source not in self._states:
                raise InvalidConfigError(
                    f"Transition source '{source}' "
                    f"is not a defined state"
                )
            state_config = self._states[source]
            if "on" not in state_config:
                state_config["on"] = {}
            entry: Dict[str, Any] = {}
            if not t["internal"]:
                entry["target"] = t["target"]
            if t["guard"]:
                entry["guard"] = t["guard"]
            if t["actions"]:
                entry["actions"] = t["actions"]
            if t["reenter"]:
                entry["reenter"] = True
            event = t["event"]
            if event in state_config["on"]:
                existing = state_config["on"][event]
                if isinstance(existing, list):
                    existing.append(entry)
                else:
                    state_config["on"][event] = [existing, entry]
            else:
                state_config["on"][event] = entry

        config: Dict[str, Any] = {
            "id": self._machine_id,
            "states": self._states,
        }
        if self._initial_state:
            config["initial"] = self._initial_state
        ctx = context or self._context
        if ctx:
            config["context"] = ctx

        logic = MachineLogic(
            actions=self._actions,
            guards=self._guards,
            services=self._services,
        )
        return _original_create_machine(config, logic=logic)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_pythonic.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/xstate_statemachine/pythonic.py tests/test_pythonic.py
git commit -m "feat(pythonic): add MachineBuilder fluent API"
```

---

### Task 8: `StateMachine` class-based API with metaclass

**Files:**
- Modify: `src/xstate_statemachine/pythonic.py`
- Modify: `tests/test_pythonic.py`

- [ ] **Step 1: Write failing tests for StateMachine**

Append to `tests/test_pythonic.py`:

```python
from xstate_statemachine.pythonic import StateMachine


class TestStateMachineClassBased(unittest.TestCase):
    """Tests for the StateMachine class-based API."""

    def test_basic_machine_creation(self):
        class Light(StateMachine):
            off = State(initial=True)
            on = State()
            toggle = off.to(on, event="TOGGLE") | on.to(
                off, event="TOGGLE"
            )

        machine = Light.create_machine()
        interp = SyncInterpreter(machine).start()
        self.assertIn("Light.off", interp.current_state_ids)
        interp.send("TOGGLE")
        self.assertIn("Light.on", interp.current_state_ids)
        interp.send("TOGGLE")
        self.assertIn("Light.off", interp.current_state_ids)
        interp.stop()

    def test_custom_machine_id(self):
        class Light(StateMachine):
            machine_id = "myLight"
            off = State(initial=True)
            on = State()

        machine = Light.create_machine()
        interp = SyncInterpreter(machine).start()
        self.assertIn("myLight.off", interp.current_state_ids)
        interp.stop()

    def test_actions_fire(self):
        result = {}

        class Counter(StateMachine):
            idle = State(initial=True)
            done = State()
            go = idle.to(done, event="GO", actions=["logIt"])

            @action
            def log_it(self, i, ctx, e, a):
                result["fired"] = True

        machine = Counter.create_machine()
        interp = SyncInterpreter(machine).start()
        interp.send("GO")
        interp.stop()
        self.assertTrue(result["fired"])

    def test_guards_block(self):
        class Gated(StateMachine):
            idle = State(initial=True)
            active = State()
            go = idle.to(
                active, event="GO", guard="isReady"
            )

            @guard
            def is_ready(self, ctx, e):
                return ctx.get("ready", False)

        machine = Gated.create_machine(context={"ready": False})
        interp = SyncInterpreter(machine).start()
        interp.send("GO")
        self.assertIn("Gated.idle", interp.current_state_ids)
        interp.stop()

    def test_context_override(self):
        class WithCtx(StateMachine):
            initial_context = {"x": 1}
            idle = State(initial=True)

        machine = WithCtx.create_machine(context={"x": 99})
        interp = SyncInterpreter(machine).start()
        self.assertEqual(interp.context["x"], 99)
        interp.stop()

    def test_state_names_auto_inferred(self):
        class M(StateMachine):
            my_state = State(initial=True)

        machine = M.create_machine()
        interp = SyncInterpreter(machine).start()
        self.assertIn("M.my_state", interp.current_state_ids)
        interp.stop()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_pythonic.py::TestStateMachineClassBased -v`
Expected: FAIL — `ImportError: cannot import name 'StateMachine'`

- [ ] **Step 3: Write `_StateMachineMeta` and `StateMachine` implementation**

Append to `src/xstate_statemachine/pythonic.py`:

```python
# -------------------------------------------------------------------------
# 🏗️ Class-Based API: StateMachine + Metaclass
# -------------------------------------------------------------------------


class _StateMachineMeta(type):
    """Metaclass for ``StateMachine`` that collects States, Transitions,
    and decorated methods at class-definition time.
    """

    def __new__(mcs, name, bases, namespace):
        # 📝 Skip processing for the base StateMachine class itself
        if name == "StateMachine" and not any(
            hasattr(b, "_xsm_is_base") for b in bases
        ):
            cls = super().__new__(mcs, name, bases, namespace)
            cls._xsm_is_base = True
            return cls

        states: List[State] = []
        transitions: List[Union[Transition, TransitionGroup]] = []
        decorated: List[Callable] = []

        for attr_name, attr_value in list(namespace.items()):
            if attr_name.startswith("_"):
                continue

            # 📝 Collect nested State subclasses
            if (
                isinstance(attr_value, type)
                and issubclass(attr_value, State)
                and attr_value is not State
            ):
                child_states = []
                for (
                    child_attr_name,
                    child_attr_value,
                ) in vars(attr_value).items():
                    if child_attr_name.startswith("_"):
                        continue
                    if isinstance(child_attr_value, State):
                        if not child_attr_value.name:
                            child_attr_value.name = child_attr_name
                        child_states.append(child_attr_value)
                state_obj = State(
                    name=attr_name,
                    initial=getattr(
                        attr_value, "_xsm_initial", False
                    ),
                    final=getattr(
                        attr_value, "_xsm_final", False
                    ),
                    parallel=getattr(
                        attr_value, "_xsm_parallel", False
                    ),
                    states=child_states if child_states else None,
                )
                states.append(state_obj)
                # 📝 Keep the class in namespace so transition
                # expressions like moving.up still work
                continue

            # 📝 Collect State instances
            if isinstance(attr_value, State):
                if not attr_value.name:
                    attr_value.name = attr_name
                states.append(attr_value)
                continue

            # 📝 Collect Transitions / TransitionGroups
            if isinstance(
                attr_value, (Transition, TransitionGroup)
            ):
                transitions.append(attr_value)
                continue

            # 📝 Collect decorated methods
            if callable(attr_value) and hasattr(
                attr_value, "_xsm_type"
            ):
                decorated.append(attr_value)

        cls = super().__new__(mcs, name, bases, namespace)
        cls._xsm_states = states
        cls._xsm_transitions = transitions
        cls._xsm_decorated = decorated
        return cls


class StateMachine(metaclass=_StateMachineMeta):
    """Base class for defining state machines using class syntax.

    Subclass this and define ``State`` attributes, transitions,
    and decorated action/guard/service methods.

    Class Attributes:
        machine_id: Optional machine ID (defaults to class name).
        initial_context: Optional initial context dict.

    Example::

        class Light(StateMachine):
            off = State(initial=True)
            on = State()
            toggle = off.to(on, event="TOGGLE") | on.to(off, event="TOGGLE")

        machine = Light.create_machine()
    """

    machine_id: Optional[str] = None
    initial_context: Optional[Dict] = None

    @classmethod
    def create_machine(cls, context=None):
        """Create a ``MachineNode`` from this class definition.

        Args:
            context: Optional context override.

        Returns:
            A ``MachineNode`` ready for interpreter use.
        """
        mid = cls.machine_id or cls.__name__
        ctx = context or cls.initial_context

        config = _compile_config(
            machine_id=mid,
            states=cls._xsm_states,
            transitions=cls._xsm_transitions,
            context=ctx,
        )

        instance = cls()
        logic = _compile_logic_from_instance(
            instance=instance,
            decorated=cls._xsm_decorated,
        )

        return _original_create_machine(config, logic=logic)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_pythonic.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/xstate_statemachine/pythonic.py tests/test_pythonic.py
git commit -m "feat(pythonic): add StateMachine class-based API with metaclass"
```

---

## Chunk 4: Exports, Backward Compatibility, and Documentation

### Task 9: Wire up `__init__.py` exports

**Files:**
- Modify: `src/xstate_statemachine/__init__.py`

- [ ] **Step 1: Add imports and exports**

Add the following imports and `__all__` entries to `src/xstate_statemachine/__init__.py`:

After the existing project-specific imports block, add:

```python
# -------------------------------------------------------------------------
# 🐍 Pythonic API
# -------------------------------------------------------------------------
from .pythonic import (
    State,
    StateMachine,
    MachineBuilder,
    build_machine,
    transition,
    action,
    guard,
    service,
)
```

Add to `__all__`:

```python
    # 🐍 Pythonic API
    "State",
    "StateMachine",
    "MachineBuilder",
    "build_machine",
    "transition",
    "action",
    "guard",
    "service",
```

- [ ] **Step 2: Run import test**

Run: `uv run python -c "from xstate_statemachine import State, StateMachine, MachineBuilder, build_machine, transition, action, guard, service; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/xstate_statemachine/__init__.py
git commit -m "feat(pythonic): export Pythonic API from __init__.py"
```

---

### Task 10: Backward compatibility tests

**Files:**
- Modify: `tests/test_pythonic.py`

- [ ] **Step 1: Write backward compatibility tests**

Append to `tests/test_pythonic.py`:

```python
from xstate_statemachine import (
    create_machine,
    SyncInterpreter,
    MachineLogic,
    PluginBase,
)


class TestBackwardCompatibility(unittest.TestCase):
    """Verify existing JSON API still works unchanged."""

    def test_json_api_still_works(self):
        config = {
            "id": "test",
            "initial": "idle",
            "states": {
                "idle": {"on": {"GO": "running"}},
                "running": {"type": "final"},
            },
        }
        machine = create_machine(config)
        interp = SyncInterpreter(machine).start()
        self.assertIn("test.idle", interp.current_state_ids)
        interp.send("GO")
        self.assertIn("test.running", interp.current_state_ids)
        interp.stop()

    def test_pythonic_works_with_plugins(self):
        events_seen = []

        class TestPlugin(PluginBase):
            def on_transition(self, interp, frm, to, t):
                events_seen.append("transition")

        idle = State("idle", initial=True)
        active = State("active")
        t = idle.to(active, event="GO")
        machine = build_machine(
            id="test",
            states=[idle, active],
            transitions=[t],
        )
        interp = SyncInterpreter(machine)
        interp.use(TestPlugin())
        interp.start()
        interp.send("GO")
        interp.stop()
        self.assertIn("transition", events_seen)

    def test_all_existing_tests_still_pass(self):
        """Meta-test: existing test suite must not be broken.

        This is verified by running the full test suite, not by
        this individual test. This test just documents the intent.
        """
        pass
```

- [ ] **Step 2: Run all tests (existing + new)**

Run: `uv run pytest -v`
Expected: All tests PASS (both existing 461 and new pythonic tests)

- [ ] **Step 3: Commit**

```bash
git add tests/test_pythonic.py
git commit -m "test(pythonic): add backward compatibility tests"
```

---

### Task 11: Run pre-commit and full test suite

**Files:** None (validation only)

- [ ] **Step 1: Run pre-commit on all files**

Run: `uv run pre-commit run --all-files`
Expected: All hooks PASS

- [ ] **Step 2: Fix any formatting issues and re-run**

If Black or Flake8 report issues, fix them and re-run.

- [ ] **Step 3: Run full test suite with coverage**

Run: `uv run pytest --cov=src/xstate_statemachine -v`
Expected: All tests PASS, coverage includes `pythonic.py`

- [ ] **Step 4: Commit any formatting fixes**

```bash
git add -u
git commit -m "style: fix formatting in pythonic API code"
```

---

### Task 12: Update CHANGELOG.md

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Add changelog entry**

Add under `## [Unreleased]` (create if missing):

```markdown
### Added
- **Pythonic API** for defining state machines in pure Python without JSON dicts:
  - `StateMachine` base class with metaclass for class-based declarations
  - `MachineBuilder` fluent builder for programmatic/dynamic construction
  - `build_machine()` function for functional-style machine definition
  - `State` class for defining states with all features (hierarchy, parallel, final, after, invoke, always, onDone)
  - `Transition` and `TransitionGroup` for fluent transition definitions with `|` combinator
  - `@action`, `@guard`, `@service` decorators with auto snake_case-to-camelCase naming
  - `transition()` standalone function for functional API
  - Full backward compatibility — all existing JSON-based APIs work unchanged
```

- [ ] **Step 2: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: add Pythonic API entry to CHANGELOG"
```

---

### Task 13: Final validation

**Files:** None (validation only)

- [ ] **Step 1: Run full test suite one final time**

Run: `uv run pytest -v`
Expected: ALL tests pass (existing + new)

- [ ] **Step 2: Run pre-commit one final time**

Run: `uv run pre-commit run --all-files`
Expected: All hooks PASS

- [ ] **Step 3: Verify git status is clean**

Run: `git status`
Expected: Clean working tree, all changes committed
