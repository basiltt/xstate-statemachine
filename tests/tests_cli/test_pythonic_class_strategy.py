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

    def test_logic_contains_statemachine_subclass(self) -> None:
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
        self.assertIn("TrafficLightMachine.create_machine()", code)

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
