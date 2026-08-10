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
    assign,
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

    async def test_high_throughput_events_are_never_dropped(self) -> None:
        """A busy producer must not be mistaken for a runaway `raise`.

        🐛 Regression guard: the first bound counted events processed while
        the queue was non-empty, which cannot distinguish a self-feeding
        `raise` from a merely busy producer. 5,000 concurrent legitimate
        `send()` calls lost 3,999 of them — silent data loss far worse than
        the hang it was meant to prevent. The bound now measures the RAISE
        CHAIN, so external traffic of any volume is never throttled.
        """
        # Arrange — a counter driven purely by external events.
        config = {
            "id": "m",
            "initial": "a",
            "context": {"n": 0},
            "states": {
                "a": {
                    "on": {
                        "TICK": {
                            "actions": assign(
                                {"n": lambda a: a["context"]["n"] + 1}
                            )
                        }
                    }
                }
            },
        }
        interpreter = await Interpreter(build(config)).start()
        self.addAsyncCleanup(interpreter.stop)

        # Act — well above the default 1000 microstep ceiling.
        total = 3000
        await asyncio.gather(*[interpreter.send("TICK") for _ in range(total)])
        for _ in range(400):
            if interpreter.context["n"] >= total:
                break
            await asyncio.sleep(0.01)

        # Assert — every single event was processed.
        self.assertEqual(total, interpreter.context["n"])

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


# -----------------------------------------------------------------------------
# 🕰️ Deep History Into A Parallel State
# -----------------------------------------------------------------------------
class TestDeepHistoryParallel(unittest.IsolatedAsyncioTestCase):
    """Restoring deep history must yield exactly one leaf per region.

    🐛 Regression: each remembered leaf was entered in its OWN
    `_enter_states` call. The explicit-child guard is computed per call, so
    restoring `r1.y` walked through `r1`, which could not see that `y` was
    explicitly targeted and therefore ALSO ran its default `initial` descent
    into `r1.x`. Deep history into a parallel state activated TWO leaves in
    one region — forbidden by SCXML, and a direct violation of the
    one-state-per-region invariant the library is built on.
    """

    CONFIG: Dict[str, Any] = {
        "id": "m",
        "initial": "par",
        "context": {},
        "states": {
            "par": {
                "type": "parallel",
                "on": {"OUT": "away"},
                "states": {
                    "r1": {
                        "initial": "x",
                        "states": {"x": {"on": {"T": "y"}}, "y": {}},
                    },
                    "r2": {"initial": "p", "states": {"p": {}}},
                    "hist": {"type": "history", "history": "deep"},
                },
            },
            "away": {"on": {"BACK": "par.hist"}},
        },
    }

    @staticmethod
    def _leaves(ids: Any, region: str) -> List[str]:
        """Returns the active leaf ids belonging to one region."""
        return sorted(i for i in ids if f".{region}." in i)

    def test_sync_restores_exactly_one_leaf_per_region(self) -> None:
        """Only the remembered leaf may be active after a restore."""
        # Arrange — move r1 to 'y', then leave the parallel state entirely.
        interpreter = SyncInterpreter(build(self.CONFIG)).start()
        interpreter.send("T")
        self.assertEqual(
            ["m.par.r1.y"], self._leaves(interpreter.current_state_ids, "r1")
        )
        interpreter.send("OUT")

        # Act
        interpreter.send("BACK")

        # Assert — 'y' restored, and 'x' NOT resurrected alongside it.
        self.assertEqual(
            ["m.par.r1.y"],
            self._leaves(interpreter.current_state_ids, "r1"),
            "two leaves active in a single region",
        )
        self.assertEqual(
            ["m.par.r2.p"], self._leaves(interpreter.current_state_ids, "r2")
        )

    async def test_async_restores_exactly_one_leaf_per_region(self) -> None:
        """The async engine must uphold the same invariant."""
        # Arrange
        interpreter = await Interpreter(build(self.CONFIG)).start()
        self.addAsyncCleanup(interpreter.stop)
        await drain(interpreter, "T", "OUT")

        # Act
        await drain(interpreter, "BACK")

        # Assert
        self.assertEqual(
            ["m.par.r1.y"],
            self._leaves(interpreter.current_state_ids, "r1"),
            "two leaves active in a single region",
        )


