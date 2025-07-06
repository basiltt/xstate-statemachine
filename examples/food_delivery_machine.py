# food_delivery_machine.py
import asyncio
import random
from uuid import uuid4

from src.xstate_machine import (
    Interpreter,
    LoggingInspector,
    MachineLogic,
    create_machine,
    Event,
)

# In the user's main.py file
import logging

# Configure logging for the application
logging.basicConfig(
    level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s"
)

# In food_delivery_machine.py


async def main():
    """
    Runs a complex simulation of a food delivery service state machine.
    """
    print("🎬 --- Food Delivery Service Simulation --- 🎬\n")

    # ... (Actor and Machine configs remain the same) ...
    delivery_actor_config = {
        "id": "deliveryActor",
        "initial": "assigning",
        "context": {"driverId": None, "pickupTime": 0},
        "states": {
            "assigning": {
                "after": {"10000": "noDriversAvailable"},
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
            "noDriversAvailable": {"entry": ["notifyParentNoDrivers"]},
            "deliveryComplete": {"type": "final"},
        },
    }
    order_machine_config = {
        "id": "orderMachine",
        "initial": "Browse",
        "context": {
            "orderId": str(uuid4()),
            "cart": [],
            "deliveryActor": None,
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
                        "guard": "cartIsNotEmpty",
                    },
                    "CANCEL": "cancelled",
                }
            },
            "paying": {
                "invoke": {
                    "src": "processPayment",
                    "onDone": "preparing",
                    "onError": {
                        "target": "paymentFailed",
                        "actions": ["logPaymentFailure"],
                    },
                }
            },
            "paymentFailed": {"on": {"RETRY_PAYMENT": "paying"}},
            "preparing": {
                "entry": ["spawn_deliveryActor", "assignToKitchen"],
                "type": "parallel",
                "states": {
                    "kitchen": {
                        "initial": "prepping",
                        "states": {
                            "prepping": {"after": {"5000": "packaging"}},
                            "packaging": {"after": {"2000": "readyForPickup"}},
                            "readyForPickup": {
                                "entry": ["notifyActorPickupReady"]
                            },
                        },
                    },
                    "delivery": {
                        "on": {
                            "NO_DRIVERS": "#orderMachine.cancelled",
                            "DELIVERY_COMPLETE": "#orderMachine.delivered",
                        }
                    },
                },
            },
            "delivered": {"type": "final"},
            "cancelled": {"type": "final"},
        },
    }

    # --- Define the Implementation Logic (Actions, Services, Guards) ---

    delivery_actor_machine_node = create_machine(
        delivery_actor_config,
        MachineLogic(
            actions={
                "assignDriver": lambda i, ctx, evt: ctx.update(
                    {"driverId": evt.payload.get("driverId", "DRV-007")}
                ),
                "notifyParentNoDrivers": lambda i, ctx, evt: asyncio.create_task(
                    i.parent.send("NO_DRIVERS")
                ),
            }
        ),
    )

    order_machine_logic = MachineLogic(
        actions={
            "addItemToCart": lambda i, ctx, evt: ctx["cart"].append(
                evt.payload.get("item")
            ),
            "logPaymentFailure": lambda i, ctx, evt: print(
                f"💳 Payment failed: {evt.data.get('error')}"
            ),
            "assignToKitchen": lambda i, ctx, evt: print(
                f"🍳 Order {ctx['orderId']} assigned to kitchen."
            ),
            # ✨ FIX: Retrieve the actor reference dynamically from the context
            # instead of using a hardcoded ID.
            "notifyActorPickupReady": lambda i, ctx, evt: asyncio.create_task(
                next(iter(ctx["actors"].values())).send("PICKUP_READY")
            ),
        },
        guards={"cartIsNotEmpty": lambda ctx, evt: bool(ctx.get("cart"))},
        services={
            "processPayment": async_process_payment,
            "deliveryActor": delivery_actor_machine_node,
        },
    )

    # --- Create and Run the Simulation ---
    order_machine = create_machine(order_machine_config, order_machine_logic)
    interpreter = Interpreter(order_machine)
    interpreter.use(LoggingInspector())
    await interpreter.start()

    print("\n--- 🤖 SIMULATION LOG ---")
    print(f"Initial State: {interpreter.current_state_ids}\n")

    # Simulate user actions
    await interpreter.send("ADD_TO_CART", item="Pizza")
    await asyncio.sleep(0.1)
    print(f"Cart Contents: {interpreter.context['cart']}")

    await interpreter.send("ADD_TO_CART", item="Salad")
    await asyncio.sleep(0.1)
    print(f"Cart Contents: {interpreter.context['cart']}\n")

    await interpreter.send("CHECKOUT")

    # Give the payment and spawn process time to complete
    await asyncio.sleep(3)

    # A driver becomes available!
    # ✨ FIX: Retrieve the actor reference dynamically to send it a message.
    if interpreter.context.get("actors"):
        print("\n---  Assigned a driver! ---")
        delivery_actor_ref = next(iter(interpreter.context["actors"].values()))
        await delivery_actor_ref.send("DRIVER_ASSIGNED", driverId="DRV-451")
        # Let the rest of the simulation run
        await asyncio.sleep(15)
    else:
        print("\n--- 🤷 No actor was spawned, simulation might end early. ---")

    print("\n--- 🏁 SIMULATION COMPLETE ---")
    print(f"Final State: {interpreter.current_state_ids}")
    print(f"Final Context: {interpreter.context}")

    await interpreter.stop()


# ✨ FIX: Update the async service to the correct signature.
async def async_process_payment(
    interpreter: Interpreter, ctx: dict, evt: Event
) -> dict:
    """A simulated async function that represents calling a payment gateway."""
    print("💳 Processing payment...")
    await asyncio.sleep(2)
    if random.random() > 0.1:
        print("✅ Payment successful!")
        return {"confirmationCode": "PMT-ABC-123"}
    else:
        print("❌ Payment failed!")
        raise Exception("Insufficient funds")


if __name__ == "__main__":
    asyncio.run(main())
