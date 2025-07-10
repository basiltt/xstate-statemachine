# -------------------------------------------------------------------------------
# 🍔 Food Delivery Logic
# examples/async/complex/class_approach/without_logic_loader/food_delivery/food_delivery_logic.py
# -------------------------------------------------------------------------------
"""
Class-based logic for simulating a food delivery order workflow.
"""

import asyncio
import logging
import random
from typing import Any, Dict

from src.xstate_statemachine import Interpreter, Event, ActionDefinition

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


class FoodDeliveryLogic:
    """Provides actions and a service for a food delivery state machine."""

    # -------------------------------------------------------------------------
    # 🛠️ Actions
    # -------------------------------------------------------------------------

    def set_pending_status(  # noqa
        self,
        interpreter: Interpreter,  # noqa
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """🧾 Mark order as pending confirmation."""
        context["order_id"] = event.payload.get("order_id")
        context["status"] = "PENDING_CONFIRMATION"
        logger.info(f"🧾 Order #{context['order_id']} placed.")

    def log_confirmation(  # noqa
        self,
        interpreter: Interpreter,  # noqa
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """✅ Log restaurant confirmation result."""
        result = event.data
        logger.info(
            f"✅ Restaurant confirmed #{context['order_id']}: {result}"
        )

    def set_rejection_error(  # noqa
        self,
        interpreter: Interpreter,  # noqa
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """❌ Record rejection reason and status."""
        context["error"] = str(event.data)
        context["status"] = "REJECTED_BY_RESTAURANT"
        logger.error(
            f"❌ Order #{context['order_id']} rejected: {context['error']}"
        )

    def set_timeout_error(  # noqa
        self,
        interpreter: Interpreter,  # noqa
        context: Dict[str, Any],
        event: Event,  # noqa
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """⌛ Record timeout error for missing driver."""
        context["error"] = "No driver found in time."
        context["status"] = "FAILED_NO_DRIVER"
        logger.error(f"⌛ Timeout: {context['error']}")

    def update_status_to_finding_driver(  # noqa
        self,
        interpreter: Interpreter,  # noqa
        context: Dict[str, Any],
        event: Event,  # noqa
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """🤝 Transition to driver search state."""
        context["status"] = "FINDING_DRIVER"
        logger.info("🤝 Searching for delivery driver...")

    def update_status_to_preparing(  # noqa
        self,
        interpreter: Interpreter,  # noqa
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """👨‍🍳 Mark food as being prepared."""
        context["status"] = "PREPARING_FOOD"
        driver = event.payload.get("driver_name")
        logger.info(f"👨‍🍳 Driver {driver} picked up order.")

    def update_status_to_delivering(  # noqa
        self,
        interpreter: Interpreter,  # noqa
        context: Dict[str, Any],
        event: Event,  # noqa
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """🛵 Mark order as out for delivery."""
        context["status"] = "OUT_FOR_DELIVERY"
        logger.info("🛵 Order is out for delivery.")

    def update_status_to_delivered(  # noqa
        self,
        interpreter: Interpreter,  # noqa
        context: Dict[str, Any],
        event: Event,  # noqa
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """🎉 Mark order as delivered."""
        context["status"] = "DELIVERED"
        logger.info("🎉 Order delivered! Enjoy your meal.")

    def log_failure_reason(  # noqa
        self,
        interpreter: Interpreter,  # noqa
        context: Dict[str, Any],
        event: Event,  # noqa
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """⚠️ Log final failure reason."""
        logger.error(
            f"❌ Order #{context['order_id']} failed: {context['error']}"
        )

    # -------------------------------------------------------------------------
    # 🚀 Services
    # -------------------------------------------------------------------------

    async def confirm_with_restaurant(  # noqa
        self,
        interpreter: Interpreter,  # noqa
        context: Dict[str, Any],  # noqa
        event: Event,  # noqa
    ) -> Dict[str, Any]:
        """📞 Async service to confirm order with restaurant.

        Args:
            interpreter: The running interpreter.
            context: Mutable context dict.
            event: The triggering Event.

        Returns:
            Confirmation result and prep time.

        Raises:
            ConnectionError: If restaurant cannot accept orders.
        """
        logger.info("📞 Contacting restaurant...")
        await asyncio.sleep(2.0)
        if random.random() < 0.2:
            raise ConnectionError("Restaurant unavailable.")
        return {"confirmed": True, "estimated_prep_time": "20m"}
