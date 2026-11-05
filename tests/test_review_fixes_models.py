# tests/test_review_fixes_models.py
# -----------------------------------------------------------------------------
# 🛡️ 0.12.0 code-review fixes: config parsing, events, resolution, validation
# -----------------------------------------------------------------------------
# 🏛️ Config parsing is a trust boundary. Every test here pins a value the
# parser used to accept silently (or a library side effect it used to have)
# and that now either works the way XState v5 defines it or fails loudly
# with an `InvalidConfigError` naming the state, key and value.
# -----------------------------------------------------------------------------
"""Regression tests for the models / events / resolver / validation review."""

import contextlib
import logging
import unittest
import warnings
from typing import Any, Dict, Iterator, List

from src.xstate_statemachine import (
    Interpreter,
    InvalidConfigError,
    MachineLogic,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.events import (
    _engine_after,
    _engine_done,
    _engine_error,
    is_system_event,
    persist_event,
    restore_event,
)
from src.xstate_statemachine.exceptions import SnapshotCorruptError
from src.xstate_statemachine.logic_loader import LogicLoader
from src.xstate_statemachine.models import ActionDefinition, MachineNode
from src.xstate_statemachine.resolver import resolve_target_state


def _node(config: Dict[str, Any]) -> MachineNode:
    """Parse *config* without logic or build-time validation."""
    return MachineNode(config, MachineLogic())


def _one_state(state: Dict[str, Any], **root: Any) -> Dict[str, Any]:
    """A machine ``m`` whose only state ``a`` is *state*."""
    return {"id": "m", "initial": "a", "states": {"a": state}, **root}


class _Quiet(unittest.TestCase):
    """Silences library logging unless a test captures it."""

    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)


class TestRootLoggerUntouched(unittest.TestCase):
    """MOD-01: parsing an invoke must not configure the root logger."""

    def test_invoke_parse_installs_no_root_handler(self) -> None:
        # Arrange
        root = logging.getLogger()
        saved = list(root.handlers)
        for handler in saved:
            root.removeHandler(handler)
        self.addCleanup(lambda: [root.addHandler(h) for h in saved])

        # Act
        _node(_one_state({"invoke": {"src": "svc"}}))
        _node(_one_state({"invoke": {}}))  # the missing-`src` warning path

        # Assert
        self.assertEqual([], root.handlers)

    def test_missing_src_warning_uses_the_library_logger(self) -> None:
        with self.assertLogs("src.xstate_statemachine.models", "WARNING"):
            _node(_one_state({"invoke": {}}))


class TestOnDoneList(_Quiet):
    """MOD-02: every `onDone` alternative is kept, not just the first."""

    CONFIG: Dict[str, Any] = {
        "id": "m",
        "initial": "a",
        "states": {
            "a": {
                "initial": "x",
                "states": {"x": {"on": {"E": "y"}}, "y": {"type": "final"}},
                "onDone": [
                    {"target": "b", "guard": "isB"},
                    {"target": "c", "actions": "mark"},
                ],
            },
            "b": {},
            "c": {},
        },
    }

    def _logic(self, marks: List[str]) -> MachineLogic:
        return MachineLogic(
            guards={"isB": lambda c, e: False},
            actions={"mark": lambda i, c, e, a: marks.append("c")},
        )

    def test_both_alternatives_are_parsed(self) -> None:
        machine = create_machine(self.CONFIG, logic=self._logic([]))
        node = machine.states["a"]
        self.assertEqual(
            ["b", "c"], [t.target_str for t in node.on_done_transitions]
        )
        self.assertIs(node.on_done, node.on_done_transitions[0])

    def test_discovery_requires_logic_of_every_alternative(self) -> None:
        actions, guards, _ = LogicLoader.required_names(_node(self.CONFIG))
        self.assertIn("mark", actions)
        self.assertIn("isB", guards)

    def test_unresolvable_target_in_a_later_alternative_is_rejected(
        self,
    ) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {
                    "initial": "x",
                    "states": {"x": {"type": "final"}},
                    "onDone": [{"target": "b", "guard": "g"}, "nope"],
                },
                "b": {},
            },
        }
        logic = MachineLogic(guards={"g": lambda c, e: True})
        with self.assertRaisesRegex(InvalidConfigError, "nope"):
            create_machine(cfg, logic=logic)

    def test_fallback_alternative_fires_when_the_guard_fails(self) -> None:
        marks: List[str] = []
        machine = create_machine(self.CONFIG, logic=self._logic(marks))
        interpreter = SyncInterpreter(machine).start()
        self.addCleanup(interpreter.stop)
        interpreter.send("E")
        self.assertEqual({"m.c"}, interpreter.current_state_ids)
        self.assertEqual(["c"], marks)


