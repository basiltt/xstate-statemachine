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
# 📚 File Overview
# -----------------------------------------------------------------------------
# This file implements a chatbot simulation for a service provider search
# using the `xstate-machine` library. It demonstrates how to define a
# state machine in a JSON file (`chatbot.json`) and link its actions and
# services to Python functions. The simulation includes asynchronous
# operations for fetching data and managing conversational flow.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# 🪵 Logging Configuration
# -----------------------------------------------------------------------------
# Configures the application's logging to display messages from the
# `xstate-machine` library and the application itself, with informative
# prefixes.
# -----------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 🛠️ Mock Asynchronous Services (Actors)
# -----------------------------------------------------------------------------


async def fetch_service_providers_actor(
    interpreter: Interpreter, context: Dict[str, Any], event: Event
) -> Dict[str, Any]:
    """
    A mock asynchronous service that simulates fetching local service providers.

    This actor retrieves the `zipCode` and `identifiedService` from the
    interpreter's context to simulate a targeted search. It introduces
    a delay to mimic network latency.

    Args:
        interpreter (Interpreter): The interpreter instance invoking this service.
        context (Dict[str, Any]): The current context of the state machine.
        event (Event): The `invoke` event that triggered this service.

    Returns:
        Dict[str, Any]: A dictionary containing a list of mock service providers.
    """
    zip_code: str = context.get("zipCode", "N/A")
    provider_type: str = context.get("identifiedService", "general")
    logger.info(
        f"🔍 Provider Service Actor: Searching for '{provider_type}' in zip code {zip_code}..."
    )
    await asyncio.sleep(2)  # Simulate network latency
    logger.info("✅ Provider Service Actor: Found 3 mock providers.")
    return {
        "providers": [
            {"name": "A1 Plumbing", "rating": 4.8, "type": "plumber"},
            {"name": "Bolt Electrical", "rating": 4.9, "type": "electrician"},
            {"name": "Speedy Repairs", "rating": 4.6, "type": "handyman"},
        ]
    }


# -----------------------------------------------------------------------------
# ⚙️ Action Implementations
# -----------------------------------------------------------------------------


def _set_provider_type_prompt_action(
    interpreter: Interpreter,
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,
) -> None:
    """
    Sets the prompt message for asking the user about the provider type.

    Args:
        interpreter (Interpreter): The interpreter instance.
        context (Dict[str, Any]): The current context of the state machine.
        event (Event): The event that triggered this action.
        action_def (ActionDefinition): The definition of the action being executed.
    """
    context["providerTypePrompt"] = (
        "What type of provider are you looking for?"
    )
    logger.debug("💬 Action: 'providerTypePrompt' set.")


def _set_provider_type_action(
    interpreter: Interpreter,
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,
) -> None:
    """
    Sets the identified service type based on the event payload.

    Args:
        interpreter (Interpreter): The interpreter instance.
        context (Dict[str, Any]): The current context of the state machine.
        event (Event): The event containing the provider type in its payload.
        action_def (ActionDefinition): The definition of the action being executed.
    """
    identified_type: Any = event.payload.get("type")
    if identified_type:
        context["identifiedService"] = identified_type
        logger.info(
            f"📝 Action: 'identifiedService' set to '{identified_type}'."
        )
    else:
        logger.warning(
            "⚠️ Action: 'type' not found in event payload for setProviderType."
        )


def _set_zip_code_prompt_action(
    interpreter: Interpreter,
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,
) -> None:
    """
    Sets the prompt message for asking the user to enter their zip code.

    Args:
        interpreter (Interpreter): The interpreter instance.
        context (Dict[str, Any]): The current context of the state machine.
        event (Event): The event that triggered this action.
        action_def (ActionDefinition): The definition of the action being executed.
    """
    context["zipCodePrompt"] = "Please enter your 5-digit zip code."
    logger.debug("💬 Action: 'zipCodePrompt' set.")


def _set_zip_code_action(
    interpreter: Interpreter,
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,
) -> None:
    """
    Sets the zip code based on the event payload.

    Args:
        interpreter (Interpreter): The interpreter instance.
        context (Dict[str, Any]): The current context of the state machine.
        event (Event): The event containing the zip code in its payload.
        action_def (ActionDefinition): The definition of the action being executed.
    """
    zip_code: Any = event.payload.get("zip")
    if zip_code:
        context["zipCode"] = zip_code
        logger.info(f"📝 Action: 'zipCode' set to '{zip_code}'.")
    else:
        logger.warning(
            "⚠️ Action: 'zip' not found in event payload for setZipCode."
        )


def _log_event_value_action(
    interpreter: Interpreter,
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,
) -> None:
    """
    Logs the type and payload of the current event.

    Args:
        interpreter (Interpreter): The interpreter instance.
        context (Dict[str, Any]): The current context of the state machine.
        event (Event): The event to be logged.
        action_def (ActionDefinition): The definition of the action being executed.
    """
    logger.info(f"📝 Event Logged: {event.type} | Payload: {event.payload}")


