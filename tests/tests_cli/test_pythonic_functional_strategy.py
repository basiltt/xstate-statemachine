# tests/tests_cli/test_pythonic_functional_strategy.py
"""Tests for PythonicFunctionalStrategy."""

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


class TestPythonicFunctionalStrategy(unittest.TestCase):
    """Tests for pythonic-functional code generation."""

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

    def test_logic_contains_state_objects(self) -> None:
        """Generated logic creates State objects with name as first arg."""
        s = get_strategy("pythonic-functional")
        code = s.generate_logic(self._make_ctx())
        self.assertIn("green = State(", code)
        self.assertIn('"green"', code)
        self.assertIn("initial=True", code)

    def test_logic_contains_to_transitions(self) -> None:
        """Generated logic uses .to() calls on state objects."""
        s = get_strategy("pythonic-functional")
        code = s.generate_logic(self._make_ctx())
        self.assertIn("green.to(yellow", code)

    def test_logic_contains_build_machine_call(self) -> None:
        """Generated logic calls build_machine() with correct args."""
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
        """Generated logic imports build_machine."""
        s = get_strategy("pythonic-functional")
        code = s.generate_logic(self._make_ctx())
        self.assertIn("build_machine", code)

    def test_logic_has_decorated_functions(self) -> None:
        """Generated logic has module-level decorated functions."""
        s = get_strategy("pythonic-functional")
        code = s.generate_logic(self._make_ctx())
        self.assertIn("@action", code)
        self.assertIn("@guard", code)
        self.assertIn("@service", code)

    def test_logic_contains_rich_docstrings(self) -> None:
        """Generated logic has Args section in docstrings."""
        s = get_strategy("pythonic-functional")
        code = s.generate_logic(self._make_ctx())
        self.assertIn("Args:", code)

    def test_logic_contains_error_handling(self) -> None:
        """Generated logic has try/except error handling."""
        s = get_strategy("pythonic-functional")
        code = s.generate_logic(self._make_ctx())
        self.assertIn("try:", code)
        self.assertIn("except Exception:", code)

    def test_logic_no_self_parameter(self) -> None:
        """Module-level functions have no self parameter."""
        s = get_strategy("pythonic-functional")
        code = s.generate_logic(self._make_ctx())
        self.assertNotIn("self,", code)

    def test_runner_calls_build(self) -> None:
        """Runner calls build() and uses SyncInterpreter."""
        s = get_strategy("pythonic-functional")
        code = s.generate_runner(self._make_ctx())
        self.assertIn("build()", code)
        self.assertIn("SyncInterpreter(machine)", code)

    def test_runner_async_mode(self) -> None:
        """Async runner uses Interpreter and asyncio."""
        s = get_strategy("pythonic-functional")
        ctx = self._make_ctx(is_async=True)
        code = s.generate_runner(ctx)
        self.assertIn("Interpreter(machine)", code)
        self.assertIn("asyncio.run(main())", code)
        self.assertIn("await ", code)

    def test_runner_has_main_guard(self) -> None:
        """Runner has if __name__ == '__main__' block."""
        s = get_strategy("pythonic-functional")
        code = s.generate_runner(self._make_ctx())
        self.assertIn('if __name__ == "__main__":', code)

    def test_runner_sends_events(self) -> None:
        """Runner simulates events from the config."""
        s = get_strategy("pythonic-functional")
        code = s.generate_runner(self._make_ctx())
        self.assertIn('send("TIMER")', code)

    def test_logic_contains_section_headers(self) -> None:
        """Generated logic has section headers for actions/guards/services."""
        s = get_strategy("pythonic-functional")
        code = s.generate_logic(self._make_ctx())
        self.assertIn("# Actions", code)
        self.assertIn("# Guards", code)
        self.assertIn("# Services", code)

    def test_logic_build_function_docstring(self) -> None:
        """build() function has a descriptive docstring."""
        s = get_strategy("pythonic-functional")
        code = s.generate_logic(self._make_ctx())
        self.assertIn("def build()", code)
        self.assertIn("build_machine()", code)

    def test_logic_state_entry_actions(self) -> None:
        """States with entry actions include them in State constructor."""
        s = get_strategy("pythonic-functional")
        code = s.generate_logic(self._make_ctx())
        self.assertIn('entry=["logEnter"]', code)

    def test_logic_state_invoke(self) -> None:
        """States with invoke include it in State constructor."""
        s = get_strategy("pythonic-functional")
        code = s.generate_logic(self._make_ctx())
        self.assertIn("invoke=", code)
        self.assertIn("fetchData", code)

    def test_logic_transition_with_actions(self) -> None:
        """Transitions include actions parameter."""
        s = get_strategy("pythonic-functional")
        code = s.generate_logic(self._make_ctx())
        self.assertIn('actions="increment"', code)

    def test_logic_transition_with_guard(self) -> None:
        """Transitions include guard parameter."""
        s = get_strategy("pythonic-functional")
        code = s.generate_logic(self._make_ctx())
        self.assertIn('guard="isReady"', code)

    def test_logic_build_machine_actions_refs(self) -> None:
        """build_machine() receives action function references (not strings)."""
        s = get_strategy("pythonic-functional")
        code = s.generate_logic(self._make_ctx())
        self.assertIn("actions=[", code)
        # Function references, not strings
        self.assertIn("increment", code)
        self.assertIn("log_enter", code)

    def test_logic_build_machine_guards_refs(self) -> None:
        """build_machine() receives guard function references."""
        s = get_strategy("pythonic-functional")
        code = s.generate_logic(self._make_ctx())
        self.assertIn("guards=[", code)
        self.assertIn("is_ready", code)

    def test_logic_build_machine_services_refs(self) -> None:
        """build_machine() receives service function references."""
        s = get_strategy("pythonic-functional")
        code = s.generate_logic(self._make_ctx())
        self.assertIn("services=[", code)
        self.assertIn("fetch_data", code)

    def test_logic_build_machine_context(self) -> None:
        """build_machine() receives context dictionary."""
        s = get_strategy("pythonic-functional")
        code = s.generate_logic(self._make_ctx())
        self.assertIn("context=", code)
        self.assertIn("'count': 0", code)

    def test_logic_logger_info_before_try(self) -> None:
        """logger.info goes BEFORE the try: block, not inside it."""
        s = get_strategy("pythonic-functional")
        code = s.generate_logic(self._make_ctx())
        # Find the pattern: logger.info followed by try: at the same indent
        lines = code.split("\n")
        for i, line in enumerate(lines):
            if "logger.info" in line and "Executing action" in line:
                # The next non-empty line should be try:
                for j in range(i + 1, len(lines)):
                    if lines[j].strip():
                        self.assertIn("try:", lines[j])
                        break
                break
