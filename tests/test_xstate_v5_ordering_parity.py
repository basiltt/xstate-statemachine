# /tests/test_xstate_v5_ordering_parity.py
# -----------------------------------------------------------------------------
# 🧪 Test Suite: XState v5 microstep parity (entry/exit order and friends)
# -----------------------------------------------------------------------------
# One class per behaviour where the engine used to disagree with XState v5.
# Every expected trace below was recorded from xstate 5.33.3 (the conformance
# cases shared with the Rust engine, `conformance/cases/*.json` in
# xstate-statemachine-rs). These tests are self-contained so they run in CI
# without the sibling checkout `test_xstate_conformance_cases.py` needs.
#
# Both engines run every scenario: the algorithm lives in `BaseInterpreter`,
# so a divergence between them would itself be a bug.
# -----------------------------------------------------------------------------
"""XState v5 parity of the microstep: ordering, domains, completion."""

import asyncio
import json
import logging
import unittest
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from src.xstate_statemachine import (
    Interpreter,
    SyncInterpreter,
    create_machine,
    initial_transition,
    pure_transition,
)
from src.xstate_statemachine.testing_utils import stub_logic

Step = Union[str, Dict[str, Any]]


def _run_sync(
    config: Dict[str, Any], steps: Sequence[Step], **stub: Any
) -> Tuple[List[List[str]], SyncInterpreter]:
    """Start *config* on the sync engine; return the actions of each step."""
    ran: List[str] = []
    machine = create_machine(config, logic=stub_logic(config, ran=ran, **stub))
    interp = SyncInterpreter(machine).start()
    trace = [ran[:]]
    for step in steps:
        del ran[:]
        interp.send(step)
        trace.append(ran[:])
    return trace, interp


def _run_async(
    config: Dict[str, Any], steps: Sequence[Step], **stub: Any
) -> Tuple[List[List[str]], Dict[str, Any]]:
    """Same as `_run_sync` on the asyncio engine; returns a final summary."""

    async def main() -> Tuple[List[List[str]], Dict[str, Any]]:
        ran: List[str] = []
        machine = create_machine(
            config, logic=stub_logic(config, ran=ran, **stub)
        )
        interp = Interpreter(machine)
        await interp.start()
        await interp.await_settled(2.0)
        trace = [ran[:]]
        for step in steps:
            del ran[:]
            await interp.send(step, wait=True)
            await interp.await_settled(2.0)
            trace.append(ran[:])
        summary = {
            "state_ids": sorted(interp.current_state_ids),
            "status": interp.status,
        }
        if interp.status == "running":
            await interp.stop()
        return trace, summary

    return asyncio.run(main())


class _Parity(unittest.TestCase):
    """Runs a scenario on both engines and compares with the XState trace."""

    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

    def check(
        self,
        config: Dict[str, Any],
        steps: Sequence[Step],
        expected: List[List[str]],
        *,
        state_ids: Sequence[str],
        status: str = "running",
        **stub: Any,
    ) -> None:
        trace, interp = _run_sync(config, steps, **stub)
        with self.subTest(engine="sync"):
            self.assertEqual(expected, trace)
            self.assertEqual(
                sorted(state_ids), sorted(interp.current_state_ids)
            )
            self.assertEqual(status, interp.status)
        trace, summary = _run_async(config, steps, **stub)
        with self.subTest(engine="async"):
            self.assertEqual(expected, trace)
            self.assertEqual(sorted(state_ids), summary["state_ids"])
            self.assertEqual(status, summary["status"])


class TestExitOrderIsReverseDocumentOrder(_Parity):
    """Exit set: reverse document order, region by region (SCXML exitStates)."""

    CONFIG = {
        "id": "m",
        "initial": "p",
        "states": {
            "p": {
                "type": "parallel",
                "on": {"STOP": "done"},
                "states": {
                    "zeta": {
                        "initial": "z1",
                        "entry": "e_zeta",
                        "exit": "x_zeta",
                        "states": {"z1": {"entry": "e_z1", "exit": "x_z1"}},
                    },
                    "alpha": {
                        "initial": "a1",
                        "entry": "e_alpha",
                        "exit": "x_alpha",
                        "states": {"a1": {"entry": "e_a1", "exit": "x_a1"}},
                    },
                },
            },
            "done": {"type": "final"},
        },
    }

    def test_regions_exit_whole_and_last_declared_first(self) -> None:
        self.check(
            self.CONFIG,
            ["STOP"],
            [
                ["e_zeta", "e_z1", "e_alpha", "e_a1"],
                ["x_a1", "x_alpha", "x_z1", "x_zeta"],
            ],
            state_ids=["m.done"],
            status="done",
        )

    def test_order_does_not_depend_on_state_names(self) -> None:
        """Swapping the declaration order swaps the exit order -- the ids'
        spelling no longer decides it."""
        states = self.CONFIG["states"]["p"]["states"]  # type: ignore[index]
        swapped = {
            **self.CONFIG,
            "states": {
                **self.CONFIG["states"],  # type: ignore[dict-item]
                "p": {
                    **self.CONFIG["states"]["p"],  # type: ignore[index]
                    "states": {
                        "alpha": states["alpha"],
                        "zeta": states["zeta"],
                    },
                },
            },
        }
        trace, _ = _run_sync(swapped, ["STOP"])
        self.assertEqual(["x_z1", "x_zeta", "x_a1", "x_alpha"], trace[1])


class TestParallelEntryIsDocumentOrder(_Parity):
    """Entry set: document order; the targeted region is not entered last."""

    CONFIG = {
        "id": "m",
        "initial": "idle",
        "states": {
            "idle": {"on": {"GO": "#m.p.first.f2"}},
            "p": {
                "type": "parallel",
                "entry": "e_p",
                "states": {
                    "first": {
                        "initial": "f1",
                        "entry": "e_first",
                        "states": {
                            "f1": {"entry": "e_f1"},
                            "f2": {"entry": "e_f2"},
                        },
                    },
                    "second": {
                        "initial": "s1",
                        "entry": "e_second",
                        "states": {"s1": {"entry": "e_s1"}},
                    },
                },
            },
        },
    }

    def test_targeted_region_is_entered_in_declaration_order(self) -> None:
        self.check(
            self.CONFIG,
            ["GO"],
            [[], ["e_p", "e_first", "e_f2", "e_second", "e_s1"]],
            state_ids=["m.p.first.f2", "m.p.second.s1"],
        )


