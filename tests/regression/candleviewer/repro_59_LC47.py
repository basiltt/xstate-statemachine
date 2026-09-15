"""LC-47 repro: target resolution WRITES to `transition.target_str` on the
`TransitionDefinition` objects that live on the shared `MachineNode`.

`base_interpreter.py:1195` and `sync_interpreter.py:1478` both do
`transition.target_str = tgt` after a successful `resolve_target_state`,
turning the machine *definition* into an accidental memoisation cache. The
`MachineNode` is explicitly designed to be shared -- the documented pattern is
to `create_machine()` once and hand the same node to many interpreters -- so
every interpreter writes into state that all the others read.

This is a code-quality / latent-hazard report, not a live-failure report: the
value written is currently always identical to the authored one, because the
FIRST resolution attempt (`(target_str, source)`) already succeeds for every
target form the resolver accepts. So the observable state is unchanged; what
this script shows is that the write happens at all, on a shared object, from
many interpreters, including concurrently from threads.

`target_str` is installed as a watched property so every assignment is
counted. Exit code 1 if the shared definition object is written to during
interpretation.
"""

from __future__ import annotations

import logging
import sys
import threading

from xstate_statemachine import SyncInterpreter, create_machine

logging.disable(logging.CRITICAL)

CONFIG = {
    "id": "order",
    "initial": "idle",
    "states": {
        "idle": {"on": {"SUBMIT": "open"}},
        "open": {"on": {"CLOSE": "closed"}},
        "closed": {"type": "final"},
    },
}

# 🌳 ONE shared MachineNode -- the documented, 19x-cheaper pattern.
MACHINE = create_machine(CONFIG)
TRANSITION = MACHINE.states["idle"].on["SUBMIT"][0]

WRITES: list[tuple[str, str]] = []
LOCK = threading.Lock()


def watch(transition) -> None:
    """Replace `target_str` with a property that records every assignment."""
    stored = transition.__dict__.pop("target_str")
    transition.__dict__["_target_str"] = stored

    class Watched(type(transition)):
        @property
        def target_str(self):
            return self.__dict__["_target_str"]

        @target_str.setter
        def target_str(self, value):
            with LOCK:
                WRITES.append((threading.current_thread().name, value))
            self.__dict__["_target_str"] = value

    transition.__class__ = Watched


authored = TRANSITION.target_str
watch(TRANSITION)
print(f"OBSERVED target_str as authored in config  : {authored!r}")

# 1️⃣ A single interpreter writes to the shared definition object.
it1 = SyncInterpreter(MACHINE).start()
it1.send("SUBMIT")
print(f"OBSERVED writes after 1 interpreter, 1 event: {WRITES}")

# 2️⃣ A second interpreter over the SAME node writes to the same field.
it2 = SyncInterpreter(MACHINE).start()
it2.send("SUBMIT")
print(f"OBSERVED writes after a 2nd interpreter     : {len(WRITES)}")

# 3️⃣ Concurrent SyncInterpreters (whose `after` timers are real threads, so
#    nothing serialises them onto one loop) all write this shared field.
WRITES.clear()


def drive() -> None:
    it = SyncInterpreter(MACHINE).start()
    for _ in range(100):
        it.send("SUBMIT")
        it.send("CLOSE")


threads = [threading.Thread(target=drive, name=f"w{i}") for i in range(8)]
for t in threads:
    t.start()
for t in threads:
    t.join()
writers = sorted({name for name, _ in WRITES})
print(
    f"OBSERVED 8 threads x 100 cycles -> {len(WRITES)} writes to ONE shared "
    f"definition object from threads {writers}"
)
print(f"OBSERVED values written                     : "
      f"{sorted({v for _, v in WRITES})}")
print(f"OBSERVED final target_str                   : {TRANSITION.target_str!r}")
print(
    "EXPECTED zero writes: the machine definition should be immutable under "
    "interpretation, with resolution results memoised in a per-interpreter "
    "cache keyed by id(transition)"
)

sys.exit(0 if not WRITES else 1)
