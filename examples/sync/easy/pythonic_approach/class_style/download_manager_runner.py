# examples/sync/easy/pythonic_approach/class_style/download_manager_runner.py
# -----------------------------------------------------------------------------
# ⬇️ Download Manager — class-style Pythonic API
# -----------------------------------------------------------------------------
# Demonstrates the `StateMachine` subclass: states are class attributes and
# logic lives in `@action` / `@guard` / `@service` decorated METHODS, so
# related behaviour sits together in one namespace.
#
# The machine lives in `download_manager_logic.py`, GENERATED from
# `download_manager.json`:
#
#     xsm generate-template download_manager.json \
#         --template pythonic-class --async-mode no
#
# Implement your logic in the generated stubs; keep the runner separate, since
# regeneration overwrites the machine structure.
# -----------------------------------------------------------------------------
"""Walk the download-manager machine through two scenarios."""

import logging
import os
import sys

from xstate_statemachine import SyncInterpreter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# 📝 The class template exposes the machine through the StateMachine
#    subclass itself rather than a build() function.
from download_manager_logic import DownloadManagerMachine  # noqa: E402


def build():
    """Build the machine from the generated StateMachine subclass."""
    return DownloadManagerMachine.create_machine()


logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def _show(interpreter: SyncInterpreter, label: str) -> None:
    """Print the active states plus any tags they carry."""
    tags = sorted(interpreter.tags)
    suffix = f"   tags={tags}" if tags else ""
    logger.info(
        "%-20s %s%s", label, sorted(interpreter.current_state_ids), suffix
    )


def scenario_pause_and_resume() -> None:
    """START -> PAUSE -> RESUME -> CANCEL, without ever finishing."""
    logger.info("--- Scenario 1: pause and resume ---")
    interpreter = SyncInterpreter(build()).start()

    _show(interpreter, "initial")
    interpreter.send("START")
    _show(interpreter, "after START")

    # 🏷️ `downloading` and `paused` both carry the "busy" tag, so a UI can
    #    show a spinner with one check instead of enumerating state ids.
    interpreter.send("PAUSE")
    _show(interpreter, "after PAUSE")

    interpreter.send("RESUME")
    _show(interpreter, "after RESUME")

    interpreter.send("CANCEL")
    _show(interpreter, "after CANCEL")
    interpreter.stop()


def scenario_guarded_retry() -> None:
    """RETRY is guarded by `canRetry`, so failure is not always recoverable."""
    logger.info("--- Scenario 2: guarded retry ---")
    interpreter = SyncInterpreter(build()).start()

    interpreter.send("START")
    _show(interpreter, "after START")

    # 📝 `matches()` accepts the ORIGINAL state name from the JSON, even when
    #    the generated Python binding was renamed to be a valid identifier.
    if interpreter.matches("downloadManager.complete"):
        logger.info("download finished before we could interfere")
    else:
        interpreter.send("RETRY")
        _show(interpreter, "after RETRY")

    interpreter.stop()


def main() -> None:
    """Execute both scenarios."""
    scenario_pause_and_resume()
    logger.info("")
    scenario_guarded_retry()
    logger.info("")
    logger.info("Simulation complete.")


if __name__ == "__main__":
    main()
