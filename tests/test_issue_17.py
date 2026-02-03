"""Test for issue #17: logic_providers camelCase to snake_case mapping."""

import asyncio
import unittest
from xstate_statemachine import create_machine, Interpreter, MachineLogic


class TestLogic:
    """Test logic class with snake_case method names."""

    async def store_job_params(self, interpreter, context, event, action_def):
        """Store job parameters - maps to 'storeJobParams' in JSON."""
        context["stored"] = True

    async def mark_started(self, interpreter, context, event, action_def):
        """Mark job as started - maps to 'markStarted' in JSON."""
        context["started"] = True

    async def validate_params(self, interpreter, context, event, action_def):
        """Validate parameters - maps to 'validateParams' in JSON."""
        context["validated"] = True
        # Send COMPLETE event to trigger transition
        await interpreter.send("COMPLETE")

    def can_retry(self, context, event) -> bool:
        """Guard: can retry - maps to 'canRetry' in JSON."""
        return True


class TestLogicProvidersCamelCase(unittest.IsolatedAsyncioTestCase):
    """Test that logic_providers properly maps camelCase JSON to snake_case Python."""

    def setUp(self):
        """Set up test machine config with camelCase action names."""
        self.config = {
            "id": "testMachine",
            "initial": "idle",
            "context": {"value": 0},
            "states": {
                "idle": {
                    "on": {
                        "START": {
                            "target": "running",
                            "actions": ["storeJobParams", "markStarted"],
                        }
                    }
                },
                "running": {
                    "entry": ["validateParams"],
                    "on": {"COMPLETE": {"target": "completed", "guard": "canRetry"}},
                },
                "completed": {"type": "final"},
            },
        }

    def test_logic_providers_camelcase_mapping(self):
        """Test that logic_providers auto-discovers camelCase JSON actions."""
        logic = TestLogic()

        # This should NOT raise ImplementationMissingError
        machine = create_machine(self.config, logic_providers=[logic])

        # Verify actions are bound
        self.assertIn("storeJobParams", machine.logic.actions)
        self.assertIn("markStarted", machine.logic.actions)
        self.assertIn("validateParams", machine.logic.actions)
        self.assertIn("canRetry", machine.logic.guards)

    async def test_logic_providers_full_execution(self):
        """Test full execution with logic_providers auto-discovery."""
        logic = TestLogic()

        # This should work end-to-end
        machine = create_machine(self.config, logic_providers=[logic])
        interpreter = Interpreter(machine)
        await interpreter.start()

        # Verify initial state
        self.assertIn("testMachine.idle", interpreter.current_state_ids)

        # Send START event
        await interpreter.send("START")

        # Allow time for async actions
        await asyncio.sleep(0.1)

        # Verify context was updated by actions
        self.assertTrue(interpreter.context.get("stored"))
        self.assertTrue(interpreter.context.get("started"))
        self.assertTrue(interpreter.context.get("validated"))

        # Verify final state
        self.assertIn("testMachine.completed", interpreter.current_state_ids)

        await interpreter.stop()


if __name__ == "__main__":
    unittest.main()
