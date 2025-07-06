# drone_machine.py
import asyncio

from src.xstate_machine import MachineLogic, create_machine, Interpreter

# In the user's main.py file
import logging

# Configure logging for their entire application
logging.basicConfig(
    level=logging.WARNING, format="[%(levelname)s] %(name)s: %(message)s"
)

# Specifically enable INFO-level logs just for your library
logging.getLogger("xstate_machine").setLevel(logging.INFO)


async def main():
    # 1. Define your state machine in XState JSON format
    drone_config = {
        "id": "drone",
        "initial": "idle",
        "context": {"battery": 100},
        "states": {
            "idle": {"on": {"TAKEOFF": {"target": "flying"}}},
            "flying": {
                "after": {
                    "5000": {
                        "target": "landing",
                        "actions": [{"type": "logLowBattery"}],
                    }
                },
                "on": {"LAND": {"target": "landing"}},
            },
            "landing": {"type": "final"},
        },
    }

    # 2. Provide the implementation for your actions
    logic = MachineLogic(
        actions={
            # ✨ FIX: Update the lambda to accept the `interpreter` argument.
            "logLowBattery": lambda interpreter, ctx, evt: print(
                f"🔋 Low battery ({ctx['battery']}%). Returning to land."
            )
        }
    )

    # 3. Create and run the machine
    machine = create_machine(drone_config, logic)
    interpreter = await Interpreter(machine).start()

    print(f"🚀 State: {interpreter.current_state_ids}")
    await interpreter.send("TAKEOFF")

    # Wait for the machine to enter the 'flying' state before printing
    await asyncio.sleep(0.1)
    print(f"🚀 State: {interpreter.current_state_ids}")

    # The 'after' transition will trigger automatically
    await asyncio.sleep(6)
    print(f"🚀 Final State: {interpreter.current_state_ids}")

    await interpreter.stop()


if __name__ == "__main__":
    asyncio.run(main())
