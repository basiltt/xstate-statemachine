"""
examples/food_delivery_machine.py
-------
A complex simulation of a food delivery service using the XState machine library.

This script demonstrates various advanced features of the state machine,
including nested states, parallel states, invoked services, delayed transitions,
guards, actions, and actor spawning/communication.
"""

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------
import asyncio
import logging
import random
from typing import Any, Dict, Optional  # 📝 Added Optional for clarity
from uuid import uuid4

from src.xstate_statemachine import (
    Event,
    Interpreter,
    LoggingInspector,
    MachineLogic,
    create_machine,
)

# -----------------------------------------------------------------------------
# Logger Configuration
# -----------------------------------------------------------------------------
# Configure logging for the entire application to display INFO level messages and above.
logging.basicConfig(
    level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s"
)
# Get a logger instance for this specific module
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 🛠️ Asynchronous Services
# -----------------------------------------------------------------------------
# These functions simulate external asynchronous operations like payment processing.
# They are designed to be 'invoked' by the state machine.
# -----------------------------------------------------------------------------


async def async_process_payment(
    interpreter: Interpreter, ctx: Dict[str, Any], evt: Event
) -> Dict[str, Any]:
    """
    A simulated asynchronous function representing a call to a payment gateway.

    This function simulates a network request to an external payment service.
    It introduces a random failure chance to mimic real-world scenarios.

    Args:
        interpreter (Interpreter): The state machine interpreter instance.
        ctx (Dict[str, Any]): The current context of the state machine.
        evt (Event): The event that triggered this service.

    Returns:
        Dict[str, Any]: A dictionary containing payment confirmation details if successful.

    Raises:
        Exception: If the simulated payment fails due to insufficient funds or other issues.
    """
    logger.info("💳 Processing payment...")
    await asyncio.sleep(2)  # ⏳ Simulate network latency
    if random.random() > 0.1:
        logger.info("✅ Payment successful!")
        return {"confirmationCode": "PMT-ABC-123"}
    else:
        logger.error("❌ Payment failed!")
        raise Exception("Insufficient funds")


# -----------------------------------------------------------------------------
# Machine Configurations
# -----------------------------------------------------------------------------


def get_delivery_actor_config() -> Dict[str, Any]:
    """
    Returns the configuration dictionary for the delivery actor state machine.

    This configuration defines the states, transitions, and initial context
    for managing a delivery driver's lifecycle.

    Returns:
        Dict[str, Any]: The configuration for the delivery actor machine.
    """
    return {
        "id": "deliveryActor",
        "initial": "assigning",
        "context": {"driverId": None, "pickupTime": 0},
        "states": {
            "assigning": {
                "after": {
                    "10000": "noDriversAvailable"
                },  # ⏱️ Timeout if no driver assigned
                "on": {
                    "DRIVER_ASSIGNED": {
                        "target": "enRouteToRestaurant",
                        "actions": ["assignDriver"],
                    }
                },
            },
            "enRouteToRestaurant": {"on": {"PICKUP_READY": "waitingForFood"}},
            "waitingForFood": {"on": {"FOOD_PICKED_UP": "enRouteToCustomer"}},
            "enRouteToCustomer": {"on": {"ARRIVED": "deliveryComplete"}},
            "noDriversAvailable": {
                "entry": ["notifyParentNoDrivers"]
            },  # 🗣️ Notify parent on no drivers
            "deliveryComplete": {
                "type": "final"
            },  # 🎉 Final state for successful delivery
        },
    }


