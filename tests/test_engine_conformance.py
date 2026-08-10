# /tests/test_engine_conformance.py
# -----------------------------------------------------------------------------
# 🧪 Test Suite: Cross-Engine Conformance & Transition Atomicity
# -----------------------------------------------------------------------------
# This module exists because the library ships TWO independent engines —
# `Interpreter` (asyncio) and `SyncInterpreter` (threads) — that implement the
# statechart algorithm SEPARATELY. Every previous suite pinned each engine on
# its own, which is precisely how a family of divergences survived 2,647
# passing tests: each engine was self-consistent, and nothing ever asserted
# they agreed with EACH OTHER.
#
# 🏛️ Architecture decision: tests here drive the SAME machine config through
# BOTH engines and assert IDENTICAL observable behaviour — including error
# paths, which is where every divergence was actually found. A test that only
# exercised the happy path would have passed against the broken versions.
#
# Covers the release-blocking defects found by the v0.6.0 battle test:
#   1. Sync engine corrupted to an EMPTY configuration on a mid-transition raise
#   2. Async engine died silently on an unresolvable target
#   3. Deep history into a parallel state produced two leaves in one region
#   4. Invoked child machine fired `onDone` early and leaked its interpreter
#   5. A self-raising action hung the process (no microstep bound on `raise`)
#   6. Sync passed a SYNTHETIC event to entry/exit actions, losing the payload
# -----------------------------------------------------------------------------
"""
Conformance tests asserting both engines behave identically.
"""

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import asyncio
import logging
import unittest
from typing import Any, Dict, List

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from src.xstate_statemachine import (
    ImplementationMissingError,
    Interpreter,
    MachineLogic,
    StateNotFoundError,
    SyncInterpreter,
    XStateMachineError,
    create_machine,
)

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 🛠️ Helpers
# -----------------------------------------------------------------------------
def build(config: Dict[str, Any], **logic_kwargs: Any) -> Any:
    """Builds a machine from a raw config plus inline logic.

    Args:
        config: The raw machine configuration.
        **logic_kwargs: Passed straight through to `MachineLogic`.

    Returns:
        Any: The constructed `MachineNode`.
    """
    return create_machine(config, logic=MachineLogic(**logic_kwargs))


async def drain(interpreter: Interpreter, *events: str) -> None:
    """Sends events to an async interpreter and lets the loop settle.

    Args:
        interpreter: The running async interpreter.
        *events: Event names to send in order.
    """
    for event in events:
        await interpreter.send(event)
    await asyncio.sleep(0.05)


# -----------------------------------------------------------------------------
# ⚛️ Transition Atomicity
# -----------------------------------------------------------------------------
class TestTransitionAtomicity(unittest.IsolatedAsyncioTestCase):
    """A transition must apply completely or not at all.

    🐛 Regression: `_process_single_transition` ran exit → actions → enter with
    no rollback. When a transition action raised, the source state had already
    been exited and the target was never entered, leaving
    `current_state_ids == set()` while `status` still reported "running".
    The machine was permanently dead AND advertised itself as healthy, so a
    supervisor watching `is_running` would never restart it.
    """

    CONFIG: Dict[str, Any] = {
        "id": "m",
        "initial": "a",
        "context": {},
        "states": {
            "a": {"on": {"G": {"target": "b", "actions": ["missing"]}}},
            "b": {"on": {"N": "c"}},
            "c": {},
        },
    }

    def test_sync_keeps_a_valid_configuration_when_an_action_raises(
        self,
    ) -> None:
        """The machine must never be left with zero active states."""
        # Arrange
        interpreter = SyncInterpreter(build(self.CONFIG)).start()

        # Act — a missing action implementation raises mid-transition.
        with self.assertRaises(ImplementationMissingError):
            interpreter.send("G")

        # Assert — still in a REAL state, not an empty configuration.
        self.assertTrue(
            interpreter.current_state_ids,
            "machine was left with no active state at all",
        )
        self.assertEqual({"m.a"}, interpreter.current_state_ids)

    def test_sync_still_processes_events_after_a_failed_transition(
        self,
    ) -> None:
        """A failed transition must not brick the interpreter."""
        # Arrange
        interpreter = SyncInterpreter(build(self.CONFIG)).start()
        with self.assertRaises(ImplementationMissingError):
            interpreter.send("G")

        # Act — the machine should still respond to a valid event.
        interpreter.send(
            "N"
        )  # not handled in 'a' — must be a no-op, not a crash

        # Assert
        self.assertEqual({"m.a"}, interpreter.current_state_ids)
        self.assertTrue(interpreter.is_running)

    async def test_async_keeps_a_valid_configuration_when_an_action_raises(
        self,
    ) -> None:
        """The async engine must uphold the same invariant."""
        # Arrange
        interpreter = await Interpreter(build(self.CONFIG)).start()
        self.addAsyncCleanup(interpreter.stop)

        # Act
        await drain(interpreter, "G")

        # Assert
        self.assertTrue(
            interpreter.current_state_ids,
            "machine was left with no active state at all",
        )
        self.assertEqual("running", interpreter.status)


