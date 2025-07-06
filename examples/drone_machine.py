import asyncio
import logging

from src.xstate_machine import Interpreter, MachineLogic, create_machine

# Configure logging for the application
logging.basicConfig(
    level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s"
)


async def main():
    # 1. Define the state machine in XState JSON format
    drone_config = {
        "id": "drone",
        "initial": "idle",
        "context": {"battery": 100},
        "states": {
            "idle": {"on": {"TAKEOFF": "flying"}},
            "flying": {
                "after": {
                    "5000": {
                        "target": "landing",
                        "actions": ["logLowBattery"],
                    }
                },
                "on": {"LAND": "landing"},
            },
            "landing": {"type": "final"},
        },
    }

    # 2. Provide the implementation for your actions
    logic = MachineLogic(
        actions={
            # ⬇️ FIX: Update the lambda to accept the fourth `action_def` argument ⬇️
            "logLowBattery": lambda interpreter, ctx, evt, action_def: print(
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