# -----------------------------------------------------------------------------
# 🤖 Invoking A Child MACHINE
# -----------------------------------------------------------------------------
class TestInvokedChildMachine(unittest.IsolatedAsyncioTestCase):
    """`invoke` of a `MachineNode` must complete correctly and leak nothing.

    🐛 Regression (async): `await child.start()` returns once the child's
    INITIAL state is entered, not when it finishes, so `onDone` fired
    immediately with the child's initial context. The managing task was then
    cancelled and the `finally` deleted the registry entry WITHOUT stopping
    the child — orphaning its run loop and every timer. Measured at +2
    permanently live tasks per invocation, surviving the parent's `stop()`.

    🐛 Regression (sync): `onDone` was never fired at all, so a parent waited
    forever even when the child finished immediately.
    """

    SLOW_CHILD: Dict[str, Any] = {
        "id": "c",
        "initial": "w",
        "context": {},
        "states": {"w": {"after": {600000: "d"}}, "d": {"type": "final"}},
    }
    FAST_CHILD: Dict[str, Any] = {
        "id": "c",
        "initial": "w",
        "context": {"v": 1},
        "states": {"w": {"always": "d"}, "d": {"type": "final"}},
    }
    PARENT: Dict[str, Any] = {
        "id": "p",
        "initial": "a",
        "context": {},
        "states": {
            "a": {"invoke": {"src": "child", "id": "ch", "onDone": "done"}},
            "done": {},
        },
    }

    def _parent_for(self, child_config: Dict[str, Any]) -> Any:
        """Builds the parent machine wired to a given child."""
        return build(
            self.PARENT,
            services={"child": build(child_config)},
        )

    async def test_async_does_not_fire_on_done_early(self) -> None:
        """A child that has not finished must not satisfy `onDone`."""
        # Arrange / Act
        interpreter = await Interpreter(
            self._parent_for(self.SLOW_CHILD)
        ).start()
        self.addAsyncCleanup(interpreter.stop)
        await asyncio.sleep(0.2)

        # Assert — still waiting on the child.
        self.assertEqual({"p.a"}, interpreter.current_state_ids)

    async def test_async_fires_on_done_when_the_child_completes(self) -> None:
        """A child reaching a final state must satisfy `onDone`."""
        # Arrange / Act
        interpreter = await Interpreter(
            self._parent_for(self.FAST_CHILD)
        ).start()
        self.addAsyncCleanup(interpreter.stop)
        await asyncio.sleep(0.2)

        # Assert
        self.assertEqual({"p.done"}, interpreter.current_state_ids)

    async def test_async_does_not_orphan_the_child(self) -> None:
        """`stop()` must tear down the invoked child machine."""
        # Arrange — measure the live task count across repeated invocations.
        baseline = len([t for t in asyncio.all_tasks() if not t.done()])

        # Act
        for _ in range(20):
            interpreter = await Interpreter(
                self._parent_for(self.SLOW_CHILD)
            ).start()
            await asyncio.sleep(0)
            await interpreter.stop()
        await asyncio.sleep(0.2)

        # Assert — no monotonic climb.
        alive = len([t for t in asyncio.all_tasks() if not t.done()])
        self.assertLessEqual(
            alive,
            baseline,
            f"orphaned tasks: {alive} live vs {baseline} baseline",
        )

    async def test_failed_child_machine_fires_on_error(self) -> None:
        """A crashed child must satisfy `onError`, not `onDone`.

        🐛 Regression guard: the poll loop treated ANY non-running status as
        success, so a child that ended in `status == "error"` was reported as
        a clean completion and a parent modelling failure with `onError`
        silently took the happy path.
        """

        async def explode(_i: Any, _c: Any, _e: Any) -> None:
            """A service that always fails."""
            await asyncio.sleep(0.01)
            raise ValueError("child failed")

        # Arrange
        failing_child = build(
            {
                "id": "c",
                "initial": "w",
                "context": {},
                "states": {"w": {"invoke": {"src": "boom"}}},
            },
            services={"boom": explode},
        )
        parent = build(
            {
                "id": "p",
                "initial": "a",
                "context": {},
                "states": {
                    "a": {
                        "invoke": {
                            "src": "child",
                            "id": "k",
                            "onDone": "done",
                            "onError": "failed",
                        }
                    },
                    "done": {},
                    "failed": {},
                },
            },
            services={"child": failing_child},
        )
        interpreter = await Interpreter(parent).start()
        self.addAsyncCleanup(interpreter.stop)

        # Act
        await asyncio.sleep(0.4)

        # Assert
        self.assertEqual({"p.failed"}, interpreter.current_state_ids)

    def test_sync_fires_on_done_when_the_child_completes(self) -> None:
        """The sync engine must report child completion too."""
        # Arrange / Act
        interpreter = SyncInterpreter(
            self._parent_for(self.FAST_CHILD)
        ).start()
        self.addCleanup(interpreter.stop)

        # Assert — poll briefly; the child runs on its own thread.
        for _ in range(200):
            if interpreter.current_state_ids == {"p.done"}:
                break
            import time

            time.sleep(0.01)
        self.assertEqual({"p.done"}, interpreter.current_state_ids)