class TestCrossRegionTargetHasParallelDomain(_Parity):
    """A target in a sibling region: the parallel state is the domain."""

    CONFIG = {
        "id": "m",
        "initial": "p",
        "states": {
            "p": {
                "type": "parallel",
                "entry": "e_p",
                "exit": "x_p",
                "states": {
                    "r1": {
                        "initial": "a",
                        "entry": "e_r1",
                        "exit": "x_r1",
                        "states": {
                            "a": {
                                "entry": "e_a",
                                "exit": "x_a",
                                "on": {"E": "#m.p.r2.d"},
                            }
                        },
                    },
                    "r2": {
                        "initial": "c",
                        "entry": "e_r2",
                        "exit": "x_r2",
                        "states": {
                            "c": {"entry": "e_c", "exit": "x_c"},
                            "d": {"entry": "e_d", "exit": "x_d"},
                        },
                    },
                },
            }
        },
    }

    def test_both_regions_exit_and_reenter_but_not_the_parallel(self) -> None:
        self.check(
            self.CONFIG,
            ["E"],
            [
                ["e_p", "e_r1", "e_a", "e_r2", "e_c"],
                ["x_c", "x_r2", "x_a", "x_r1", "e_r1", "e_a", "e_r2", "e_d"],
            ],
            state_ids=["m.p.r1.a", "m.p.r2.d"],
        )


class TestReenterHasDomainAboveTheSource(_Parity):
    """reenter: true -- the source exits and re-enters before its child."""

    CONFIG = {
        "id": "m",
        "initial": "p",
        "states": {
            "p": {
                "initial": "a",
                "entry": "e_p",
                "exit": "x_p",
                "on": {
                    "SOFT": {"target": ".b", "actions": "soft"},
                    "HARD": {
                        "target": ".a",
                        "reenter": True,
                        "actions": "hard",
                    },
                },
                "states": {
                    "a": {"entry": "e_a", "exit": "x_a"},
                    "b": {"entry": "e_b", "exit": "x_b"},
                },
            }
        },
    }

    def test_descendant_target_reenters_the_source(self) -> None:
        self.check(
            self.CONFIG,
            ["SOFT", "HARD"],
            [
                ["e_p", "e_a"],
                ["x_a", "soft", "e_b"],
                ["x_b", "x_p", "hard", "e_p", "e_a"],
            ],
            state_ids=["m.p.a"],
        )

    def test_reentering_root_transition_reenters_the_root(self) -> None:
        """XState: a re-entering transition on the root exits and enters
        the root itself; a plain one does not."""
        config = {
            "id": "m",
            "initial": "a",
            "entry": "e_root",
            "exit": "x_root",
            "on": {
                "R": {"target": ".b", "reenter": True, "actions": "t"},
                "S": {"target": ".b", "actions": "s"},
            },
            "states": {
                "a": {"entry": "e_a", "exit": "x_a"},
                "b": {"entry": "e_b", "exit": "x_b"},
            },
        }
        self.check(
            config,
            ["R", "S"],
            [
                ["e_root", "e_a"],
                ["x_a", "x_root", "t", "e_root", "e_b"],
                ["x_b", "s", "e_b"],
            ],
            state_ids=["m.b"],
        )


class TestExitActionsRunOnCompletion(_Parity):
    """Reaching a top-level final state runs every remaining exit action."""

    CONFIG = {
        "id": "m",
        "initial": "a",
        "exit": "x_root",
        "states": {
            "a": {"exit": "x_a", "on": {"END": "done"}},
            "done": {"type": "final", "entry": "e_done", "exit": "x_done"},
        },
    }

    def test_final_state_and_root_exit_after_entry(self) -> None:
        self.check(
            self.CONFIG,
            ["END"],
            [[], ["x_a", "e_done", "x_done", "x_root"]],
            state_ids=["m.done"],
            status="done",
        )

    def test_starting_in_a_final_state_also_exits(self) -> None:
        """xstate 5.33.3: e_root, e_done, x_done, x_root at start."""
        config = {
            "id": "m",
            "initial": "done",
            "entry": "e_root",
            "exit": "x_root",
            "states": {
                "done": {"type": "final", "entry": "e_done", "exit": "x_done"}
            },
        }
        self.check(
            config,
            [],
            [["e_root", "e_done", "x_done", "x_root"]],
            state_ids=["m.done"],
            status="done",
        )

    def test_output_is_resolved_before_the_exit_actions(self) -> None:
        config = {
            "id": "m",
            "initial": "a",
            "context": {"n": 1},
            "output": lambda args: args["context"]["n"],
            "exit": {
                "type": "xstate.assign",
                "params": {"assignment": {"n": 99}},
            },
            "states": {
                "a": {"on": {"END": "done"}},
                "done": {"type": "final"},
            },
        }
        _, interp = _run_sync(config, ["END"])
        self.assertEqual("done", interp.status)
        self.assertEqual(1, interp.output)
        self.assertEqual({"n": 99}, interp.context)


