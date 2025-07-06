# examples/tape_recorder_machine.py
import asyncio
import json
import logging
from typing import Any, Dict

from src.xstate_machine import (
    Event,
    Interpreter,
    LoggingInspector,
    MachineLogic,
    create_machine,
)
from src.xstate_machine.models import ActionDefinition

# -----------------------------------------------------------------------------
# 🪵 Logging Configuration
# -----------------------------------------------------------------------------
# This demonstrates how an application using the `xstate-machine` library
# can configure its own logging to see output from the library.
# -----------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s"
)


# -----------------------------------------------------------------------------
# 📼 Tape Recorder Class
# -----------------------------------------------------------------------------
# This class encapsulates all the logic and state for a tape recorder,
# demonstrating a class-based approach to state machine implementation. The class
# holds the state (e.g., `self.mic_stream`) and the behavioral logic (the
# action and service methods), while the state machine definition (the "what")
# is loaded entirely from an external JSON file.
# -----------------------------------------------------------------------------


class TapeRecorder:
    """A class that implements the logic for the TapeRecorder state machine."""

    def __init__(self):
        """Initializes the TapeRecorder instance.

        This constructor performs all necessary setup:
        1. Loads the state machine definition from `TapeRecorder.json`.
        2. Creates a `MachineLogic` object that maps the action and service
           names from the JSON to the methods of this class instance.
        3. Creates the state machine and the interpreter that will run it.
        """
        # 📝 Instance variables to hold mock resources.
        self.mic_stream: Any = None
        self.file_writer: Any = None

        # 📜 Load the machine definition from the JSON file.
        with open("TapeRecorder.json") as f:
            recorder_config = json.load(f)

        # 🧠 Define the implementation logic by binding strings from the JSON
        # to the methods of this class instance.
        recorder_logic = MachineLogic(
            actions={
                "assign mic": self.assign_mic_action,
                "assign file": self.assign_file_action,
                "context_do": self.context_do_action,
                "console_error": self.console_error_action,
            },
            services={
                "MediaRecorderStream_actor": self.media_recorder_actor,
                "FileWriterStream_actor": self.file_writer_actor,
                "pipeTo_actor": self.pipe_to_actor,
            },
        )

        # 🚀 Create and store the interpreter instance.
        recorder_machine = create_machine(recorder_config, recorder_logic)
        self.interpreter = Interpreter(recorder_machine)
        self.interpreter.use(LoggingInspector())

    # -------------------------------------------------------------------------
    # Action Implementations
    # -------------------------------------------------------------------------

    def assign_mic_action(
        self,
        interpreter: Interpreter,
        context: Dict,
        event: Event,
        action: ActionDefinition,
    ) -> None:
        """Assigns the mock microphone stream from the event payload to the context."""
        print("🎤 Microphone assigned to context.")
        context["mic"] = event.payload.get("stream")

    def assign_file_action(
        self,
        interpreter: Interpreter,
        context: Dict,
        event: Event,
        action: ActionDefinition,
    ) -> None:
        """Assigns the mock file writer from the event payload to the context."""
        print("📄 File handle assigned to context.")
        context["file"] = event.payload.get("writer")

    def context_do_action(
        self,
        interpreter: Interpreter,
        context: Dict,
        event: Event,
        action: ActionDefinition,
    ) -> None:
        """A generic action that simulates calling a method on a context object."""
        # ✨ FIX: Use the `action` argument directly to get the params.
        params = action.params
        target_name = params.get("assign")
        method_name = params.get("name")
        target_obj = context.get(target_name)

        if target_obj and hasattr(target_obj, method_name):
            print(f"🎶 Calling '{method_name}' on '{target_name}'...")
            getattr(target_obj, method_name)()

    def console_error_action(
        self,
        interpreter: Interpreter,
        context: Dict,
        event: Event,
        action: ActionDefinition,
    ) -> None:
        """Logs an error event to the console."""
        print(f"❌ An error occurred: {event.data}")

    # -------------------------------------------------------------------------
    # Service (Actor) Implementations
    # -------------------------------------------------------------------------

    async def media_recorder_actor(
        self, interpreter: Interpreter, context: Dict, event: Event
    ) -> Dict:
        """Simulates acquiring a microphone stream asynchronously."""
        print("🎤 Actor: Acquiring microphone...")
        await asyncio.sleep(0.5)

        self.mic_stream = type(
            "MicStream",
            (),
            {
                "start": lambda: print("  ▶️ Mic stream started recording."),
                "stop": lambda: print("  ⏹️ Mic stream stopped recording."),
                "pause": lambda: print("  ⏸️ Mic stream paused."),
                "resume": lambda: print("  ⏯️ Mic stream resumed."),
            },
        )()

        # ✨ FIX: Access the invocation input from the event's payload.
        event_name = f"ok_{event.payload['input']['fixme1']}"
        await interpreter.send(event_name, stream=self.mic_stream)
        return {"status": "microphone ready"}

    async def file_writer_actor(
        self, interpreter: Interpreter, context: Dict, event: Event
    ) -> Dict:
        """Simulates creating/opening a file for writing asynchronously."""
        print("📄 Actor: Opening file for writing...")
        await asyncio.sleep(1.0)
        self.file_writer = {"path": "out.weba"}

        # ✨ FIX: Access the invocation input from the event's payload.
        event_name = f"ok_{event.payload['input']['fixme1']}"
        await interpreter.send(event_name, writer=self.file_writer)
        return {"status": "file ready"}

    async def pipe_to_actor(
        self, interpreter: Interpreter, context: Dict, event: Event
    ) -> Dict:
        """Simulates the process of piping audio data to the file.

        Args:
            interpreter: The interpreter instance invoking this service.
            context: The current context of the state machine.
            event: The `invoke` event.

        Returns:
            A dictionary indicating the result of the operation.
        """
        print("💾 Actor: Saving audio data to file...")
        await asyncio.sleep(2)
        print("✅ Actor: Saving complete.")
        await interpreter.send("done")
        return {"bytesWritten": 1024}


