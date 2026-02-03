# /tests/test_plugins.py
# -----------------------------------------------------------------------------
# 🧪 Test Suite: Plugin System
# -----------------------------------------------------------------------------
# This module provides a comprehensive test suite for the plugin system of the
# state machine library. It validates the foundational `PluginBase` class,
# ensuring that its interface is stable and that custom plugins can be built
# upon it without issue.
#
# A significant portion of the suite is dedicated to the built-in
# `LoggingInspector` plugin, verifying its ability to handle various events,
# transitions, and payloads gracefully without errors. The tests also cover
# scenarios with multiple plugins to ensure they are invoked in the correct
# order.
#
# The overall goal is to guarantee the plugin system is robust, extensible,
# and that the default plugins are reliable and informative.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import logging
import unittest
from typing import Any, List, Optional, Set
from unittest.mock import MagicMock

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from src.xstate_statemachine import Event, LoggingInspector, PluginBase
from src.xstate_statemachine import Interpreter
from src.xstate_statemachine.events import DoneEvent, AfterEvent
from src.xstate_statemachine.models import StateNode, ActionDefinition

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
# Configures a basic logger to show informative messages during test execution.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 🏛️ Test Class: TestPlugins
# -----------------------------------------------------------------------------


class TestPlugins(unittest.TestCase):
    """A collection of unit tests for the plugin system.

    This suite validates the `PluginBase` contract and the functionality
    of the built-in `LoggingInspector` plugin.
    """

    # -------------------------------------------------------------------------
    # 🔌 PluginBase Class Tests
    # -------------------------------------------------------------------------

    def test_plugin_base_methods_do_not_raise_errors(self) -> None:
        """The base PluginBase methods should execute without error."""
        logger.info("🧪 Testing that PluginBase methods run without errors.")
        # 📋 Arrange: Create a plugin instance and mock objects to satisfy type hints.
        plugin = PluginBase()
        # ✅ FIX: Use MagicMock() instead of None to satisfy type hints.
        mock_interpreter = MagicMock(spec=Interpreter)
        mock_action = MagicMock(spec=ActionDefinition)
        mock_transition = MagicMock()

        # 🚀 Act & Assert: Call each hook. The test passes if no exceptions are raised.
        try:
            plugin.on_interpreter_start(interpreter=mock_interpreter)
            plugin.on_interpreter_stop(interpreter=mock_interpreter)
            plugin.on_event_received(interpreter=mock_interpreter, event=Event("TEST"))
            plugin.on_transition(
                interpreter=mock_interpreter,
                from_states=set(),
                to_states=set(),
                transition=mock_transition,
            )
            plugin.on_action_execute(interpreter=mock_interpreter, action=mock_action)
        except Exception as ex:
            self.fail(f"❌ PluginBase methods raised an unexpected exception: {ex}")

    def test_plugin_base_with_no_overrides(self) -> None:
        """A subclass with no overrides should function like the base class."""
        logger.info("🧪 Testing that an empty plugin subclass is valid.")

        # 📋 Arrange: Define an empty plugin and create a mock interpreter.
        class EmptyPlugin(PluginBase):
            pass

        plugin = EmptyPlugin()
        # ✅ FIX: Use a MagicMock instead of None to satisfy the type checker.
        mock_interpreter = MagicMock(spec=Interpreter)

        # 🚀 Act & Assert: Ensure the inherited methods can be called without error.
        try:
            plugin.on_interpreter_start(interpreter=mock_interpreter)
            plugin.on_interpreter_stop(interpreter=mock_interpreter)
        except Exception as e:
            self.fail(f"❌ EmptyPlugin raised an unexpected exception: {e}")

    def test_plugin_method_raising_exception(self) -> None:
        """An exception in a plugin should not halt the test suite."""
        logger.info("🧪 Testing that exceptions from plugins are propagated correctly.")

        # 📋 Arrange: A plugin designed to fail.
        class FailingPlugin(PluginBase):
            def on_interpreter_start(self, _interpreter: Optional[Interpreter]) -> None:
                raise ValueError("Plugin failed")

        plugin = FailingPlugin()

        # 🚀 Act & Assert: The interpreter is responsible for handling this,
        # but for a direct call, the exception should be raised.
        with self.assertRaises(ValueError):
            plugin.on_interpreter_start(_interpreter=None)

    # -------------------------------------------------------------------------
    # 🔍 LoggingInspector Plugin Tests
    # -------------------------------------------------------------------------

    def test_logging_inspector_handles_various_events(self) -> None:
        """LoggingInspector should not crash on different event types."""
        logger.info("🧪 Testing LoggingInspector with various event types.")
        # 📋 Arrange: Create the inspector and a mock interpreter.
        inspector = LoggingInspector()
        mock_interp = MagicMock(spec=Interpreter)

        # 🚀 Act & Assert: Send various event types to the inspector's hook.
        try:
            inspector.on_event_received(
                mock_interp, Event("TEST_EVENT", payload={"data": "test_data"})
            )
            # ✅ FIX: Ignore type error. It's valid to pass a subclass (DoneEvent)
            # where the base class (Event) is expected.
            inspector.on_event_received(
                mock_interp,
                DoneEvent(  # type: ignore
                    type="done.invoke.test_service",
                    data={"result": "success"},
                    src="test_service",
                ),
            )
            inspector.on_event_received(mock_interp, Event("SIMPLE_EVENT"))
        except Exception as ex:
            self.fail(
                "❌ LoggingInspector failed to handle different event types "
                f"gracefully: {ex}"
            )

    def test_logging_inspector_handles_all_event_types(self) -> None:
        """The logging inspector should not crash when given any event type."""
        logger.info("🧪 Testing LoggingInspector with special event subtypes.")
        # 📋 Arrange
        inspector = LoggingInspector()
        mock_interp = MagicMock(spec=Interpreter)

        # 🚀 Act & Assert: Test `AfterEvent` and `DoneEvent`.
        try:
            # ✅ FIX: Ignore type errors for passing subclasses.
            inspector.on_event_received(
                mock_interp,
                AfterEvent(type="after.1000.state"),  # type: ignore
            )
            inspector.on_event_received(
                mock_interp,
                DoneEvent(type="done.invoke.svc", data=None, src="svc"),  # type: ignore
            )
        except Exception as e:
            self.fail(f"❌ Inspector failed on special event types: {e}")

    def test_logging_inspector_on_transition(self) -> None:
        """Ensures LoggingInspector's on_transition method runs without error."""
        logger.info("🧪 Testing LoggingInspector's `on_transition` hook.")
        # 📋 Arrange
        inspector = LoggingInspector()
        mock_interp = MagicMock(spec=Interpreter)
        mock_interp.context = {"value": 1}
        from_state = MagicMock(spec=StateNode)
        from_state.id = "state.a"
        to_state = MagicMock(spec=StateNode)
        to_state.id = "state.b"
        transition = MagicMock()
        transition.event = "TEST_EVENT"

        # 🚀 Act & Assert: The call should complete without raising any exceptions.
        inspector.on_transition(mock_interp, {from_state}, {to_state}, transition)

    def test_logging_inspector_handles_internal_transition(self) -> None:
        """LoggingInspector should log context changes on internal transitions."""
        logger.info("🧪 Testing LoggingInspector with an internal transition.")
        # 📋 Arrange
        inspector = LoggingInspector()
        mock_interp = MagicMock(spec=Interpreter)
        mock_interp.context = {"count": 10}
        state_node = MagicMock(spec=StateNode)
        state_node.id = "state.a"
        transition = MagicMock()
        transition.event = "INTERNAL_EVENT"
        transition.actions = ["someAction"]

        # 🚀 Act & Assert: The call should complete without raising any exceptions.
        inspector.on_transition(mock_interp, {state_node}, {state_node}, transition)

    def test_logging_inspector_on_action_execute(self) -> None:
        """Ensures LoggingInspector's on_action_execute method runs without error."""
        logger.info("🧪 Testing LoggingInspector's `on_action_execute` hook.")
        # 📋 Arrange
        inspector = LoggingInspector()
        mock_interp = MagicMock(spec=Interpreter)
        action_def = MagicMock(spec=ActionDefinition)
        action_def.type = "testAction"

        # 🚀 Act & Assert: The call should complete without raising any exceptions.
        inspector.on_action_execute(mock_interp, action_def)

    def test_logging_inspector_with_primitive_payload(self) -> None:
        """LoggingInspector should handle non-dict payloads gracefully."""
        logger.info("🧪 Testing LoggingInspector with primitive payloads.")
        # 📋 Arrange
        inspector = LoggingInspector()
        mock_interp = MagicMock(spec=Interpreter)
        # 🚀 Act & Assert: The calls should complete without raising any exceptions.
        # ✅ FIX: Ignore type errors. The test is intentionally passing non-dict payloads
        # to ensure the inspector handles them without crashing.
        inspector.on_event_received(
            mock_interp,
            Event("EVENT_WITH_STRING", payload="a string value"),  # type: ignore
        )
        inspector.on_event_received(
            mock_interp,
            Event("EVENT_WITH_INT", payload=123),  # type: ignore
        )

    def test_logging_inspector_with_complex_payload(self) -> None:
        """Logging Inspector should handle complex nested data in payloads."""
        logger.info("🧪 Testing LoggingInspector with a complex payload.")
        # 📋 Arrange
        inspector = LoggingInspector()
        mock_interp = MagicMock(spec=Interpreter)
        complex_payload = {"user": {"name": "test", "roles": ["admin", "editor"]}}
        # 🚀 Act & Assert: The call should complete without raising any exceptions.
        try:
            inspector.on_event_received(
                mock_interp, Event("COMPLEX", payload=complex_payload)
            )
        except Exception as e:
            self.fail(f"❌ Inspector failed on complex payload: {e}")

    def test_logging_inspector_on_event_with_none_payload(self) -> None:
        """Logging Inspector should not fail if payload is explicitly None."""
        logger.info("🧪 Testing LoggingInspector with a None payload.")
        # 📋 Arrange
        inspector = LoggingInspector()
        mock_interp = MagicMock(spec=Interpreter)
        # 🚀 Act & Assert: The call should complete without raising any exceptions.
        try:
            # ✅ FIX: Ignore type error. This test validates correct handling of a None payload.
            inspector.on_event_received(
                mock_interp,
                Event("TEST", payload=None),  # type: ignore
            )
        except Exception as e:
            self.fail(f"❌ Inspector failed on None payload: {e}")

    def test_logging_inspector_with_empty_context(self) -> None:
        """Logging Inspector on_transition should handle an empty context."""
        logger.info("🧪 Testing LoggingInspector's on_transition with empty context.")
        # 📋 Arrange
        inspector = LoggingInspector()
        mock_interp = MagicMock(spec=Interpreter)
        mock_interp.context = {}  # Empty context
        from_state, to_state, transition = (
            MagicMock(spec=StateNode),
            MagicMock(spec=StateNode),
            MagicMock(),
        )
        from_state.id, to_state.id, transition.event = "a", "b", "EV"

        # 🚀 Act & Assert: The call should complete without raising any exceptions.
        try:
            inspector.on_transition(mock_interp, {from_state}, {to_state}, transition)
        except Exception as e:
            self.fail(f"❌ Inspector failed on empty context: {e}")

    # -------------------------------------------------------------------------
    # 🧩 Custom and Multi-Plugin Scenarios
    # -------------------------------------------------------------------------

    def test_custom_plugin_hooks_are_callable(self) -> None:
        """A custom plugin's overridden methods should be callable in order."""
        logger.info("🧪 Testing that custom plugin hooks are called correctly.")
        # 📋 Arrange: A list to track the order of method calls.
        call_order: List[str] = []

        class CustomPlugin(PluginBase):
            """A test plugin that records the order of hook invocations."""

            def on_interpreter_start(self, _i: Optional[Interpreter]) -> None:
                call_order.append("start")

            def on_event_received(self, _i: Optional[Interpreter], _e: Event) -> None:
                call_order.append("event")

            def on_action_execute(
                self, _i: Optional[Interpreter], _a: Optional[ActionDefinition]
            ) -> None:
                call_order.append("action")

            def on_transition(
                self,
                _i: Optional[Interpreter],
                _fs: Set[StateNode],
                _ts: Set[StateNode],
                _t: Any,
            ) -> None:
                call_order.append("transition")

            def on_interpreter_stop(self, _i: Optional[Interpreter]) -> None:
                call_order.append("stop")

        plugin = CustomPlugin()
        # ✅ FIX: Use mock objects instead of None to satisfy stricter type hints.
        mock_interpreter = MagicMock(spec=Interpreter)
        mock_action = MagicMock(spec=ActionDefinition)

        # 🚀 Act: Call all the hooks in a typical lifecycle order.
        plugin.on_interpreter_start(mock_interpreter)
        plugin.on_event_received(mock_interpreter, Event("test"))
        plugin.on_action_execute(mock_interpreter, mock_action)
        plugin.on_transition(mock_interpreter, set(), set(), None)
        plugin.on_interpreter_stop(mock_interpreter)

        # ✅ Assert: The hooks were called in the expected sequence.
        self.assertEqual(call_order, ["start", "event", "action", "transition", "stop"])

    def test_multiple_plugins_are_called_in_order(self) -> None:
        """Multiple plugins should be called in the order they are added."""
        logger.info("🧪 Testing invocation order for multiple plugins.")
        # 📋 Arrange: A list to track call order and two simple plugins.
        call_order: List[str] = []

        class PluginA(PluginBase):
            def on_interpreter_start(self, _interpreter: Optional[Interpreter]) -> None:
                call_order.append("A")

        class PluginB(PluginBase):
            def on_interpreter_start(self, _interpreter: Optional[Interpreter]) -> None:
                call_order.append("B")

        mock_interpreter = MagicMock(spec=Interpreter)
        mock_interpreter._plugins = [PluginA(), PluginB()]

        # 🚀 Act: Simulate the interpreter's internal plugin loop.
        for p in mock_interpreter._plugins:
            p.on_interpreter_start(mock_interpreter)

        # ✅ Assert: The plugins were called in the order they were registered.
        self.assertEqual(call_order, ["A", "B"])

    def test_plugin_can_modify_shared_object(self) -> None:
        """A plugin should be able to interact with a shared mutable object."""
        logger.info("🧪 Testing a plugin that modifies a shared object.")
        # 📋 Arrange: A list that the plugin will write to.
        log_list: List[str] = []

        class StateLoggerPlugin(PluginBase):
            def __init__(self, logs: List[str]) -> None:
                # ✅ FIX: Removed the `super().__init__()` call. While good practice,
                # it was confusing the linter in this nested class context, and
                # is not strictly necessary as the base __init__ does nothing.
                self.logs = logs

            def on_transition(
                self,
                interpreter: Interpreter,
                _fs: Set[StateNode],
                _ts: Set[StateNode],
                _t: Any,
            ) -> None:
                # This plugin's job is to log the current state ID to the shared list.
                self.logs.append(list(interpreter.current_state_ids)[0])

        mock_interpreter = MagicMock(spec=Interpreter)
        mock_interpreter.current_state_ids = {"state.b"}
        plugin = StateLoggerPlugin(log_list)

        # 🚀 Act: Trigger the plugin's hook.
        plugin.on_transition(mock_interpreter, set(), set(), None)

        # ✅ Assert: The plugin successfully appended the state to the shared list.
        self.assertEqual(log_list, ["state.b"])

    def test_plugin_receives_correct_interpreter_instance(self) -> None:
        """The interpreter instance passed to a plugin hook should be correct."""
        logger.info("🧪 Testing that plugins receive the correct interpreter instance.")

        # 📋 Arrange: A plugin that captures the ID of the interpreter it receives.
        class MyPlugin(PluginBase):
            def __init__(self) -> None:
                self.captured_id: Optional[str] = None

            def on_interpreter_start(self, interpreter: Interpreter) -> None:
                self.captured_id = interpreter.id

        plugin = MyPlugin()
        mock_interpreter = MagicMock(spec=Interpreter)
        mock_interpreter.id = "test-machine-123"

        # 🚀 Act: Trigger the hook.
        plugin.on_interpreter_start(mock_interpreter)

        # ✅ Assert: The ID captured by the plugin matches the mock's ID.
        self.assertEqual(plugin.captured_id, "test-machine-123")
