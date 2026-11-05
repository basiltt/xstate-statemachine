# tests/test_review_fixes_cross_group.py
# -----------------------------------------------------------------------------
# 🛡️ 0.12.0 code-review fixes: the cross-group requests
# -----------------------------------------------------------------------------
# 🏛️ The review ran as ten independent groups, each owning a set of modules.
# A finding whose fix lived in ANOTHER group's module was handed over as a
# cross-group request. This file pins those fixes: the typed error for an
# unresolved delivery target (BI-32), owner-filtered clock pumps for a child
# sharing its parent's SimulatedClock (ENG-06), the deep-copy fallback for an
# uncopyable initial context (PD-11), discovery of static methods, of the
# user's own built-in-named actions and of spawn actions inside invoke
# handlers (RU-04/05/06), and the factory's argument checks (RU-20..22).
# -----------------------------------------------------------------------------
"""Regression tests for the cross-group review requests."""

import threading
import time
import types
import unittest
import warnings
from typing import Any, Dict, List

from src.xstate_statemachine import (
    ActorSpawningError,
    InvalidConfigError,
    MachineLogic,
    SyncInterpreter,
    UnresolvedTargetError,
    create_machine,
)
from src.xstate_statemachine.clock import SimulatedClock
from src.xstate_statemachine.logic_loader import LogicLoader
from src.xstate_statemachine.models import MachineNode

_SIMPLE: Dict[str, Any] = {
    "id": "m",
    "initial": "a",
    "states": {"a": {"on": {"GO": "b"}}, "b": {}},
}


def _module(name: str, **members: Any) -> types.ModuleType:
    """A throwaway module holding *members*, each stamped as defined there."""
    mod = types.ModuleType(name)
    for key, value in members.items():
        if callable(value) and getattr(value, "__module__", None) != "else":
            value.__module__ = name
        setattr(mod, key, value)
    return mod


# -----------------------------------------------------------------------------
# BI-32: a typed error for an unresolved delivery target
# -----------------------------------------------------------------------------
class TestUnresolvedTargetError(unittest.TestCase):
    """`sendTo` & co. that reach no live actor record a typed soft error."""

    def test_is_an_actor_spawning_error_for_old_handlers(self) -> None:
        self.assertTrue(issubclass(UnresolvedTargetError, ActorSpawningError))

    def test_send_parent_without_a_parent_records_the_typed_error(
        self,
    ) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {
                    "on": {
                        "GO": {
                            "target": "b",
                            "actions": [
                                {
                                    "type": "sendParent",
                                    "params": {"event": "X"},
                                }
                            ],
                        }
                    }
                },
                "b": {},
            },
        }
        interp = SyncInterpreter(create_machine(cfg)).start()
        interp.send("GO")
        self.assertIn("m.b", interp.current_state_ids)  # still committed
        self.assertFalse(interp.last_transition_ok)
        self.assertIsInstance(interp.last_error, UnresolvedTargetError)
        self.assertIsInstance(interp.last_error, ActorSpawningError)
        self.assertIn("sendParent", str(interp.last_error))
        interp.stop()


# -----------------------------------------------------------------------------
# ENG-06: a child sharing its parent's SimulatedClock pumps only its own timers
# -----------------------------------------------------------------------------
class TestSharedClockPump(unittest.TestCase):
    """Owner-filtered pumps keep a parent's deadlines on the parent's thread."""

    def test_pump_filtered_fires_only_the_matching_owners(self) -> None:
        clock = SimulatedClock()
        fired: List[str] = []
        clock.set_timeout(lambda: fired.append("p"), 1.0, owner="parent.w")
        clock.set_timeout(lambda: fired.append("c"), 1.0, owner="kid.x")
        clock._now = 5.0  # both due; move time WITHOUT firing

        kid_only = clock.pump_filtered(
            lambda o: isinstance(o, str) and o.startswith("kid.")
        )

        self.assertEqual(kid_only, 1)
        self.assertEqual(fired, ["c"])
        self.assertEqual(clock.pending, 1)  # the parent's is still queued
        self.assertEqual(clock.pump(), 1)
        self.assertEqual(fired, ["c", "p"])

    def test_pump_filtered_keeps_deadline_order_for_the_rest(self) -> None:
        clock = SimulatedClock()
        fired: List[str] = []
        clock.set_timeout(lambda: fired.append("p1"), 1.0, owner="p")
        clock.set_timeout(lambda: fired.append("c"), 2.0, owner="c")
        clock.set_timeout(lambda: fired.append("p2"), 3.0, owner="p")
        clock._now = 5.0
        self.assertEqual(clock.pump_filtered(lambda o: o == "c"), 1)
        self.assertEqual(clock.pump(), 2)
        self.assertEqual(fired, ["c", "p1", "p2"])

    def test_child_pump_thread_leaves_the_parents_deadline_alone(
        self,
    ) -> None:
        clock = SimulatedClock()
        child_cfg = {
            "id": "kid",
            "initial": "w",
            "states": {
                "w": {"after": {500: "done"}},
                "done": {"type": "final"},
            },
        }
        parent_cfg = {
            "id": "par",
            "initial": "waiting",
            "states": {
                "waiting": {"invoke": {"src": "kid"}, "after": {1000: "late"}},
                "late": {},
            },
        }
        logic = MachineLogic(services={"kid": create_machine(child_cfg)})
        parent = SyncInterpreter(
            create_machine(parent_cfg, logic=logic), clock=clock
        ).start()
        try:
            child = next(iter(parent._actors.values()))
            self.assertTrue(child._shares_parent_clock)
            self.assertIs(child.clock, clock)

            clock._now = 5.0  # both the child's and the parent's are due
            deadline = time.monotonic() + 5.0
            while child.status == "running" and time.monotonic() < deadline:
                time.sleep(0.01)  # the child's runner thread pumps it

            self.assertNotEqual(child.status, "running")
            # 🧵 The child's pump ran on ITS thread and must not have fired
            #    the parent's `after` deadline off the parent's thread.
            self.assertIn("par.waiting", parent.current_state_ids)
            parent.tick()  # the owner thread fires it
            self.assertIn("par.late", parent.current_state_ids)
        finally:
            parent.stop()


