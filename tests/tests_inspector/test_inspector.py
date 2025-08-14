import os
import unittest
from unittest.mock import patch, MagicMock

# Use a sharable in-memory SQLite database for testing across threads
os.environ["DATABASE_URL"] = (
    "sqlite:///file:memdb1?mode=memory&cache=shared&uri=true"
)

from contextlib import contextmanager
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine

from src.xstate_statemachine import create_machine
from src.xstate_statemachine.inspector.plugin import InspectorPlugin
from src.xstate_statemachine.inspector.server import (
    create_app,
    get_db,
    message_queue,
)
from src.xstate_statemachine.inspector.db import EventLog

# --- Test Database Setup ---
# Use the same sharable in-memory database URI
engine = create_engine(
    "sqlite:///file:memdb1?mode=memory&cache=shared&uri=true",
    connect_args={"check_same_thread": False},
)


@contextmanager
def get_test_session_cm():
    """A context manager for providing a test database session."""
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()


def override_get_db():
    """Dependency override to use the testing database session."""
    with get_test_session_cm() as session:
        yield session


class TestInspector(unittest.TestCase):

    def setUp(self):
        app = create_app(mount_static_files=False)
        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

        # Clear the message queue before each test
        while not message_queue.empty():
            message_queue.get()

        # Recreate the database for each test to ensure isolation
        SQLModel.metadata.drop_all(bind=engine)
        SQLModel.metadata.create_all(bind=engine)

    @patch("src.xstate_statemachine.inspector.plugin.start_inspector_server")
    def test_plugin_init_starts_server(self, mock_start_server):
        InspectorPlugin(session_factory=get_test_session_cm)
        mock_start_server.assert_called_once()

    @patch("src.xstate_statemachine.inspector.plugin.start_inspector_server")
    @patch("src.xstate_statemachine.inspector.plugin.message_queue.put")
    def test_handle_inspection_event(self, mock_queue_put, mock_start_server):
        from sqlmodel import select

        plugin = InspectorPlugin(session_factory=get_test_session_cm)
        mock_interpreter = MagicMock()
        mock_interpreter.id = "test_machine"

        plugin._handle_inspection_event("test_event", mock_interpreter, {})

        mock_queue_put.assert_called_once()
        with get_test_session_cm() as session:
            results = session.exec(select(EventLog)).all()
            self.assertEqual(len(results), 1)

    @patch("src.xstate_statemachine.inspector.plugin.start_inspector_server")
    def test_full_flow_and_api_endpoints(self, mock_start_server):
        inspector = InspectorPlugin(session_factory=get_test_session_cm)
        light_switch_machine = create_machine(
            {
                "id": "light_switch",
                "initial": "off",
                "context": {"flips": 0},
                "states": {
                    "off": {"on": {"TOGGLE": "on"}},
                    "on": {"on": {"TOGGLE": "off"}},
                },
            }
        )
        mock_interpreter = MagicMock()
        mock_interpreter.id = "light_switch"
        mock_interpreter.context = {"flips": 0}
        mock_interpreter.current_states = {MagicMock(id="light_switch.off")}
        mock_interpreter.machine.to_dict.return_value = (
            light_switch_machine.to_dict()
        )

        inspector.on_interpreter_start(mock_interpreter)

        mock_interpreter.context = {"flips": 1}
        inspector.on_transition(
            mock_interpreter,
            {MagicMock(id="light_switch.off")},
            {MagicMock(id="light_switch.on")},
            MagicMock(event="TOGGLE"),
        )

        response = self.client.get("/api/sessions")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), ["light_switch"])

        response = self.client.get("/api/history/light_switch")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)

    @patch("src.xstate_statemachine.inspector.plugin.start_inspector_server")
    def test_websocket_connection(self, mock_start_server):
        with self.client.websocket_connect("/ws") as websocket:
            self.assertIsNotNone(websocket)

    @patch("src.xstate_statemachine.inspector.plugin.start_inspector_server")
    def test_api_get_history_for_nonexistent_session(self, mock_start_server):
        """Test that the API returns an empty list for a non-existent session."""
        response = self.client.get("/api/history/nonexistent_session")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    @patch("src.xstate_statemachine.inspector.plugin.start_inspector_server")
    def test_context_diffing(self, mock_start_server):
        """Test the context diffing logic with various changes."""
        inspector = InspectorPlugin(session_factory=get_test_session_cm)
        mock_interpreter = MagicMock()
        mock_interpreter.id = "diff_machine"
        mock_interpreter.context = {"a": 1, "b": 2}

        # Simulate event received to cache the initial context
        inspector.on_event_received(mock_interpreter, MagicMock())

        # Simulate context changes
        mock_interpreter.context = {
            "a": 1,
            "b": 3,
            "c": 4,
        }  # 'b' changed, 'c' added

        with patch.object(
            inspector, "_handle_inspection_event"
        ) as mock_handle:
            inspector.on_transition(
                mock_interpreter,
                {MagicMock()},
                {MagicMock()},
                MagicMock(event="EVENT"),
            )
            mock_handle.assert_called_once()
            args, _ = mock_handle.call_args
            payload = args[2]
            diff = payload["context_diff"]

            self.assertEqual(diff["added"], {"c": 4})
            self.assertEqual(diff["changed"], {"b": {"old": 2, "new": 3}})
            self.assertEqual(diff["removed"], {})

    # A new test class for the ConnectionManager is not strictly necessary as it is
    # simple and implicitly tested via the websocket tests, but can be added for completeness.
    # For now, adding more tests to the main class provides more value.

    @patch("src.xstate_statemachine.inspector.plugin.start_inspector_server")
    def test_websocket_command_pause_resume(self, mock_start_server):
        """Test that sending pause/resume commands over WebSocket works."""
        # This test needs a real interpreter to be registered
        from src.xstate_statemachine.inspector.server import (
            active_interpreters,
        )
        from src.xstate_statemachine.base_interpreter import BaseInterpreter
        import time

        # We need to mock the interpreter that would be registered by the plugin
        interpreter = MagicMock(spec=BaseInterpreter)
        interpreter.id = "test_ws_cmd"

        active_interpreters[interpreter.id] = interpreter

        with self.client.websocket_connect("/ws") as websocket:
            # Test Pause
            websocket.send_json(
                {"command": "pause", "machine_id": "test_ws_cmd"}
            )
            # Give a moment for the server to process
            time.sleep(0.01)
            interpreter.pause.assert_called_once()

            # Test Resume
            websocket.send_json(
                {"command": "resume", "machine_id": "test_ws_cmd"}
            )
            time.sleep(0.01)
            interpreter.resume.assert_called_once()

        # Clean up
        active_interpreters.pop("test_ws_cmd", None)

    @patch("src.xstate_statemachine.inspector.plugin.start_inspector_server")
    def test_websocket_invalid_command(self, mock_start_server):
        """Test that sending an invalid command over WebSocket is ignored."""
        with self.client.websocket_connect("/ws") as websocket:
            websocket.send_json(
                {"command": "invalid_command", "machine_id": "test_ws_cmd"}
            )
            # No error should be raised. The server should just ignore it.
            # We can't easily assert that nothing happened, but we can assert
            # that the connection is still open.
            websocket.send_json({"command": "ping"})  # send another message

    @patch("src.xstate_statemachine.inspector.plugin.start_inspector_server")
    def test_websocket_command_for_nonexistent_machine(
        self, mock_start_server
    ):
        """Test that a command for a non-existent machine is ignored."""
        with self.client.websocket_connect("/ws") as websocket:
            websocket.send_json(
                {"command": "pause", "machine_id": "nonexistent"}
            )
            # No error should be raised.
            websocket.send_json({"command": "ping"})


