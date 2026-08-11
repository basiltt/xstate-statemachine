# tests/tests_cli/test_round_trip.py
# -----------------------------------------------------------------------------
# 🏛️ The regression gate for code generation fidelity
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: this file is the reason the v0.7.0 defects cannot
# come back. Every other CLI test asserts on generated *strings*; this one
# executes the generated code and compares the machine it builds against
# ``create_machine(source_json)``.
#
# Before v0.7.0 the three pythonic templates scored 0/104 here. String-level
# tests scored 100% the whole time.
# -----------------------------------------------------------------------------
"""Structural round-trip tests for the pythonic code generators."""

import glob
import json
import logging
import os
import unittest
from typing import Any, Callable, Dict, List, Tuple

from src.xstate_statemachine.cli import builders
from src.xstate_statemachine.cli.ir import MachineIR, parse_machine

from .golden import assert_round_trip

logger = logging.getLogger(__name__)

_CORPUS = os.path.join(
    os.path.dirname(__file__), "stately_machines", "*.json"
)

# 📝 Imports the generated snippets rely on. The real CLI emits these via
#    _shared.generate_imports; here we only exercise machine construction.
_HEADER = (
    "from typing import Any\n"
    "from xstate_statemachine import (\n"
    "    MachineBuilder,\n"
    "    State,\n"
    "    StateMachine,\n"
    "    build_machine,\n"
    ")\n\n"
)

_RENDERERS: List[Tuple[str, Callable[..., str]]] = [
    ("functional", builders.render_functional_build),
    ("builder", builders.render_builder_build),
]

# 🛡️ Machines the ENGINE itself rejects. These are invalid source data, not
#    generator bugs -- emailProcessing.json has no "states" key at all.
_INVALID_SOURCES = {"emailProcessing.json"}


def _render(name: str, machine: MachineIR) -> str:
    """Render *machine* with the named strategy, plus imports."""
    renderer = dict(_RENDERERS)[name]
    return _HEADER + renderer(machine, context=machine.context)


class TestRoundTripSynthetic(unittest.TestCase):
    """Targeted regressions for each Tier-0 defect."""

    def _check(self, config: Dict[str, Any]) -> None:
        machine = parse_machine(config)
        for name, _ in _RENDERERS:
            with self.subTest(template=name):
                assert_round_trip(
                    config, _render(name, machine), label=name
                )

    def test_flat_two_state_machine_has_transitions(self) -> None:
        """Defect #1: functional produced machines with ZERO transitions.

        `.to()` RETURNS a Transition; emitting it as a bare expression
        discarded it. Every machine ever produced could start but never move.
        """
        self._check(
            {
                "id": "flat",
                "initial": "idle",
                "states": {
                    "idle": {"on": {"GO": "busy"}},
                    "busy": {"on": {"STOP": "idle"}},
                },
            }
        )

    def test_nested_states_survive(self) -> None:
        """Defect #2: builder dropped every nested state, silently."""
        self._check(
            {
                "id": "n",
                "initial": "outerA",
                "states": {
                    "outerA": {
                        "initial": "innerX",
                        "states": {
                            "innerX": {"on": {"GO": "innerY"}},
                            "innerY": {},
                        },
                        "on": {"NEXT": "outerB"},
                    },
                    "outerB": {"type": "final"},
                },
            }
        )

    def test_colliding_identifiers_keep_distinct_states(self) -> None:
        """Defect #3: 'my-state' and 'my_state' collapsed into one variable."""
        self._check(
            {
                "id": "collide",
                "initial": "my-state",
                "states": {
                    "my-state": {"on": {"GO": "my_state"}},
                    "my_state": {"on": {"BACK": "my state"}},
                    "my state": {},
                },
            }
        )

    def test_python_keywords_as_state_names(self) -> None:
        """Defect #7: a state named 'None' emitted 'None = none'."""
        self._check(
            {
                "id": "kw",
                "initial": "class",
                "states": {
                    "class": {"on": {"GO": "None"}},
                    "None": {"on": {"GO": "return"}},
                    "return": {},
                },
            }
        )

    def test_rich_features_survive(self) -> None:
        """Defect #4: final/after/always/parallel/tags/meta were dropped."""
        self._check(
            {
                "id": "rich",
                "initial": "waiting",
                "states": {
                    "waiting": {
                        "tags": ["busy"],
                        "meta": {"note": "hi"},
                        "entry": "logIn",
                        "exit": "logOut",
                        "after": {
                            1000: "done",
                            "BACKOFF": {
                                "target": "waiting",
                                "guard": "canRetry",
                            },
                        },
                        "always": [{"target": "done", "guard": "skip"}],
                    },
                    "done": {"type": "final"},
                },
            }
        )

    def test_parallel_regions_and_history(self) -> None:
        """Parallel regions, nested finals, history and onDone."""
        self._check(
            {
                "id": "par",
                "initial": "work",
                "states": {
                    "work": {
                        "type": "parallel",
                        "states": {
                            "a": {
                                "initial": "a1",
                                "states": {
                                    "a1": {"on": {"A": "a2"}},
                                    "a2": {"type": "final"},
                                    "aHist": {
                                        "type": "history",
                                        "history": "deep",
                                    },
                                },
                            },
                            "b": {
                                "initial": "b1",
                                "states": {
                                    "b1": {"on": {"B": "b2"}},
                                    "b2": {"type": "final"},
                                },
                            },
                        },
                        "onDone": "finished",
                    },
                    "finished": {"type": "final"},
                },
            }
        )

    def test_composite_guards_and_invoke(self) -> None:
        """Defect #5: guards nested inside and/or/not were never extracted."""
        self._check(
            {
                "id": "svc",
                "initial": "idle",
                "states": {
                    "idle": {
                        "on": {
                            "GO": {
                                "target": "loading",
                                "guard": {
                                    "type": "and",
                                    "params": {
                                        "guards": [
                                            "hasItems",
                                            {
                                                "type": "not",
                                                "params": {
                                                    "guards": ["isBanned"]
                                                },
                                            },
                                        ]
                                    },
                                },
                            }
                        }
                    },
                    "loading": {
                        "invoke": {
                            "src": "fetch",
                            "id": "f",
                            "onDone": "ok",
                            "onError": "err",
                        }
                    },
                    "ok": {"type": "final"},
                    "err": {},
                },
            }
        )

    def test_root_level_properties(self) -> None:
        """Machine-level `on` was dropped, so global escapes vanished."""
        self._check(
            {
                "id": "root",
                "initial": "a",
                "tags": ["top"],
                "on": {"EMERGENCY": "halt"},
                "states": {"a": {"on": {"GO": "b"}}, "b": {}, "halt": {}},
            }
        )

    def test_unicode_state_names(self) -> None:
        """Non-ASCII names must produce valid Python and keep their ids."""
        self._check(
            {
                "id": "i18n",
                "initial": "Возвращение управления",
                "states": {
                    "Возвращение управления": {"on": {"GO": "状態"}},
                    "状態": {"on": {"GO": "café"}},
                    "café": {},
                },
            }
        )

    def test_final_state_with_outgoing_transition(self) -> None:
        """Real exports ship final states with an 'undo' transition."""
        self._check(
            {
                "id": "undo",
                "initial": "consider",
                "states": {
                    "consider": {"on": {"select": "selected"}},
                    "selected": {
                        "type": "final",
                        "on": {"unselect": "consider"},
                    },
                },
            }
        )


