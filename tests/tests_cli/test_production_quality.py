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

    def _make_ctx(self, template: str) -> GenerationContext:
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