class TestStateTypeValidation(_Quiet):
    """MOD-03: a mistyped `type` no longer changes semantics silently."""

    def test_miscased_final_on_a_leaf_is_rejected(self) -> None:
        with self.assertRaisesRegex(InvalidConfigError, r"m\.a.*'Final'"):
            _node(_one_state({"type": "Final"}))

    def test_misspelled_parallel_on_a_parent_is_rejected(self) -> None:
        cfg = _one_state({"type": "paralel", "states": {"x": {}, "y": {}}})
        with self.assertRaisesRegex(InvalidConfigError, "'paralel'"):
            _node(cfg)

    def test_compound_or_parallel_without_children_is_rejected(self) -> None:
        for kind in ("compound", "parallel"):
            with self.subTest(kind=kind):
                with self.assertRaisesRegex(InvalidConfigError, "no child"):
                    _node(_one_state({"type": kind}))

    def test_final_with_children_stays_compound_and_warns(self) -> None:
        # 📝 Compatibility: real Stately exports ship this shape.
        cfg = _one_state(
            {
                "type": "final",
                "initial": "x",
                "states": {"x": {"type": "final"}},
            }
        )
        logging.disable(logging.NOTSET)
        with self.assertLogs("src.xstate_statemachine.models", "WARNING"):
            node = _node(cfg)
        self.assertEqual("compound", node.states["a"].type)

    def test_valid_types_still_build(self) -> None:
        node = _node(
            {
                "id": "m",
                "type": "parallel",
                "states": {
                    "r": {"initial": "x", "states": {"x": {"type": "final"}}},
                    "s": {"type": "atomic"},
                },
            }
        )
        self.assertEqual("parallel", node.type)
        self.assertEqual("final", node.states["r"].states["x"].type)


class TestHistoryValidation(_Quiet):
    """MOD-04: a `history` typo is an error, not a silent shallow."""

    def _cfg(self, history: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": "m",
            "initial": "a",
            "states": {"a": {}, "h": {"type": "history", **history}},
        }

    def test_invalid_kind_is_rejected(self) -> None:
        with self.assertRaisesRegex(InvalidConfigError, r"m\.h.*'dep'"):
            _node(self._cfg({"history": "dep"}))

    def test_kind_defaults_to_shallow_and_deep_is_kept(self) -> None:
        self.assertEqual("shallow", _node(self._cfg({})).states["h"].history)
        deep = _node(self._cfg({"history": "deep"}))
        self.assertEqual("deep", deep.states["h"].history)

    def test_non_string_default_target_is_rejected(self) -> None:
        with self.assertRaisesRegex(InvalidConfigError, "'target'"):
            _node(self._cfg({"target": 5}))


