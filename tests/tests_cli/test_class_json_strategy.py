# tests/tests_cli/test_class_json_strategy.py
"""Tests for the ClassJsonStrategy."""

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
