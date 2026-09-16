"""xstate-statemachine adapter: native asyncio Interpreter engine.

Only S8 (async_dispatch) is meaningful here -- it drives the flat toggle
machine through the library's native asyncio interpreter loop
(`Interpreter`, as opposed to `SyncInterpreter`). Every other scenario is
identical to (and already covered by) `xstate_sync.py`'s `SyncInterpreter`
path, so they are intentionally left unsupported here to avoid double
counting the same code paths under two adapter names.
"""

from __future__ import annotations

import asyncio

from xstate_statemachine import Interpreter, __version__, create_machine

LIB_NAME = "xstate-statemachine (async)"
LIB_VERSION = __version__

CAPABILITY_NOTES = {
    "S1": "identical flat-toggle path already benchmarked via SyncInterpreter in xstate_sync.py",
    "S2": "identical guarded-context path already benchmarked via SyncInterpreter in xstate_sync.py",
    "S3": "identical hierarchical path already benchmarked via SyncInterpreter in xstate_sync.py",
    "S4": "identical parallel path already benchmarked via SyncInterpreter in xstate_sync.py",
    "S5": "identical construction path already benchmarked via SyncInterpreter in xstate_sync.py",
    "S6": "identical many-instances path already benchmarked via SyncInterpreter in xstate_sync.py",
    "S7": "identical delayed-transition path already benchmarked via SyncInterpreter in xstate_sync.py",
}

_S1_CONFIG = {
    "id": "toggle",
    "initial": "A",
    "states": {
        "A": {"on": {"NEXT": "B"}},
        "B": {"on": {"NEXT": "A"}},
    },
}


def setup_S1():
    return None


def setup_S2():
    return None


def setup_S3():
    return None


def setup_S4():
    return None


def setup_S5():
    return None


def setup_S6():
    return None


def setup_S7():
    return None


def setup_S8():
    async def _run(n: int, interp: Interpreter) -> None:
        for _ in range(n):
            await interp.send("NEXT", wait=True)

    def hot(n: int) -> None:
        machine = create_machine(_S1_CONFIG)

        async def _main() -> Interpreter:
            interp = await Interpreter(machine).start()
            await _run(n, interp)
            await interp.stop()
            return interp

        interp = asyncio.run(_main())
        assert interp.current_state_ids <= {"toggle.A", "toggle.B"}

    return hot
