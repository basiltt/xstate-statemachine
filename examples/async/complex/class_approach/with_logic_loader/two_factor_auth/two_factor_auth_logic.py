# examples/async/complex/class_approach/with_logic_loader/two_factor_auth/two_factor_auth_logic.py
import asyncio
import logging
import random
from typing import Dict, Any

from src.xstate_statemachine import Interpreter, Event, ActionDefinition


class TwoFactorAuthLogic:
    """Class-based logic for a 2FA system."""

    # --- Actions ---
    def store_generated_code(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        ctx["generated_code"] = e.data.get("code")
        logging.info(
            f"🤫 A 2FA code has been generated and stored (it's {ctx['generated_code']})."
        )

    def set_error(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        ctx["error"] = str(e.data)
        logging.error(f"🔥 Delivery failed: {ctx['error']}")
        # Use a top-level event to transition the whole machine to failure
        asyncio.create_task(i.send("DELIVERY_FAILED"))

    def store_user_input(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        ctx["user_code_input"] = e.payload.get("code")
        logging.info(f"⌨️ User submitted code: {ctx['user_code_input']}")

    def increment_attempts(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        logging.warning("❌ Incorrect code. Please try again.")

    async def notify_validation_success(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        logging.info("✅ Code validation successful!")
        # This event will be heard by the other parallel region
        await i.send("VALIDATION_SUCCESS")

    def log_final_success(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        logging.info("🎉🎉🎉 2FA Authentication successful!")

    # --- Guards ---
    def is_code_correct(self, ctx: Dict, e: Event) -> bool:
        return ctx["user_code_input"] == ctx["generated_code"]

    # --- Services ---
    async def send_auth_code(
        self, i: Interpreter, ctx: Dict, e: Event
    ) -> Dict[str, Any]:
        delivery_method = ctx.get("delivery_method")
        code = str(random.randint(100000, 999999))
        logging.info(
            f"📞 Invoking service: Sending 2FA code via {delivery_method}..."
        )
        await asyncio.sleep(2.0)

        if delivery_method == "FAIL":
            raise ConnectionError("Upstream SMS gateway failed.")

        logging.info(f"📲 Code sent successfully via {delivery_method}.")
        return {"code": code}
