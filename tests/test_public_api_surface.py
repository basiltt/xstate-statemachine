# /tests/test_public_api_surface.py
# -----------------------------------------------------------------------------
# 🧪 Test Suite: Documented Public API Surface
# -----------------------------------------------------------------------------
# This module pins the interpreter attributes that the README and the `docs/`
# guides present as public API. Prior to v0.5.1 several of these names were
# documented but never implemented, so every published example raised
# `AttributeError` on contact.
#
# 🏛️ Architecture decision: these are *contract* tests. They exist to ensure
# documentation and implementation cannot silently diverge again — if a
# documented name is removed, a test fails rather than a user's copy-pasted
# snippet.
#
# Also covers `spawn_`/`spawn_blocking_` logic auto-discovery, which routed
# actor keys to `actions` instead of `services` and therefore made the actor
# model structurally incompatible with `logic_modules=` discovery.
# -----------------------------------------------------------------------------
"""
Contract tests for the documented public interpreter API.
"""

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import asyncio
import io
import logging
import sys
import types
import unittest
from typing import Any, Dict

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from src.xstate_statemachine import (
    InvalidConfigError,
    Interpreter,
    LoggingInspector,
    MachineLogic,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.cli.__main__ import _safe_print
from src.xstate_statemachine.models import is_spawn_action, spawn_service_key

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# 📐 A trivial two-state machine reused across the suite.
SIMPLE_CONFIG: Dict[str, Any] = {
    "id": "m",
    "initial": "a",
    "states": {"a": {"on": {"GO": "b"}}, "b": {}},
}


# -----------------------------------------------------------------------------
# 📖 Documented Attribute Aliases
# -----------------------------------------------------------------------------
class TestDocumentedAttributes(unittest.IsolatedAsyncioTestCase):
    """Pins the attribute names published in the README and docs guides."""

    def test_active_state_ids_matches_current_state_ids_sync(self) -> None:
        """`active_state_ids` must mirror `current_state_ids`."""
        # Arrange
        interpreter = SyncInterpreter(
            create_machine(SIMPLE_CONFIG, logic=MachineLogic())
        ).start()

        # Act / Assert
        self.assertEqual(
            interpreter.current_state_ids, interpreter.active_state_ids
        )
        self.assertEqual({"m.a"}, interpreter.active_state_ids)

        interpreter.send("GO")
        self.assertEqual({"m.b"}, interpreter.active_state_ids)

    async def test_active_state_ids_matches_current_state_ids_async(
        self,
    ) -> None:
        """The async interpreter must expose the same alias."""
        # Arrange
        interpreter = await Interpreter(
            create_machine(SIMPLE_CONFIG, logic=MachineLogic())
        ).start()
        self.addAsyncCleanup(interpreter.stop)

        # Act / Assert
        self.assertEqual(
            interpreter.current_state_ids, interpreter.active_state_ids
        )

    def test_is_running_reflects_lifecycle_sync(self) -> None:
        """`is_running` must be True only between start() and stop()."""
        # Arrange
        interpreter = SyncInterpreter(
            create_machine(SIMPLE_CONFIG, logic=MachineLogic())
        )
        self.assertFalse(interpreter.is_running)

        # Act
        interpreter.start()
        self.assertTrue(interpreter.is_running)
        interpreter.stop()

        # Assert
        self.assertFalse(interpreter.is_running)

    async def test_is_running_reflects_lifecycle_async(self) -> None:
        """The async interpreter's `is_running` must track its status."""
        # Arrange
        interpreter = Interpreter(
            create_machine(SIMPLE_CONFIG, logic=MachineLogic())
        )
        self.assertFalse(interpreter.is_running)

        # Act
        await interpreter.start()
        self.assertTrue(interpreter.is_running)
        await interpreter.stop()

        # Assert
        self.assertFalse(interpreter.is_running)

    def test_plugins_property_is_assignable(self) -> None:
        """Docs assign a list directly: `interp.plugins = [...]`."""
        # Arrange
        interpreter = SyncInterpreter(
            create_machine(SIMPLE_CONFIG, logic=MachineLogic())
        )
        inspector = LoggingInspector()

        # Act
        interpreter.plugins = [inspector]

        # Assert
        self.assertIn(inspector, interpreter.plugins)
        interpreter.start()
        interpreter.send("GO")
        self.assertEqual({"m.b"}, interpreter.active_state_ids)

    def test_plugins_property_rejects_non_list(self) -> None:
        """Assigning a non-list must fail fast with a clear error."""
        # Arrange
        interpreter = SyncInterpreter(
            create_machine(SIMPLE_CONFIG, logic=MachineLogic())
        )

        # Act / Assert
        with self.assertRaises(TypeError):
            interpreter.plugins = LoggingInspector()  # type: ignore[assignment]

    def test_plugins_property_rejects_non_plugin_elements(self) -> None:
        """Element types are validated at assignment, not mid-transition.

        Without this the failure surfaces later as an `AttributeError` raised
        from deep inside event processing, with a traceback pointing at
        interpreter internals rather than the offending assignment.
        """
        # Arrange
        interpreter = SyncInterpreter(
            create_machine(SIMPLE_CONFIG, logic=MachineLogic())
        )

        # Act / Assert
        with self.assertRaises(TypeError):
            interpreter.plugins = [object()]  # type: ignore[list-item]

    async def test_is_running_false_after_from_snapshot(self) -> None:
        """A restored async interpreter has no run loop, so it is not running.

        🐛 Regression guard: `from_snapshot` restores the persisted status
        verbatim, yielding `status == "running"` with no `_event_loop_task`.
        `is_running` must not claim such an instance can process events — it
        would silently enqueue and drop every `send()`.
        """
        # Arrange
        source = await Interpreter(
            create_machine(SIMPLE_CONFIG, logic=MachineLogic())
        ).start()
        self.addAsyncCleanup(source.stop)
        snapshot = source.get_snapshot()

        # Act
        restored = Interpreter.from_snapshot(
            snapshot, create_machine(SIMPLE_CONFIG, logic=MachineLogic())
        )

        # Assert — status may say "running", but liveness must not.
        self.assertFalse(restored.is_running)

    async def test_external_cancel_does_not_skip_stop_cleanup(self) -> None:
        """`stop()` must still tear down after an external cancellation.

        🐛 Regression guard: the run loop briefly forced `status = "stopped"`
        in a `finally` clause. Cancellation is not always initiated by
        `stop()` — an enclosing TaskGroup, supervisor, or timeout can cancel
        `_event_loop_task` directly. Marking the status there made the
        subsequent `stop()` hit its idempotency guard and return early,
        skipping actor teardown and task cancellation, so invoked services
        kept running forever.
        """
        # Arrange — a service that ticks until cancelled.
        ticks: list = []

        async def ticker(_i: Any, _c: Any, _e: Any) -> None:
            while True:
                await asyncio.sleep(0.01)
                ticks.append(1)

        config = {
            "id": "m",
            "initial": "run",
            "states": {"run": {"invoke": {"src": "ticker"}}},
        }
        interpreter = await Interpreter(
            create_machine(
                config, logic=MachineLogic(services={"ticker": ticker})
            )
        ).start()
        await asyncio.sleep(0.05)

        # Act — cancel the loop externally, then stop().
        interpreter._event_loop_task.cancel()
        try:
            await interpreter._event_loop_task
        except asyncio.CancelledError:
            pass
        await interpreter.stop()

        # Assert — the invoked service was actually torn down.
        settled = len(ticks)
        await asyncio.sleep(0.08)
        self.assertEqual(
            settled, len(ticks), "service kept running after stop()"
        )

    def test_use_and_plugins_property_agree(self) -> None:
        """`use()` registrations must be visible through `.plugins`."""
        # Arrange
        interpreter = SyncInterpreter(
            create_machine(SIMPLE_CONFIG, logic=MachineLogic())
        )
        inspector = LoggingInspector()

        # Act
        interpreter.use(inspector)

        # Assert
        self.assertIn(inspector, interpreter.plugins)


# -----------------------------------------------------------------------------
# 👶 Actor Spawning Under Logic Auto-Discovery
# -----------------------------------------------------------------------------
class TestSpawnActionAutoDiscovery(unittest.TestCase):
    """Pins that `spawn_` actor keys resolve as services, not actions.

    🐛 Regression: `LogicLoader._extract_logic_from_node` registered
    `spawn_<key>` as a required *action*. The interpreters resolve those keys
    from `logic.services` at execution time, so auto-discovery always failed
    with `ImplementationMissingError` and the actor model could only be used
    by bypassing discovery with an explicit `logic=`.
    """

    @staticmethod
    def _make_logic_module() -> types.ModuleType:
        """Builds an in-memory logic module exposing a child-machine service.

        Returns:
            types.ModuleType: A module with a `child` service function.
        """
        module = types.ModuleType("spawn_logic_fixture")
        child = create_machine(
            {"id": "child", "initial": "i", "states": {"i": {}}},
            logic=MachineLogic(),
        )

        def child_service(_interpreter: Any, _ctx: Any, _event: Any) -> Any:
            """Returns the child machine to spawn."""
            return child

        # 🏷️ Name the function to match the `spawn_child` action key.
        child_service.__name__ = "child"
        module.child = child_service  # type: ignore[attr-defined]
        return module

    def test_spawn_key_registered_as_service(self) -> None:
        """`spawn_child` must look up a `child` *service*."""
        # Arrange
        module = self._make_logic_module()
        config = {
            "id": "m",
            "initial": "a",
            "context": {},
            "states": {"a": {"entry": ["spawn_child"]}},
        }

        # Act
        machine = create_machine(config, logic_modules=[module])

        # Assert
        self.assertIn("child", machine.logic.services)
        self.assertNotIn("spawn_child", machine.logic.actions)

    def test_spawn_blocking_key_registered_as_service(self) -> None:
        """`spawn_blocking_child` must strip the full prefix."""
        # Arrange
        module = self._make_logic_module()
        config = {
            "id": "m",
            "initial": "a",
            "context": {},
            "states": {"a": {"entry": ["spawn_blocking_child"]}},
        }

        # Act
        machine = create_machine(config, logic_modules=[module])

        # Assert
        self.assertIn("child", machine.logic.services)
        self.assertNotIn("spawn_blocking_child", machine.logic.actions)

    def test_ordinary_actions_still_registered_as_actions(self) -> None:
        """Non-spawn actions must be unaffected by the routing change."""
        # Arrange
        module = types.ModuleType("plain_logic_fixture")

        def do_thing(_i: Any, _c: Any, _e: Any, _a: Any) -> None:
            """A plain action implementation."""

        module.do_thing = do_thing  # type: ignore[attr-defined]
        config = {
            "id": "m",
            "initial": "a",
            "context": {},
            "states": {"a": {"entry": ["do_thing"]}},
        }

        # Act
        machine = create_machine(config, logic_modules=[module])

        # Assert
        self.assertIn("do_thing", machine.logic.actions)


# -----------------------------------------------------------------------------
# 🔑 Spawn Service-Key Derivation
# -----------------------------------------------------------------------------
class TestSpawnServiceKeyDerivation(unittest.TestCase):
    """Pins the single source of truth for spawn key derivation.

    🐛 Regression: three sites derived the key differently. `Interpreter` used
    `type.replace("spawn_", "")` (unanchored and global) and `SyncInterpreter`
    used `type.split("_", 2)[-1]`, so multi-word and `spawn_blocking_` keys
    resolved to the wrong service — or none at all.
    """

    def test_simple_key(self) -> None:
        """A single-word key drops only its prefix."""
        self.assertEqual("worker", spawn_service_key("spawn_worker"))

    def test_multi_word_key_is_preserved(self) -> None:
        """`split("_", 2)[-1]` used to truncate this to 'worker'."""
        self.assertEqual("my_worker", spawn_service_key("spawn_my_worker"))

    def test_blocking_prefix_fully_stripped(self) -> None:
        """`replace("spawn_", "")` used to leave 'blocking_worker'."""
        self.assertEqual("worker", spawn_service_key("spawn_blocking_worker"))

    def test_inner_spawn_substring_is_not_stripped(self) -> None:
        """`replace` used to mangle this to 'rehandler'."""
        self.assertEqual(
            "respawn_handler", spawn_service_key("spawn_respawn_handler")
        )

    def test_non_spawn_action_unchanged(self) -> None:
        """A plain action type passes through untouched."""
        self.assertEqual("do_thing", spawn_service_key("do_thing"))

    def test_is_spawn_action_detection(self) -> None:
        """Both spawn flavours are detected; plain actions are not."""
        self.assertTrue(is_spawn_action("spawn_worker"))
        self.assertTrue(is_spawn_action("spawn_blocking_worker"))
        self.assertFalse(is_spawn_action("do_thing"))

    def test_loader_and_interpreter_agree_on_multi_word_key(self) -> None:
        """Discovery and lookup must derive the same key end-to-end."""
        # Arrange
        module = types.ModuleType("spawn_multiword_fixture")
        child = create_machine(
            {"id": "child", "initial": "i", "states": {"i": {}}},
            logic=MachineLogic(),
        )

        def my_worker(_i: Any, _c: Any, _e: Any) -> Any:
            """Returns the child machine to spawn."""
            return child

        module.my_worker = my_worker  # type: ignore[attr-defined]
        config = {
            "id": "m",
            "initial": "a",
            "context": {},
            "states": {"a": {"entry": ["spawn_my_worker"]}},
        }

        # Act
        machine = create_machine(config, logic_modules=[module])
        interpreter = SyncInterpreter(machine).start()
        # 🧹 Spawning starts a background actor thread; stop it so it cannot
        #    leak into unrelated tests that count live `actor-` threads.
        self.addCleanup(interpreter.stop)

        # Assert — the actor actually spawned rather than raising.
        self.assertIn("my_worker", machine.logic.services)
        self.assertEqual({"m.a"}, interpreter.active_state_ids)


# -----------------------------------------------------------------------------
# 🧠 Guard Evaluation Is Not Multiplied By Parallel Width
# -----------------------------------------------------------------------------
class TestSharedGuardEvaluatedOnce(unittest.TestCase):
    """Pins that a shared ancestor's guard runs once, not once per region.

    🐛 Regression: `_select_transitions` walks up from every active leaf, so an
    ancestor transition was guard-evaluated once per parallel region before
    de-duplication discarded the duplicates. Guards are documented as pure, but
    are commonly written with side effects (counters, metrics), and the
    `on_guard_evaluated` plugin hook fired N times for one logical decision.
    """

    def test_ancestor_guard_evaluated_once_across_regions(self) -> None:
        """Three regions must not trigger three guard evaluations."""
        # Arrange
        calls: list = []

        def counting_guard(_ctx: Any, _event: Any) -> bool:
            calls.append(1)
            return True

        config = {
            "id": "m",
            "initial": "par",
            "states": {
                "par": {
                    "type": "parallel",
                    "on": {"E": {"target": "#m.done", "guard": "g"}},
                    "states": {
                        "r1": {"initial": "s", "states": {"s": {}}},
                        "r2": {"initial": "s", "states": {"s": {}}},
                        "r3": {"initial": "s", "states": {"s": {}}},
                    },
                },
                "done": {},
            },
        }
        interpreter = SyncInterpreter(
            create_machine(
                config, logic=MachineLogic(guards={"g": counting_guard})
            )
        ).start()

        # Act
        interpreter.send("E")

        # Assert
        self.assertEqual(1, len(calls))
        self.assertEqual({"m.done"}, interpreter.active_state_ids)


# -----------------------------------------------------------------------------
# 🧬 Documented `MachineLogic` Subclass Authoring Style
# -----------------------------------------------------------------------------
class TestMachineLogicSubclassStyle(unittest.TestCase):
    """Pins the subclass authoring style shown throughout the guides.

    🐛 Regression: `docs/_guide/actions.md`, `guards.md`, `context.md` and
    `docs/api/index.md` all document defining logic as methods on a
    `MachineLogic` subclass. Nothing ever collected those methods, so every
    one of those published examples raised `ImplementationMissingError` on
    the first transition that used them.
    """

    def test_subclass_action_and_guard_are_registered(self) -> None:
        """Methods must resolve without any explicit dict wiring."""

        # Arrange
        class Logic(MachineLogic):
            """Logic authored in the documented subclass style."""

            def bump(self, _i: Any, ctx: Any, _e: Any, _a: Any) -> None:
                """A 4-arity method: an action."""
                ctx["n"] = ctx.get("n", 0) + 1

            def always_true(self, _c: Any, _e: Any) -> bool:
                """A 2-arity method: a guard."""
                return True

        config = {
            "id": "m",
            "initial": "a",
            "context": {},
            "states": {
                "a": {
                    "on": {
                        "E": {
                            "target": "b",
                            "guard": "always_true",
                            "actions": ["bump"],
                        }
                    }
                },
                "b": {},
            },
        }

        # Act
        interpreter = SyncInterpreter(
            create_machine(config, logic=Logic())
        ).start()
        interpreter.send("E")

        # Assert — the guard passed AND the action ran.
        self.assertEqual({"m.b"}, interpreter.active_state_ids)
        self.assertEqual(1, interpreter.context["n"])

    def test_subclass_service_is_registered(self) -> None:
        """A 3-arity method must register as an invokable service."""

        # Arrange
        class Logic(MachineLogic):
            """Logic exposing a service method."""

            def fetch(self, _i: Any, _c: Any, _e: Any) -> Dict[str, int]:
                """A 3-arity method: a service."""
                return {"v": 7}

        config = {
            "id": "m",
            "initial": "l",
            "states": {
                "l": {"invoke": {"src": "fetch", "onDone": "d"}},
                "d": {},
            },
        }

        # Act
        interpreter = SyncInterpreter(
            create_machine(config, logic=Logic())
        ).start()

        # Assert
        self.assertEqual({"m.d"}, interpreter.active_state_ids)

    def test_explicit_dict_wins_over_subclass_method(self) -> None:
        """Explicit wiring must remain the escape hatch.

        Arity-based classification cannot be right for every conceivable
        signature, so a constructor argument must always be able to override
        it rather than be silently replaced.
        """

        # Arrange
        class Logic(MachineLogic):
            """A subclass whose guard is deliberately overridden."""

            def gate(self, _c: Any, _e: Any) -> bool:
                """Returns False; the explicit binding returns True."""
                return False

        # Act
        logic = Logic(guards={"gate": lambda _c, _e: True})

        # Assert
        self.assertTrue(logic.guards["gate"](None, None))

    def test_private_methods_are_not_registered(self) -> None:
        """Underscore-prefixed helpers are implementation, not logic."""

        # Arrange
        class Logic(MachineLogic):
            """A subclass with a private helper of guard-like arity."""

            def _helper(self, _c: Any, _e: Any) -> bool:
                """A private helper that must stay unregistered."""
                return True

        # Act
        logic = Logic()

        # Assert
        self.assertNotIn("_helper", logic.guards)

    def test_plain_machine_logic_registers_nothing(self) -> None:
        """The base class must keep its empty-registry contract."""
        # Arrange / Act
        logic = MachineLogic()

        # Assert
        self.assertEqual({}, logic.actions)
        self.assertEqual({}, logic.guards)
        self.assertEqual({}, logic.services)


# -----------------------------------------------------------------------------
# 🛡️ Config Validation Reaches The User, Not A Raw TypeError
# -----------------------------------------------------------------------------
class TestMetadataConfigValidation(unittest.TestCase):
    """Pins actionable errors for malformed `tags` / `meta`.

    🐛 Regression: `set(raw_tags)` decided the outcome. `tags: 123` surfaced
    as "'int' object is not iterable" with no indication of WHICH state was
    wrong, and `tags: {"a": 1}` was silently accepted as the tag set `{"a"}`
    by iterating the mapping's keys — a typo that produced working-looking
    nonsense.
    """

    @staticmethod
    def _config(key: str, value: Any) -> Dict[str, Any]:
        """Builds a one-state machine carrying a metadata key."""
        return {
            "id": "m",
            "initial": "a",
            "states": {"a": {key: value}},
        }

    def test_non_iterable_tags_names_the_offending_state(self) -> None:
        """The message must identify the state and the expected shape."""
        # Act / Assert
        with self.assertRaises(InvalidConfigError) as caught:
            create_machine(self._config("tags", 123), logic=MachineLogic())

        self.assertIn("m.a", str(caught.exception))
        self.assertIn("tags", str(caught.exception))

    def test_dict_tags_are_rejected_not_silently_keyed(self) -> None:
        """A mapping must not be reinterpreted as its key set."""
        # Act / Assert
        with self.assertRaises(InvalidConfigError):
            create_machine(
                self._config("tags", {"a": 1}), logic=MachineLogic()
            )

    def test_non_string_tag_elements_are_rejected(self) -> None:
        """Every element must be a string."""
        # Act / Assert
        with self.assertRaises(InvalidConfigError) as caught:
            create_machine(
                self._config("tags", ["ok", 5]), logic=MachineLogic()
            )

        self.assertIn("5", str(caught.exception))

    def test_non_dict_meta_is_rejected(self) -> None:
        """`meta` must be an object, not a scalar."""
        # Act / Assert
        with self.assertRaises(InvalidConfigError):
            create_machine(self._config("meta", "nope"), logic=MachineLogic())

    def test_valid_tag_shapes_still_parse(self) -> None:
        """A bare string and a list must both keep working."""
        # Act
        single = create_machine(
            self._config("tags", "one"), logic=MachineLogic()
        )
        many = create_machine(
            self._config("tags", ["a", "b"]), logic=MachineLogic()
        )

        # Assert
        self.assertEqual({"one"}, single.states["a"].tags)
        self.assertEqual({"a", "b"}, many.states["a"].tags)


# -----------------------------------------------------------------------------
# 🔤 CLI Output On Legacy Consoles
# -----------------------------------------------------------------------------
class TestCliSafePrint(unittest.TestCase):
    """Pins that emoji-rich CLI output degrades instead of leaking escapes.

    🐛 Regression: `_safe_print` only caught `UnicodeEncodeError`, so it was
    structurally blind to a stream built with `errors="backslashreplace"` —
    which never raises and instead prints a literal `✅` to the user's
    terminal.
    """

    def _capture(self, errors: str) -> bytes:
        """Runs `_safe_print` against a cp1252 stream with `errors`."""
        # Arrange
        buffer = io.BytesIO()
        stream = io.TextIOWrapper(buffer, encoding="cp1252", errors=errors)
        original = sys.stdout
        sys.stdout = stream
        try:
            _safe_print("OK ✅ DONE")
            stream.flush()
        finally:
            sys.stdout = original
        return buffer.getvalue()

    def test_strict_stream_does_not_raise(self) -> None:
        """The historic failure mode stays fixed."""
        self.assertIn(b"OK ", self._capture("strict"))

    def test_backslashreplace_stream_emits_no_literal_escape(self) -> None:
        """The silent failure mode must not print `✅`."""
        # Act
        written = self._capture("backslashreplace")

        # Assert
        self.assertNotIn(rb"\u2705", written)
        self.assertIn(b"OK ", written)
        self.assertIn(b"DONE", written)

    def test_utf8_stream_preserves_the_emoji(self) -> None:
        """A capable console must still get the real character."""
        # Arrange
        buffer = io.BytesIO()
        stream = io.TextIOWrapper(buffer, encoding="utf-8")
        original = sys.stdout
        sys.stdout = stream
        try:
            _safe_print("OK ✅")
            stream.flush()
        finally:
            sys.stdout = original

        # Assert
        self.assertIn("✅".encode("utf-8"), buffer.getvalue())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
