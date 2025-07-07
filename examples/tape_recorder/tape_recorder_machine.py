import asyncio
import json
import logging
from typing import Any, Dict

from src.xstate_statemachine import (
    Event,
    Interpreter,
    LoggingInspector,
    MachineLogic,
    create_machine,
)
from src.xstate_statemachine.models import ActionDefinition

# -----------------------------------------------------------------------------
# 📚 File Overview
# -----------------------------------------------------------------------------
# This file implements a Tape Recorder simulation using the `xstate-machine`
# library. It demonstrates a class-based approach where the state machine
# definition is loaded from an external JSON file (`TapeRecorder.json`),
# and the corresponding actions and services are implemented as methods
# within the `TapeRecorder` class.
#
# The simulation showcases asynchronous operations for acquiring resources
# (microphone, file handles) and processing data, along with state transitions
# triggered by user actions like start, pause, resume, and stop.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# 🪵 Logging Configuration
# -----------------------------------------------------------------------------
# This configures the application's logging to display messages from the
# `xstate-machine` library and the application itself.
# -----------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


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
    """
    A class that implements the logic for the TapeRecorder state machine.

    This class manages the state and behavior of a simulated tape recorder,
    integrating with the `xstate-machine` library. It loads its state
    machine definition from a JSON file and maps state machine actions
    and services to its own methods.
    """

    def __init__(self) -> None:
        """
        Initializes the TapeRecorder instance.

        This constructor performs all necessary setup:
        1. Loads the state machine definition from `TapeRecorder.json`.
        2. Creates a `MachineLogic` object that maps the action and service
           names from the JSON to the methods of this class instance.
        3. Creates the state machine and the interpreter that will run it.
        """
        logger.info("🚀 Initializing TapeRecorder...")

        # 📝 Instance variables to hold mock resources.
        self.mic_stream: Any = None
        self.file_writer: Any = None

        # 📜 Load the machine definition from the JSON file.
        try:
            with open("TapeRecorder.json", "r") as f:
                recorder_config: Dict[str, Any] = json.load(f)
            logger.info(
                "✅ TapeRecorder machine configuration loaded successfully."
            )
        except FileNotFoundError:
            logger.error(
                "❌ TapeRecorder.json not found. Please ensure it's in the same directory."
            )
            raise
        except json.JSONDecodeError:
            logger.error(
                "❌ TapeRecorder.json is malformed. Please check its syntax."
            )
            raise

        # 🧠 Define the implementation logic by binding strings from the JSON
        # to the methods of this class instance. This establishes the
        # separation of concerns between state definition (JSON) and
        # implementation details (Python methods).
        recorder_logic = MachineLogic(
            actions={
                "assign mic": self._assign_mic_action,
                "assign file": self._assign_file_action,
                "context_do": self._context_do_action,
                "console_error": self._console_error_action,
            },
            services={
                "MediaRecorderStream_actor": self._media_recorder_actor,
                "FileWriterStream_actor": self._file_writer_actor,
                "pipeTo_actor": self._pipe_to_actor,
            },
        )
        logger.info("✅ Machine logic mapped to TapeRecorder methods.")

        # 🚀 Create and store the interpreter instance.
        recorder_machine = create_machine(recorder_config, recorder_logic)
        self.interpreter: Interpreter = Interpreter(recorder_machine)
        self.interpreter.use(LoggingInspector())
        logger.info(
            "✅ State machine interpreter created and configured with logging inspector."
        )

    # -------------------------------------------------------------------------
    # ⚙️ Action Implementations
    # -------------------------------------------------------------------------

    def _assign_mic_action(
        self,
        interpreter: Interpreter,
        context: Dict[str, Any],
        event: Event,
        action: ActionDefinition,
    ) -> None:
        """
        Assigns the mock microphone stream from the event payload to the context.

        Args:
            interpreter (Interpreter): The interpreter instance.
            context (Dict[str, Any]): The current context of the state machine.
            event (Event): The event that triggered this action.
            action (ActionDefinition): The definition of the action being executed.
        """
        stream = event.payload.get("stream")
        if stream:
            context["mic"] = stream
            logger.info("🎤 Microphone assigned to context.")
        else:
            logger.warning(
                "⚠️ No microphone stream found in event payload for assignment."
            )

    def _assign_file_action(
        self,
        interpreter: Interpreter,
        context: Dict[str, Any],
        event: Event,
        action: ActionDefinition,
    ) -> None:
        """
        Assigns the mock file writer from the event payload to the context.

        Args:
            interpreter (Interpreter): The interpreter instance.
            context (Dict[str, Any]): The current context of the state machine.
            event (Event): The event that triggered this action.
            action (ActionDefinition): The definition of the action being executed.
        """
        writer = event.payload.get("writer")
        if writer:
            context["file"] = writer
            logger.info("📄 File handle assigned to context.")
        else:
            logger.warning(
                "⚠️ No file writer found in event payload for assignment."
            )

    def _context_do_action(
        self,
        interpreter: Interpreter,
        context: Dict[str, Any],
        event: Event,
        action: ActionDefinition,
    ) -> None:
        """
        A generic action that simulates calling a method on a context object.

        This action uses parameters defined in the state machine's action
        definition to dynamically call methods on objects stored in the context.

        Args:
            interpreter (Interpreter): The interpreter instance.
            context (Dict[str, Any]): The current context of the state machine.
            event (Event): The event that triggered this action.
            action (ActionDefinition): The definition of the action being executed.
        """
        params: Dict[str, Any] = action.params if action.params else {}
        target_name: str = params.get("assign", "")
        method_name: str = params.get("name", "")

        target_obj: Any = context.get(target_name)

        if target_obj and hasattr(target_obj, method_name):
            logger.info(f"🎶 Calling '{method_name}' on '{target_name}'...")
            try:
                getattr(target_obj, method_name)()
                logger.info(
                    f"✅ Successfully called '{method_name}' on '{target_name}'."
                )
            except Exception as e:
                logger.error(
                    f"❌ Error calling '{method_name}' on '{target_name}': {e}"
                )
        else:
            logger.warning(
                f"⚠️ Could not call method '{method_name}' on '{target_name}'. "
                "Target object or method not found."
            )

    def _console_error_action(
        self,
        interpreter: Interpreter,
        context: Dict[str, Any],
        event: Event,
        action: ActionDefinition,
    ) -> None:
        """
        Logs an error event to the console.

        Args:
            interpreter (Interpreter): The interpreter instance.
            context (Dict[str, Any]): The current context of the state machine.
            event (Event): The error event containing data about the error.
            action (ActionDefinition): The definition of the action being executed.
        """
        logger.error(f"❌ An error occurred in state machine: {event.data}")

    # -------------------------------------------------------------------------
    # 🎭 Service (Actor) Implementations
    # -------------------------------------------------------------------------

    async def _media_recorder_actor(
        self, interpreter: Interpreter, context: Dict[str, Any], event: Event
    ) -> Dict[str, Any]:
        """
        Simulates acquiring a microphone stream asynchronously.

        Args:
            interpreter (Interpreter): The interpreter instance invoking this service.
            context (Dict[str, Any]): The current context of the state machine.
            event (Event): The `invoke` event that triggered this service.

        Returns:
            Dict[str, Any]: A dictionary indicating the status of the operation.
        """
        logger.info("🎤 Actor: Acquiring microphone stream...")
        await asyncio.sleep(0.5)  # Simulate asynchronous work

        # Create a mock microphone stream object with callable methods.
        # This demonstrates dynamically creating an object with specific behaviors.
        self.mic_stream = type(
            "MicStream",
            (),
            {
                "start": lambda self_instance: logger.info(
                    "  ▶️ Mic stream started recording."
                ),
                "stop": lambda self_instance: logger.info(
                    "  ⏹️ Mic stream stopped recording."
                ),
                "pause": lambda self_instance: logger.info(
                    "  ⏸️ Mic stream paused."
                ),
                "resume": lambda self_instance: logger.info(
                    "  ⏯️ Mic stream resumed."
                ),
            },
        )()
        logger.info("✅ Mock microphone stream acquired.")

        # Access the invocation input from the event's payload and send a success event.
        event_name = (
            f"ok_{event.payload.get('input', {}).get('fixme1', 'media_ready')}"
        )
        await interpreter.send(event_name, stream=self.mic_stream)
        logger.debug(f"✉️ Sent event: '{event_name}' with mic stream.")
        return {"status": "microphone ready"}

    async def _file_writer_actor(
        self, interpreter: Interpreter, context: Dict[str, Any], event: Event
    ) -> Dict[str, Any]:
        """
        Simulates creating/opening a file for writing asynchronously.

        Args:
            interpreter (Interpreter): The interpreter instance invoking this service.
            context (Dict[str, Any]): The current context of the state machine.
            event (Event): The `invoke` event that triggered this service.

        Returns:
            Dict[str, Any]: A dictionary indicating the status of the operation.
        """
        logger.info("📄 Actor: Opening file for writing...")
        await asyncio.sleep(1.0)  # Simulate asynchronous file I/O

        self.file_writer = {"path": "out.weba"}
        logger.info("✅ Mock file writer ready.")

        # Access the invocation input from the event's payload and send a success event.
        event_name = (
            f"ok_{event.payload.get('input', {}).get('fixme1', 'file_ready')}"
        )
        await interpreter.send(event_name, writer=self.file_writer)
        logger.debug(f"✉️ Sent event: '{event_name}' with file writer.")
        return {"status": "file ready"}

    async def _pipe_to_actor(
        self, interpreter: Interpreter, context: Dict[str, Any], event: Event
    ) -> Dict[str, Any]:
        """
        Simulates the process of piping audio data to the file.

        Args:
            interpreter (Interpreter): The interpreter instance invoking this service.
            context (Dict[str, Any]): The current context of the state machine.
            event (Event): The `invoke` event.

        Returns:
            Dict[str, Any]: A dictionary indicating the result of the operation.
        """
        logger.info("💾 Actor: Saving audio data to file...")
        await asyncio.sleep(2)  # Simulate data writing process
        logger.info("✅ Actor: Saving complete.")
        await interpreter.send("done")
        logger.debug("✉️ Sent event: 'done' after saving.")
        return {"bytesWritten": 1024}