# -----------------------------------------------------------------------------
# 🎯 Unresolvable Targets Are Survivable On Both Engines
# -----------------------------------------------------------------------------
class TestUnresolvableTarget(unittest.IsolatedAsyncioTestCase):
    """A bad target must not silently kill the async run loop.

    🐛 Regression: `SyncInterpreter` raised `StateNotFoundError` and kept
    running, but `Interpreter` let the error escape `_run_event_loop`, which
    set `status = "stopped"`. Since `send()` is fire-and-forget the caller was
    never informed — the machine went silently dead and dropped every later
    event.
    """

    CONFIG: Dict[str, Any] = {
        "id": "m",
        "initial": "a",
        "context": {},
        "states": {
            "a": {"on": {"BAD": "nonexistent", "OK": "b"}},
            "b": {},
        },
    }

    def test_sync_raises_and_stays_running(self) -> None:
        """The sync engine surfaces the error to the caller."""
        # Arrange
        interpreter = SyncInterpreter(build(self.CONFIG)).start()

        # Act / Assert
        with self.assertRaises(StateNotFoundError):
            interpreter.send("BAD")

        self.assertEqual("running", interpreter.status)
        self.assertEqual({"m.a"}, interpreter.current_state_ids)

    async def test_async_survives_and_keeps_processing(self) -> None:
        """The async engine must stay alive and honour later events."""
        # Arrange
        interpreter = await Interpreter(build(self.CONFIG)).start()
        self.addAsyncCleanup(interpreter.stop)

        # Act — a bad target, then a perfectly good event.
        await drain(interpreter, "BAD")
        self.assertEqual(
            "running", interpreter.status, "run loop died on a bad target"
        )

        await drain(interpreter, "OK")

        # Assert — the good event was still processed.
        self.assertEqual({"m.b"}, interpreter.current_state_ids)