class TestBooleanFlags(_Quiet):
    """MOD-05: flags accept only true/false; ``"false"`` is not truthy."""

    def test_string_root_flags_are_rejected(self) -> None:
        for key in ("strict", "strictTargets"):
            with self.subTest(key=key):
                cfg = _one_state({}, **{key: "false"})
                with self.assertRaisesRegex(
                    InvalidConfigError, f"'{key}'.*'false'"
                ):
                    _node(cfg)

    def test_string_strict_config_is_rejected(self) -> None:
        with self.assertRaisesRegex(InvalidConfigError, "'strictConfig'"):
            create_machine(_one_state({}, strictConfig="no"))

    def test_string_transition_flags_are_rejected(self) -> None:
        for key in ("reenter", "internal"):
            with self.subTest(key=key):
                cfg = _one_state({"on": {"E": {"target": "a", key: "false"}}})
                with self.assertRaisesRegex(
                    InvalidConfigError, rf"Transition 'E'.*'{key}'"
                ):
                    _node(cfg)

    def test_real_booleans_and_null_still_work(self) -> None:
        node = _node(_one_state({}, strict=True, strictTargets=None))
        self.assertTrue(node.strict)
        self.assertFalse(node.strict_targets)
        on = (
            _node(
                _one_state(
                    {
                        "on": {
                            "R": {"target": "a", "reenter": True},
                            "I": {"target": "a", "internal": False},
                        }
                    }
                )
            )
            .states["a"]
            .on
        )
        self.assertTrue(on["R"][0].reenter)
        self.assertTrue(on["I"][0].reenter)


class TestUserActionNamedLikeBuiltin(_Quiet):
    """MOD-06: a user action spelled like a built-in wins, params and all."""

    CONFIG = _one_state(
        {"entry": [{"type": "cancel", "params": {"orderId": 7}}]},
        strictConfig=True,
    )

    @staticmethod
    def _logic(seen: List[Any]) -> MachineLogic:
        return MachineLogic(
            actions={"cancel": lambda i, c, e, a: seen.append(a.params)}
        )

    def test_sync_engine_runs_the_user_action(self) -> None:
        seen: List[Any] = []
        machine = create_machine(self.CONFIG, logic=self._logic(seen))
        interpreter = SyncInterpreter(machine).start()
        self.addCleanup(interpreter.stop)
        self.assertEqual([{"orderId": 7}], seen)


class TestUserActionNamedLikeBuiltinAsync(unittest.IsolatedAsyncioTestCase):
    """MOD-06 on the async engine."""

    async def test_async_engine_runs_the_user_action(self) -> None:
        seen: List[Any] = []
        machine = create_machine(
            TestUserActionNamedLikeBuiltin.CONFIG,
            logic=TestUserActionNamedLikeBuiltin._logic(seen),
        )
        interpreter = await Interpreter(machine).start()
        try:
            self.assertEqual([{"orderId": 7}], seen)
        finally:
            await interpreter.stop()


class TestBuiltinParamsStillChecked(_Quiet):
    """MOD-06: without a user implementation the built-in check stays."""

    def test_builtin_cancel_without_send_id_is_rejected(self) -> None:
        cfg = _one_state({"entry": [{"type": "cancel", "params": {}}]})
        with self.assertRaisesRegex(
            InvalidConfigError, r"m\.a' entry.*sendId"
        ):
            _node(cfg)


class TestRestoreUsesPrivateMinters(unittest.TestCase):
    """EVT-01: restoring an engine event must not trip a deprecation."""

    def test_every_engine_kind_restores_without_warning(self) -> None:
        events = [
            _engine_done("done.invoke.s", {"ok": 1}, "s"),
            _engine_error("error.platform.s", ValueError("x"), "s"),
            _engine_after("after.5.m.a", 1.0, 1.5),
        ]
        for event in events:
            with self.subTest(kind=type(event).__name__):
                with warnings.catch_warnings():
                    warnings.simplefilter("error")
                    restored = restore_event(persist_event(event))
                self.assertTrue(is_system_event(restored))
                self.assertEqual(event.type, restored.type)