# -----------------------------------------------------------------------------
# 🚀 Main Simulation
# -----------------------------------------------------------------------------


async def main() -> None:
    """
    Initializes and runs the TapeRecorder simulation.

    This function sets up the TapeRecorder, starts its state machine,
    and sends a sequence of events to simulate user interactions
    (start, pause, resume, stop recording).
    """
    logger.info(
        "🎬 --- Tape Recorder Simulation (Class-Based) Starting --- 🎬\n"
    )

    # 1. Instantiate the main class. It handles all setup internally.
    tape_recorder: TapeRecorder = TapeRecorder()

    # 2. Start the machine.
    await tape_recorder.interpreter.start()
    logger.info(
        f"Starting state machine. Initial State: {tape_recorder.interpreter.current_state_ids}\n"
    )

    # 3. Send an event to start recording.
    logger.info("--- ➡️  User presses START ---")
    await tape_recorder.interpreter.send("action_start")
    logger.info("✉️ Sent 'action_start' event.")

    # The machine is now in the parallel 'acquiring' state, waiting for both
    # the mic and file actors to complete their async work.
    await asyncio.sleep(1.5)
    logger.info(
        f"\n✅ Machine is now recording. Current State: {tape_recorder.interpreter.current_state_ids}\n"
    )

    # 4. Send a pause and resume event.
    logger.info("--- ⏸️  User presses PAUSE ---")
    await tape_recorder.interpreter.send("action_pause")
    logger.info("✉️ Sent 'action_pause' event.")
    await asyncio.sleep(1)
    logger.info(
        f"Current State after pause: {tape_recorder.interpreter.current_state_ids}\n"
    )

    logger.info("--- ⏯️  User presses RESUME ---")
    await tape_recorder.interpreter.send("action_resume")
    logger.info("✉️ Sent 'action_resume' event.")
    await asyncio.sleep(1)
    logger.info(
        f"Current State after resume: {tape_recorder.interpreter.current_state_ids}\n"
    )

    # 5. Send an event to stop recording.
    logger.info("--- ⏹️  User presses STOP ---")
    await tape_recorder.interpreter.send("action_stop")
    logger.info("✉️ Sent 'action_stop' event.")

    # The machine will now be in the 'saving' state, waiting for the pipeTo actor.
    await asyncio.sleep(2.5)

    logger.info("\n--- 🏁 SIMULATION COMPLETE ---")
    logger.info(f"Final State: {tape_recorder.interpreter.current_state_ids}")

    await tape_recorder.interpreter.stop()
    logger.info("🛑 State machine interpreter stopped.")


if __name__ == "__main__":
    asyncio.run(main())
