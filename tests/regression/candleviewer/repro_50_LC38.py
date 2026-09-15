"""LC-38 repro: `SyncInterpreter` is not single-threaded.

`sync_interpreter.py` starts one *daemon OS thread per `after` timer*
(`_after_timer` -> `threading.Thread(target=timer_thread, ...)`).
When the deadline elapses that thread calls `self.send(...)`, which appends to
`self._event_queue` and runs the full macrostep -- entry/exit actions, guards
and `context` mutation -- on the timer thread, concurrently with whatever the
owning thread is doing. There is no `threading.Lock` anywhere in the
codebase, and `_is_processing` is a plain check-then-set boolean
(`sync_interpreter.py:337-340`), which is a textbook TOCTOU race, not a
mutex.

This script demonstrates both halves:

  1. The state advances and context is mutated while the main thread merely
     `time.sleep()`s -- no `send()`, no pump -- and the mutating thread is
     NOT `MainThread`.
  2. A main-thread `send()` loop racing the timers loses increments: the
     counter ends below the number of writes actually performed, because
     `context["n"] += 1` from two threads is not atomic across the
     read-modify-write the interpreter performs.

Exit code 1 if either non-single-threaded behaviour is observed.
"""

from __future__ import annotations

import logging
import sys
import threading
import time

from xstate_statemachine import MachineLogic, SyncInterpreter, create_machine

logging.disable(logging.CRITICAL)

DELAY_MS = 150

CFG = {
    "id": "order",
    "initial": "submitting",
    "context": {"n": 0, "threads": []},
    "states": {
        "submitting": {
            "after": {DELAY_MS: {"target": "timed_out", "actions": ["bump"]}},
            "on": {"TICK": {"actions": ["bump"]}},
        },
        "timed_out": {"type": "final"},
    },
}

writes = 0
writes_lock = threading.Lock()


def bump(interpreter, context, event, action_def):  # noqa: ANN001
    global writes
    name = threading.current_thread().name
    if name not in context["threads"]:
        context["threads"].append(name)
    with writes_lock:
        writes += 1
    # Widen the read-modify-write window the interpreter offers to any
    # concurrent thread. No lock protects `context` in the library.
    n = context["n"]
    time.sleep(0.002)
    context["n"] = n + 1


def build() -> SyncInterpreter:
    m = create_machine(CFG, logic=MachineLogic(actions={"bump": bump}))
    return SyncInterpreter(m).start()


def main() -> int:
    # --- 1. advance with no event pump at all -------------------------------
    sm = build()
    before = sm.current_state_ids.copy()
    main_name = threading.current_thread().name
    time.sleep(DELAY_MS / 1000 + 0.3)
    after = sm.current_state_ids.copy()
    off_main = [t for t in sm.context["threads"] if t != main_name]

    print(f"OBSERVED: state before sleep = {sorted(before)}")
    print(f"OBSERVED: state after pure time.sleep() = {sorted(after)}")
    print(f"OBSERVED: threads that mutated context = {sm.context['threads']}")
    print(f"OBSERVED: non-main mutating threads = {off_main}")
    print(
        "EXPECTED: a synchronous interpreter never advances without a "
        "send(); all context mutation happens on the calling thread."
    )
    advanced_off_thread = bool(off_main)

    # --- 2. lost update race -------------------------------------------------
    global writes
    writes = 0
    sm2 = build()
    deadline = time.perf_counter() + (DELAY_MS / 1000 + 0.3)
    while time.perf_counter() < deadline:
        try:
            sm2.send("TICK")
        except Exception:  # interpreter reached final state
            break
    time.sleep(0.2)
    counted = sm2.context["n"]
    print(
        f"OBSERVED: bump() executed {writes} times, context['n'] = {counted}"
    )
    print("EXPECTED: context['n'] == number of bump() executions.")
    lost_update = counted != writes

    return 0 if not (advanced_off_thread or lost_update) else 1


if __name__ == "__main__":
    sys.exit(main())
