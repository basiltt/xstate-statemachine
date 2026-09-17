# tests/test_build_time_validation.py
# -----------------------------------------------------------------------------
# 🏛️ #29 / #30 / #31: silent runtime no-ops become build-time errors
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: an unknown ACTION already raised at
# create_machine(); an unknown TARGET, a dead `always` loop and a
# misspelled built-in key did not. Each was a silent no-op no test could
# catch. `validation.py` walks the finished tree once and reports every
# finding together.
# -----------------------------------------------------------------------------
"""Build-time validation and XState-conformant relative targets."""

import logging
import unittest
import warnings
from typing import Any, Dict

from src.xstate_statemachine import (
    InvalidConfigError,
    MachineLogic,
    SyncInterpreter,
    create_machine,
)


class _Quiet(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)


class TestUnresolvableTargets(_Quiet):
    """#30: every target must resolve at create_machine()."""

    def test_unknown_target_is_rejected_at_build_time(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"on": {"GO": "nope"}}},
        }
        with self.assertRaises(InvalidConfigError) as cm:
            create_machine(cfg)
        msg = str(cm.exception)
        self.assertIn("m.a", msg)
        self.assertIn("'nope'", msg)
        self.assertIn("does not resolve", msg)

    def test_all_failures_reported_together(self) -> None:
        """A rename that breaks many transitions is ONE message."""
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {
                    "on": {"X": "gone1", "Y": "gone2"},
                    "after": {"5": "gone3"},
                },
            },
        }
        with self.assertRaises(InvalidConfigError) as cm:
            create_machine(cfg)
        msg = str(cm.exception)
        for missing in ("gone1", "gone2", "gone3"):
            self.assertIn(missing, msg)

    def test_invoke_ondone_and_onerror_targets_are_checked(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {
                    "invoke": {
                        "src": "svc",
                        "onDone": "missing",
                        "onError": "b",
                    }
                },
                "b": {},
            },
        }
        with self.assertRaises(InvalidConfigError) as cm:
            create_machine(
                cfg, logic=MachineLogic(services={"svc": lambda *a: None})
            )
        self.assertIn("missing", str(cm.exception))

    def test_dotted_state_key_still_resolves(self) -> None:
        """Strict must not be stupid: an exact key like 'v2.0' is fine."""
        cfg = {
            "id": "m",
            "initial": "v1.0",
            "states": {"v1.0": {"on": {"G": "v2.0"}}, "v2.0": {}},
        }
        i = SyncInterpreter(create_machine(cfg)).start()
        i.send("G")
        self.assertEqual(i.current_state_ids, {"m.v2.0"})

    def test_strict_targets_false_warns_instead_of_raising(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"on": {"GO": "nope"}}},
        }
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            create_machine(cfg, strict_targets=False)
        deprecations = [
            w for w in caught if issubclass(w.category, DeprecationWarning)
        ]
        self.assertEqual(len(deprecations), 1)
        self.assertIn("nope", str(deprecations[0].message))
        self.assertIn("1.0", str(deprecations[0].message))