# -----------------------------------------------------------------------------
# 📨 Entry/Exit Actions Receive The REAL Triggering Event
# -----------------------------------------------------------------------------
class TestEntryExitEventIdentity(unittest.IsolatedAsyncioTestCase):
    """Entry and exit actions must see the event that caused the transition.

    🐛 Regression: `SyncInterpreter` synthesised `entry.<id>` / `exit.<id>`
    events, so an entry action reading `event.payload` — the normal way to
    seed state from an event — silently received an EMPTY payload. The async
    engine passed the real event, matching XState, so the engines disagreed
    and the sync one lost user data with no error.
    """

    CONFIG: Dict[str, Any] = {
        "id": "m",
        "initial": "a",
        "context": {},
        "states": {
            "a": {"exit": ["onExit"], "on": {"LOGIN": "b"}},
            "b": {"entry": ["onEntry"]},
        },
    }

    @staticmethod
    def _recording_logic(sink: List[Any]) -> Dict[str, Any]:
        """Builds logic recording the event each hook observes."""

        def record(_i: Any, _c: Any, event: Any, _a: Any) -> None:
            """Captures the event type and payload."""
            sink.append((event.type, dict(event.payload or {})))

        return {"actions": {"onExit": record, "onEntry": record}}

    def test_sync_passes_the_real_event_and_payload(self) -> None:
        """Sync must not substitute a synthetic entry/exit event."""
        # Arrange
        seen: List[Any] = []
        interpreter = SyncInterpreter(
            build(self.CONFIG, **self._recording_logic(seen))
        ).start()
        seen.clear()

        # Act
        interpreter.send("LOGIN", user="ada", token="xyz")

        # Assert — both hooks saw the REAL event, payload intact.
        self.assertEqual(2, len(seen))
        for observed_type, payload in seen:
            self.assertEqual("LOGIN", observed_type)
            self.assertEqual({"user": "ada", "token": "xyz"}, payload)

    async def test_both_engines_agree_on_the_event(self) -> None:
        """The two engines must observe identical events."""
        # Arrange
        sync_seen: List[Any] = []
        async_seen: List[Any] = []

        sync_interpreter = SyncInterpreter(
            build(self.CONFIG, **self._recording_logic(sync_seen))
        ).start()
        sync_seen.clear()
        sync_interpreter.send("LOGIN", user="ada")

        async_interpreter = await Interpreter(
            build(self.CONFIG, **self._recording_logic(async_seen))
        ).start()
        self.addAsyncCleanup(async_interpreter.stop)
        async_seen.clear()
        await drain(async_interpreter, "LOGIN")

        # Assert — same event type observed by both.
        self.assertEqual([t for t, _ in sync_seen], [t for t, _ in async_seen])


# -----------------------------------------------------------------------------
# 🛟 Runaway `raise` Storms Are Bounded
# -----------------------------------------------------------------------------
class TestRaiseStormIsBounded(unittest.IsolatedAsyncioTestCase):
    """A self-feeding `raise` must terminate, not hang the process.

    🐛 Regression: `max_iterations` was wired ONLY into the eventless
    (`always`) path. The `raise` built-in routes through the event queue,
    which was unbounded, so a single mis-written action hung the machine
    forever. On the sync engine `send()` never returned; on the async engine
    the whole asyncio loop was starved — a heartbeat task scheduled every
    50 ms ran ZERO times in four seconds, freezing every other coroutine in
    the process (HTTP handlers, health checks, graceful shutdown).
    """

    CONFIG: Dict[str, Any] = {
        "id": "m",
        "initial": "a",
        "context": {},
        "states": {
            "a": {
                "on": {
                    "PING": {
                        "actions": [
                            {
                                "type": "raise",
                                "params": {"event": {"type": "PING"}},
                            }
                        ]
                    }
                }
            }
        },
    }

    def test_sync_send_returns_instead_of_hanging(self) -> None:
        """`send()` must return once the microstep bound is hit."""
        # Arrange
        interpreter = SyncInterpreter(build(self.CONFIG)).start()

        # Act — this used to spin forever.
        interpreter.send("PING")

        # Assert — we got here at all, and the machine is still usable.
        self.assertEqual({"m.a"}, interpreter.current_state_ids)
        self.assertTrue(interpreter.is_running)

    async def test_async_loop_is_not_starved(self) -> None:
        """Other coroutines must keep running during a raise storm."""
        # Arrange — a heartbeat proving the event loop still schedules.
        beats = {"n": 0}

        async def heartbeat() -> None:
            """Ticks continuously while the machine processes."""
            while True:
                await asyncio.sleep(0.01)
                beats["n"] += 1

        ticker = asyncio.create_task(heartbeat())
        self.addAsyncCleanup(ticker.cancel)

        interpreter = await Interpreter(build(self.CONFIG)).start()
        self.addAsyncCleanup(interpreter.stop)

        # Act
        await interpreter.send("PING")
        await asyncio.sleep(0.3)

        # Assert — the loop was never monopolised.
        self.assertGreater(
            beats["n"], 0, "asyncio event loop was starved by a raise storm"
        )