def get_order_machine_config() -> Dict[str, Any]:
    """
    Returns the configuration dictionary for the main order state machine.

    This configuration defines the entire lifecycle of a food order,
    from Browse to delivery or cancellation, including payment and
    parallel processing for kitchen and delivery.

    Returns:
        Dict[str, Any]: The configuration for the order machine.
    """
    return {
        "id": "orderMachine",
        "initial": "Browse",
        "context": {
            "orderId": str(uuid4()),
            "cart": [],
            "deliveryActor": None,  # 📦 To hold the spawned delivery actor reference
        },
        "states": {
            "Browse": {
                "on": {
                    "ADD_TO_CART": {
                        "target": "ordering",
                        "actions": ["addItemToCart"],
                    }
                }
            },
            "ordering": {
                "on": {
                    "ADD_TO_CART": {"actions": ["addItemToCart"]},
                    "CHECKOUT": {
                        "target": "paying",
                        "guard": "cartIsNotEmpty",  # 🚫 Guard to ensure cart isn't empty
                    },
                    "CANCEL": "cancelled",
                }
            },
            "paying": {
                "invoke": {
                    "src": "processPayment",  # 📞 Invoke the payment service
                    "onDone": "preparing",  # ✅ On successful payment
                    "onError": {
                        "target": "paymentFailed",
                        "actions": [
                            "logPaymentFailure"
                        ],  # ❌ On payment failure
                    },
                }
            },
            "paymentFailed": {
                "on": {"RETRY_PAYMENT": "paying"}
            },  # 🔄 Allow retrying payment
            "preparing": {
                "entry": [
                    "spawn_deliveryActor",
                    "assignToKitchen",
                ],  # ➕ Entry actions
                "type": "parallel",  # 👯 Parallel states for kitchen and delivery
                "states": {
                    "kitchen": {
                        "initial": "prepping",
                        "states": {
                            "prepping": {
                                "after": {"5000": "packaging"}
                            },  # ⏱️ Simulate prep time
                            "packaging": {
                                "after": {"2000": "readyForPickup"}
                            },  # ⏱️ Simulate packaging time
                            "readyForPickup": {
                                "entry": [
                                    "notifyActorPickupReady"
                                ]  # 🗣️ Notify delivery actor
                            },
                        },
                    },
                    "delivery": {
                        "on": {
                            "NO_DRIVERS": "#orderMachine.cancelled",  # 🛑 If no drivers, cancel order
                            "DELIVERY_COMPLETE": "#orderMachine.delivered",  # ✅ Delivery finished
                        }
                    },
                },
            },
            "delivered": {
                "type": "final"
            },  # 🎉 Final state for successful delivery
            "cancelled": {
                "type": "final"
            },  # 🛑 Final state for cancelled order
        },
    }


# -----------------------------------------------------------------------------
# Machine Logic (Actions, Services, Guards)
# -----------------------------------------------------------------------------