class TestWildcardMatchesEngineEvents(_Parity):
    """`*` / `prefix.*` receive engine events (XState `getCandidates`)."""

    CONFIG = {
        "id": "w",
        "initial": "a",
        "states": {
            "a": {
                "invoke": {"src": "ok", "id": "ok"},
                "on": {"*": {"actions": "starA"}, "NEXT": "b"},
            },
            "b": {
                "invoke": {"src": "boom", "id": "boom"},
                "on": {"*": {"actions": "starB"}},
            },
        },
    }

    @staticmethod
    def _logic(ran: List[str]) -> Any:
        logic = stub_logic(
            TestWildcardMatchesEngineEvents.CONFIG,
            ran=ran,
            service_results={"ok": 1},
        )

        def boom(*_args: Any, **_kw: Any) -> Any:
            raise RuntimeError("kaboom")

        logic.services["boom"] = boom  # type: ignore[index]
        return logic

    def test_done_and_error_reach_the_wildcard_on_both_engines(self) -> None:
        # Sync engine.
        ran: List[str] = []
        machine = create_machine(self.CONFIG, logic=self._logic(ran))
        interp = SyncInterpreter(machine).start()
        self.assertEqual(["starA"], ran)  # done.invoke.ok
        del ran[:]
        interp.send("NEXT")
        self.assertEqual(["starB"], ran)  # error.platform.boom
        self.assertEqual("running", interp.status)
        self.assertEqual({"w.b"}, interp.current_state_ids)
        del ran[:]
        interp.send("PING")
        self.assertEqual(["starB"], ran)

        # Async engine.
        async def main() -> None:
            ran2: List[str] = []
            m2 = create_machine(self.CONFIG, logic=self._logic(ran2))
            i2 = Interpreter(m2)
            await i2.start()
            await i2.await_settled(2.0)
            self.assertEqual(["starA"], ran2)
            del ran2[:]
            await i2.send("NEXT", wait=True)
            await i2.await_settled(2.0)
            self.assertEqual(["starB"], ran2)
            self.assertEqual("running", i2.status)
            await i2.stop()

        asyncio.run(main())

    def test_partial_descriptor_catches_a_service_failure(self) -> None:
        config = {
            "id": "w",
            "initial": "b",
            "states": {
                "b": {
                    "invoke": {"src": "boom", "id": "boom"},
                    "on": {"error.platform.*": "failed"},
                },
                "failed": {},
            },
        }
        logic = stub_logic(config)

        def boom(*_args: Any, **_kw: Any) -> Any:
            raise RuntimeError("kaboom")

        logic.services["boom"] = boom  # type: ignore[index]
        interp = SyncInterpreter(create_machine(config, logic=logic)).start()
        self.assertEqual("running", interp.status)
        self.assertEqual({"w.failed"}, interp.current_state_ids)

    def test_own_on_done_still_outranks_the_wildcard(self) -> None:
        config = {
            "id": "m",
            "initial": "l",
            "states": {
                "l": {
                    "invoke": {"src": "s", "id": "s", "onDone": "ok"},
                    "on": {"*": "wild"},
                },
                "ok": {},
                "wild": {},
            },
        }
        _, interp = _run_sync(config, [])
        self.assertEqual({"m.ok"}, interp.current_state_ids)

    def test_deeper_wildcard_outranks_an_ancestor_handler(self) -> None:
        """As in XState: the deepest matching state wins, `*` included."""
        config = {
            "id": "m",
            "initial": "p",
            "states": {
                "p": {
                    "invoke": {"src": "s", "id": "s", "onDone": "#m.ok"},
                    "initial": "c",
                    "states": {"c": {"on": {"*": {"actions": "star"}}}},
                },
                "ok": {},
            },
        }
        trace, interp = _run_sync(config, [])
        self.assertEqual([["star"]], trace)
        self.assertEqual({"m.p.c"}, interp.current_state_ids)


class TestMultiTargetParallelEntry(_Parity):
    """`target: [a, b]` in different regions of one parallel state."""

    CONFIG = {
        "id": "m",
        "initial": "idle",
        "states": {
            "idle": {"on": {"GO": {"target": ["#m.p.r1.x", "#m.p.r2.y"]}}},
            "p": {
                "type": "parallel",
                "states": {
                    "r1": {
                        "initial": "a",
                        "states": {
                            "a": {"entry": "e_a"},
                            "x": {"entry": "e_x"},
                        },
                    },
                    "r2": {
                        "initial": "c",
                        "states": {
                            "c": {"entry": "e_c"},
                            "y": {"entry": "e_y"},
                        },
                    },
                },
            },
        },
    }

    def test_both_targets_replace_the_initial_states(self) -> None:
        self.check(
            self.CONFIG,
            ["GO"],
            [[], ["e_x", "e_y"]],
            state_ids=["m.p.r1.x", "m.p.r2.y"],
        )

    def test_single_element_list_is_a_plain_target(self) -> None:
        config = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"on": {"GO": {"target": ["b"]}}}, "b": {}},
        }
        _, interp = _run_sync(config, ["GO"])
        self.assertEqual({"m.b"}, interp.current_state_ids)

    def test_hash_of_a_multi_target_transition_uses_the_first_target(
        self,
    ) -> None:
        """The structure hash renders a transition's FIRST target, as the
        Rust engine's `machine_hash` does (cross-language fixtures)."""
        from src.xstate_statemachine.persistence.snapshot import (
            structure_hash,
        )

        def chart(target: Any) -> Dict[str, Any]:
            cfg = json.loads(json.dumps(self.CONFIG))
            cfg["states"]["idle"]["on"]["GO"]["target"] = target
            return cfg

        multi_cfg = chart(["#m.p.r1.x", "#m.p.r2.y"])
        multi = create_machine(multi_cfg, logic=stub_logic(multi_cfg))
        single_cfg = chart("#m.p.r1.x")
        single = create_machine(single_cfg, logic=stub_logic(single_cfg))
        self.assertEqual(structure_hash(single), structure_hash(multi))

    def test_incompatible_target_shapes_are_rejected(self) -> None:
        from src.xstate_statemachine import InvalidConfigError

        def chart(targets: List[str]) -> Dict[str, Any]:
            cfg = json.loads(json.dumps(self.CONFIG))
            cfg["states"]["idle"]["on"]["GO"]["target"] = targets
            return cfg

        bad = [
            ["#m.p.r1.a", "#m.p.r1.x"],  # one compound region
            ["#m.p.r1", "#m.p.r1.x"],  # a target and its descendant
            ["#m.p.r1.x", "#m.p.r1.x"],  # the same state twice
            ["#m.idle", "#m.p.r1.x"],  # not under one parallel state
            [],  # empty
        ]
        for targets in bad:
            with self.subTest(targets=targets):
                with self.assertRaises(InvalidConfigError):
                    cfg = chart(targets)
                    create_machine(cfg, logic=stub_logic(cfg))
        with self.assertRaises(InvalidConfigError):
            create_machine(chart(["#m.p.r1.x", 7]))  # type: ignore[list-item]


