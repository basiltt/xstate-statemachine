import asyncio
import json
import logging
from xstate_statemachine import create_machine, Interpreter, LoggingInspector
from coffee_machine_logic import coffee_machine_logic

logging.basicConfig(level=logging.INFO)


async def run_coffee_machine_example():
    print("\n--- Initializing Coffee Machine Simulation ---")
    with open("coffee_machine.json", "r") as f:
        coffee_config = json.load(f)

    coffee_machine_node = create_machine(coffee_config, coffee_machine_logic)

    interpreter = await Interpreter(coffee_machine_node).start()
    interpreter.use(LoggingInspector())

    print(
        f"Initial state: {interpreter.current_state_ids} | Context: {interpreter.context}"
    )

    # --- Scenario 1: Make an Espresso ---
    print("\n--- Scenario 1: Making an Espresso ---")
    await interpreter.send("SELECT_ESPRESSO")
    print(
        f"Current state: {interpreter.current_state_ids} | Context: {interpreter.context}"
    )

    await interpreter.send("BREW")
    await asyncio.sleep(3.5)  # Wait a bit more than the 3-second brew time
    print(
        f"Current state: {interpreter.current_state_ids} | Context: {interpreter.context}"
    )

    await interpreter.send("TAKE_DRINK")
    print(
        f"Current state: {interpreter.current_state_ids} | Context: {interpreter.context}"
    )

    # --- Scenario 2: Make 5 more coffees to run out of water ---
    print("\n--- Scenario 2: Making 5 more coffees to run out of water ---")
    for i in range(5):
        print(f"\nMaking coffee #{interpreter.context['coffeeCount'] + 1}...")
        await interpreter.send("SELECT_LATTE")
        await interpreter.send("BREW")
        await asyncio.sleep(3.5)
        await interpreter.send("TAKE_DRINK")
        print(
            f"Current state: {interpreter.current_state_ids} | Context: {interpreter.context}"
        )

    # --- Scenario 3: Try to brew with no water ---
    print("\n--- Scenario 3: Trying to brew with no water (should fail) ---")
    await interpreter.send("SELECT_ESPRESSO")
    await interpreter.send(
        "BREW"
    )  # This should be blocked by the 'canBrew' guard due to low water
    print(
        f"Current state: {interpreter.current_state_ids} | Context: {interpreter.context}"
    )

    # --- Scenario 4: Refill Water ---
    print("\n--- Scenario 4: Refilling Water Tank ---")
    print(f"Current water level: {interpreter.context['waterLevel']}%")
    await interpreter.send("REFILL_WATER")
    print(
        f"Current state: {interpreter.current_state_ids} | Context: {interpreter.context}"
    )
    await asyncio.sleep(4.5)  # Wait a bit more than the 4-second refill time
    print(
        f"Current state: {interpreter.current_state_ids} | Context: {interpreter.context}"
    )

    # --- Scenario 5: Try brewing again after refill ---
    print(
        "\n--- Scenario 5: Trying to brew after refilling (should succeed) ---"
    )
    await interpreter.send("SELECT_LATTE")
    await interpreter.send("BREW")
    await asyncio.sleep(3.5)
    await interpreter.send("TAKE_DRINK")
    print(
        f"Current state: {interpreter.current_state_ids} | Context: {interpreter.context}"
    )

    # --- Scenario 6: Clean Machine ---
    print("\n--- Scenario 6: Cleaning Machine ---")
    print(f"Current coffee count: {interpreter.context['coffeeCount']}")
    await interpreter.send("CLEAN_MACHINE")
    print(
        f"Current state: {interpreter.current_state_ids} | Context: {interpreter.context}"
    )
    await asyncio.sleep(5.5)
    print(
        f"Current state: {interpreter.current_state_ids} | Context: {interpreter.context}"
    )

    await interpreter.stop()
    print("\n--- Coffee Machine simulation ended ---")


if __name__ == "__main__":
    asyncio.run(run_coffee_machine_example())
