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
            json_filenames=["parent.json", "child.json"],
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
        self.assertIn("json.load", code)
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

    def test_runner_imports_json_and_path(self) -> None:
        """Hierarchical runner imports json and Path."""
        s = get_strategy("pythonic-class")
        code = s.generate_runner(self._make_ctx())
        self.assertIn("import json", code)
        self.assertIn("from pathlib import Path", code)

    def test_runner_imports_create_machine(self) -> None:
        """Hierarchical runner imports create_machine for children."""
        s = get_strategy("pythonic-class")
        code = s.generate_runner(self._make_ctx())
        self.assertIn("create_machine", code)

    def test_runner_has_main_guard(self) -> None:
        """Runner has if __name__ == '__main__' block."""
        s = get_strategy("pythonic-class")
        code = s.generate_runner(self._make_ctx())
        self.assertIn("__main__", code)

    def test_runner_sends_parent_events(self) -> None:
        """Runner sends parent events."""
        s = get_strategy("pythonic-class")
        code = s.generate_runner(self._make_ctx())
        self.assertIn("START", code)
        self.assertIn("STOP", code)

    def test_runner_sends_child_events(self) -> None:
        """Runner sends child events."""
        s = get_strategy("pythonic-class")
        code = s.generate_runner(self._make_ctx())
        self.assertIn("CHILD_EVENT", code)


class TestHierarchyPythonicBuilder(unittest.TestCase):
    """Tests for pythonic-builder hierarchical generation."""

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
            json_filenames=["parent.json", "child.json"],
            hierarchy=True,
            sleep=True,
            sleep_time=2,
            loader=False,
        )
        defaults.update(overrides)
        return GenerationContext(**defaults)

    def test_runner_calls_build(self) -> None:
        """Builder hierarchy runner calls build()."""
        s = get_strategy("pythonic-builder")
        code = s.generate_runner(self._make_ctx())
        self.assertIn("build()", code)

    def test_runner_loads_child_from_json(self) -> None:
        """Hierarchical runner loads child configs from JSON."""
        s = get_strategy("pythonic-builder")
        code = s.generate_runner(self._make_ctx())
        self.assertIn("json.load", code)
        self.assertIn("child.json", code)

    def test_runner_stops_children_before_parent(self) -> None:
        """Shutdown order: children first, then parent."""
        s = get_strategy("pythonic-builder")
        code = s.generate_runner(self._make_ctx())
        child_stop = code.find(".stop()")
        parent_stop = code.rfind(".stop()")
        self.assertNotEqual(child_stop, -1)
        self.assertNotEqual(parent_stop, -1)
        self.assertLess(child_stop, parent_stop)

    def test_runner_imports_json_and_path(self) -> None:
        """Hierarchical runner imports json and Path."""
        s = get_strategy("pythonic-builder")
        code = s.generate_runner(self._make_ctx())
        self.assertIn("import json", code)
        self.assertIn("from pathlib import Path", code)

    def test_runner_creates_child_interpreter(self) -> None:
        """Runner creates interpreter for child machine."""
        s = get_strategy("pythonic-builder")
        code = s.generate_runner(self._make_ctx())
        self.assertIn("SyncInterpreter(", code)

    def test_runner_sends_child_events(self) -> None:
        """Runner sends child events."""
        s = get_strategy("pythonic-builder")
        code = s.generate_runner(self._make_ctx())
        self.assertIn("CHILD_EVENT", code)

    def test_runner_has_main_guard(self) -> None:
        """Runner has if __name__ == '__main__' block."""
        s = get_strategy("pythonic-builder")
        code = s.generate_runner(self._make_ctx())
        self.assertIn("__main__", code)


class TestHierarchyPythonicFunctional(unittest.TestCase):
    """Tests for pythonic-functional hierarchical generation."""

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
            json_filenames=["parent.json", "child.json"],
            hierarchy=True,
            sleep=True,
            sleep_time=2,
            loader=False,
        )
        defaults.update(overrides)
        return GenerationContext(**defaults)

    def test_runner_calls_build(self) -> None:
        """Functional hierarchy runner calls build()."""
        s = get_strategy("pythonic-functional")
        code = s.generate_runner(self._make_ctx())
        self.assertIn("build()", code)

    def test_runner_loads_child_from_json(self) -> None:
        """Hierarchical runner loads child configs from JSON."""
        s = get_strategy("pythonic-functional")
        code = s.generate_runner(self._make_ctx())
        self.assertIn("json.load", code)
        self.assertIn("child.json", code)

    def test_runner_stops_children_before_parent(self) -> None:
        """Shutdown order: children first, then parent."""
        s = get_strategy("pythonic-functional")
        code = s.generate_runner(self._make_ctx())
        child_stop = code.find(".stop()")
        parent_stop = code.rfind(".stop()")
        self.assertNotEqual(child_stop, -1)
        self.assertNotEqual(parent_stop, -1)
        self.assertLess(child_stop, parent_stop)

    def test_runner_imports_json_and_path(self) -> None:
        """Hierarchical runner imports json and Path."""
        s = get_strategy("pythonic-functional")
        code = s.generate_runner(self._make_ctx())
        self.assertIn("import json", code)
        self.assertIn("from pathlib import Path", code)

    def test_runner_creates_child_interpreter(self) -> None:
        """Runner creates interpreter for child machine."""
        s = get_strategy("pythonic-functional")
        code = s.generate_runner(self._make_ctx())
        self.assertIn("SyncInterpreter(", code)

    def test_runner_sends_child_events(self) -> None:
        """Runner sends child events."""
        s = get_strategy("pythonic-functional")
        code = s.generate_runner(self._make_ctx())
        self.assertIn("CHILD_EVENT", code)

    def test_runner_has_main_guard(self) -> None:
        """Runner has if __name__ == '__main__' block."""
        s = get_strategy("pythonic-functional")
        code = s.generate_runner(self._make_ctx())
        self.assertIn("__main__", code)