# -----------------------------------------------------------------------------
# PD-11: an uncopyable handle in the initial context
# -----------------------------------------------------------------------------
class TestUncopyableInitialContext(unittest.TestCase):
    """A lock (or DB session) in `context` no longer breaks construction."""

    def test_lock_in_context_builds_and_starts_with_a_warning(self) -> None:
        lock = threading.Lock()
        cfg = {
            "id": "m",
            "initial": "a",
            "context": {"lock": lock, "n": 0},
            "states": {"a": {"on": {"GO": "b"}}, "b": {}},
        }
        machine = create_machine(cfg)
        with self.assertLogs(level="WARNING") as logs:
            interp = SyncInterpreter(machine).start()
        self.assertTrue(
            any("deep-copied" in line for line in logs.output), logs.output
        )
        self.assertIs(interp.context["lock"], lock)  # shared, not lost
        self.assertEqual(interp.context["n"], 0)
        interp.send("GO")
        self.assertIn("m.b", interp.current_state_ids)
        interp.stop()

    def test_context_factory_result_gets_the_same_fallback(self) -> None:
        lock = threading.Lock()
        cfg = {
            "id": "m",
            "initial": "a",
            "context": lambda _input: {"lock": lock},
            "states": {"a": {}},
        }
        interp = SyncInterpreter(create_machine(cfg)).start()
        self.assertIs(interp.context["lock"], lock)
        interp.stop()


