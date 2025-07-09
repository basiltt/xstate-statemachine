# examples/async/complex/class_approach/without_logic_loader/iot_firmware_update/iot_firmware_update_logic.py
import asyncio
import logging
import random
from typing import Dict, Any

from src.xstate_statemachine import Interpreter, Event, ActionDefinition


class FirmwareUpdaterLogic:
    """Class-based logic for the IoT device firmware update process."""

    # --- Actions ---
    def store_update_info(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        ctx["latest_version_info"] = e.data
        logging.info(
            f"⬇️  New version {e.data.get('version')} found. Preparing to download."
        )

    def store_package_path(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        ctx["update_package_path"] = e.data.get("path")
        logging.info(
            f"✅ Download complete. Package saved to {ctx['update_package_path']}"
        )

    def log_applying_update(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        logging.warning(
            "⚡ Applying update... Device will be unresponsive for 5 seconds."
        )

    def update_current_version(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        ctx["current_version"] = ctx["latest_version_info"]["version"]
        logging.info(
            f"🎉 Update successful! Device is now on version {ctx['current_version']}."
        )

    def set_error(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        ctx["error"] = str(e.data)
        logging.error(f"❌ An error occurred: {ctx['error']}")

    # --- Guards (as methods, though JSON uses 'cond' which is an alias) ---
    def is_update_available(self, ctx: Dict, e: Event) -> bool:
        """The 'cond' property in XState is an alias for 'guard'."""
        latest_version = e.data.get("version")
        return latest_version > ctx.get("current_version", "0.0.0")

    # --- Services ---
    async def check_for_update_service(
        self, i: Interpreter, ctx: Dict, e: Event
    ) -> Dict[str, Any]:
        logging.info("  -> ☁️  Invoking service: Checking update server...")
        await asyncio.sleep(1.5)
        if random.random() < 0.1:
            raise ConnectionError("Update server is unreachable.")
        return {"version": "1.1.0", "size_kb": 2048}

    async def download_firmware_service(
        self, i: Interpreter, ctx: Dict, e: Event
    ) -> Dict[str, Any]:
        version_to_download = ctx["latest_version_info"]["version"]
        logging.info(
            f"  -> 🌐 Invoking service: Downloading version {version_to_download}..."
        )
        await asyncio.sleep(2.5)
        if random.random() < 0.1:
            raise IOError("Download corrupted (checksum mismatch).")
        return {"path": f"/tmp/firmware-{version_to_download}.bin"}