class FoodDeliveryLogic(MachineLogic):
    """
    Encapsulates all custom logic (actions, guards, services) for the food delivery state machine.

    This class centralizes the behavioral aspects of the state machine, adhering to
    the principle of separation of concerns.
    """

    def __init__(self, delivery_actor_machine_node: Any):
        """
        Initializes the FoodDeliveryLogic with necessary components.

        Args:
            delivery_actor_machine_node (Any): The state machine node for the delivery actor
                                              which will be spawned as a service.
        """
        super().__init__()
        self._delivery_actor_machine_node = delivery_actor_machine_node
        self._setup_actions()
        self._setup_guards()
        self._setup_services()

    def _setup_actions(self) -> None:
        """
        Defines and sets up all action functions used by the state machines.

        Actions are side effects performed during state transitions or on entry/exit of states.
        Each action receives the interpreter, context, event, and action definition.
        """
        self.actions = {
            "addItemToCart": self._add_item_to_cart,
            "logPaymentFailure": self._log_payment_failure,
            "assignToKitchen": self._assign_to_kitchen,
            "notifyActorPickupReady": self._notify_actor_pickup_ready,
            "assignDriver": self._assign_driver,
            "notifyParentNoDrivers": self._notify_parent_no_drivers,
            "spawn_deliveryActor": self._spawn_delivery_actor,
        }

    def _setup_guards(self) -> None:
        """
        Defines and sets up all guard functions used by the state machines.

        Guards are conditions that must be true for a transition to occur.
        Each guard receives the context and event.
        """
        self.guards = {
            "cartIsNotEmpty": self._cart_is_not_empty,
        }

    def _setup_services(self) -> None:
        """
        Defines and sets up all service functions used by the state machines.

        Services are asynchronous operations invoked by states. They can be
        other state machines (actors) or external async functions.
        """
        self.services = {
            "processPayment": async_process_payment,
            "deliveryActor": self._delivery_actor_machine_node,
        }

    # --- Actions ---

    def _add_item_to_cart(
        self,
        interpreter: Interpreter,
        ctx: Dict[str, Any],
        evt: Event,
        action_def: Any,
    ) -> None:
        """
        Action: Adds an item to the order cart.

        Args:
            interpreter (Interpreter): The state machine interpreter.
            ctx (Dict[str, Any]): The current state machine context.
            evt (Event): The event containing the item to add.
            action_def (Any): The action definition (unused here, but required by signature).
        """
        item = evt.payload.get("item")
        if item:
            ctx["cart"].append(item)
            logger.info(f"🛒 Added '{item}' to cart. Cart: {ctx['cart']}")
        else:
            logger.warning("⚠️ Attempted to add empty item to cart.")

    def _log_payment_failure(
        self,
        interpreter: Interpreter,
        ctx: Dict[str, Any],
        evt: Event,
        action_def: Any,
    ) -> None:
        """
        Action: Logs a payment failure message.

        Args:
            interpreter (Interpreter): The state machine interpreter.
            ctx (Dict[str, Any]): The current state machine context.
            evt (Event): The event containing payment failure data.
            action_def (Any): The action definition (unused here, but required by signature).
        """
        error_message = evt.data.get("error", "Unknown payment error")
        logger.error(
            f"💳 Payment failed for order {ctx['orderId']}: {error_message}"
        )

    def _assign_to_kitchen(
        self,
        interpreter: Interpreter,
        ctx: Dict[str, Any],
        evt: Event,
        action_def: Any,
    ) -> None:
        """
        Action: Logs that the order has been assigned to the kitchen.

        Args:
            interpreter (Interpreter): The state machine interpreter.
            ctx (Dict[str, Any]): The current state machine context.
            evt (Event): The event that triggered this action.
            action_def (Any): The action definition (unused here, but required by signature).
        """
        logger.info(f"🍳 Order {ctx['orderId']} assigned to kitchen.")

    def _notify_actor_pickup_ready(
        self,
        interpreter: Interpreter,
        ctx: Dict[str, Any],
        evt: Event,
        action_def: Any,
    ) -> None:
        """
        Action: Notifies the spawned delivery actor that the food is ready for pickup.

        Args:
            interpreter (Interpreter): The state machine interpreter.
            ctx (Dict[str, Any]): The current state machine context.
            evt (Event): The event that triggered this action.
            action_def (Any): The action definition (unused here, but required by signature).
        """
        # 🤝 Get the spawned actor reference. Assuming there's only one actor for simplicity.
        delivery_actor_ref = next(iter(ctx["actors"].values()), None)
        if delivery_actor_ref:
            asyncio.create_task(delivery_actor_ref.send("PICKUP_READY"))
            logger.info("📢 Notified delivery actor: PICKUP_READY.")
        else:
            logger.warning(
                "⚠️ No delivery actor found to notify for PICKUP_READY."
            )

    def _assign_driver(
        self,
        interpreter: Interpreter,
        ctx: Dict[str, Any],
        evt: Event,
        action_def: Any,
    ) -> None:
        """
        Action: Assigns a driver ID to the delivery actor's context.

        Args:
            interpreter (Interpreter): The state machine interpreter.
            ctx (Dict[str, Any]): The current state machine context of the delivery actor.
            evt (Event): The event containing the driver ID.
            action_def (Any): The action definition (unused here, but required by signature).
        """
        driver_id = evt.payload.get("driverId", "DRV-007")
        ctx.update({"driverId": driver_id})
        logger.info(f"🚚 Driver {driver_id} assigned.")

    def _notify_parent_no_drivers(
        self,
        interpreter: Interpreter,
        ctx: Dict[str, Any],
        evt: Event,
        action_def: Any,
    ) -> None:
        """
        Action: Notifies the parent state machine (orderMachine) that no drivers are available.

        Args:
            interpreter (Interpreter): The state machine interpreter of the delivery actor.
            ctx (Dict[str, Any]): The current state machine context of the delivery actor.
            evt (Event): The event that triggered this action.
            action_def (Any): The action definition (unused here, but required by signature).
        """
        if interpreter.parent:
            asyncio.create_task(interpreter.parent.send("NO_DRIVERS"))
            logger.warning(
                "🚫 No drivers available. Notifying parent order machine."
            )
        else:
            logger.error(
                "❌ Delivery actor has no parent to notify about no drivers."
            )

    def _spawn_delivery_actor(
        self,
        interpreter: Interpreter,
        ctx: Dict[str, Any],
        evt: Event,
        action_def: Any,
    ) -> None:
        """
        Action: Spawns the delivery actor as a child of the order machine.

        This action is typically called when the order enters a state that requires
        delivery coordination, like 'preparing'.

        Args:
            interpreter (Interpreter): The state machine interpreter for the order machine.
            ctx (Dict[str, Any]): The current state machine context for the order machine.
            evt (Event): The event that triggered this action.
            action_def (Any): The action definition (unused here, but required by signature).
        """
        # The 'deliveryActor' service is already defined in self.services
        # The xstate-machine library handles spawning actors defined in services.
        # This action ensures the actor is listed in the context.
        # The actual spawning is triggered by 'invoke' in the state config.
        logger.info("🚀 Attempting to spawn delivery actor...")
        # The xstate_statemachine library's Interpreter manages the actual spawning
        # and adding to ctx['actors'] when a service with 'type: "machine"' is invoked.
        # This action primarily serves as a log point or to trigger additional logic
        # if the spawning mechanism were more complex or manual.

        # For this specific library, the `spawn_deliveryActor` action itself doesn't
        # directly perform the spawn. Instead, the `invoke` configuration in the
        # `preparing` state handles it. This action is here to match the original
        # code's intention and can be used for logging or pre-spawn setup.
        pass  # Actual spawning handled by the 'invoke' config in the state.

    # --- Guards ---

    def _cart_is_not_empty(self, ctx: Dict[str, Any], evt: Event) -> bool:
        """
        Guard: Checks if the shopping cart is not empty.

        Args:
            ctx (Dict[str, Any]): The current state machine context.
            evt (Event): The event that triggered this guard.

        Returns:
            bool: True if the cart contains items, False otherwise.
        """
        is_not_empty = bool(ctx.get("cart"))
        if not is_not_empty:
            logger.warning("🚫 Checkout failed: Cart is empty.")
        return is_not_empty


