"""
Demo runner for the “Audio recording with websocket” machine
   • loads the JSON config
   • wires AudioWizardLogic via LogicLoader
   • drives two scenarios to exercise most branches
"""

import json
import logging
import pathlib
import sys
import time

from src.xstate_statemachine import create_machine, SyncInterpreter

# -------------------------------------------------------------------#
# logging                                                            #
# -------------------------------------------------------------------#
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(message)s", datefmt="%H:%M:%S"
)
_log = logging.getLogger(__name__)

# -------------------------------------------------------------------#
# project import path                                                #
# -------------------------------------------------------------------#
ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent.parent.parent.parent))  # adjust if needed

from audio_wizard_logic import AudioWizardLogic  # noqa: E402


def load_config() -> dict:
    cfg_path = ROOT / "audio_wizard.json"
    if not cfg_path.exists():  # fall-back to inline string
        return json.loads(CONFIG_JSON)
    return json.loads(cfg_path.read_text(encoding="utf-8"))


def scenario_happy(interpreter: SyncInterpreter) -> None:
    """
    Successful flow:
       1. open WebSocket ► token missing ► submitting ► token received
       2. auto connect ► wsConnectSuccess ► connected
       3. start recording ► send 3 chunks ► stop ► done ► closed
    """
    _log.info("🚩  Running HAPPY path")
    interpreter.send("startWebsocket")
    interpreter.send("🟢 sessionSubmitSucces", token="TOK123")

    # start the recorder once websocket connected
    interpreter.send("startOrResumeRecording")
    for i in range(3):
        interpreter.send("dataAvailable", message=f"chunk-{i}".encode(), seq=i)
        time.sleep(0.01)
    interpreter.send("stopRecording")  # queues stop_recording message

    # drain send/receive loop
    time.sleep(0.05)
    _log.info("✅  End state → %s", interpreter.current_state_ids)


def scenario_token_expired(interpreter: SyncInterpreter) -> None:
    """
    Token expires → submitting again → abandoned on error
    """
    _log.info("🚩  Running EXPIRE path")
    interpreter.context["token"] = "OLD"
    interpreter.context["token_expired"] = True

    interpreter.send("startWebsocket")  # goes to disconnected.waiting
    # waiting always → guard “Session expired” true?  yes → submitting
    interpreter.send("🔴 sessionSubmitError")  # onError branch
    _log.info("🛑  End state → %s", interpreter.current_state_ids)


def main() -> None:
    config = load_config()
    logic = AudioWizardLogic()

    machine = create_machine(config, logic_providers=[logic])
    interp = SyncInterpreter(machine)
    interp.start()

    scenario_happy(interp)
    interp.stop()

    # fresh interpreter for second run
    interp = SyncInterpreter(machine)
    interp.start()
    scenario_token_expired(interp)
    interp.stop()


# -------------------------------------------------------------------#
# inline JSON in case you don’t store it as a separate file          #
# -------------------------------------------------------------------#
CONFIG_JSON = r"""
PUT-THE-LONG-JSON-YOU-PASTED-HERE
"""

if __name__ == "__main__":
    main()