class TestJsonChooseWithCompositeGuards(_Parity):
    """JSON `choose` (`params.branches`) with `and`/`or`/`not`/`stateIn`."""

    CONFIG = {
        "id": "m",
        "initial": "p",
        "states": {
            "p": {
                "type": "parallel",
                "states": {
                    "mode": {
                        "initial": "day",
                        "states": {
                            "day": {"on": {"NIGHT": "night"}},
                            "night": {},
                        },
                    },
                    "work": {
                        "initial": "idle",
                        "states": {
                            "idle": {
                                "on": {
                                    "PING": {
                                        "actions": [
                                            {
                                                "type": "choose",
                                                "params": {
                                                    "branches": [
                                                        {
                                                            "guard": {
                                                                "type": "stateIn",
                                                                "params": {
                                                                    "stateValue": "#m.p.mode.night"
                                                                },
                                                            },
                                                            "actions": "atNight",
                                                        },
                                                        {
                                                            "guard": {
                                                                "type": "and",
                                                                "params": {
                                                                    "guards": [
                                                                        "isAdmin",
                                                                        {
                                                                            "type": "not",
                                                                            "params": {
                                                                                "guard": "isBanned"
                                                                            },
                                                                        },
                                                                    ]
                                                                },
                                                            },
                                                            "actions": "adminByDay",
                                                        },
                                                        {
                                                            "actions": "otherwise"
                                                        },
                                                    ]
                                                },
                                            }
                                        ]
                                    },
                                    "LOCK": {
                                        "target": "locked",
                                        "guard": {
                                            "type": "or",
                                            "params": {
                                                "guards": [
                                                    "isAdmin",
                                                    "isBanned",
                                                ]
                                            },
                                        },
                                    },
                                }
                            },
                            "locked": {},
                        },
                    },
                },
            }
        },
    }

    def test_first_matching_branch_runs(self) -> None:
        self.check(
            self.CONFIG,
            ["PING", "NIGHT", "PING", "LOCK"],
            [[], ["adminByDay"], [], ["atNight"], []],
            state_ids=["m.p.mode.night", "m.p.work.locked"],
            guards={"isAdmin": True, "isBanned": False},
        )

    def test_fallback_branch_without_guard(self) -> None:
        trace, _ = _run_sync(
            self.CONFIG, ["PING"], guards={"isAdmin": False, "isBanned": False}
        )
        self.assertEqual(["otherwise"], trace[1])

    def test_stub_logic_sees_branch_actions_and_guards(self) -> None:
        from src.xstate_statemachine.testing_utils import logic_names

        actions, guards, _ = logic_names(
            create_machine(self.CONFIG, logic=stub_logic(self.CONFIG))
        )
        self.assertLessEqual({"atNight", "adminByDay", "otherwise"}, actions)
        self.assertLessEqual({"isAdmin", "isBanned"}, guards)

    def test_python_choose_helper_still_uses_conditions(self) -> None:
        from src.xstate_statemachine import choose

        config = {
            "id": "c",
            "initial": "a",
            "states": {
                "a": {
                    "on": {
                        "GO": {
                            "actions": [
                                choose(
                                    [
                                        {"guard": "no", "actions": "first"},
                                        {"actions": ["second"]},
                                    ]
                                )
                            ]
                        }
                    }
                }
            },
        }
        trace, _ = _run_sync(config, ["GO"], guards={"no": False})
        self.assertEqual(["second"], trace[1])


class TestConflictingTransitionsShareOneMicrostep(_Parity):
    """removeConflictingTransitions + exit → actions → entry per microstep.

    Cases `038_conflict_document_order_preemption`,
    `039_microstep_groups_exit_actions_entry` and
    `040_eventless_descendant_preempts_ancestor`.
    """

    PREEMPT = {
        "id": "m",
        "initial": "p",
        "states": {
            "p": {
                "type": "parallel",
                "states": {
                    "r1": {
                        "initial": "a",
                        "states": {
                            "a": {
                                "entry": "e_a",
                                "exit": "x_a",
                                "on": {
                                    "E": {
                                        "target": "#m.p.r2.x",
                                        "actions": "t1",
                                    }
                                },
                            }
                        },
                    },
                    "r2": {
                        "initial": "x",
                        "states": {
                            "x": {
                                "entry": "e_x",
                                "exit": "x_x",
                                "on": {"E": {"target": "y", "actions": "t2"}},
                            },
                            "y": {"entry": "e_y"},
                        },
                    },
                },
            }
        },
    }

    GROUPED = {
        "id": "m",
        "initial": "p",
        "states": {
            "p": {
                "type": "parallel",
                "on": {"E": {"target": "#m.out", "actions": "tp"}},
                "states": {
                    "r1": {
                        "initial": "a",
                        "states": {
                            "a": {
                                "exit": "x_a",
                                "on": {"E": {"target": "b", "actions": "ta"}},
                            },
                            "b": {"entry": "e_b"},
                        },
                    },
                    "r2": {"initial": "c", "states": {"c": {"exit": "x_c"}}},
                    "r3": {
                        "initial": "d",
                        "states": {
                            "d": {
                                "exit": "x_d",
                                "on": {"E": {"target": "f", "actions": "td"}},
                            },
                            "f": {"entry": "e_f"},
                        },
                    },
                },
            },
            "out": {"entry": "e_out"},
        },
    }

    EVENTLESS = {
        "id": "m",
        "initial": "p",
        "states": {
            "p": {
                "type": "parallel",
                "always": {
                    "target": "#m.out",
                    "guard": {
                        "type": "stateIn",
                        "params": {"stateValue": "#m.p.r2.c"},
                    },
                    "actions": "tp",
                },
                "states": {
                    "r1": {"initial": "a", "states": {"a": {}}},
                    "r2": {
                        "initial": "b",
                        "states": {
                            "b": {"on": {"GO": "c"}},
                            "c": {
                                "exit": "x_c",
                                "always": {"target": "d", "actions": "tc"},
                            },
                            "d": {"entry": "e_d"},
                        },
                    },
                },
            },
            "out": {"entry": "e_out"},
        },
    }

    def test_first_selected_wins_a_conflict_in_document_order(self) -> None:
        # r1's transition exits (and re-enters) r2's source: r2's
        # transition is preempted instead of running on the re-entered x.
        self.check(
            self.PREEMPT,
            ["E"],
            [["e_a", "e_x"], ["x_x", "x_a", "t1", "e_a", "e_x"]],
            state_ids=["m.p.r1.a", "m.p.r2.x"],
        )

    def test_exits_then_actions_then_entries(self) -> None:
        # p's own handler loses to the regions; the two region transitions
        # are one microstep, not two interleaved ones.
        self.check(
            self.GROUPED,
            ["E"],
            [[], ["x_d", "x_a", "ta", "td", "e_b", "e_f"]],
            state_ids=["m.p.r1.b", "m.p.r2.c", "m.p.r3.f"],
        )

    def test_descendant_eventless_transition_preempts_the_ancestor(
        self,
    ) -> None:
        self.check(
            self.EVENTLESS,
            ["GO"],
            [[], ["x_c", "tc", "e_d"]],
            state_ids=["m.p.r1.a", "m.p.r2.d"],
        )

    def test_rollback_restores_every_region_of_the_microstep(self) -> None:
        def boom(*_: Any) -> None:
            raise RuntimeError("boom")

        config = json.loads(json.dumps(self.GROUPED))
        config["actionErrorPolicy"] = "rollback"
        ran: List[str] = []
        logic = stub_logic(config, ran=ran)
        logic.actions["td"] = boom
        interp = SyncInterpreter(create_machine(config, logic=logic)).start()
        interp.send("E")
        # td failed after both regions had exited: the whole microstep is
        # undone, not only r3's half of it.
        self.assertEqual(["x_d", "x_a", "ta"], ran)
        self.assertEqual(
            {"m.p.r1.a", "m.p.r2.c", "m.p.r3.d"}, interp.current_state_ids
        )
        self.assertFalse(interp.last_transition_ok)

    def test_plugins_see_every_transition_of_the_microstep(self) -> None:
        from src.xstate_statemachine import PluginBase

        seen: List[Tuple[str, List[str]]] = []

        class Spy(PluginBase[Any]):
            def on_transition(
                self,
                interpreter: Any,
                from_states: Any,
                to_states: Any,
                transition: Any,
            ) -> None:
                seen.append(
                    (
                        transition.source.id,
                        sorted(s.id for s in to_states if not s.states),
                    )
                )

        logic = stub_logic(self.GROUPED)
        interp = SyncInterpreter(create_machine(self.GROUPED, logic=logic))
        interp.use(Spy())
        interp.start()
        del seen[:]  # the initial transition
        interp.send("E")
        after = ["m.p.r1.b", "m.p.r2.c", "m.p.r3.f"]
        self.assertEqual([("m.p.r1.a", after), ("m.p.r3.d", after)], seen)