def _set_service_providers_action(
    interpreter: Interpreter,
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,
) -> None:
    """
    Sets the list of service providers in the context from the event data.
    This action typically processes the result of an invoked service.

    Args:
        interpreter (Interpreter): The interpreter instance.
        context (Dict[str, Any]): The current context of the state machine.
        event (Event): The event containing the service providers data.
        action_def (ActionDefinition): The definition of the action being executed.
    """
    providers: Any = event.data.get("providers")
    if providers:
        context["serviceProviders"] = providers
        logger.info(
            f"📝 Action: 'serviceProviders' set with {len(providers)} providers."
        )
    else:
        logger.warning(
            "⚠️ Action: 'providers' not found in event data for setServiceProviders."
        )


def _log_event_output_action(
    interpreter: Interpreter,
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,
) -> None:
    """
    Logs the type and data of an event, typically used for service results.

    Args:
        interpreter (Interpreter): The interpreter instance.
        context (Dict[str, Any]): The current context of the state machine.
        event (Event): The event containing the service result data.
        action_def (ActionDefinition): The definition of the action being executed.
    """
    logger.info(f"📝 Service Result Logged: {event.type}, Data: {event.data}")


# -----------------------------------------------------------------------------
# 🚀 Main Simulation Logic
# -----------------------------------------------------------------------------


async def main() -> None:
    """
    Loads the chatbot machine from a JSON file and simulates a user
    searching for a local service provider.

    This function orchestrates the simulation by:
    1. Loading the state machine definition.
    2. Mapping actions and services to Python functions.
    3. Starting the interpreter.
    4. Sending a sequence of events to mimic user interaction.
    5. Logging the state and context changes.
    """
    logger.info("🎬 --- Chatbot Provider Search Simulation Starting --- 🎬\n")

    # 📜 Load the machine definition from the JSON file.
    try:
        with open("chatbot.json", "r") as f:
            chatbot_config: Dict[str, Any] = json.load(f)
        logger.info("✅ Chatbot machine configuration loaded successfully.")
    except FileNotFoundError:
        logger.error(
            "❌ chatbot.json not found. Please ensure it's in the same directory."
        )
        raise
    except json.JSONDecodeError:
        logger.error("❌ chatbot.json is malformed. Please check its syntax.")
        raise

    # 🧠 Define the implementation logic for the machine by binding
    # action and service names from the JSON to concrete Python functions.
    chatbot_logic = MachineLogic(
        actions={
            "setProviderTypePrompt": _set_provider_type_prompt_action,
            "setProviderType": _set_provider_type_action,
            "setZipCodePrompt": _set_zip_code_prompt_action,
            "setZipCode": _set_zip_code_action,
            "logEventValue": _log_event_value_action,
            "setServiceProviders": _set_service_providers_action,
            "logEventOutput": _log_event_output_action,
        },
        services={
            "fetchProvidersActor": fetch_service_providers_actor,
        },
    )
    logger.info("✅ Machine logic mapped to chatbot functions.")

    # 🚀 Create the machine definition from the loaded config and logic.
    chatbot_machine = create_machine(chatbot_config, chatbot_logic)
    logger.info("✅ State machine created.")

    # --- Run the Simulation ---
    interpreter: Interpreter = Interpreter(chatbot_machine)
    interpreter.use(
        LoggingInspector()
    )  # Attach logging inspector for detailed trace
    logger.info("✅ Interpreter created and configured with LoggingInspector.")

    await interpreter.start()
    logger.info("🏁 Interpreter started.")

    print("\n--- 🤖 SIMULATION LOG ---")
    print(f"Initial State: {interpreter.current_state_ids}\n")

    # 1. User wants to search for a provider.
    logger.info("--- Step 1: User triggers provider search ---")
    await interpreter.send("searchProviders")
    await asyncio.sleep(0.1)  # Allow event to process and state to update
    print(f"Current State: {interpreter.current_state_ids}")
    # 🧪 Validate that the prompt has been set in the context
    print(
        f"Context Prompt: {interpreter.context.get('providerTypePrompt', 'N/A')}\n"
    )

    # 2. User specifies the provider type.
    logger.info("--- Step 2: User specifies they need a plumber ---")
    await interpreter.send("captureProviderType", type="plumber")
    await asyncio.sleep(0.1)  # Allow event to process and state to update
    print(f"Current State: {interpreter.current_state_ids}")
    # 🧪 Validate that the zip code prompt has been set
    print(
        f"Context Prompt: {interpreter.context.get('zipCodePrompt', 'N/A')}\n"
    )
    logger.debug(f"Current context: {interpreter.context}")

    # 3. User provides their zip code, triggering the async search.
    logger.info("--- Step 3: User provides zip code, triggering API call ---")
    await interpreter.send("captureUserZipCode", zip="90210")

    # Wait for the async `invoke` (fetchProvidersActor) to complete.
    # The sleep duration should be greater than the actor's internal sleep.
    await asyncio.sleep(3)

    print("\n--- 🏁 SIMULATION COMPLETE ---")
    print(f"Final State: {interpreter.current_state_ids}")
    print("Service Providers Found:")
    # ✅ Display the results fetched by the service and stored in context
    print(
        json.dumps(interpreter.context.get("serviceProviders", []), indent=2)
    )

    await interpreter.stop()
    logger.info("🛑 Interpreter stopped.")


if __name__ == "__main__":
    # Entry point for the simulation
    asyncio.run(main())
