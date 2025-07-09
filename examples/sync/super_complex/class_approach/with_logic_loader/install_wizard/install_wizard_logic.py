# examples/sync/super_complex/class_approach/with_logic_loader/install_wizard/install_wizard_logic.py

import logging
import time
from typing import Dict, Any

from src.xstate_statemachine import SyncInterpreter, Event, ActionDefinition


class InstallWizardLogic:
    """Class-based logic for the multi-step installation wizard."""

    # --- Actions ---
    def store_network_config(
        self, i: SyncInterpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        ctx["config"]["network"] = e.payload
        logging.info(f"🔧 Configured Network: {e.payload}")

    def store_database_config(
        self, i: SyncInterpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        ctx["config"]["database"] = e.payload
        logging.info(f"🔧 Configured Database: {e.payload}")

    def store_admin_config(
        self, i: SyncInterpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        ctx["config"]["admin"] = e.payload
        logging.info(f"🔧 Configured Admin User: {e.payload}")
        logging.info("✅ Configuration complete. Proceeding to installation.")

    def set_error(
        self, i: SyncInterpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        ctx["error"] = str(e.data)
        logging.error(f"❌ Installation failed: {ctx['error']}")

    def log_install_start(
        self, i: SyncInterpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        logging.info("🚀 Starting installation process...")

    def log_success(
        self, i: SyncInterpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        logging.info("🎉🎉🎉 Installation finished successfully! 🎉🎉🎉")

    def log_failure(
        self, i: SyncInterpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        logging.error("💥 Installation failed. Please check the logs.")

    # --- Services ---
    def run_installation_steps(
        self, i: SyncInterpreter, ctx: Dict, e: Event
    ) -> Dict[str, Any]:
        """A synchronous service simulating the entire installation process."""
        db_config = ctx["config"]["database"]

        # Step 1: Copy files
        i.send({"type": "INSTALL_STEP", "step": "copying_files"})
        logging.info("  -> Copying application files...")
        time.sleep(1)
        ctx["install_log"].append("Copied files.")

        # Step 2: Run scripts
        i.send({"type": "INSTALL_STEP", "step": "running_scripts"})
        logging.info("  -> Running database migration scripts...")
        time.sleep(1.5)

        # Simulate a potential failure
        if db_config.get("type") == "unsupported_db":
            raise SystemError("Database version is not supported.")

        ctx["install_log"].append("Ran DB migrations.")

        # Step 3: Finalize
        i.send({"type": "INSTALL_STEP", "step": "finalizing"})
        logging.info("  -> Finalizing installation...")
        time.sleep(0.5)
        ctx["install_log"].append("Finalized setup.")

        return {
            "status": "complete",
            "steps_executed": len(ctx["install_log"]),
        }