class TestDoneStateIsAnInternalEvent(unittest.TestCase):
    """`done.state.*` goes to the internal queue (XState `internalQueue`).

    Case `041_done_state_before_queued_external_event`: with FINISH and
    NEXT queued together, the `onDone` transition is taken before NEXT.
    """

    CONFIG = {
        "id": "m",
        "initial": "work",
        "states": {
            "work": {
                "initial": "step",
                "onDone": {"target": "after", "actions": "onDoneTaken"},
                "on": {"NEXT": {"actions": "nextInWork"}},
                "states": {
                    "step": {"on": {"FINISH": "end"}},
                    "end": {"type": "final", "entry": "enterEnd"},
                },
            },
            "after": {"on": {"NEXT": {"actions": "nextInAfter"}}},
        },
    }

    EXPECTED = ["enterEnd", "onDoneTaken", "nextInAfter"]

    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

    def test_sync_batch_runs_on_done_before_the_queued_event(self) -> None:
        ran: List[str] = []
        logic = stub_logic(self.CONFIG, ran=ran)
        interp = SyncInterpreter(create_machine(self.CONFIG, logic=logic))
        interp.start()
        interp.send_events(["FINISH", "NEXT"])
        self.assertEqual(self.EXPECTED, ran)
        self.assertEqual({"m.after"}, interp.current_state_ids)

    def test_async_queued_sends_run_on_done_first(self) -> None:
        async def main() -> Tuple[List[str], Any]:
            ran: List[str] = []
            logic = stub_logic(self.CONFIG, ran=ran)
            interp = Interpreter(create_machine(self.CONFIG, logic=logic))
            await interp.start()
            # Both land in the inbox before the run loop takes either.
            interp.send("FINISH")
            await interp.send("NEXT", wait=True)
            await interp.await_settled(2.0)
            ids = set(interp.current_state_ids)
            await interp.stop()
            return ran, ids

        ran, ids = asyncio.run(main())
        self.assertEqual(self.EXPECTED, ran)
        self.assertEqual({"m.after"}, ids)

    def test_rollback_withdraws_the_done_event_it_queued(self) -> None:
        def boom(*_: Any) -> None:
            raise RuntimeError("boom")

        config = json.loads(json.dumps(self.CONFIG))
        config["actionErrorPolicy"] = "rollback"
        config["states"]["work"]["states"]["step"]["on"]["FINISH"] = {
            "target": "end",
            "actions": "explode",
        }
        config["states"]["work"]["states"]["end"]["entry"] = [
            "enterEnd",
            "explodeLater",
        ]
        ran: List[str] = []
        logic = stub_logic(config, ran=ran)
        logic.actions["explodeLater"] = boom
        interp = SyncInterpreter(create_machine(config, logic=logic)).start()
        interp.send("FINISH")
        # The entry action failed: the step is undone and the done event
        # the final state queued is withdrawn with it.
        self.assertEqual({"m.work.step"}, interp.current_state_ids)
        self.assertNotIn("onDoneTaken", ran)


class TestGuardEvaluationOrder(unittest.TestCase):
    """XState `selectTransitions` / `selectEventlessTransitions` guard order.

    Case `042_guard_evaluation_order` (`logic.record_guards`): per region
    the deepest state's candidates are tried in order and evaluation stops
    at the first enabled one; a region's own handlers are consulted only
    when its active child had none, the parallel ancestor only when no
    region matched; every active leaf walks up to its first enabled
    `always`, so a shared ancestor's `always` guard runs once per region.
    """

    CONFIG = {
        "id": "m",
        "initial": "p",
        "states": {
            "p": {
                "type": "parallel",
                "always": {"target": "#m.out", "guard": "gAlways"},
                "on": {
                    "E": {"actions": "pTook", "guard": "gP"},
                    "F": {"actions": "pF", "guard": "gPF"},
                },
                "states": {
                    "r1": {
                        "initial": "a",
                        "on": {"E": {"actions": "r1Took", "guard": "gR1"}},
                        "states": {
                            "a": {
                                "on": {
                                    "E": [
                                        {
                                            "target": "b",
                                            "guard": "gA1",
                                            "actions": "a1",
                                        },
                                        {"guard": "gA2", "actions": "a2"},
                                        {"guard": "gA3", "actions": "a3"},
                                    ]
                                }
                            },
                            "b": {},
                        },
                    },
                    "r2": {
                        "initial": "c",
                        "states": {
                            "c": {
                                "on": {
                                    "E": {"guard": "gC", "actions": "cTook"},
                                    "F": {"guard": "gCF", "actions": "cF"},
                                }
                            }
                        },
                    },
                },
            },
            "out": {},
        },
    }

    GUARDS = {
        "gAlways": False,
        "gA1": False,
        "gA2": True,
        "gC": False,
        "gCF": False,
    }

    #: (actions, guards) after start() and after E, F, G -- xstate 5.33.3.
    EXPECTED = [
        ([], ["gAlways", "gAlways"]),
        (["a2"], ["gA1", "gA2", "gC", "gAlways", "gAlways"]),
        (["pF"], ["gCF", "gPF", "gAlways", "gAlways"]),
        ([], ["gAlways", "gAlways"]),
    ]

    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

    def test_sync_engine(self) -> None:
        ran: List[str] = []
        log: List[str] = []
        logic = stub_logic(
            self.CONFIG, ran=ran, guards=self.GUARDS, guard_log=log
        )
        interp = SyncInterpreter(create_machine(self.CONFIG, logic=logic))
        interp.start()
        trace = [(ran[:], log[:])]
        for event in ("E", "F", "G"):
            del ran[:], log[:]
            interp.send(event)
            trace.append((ran[:], log[:]))
        self.assertEqual(self.EXPECTED, trace)

    def test_async_engine(self) -> None:
        async def main() -> List[Tuple[List[str], List[str]]]:
            ran: List[str] = []
            log: List[str] = []
            logic = stub_logic(
                self.CONFIG, ran=ran, guards=self.GUARDS, guard_log=log
            )
            interp = Interpreter(create_machine(self.CONFIG, logic=logic))
            await interp.start()
            await interp.await_settled(2.0)
            trace = [(ran[:], log[:])]
            for event in ("E", "F", "G"):
                del ran[:], log[:]
                await interp.send(event, wait=True)
                await interp.await_settled(2.0)
                trace.append((ran[:], log[:]))
            await interp.stop()
            return trace

        self.assertEqual(self.EXPECTED, asyncio.run(main()))

    def test_ancestor_handler_is_not_taken_beside_a_region(self) -> None:
        # p's targetless handler does not conflict with anything, so only
        # selection keeps it out: a region handled E.
        trace, interp = _run_sync(self.CONFIG, ["E"], guards=self.GUARDS)
        self.assertNotIn("pTook", trace[1])
        self.assertNotIn("r1Took", trace[1])

    def test_can_evaluates_like_a_send(self) -> None:
        log: List[str] = []
        logic = stub_logic(self.CONFIG, guards=self.GUARDS, guard_log=log)
        interp = SyncInterpreter(create_machine(self.CONFIG, logic=logic))
        interp.start()
        del log[:]
        self.assertTrue(interp.can("E"))
        self.assertEqual(["gA1", "gA2", "gC"], log)