# -----------------------------------------------------------------------------
# 🧯 Robustness Fixes From The Battle Test
# -----------------------------------------------------------------------------
class TestRobustnessFixes(unittest.IsolatedAsyncioTestCase):
    """Non-blocking defects found by the v0.6.0 battle test."""

    SIMPLE: Dict[str, Any] = {
        "id": "m",
        "initial": "a",
        "context": {},
        "states": {"a": {"on": {"G": "b"}}, "b": {"on": {"N": "c"}}, "c": {}},
    }

    def test_restart_after_stop_raises_instead_of_no_op(self) -> None:
        """A stopped interpreter must not pretend it restarted.

        🐛 Regression: `start()` returned `self`, so state ids still read as
        live while `status` stayed "stopped" and every event was dropped.
        """
        # Arrange
        interpreter = SyncInterpreter(build(self.SIMPLE)).start()
        interpreter.stop()

        # Act / Assert
        with self.assertRaises(XStateMachineError):
            interpreter.start()

    async def test_async_restart_after_stop_raises(self) -> None:
        """The async engine must refuse a restart too."""
        # Arrange
        interpreter = await Interpreter(build(self.SIMPLE)).start()
        await interpreter.stop()

        # Act / Assert
        with self.assertRaises(XStateMachineError):
            await interpreter.start()

    async def test_send_to_a_stopped_machine_does_not_queue(self) -> None:
        """Events sent after `stop()` must be dropped, not accumulated.

        🐛 Regression: nothing drains the queue after shutdown, so every
        `send()` accumulated forever — a slow leak in any process holding a
        reference to a finished machine.
        """
        # Arrange
        interpreter = await Interpreter(build(self.SIMPLE)).start()
        await interpreter.stop()

        # Act
        for _ in range(200):
            await interpreter.send("G")

        # Assert
        self.assertEqual(0, interpreter._event_queue.qsize())

    def test_a_failing_plugin_cannot_break_the_interpreter(self) -> None:
        """Observability must not break the thing it observes.

        🐛 Regression: plugin hook exceptions propagated out of `send()` on
        the sync engine and killed the run loop on the async engine, even
        though actions and subscribers were already contained.
        """

        class ExplodingPlugin:
            """A plugin whose hooks always fail."""

            def on_transition(self, *_a: Any, **_k: Any) -> None:
                """Always raises."""
                raise ValueError("metrics exporter is down")

            def on_event_received(self, *_a: Any, **_k: Any) -> None:
                """No-op."""

        # Arrange
        interpreter = SyncInterpreter(build(self.SIMPLE))
        interpreter.use(ExplodingPlugin())
        interpreter.start()

        # Act
        interpreter.send("G")
        interpreter.send("N")

        # Assert — transitions still happened.
        self.assertEqual({"m.c"}, interpreter.current_state_ids)

    def test_registered_plugin_identity_is_preserved(self) -> None:
        """Containment must not break `plugin in interpreter.plugins`."""
        # Arrange
        from src.xstate_statemachine import LoggingInspector

        inspector = LoggingInspector()
        interpreter = SyncInterpreter(build(self.SIMPLE))

        # Act
        interpreter.use(inspector)

        # Assert
        self.assertIn(inspector, interpreter.plugins)

    def test_plugins_getter_returns_user_objects_not_wrappers(self) -> None:
        """Error containment must not leak its wrapper to user code.

        🐛 Regression guard: plugins are wrapped in an internal containment
        proxy at registration. Returning the proxy from the getter broke `is`
        comparisons, `isinstance(p, PluginBase)`, and attribute access on the
        caller's own object — so a plugin that keeps state became unusable
        through the public API.
        """
        # Arrange
        from src.xstate_statemachine import PluginBase

        class StatefulPlugin(PluginBase):
            """A plugin that records what it observed."""

            def __init__(self) -> None:
                """Initialises the observation log."""
                self.seen: List[str] = []

            def on_transition(
                self, _i: Any, _f: Any, _t: Any, tr: Any
            ) -> None:
                """Records the event that caused the transition."""
                self.seen.append(tr.event)

            def on_event_received(self, _i: Any, _e: Any) -> None:
                """No-op."""

        plugin = StatefulPlugin()
        interpreter = SyncInterpreter(build(self.SIMPLE))
        interpreter.use(plugin)
        interpreter.start()
        interpreter.send("G")

        # Assert — the public API hands back the caller's own object.
        returned = interpreter.plugins[0]
        self.assertIs(returned, plugin)
        self.assertIsInstance(returned, PluginBase)
        self.assertIn(plugin, interpreter.plugins)
        self.assertIn("G", plugin.seen)

    def test_plugins_setter_round_trips_identity(self) -> None:
        """`interpreter.plugins = [p]` then reading back must yield `p`."""
        # Arrange
        from src.xstate_statemachine import LoggingInspector

        inspector = LoggingInspector()
        interpreter = SyncInterpreter(build(self.SIMPLE))

        # Act
        interpreter.plugins = [inspector]

        # Assert
        self.assertIs(interpreter.plugins[0], inspector)

    def test_machine_key_wins_over_a_shadowing_custom_id(self) -> None:
        """A nested `id` must not hijack `#machineId` targets.

        🐛 Regression guard: the custom-id registry was consulted BEFORE the
        machine key, so a nested state declaring `id: "m"` on a machine also
        called "m" silently redirected every existing `#m.child` target into
        that unrelated branch.
        """
        # Arrange
        config = {
            "id": "m",
            "initial": "a",
            "context": {},
            "states": {
                "a": {"on": {"G": "#m.b"}},
                "b": {},
                "shadow": {
                    "id": "m",
                    "initial": "z",
                    "states": {"z": {}, "b": {}},
                },
            },
        }
        interpreter = SyncInterpreter(build(config)).start()

        # Act
        interpreter.send("G")

        # Assert — the machine root wins, not the shadowing branch.
        self.assertEqual({"m.b"}, interpreter.current_state_ids)

    def test_rollback_rearms_the_source_states_timers(self) -> None:
        """A rolled-back state must not lose its `after` timer.

        🐛 Regression guard: exiting cancels each exited state's timers and
        services. Restoring only the state NODES produced a configuration
        that looked correct but was inert — a rolled-back state with
        `after: {250: ...}` would never time out again.
        """
        # Arrange
        fired: List[str] = []
        config = {
            "id": "m",
            "initial": "a",
            "context": {},
            "states": {
                "a": {
                    "after": {250: "timeout"},
                    "on": {"G": {"target": "b", "actions": ["missing"]}},
                },
                "b": {},
                "timeout": {"entry": ["mark"]},
            },
        }
        interpreter = SyncInterpreter(
            build(config, actions={"mark": lambda *_a: fired.append("T")})
        ).start()
        self.addCleanup(interpreter.stop)

        # Act — a failing transition rolls back to 'a'.
        with self.assertRaises(ImplementationMissingError):
            interpreter.send("G")
        self.assertEqual({"m.a"}, interpreter.current_state_ids)

        # Assert — the timer still fires.
        import time

        for _ in range(100):
            if fired:
                break
            time.sleep(0.01)
        self.assertEqual(["T"], fired)

    def test_corrupt_snapshot_raises_a_library_error(self) -> None:
        """A bad snapshot must be catchable via `XStateMachineError`.

        🐛 Regression: `json.JSONDecodeError` leaked, so the documented way
        to catch this library's failures silently missed corrupt snapshots
        arriving from Redis, disk or a queue.
        """
        # Arrange
        machine = build(self.SIMPLE)

        # Act / Assert
        for corrupt in ("not-json", "", "[1,2,3]"):
            with self.assertRaises(XStateMachineError):
                SyncInterpreter.from_snapshot(corrupt, machine)

    def test_dotted_state_keys_are_rejected(self) -> None:
        """A '.' in a state key collides with the id separator.

        🐛 Regression: a flat state `"x.y"` and a nested `x > y` produced the
        SAME id, so `matches()`, snapshots and target resolution could not
        tell them apart — targeting `"x.y"` silently entered the nested
        state and ran the wrong entry actions.
        """
        # Act / Assert
        with self.assertRaises(XStateMachineError):
            build(
                {
                    "id": "m",
                    "initial": "x.y",
                    "context": {},
                    "states": {
                        "x.y": {},
                        "x": {"initial": "y", "states": {"y": {}}},
                    },
                }
            )

    def test_custom_state_id_resolves_a_hash_target(self) -> None:
        """`#myId` must find a state that declared `id`.

        🐛 Regression: `StateNode` never read `config["id"]`, so this core
        XState cross-branch idiom — used by 37 of the 104 bundled Stately
        machines — always raised `StateNotFoundError`.
        """
        # Arrange
        config = {
            "id": "m",
            "initial": "a",
            "context": {},
            "states": {
                "a": {"on": {"GO": "#tgt"}},
                "br": {"initial": "in", "states": {"in": {"id": "tgt"}}},
            },
        }
        interpreter = SyncInterpreter(build(config)).start()

        # Act
        interpreter.send("GO")

        # Assert
        self.assertEqual({"m.br.in"}, interpreter.current_state_ids)

    def test_duplicate_custom_ids_are_rejected(self) -> None:
        """Two states may not claim the same custom id."""
        # Act / Assert
        with self.assertRaises(XStateMachineError):
            build(
                {
                    "id": "m",
                    "initial": "a",
                    "context": {},
                    "states": {
                        "a": {"id": "dup"},
                        "b": {"id": "dup"},
                    },
                }
            )


