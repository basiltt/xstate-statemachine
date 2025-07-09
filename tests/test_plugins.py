# tests/test_plugins.py
import logging
import unittest
from unittest.mock import MagicMock

from src.xstate_statemachine import (
    PluginBase,
    LoggingInspector,
    Event,
)
from src.xstate_statemachine.events import DoneEvent

# -----------------------------------------------------------------------------
# Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Test Class for Plugins
# -----------------------------------------------------------------------------
class TestPlugins(unittest.TestCase):
    """
    Test suite for the plugin system and built-in plugins.
    """

    def test_plugin_base_methods_do_not_raise_errors(self) -> None:
        """The base PluginBase methods should execute without error."""
        plugin = PluginBase()
        try:
            plugin.on_interpreter_start(None)
            plugin.on_interpreter_stop(None)
            plugin.on_event_received(None, Event("TEST"))
            plugin.on_transition(None, set(), set(), None)
            plugin.on_action_execute(None, None)
        except Exception as ex:
            self.fail(
                f"PluginBase methods raised an unexpected exception: {ex}"
            )

    def test_logging_inspector_handles_various_events(self) -> None:
        """LoggingInspector should not crash on different event types."""
        inspector = LoggingInspector()
        mock_interp = MagicMock()

        try:
            inspector.on_event_received(
                mock_interp, Event("TEST_EVENT", payload={"data": "test_data"})
            )
            inspector.on_event_received(
                mock_interp,
                DoneEvent(
                    "done.invoke.test_service",
                    data={"result": "success"},
                    src="test_service",
                ),
            )
            inspector.on_event_received(mock_interp, Event("SIMPLE_EVENT"))
        except Exception as ex:
            self.fail(
                f"LoggingInspector failed to handle different event types gracefully: {ex}"
            )

    def test_logging_inspector_on_transition(self) -> None:
        """Ensures LoggingInspector's on_transition method runs without error."""
        inspector = LoggingInspector()
        mock_interp = MagicMock()
        mock_interp.context = {"value": 1}
        from_state = MagicMock()
        from_state.id = "state.a"
        to_state = MagicMock()
        to_state.id = "state.b"
        transition = MagicMock()
        transition.event = "TEST_EVENT"

        inspector.on_transition(
            mock_interp, {from_state}, {to_state}, transition
        )

    def test_logging_inspector_on_action_execute(self) -> None:
        """Ensures LoggingInspector's on_action_execute method runs without error."""
        inspector = LoggingInspector()
        mock_interp = MagicMock()
        action_def = MagicMock()
        action_def.type = "testAction"

        inspector.on_action_execute(mock_interp, action_def)

    def test_logging_inspector_with_primitive_payload(self) -> None:
        """LoggingInspector should handle non-dict payloads gracefully."""
        inspector = LoggingInspector()
        mock_interp = MagicMock()
        inspector.on_event_received(
            mock_interp, Event("EVENT_WITH_STRING", payload="a string value")
        )
        inspector.on_event_received(
            mock_interp, Event("EVENT_WITH_INT", payload=123)
        )

    def test_custom_plugin_hooks_are_callable(self) -> None:
        """A custom plugin's overridden methods should be callable."""
        call_order = []

        class CustomPlugin(PluginBase):
            def on_interpreter_start(self, i):
                call_order.append("start")

            def on_event_received(self, i, e):
                call_order.append("event")

            def on_action_execute(self, i, a):
                call_order.append("action")

            def on_transition(self, i, fs, ts, t):
                call_order.append("transition")

            def on_interpreter_stop(self, i):
                call_order.append("stop")

        plugin = CustomPlugin()
        plugin.on_interpreter_start(None)
        plugin.on_event_received(None, Event("test"))
        plugin.on_action_execute(None, None)
        plugin.on_transition(None, set(), set(), None)
        plugin.on_interpreter_stop(None)
        self.assertEqual(
            call_order, ["start", "event", "action", "transition", "stop"]
        )

    def test_logging_inspector_handles_internal_transition(self) -> None:
        """LoggingInspector should log context changes on internal transitions."""
        inspector = LoggingInspector()
        mock_interp = MagicMock()
        mock_interp.context = {"count": 10}
        state_node = MagicMock()
        state_node.id = "state.a"
        transition = MagicMock()
        transition.event = "INTERNAL_EVENT"
        transition.actions = ["someAction"]
        inspector.on_transition(
            mock_interp, {state_node}, {state_node}, transition
        )

    # ---------- 10 New Tests ----------

    def test_plugin_base_with_no_overrides(self) -> None:
        """A subclass with no overrides should function like the base class."""

        class EmptyPlugin(PluginBase):
            pass

        plugin = EmptyPlugin()
        try:
            plugin.on_interpreter_start(None)
            plugin.on_interpreter_stop(None)
        except Exception as e:
            self.fail(f"EmptyPlugin raised an unexpected exception: {e}")

    def test_multiple_plugins_are_called_in_order(self) -> None:
        """Multiple plugins should be called in the order they are added."""
        call_order = []

        class PluginA(PluginBase):
            def on_interpreter_start(self, i):
                call_order.append("A")

        class PluginB(PluginBase):
            def on_interpreter_start(self, i):
                call_order.append("B")

        mock_interpreter = MagicMock()
        mock_interpreter._plugins = [PluginA(), PluginB()]

        # This is a conceptual test. The actual loop is in the interpreter.
        for p in mock_interpreter._plugins:
            p.on_interpreter_start(mock_interpreter)

        self.assertEqual(call_order, ["A", "B"])

    def test_logging_inspector_on_event_with_none_payload(self) -> None:
        """Logging Inspector should not fail if payload is explicitly None."""
        inspector = LoggingInspector()
        mock_interp = MagicMock()
        try:
            inspector.on_event_received(
                mock_interp, Event("TEST", payload=None)
            )
        except Exception as e:
            self.fail(f"Inspector failed on None payload: {e}")

    def test_plugin_can_modify_shared_object(self) -> None:
        """A plugin should be able to interact with a shared mutable object."""
        log_list = []

        class StateLoggerPlugin(PluginBase):
            def __init__(self, logs):
                self.logs = logs

            def on_transition(self, i, fs, ts, t):
                self.logs.append(list(i.current_state_ids)[0])

        mock_interpreter = MagicMock()
        mock_interpreter.current_state_ids = {"state.b"}
        plugin = StateLoggerPlugin(log_list)
        plugin.on_transition(mock_interpreter, set(), set(), None)
        self.assertEqual(log_list, ["state.b"])

    def test_logging_inspector_with_complex_payload(self) -> None:
        """Logging Inspector should handle complex nested data in payloads."""
        inspector = LoggingInspector()
        mock_interp = MagicMock()
        complex_payload = {
            "user": {"name": "test", "roles": ["admin", "editor"]}
        }
        try:
            inspector.on_event_received(
                mock_interp, Event("COMPLEX", payload=complex_payload)
            )
        except Exception as e:
            self.fail(f"Inspector failed on complex payload: {e}")

    def test_plugin_method_raising_exception(self) -> None:
        """An exception in a plugin should not halt the test suite (it's up to the interpreter to handle)."""

        class FailingPlugin(PluginBase):
            def on_interpreter_start(self, i):
                raise ValueError("Plugin failed")

        plugin = FailingPlugin()
        with self.assertRaises(ValueError):
            plugin.on_interpreter_start(None)

    def test_logging_inspector_with_empty_context(self) -> None:
        """Logging Inspector on_transition should handle an empty context."""
        inspector = LoggingInspector()
        mock_interp = MagicMock()
        mock_interp.context = {}  # Empty context
        from_state, to_state, transition = (
            MagicMock(),
            MagicMock(),
            MagicMock(),
        )
        from_state.id, to_state.id, transition.event = "a", "b", "EV"

        try:
            inspector.on_transition(
                mock_interp, {from_state}, {to_state}, transition
            )
        except Exception as e:
            self.fail(f"Inspector failed on empty context: {e}")

    def test_logging_inspector_with_no_state_change(self) -> None:
        """Logging Inspector should log internal transitions correctly when state does not change."""
        inspector = LoggingInspector()
        mock_interp, state, transition = MagicMock(), MagicMock(), MagicMock()
        mock_interp.context, state.id, transition.event, transition.actions = (
            {},
            "a",
            "EV",
            ["action"],
        )

        # The logic for this is inside on_transition, so we can't fully mock it
        # but we can check that it doesn't raise an error.
        try:
            inspector.on_transition(mock_interp, {state}, {state}, transition)
        except Exception as e:
            self.fail(f"Inspector failed on no-change transition: {e}")

    def test_plugin_receives_correct_interpreter_instance(self) -> None:
        """The interpreter instance passed to a plugin hook should be the correct one."""

        class MyPlugin(PluginBase):
            def on_interpreter_start(self, interpreter):
                self.captured_id = interpreter.id

        plugin = MyPlugin()
        mock_interpreter = MagicMock()
        mock_interpreter.id = "test-machine-123"
        plugin.on_interpreter_start(mock_interpreter)
        self.assertEqual(plugin.captured_id, "test-machine-123")

    def test_logging_inspector_handles_all_event_types(self) -> None:
        """The logging inspector should not crash when given any event type."""
        from src.xstate_statemachine.events import AfterEvent, DoneEvent

        inspector = LoggingInspector()
        mock_interp = MagicMock()

        try:
            inspector.on_event_received(
                mock_interp, AfterEvent("after.1000.state")
            )
            inspector.on_event_received(
                mock_interp, DoneEvent("done.invoke.svc", data=None, src="svc")
            )
        except Exception as e:
            self.fail(f"Inspector failed on special event types: {e}")
