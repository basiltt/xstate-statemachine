# /tests/test_public_api_surface.py
# -----------------------------------------------------------------------------
# 🧪 Test Suite: Documented Public API Surface
# -----------------------------------------------------------------------------
# This module pins the interpreter attributes that the README and the `docs/`
# guides present as public API. Prior to v0.5.1 several of these names were
# documented but never implemented, so every published example raised
# `AttributeError` on contact.
#
# 🏛️ Architecture decision: these are *contract* tests. They exist to ensure
# documentation and implementation cannot silently diverge again — if a
# documented name is removed, a test fails rather than a user's copy-pasted
# snippet.
#
# Also covers `spawn_`/`spawn_blocking_` logic auto-discovery, which routed
# actor keys to `actions` instead of `services` and therefore made the actor
# model structurally incompatible with `logic_modules=` discovery.
# -----------------------------------------------------------------------------
"""
Contract tests for the documented public interpreter API.
"""

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import logging
import types
import unittest
from typing import Any, Dict

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from src.xstate_statemachine import (
    Interpreter,
    LoggingInspector,
    MachineLogic,
    SyncInterpreter,
    create_machine,
)

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# 📐 A trivial two-state machine reused across the suite.
SIMPLE_CONFIG: Dict[str, Any] = {
    "id": "m",
    "initial": "a",
    "states": {"a": {"on": {"GO": "b"}}, "b": {}},
}


# -----------------------------------------------------------------------------
# 📖 Documented Attribute Aliases
# -----------------------------------------------------------------------------
class TestDocumentedAttributes(unittest.IsolatedAsyncioTestCase):
    """Pins the attribute names published in the README and docs guides."""

    def test_active_state_ids_matches_current_state_ids_sync(self) -> None:
        """`active_state_ids` must mirror `current_state_ids`."""
        # Arrange
        interpreter = SyncInterpreter(
            create_machine(SIMPLE_CONFIG, logic=MachineLogic())
        ).start()

        # Act / Assert
        self.assertEqual(
            interpreter.current_state_ids, interpreter.active_state_ids
        )
        self.assertEqual({"m.a"}, interpreter.active_state_ids)

        interpreter.send("GO")
        self.assertEqual({"m.b"}, interpreter.active_state_ids)

    async def test_active_state_ids_matches_current_state_ids_async(
        self,
    ) -> None:
        """The async interpreter must expose the same alias."""
        # Arrange
        interpreter = await Interpreter(
            create_machine(SIMPLE_CONFIG, logic=MachineLogic())
        ).start()
        self.addAsyncCleanup(interpreter.stop)

        # Act / Assert
        self.assertEqual(
            interpreter.current_state_ids, interpreter.active_state_ids
        )

    def test_is_running_reflects_lifecycle_sync(self) -> None:
        """`is_running` must be True only between start() and stop()."""
        # Arrange
        interpreter = SyncInterpreter(
            create_machine(SIMPLE_CONFIG, logic=MachineLogic())
        )
        self.assertFalse(interpreter.is_running)

        # Act
        interpreter.start()
        self.assertTrue(interpreter.is_running)
        interpreter.stop()

        # Assert
        self.assertFalse(interpreter.is_running)

    async def test_is_running_reflects_lifecycle_async(self) -> None:
        """The async interpreter's `is_running` must track its status."""
        # Arrange
        interpreter = Interpreter(
            create_machine(SIMPLE_CONFIG, logic=MachineLogic())
        )
        self.assertFalse(interpreter.is_running)

        # Act
        await interpreter.start()
        self.assertTrue(interpreter.is_running)
        await interpreter.stop()

        # Assert
        self.assertFalse(interpreter.is_running)

    def test_plugins_property_is_assignable(self) -> None:
        """Docs assign a list directly: `interp.plugins = [...]`."""
        # Arrange
        interpreter = SyncInterpreter(
            create_machine(SIMPLE_CONFIG, logic=MachineLogic())
        )
        inspector = LoggingInspector()

        # Act
        interpreter.plugins = [inspector]

        # Assert
        self.assertIn(inspector, interpreter.plugins)
        interpreter.start()
        interpreter.send("GO")
        self.assertEqual({"m.b"}, interpreter.active_state_ids)

    def test_plugins_property_rejects_non_list(self) -> None:
        """Assigning a non-list must fail fast with a clear error."""
        # Arrange
        interpreter = SyncInterpreter(
            create_machine(SIMPLE_CONFIG, logic=MachineLogic())
        )

        # Act / Assert
        with self.assertRaises(TypeError):
            interpreter.plugins = LoggingInspector()  # type: ignore[assignment]

    def test_use_and_plugins_property_agree(self) -> None:
        """`use()` registrations must be visible through `.plugins`."""
        # Arrange
        interpreter = SyncInterpreter(
            create_machine(SIMPLE_CONFIG, logic=MachineLogic())
        )
        inspector = LoggingInspector()

        # Act
        interpreter.use(inspector)

        # Assert
        self.assertIn(inspector, interpreter.plugins)


