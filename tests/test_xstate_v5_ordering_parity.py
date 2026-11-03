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
from typing import Any, Dict, List, Sequence, Tuple, Union

from src.xstate_statemachine import (
    Interpreter,
    SyncInterpreter,
    create_machine,
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


if __name__ == "__main__":
    unittest.main()
