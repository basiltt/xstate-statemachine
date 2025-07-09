# examples/sync/super_complex/class_approach/with_logic_loader/ecommerce_fulfillment/ecommerce_fulfillment_logic.py
import logging
import time
import random
from typing import Dict, Any

from src.xstate_statemachine import SyncInterpreter, Event, ActionDefinition


class ECommerceFulfillmentLogic:
    """Class-based logic for the E-Commerce Fulfillment state machine."""

    # --- Actions ---
    def markOrderStatus(
        self, i: SyncInterpreter, ctx: Dict, e: Event, ad: ActionDefinition
    ):
        status = ad.params.get("status", "UNKNOWN")
        ctx["orderStatus"] = status
        logging.info(f"📦 Order status updated to: {status}")

    def sendEmail(
        self, i: SyncInterpreter, ctx: Dict, e: Event, ad: ActionDefinition
    ):
        template = ad.params.get("template", "general")
        logging.info(f"📧 Sending email with template: '{template}'")

    def logOrderCompletion(
        self, i: SyncInterpreter, ctx: Dict, e: Event, ad: ActionDefinition
    ):
        logging.info(
            f"🏁 Order flow for orderId '{ctx['orderId']}' has completed with status: {ctx['orderStatus']}."
        )

    def addTrackingNumber(
        self, i: SyncInterpreter, ctx: Dict, e: Event, ad: ActionDefinition
    ):
        ctx["trackingNumber"] = e.data.get("trackingId")
        logging.info(f"🚚 Tracking number added: {ctx['trackingNumber']}")

    def releaseInventory(self, i, c, e, a):
        logging.info("🏬 Inventory released.")

    def reserveInventory(self, i, c, e, a):
        logging.info("🏬 Inventory reserved.")

    def queueRefund(self, i, c, e, a):
        logging.info("💰 Refund queued.")

    # --- Guards ---
    def cartIsNotEmpty(self, ctx: Dict, e: Event) -> bool:
        is_valid = len(ctx.get("cart", [])) > 0
        if not is_valid:
            logging.warning("Guard: Cart is empty, checkout blocked.")
        return is_valid

    def paymentIsValid(self, ctx: Dict, e: Event) -> bool:
        is_valid = e.payload and e.payload.get("card_number")
        if not is_valid:
            logging.warning("Guard: Payment info is invalid, charge blocked.")
        return is_valid

    # --- Services ---
    def chargePayment(
        self, i: SyncInterpreter, ctx: Dict, e: Event
    ) -> Dict[str, Any]:
        logging.info("💳 Attempting to charge payment...")
        time.sleep(1)  # Simulate payment gateway latency
        if e.payload.get("card_number") == "fail_card":
            raise ConnectionError("Payment gateway declined the transaction.")
        return {"transactionId": f"txn_{random.randint(1000, 9999)}"}

    def arrangeShipment(
        self, i: SyncInterpreter, ctx: Dict, e: Event
    ) -> Dict[str, Any]:
        logging.info("🚚 Arranging shipment with carrier...")
        time.sleep(1)  # Simulate API call to shipping provider
        return {"trackingId": f"1Z{random.randint(100000, 999999)}"}

    def debouncedSave(
        self, i: SyncInterpreter, ctx: Dict, e: Event
    ) -> Dict[str, Any]:
        logging.info("💾 Inventory change detected, saving...")
        time.sleep(0.5)  # Simulate debounced save
        logging.info("💾 Inventory synced.")
        return {"synced": True}
