# examples/sync/features/history_shallow_deep/history_shallow_deep_runner.py
# -----------------------------------------------------------------------------
# 🕰️ Shallow vs. deep history on the SAME region
# -----------------------------------------------------------------------------
"""Contrasts `history: "shallow"` and `history: "deep"` side by side.

A history pseudostate remembers where a compound region was when it was
last exited. The two kinds differ in how MUCH they remember:

* ``"shallow"`` (the default) restores only the parent's immediate child;
  that child's own ``initial`` chain then applies beneath it.
* ``"deep"`` restores the full nested configuration, right down to the
  leaf that was active.

One parent may declare both kinds at once -- history is recorded once per
parent and the shallow/deep distinction is applied at RESTORE time -- so
the same region is left from a nested grandchild and re-entered through
each pseudostate in turn. Use shallow for "go back to the tab I was on",
deep for "resume exactly where I was inside that tab".
"""

import logging
import os
import sys
from typing import Any, Dict

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
)
from xstate_statemachine import SyncInterpreter, create_machine

if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - platform detail
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# An editor with two tabs; the "code" tab has its own nested view modes.
CONFIG: Dict[str, Any] = {
    "id": "editor",
    "initial": "tabs",
    "states": {
        "tabs": {
            "initial": "preview",
            "on": {"CLOSE": "closed"},
            "states": {
                "preview": {"on": {"CODE": "code"}},
                "code": {
                    "initial": "read",
                    "states": {
                        "read": {"on": {"EDIT": "edit"}},
                        "edit": {},
                    },
                },
                "shallowHist": {"type": "history", "history": "shallow"},
                "deepHist": {"type": "history", "history": "deep"},
            },
        },
        "closed": {
            "on": {
                "REOPEN_TAB": "tabs.shallowHist",
                "RESUME_EXACTLY": "tabs.deepHist",
            }
        },
    },
}


def leave_from_code_edit(interp: SyncInterpreter) -> None:
    """Drive the editor to tabs.code.edit, then close it."""
    interp.send("CODE")
    interp.send("EDIT")
    assert interp.current_state_ids == {"editor.tabs.code.edit"}
    interp.send("CLOSE")
    assert interp.current_state_ids == {"editor.closed"}


def main() -> None:
    machine = create_machine(CONFIG)

    # --- shallow: back to the "code" tab, but at its INITIAL view ("read")
    interp = SyncInterpreter(machine).start()
    leave_from_code_edit(interp)
    interp.send("REOPEN_TAB")
    shallow = set(interp.current_state_ids)
    logger.info("shallow history restored -> %s", sorted(shallow))
    interp.stop()

    # --- deep: back to the "code" tab AND the exact view ("edit")
    interp = SyncInterpreter(machine).start()
    leave_from_code_edit(interp)
    interp.send("RESUME_EXACTLY")
    deep = set(interp.current_state_ids)
    logger.info("deep history restored    -> %s", sorted(deep))
    interp.stop()

    assert shallow == {"editor.tabs.code.read"}, shallow
    assert deep == {"editor.tabs.code.edit"}, deep
    print("shallow -> code.read (tab remembered, view reset)")
    print("deep    -> code.edit (tab AND nested view remembered)")


if __name__ == "__main__":
    main()
