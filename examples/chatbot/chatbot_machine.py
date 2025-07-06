# examples/chatbot_machine.py
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

# -----------------------------------------------------------------------------
# 🪵 Logging Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s"
)


# -----------------------------------------------------------------------------
# 🛠️ Mock Asynchronous Service
# -----------------------------------------------------------------------------


async def fetch_service_providers(
    interpreter: Interpreter, context: Dict[str, Any], event: Event
) -> Dict[str, Any]:
    """A mock service that simulates fetching local service providers."""
    zip_code = context.get("zipCode", "N/A")
    provider_type = context.get("identifiedService", "general")
    print(
        f"\n🔍 Provider Service: Searching for '{provider_type}' in zip code {zip_code}..."
    )
    await asyncio.sleep(2)  # Simulate network latency
    print("✅ Provider Service: Found 3 providers.")
    return {
        "providers": [
            {"name": "A1 Plumbing", "rating": 4.8, "type": "plumber"},
            {"name": "Bolt Electrical", "rating": 4.9, "type": "electrician"},
            {"name": "Speedy Repairs", "rating": 4.6, "type": "handyman"},
        ]
    }


# -----------------------------------------------------------------------------
# 🚀 Main Simulation
# -----------------------------------------------------------------------------


async def main():
    """
    Loads the chatbot machine from a JSON file and simulates a user
    searching for a local service provider.
    """
    print("🎬 --- Chatbot Provider Search Simulation --- 🎬\n")

    # 📜 Load the machine definition from the JSON file.
    with open("chatbot.json") as f:
        chatbot_config = json.load(f)

    # 🧠 Define the implementation logic for the machine.
    chatbot_logic = MachineLogic(
        actions={
            "setProviderTypePrompt": lambda i, ctx, evt: ctx.update(
                {
                    "providerTypePrompt": "What type of provider are you looking for?"
                }
            ),
            "setProviderType": lambda i, ctx, evt: ctx.update(
                {"identifiedService": evt.payload.get("type")}
            ),
            "setZipCodePrompt": lambda i, ctx, evt: ctx.update(
                {"zipCodePrompt": "Please enter your 5-digit zip code."}
            ),
            "setZipCode": lambda i, ctx, evt: ctx.update(
                {"zipCode": evt.payload.get("zip")}
            ),
            # ✨ FIX: Use the imported `logging` module directly, not an undefined `logger` variable.
            "logEventValue": lambda i, ctx, evt: logging.info(
                f"📝 Event Logged: {evt.type} | Payload: {evt.payload}"
            ),
            "setServiceProviders": lambda i, ctx, evt: ctx.update(
                {"serviceProviders": evt.data.get("providers")}
            ),
            # ✨ FIX: Use the imported `logging` module directly.
            "logEventOutput": lambda i, ctx, evt: logging.info(
                f"📝 Service Result Logged: {evt.type}, Data: {evt.data}"
            ),
        },
        services={
            "fetchProvidersActor": fetch_service_providers,
        },
    )

    # 🚀 Create the machine definition from the loaded config and logic.
    chatbot_machine = create_machine(chatbot_config, chatbot_logic)

    # --- Run the Simulation ---
    interpreter = Interpreter(chatbot_machine)
    interpreter.use(LoggingInspector())
    await interpreter.start()

    print("--- 🤖 SIMULATION LOG ---")
    print(f"Initial State: {interpreter.current_state_ids}\n")

    # 1. User wants to search for a provider.
    print("--- Step 1: User triggers provider search ---")
    await interpreter.send("searchProviders")
    await asyncio.sleep(0.1)  # Allow event to process
    print(f"Current State: {interpreter.current_state_ids}")
    print(f"Context Prompt: {interpreter.context['providerTypePrompt']}\n")

    # 2. User specifies the provider type.
    print("--- Step 2: User specifies they need a plumber ---")
    await interpreter.send("captureProviderType", type="plumber")
    await asyncio.sleep(0.1)
    print(f"Current State: {interpreter.current_state_ids}")
    print(f"Context Prompt: {interpreter.context['zipCodePrompt']}\n")

    # 3. User provides their zip code, triggering the async search.
    print("--- Step 3: User provides zip code, triggering API call ---")
    await interpreter.send("captureUserZipCode", zip="90210")

    # Wait for the async `invoke` to complete.
    await asyncio.sleep(3)

    print("\n--- 🏁 SIMULATION COMPLETE ---")
    print(f"Final State: {interpreter.current_state_ids}")
    print("Service Providers Found:")
    print(json.dumps(interpreter.context.get("serviceProviders"), indent=2))

    await interpreter.stop()


if __name__ == "__main__":
    asyncio.run(main())
