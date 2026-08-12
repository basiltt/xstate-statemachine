# examples/sync/super_complex/class_approach/with_logic_loader/install_wizard/install_wizard_logic.py
# -----------------------------------------------------------------------------
# 🛠️ Install Wizard Logic
# -----------------------------------------------------------------------------
"""
Class-based logic for a multistep installation wizard:

  • Stores network/database/admin configs
  • Logs start, success, and failure
  • Runs synchronous installation steps service
"""

import logging
import time
from typing import Any, Dict

from xstate_statemachine import SyncInterpreter, Event, ActionDefinition

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


class InstallWizardLogic:
    """Encapsulates actions and services for the installation wizard."""

    # -------------------------------------------------------------------------
    # ⚙️ Actions
    # -------------------------------------------------------------------------

    def store_network_config(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        ctx: Dict[str, Any],
        evt: Event,
        _action: ActionDefinition,
    ) -> None:
        """🌐 Action: Save network settings from payload."""
        ctx.setdefault("config", {})["network"] = evt.payload
        logger.info("🔧 Configured Network: %s", evt.payload)

    def store_database_config(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        ctx: Dict[str, Any],
        evt: Event,
        _action: ActionDefinition,
    ) -> None:
        """🗄️ Action: Save database settings from payload."""
        ctx.setdefault("config", {})["database"] = evt.payload
        logger.info("🔧 Configured Database: %s", evt.payload)

    def store_admin_config(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        ctx: Dict[str, Any],
        evt: Event,
        _action: ActionDefinition,
    ) -> None:
        """👤 Action: Save admin user settings and proceed."""
        ctx.setdefault("config", {})["admin"] = evt.payload
        logger.info("🔧 Configured Admin User: %s", evt.payload)
        logger.info("✅ Configuration complete. Proceeding to installation.")

    def set_error(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        ctx: Dict[str, Any],
        evt: Event,
        _action: ActionDefinition,
    ) -> None:
        """❌ Action: Record installation error from service data."""
        ctx["error"] = str(evt.data)
        logger.error("❌ Installation failed: %s", ctx["error"])

    def log_install_start(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        ctx: Dict[str, Any],  # noqa
        _evt: Event,
        _action: ActionDefinition,
    ) -> None:
        """🚀 Action: Log beginning of installation service."""
        logger.info("🚀 Starting installation process...")

    def log_success(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        ctx: Dict[str, Any],  # noqa
        _evt: Event,
        _action: ActionDefinition,
    ) -> None:
        """🎉 Action: Log successful installation completion."""
        logger.info("🎉 Installation finished successfully!")

    def log_failure(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        ctx: Dict[str, Any],  # noqa
        _evt: Event,
        _action: ActionDefinition,
    ) -> None:
        """💥 Action: Log installation failure."""
        logger.error("💥 Installation failed. Please check logs.")

    # -------------------------------------------------------------------------
    # 🛠️ Services
    # -------------------------------------------------------------------------

    def run_installation_steps(  # noqa
        self,
        interpreter: SyncInterpreter,
        ctx: Dict[str, Any],
        _evt: Event,
    ) -> Dict[str, Any]:
        """🔧 Service: Perform all installation steps synchronously.

        Args:
            interpreter: The SyncInterpreter instance.
            ctx: Mutable context holding install_log and config.
            _evt: Triggering Event.

        Returns:
            Dict with status and number of steps executed.

        Raises:
            SystemError: On an unsupported database version.
        """
        ctx.setdefault("install_log", [])
        db_cfg = ctx["config"].get("database", {})

        # Step 1: Copy files
        interpreter.send({"type": "INSTALL_STEP", "step": "copying_files"})
        logger.info("  -> Copying application files...")
        time.sleep(1)
        ctx["install_log"].append("Copied files.")

        # Step 2: Run scripts
        interpreter.send({"type": "INSTALL_STEP", "step": "running_scripts"})
        logger.info("  -> Running DB migration scripts...")
        time.sleep(1.5)
        if db_cfg.get("type") == "unsupported_db":
            raise SystemError("Database version is not supported.")
        ctx["install_log"].append("Ran DB migrations.")

        # Step 3: Finalize
        interpreter.send({"type": "INSTALL_STEP", "step": "finalizing"})
        logger.info("  -> Finalizing installation...")
        time.sleep(0.5)
        ctx["install_log"].append("Finalized setup.")

        return {
            "status": "complete",
            "steps_executed": len(ctx["install_log"]),
        }