if __name__ == "__main__":
    unittest.main()


class TestInspectorPluginPayloads(unittest.TestCase):
    def setUp(self):
        from src.xstate_statemachine.base_interpreter import BaseInterpreter

        self.plugin = InspectorPlugin(session_factory=get_test_session_cm)
        self.mock_interpreter = MagicMock(spec=BaseInterpreter)
        self.mock_interpreter.id = "test_payload_machine"

        # Recreate the database for each test to ensure isolation
        SQLModel.metadata.drop_all(bind=engine)
        SQLModel.metadata.create_all(bind=engine)

    @patch("src.xstate_statemachine.inspector.plugin.start_inspector_server")
    def test_on_action_execute_payload(self, mock_start_server):
        """Verify the payload for the on_action_execute hook."""
        from src.xstate_statemachine.models import ActionDefinition

        action_def = ActionDefinition("my_action")

        with patch.object(
            self.plugin, "_handle_inspection_event"
        ) as mock_handle:
            self.plugin.on_action_execute(self.mock_interpreter, action_def)
            mock_handle.assert_called_once()
            args, _ = mock_handle.call_args
            self.assertEqual(args[0], "action_executed")
            self.assertEqual(args[2]["action"], "my_action")

    @patch("src.xstate_statemachine.inspector.plugin.start_inspector_server")
    def test_on_guard_evaluated_payload(self, mock_start_server):
        """Verify the payload for the on_guard_evaluated hook."""
        from src.xstate_statemachine.events import Event

        event = Event("SOME_EVENT")

        with patch.object(
            self.plugin, "_handle_inspection_event"
        ) as mock_handle:
            self.plugin.on_guard_evaluated(
                self.mock_interpreter, "my_guard", event, True
            )
            mock_handle.assert_called_once()
            args, _ = mock_handle.call_args
            self.assertEqual(args[0], "guard_evaluated")
            payload = args[2]
            self.assertEqual(payload["guard"], "my_guard")
            self.assertEqual(payload["event"], "SOME_EVENT")
            self.assertTrue(payload["result"])

    @patch("src.xstate_statemachine.inspector.plugin.start_inspector_server")
    def test_on_service_start_payload(self, mock_start_server):
        """Verify the payload for the on_service_start hook."""
        from src.xstate_statemachine.models import InvokeDefinition

        invoke_def = MagicMock(spec=InvokeDefinition)
        invoke_def.src = "my_service"
        invoke_def.id = "my_service_id"

        with patch.object(
            self.plugin, "_handle_inspection_event"
        ) as mock_handle:
            self.plugin.on_service_start(self.mock_interpreter, invoke_def)
            mock_handle.assert_called_once()
            args, _ = mock_handle.call_args
            self.assertEqual(args[0], "service_started")
            payload = args[2]
            self.assertEqual(payload["service"], "my_service")
            self.assertEqual(payload["id"], "my_service_id")

    @patch("src.xstate_statemachine.inspector.plugin.start_inspector_server")
    def test_on_service_done_payload(self, mock_start_server):
        """Verify the payload for the on_service_done hook."""
        from src.xstate_statemachine.models import InvokeDefinition

        invoke_def = MagicMock(spec=InvokeDefinition)
        invoke_def.src = "my_service"
        invoke_def.id = "my_service_id"
        result = {"data": "success"}

        with patch.object(
            self.plugin, "_handle_inspection_event"
        ) as mock_handle:
            self.plugin.on_service_done(
                self.mock_interpreter, invoke_def, result
            )
            mock_handle.assert_called_once()
            args, _ = mock_handle.call_args
            self.assertEqual(args[0], "service_done")
            payload = args[2]
            self.assertEqual(payload["service"], "my_service")
            self.assertEqual(payload["id"], "my_service_id")
            self.assertEqual(payload["result"], result)

    @patch("src.xstate_statemachine.inspector.plugin.start_inspector_server")
    def test_on_service_error_payload(self, mock_start_server):
        """Verify the payload for the on_service_error hook."""
        from src.xstate_statemachine.models import InvokeDefinition

        invoke_def = MagicMock(spec=InvokeDefinition)
        invoke_def.src = "my_service"
        invoke_def.id = "my_service_id"
        error = ValueError("service failed")

        with patch.object(
            self.plugin, "_handle_inspection_event"
        ) as mock_handle:
            self.plugin.on_service_error(
                self.mock_interpreter, invoke_def, error
            )
            mock_handle.assert_called_once()
            args, _ = mock_handle.call_args
            self.assertEqual(args[0], "service_error")
            payload = args[2]
            self.assertEqual(payload["service"], "my_service")
            self.assertEqual(payload["id"], "my_service_id")
            self.assertEqual(payload["error"], str(error))