# -----------------------------------------------------------------------------
# 🔀 Deterministic Exit Order & Config Validation
# -----------------------------------------------------------------------------
class TestDeterminismAndValidation(unittest.TestCase):
    """Ordering must be reproducible and bad config must be actionable."""

    def test_parallel_exit_order_is_deterministic(self) -> None:
        """The same machine and event must always exit in the same order.

        🐛 Regression: states were sorted by depth alone, so ties between
        sibling parallel regions were broken by set iteration order. The same
        machine could emit exit actions in a different order between runs —
        untestable, and it makes cleanup logic subtly unreliable.
        """
        # Arrange
        config = {
            "id": "m",
            "initial": "p",
            "context": {},
            "states": {
                "p": {
                    "type": "parallel",
                    "on": {"OUT": "done"},
                    "states": {
                        "r1": {
                            "initial": "a",
                            "states": {"a": {"exit": ["x1"]}},
                        },
                        "r2": {
                            "initial": "b",
                            "states": {"b": {"exit": ["x2"]}},
                        },
                        "r3": {
                            "initial": "c",
                            "states": {"c": {"exit": ["x3"]}},
                        },
                    },
                },
                "done": {},
            },
        }

        # Act — repeat enough times that a hash-order flake would surface.
        observed = set()
        for _ in range(25):
            order: List[str] = []
            actions = {
                name: (lambda _i, _c, _e, _a, n=name: order.append(n))
                for name in ("x1", "x2", "x3")
            }
            interpreter = SyncInterpreter(
                build(config, actions=actions)
            ).start()
            interpreter.send("OUT")
            observed.add(tuple(order))

        # Assert
        self.assertEqual(1, len(observed), f"non-deterministic: {observed}")

    def test_malformed_config_raises_actionable_errors(self) -> None:
        """Bad config must never surface as a raw TypeError/AttributeError.

        🐛 Regression: several shapes reached `.items()` / `.get()` directly,
        producing "'str' object has no attribute 'items'" from library
        internals — naming neither the offending state nor the key, so a typo
        in a large config was untraceable. Others were accepted silently and
        produced a machine that hung or dropped every event.
        """
        # Arrange
        malformed = {
            "states not a dict": {
                "id": "m",
                "initial": "a",
                "states": "nope",
            },
            "state not a dict": {
                "id": "m",
                "initial": "a",
                "states": {"a": "nope"},
            },
            "on not a dict": {
                "id": "m",
                "initial": "a",
                "states": {"a": {"on": "nope"}},
            },
            "after not a dict": {
                "id": "m",
                "initial": "a",
                "states": {"a": {"after": "nope"}},
            },
            "invoke not a dict": {
                "id": "m",
                "initial": "a",
                "states": {"a": {"invoke": 7}},
            },
            "initial not a string": {
                "id": "m",
                "initial": 5,
                "states": {"a": {}},
            },
            "context not a mapping": {
                "id": "m",
                "initial": "a",
                "context": [],
                "states": {"a": {}},
            },
        }

        # Act / Assert
        for label, config in malformed.items():
            with self.subTest(config=label):
                with self.assertRaises(XStateMachineError):
                    build(config)

    def test_stately_template_placeholder_context_is_tolerated(self) -> None:
        """Real Stately exports ship `"context": "{{initialContext}}"`.

        🐛 Regression guard: tightening context validation initially rejected
        NINE machines in the bundled Stately corpus, dropping it from 103/104
        to 95/104 — silently breaking the library's headline promise of
        running XState JSON unmodified. A string context is downgraded to a
        warning and treated as empty.
        """
        # Arrange / Act
        machine = build(
            {
                "id": "m",
                "initial": "a",
                "context": "{{initialContext}}",
                "states": {"a": {}},
            }
        )
        interpreter = SyncInterpreter(machine).start()

        # Assert
        self.assertEqual({}, interpreter.context)
        self.assertEqual({"m.a"}, interpreter.current_state_ids)

    def test_a_context_factory_is_still_accepted(self) -> None:
        """Validation must not break the documented callable context."""
        # Arrange / Act
        machine = build(
            {
                "id": "m",
                "initial": "a",
                "context": lambda _input: {"seeded": True},
                "states": {"a": {}},
            }
        )
        interpreter = SyncInterpreter(machine).start()

        # Assert
        self.assertTrue(interpreter.context["seeded"])
