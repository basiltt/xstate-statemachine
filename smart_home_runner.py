# # -------------------------------------------------------------------------------
# # 📡 Generated Runner File
# # -------------------------------------------------------------------------------
# from pathlib import Path
# import json
# from xstate_statemachine import LoggingInspector
# from xstate_statemachine import create_machine, Interpreter
# import logging
# import asyncio
#
# from smart_home_logic import SmartHomeLogic as LogicProvider
# from xstate_statemachine.inspector.plugin import InspectorPlugin
#
# # -----------------------------------------------------------------------------
# # 🧾 Logger Configuration
# # -----------------------------------------------------------------------------
# logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
# logger = logging.getLogger(__name__)
#
# async def main() -> None:
#     """Executes the simulation for the smart_home machine."""
#     # 📂 1. Configuration Loading
#     # ---------------------------------------------------------------------------
#     config_path = Path(r"smarthome.json")
#     if not config_path.is_absolute() and config_path.parent == Path('.'):
#         here = Path(__file__).resolve().parent
#         candidate = here / config_path.name
#         config_path = candidate if candidate.exists() else here.parent / config_path.name
#     with open(config_path, 'r', encoding='utf-8') as f:
#         config = json.load(f)
#     # ---------------------------------------------------------------------------
#     # 🧠 2. Logic Binding
#     # ---------------------------------------------------------------------------
#     logic_provider = LogicProvider()
#     machine = create_machine(config, logic_providers=[logic_provider])
#     # ---------------------------------------------------------------------------
#     # ⚙️  3. Interpreter Setup
#     # ---------------------------------------------------------------------------
#     interpreter = (
#         Interpreter(machine)
#         .use(LoggingInspector())
#         .use(InspectorPlugin())
#     )
#     await interpreter.start()
#
#     # interpreter = Interpreter(machine)
#     # # Attach both plugins to it
#     # interpreter.use(LoggingInspector())
#     # interpreter.use(InspectorPlugin())
#     # await interpreter.start()
#     logger.info(f'Initial state: {interpreter.current_state_ids}')
#     interpreter.pause()
#     # ---------------------------------------------------------------------------
#     # 🚀 4. Simulation Scenario
#     # ---------------------------------------------------------------------------
#     # ▶️ Enable
#     logger.info('→ Sending event: %s', 'ENABLE')
#     await interpreter.send('ENABLE')
#     await asyncio.sleep(2)
#
#     # ▶️ Power Down
#     logger.info('→ Sending event: %s', 'POWER_DOWN')
#     await interpreter.send('POWER_DOWN')
#     await asyncio.sleep(2)
#
#     await interpreter.stop()
#
#
# if __name__ == '__main__':
#     asyncio.run(main())


import asyncio
import json
import logging
from pathlib import Path
from xstate_statemachine import (
    create_machine,
    Interpreter,
    LoggingInspector,
    MachineLogic,
)

from smart_home_logic import SmartHomeLogic
from xstate_statemachine.inspector.plugin import InspectorPlugin

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Initializes the SmartHome machine and keeps it running for inspection."""
    here = Path(__file__).resolve().parent

    # 1. Load all machine configurations
    parent_config = json.loads((here / "smarthome.json").read_text())
    thermostat_config = json.loads((here / "thermostat.json").read_text())
    lightbulb_config = {
        "id": "LightBulb",
        "initial": "off",
        "states": {
            "off": {"after": {"500": "on"}},
            "on": {"after": {"500": "off"}},
        },
    }

    # 2. Create MachineNode instances for the actors
    thermostat_machine = create_machine(thermostat_config)
    lightbulb_machine = create_machine(lightbulb_config)

    # 3. Create the parent machine's logic, injecting actors as services
    logic_provider = SmartHomeLogic()
    logic = MachineLogic(
        actions={
            "logPowerOn": logic_provider.log_power_on,
            "logPowerOff": logic_provider.log_power_off,
        },
        services={
            "LightBulb": lightbulb_machine,
            "Thermostat": thermostat_machine,
        },
    )

    machine = create_machine(parent_config, logic=logic)

    # 4. Setup the interpreter with the inspector
    interpreter = (
        Interpreter(machine).use(LoggingInspector()).use(InspectorPlugin())
    )

    # 5. Start the machine and wait indefinitely for UI interaction
    print("\n🚀 Starting state machine and inspector...")
    print("✅ Inspector is running at http://127.0.0.1:8008\n")

    # Start the machine in a paused state so you can control it from the UI
    await interpreter.start(paused=True)

    logger.info(
        f"Machine '{interpreter.id}' is running but PAUSED. Initial state: {interpreter.current_state_ids}."
    )
    logger.info("Use the web UI to resume, pause, and send events.")

    try:
        # This keeps the script, and thus the inspector server, running forever.
        await asyncio.Event().wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("\n🛑 Shutting down...")
        await interpreter.stop()
        logger.info("✅ Shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())