class TestErrorsNameTheirLocation(_Quiet):
    """MOD-07: parse errors name the state and the key."""

    def test_bad_entry_action_names_state_and_key(self) -> None:
        with self.assertRaisesRegex(InvalidConfigError, r"State 'm\.a' entry"):
            _node(_one_state({"entry": [5]}))

    def test_bad_transition_action_names_the_event(self) -> None:
        cfg = _one_state({"on": {"GO": {"actions": [5]}}})
        with self.assertRaisesRegex(InvalidConfigError, "transition 'GO'"):
            _node(cfg)

    def test_bad_guard_names_the_transition(self) -> None:
        cfg = _one_state({"on": {"GO": {"guard": 5}}})
        with self.assertRaisesRegex(
            InvalidConfigError, r"Transition 'GO' on state 'm\.a'.*guard"
        ):
            _node(cfg)

    def test_bad_transition_item_names_state_and_event(self) -> None:
        cfg = _one_state({"on": {"GO": [5]}})
        with self.assertRaisesRegex(
            InvalidConfigError, r"State 'm\.a' on 'GO'.*transition item"
        ):
            _node(cfg)


class TestActionShape(_Quiet):
    """MOD-08: action objects are validated, not guessed."""

    def test_missing_type_is_rejected(self) -> None:
        with self.assertRaisesRegex(InvalidConfigError, "'type'"):
            ActionDefinition({"params": {}})

    def test_non_mapping_params_is_rejected(self) -> None:
        with self.assertRaisesRegex(InvalidConfigError, "'params'"):
            ActionDefinition({"type": "raise", "params": 5})

    def test_callable_params_are_accepted(self) -> None:
        action = ActionDefinition({"type": "doIt", "params": lambda a: {}})
        self.assertTrue(callable(action.params))

    def test_unknown_builtin_param_is_reported(self) -> None:
        cfg = _one_state(
            {
                "entry": [
                    {"type": "raise", "params": {"event": "X", "delya": 5}}
                ],
                "on": {"X": {}},
            },
            strictConfig=True,
        )
        with self.assertRaisesRegex(InvalidConfigError, "'delya'"):
            create_machine(cfg)


class TestRootNumbers(_Quiet):
    """MOD-09: numeric root options are range-checked, never truncated."""

    def test_bad_max_iterations_are_rejected(self) -> None:
        for value in (0, -3, 2.9, True, "nan", "abc"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(
                    InvalidConfigError, "'maxIterations'"
                ):
                    _node(_one_state({}, maxIterations=value))

    def test_whole_numbers_are_accepted(self) -> None:
        for value in (1, "5", 5.0):
            with self.subTest(value=value):
                node = _node(_one_state({}, maxIterations=value))
                self.assertEqual(int(float(value)), node.max_iterations)

    def test_bad_spawn_blocking_timeouts_are_rejected(self) -> None:
        for value in ("nan", "inf", -1, True, "x"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(
                    InvalidConfigError, "'spawnBlockingTimeout'"
                ):
                    _node(_one_state({}, spawnBlockingTimeout=value))

    def test_valid_timeouts_are_kept(self) -> None:
        node = _node(_one_state({}, spawnBlockingTimeout=0))
        self.assertEqual(0.0, node.spawn_blocking_timeout_ms)
        self.assertIsNone(_node(_one_state({})).spawn_blocking_timeout_ms)


class TestInitialValidation(_Quiet):
    """MOD-10: an unknown `initial` fails at build time, with a hint."""

    def test_unknown_initial_is_rejected_with_a_suggestion(self) -> None:
        cfg = {"id": "m", "initial": "idel", "states": {"idle": {}, "b": {}}}
        with self.assertRaisesRegex(
            InvalidConfigError, r"State 'm'.*'idel'.*Did you mean 'idle'"
        ):
            _node(cfg)

    def test_nested_unknown_initial_is_rejected(self) -> None:
        cfg = _one_state({"initial": "zzz", "states": {"x": {}}})
        with self.assertRaisesRegex(InvalidConfigError, r"m\.a.*'zzz'"):
            _node(cfg)


class TestAfterKeys(_Quiet):
    """MOD-11: `after` keys are whole milliseconds or a delay name."""

    def _after(self, after: Dict[Any, Any]) -> Dict[Any, Any]:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"after": after}, "b": {}, "c": {}},
        }
        return _node(cfg).states["a"].after

    def test_bad_numeric_keys_are_rejected(self) -> None:
        for key in (1.5, "1.5", -5, "-5", True, "", float("nan")):
            with self.subTest(key=key):
                with self.assertRaisesRegex(InvalidConfigError, "'after' key"):
                    self._after({key: "b"})

    def test_colliding_keys_are_rejected(self) -> None:
        with self.assertRaisesRegex(InvalidConfigError, "both name"):
            self._after({"100": "b", " 100": "c"})

    def test_valid_keys_and_event_names(self) -> None:
        after = self._after({"500": "b", 250: "c", "1e3": "b", "SLOW": "c"})
        self.assertEqual({500, 250, 1000, "SLOW"}, set(after))
        self.assertEqual("after.1000.m.a", after[1000][0].event)