# -----------------------------------------------------------------------------
# 🚀 Main Simulation
# -----------------------------------------------------------------------------


async def main():
    """Initializes and runs the TapeRecorder simulation."""
    print("🎬 --- Tape Recorder Simulation (Class-Based) --- 🎬\n")

    # 1. Instantiate the main class. It handles all setup internally.
    tape_recorder = TapeRecorder()

    # 2. Start the machine.
    await tape_recorder.interpreter.start()
    print(f"Initial State: {tape_recorder.interpreter.current_state_ids}\n")

    # 3. Send an event to start recording.
    print("--- ➡️  User presses START ---")
    await tape_recorder.interpreter.send("action_start")

    # The machine is now in the parallel 'acquiring' state, waiting for both
    # the mic and file actors to complete their async work.
    await asyncio.sleep(1.5)
    print(
        f"\n✅ Machine is now recording. Current State: {tape_recorder.interpreter.current_state_ids}\n"
    )

    # 4. Send a pause and resume event.
    print("--- ⏸️  User presses PAUSE ---")
    await tape_recorder.interpreter.send("action_pause")
    await asyncio.sleep(1)
    print(f"Current State: {tape_recorder.interpreter.current_state_ids}\n")

    print("--- ⏯️  User presses RESUME ---")
    await tape_recorder.interpreter.send("action_resume")
    await asyncio.sleep(1)
    print(f"Current State: {tape_recorder.interpreter.current_state_ids}\n")

    # 5. Send an event to stop recording.
    print("--- ⏹️  User presses STOP ---")
    await tape_recorder.interpreter.send("action_stop")

    # The machine will now be in the 'saving' state, waiting for the pipeTo actor.
    await asyncio.sleep(2.5)

    print("\n--- 🏁 SIMULATION COMPLETE ---")
    print(f"Final State: {tape_recorder.interpreter.current_state_ids}")

    await tape_recorder.interpreter.stop()


if __name__ == "__main__":
    asyncio.run(main())
