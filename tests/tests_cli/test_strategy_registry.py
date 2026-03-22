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

            def generate_logic(self, ctx: GenerationContext) -> str:
                return "logic"

            def generate_runner(self, ctx: GenerationContext) -> str:
                return "runner"

        s = DummyStrategy()
        self.assertEqual(s.name, "dummy")