# -----------------------------------------------------------------------------
# 👶 Actor Spawning Under Logic Auto-Discovery
# -----------------------------------------------------------------------------
class TestSpawnActionAutoDiscovery(unittest.TestCase):
    """Pins that `spawn_` actor keys resolve as services, not actions.

    🐛 Regression: `LogicLoader._extract_logic_from_node` registered
    `spawn_<key>` as a required *action*. The interpreters resolve those keys
    from `logic.services` at execution time, so auto-discovery always failed
    with `ImplementationMissingError` and the actor model could only be used
    by bypassing discovery with an explicit `logic=`.
    """

    @staticmethod
    def _make_logic_module() -> types.ModuleType:
        """Builds an in-memory logic module exposing a child-machine service.

        Returns:
            types.ModuleType: A module with a `child` service function.
        """
        module = types.ModuleType("spawn_logic_fixture")
        child = create_machine(
            {"id": "child", "initial": "i", "states": {"i": {}}},
            logic=MachineLogic(),
        )

        def child_service(_interpreter: Any, _ctx: Any, _event: Any) -> Any:
            """Returns the child machine to spawn."""
            return child

        # 🏷️ Name the function to match the `spawn_child` action key.
        child_service.__name__ = "child"
        module.child = child_service  # type: ignore[attr-defined]
        return module

    def test_spawn_key_registered_as_service(self) -> None:
        """`spawn_child` must look up a `child` *service*."""
        # Arrange
        module = self._make_logic_module()
        config = {
            "id": "m",
            "initial": "a",
            "context": {},
            "states": {"a": {"entry": ["spawn_child"]}},
        }

        # Act
        machine = create_machine(config, logic_modules=[module])

        # Assert
        self.assertIn("child", machine.logic.services)
        self.assertNotIn("spawn_child", machine.logic.actions)

    def test_spawn_blocking_key_registered_as_service(self) -> None:
        """`spawn_blocking_child` must strip the full prefix."""
        # Arrange
        module = self._make_logic_module()
        config = {
            "id": "m",
            "initial": "a",
            "context": {},
            "states": {"a": {"entry": ["spawn_blocking_child"]}},
        }

        # Act
        machine = create_machine(config, logic_modules=[module])

        # Assert
        self.assertIn("child", machine.logic.services)
        self.assertNotIn("spawn_blocking_child", machine.logic.actions)

    def test_ordinary_actions_still_registered_as_actions(self) -> None:
        """Non-spawn actions must be unaffected by the routing change."""
        # Arrange
        module = types.ModuleType("plain_logic_fixture")

        def do_thing(_i: Any, _c: Any, _e: Any, _a: Any) -> None:
            """A plain action implementation."""

        module.do_thing = do_thing  # type: ignore[attr-defined]
        config = {
            "id": "m",
            "initial": "a",
            "context": {},
            "states": {"a": {"entry": ["do_thing"]}},
        }

        # Act
        machine = create_machine(config, logic_modules=[module])

        # Assert
        self.assertIn("do_thing", machine.logic.actions)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