class TestAssignComputesAgainstThePriorContext(unittest.TestCase):
    """One `assign` computes every property against the context BEFORE it.

    XState v5 `assign({a: ({context}) => context.b, b: 1})` gives `a` the
    OLD `b`: all properties are resolved first, then merged. Consecutive
    assigns still see each other's writes (case
    `043_assign_actions_apply_in_order`).
    """

    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

    @staticmethod
    def _config(*actions: Any) -> Dict[str, Any]:
        return {
            "id": "m",
            "initial": "a",
            "context": {"a": 0, "b": 0},
            "states": {"a": {"on": {"GO": {"actions": list(actions)}}}},
        }

    def _run(self, engine: str, *actions: Any) -> Dict[str, Any]:
        config = self._config(*actions)
        machine = create_machine(config, logic=stub_logic(config))
        if engine == "sync":
            interp = SyncInterpreter(machine).start()
            interp.send("GO")
            return dict(interp.context)

        async def main() -> Dict[str, Any]:
            interp = Interpreter(machine)
            await interp.start()
            await interp.send("GO", wait=True)
            ctx = dict(interp.context)
            await interp.stop()
            return ctx

        return asyncio.run(main())

    def test_later_property_does_not_see_an_earlier_one(self) -> None:
        from src.xstate_statemachine import assign

        action = assign(
            {
                "b": 1,
                "a": lambda args: args["context"]["b"] + 10,
            }
        )
        for engine in ("sync", "async"):
            with self.subTest(engine=engine):
                self.assertEqual({"a": 10, "b": 1}, self._run(engine, action))

    def test_properties_swap_without_a_temporary(self) -> None:
        from src.xstate_statemachine import assign

        action = assign(
            {
                "a": lambda args: args["context"]["b"],
                "b": lambda args: args["context"]["a"],
            }
        )
        config = self._config(action)
        config["context"] = {"a": "x", "b": "y"}
        interp = SyncInterpreter(
            create_machine(config, logic=stub_logic(config))
        ).start()
        interp.send("GO")
        self.assertEqual({"a": "y", "b": "x"}, interp.context)

    def test_consecutive_assigns_see_each_other(self) -> None:
        from src.xstate_statemachine import assign

        first = assign({"b": 5})
        second = assign({"a": lambda args: args["context"]["b"] * 2})
        for engine in ("sync", "async"):
            with self.subTest(engine=engine):
                self.assertEqual(
                    {"a": 10, "b": 5}, self._run(engine, first, second)
                )


class TestCompoundSelfTargetWithoutReenter(_Parity):
    """A compound targeting itself (no `reenter`) resets its children.

    Case `044_compound_self_target_without_reenter`: the domain is the
    source, so its active descendants exit and its initial child is
    entered again; the source itself stays (no `x_p` / `e_p`).
    """

    CONFIG = {
        "id": "m",
        "initial": "p",
        "states": {
            "p": {
                "initial": "a",
                "entry": "e_p",
                "exit": "x_p",
                "on": {
                    "RESET": {"target": "p", "actions": "t"},
                    "HARD": {"target": "p", "reenter": True, "actions": "h"},
                },
                "states": {
                    "a": {"entry": "e_a", "exit": "x_a", "on": {"NEXT": "b"}},
                    "b": {"entry": "e_b", "exit": "x_b"},
                },
            }
        },
    }

    def test_children_exit_and_the_initial_child_is_reentered(self) -> None:
        self.check(
            self.CONFIG,
            ["NEXT", "RESET", "NEXT", "HARD"],
            [
                ["e_p", "e_a"],
                ["x_a", "e_b"],
                ["x_b", "t", "e_a"],
                ["x_a", "e_b"],
                ["x_b", "x_p", "h", "e_p", "e_a"],
            ],
            state_ids=["m.p.a"],
        )

    def test_parallel_self_target_resets_every_region(self) -> None:
        config = {
            "id": "m",
            "initial": "p",
            "states": {
                "p": {
                    "type": "parallel",
                    "entry": "e_p",
                    "on": {"RESET": {"target": "p", "actions": "t"}},
                    "states": {
                        "r1": {
                            "initial": "a",
                            "states": {
                                "a": {"entry": "e_a", "on": {"GO": "b"}},
                                "b": {"exit": "x_b"},
                            },
                        },
                        "r2": {
                            "initial": "c",
                            "states": {"c": {"entry": "e_c", "exit": "x_c"}},
                        },
                    },
                }
            },
        }
        self.check(
            config,
            ["GO", "RESET"],
            [["e_p", "e_a", "e_c"], [], ["x_c", "x_b", "t", "e_a", "e_c"]],
            state_ids=["m.p.r1.a", "m.p.r2.c"],
        )

    def test_atomic_self_target_still_runs_only_its_actions(self) -> None:
        config = {
            "id": "s",
            "initial": "a",
            "states": {
                "a": {
                    "entry": "e_a",
                    "exit": "x_a",
                    "on": {"SOFT": {"target": "a", "actions": "soft"}},
                }
            },
        }
        self.check(config, ["SOFT"], [["e_a"], ["soft"]], state_ids=["s.a"])