# -----------------------------------------------------------------------------
# Main Simulation
# -----------------------------------------------------------------------------


async def main() -> None:
    """
    Runs a complex simulation of a food delivery service state machine.

    This function orchestrates the creation of state machines, their interpreters,
    and simulates various user and system events to demonstrate the flow
    of a food order from Browse to delivery or cancellation.
    """
    logger.info("🎬 --- Food Delivery Service Simulation --- 🎬\n")

    # 📦 Get machine configurations
    delivery_actor_config = get_delivery_actor_config()
    order_machine_config = get_order_machine_config()

    # 🔗 Create the delivery actor machine node first, as it's a service for the order machine
    delivery_actor_machine_node = create_machine(
        delivery_actor_config,
        MachineLogic(
            actions={
                "assignDriver": lambda i, ctx, evt, action_def: (
                    ctx.update(
                        {"driverId": evt.payload.get("driverId", "DRV-007")}
                    ),
                    logger.info(
                        f"🚚 Driver {evt.payload.get('driverId', 'DRV-007')} assigned."
                    ),
                )[
                    1
                ],  # Return value of logger.info (None) and ensure update happens
                "notifyParentNoDrivers": lambda i, ctx, evt, action_def: (
                    (
                        asyncio.create_task(i.parent.send("NO_DRIVERS"))
                        if i.parent
                        else None
                    ),
                    logger.warning(
                        "🚫 No drivers available. Notifying parent order machine."
                    ),
                )[1],
            }
        ),
    )

    # 🧠 Create the logic instance for the main order machine
    order_machine_logic = FoodDeliveryLogic(delivery_actor_machine_node)

    # 🏭 Create the main order machine
    order_machine = create_machine(order_machine_config, order_machine_logic)

    # 🚀 Create and start the interpreter
    interpreter = Interpreter(order_machine)
    interpreter.use(
        LoggingInspector()
    )  # 🕵️‍♂️ Enable detailed state transition logging
    await interpreter.start()
    logger.info(f"Initial State: {interpreter.current_state_ids}\n")
    logger.info("--- 🤖 SIMULATION LOG ---")

    # Simulate user actions
    logger.info("➡️ Sending ADD_TO_CART event for Pizza...")
    await interpreter.send("ADD_TO_CART", item="Pizza")
    await asyncio.sleep(0.1)  # ⏱️ Allow state transition to complete
    logger.info(f"Current Cart Contents: {interpreter.context['cart']}")

    logger.info("➡️ Sending ADD_TO_CART event for Salad...")
    await interpreter.send("ADD_TO_CART", item="Salad")
    await asyncio.sleep(0.1)  # ⏱️ Allow state transition to complete
    logger.info(f"Current Cart Contents: {interpreter.context['cart']}\n")

    logger.info("➡️ Sending CHECKOUT event...")
    await interpreter.send("CHECKOUT")

    # Give the payment and spawn process time to complete
    logger.info(
        "⏳ Waiting for payment and actor spawning to complete (3 seconds)..."
    )
    await asyncio.sleep(3)

    # A driver becomes available!
    # 🔍 Check if the delivery actor has been spawned and is available in context.
    # The 'actors' key in interpreter.context holds references to spawned child actors.
    spawned_actors = interpreter.context.get("actors")
    delivery_actor_ref: Optional[Interpreter] = None
    if spawned_actors:
        # Assuming only one delivery actor is spawned and is the first in the values.
        delivery_actor_ref = next(iter(spawned_actors.values()), None)

    if delivery_actor_ref:
        logger.info("\n--- Assigned a driver! ---")
        logger.info("➡️ Sending DRIVER_ASSIGNED event to delivery actor...")
        await delivery_actor_ref.send("DRIVER_ASSIGNED", driverId="DRV-451")
        # Let the rest of the simulation run for delivery
        logger.info(
            "⏳ Allowing remaining simulation time for delivery (15 seconds)..."
        )
        await asyncio.sleep(15)
    else:
        logger.warning(
            "\n--- 🤷 No delivery actor was spawned, simulation might end early or unexpectedly. ---"
        )

    logger.info("\n--- 🏁 SIMULATION COMPLETE ---")
    logger.info(f"Final State: {interpreter.current_state_ids}")
    logger.info(f"Final Context: {interpreter.context}")

    # 🛑 Stop the interpreter
    await interpreter.stop()
    logger.info("Interpreter stopped.")


if __name__ == "__main__":
    asyncio.run(main())