# -----------------------------------------------------------------------------
# RU-04 / RU-05 / RU-06: logic discovery
# -----------------------------------------------------------------------------
class TestDiscoveryCrossGroup(unittest.TestCase):
    """Static methods, the user's own built-in-named actions, spawn routing."""

    def test_staticmethod_on_a_provider_is_discovered(self) -> None:
        class Provider:
            @staticmethod
            def mark(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
                ctx["marked"] = True

            def can_go(self, ctx: Dict[str, Any], e: Any) -> bool:
                return True

        cfg = {
            "id": "m",
            "initial": "a",
            "context": {"marked": False},
            "states": {
                "a": {
                    "entry": "mark",
                    "on": {"GO": {"target": "b", "guard": "canGo"}},
                },
                "b": {},
            },
        }
        machine = create_machine(cfg, logic_providers=[Provider()])
        interp = SyncInterpreter(machine).start()
        self.assertTrue(interp.context["marked"])
        interp.send("GO")
        self.assertIn("m.b", interp.current_state_ids)
        interp.stop()

    def test_module_defined_builtin_name_overrides_the_builtin(self) -> None:
        calls: List[str] = []

        def log(i: Any, ctx: Any, e: Any, a: Any) -> None:
            calls.append("user")

        mod = _module("owned_logic_mod", log=log)
        cfg = {"id": "m", "initial": "a", "states": {"a": {"entry": "log"}}}
        machine = create_machine(cfg, logic_modules=[mod])
        self.assertIs(machine.logic.actions["log"], log)
        SyncInterpreter(machine).start().stop()
        self.assertEqual(calls, ["user"])

    def test_imported_builtin_name_does_not_override_the_builtin(
        self,
    ) -> None:
        def log(i: Any, ctx: Any, e: Any, a: Any) -> None:
            raise AssertionError("an imported helper must not bind")

        log.__module__ = "else"  # `from somewhere import log`
        mod = _module("importer_mod", log=log)
        cfg = {"id": "m", "initial": "a", "states": {"a": {"entry": "log"}}}
        machine = create_machine(cfg, logic_modules=[mod])
        self.assertNotIn("log", machine.logic.actions)
        SyncInterpreter(machine).start().stop()  # the built-in `log` ran

    def test_provider_method_named_like_a_builtin_is_bound(self) -> None:
        class Provider:
            def __init__(self) -> None:
                self.cancelled: List[str] = []

            def cancel(self, i: Any, ctx: Any, e: Any, a: Any) -> None:
                self.cancelled.append(e.type)

        provider = Provider()
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"on": {"GO": {"actions": "cancel"}}}},
        }
        interp = SyncInterpreter(
            create_machine(cfg, logic_providers=[provider])
        ).start()
        interp.send("GO")
        self.assertEqual(provider.cancelled, ["GO"])
        interp.stop()

    def test_spawn_inside_invoke_handlers_routes_to_services(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {
                    "invoke": {
                        "src": "job",
                        "onDone": {"target": "b", "actions": "spawn_worker"},
                        "onError": {"actions": "spawn_blocking_cleaner"},
                    }
                },
                "b": {},
            },
        }
        node = MachineNode(cfg, MachineLogic())
        actions, _guards, services = LogicLoader.required_names(node)
        self.assertEqual(services, {"job", "worker", "cleaner"})
        self.assertNotIn("spawn_worker", actions)
        self.assertNotIn("spawn_blocking_cleaner", actions)

    def test_builtin_action_names_are_reported_as_spelled(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {
                    "entry": [
                        "log",
                        {
                            "type": "send_to",
                            "params": {"to": "x", "event": "E"},
                        },
                    ],
                    "on": {"GO": {"actions": "mine"}},
                }
            },
        }
        node = MachineNode(cfg, MachineLogic())
        self.assertEqual(
            LogicLoader.builtin_action_names(node), {"log", "send_to"}
        )
        actions, _g, _s = LogicLoader.required_names(node)
        self.assertEqual(actions, {"mine"})


# -----------------------------------------------------------------------------
# RU-20 / RU-21 / RU-22: factory argument checks
# -----------------------------------------------------------------------------
class TestFactoryArgumentChecks(unittest.TestCase):
    """Explicit logic plus discovery sources warns; schemas are validated."""

    def test_logic_with_modules_warns_at_the_call_site(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            create_machine(
                _SIMPLE,
                logic=MachineLogic(),
                logic_modules=[_module("unused_mod")],
            )
        hits = [w for w in caught if "NOT scanned" in str(w.message)]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].filename, __file__)

    def test_logic_alone_does_not_warn(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            create_machine(_SIMPLE, logic=MachineLogic())
        self.assertFalse(
            [w for w in caught if "NOT scanned" in str(w.message)]
        )

    def test_event_schema_values_are_validated_at_build(self) -> None:
        with self.assertRaisesRegex(InvalidConfigError, "callable"):
            create_machine(_SIMPLE, event_schemas={"GO": 42})
        with self.assertRaisesRegex(InvalidConfigError, "non-empty"):
            create_machine(_SIMPLE, event_schemas={"": lambda p: None})
        with self.assertRaisesRegex(InvalidConfigError, "dict"):
            create_machine(_SIMPLE, event_schemas=[("GO", lambda p: None)])  # type: ignore[arg-type]

        class Model:
            @staticmethod
            def validate(payload: Any) -> None:
                return None

        machine = create_machine(
            _SIMPLE, event_schemas={"GO": Model, "OTHER": lambda p: None}
        )
        self.assertEqual(set(machine.event_schemas), {"GO", "OTHER"})

    def test_collapsed_config_names_warning_points_at_the_caller(
        self,
    ) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"entry": ["storeUser", "store_user"]}},
        }
        logic = MachineLogic(actions={"store_user": lambda i, c, e, a: None})
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            create_machine(cfg, logic=logic)
        hits = [w for w in caught if "spell it one way" in str(w.message)]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].filename, __file__)

    def test_shadowed_registry_names_warning_points_at_the_caller(
        self,
    ) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"entry": "storeUser"}},
        }
        logic = MachineLogic(
            actions={
                "storeUser": lambda i, c, e, a: None,
                "store_user": lambda i, c, e, a: None,
            }
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            create_machine(cfg, logic=logic)
        hits = [w for w in caught if "registered exactly" in str(w.message)]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].filename, __file__)


if __name__ == "__main__":
    unittest.main()
