# src/xstate_statemachine/__main__.py
# -----------------------------------------------------------------------------
# 🚪 `python -m xstate_statemachine` -- the console script without the .exe
# -----------------------------------------------------------------------------
# 🏛️ Why this exists: on Windows, pip realises the `xsm` entry point as a
#    generic unsigned launcher (`Scripts\xsm.exe`). Machines governed by
#    Windows Defender Application Control / AppLocker / Smart App Control
#    block that launcher ("An Application Control policy has blocked this
#    file") while `python.exe` itself is allowed. Running the CLI through
#    the interpreter -- `python -m xstate_statemachine` -- sidesteps the
#    launcher entirely, so this module makes the shortest such spelling
#    work. `python -m xstate_statemachine.cli` continues to work as well.
# -----------------------------------------------------------------------------
"""Run the `xsm` command-line tool via ``python -m xstate_statemachine``."""

from .cli.__main__ import main

if __name__ == "__main__":  # pragma: no cover -- exercised via subprocess
    main()
