import os
import unittest
from unittest.mock import patch, MagicMock

# Use a sharable in-memory SQLite database for testing across threads
os.environ["DATABASE_URL"] = "sqlite:///file:memdb1?mode=memory&cache=shared&uri=true"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.xstate_statemachine import create_machine
from src.xstate_statemachine.inspector.plugin import InspectorPlugin
from src.xstate_statemachine.inspector.server import create_app, get_db, message_queue
from src.xstate_statemachine.inspector.db import Base, EventLog

# --- Test Database Setup ---
# Use the same sharable in-memory database URI
engine = create_engine(
    "sqlite:///file:memdb1?mode=memory&cache=shared&uri=true",
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    """Dependency override to use the testing database session."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

class TestInspector(unittest.TestCase):

    def setUp(self):
        app = create_app(mount_static_files=False)
        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

        while not message_queue.empty():
            message_queue.get()

        db = TestingSessionLocal()
        db.query(EventLog).delete()
        db.commit()
        db.close()

    @patch('src.xstate_statemachine.inspector.plugin.start_inspector_server')
    def test_plugin_init_starts_server(self, mock_start_server):
        InspectorPlugin()
        mock_start_server.assert_called_once()

    @patch('src.xstate_statemachine.inspector.plugin.start_inspector_server')
    @patch('src.xstate_statemachine.inspector.plugin.message_queue.put')
    def test_handle_inspection_event(self, mock_queue_put, mock_start_server):
        plugin = InspectorPlugin(session_factory=TestingSessionLocal)
        mock_interpreter = MagicMock()
        mock_interpreter.id = "test_machine"

        plugin._handle_inspection_event("test_event", mock_interpreter, {})

        mock_queue_put.assert_called_once()
        db = TestingSessionLocal()
        self.assertEqual(db.query(EventLog).count(), 1)
        db.close()

    @patch('src.xstate_statemachine.inspector.plugin.start_inspector_server')
    def test_full_flow_and_api_endpoints(self, mock_start_server):
        inspector = InspectorPlugin(session_factory=TestingSessionLocal)
        light_switch_machine = create_machine({
            "id": "light_switch", "initial": "off", "context": {"flips": 0},
            "states": {"off": {"on": {"TOGGLE": "on"}}, "on": {"on": {"TOGGLE": "off"}}}
        })
        mock_interpreter = MagicMock()
        mock_interpreter.id = "light_switch"
        mock_interpreter.context = {"flips": 0}
        mock_interpreter.current_states = {MagicMock(id="light_switch.off")}
        mock_interpreter.machine.to_dict.return_value = light_switch_machine.to_dict()

        inspector.on_interpreter_start(mock_interpreter)

        mock_interpreter.context = {"flips": 1}
        inspector.on_transition(
            mock_interpreter,
            {MagicMock(id="light_switch.off")},
            {MagicMock(id="light_switch.on")},
            MagicMock(event="TOGGLE")
        )

        response = self.client.get("/api/sessions")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), ["light_switch"])

        response = self.client.get("/api/history/light_switch")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)

    @patch('src.xstate_statemachine.inspector.plugin.start_inspector_server')
    def test_websocket_connection(self, mock_start_server):
        with self.client.websocket_connect("/ws") as websocket:
            self.assertIsNotNone(websocket)

    @patch('src.xstate_statemachine.inspector.plugin.start_inspector_server')
    def test_api_get_history_for_nonexistent_session(self, mock_start_server):
        """Test that the API returns an empty list for a non-existent session."""
        response = self.client.get("/api/history/nonexistent_session")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    @patch('src.xstate_statemachine.inspector.plugin.start_inspector_server')
    def test_context_diffing(self, mock_start_server):
        """Test the context diffing logic with various changes."""
        inspector = InspectorPlugin(session_factory=TestingSessionLocal)
        mock_interpreter = MagicMock()
        mock_interpreter.id = "diff_machine"
        mock_interpreter.context = {"a": 1, "b": 2}

        # Simulate event received to cache the initial context
        inspector.on_event_received(mock_interpreter, MagicMock())

        # Simulate context changes
        mock_interpreter.context = {"a": 1, "b": 3, "c": 4} # 'b' changed, 'c' added

        with patch.object(inspector, '_handle_inspection_event') as mock_handle:
            inspector.on_transition(
                mock_interpreter,
                {MagicMock()}, {MagicMock()}, MagicMock(event="EVENT")
            )
            mock_handle.assert_called_once()
            args, _ = mock_handle.call_args
            payload = args[2]
            diff = payload['context_diff']

            self.assertEqual(diff['added'], {"c": 4})
            self.assertEqual(diff['changed'], {"b": {"old": 2, "new": 3}})
            self.assertEqual(diff['removed'], {})

# A new test class for the ConnectionManager is not strictly necessary as it is
# simple and implicitly tested via the websocket tests, but can be added for completeness.
# For now, adding more tests to the main class provides more value.

if __name__ == "__main__":
    unittest.main()