class TestReadSiteTypeChecks(_Quiet):
    """MOD-12: keys that were stored unchecked are validated where read."""

    CASES: List[Any] = [
        ("invoke id", _one_state({"invoke": {"id": 5, "src": "s"}}), "'id'"),
        (
            "systemId",
            _one_state({"invoke": {"src": "s", "systemId": 5}}),
            "'systemId'",
        ),
        ("description", _one_state({"description": 5}), "'description'"),
        (
            "empty state key",
            {"id": "m", "initial": "a", "states": {"a": {}, "": {}}},
            "state key",
        ),
        ("empty target", _one_state({"on": {"E": ""}}), "empty string"),
        ("entry 0", _one_state({"entry": 0}), r"m\.a' entry"),
        ("entry False", _one_state({"entry": False}), r"m\.a' entry"),
        ("exit ''", _one_state({"exit": ""}), r"m\.a' exit"),
    ]

    def test_each_bad_value_is_rejected(self) -> None:
        for label, cfg, pattern in self.CASES:
            with self.subTest(label):
                with self.assertRaisesRegex(InvalidConfigError, pattern):
                    _node(cfg)

    def test_empty_action_list_and_absent_keys_still_build(self) -> None:
        node = _node(_one_state({"entry": [], "exit": None}))
        self.assertEqual([], node.states["a"].entry)


@contextlib.contextmanager
def _no_logs(logger_name: str, level: int) -> Iterator[None]:
    """Fail if *logger_name* emits a record at or above *level*.

    📝 `TestCase.assertNoLogs` is Python 3.10+; this library's floor is 3.9,
    so the records are captured by hand (as `tests/test_actor_lifecycle.py`
    does). The logger's own level is lifted for the block so a record the
    code emits is seen even when the logger is configured quieter.
    """
    logger = logging.getLogger(logger_name)
    records: List[logging.LogRecord] = []
    handler = logging.Handler(level)
    handler.emit = records.append  # type: ignore[method-assign]
    previous_level = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    try:
        yield
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)
    if records:
        raise AssertionError(
            f"{logger_name} logged at {logging.getLevelName(level)}+: "
            f"{[r.getMessage() for r in records]}"
        )


class TestDottedIds(_Quiet):
    """MOD-13 / RES-01: dots in ids and keys are honoured everywhere."""

    def test_get_state_by_id_with_dotted_machine_id(self) -> None:
        node = _node({"id": "my.machine", "initial": "a", "states": {"a": {}}})
        self.assertIs(node.states["a"], node.get_state_by_id("my.machine.a"))
        self.assertIs(node, node.get_state_by_id("my.machine"))

    def test_get_state_by_id_with_dotted_state_key(self) -> None:
        node = _node(
            {
                "id": "m",
                "initial": "v1.0",
                "states": {"v1.0": {"initial": "x", "states": {"x": {}}}},
            }
        )
        found = node.get_state_by_id("m.v1.0.x")
        self.assertIsNotNone(found)
        self.assertEqual("m.v1.0.x", found.id)

    def test_miss_returns_none_without_a_warning(self) -> None:
        node = _node(_one_state({}))
        logging.disable(logging.NOTSET)
        with _no_logs("src.xstate_statemachine.models", logging.WARNING):
            self.assertIsNone(node.get_state_by_id("other.a"))
            self.assertIsNone(node.get_state_by_id("m.zzz"))

    def test_dotted_custom_id_is_targetable(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {"on": {"GO": "#my.id", "DEEP": "#my.id.leaf"}},
                "b": {
                    "id": "my.id",
                    "initial": "leaf",
                    "states": {"leaf": {}},
                },
            },
        }
        machine = create_machine(cfg)
        interpreter = SyncInterpreter(machine).start()
        self.addCleanup(interpreter.stop)
        interpreter.send("DEEP")
        self.assertEqual({"m.b.leaf"}, interpreter.current_state_ids)

    def test_failed_resolution_does_not_log_errors(self) -> None:
        node = _node(_one_state({}))
        logging.disable(logging.NOTSET)
        with _no_logs("src.xstate_statemachine.resolver", logging.ERROR):
            with self.assertRaises(Exception):
                resolve_target_state("nowhere", node.states["a"])
            with self.assertRaises(Exception):
                resolve_target_state("a..b", node.states["a"])