class TestJsonAssignWithoutAssignmentWrapper(unittest.TestCase):
    """`{"type": "assign", "params": {...}}` assigns `params` itself.

    Case `045_assign_without_assignment_wrapper`; the spelling the Rust
    engine and the XState oracle accept (`params.assignment` when present,
    else `params`).
    """

    CONFIG = {
        "id": "m",
        "initial": "a",
        "context": {"count": 0, "label": "start"},
        "states": {
            "a": {
                "on": {
                    "SET": {
                        "target": "b",
                        "actions": [
                            {
                                "type": "xstate.assign",
                                "params": {"count": 1, "label": "first"},
                            },
                            "between",
                            {"type": "assign", "params": {"label": "second"}},
                        ],
                    }
                }
            },
            "b": {
                "entry": [
                    {
                        "type": "assign",
                        "params": {"assignment": {"count": 2}},
                    },
                    {"type": "assign", "params": {"flag": True}},
                ]
            },
        },
    }

    EXPECTED = {"count": 2, "label": "second", "flag": True}

    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

    def test_both_spellings_on_both_engines(self) -> None:
        trace, interp = _run_sync(self.CONFIG, ["SET"])
        self.assertEqual(self.EXPECTED, interp.context)
        self.assertEqual(["between"], trace[1])

        async def main() -> Dict[str, Any]:
            config = self.CONFIG
            interp = Interpreter(
                create_machine(config, logic=stub_logic(config))
            )
            await interp.start()
            await interp.send("SET", wait=True)
            ctx = dict(interp.context)
            await interp.stop()
            return ctx

        self.assertEqual(self.EXPECTED, asyncio.run(main()))

    def test_bare_params_may_hold_property_functions(self) -> None:
        config = {
            "id": "m",
            "initial": "a",
            "context": {"n": 1},
            "states": {
                "a": {
                    "on": {
                        "GO": {
                            "actions": [
                                {
                                    "type": "assign",
                                    "params": {
                                        "n": lambda args: args["context"]["n"]
                                        + args["event"].payload["by"]
                                    },
                                }
                            ]
                        }
                    }
                }
            },
        }
        interp = SyncInterpreter(
            create_machine(config, logic=stub_logic(config))
        ).start()
        interp.send("GO", by=4)
        self.assertEqual({"n": 5}, interp.context)

    def test_assign_without_params_changes_nothing(self) -> None:
        config = {
            "id": "m",
            "initial": "a",
            "context": {"n": 1},
            "states": {"a": {"on": {"GO": {"actions": [{"type": "assign"}]}}}},
        }
        interp = SyncInterpreter(
            create_machine(config, logic=stub_logic(config))
        ).start()
        interp.send("GO")
        self.assertEqual({"n": 1}, interp.context)


# -----------------------------------------------------------------------------
# 🔢 Guard / action traces on both engines (record_guards cases 046-050)
# -----------------------------------------------------------------------------
Trace = List[Tuple[List[str], List[str]]]


def _guard_trace_sync(
    config: Dict[str, Any],
    steps: Sequence[Step],
    guards: Dict[str, bool],
) -> Tuple[Trace, SyncInterpreter]:
    """``(actions, guards evaluated)`` after start() and every step."""
    ran: List[str] = []
    log: List[str] = []
    logic = stub_logic(config, ran=ran, guards=guards, guard_log=log)
    interp = SyncInterpreter(create_machine(config, logic=logic)).start()
    trace = [(ran[:], log[:])]
    for step in steps:
        del ran[:], log[:]
        interp.send(step)
        trace.append((ran[:], log[:]))
    return trace, interp


def _guard_trace_async(
    config: Dict[str, Any],
    steps: Sequence[Step],
    guards: Dict[str, bool],
) -> Trace:
    """Same as `_guard_trace_sync` on the asyncio engine."""

    async def main() -> Trace:
        ran: List[str] = []
        log: List[str] = []
        logic = stub_logic(config, ran=ran, guards=guards, guard_log=log)
        interp = Interpreter(create_machine(config, logic=logic))
        await interp.start()
        await interp.await_settled(2.0)
        trace = [(ran[:], log[:])]
        for step in steps:
            del ran[:], log[:]
            await interp.send(step, wait=True)
            await interp.await_settled(2.0)
            trace.append((ran[:], log[:]))
        if interp.status == "running":
            await interp.stop()
        return trace

    return asyncio.run(main())


class _GuardParity(unittest.TestCase):
    """Compares a guard/action trace on both engines with XState's."""

    GUARDS: Dict[str, bool] = {}

    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

    def check_trace(
        self,
        config: Dict[str, Any],
        steps: Sequence[Step],
        expected: Trace,
        guards: Optional[Dict[str, bool]] = None,
    ) -> None:
        stubs = self.GUARDS if guards is None else guards
        with self.subTest(engine="sync"):
            self.assertEqual(
                expected, _guard_trace_sync(config, steps, stubs)[0]
            )
        with self.subTest(engine="async"):
            self.assertEqual(
                expected, _guard_trace_async(config, steps, stubs)
            )


def _guard_in(name: str, state: str) -> Dict[str, Any]:
    """``and(name, stateIn(state))`` in the JSON dialect."""
    return {
        "type": "and",
        "params": {
            "guards": [
                name,
                {"type": "stateIn", "params": {"stateValue": state}},
            ]
        },
    }


