# -----------------------------------------------------------------------------
# ⚡ IoT Firmware Update Logic
# examples/async/complex/class_approach/without_logic_loader/iot_firmware_update/iot_firmware_update_logic.py
# -----------------------------------------------------------------------------
"""
Class-based logic for IoT device firmware update:

  • store_update_info     – action on check success
  • store_package_path    – action on download success
  • log_applying_update   – log before applying
  • update_current_version– finalize version
  • set_error             – error handler
  • is_update_available   – guard (cond alias)
  • check_for_update      – service invoke
  • download_firmware     – service invoke
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


class FirmwareUpdaterLogic:
    """Implements actions, guards, and services for firmware update."""

    def store_update_info(  # noqa
        self,
        interpreter: Interpreter,  # noqa
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """⬇️ Store latest version info in context.

        Args:
            interpreter: The async Interpreter instance.
            context: Mutable machine context.
            event: DoneEvent with update info in 'data'.
            action_def: Metadata for this action.
        """
        context["latest_version_info"] = event.data
        version = event.data.get("version")
        logger.info(f"⬇️ New version {version} found. Preparing to download.")

    def store_package_path(  # noqa
        self,
        interpreter: Interpreter,  # noqa
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """✅ Store downloaded firmware path in context.

        Args:
            interpreter: The async Interpreter instance.
            context: Mutable machine context.
            event: DoneEvent with 'path' in data.
            action_def: Metadata for this action.
        """
        path = event.data.get("path")
        context["update_package_path"] = path
        logger.info(f"✅ Download complete. Package saved to {path}")

    def log_applying_update(  # noqa
        self,
        interpreter: Interpreter,  # noqa
        context: Dict[str, Any],  # noqa
        event: Event,  # noqa
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """⚡ Log that firmware is being applied."""
        logger.warning(
            "⚡ Applying update... Device will be unresponsive for 5 seconds."
        )

    def update_current_version(  # noqa
        self,
        interpreter: Interpreter,  # noqa
        context: Dict[str, Any],
        event: Event,  # noqa
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """🎉 Finalize current version after successful apply."""
        new_version = context["latest_version_info"]["version"]
        context["current_version"] = new_version
        logger.info(f"🎉 Update successful! Now at version {new_version}.")

    def set_error(  # noqa
        self,
        interpreter: Interpreter,  # noqa
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """❌ Record error from any stage."""
        context["error"] = str(event.data)
        logger.error(f"❌ An error occurred: {context['error']}")

    def is_update_available(
        self, context: Dict[str, Any], event: Event
    ) -> bool:  # noqa
        """✔️ Guard: Proceed only if a newer version is available.

        Args:
            context: Mutable machine context.
            event: DoneEvent with version info in 'data'.

        Returns:
            True if latest version > current_version.
        """
        latest = event.data.get("version")
        current = context.get("current_version", "0.0.0")
        available = latest > current
        if not available:
            logger.info("✔️ No update available.")
        return available

    async def check_for_update_service(  # noqa
        self,
        interpreter: Interpreter,
        context: Dict[str, Any],
        event: Event,  # noqa
    ) -> Dict[str, Any]:
        """☁️ Async service: Check server for updates.

        Args:
            interpreter: The async Interpreter instance.
            context: Mutable machine context.
            event: The triggering Event.

        Returns:
            Dict with 'version' and 'size_kb'.

        Raises:
            ConnectionError: On simulated server unreachable.
        """
        logger.info("☁️ Checking update server...")
        await asyncio.sleep(1.5)
        if random.random() < 0.1:
            raise ConnectionError("Update server is unreachable.")
        return {"version": "1.1.0", "size_kb": 2048}

    async def download_firmware_service(  # noqa
        self,
        interpreter: Interpreter,
        context: Dict[str, Any],
        event: Event,  # noqa
    ) -> Dict[str, Any]:
        """🌐 Async service: Download firmware package.

        Args:
            interpreter: The async Interpreter instance.
            context: Mutable machine context.
            event: The triggering Event.

        Returns:
            Dict with 'path' to downloaded package.

        Raises:
            IOError: On simulated checksum failure.
        """
        version = context["latest_version_info"]["version"]
        logger.info(f"🌐 Downloading version {version}...")
        await asyncio.sleep(2.5)
        if random.random() < 0.1:
            raise IOError("Download corrupted (checksum mismatch).")
        return {"path": f"/tmp/firmware-{version}.bin"}
