# -------------------------------------------------------------------------------
# 🔐 Two-Factor Auth Logic
# examples/async/complex/class_approach/with_logic_loader/two_factor_auth/two_factor_auth_logic.py
# -------------------------------------------------------------------------------
"""
Class-based logic for an asynchronous two-factor authentication (2FA) system.
"""

import asyncio
import logging
import random
from typing import Any, Dict

from xstate_statemachine import Interpreter, Event, ActionDefinition

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


class TwoFactorAuthLogic:
    """Implements the core actions, guards, and services for 2FA."""

    # -------------------------------------------------------------------------
    # 🛠️ Actions
    # -------------------------------------------------------------------------

    def store_generated_code(  # noqa
        self,
        interpreter: Interpreter,  # noqa
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """🤫 Save generated 2FA code in context.

        Args:
            interpreter: The running state machine interpreter.
            context: Mutable context dict of the machine.
            event: The triggering event carrying `data`.
            action_def: Metadata for this action.
        """
        code = event.data.get("code")
        context["generated_code"] = code
        logger.info(f"🤫 Generated code stored: {code}")

    def set_error(  # noqa
        self,
        interpreter: Interpreter,
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """🔥 Record delivery error and trigger failure transition.

        Args:
            interpreter: The running state machine interpreter.
            context: Mutable context dict of the machine.
            event: The triggering event carrying error in `data`.
            action_def: Metadata for this action.
        """
        error_msg = str(event.data)
        context["error"] = error_msg
        logger.error(f"🔥 Delivery failed: {error_msg}")
        # Dispatch top-level failure event
        asyncio.create_task(interpreter.send("DELIVERY_FAILED"))

    def store_user_input(  # noqa
        self,
        interpreter: Interpreter,  # noqa
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """⌨️ Save user-submitted code input in context.

        Args:
            interpreter: The running state machine interpreter.
            context: Mutable context dict of the machine.
            event: The triggering event carrying `payload`.
            action_def: Metadata for this action.
        """
        user_code = event.payload.get("code")
        context["user_code_input"] = user_code
        logger.info(f"⌨️ User submitted code: {user_code}")

    def increment_attempts(  # noqa
        self,
        interpreter: Interpreter,  # noqa
        context: Dict[str, Any],
        event: Event,  # noqa
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """❌ Log and count an incorrect attempt.

        Args:
            interpreter: The running state machine interpreter.
            context: Mutable context dict of the machine.
            event: The triggering event.
            action_def: Metadata for this action.
        """
        context["attempts"] = context.get("attempts", 0) + 1
        logger.warning("❌ Incorrect code. Please try again.")

    async def notify_validation_success(  # noqa
        self,
        interpreter: Interpreter,
        context: Dict[str, Any],  # noqa
        event: Event,  # noqa
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """✅ Notify other regions of successful validation.

        Args:
            interpreter: The running state machine interpreter.
            context: Mutable context dict of the machine.
            event: The triggering event.
            action_def: Metadata for this action.
        """
        logger.info("✅ Code validation successful!")
        await interpreter.send("VALIDATION_SUCCESS")

    def log_final_success(  # noqa
        self,
        interpreter: Interpreter,  # noqa
        context: Dict[str, Any],  # noqa
        event: Event,  # noqa
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """🎉 Log completion of successful authentication.

        Args:
            interpreter: The running state machine interpreter.
            context: Mutable context dict of the machine.
            event: The triggering event.
            action_def: Metadata for this action.
        """
        logger.info("🎉🎉🎉 Two-factor authentication succeeded!")

    # -------------------------------------------------------------------------
    # 🛡️ Guards
    # -------------------------------------------------------------------------

    def is_code_correct(
        self, context: Dict[str, Any], event: Event
    ) -> bool:  # noqa
        """✔️ Guard: Check if user input matches generated code.

        Args:
            context: Mutable context dict of the machine.
            event: The triggering event.

        Returns:
            True if codes match, False otherwise.
        """
        return context.get("user_code_input") == context.get("generated_code")

    # -------------------------------------------------------------------------
    # 🚀 Services
    # -------------------------------------------------------------------------

    async def send_auth_code(  # noqa
        self,
        interpreter: Interpreter,  # noqa
        context: Dict[str, Any],
        event: Event,  # noqa
    ) -> Dict[str, Any]:
        """📲 Async service: Generate and send 2FA code.

        Args:
            interpreter: The running state machine interpreter.
            context: Mutable context dict of the machine.
            event: The triggering event.

        Returns:
            A dict containing the generated `code`.

        Raises:
            ConnectionError: If simulated delivery fails.
        """
        method = context.get("delivery_method", "SMS")
        code = str(random.randint(100_000, 999_999))
        logger.info(f"📞 Sending 2FA code via {method}...")
        await asyncio.sleep(2.0)

        if method == "FAIL":
            raise ConnectionError("Upstream SMS gateway failed.")

        logger.info(f"📲 Code {code} sent successfully via {method}")
        return {"code": code}