class TestRoundTripCorpus(unittest.TestCase):
    """Every real-world machine must regenerate exactly.

    This is the headline number for v0.7.0: 103/104, where the single
    exclusion has no ``states`` key and is rejected by the engine too.
    """

    def setUp(self) -> None:
        self.files = sorted(glob.glob(_CORPUS))
        if not self.files:  # pragma: no cover - corpus ships with the repo
            self.skipTest("stately_machines corpus not present")

    def test_corpus_round_trips(self) -> None:
        """Generated code rebuilds each machine identically."""
        # 🔇 These machines legitimately warn (missing initial, placeholder
        #    context). The warnings are the engine's, not the generator's.
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

        failures: List[str] = []
        checked = 0

        for path in self.files:
            name = os.path.basename(path)
            if name in _INVALID_SOURCES:
                continue
            try:
                with open(path, encoding="utf-8") as handle:
                    config = json.load(handle)
            except (OSError, json.JSONDecodeError):  # pragma: no cover
                continue

            machine = parse_machine(config)
            for template, _ in _RENDERERS:
                checked += 1
                try:
                    assert_round_trip(
                        config, _render(template, machine), label=template
                    )
                except AssertionError as exc:
                    first = str(exc).strip().splitlines()[0]
                    failures.append(f"{name} [{template}]: {first}")

        self.assertGreater(checked, 100, "corpus did not load")
        self.assertEqual(failures, [], "\n".join(failures))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()


class TestRoundTripViaStrategies(unittest.TestCase):
    """The same guarantee, through the code path the CLI actually runs.

    🏛️ TestRoundTripCorpus exercises the renderers directly. This class
    goes through ``get_strategy(...).generate_logic(ctx)`` — the exact
    entry point ``xsm generate-template`` uses — so a renderer that is
    correct but not *wired in* cannot pass. That distinction is not
    hypothetical: every renderer was already correct and every user-facing
    template was still broken.
    """

    TEMPLATES = (
        "pythonic-functional",
        "pythonic-builder",
        "pythonic-class",
    )

    def setUp(self) -> None:
        self.files = sorted(glob.glob(_CORPUS))
        if not self.files:  # pragma: no cover - corpus ships with the repo
            self.skipTest("stately_machines corpus not present")

    @staticmethod
    def _context(config: Dict[str, Any], name: str) -> Any:
        from src.xstate_statemachine.cli.strategies.base import (
            GenerationContext,
        )

        machine_id = config.get("id", "m")
        return GenerationContext(
            actions=set(),
            guards=set(),
            services=set(),
            is_async=False,
            log=True,
            machine_name="m",
            machine_id=machine_id,
            machine_names=["m"],
            machine_ids=[machine_id],
            file_count=2,
            configs=[config],
            json_filenames=[name],
            hierarchy=True,
            sleep=False,
            sleep_time=0,
            loader=False,
        )

    def test_corpus_round_trips_through_cli_strategies(self) -> None:
        """Every template regenerates every real machine exactly."""
        from src.xstate_statemachine.cli.strategies import get_strategy

        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

        failures: List[str] = []
        checked = 0

        for path in self.files:
            name = os.path.basename(path)
            if name in _INVALID_SOURCES:
                continue
            try:
                with open(path, encoding="utf-8") as handle:
                    config = json.load(handle)
            except (OSError, json.JSONDecodeError):  # pragma: no cover
                continue

            for template in self.TEMPLATES:
                checked += 1
                try:
                    code = get_strategy(template).generate_logic(
                        self._context(config, name)
                    )
                    assert_round_trip(config, code, label=template)
                except AssertionError as exc:
                    first = str(exc).strip().splitlines()[0]
                    failures.append(f"{name} [{template}]: {first}")

        self.assertGreater(checked, 300, "corpus did not load")
        self.assertEqual(failures, [], "\n".join(failures))