class TestAlwaysSelfTarget(_Quiet):
    """#29: a non-progressing `always` loop is rejected, not parked."""

    BASE: Dict[str, Any] = {
        "id": "m",
        "initial": "loop",
        "context": {"n": 0},
        "states": {"done": {}},
    }

    def _cfg(self, always: Any, entry: Any = "inc") -> Dict[str, Any]:
        cfg = {**self.BASE, "states": dict(self.BASE["states"])}
        cfg["states"]["loop"] = {"entry": entry, "always": always}
        return cfg

    def _logic(self) -> MachineLogic:
        def inc(i, c, e, a):
            c["n"] += 1

        return MachineLogic(
            actions={"inc": inc}, guards={"enough": lambda c, e: c["n"] >= 3}
        )

    def test_always_self_target_is_rejected_at_build_time(self) -> None:
        cfg = self._cfg(
            [{"target": "done", "guard": "enough"}, {"target": "loop"}]
        )
        with self.assertRaises(InvalidConfigError) as cm:
            create_machine(cfg, logic=self._logic())
        msg = str(cm.exception)
        self.assertIn("m.loop", msg)
        self.assertIn("can never make progress", msg)
        self.assertIn("reenter", msg)

    def test_always_self_target_with_reenter_is_allowed_and_converges(
        self,
    ) -> None:
        cfg = self._cfg(
            [
                {"target": "done", "guard": "enough"},
                {"target": "loop", "reenter": True},
            ]
        )
        i = SyncInterpreter(create_machine(cfg, logic=self._logic())).start()
        self.assertEqual(i.current_state_ids, {"m.done"})
        self.assertEqual(i.context["n"], 3)

    def test_always_self_target_with_actions_is_not_flagged(self) -> None:
        """An action CAN mutate context and let the guard flip."""
        cfg = self._cfg(
            [
                {"target": "done", "guard": "enough"},
                {"target": "loop", "actions": ["inc"]},
            ],
            entry=None,
        )
        create_machine(cfg, logic=self._logic())  # must not raise

    def test_always_targeting_other_state_is_not_flagged(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"always": "b"}, "b": {}},
        }
        i = SyncInterpreter(create_machine(cfg)).start()
        self.assertEqual(i.current_state_ids, {"m.b"})

    def test_internal_false_is_honoured_as_reenter(self) -> None:
        """The XState v4 spelling is an alias, not silently dropped."""
        cfg = self._cfg(
            [
                {"target": "done", "guard": "enough"},
                {"target": "loop", "internal": False},
            ]
        )
        i = SyncInterpreter(create_machine(cfg, logic=self._logic())).start()
        self.assertEqual(i.current_state_ids, {"m.done"})
        self.assertEqual(i.context["n"], 3)

    def test_explicit_self_target_does_not_reenter(self) -> None:
        """Unchanged XState v5 semantics: no reenter => entry does not re-run."""
        log = []
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"entry": "log", "on": {"E": {"target": "a"}}}},
        }
        logic = MachineLogic(
            actions={"log": lambda i, c, e, a: log.append("entry")}
        )
        i = SyncInterpreter(create_machine(cfg, logic=logic)).start()
        i.send("E")
        self.assertEqual(log, ["entry"])  # once, on start only


class TestRelativeChildTargets(_Quiet):
    """#31: `.child` resolves into the SOURCE's descendants, per XState v5."""

    CONFIG: Dict[str, Any] = {
        "id": "m",
        "initial": "A",
        "states": {
            "A": {
                "initial": "A1",
                "on": {"GO": {"target": ".A2"}},
                "states": {"A1": {"exit": "xA1"}, "A2": {"entry": "eA2"}},
            }
        },
    }

    def test_dot_child_enters_the_child(self) -> None:
        log = []
        logic = MachineLogic(
            actions={
                n: (lambda i, c, e, a, n=n: log.append(n))
                for n in ("xA1", "eA2")
            }
        )
        i = SyncInterpreter(create_machine(self.CONFIG, logic=logic)).start()
        i.send("GO")
        self.assertEqual(i.current_state_ids, {"m.A.A2"})
        self.assertEqual(log, ["xA1", "eA2"])

    def test_sibling_reading_still_works_as_fallback(self) -> None:
        """0.7.x machines that used `.sibling` from a leaf keep working."""
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"on": {"GO": ".b"}}, "b": {}},
        }
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            i = SyncInterpreter(create_machine(cfg)).start()
        i.send("GO")
        self.assertEqual(i.current_state_ids, {"m.b"})

    def test_sibling_fallback_emits_deprecation_warning(self) -> None:
        """#31 acceptance criterion 2: the fallback is observable and
        names the unambiguous spelling."""
        from src.xstate_statemachine import resolver

        resolver._SIBLING_FALLBACKS_WARNED.clear()
        cfg = {
            "id": "m31",
            "initial": "a",
            "states": {"a": {"on": {"GO": ".b"}}, "b": {}},
        }
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            create_machine(cfg)
        msgs = [
            str(w.message)
            for w in caught
            if w.category is DeprecationWarning and "SIBLING" in str(w.message)
        ]
        self.assertEqual(len(msgs), 1, caught)
        self.assertIn("'.b'", msgs[0])
        self.assertIn("'#m31.b'", msgs[0])
        self.assertIn("strictTargets", msgs[0])

    def test_child_reading_does_not_warn(self) -> None:
        cfg = {
            "id": "m",
            "initial": "A",
            "states": {
                "A": {
                    "initial": "A1",
                    "states": {"A1": {}, "A2": {}},
                    "on": {"GO": ".A2"},
                }
            },
        }
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            create_machine(cfg)
        self.assertFalse(
            [w for w in caught if "SIBLING" in str(w.message)], caught
        )

    def test_strict_targets_config_disables_sibling_fallback(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "strictTargets": True,
            "states": {"a": {"on": {"GO": ".b"}}, "b": {}},
        }
        with self.assertRaises(InvalidConfigError):
            create_machine(cfg)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
