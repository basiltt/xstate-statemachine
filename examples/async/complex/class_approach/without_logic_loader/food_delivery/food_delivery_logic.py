# examples/async/complex/class_approach/without_logic_loader/food_delivery/food_delivery_logic.py
import asyncio
import logging
import random
from typing import Dict, Any

from src.xstate_statemachine import Interpreter, Event, ActionDefinition


class FoodDeliveryLogic:
    """Class-based logic for a food delivery order tracker."""

    # --- Actions ---
    def set_pending_status(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        ctx["order_id"] = e.payload.get("order_id")
        ctx["status"] = "PENDING_CONFIRMATION"
        logging.info(
            f"🧾 Order #{ctx['order_id']} placed. Awaiting restaurant confirmation."
        )

    def log_confirmation(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        logging.info(
            f"✅ Restaurant confirmed order #{ctx['order_id']}. Result: {e.data}"
        )

    def set_rejection_error(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        ctx["error"] = str(e.data)
        ctx["status"] = "REJECTED_BY_RESTAURANT"

    def set_timeout_error(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        ctx["error"] = "Could not find a nearby driver in time."
        ctx["status"] = "FAILED_NO_DRIVER"

    def update_status_to_finding_driver(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        ctx["status"] = "FINDING_DRIVER"
        logging.info("🤝 Order confirmed. Searching for a delivery driver...")

    def update_status_to_preparing(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        ctx["status"] = "PREPARING_FOOD"
        driver = e.payload.get("driver_name")
        logging.info(
            f"👨‍🍳 Driver '{driver}' assigned! The restaurant is now preparing your order."
        )

    def update_status_to_delivering(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        ctx["status"] = "OUT_FOR_DELIVERY"
        logging.info("🛵 Your order is out for delivery!")

    def update_status_to_delivered(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        ctx["status"] = "DELIVERED"
        logging.info("🎉🎉🎉 Your order has been delivered! Enjoy your meal.")

    def log_failure_reason(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        logging.error(
            f"❌ Order #{ctx['order_id']} failed. Reason: {ctx['error']}"
        )

    # --- Services ---
    async def confirm_with_restaurant(
        self, i: Interpreter, ctx: Dict, e: Event
    ) -> Dict[str, Any]:
        logging.info("📞 Invoking service: Contacting restaurant...")
        await asyncio.sleep(2.0)

        # Simulate restaurant being too busy or closed
        if random.random() < 0.2:
            raise ConnectionError(
                "Restaurant is not accepting orders at this time."
            )

        logging.info("👍 Restaurant ACKNOWLEDGED the order.")
        return {"confirmed": True, "estimated_prep_time": "20 minutes"}