class TestAlwaysOrderFollowsEntryOrder(_GuardParity):
    """`selectEventlessTransitions` visits the leaves in ENTRY order.

    Cases `046_always_order_follows_entry_order` and
    `050_always_order_after_reentry`: XState keeps its active states as a
    list (`snapshot._nodes`); a microstep removes what it exits and appends
    what it enters (document order). When a microstep re-enters exactly
    what it exited and records no history, the previous snapshot -- and
    order -- is kept. The leaf entered first is visited first and wins a
    conflict between two regions' `always` transitions.
    """

    CONFIG: Dict[str, Any] = {
        "id": "m",
        "initial": "p",
        "on": {"RESET": ".p"},
        "states": {
            "p": {
                "type": "parallel",
                "states": {
                    "r1": {
                        "initial": "a",
                        "states": {
                            "a": {"on": {"E": "b"}},
                            "b": {
                                "always": {
                                    "target": "#m.x",
                                    "guard": _guard_in("gB", "#m.p.r2.d"),
                                    "actions": "tB",
                                }
                            },
                        },
                    },
                    "r2": {
                        "initial": "c",
                        "states": {
                            "c": {"on": {"F": "d"}},
                            "d": {
                                "always": {
                                    "target": "#m.y",
                                    "guard": _guard_in("gD", "#m.p.r1.b"),
                                    "actions": "tD",
                                }
                            },
                        },
                    },
                },
            },
            "x": {"entry": "e_x"},
            "y": {"entry": "e_y"},
        },
    }

    REENTRY: Dict[str, Any] = {
        "id": "m",
        "initial": "p",
        "states": {
            "p": {
                "type": "parallel",
                "states": {
                    "r1": {
                        "initial": "s",
                        "states": {
                            "s": {
                                "initial": "s1",
                                "on": {"RS": {"target": "s", "reenter": True}},
                                "states": {
                                    "h": {"type": "history"},
                                    "s1": {
                                        "always": {
                                            "target": "#m.x",
                                            "guard": _guard_in(
                                                "g1", "#m.p.r3.armed"
                                            ),
                                            "actions": "tX",
                                        }
                                    },
                                },
                            }
                        },
                    },
                    "r2": {
                        "initial": "t",
                        "states": {
                            "t": {
                                "initial": "t1",
                                "on": {"RT": {"target": "t", "reenter": True}},
                                "states": {
                                    "t1": {
                                        "always": {
                                            "target": "#m.y",
                                            "guard": _guard_in(
                                                "g2", "#m.p.r3.armed"
                                            ),
                                            "actions": "tY",
                                        }
                                    }
                                },
                            }
                        },
                    },
                    "r3": {
                        "initial": "idle",
                        "states": {
                            "idle": {"on": {"ARM": "armed"}},
                            "armed": {},
                        },
                    },
                },
            },
            "x": {"entry": "e_x", "on": {"BACK": "#m.p"}},
            "y": {"entry": "e_y", "on": {"BACK": "#m.p"}},
        },
    }

    def test_the_leaf_entered_first_is_visited_first_and_wins(self) -> None:
        # xstate 5.33.3, case 046.
        self.check_trace(
            self.CONFIG,
            ["F", "E", "RESET", "E", "F"],
            [
                ([], []),
                ([], ["gD"]),
                (["tD", "e_y"], ["gD", "gB"]),
                ([], []),
                ([], ["gB"]),
                (["tB", "e_x"], ["gB", "gD"]),
            ],
        )

    def test_reentry_moves_a_leaf_only_when_the_snapshot_changes(
        self,
    ) -> None:
        # xstate 5.33.3, case 050: RS records s's history (new snapshot,
        # s1 moves behind t1); RT records nothing (old order kept).
        self.check_trace(
            self.REENTRY,
            ["RS", "RT", "ARM", "BACK", "ARM"],
            [
                ([], ["g1", "g2"]),
                ([], ["g2", "g1"]),
                ([], ["g2", "g1"]),
                (["tY", "e_y"], ["g2", "g1"]),
                ([], ["g1", "g2"]),
                (["tX", "e_x"], ["g1", "g2"]),
            ],
        )

    def test_a_restored_snapshot_visits_leaves_in_document_order(
        self,
    ) -> None:
        # XState's `restoreSnapshot` rebuilds `_nodes` from the state value,
        # i.e. in document order; the live actor keeps its entry order.
        guards = {"gB": False, "gD": False}
        _, live = _guard_trace_sync(self.CONFIG, ["F", "E"], guards)
        log: List[str] = []
        logic = stub_logic(self.CONFIG, guards=guards, guard_log=log)
        machine = create_machine(self.CONFIG, logic=logic)
        restored = SyncInterpreter.from_snapshot(
            live.get_snapshot(), machine
        ).start()
        del log[:]
        restored.send("X")
        self.assertEqual(["gB", "gD"], log)

    def test_the_live_actor_keeps_its_entry_order(self) -> None:
        guards = {"gB": False, "gD": False}
        trace, _ = _guard_trace_sync(self.CONFIG, ["F", "E", "X"], guards)
        self.assertEqual(["gD", "gB"], trace[-1][1])

    def test_pure_transitions_carry_the_entry_order(self) -> None:
        log: List[str] = []
        logic = stub_logic(
            self.CONFIG, guards={"gB": False, "gD": False}, guard_log=log
        )
        machine = create_machine(self.CONFIG, logic=logic)
        snap, _ = initial_transition(machine)
        for event in ("F", "E"):
            snap, _ = pure_transition(machine, snap, event)
        del log[:]
        pure_transition(machine, snap, "X")
        self.assertEqual(["gD", "gB"], log)


class TestHistoryRecordsOnlyOnOwnerExit(_Parity):
    """History is recorded only when its owner is exited (`exitStates`).

    Case `047_history_records_only_on_owner_exit`: NEXT and TOK leave
    states inside `s` but never `s`, so BACK (k -> s.h) finds nothing
    recorded and enters the history default; after OUT exits `s`, IN
    restores what was active then.
    """

    CONFIG: Dict[str, Any] = {
        "id": "m",
        "initial": "s",
        "states": {
            "s": {
                "initial": "g",
                "on": {"OUT": "#m.out"},
                "states": {
                    "h": {"type": "history", "history": "deep"},
                    "g": {
                        "initial": "g1",
                        "on": {"TOK": "k"},
                        "states": {
                            "g1": {"entry": "e_g1", "on": {"NEXT": "g2"}},
                            "g2": {"entry": "e_g2"},
                        },
                    },
                    "k": {"on": {"BACK": "h"}},
                },
            },
            "out": {"on": {"IN": "#m.s.h"}},
        },
    }

    def test_inner_transitions_do_not_record(self) -> None:
        # xstate 5.33.3.
        self.check(
            self.CONFIG,
            ["NEXT", "TOK", "BACK"],
            [["e_g1"], ["e_g2"], [], ["e_g1"]],
            state_ids=["m.s.g.g1"],
        )

    def test_the_owner_exit_records(self) -> None:
        self.check(
            self.CONFIG,
            ["NEXT", "TOK", "BACK", "NEXT", "OUT", "IN"],
            [["e_g1"], ["e_g2"], [], ["e_g1"], ["e_g2"], [], ["e_g2"]],
            state_ids=["m.s.g.g2"],
        )

    def test_no_history_entry_until_the_owner_exits(self) -> None:
        _, interp = _run_sync(self.CONFIG, ["NEXT", "TOK"])
        self.assertEqual({}, json.loads(interp.get_snapshot())["history"])
        interp.send("BACK")
        interp.send("OUT")
        history = json.loads(interp.get_snapshot())["history"]
        self.assertEqual(["m.s"], list(history))


if __name__ == "__main__":
    unittest.main()
