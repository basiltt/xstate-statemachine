# tests/tests_cli/test_pythonic_builder_strategy.py
"""Tests for PythonicBuilderStrategy."""

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


class TestPythonicBuilderStrategy(unittest.TestCase):
    """Tests for pythonic-builder code generation."""

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

    def test_logic_contains_machine_builder(self) -> None:
        """Generated logic uses MachineBuilder fluent API."""
        s = get_strategy("pythonic-builder")
        code = s.generate_logic(self._make_ctx())
        self.assertIn('MachineBuilder("trafficLight")', code)

    def test_logic_contains_fluent_state_calls(self) -> None:
        """Generated logic has fluent .state() calls."""
        s = get_strategy("pythonic-builder")
        code = s.generate_logic(self._make_ctx())
        self.assertIn('.state("green"', code)
        self.assertIn("initial=True", code)
        self.assertIn('.state("yellow")', code)

    def test_logic_contains_transition_calls(self) -> None:
        """Generated logic has .transition() calls."""
        s = get_strategy("pythonic-builder")
        code = s.generate_logic(self._make_ctx())
        self.assertIn('.transition("green", "TIMER", "yellow"', code)

    def test_logic_contains_action_registration(self) -> None:
        """Generated logic registers actions on the builder."""
        s = get_strategy("pythonic-builder")
        code = s.generate_logic(self._make_ctx())
        self.assertIn('.action("logEnter", log_enter)', code)
        self.assertIn('.action("increment", increment)', code)

    def test_logic_contains_guard_registration(self) -> None:
        """Generated logic registers guards on the builder."""
        s = get_strategy("pythonic-builder")
        code = s.generate_logic(self._make_ctx())
        self.assertIn('.guard("isReady", is_ready)', code)

    def test_logic_contains_service_registration(self) -> None:
        """Generated logic registers services on the builder."""
        s = get_strategy("pythonic-builder")
        code = s.generate_logic(self._make_ctx())
        self.assertIn('.service("fetchData", fetch_data)', code)

    def test_logic_contains_build_call(self) -> None:
        """Generated logic calls .build() on the builder chain."""
        s = get_strategy("pythonic-builder")
        code = s.generate_logic(self._make_ctx())
        self.assertIn(".build()", code)

    def test_logic_has_decorated_functions(self) -> None:
        """Generated logic has module-level decorated functions (no self)."""
        s = get_strategy("pythonic-builder")
        code = s.generate_logic(self._make_ctx())
        self.assertIn("@action", code)
        self.assertIn("@guard", code)
        self.assertIn("@service", code)
        # Module-level functions — no self parameter
        self.assertNotIn("self,", code)

    def test_logic_imports_machine_builder(self) -> None:
        """Generated logic imports MachineBuilder."""
        s = get_strategy("pythonic-builder")
        code = s.generate_logic(self._make_ctx())
        self.assertIn("MachineBuilder", code)

    def test_runner_calls_build(self) -> None:
        """Runner calls build() and uses SyncInterpreter."""
        s = get_strategy("pythonic-builder")
        code = s.generate_runner(self._make_ctx())
        self.assertIn("build()", code)
        self.assertIn("SyncInterpreter(machine)", code)

    def test_logic_contains_rich_docstrings(self) -> None:
        """Generated logic has Args section in docstrings."""
        s = get_strategy("pythonic-builder")
        code = s.generate_logic(self._make_ctx())
        self.assertIn("Args:", code)

    def test_logic_contains_error_handling(self) -> None:
        """Generated logic has try/except error handling."""
        s = get_strategy("pythonic-builder")
        code = s.generate_logic(self._make_ctx())
        self.assertIn("try:", code)
        self.assertIn("except Exception:", code)

    def test_runner_async_mode(self) -> None:
        """Async runner uses Interpreter and asyncio."""
        s = get_strategy("pythonic-builder")
        ctx = self._make_ctx(is_async=True)
        code = s.generate_runner(ctx)
        self.assertIn("Interpreter(machine)", code)
        self.assertIn("asyncio.run(main())", code)
        self.assertIn("await ", code)

    def test_runner_has_main_guard(self) -> None:
        """Runner has if __name__ == '__main__' block."""
        s = get_strategy("pythonic-builder")
        code = s.generate_runner(self._make_ctx())
        self.assertIn('if __name__ == "__main__":', code)

    def test_runner_sends_events(self) -> None:
        """Runner simulates events from the config."""
        s = get_strategy("pythonic-builder")
        code = s.generate_runner(self._make_ctx())
        self.assertIn('send("TIMER")', code)
