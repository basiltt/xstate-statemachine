# examples/sync/super_complex/class_approach/with_logic_loader/ecommerce_fulfillment_logic.py
# -------------------------------------------------------------------------------
# 🛒 E-Commerce Fulfillment Logic
# -------------------------------------------------------------------------------
"""
Class-based logic for E-Commerce order fulfillment, with snake_case
action and guard names matching the JSON definition above.
"""

import logging
import random
import time
from typing import Any, Dict

from xstate_statemachine import SyncInterpreter, Event, ActionDefinition

logger = logging.getLogger(__name__)


class ECommerceFulfillmentLogic:
    """Encapsulates actions, guards, and services for order fulfillment."""

    # -------------------------------------------------------------------------
    # ⚙️ Actions
    # -------------------------------------------------------------------------

    def mark_order_status(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],
        event: Event,  # noqa
        action_def: ActionDefinition,
    ) -> None:
        """📦 Action: Update order status from action params."""
        status = action_def.params.get("status", "UNKNOWN")
        context["orderStatus"] = status
        logger.info("📦 Order status updated to: %s", status)

    def send_email(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],  # noqa
        event: Event,  # noqa
        action_def: ActionDefinition,
    ) -> None:
        """📧 Action: Send notification email using template param."""
        template = action_def.params.get("template", "general")
        logger.info("📧 Sending email with template: '%s'", template)

    def log_order_completion(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],
        event: Event,  # noqa
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """🏁 Action: Log completion of the entire order flow."""
        order_id = context.get("orderId")
        status = context.get("orderStatus")
        logger.info(
            "🏁 Order '%s' completed with status '%s'.", order_id, status
        )

    def add_tracking_number(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """🚚 Action: Save shipment tracking ID from service data."""
        tracking = event.data.get("trackingId")
        context["trackingNumber"] = tracking
        logger.info("🚚 Tracking number added: %s", tracking)

    def reserve_inventory(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],  # noqa
        event: Event,  # noqa
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """🏬 Action: Reserve inventory (no-op simulation)."""
        logger.info("🏬 Inventory reserved.")

    def release_inventory(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],  # noqa
        event: Event,  # noqa
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """🏬 Action: Release inventory on cancellation."""
        logger.info("🏬 Inventory released.")

    def queue_refund(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],  # noqa
        event: Event,  # noqa
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """💰 Action: Queue a customer refund."""
        logger.info("💰 Refund queued.")

    # -------------------------------------------------------------------------
    # 🛡️ Guards
    # -------------------------------------------------------------------------

    def cart_is_not_empty(
        self, context: Dict[str, Any], event: Event
    ) -> bool:  # noqa
        """✔️ Guard: Ensure the cart has at least one item."""
        valid = bool(context.get("cart"))
        if not valid:
            logger.warning("🛡️ Cannot checkout: Cart is empty.")
        return valid

    def payment_is_valid(
        self, context: Dict[str, Any], event: Event
    ) -> bool:  # noqa
        """✔️ Guard: Validate presence of a card_number."""
        valid = bool(event.payload.get("card_number"))
        if not valid:
            logger.warning("🛡️ Payment info invalid, charge blocked.")
        return valid

    # -------------------------------------------------------------------------
    # 🔄 Services
    # -------------------------------------------------------------------------

    def charge_payment(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],  # noqa
        event: Event,
    ) -> Dict[str, Any]:
        """💳 Service: Charge payment synchronously."""
        logger.info("💳 Attempting to charge payment...")
        time.sleep(1)
        if event.payload.get("card_number") == "fail_card":
            raise ConnectionError("Payment gateway declined transaction.")
        txn = f"txn_{random.randint(1000, 9999)}"
        return {"transactionId": txn}

    def arrange_shipment(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],  # noqa
        event: Event,  # noqa
    ) -> Dict[str, Any]:
        """🚚 Service: Arrange shipping synchronously."""
        logger.info("🚚 Arranging shipment...")
        time.sleep(1)
        tracking = f"1Z{random.randint(100000, 999999)}"
        return {"trackingId": tracking}

    def debounced_save(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],  # noqa
        event: Event,  # noqa
    ) -> Dict[str, Any]:
        """💾 Service: Debounced inventory sync."""
        logger.info("💾 Inventory change detected, saving...")
        time.sleep(0.5)
        return {"synced": True}
