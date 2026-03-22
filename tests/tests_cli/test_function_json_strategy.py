# tests/tests_cli/test_function_json_strategy.py
"""Tests for the FunctionJsonStrategy."""

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

# Same richer config used in Task 5 (traffic light with actions, guards, services)
FUNCTION_JSON_TEST_CONFIG = {
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


class TestFunctionJsonStrategy(unittest.TestCase):
    """Tests for function-json code generation via strategy."""

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
            configs=[FUNCTION_JSON_TEST_CONFIG],
            json_filenames=["traffic_light.json"],
            hierarchy=False,
            sleep=True,
            sleep_time=2,
            loader=True,
            style="function",
        )
        defaults.update(overrides)
        return GenerationContext(**defaults)

    # -----------------------------------------------------------------
    # Logic: No class wrapper
    # -----------------------------------------------------------------

    def test_logic_no_class_wrapper(self) -> None:
        """Generated logic must NOT contain a class definition for the logic provider."""
        s = get_strategy("function-json")
        ctx = self._make_ctx()
        code = s.generate_logic(ctx)
        # The logic file should not wrap functions in a class
        self.assertNotIn("class TrafficLightLogic:", code)
        self.assertNotIn("class TrafficLightLogic(", code)

    # -----------------------------------------------------------------
    # Logic: No self parameter
    # -----------------------------------------------------------------

    def test_logic_no_self_parameter(self) -> None:
        """Module-level functions must not have a self parameter."""
        s = get_strategy("function-json")
        ctx = self._make_ctx()
        code = s.generate_logic(ctx)
        self.assertNotIn("self,", code)
        self.assertNotIn("self)", code)

    # -----------------------------------------------------------------
    # Logic: Function-level action stubs
    # -----------------------------------------------------------------

    def test_logic_contains_action_stubs(self) -> None:
        """Generated logic has module-level function stubs for actions."""
        s = get_strategy("function-json")
        ctx = self._make_ctx()
        code = s.generate_logic(ctx)
        self.assertIn("def log_enter(", code)
        self.assertIn("def increment(", code)

    # -----------------------------------------------------------------
    # Logic: Guard stubs with -> bool
    # -----------------------------------------------------------------

    def test_logic_contains_guard_stubs(self) -> None:
        """Generated logic has guard function stubs returning bool."""
        s = get_strategy("function-json")
        ctx = self._make_ctx()
        code = s.generate_logic(ctx)
        self.assertIn("def is_ready(", code)
        self.assertIn("-> bool:", code)

    # -----------------------------------------------------------------
    # Logic: Rich docstrings with Args
    # -----------------------------------------------------------------

    def test_logic_contains_rich_docstrings(self) -> None:
        """Generated logic has rich docstrings with Args sections."""
        s = get_strategy("function-json")
        ctx = self._make_ctx()
        code = s.generate_logic(ctx)
        self.assertIn("Args:", code)
        self.assertIn("interpreter:", code)

    # -----------------------------------------------------------------
    # Logic: Error handling
    # -----------------------------------------------------------------

    def test_logic_contains_error_handling(self) -> None:
        """Generated logic wraps actions/services in try/except."""
        s = get_strategy("function-json")
        ctx = self._make_ctx()
        code = s.generate_logic(ctx)
        self.assertIn("try:", code)
        self.assertIn("except Exception:", code)
        self.assertIn("logger.exception", code)

    # -----------------------------------------------------------------
    # Logic: No noqa comments
    # -----------------------------------------------------------------

    def test_logic_no_noqa_comments(self) -> None:
        """Generated logic must not contain noqa comments."""
        s = get_strategy("function-json")
        ctx = self._make_ctx()
        code = s.generate_logic(ctx)
        self.assertNotIn("# noqa", code)

    # -----------------------------------------------------------------
    # Logic: Async actions return -> None
    # -----------------------------------------------------------------

    def test_logic_async_return_type_is_none(self) -> None:
        """Async actions return None, not Awaitable[None]."""
        s = get_strategy("function-json")
        ctx = self._make_ctx(is_async=True)
        code = s.generate_logic(ctx)
        self.assertIn("async def log_enter(", code)
        self.assertNotIn("Awaitable[None]", code)
        self.assertIn("-> None:", code)

    # -----------------------------------------------------------------
    # Logic: Service alias
    # -----------------------------------------------------------------

    def test_logic_service_has_alias(self) -> None:
        """Services with camelCase names get a snake_case alias."""
        s = get_strategy("function-json")
        ctx = self._make_ctx()
        code = s.generate_logic(ctx)
        self.assertIn("fetchData = fetch_data", code)
        self.assertIn("# alias for JSON name", code)

    # -----------------------------------------------------------------
    # Runner: Creates interpreter correctly
    # -----------------------------------------------------------------

    def test_runner_contains_interpreter(self) -> None:
        """Generated runner creates an interpreter."""
        s = get_strategy("function-json")
        ctx = self._make_ctx()
        code = s.generate_runner(ctx)
        self.assertIn("Interpreter(machine)", code)
        self.assertIn("interpreter.start()", code)

    # -----------------------------------------------------------------
    # Runner: Sync mode uses SyncInterpreter
    # -----------------------------------------------------------------

    def test_runner_sync_mode(self) -> None:
        """Sync runner uses SyncInterpreter."""
        s = get_strategy("function-json")
        ctx = self._make_ctx(is_async=False)
        code = s.generate_runner(ctx)
        self.assertIn("SyncInterpreter(machine)", code)

    # -----------------------------------------------------------------
    # Runner: logic_modules binding
    # -----------------------------------------------------------------

    def test_runner_uses_logic_modules_binding(self) -> None:
        """Runner uses logic_modules=[module] instead of logic_providers."""
        s = get_strategy("function-json")
        ctx = self._make_ctx(file_count=2)
        code = s.generate_runner(ctx)
        self.assertIn("logic_modules=", code)
        self.assertNotIn("logic_providers=", code)

    # -----------------------------------------------------------------
    # Runner: file_count=2 imports module
    # -----------------------------------------------------------------

    def test_runner_file_count_2_imports_module(self) -> None:
        """With file_count=2, runner imports logic file as a module."""
        s = get_strategy("function-json")
        ctx = self._make_ctx(file_count=2)
        code = s.generate_runner(ctx)
        self.assertIn("import traffic_light_logic", code)
        # Should NOT use class-style import
        self.assertNotIn("from traffic_light_logic import", code)

    # -----------------------------------------------------------------
    # Runner: file_count=1 uses sys.modules
    # -----------------------------------------------------------------

    def test_runner_file_count_1_uses_sys_modules(self) -> None:
        """With file_count=1, runner uses sys.modules[__name__]."""
        s = get_strategy("function-json")
        ctx = self._make_ctx(file_count=1)
        code = s.generate_runner(ctx)
        self.assertIn("import sys", code)
        self.assertIn("sys.modules[__name__]", code)

    # -----------------------------------------------------------------
    # Strategy name
    # -----------------------------------------------------------------

    def test_strategy_name(self) -> None:
        """Strategy name is 'function-json'."""
        s = get_strategy("function-json")
        self.assertEqual(s.name, "function-json")
