# examples/sync/super_complex/class_approach/with_logic_loader/audio_wizard_runner.py
# -------------------------------------------------------------------------------
# 🎙️ Audio Wizard Runner
# -------------------------------------------------------------------------------
"""
Demo runner for the “Audio recording with websocket” machine,
using snake_case action & guard names aligned to the updated JSON.
"""

import json
import logging
import pathlib
import sys
import time
from typing import Any, Dict

from audio_wizard_logic import AudioWizardLogic  # noqa: E402
from src.xstate_statemachine import create_machine, SyncInterpreter

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    datefmt="%H:%M:%S",
)

# ensure project root on sys.path if needed
ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(ROOT.parents[4]))  # adjust to reach examples folder


def load_config() -> Dict[str, Any]:
    """🔍 Load the JSON config from disk."""
    return json.loads((ROOT / "audio_wizard.json").read_text(encoding="utf-8"))


def scenario_happy(interp: SyncInterpreter) -> None:
    """🏆 Happy‐path: connect, record chunks, stop, and close."""
    logger.info("🚩 Running HAPPY path")
    time.sleep(1)  # simulate some delay before starting
    interp.send("startWebsocket")
    time.sleep(1)  # simulate connection delay
    interp.send("🟢 wsConnectSuccess", token="TOK123")
    time.sleep(1)  # simulate processing time
    interp.send("startOrResumeRecording")
    time.sleep(1)  # simulate recording setup delay
    for i in range(3):
        interp.send("dataAvailable", message=f"chunk-{i}")
        time.sleep(1)
    interp.send("stopRecording")
    time.sleep(2)
    logger.info("✅ End state → %s", interp.current_state_ids)


def scenario_token_expired(interp: SyncInterpreter) -> None:
    """⚠️ Expiry‐path: preset expired token leads to `abandonned`."""
    logger.info("🚩 Running EXPIRE path")
    interp.context["token"] = "OLD"
    interp.context["token_expired"] = True
    interp.send("startWebsocket")
    time.sleep(1)  # simulate connection delay
    interp.send("🔴 wsConnectError")
    time.sleep(1)  # simulate error handling delay
    logger.info("🛑 End state → %s", interp.current_state_ids)


def main() -> None:
    """🚀 Build interpreter and run both scenarios end-to-end."""
    config = load_config()
    logic = AudioWizardLogic()
    machine = create_machine(config, logic_providers=[logic])
    interp = SyncInterpreter(machine)
    interp.start()

    scenario_happy(interp)
    interp.stop()

    # fresh interpreter for expiry scenario
    interp = SyncInterpreter(machine)
    interp.start()
    scenario_token_expired(interp)
    interp.stop()


if __name__ == "__main__":
    main()