class TestRestoreEventValidation(unittest.TestCase):
    """EVT-02: malformed records are `SnapshotCorruptError`, never a bare
    `TypeError` / `ValueError` or silently re-typed user traffic."""

    def test_malformed_records_are_rejected(self) -> None:
        records = [
            {"type": "A", "kind": "bogus"},
            {"type": "A", "payload": [1]},
            {"type": "A", "kind": "system", "payload": "abc"},
            {"type": "A", "kind": "after", "scheduled_for": "x"},
            {"type": "A", "kind": "after", "fired_at": [1]},
        ]
        for record in records:
            with self.subTest(record=record):
                with self.assertRaises(SnapshotCorruptError):
                    restore_event(record)

    def test_system_payload_may_hold_any_key(self) -> None:
        restored = restore_event(
            {"type": "A", "kind": "system", "payload": {"event_type": 1}}
        )
        self.assertTrue(is_system_event(restored))
        self.assertEqual({"event_type": 1}, restored.payload)


class TestUnknownActionAndGuardKeys(_Quiet):
    """VAL-01: `strictConfig` also checks action and guard objects."""

    LOGIC = MachineLogic(
        actions={"act": lambda i, c, e, a: None},
        guards={"g": lambda c, e: True, "h": lambda c, e: True},
    )

    def _build(self, state: Dict[str, Any]) -> None:
        create_machine(_one_state(state, strictConfig=True), logic=self.LOGIC)

    def test_misspelled_action_key_is_reported(self) -> None:
        with self.assertRaisesRegex(InvalidConfigError, r"entry.*'parms'"):
            self._build({"entry": [{"type": "act", "parms": {}}]})

    def test_misspelled_transition_action_key_is_reported(self) -> None:
        state = {"on": {"E": {"actions": {"type": "act", "prams": {}}}}}
        with self.assertRaisesRegex(InvalidConfigError, "'prams'"):
            self._build(state)

    def test_misspelled_guard_key_is_reported(self) -> None:
        state = {"on": {"E": {"guard": {"type": "g", "parmas": {}}}}}
        with self.assertRaisesRegex(
            InvalidConfigError, r"guard 'g'.*'parmas'"
        ):
            self._build(state)

    def test_nested_guard_key_is_reported(self) -> None:
        guard = {"type": "and", "children": ["g", {"type": "h", "x": 1}]}
        with self.assertRaisesRegex(InvalidConfigError, r"guard 'h'.*'x'"):
            self._build({"on": {"E": {"guard": guard}}})

    def test_non_string_key_is_reported(self) -> None:
        with self.assertRaisesRegex(InvalidConfigError, "not a string"):
            self._build({1: "x"})

    def test_well_formed_objects_pass(self) -> None:
        self._build(
            {
                "entry": [{"type": "act", "params": {"k": 1}}],
                "on": {
                    "E": {
                        "guard": {"type": "and", "children": ["g", "h"]},
                        "actions": [
                            {"type": "raise", "params": {"event": "E"}}
                        ],
                    }
                },
            }
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
