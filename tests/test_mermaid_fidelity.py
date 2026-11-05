"""🎨 Diagram export fidelity: delayed edges, final markers, region dividers.

`to_mermaid()` / `to_plantuml()` used to omit three things a statechart
diagram needs: `after` (delayed) transitions, a ``--> [*]`` marker on final
states, and the ``--`` divider between the regions of a parallel state. These
tests pin each of them, plus the neighbouring edge kinds (`always`, `onDone`,
`invoke` onDone / onError) and the Mermaid grammar rules the output obeys.
"""

from __future__ import annotations

# -------------------------------------------------------------------------
# 📦 Standard Library Imports
# -------------------------------------------------------------------------
import copy
import re
import unittest
import warnings
from typing import Any, Dict, List

# -------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -------------------------------------------------------------------------
from src.xstate_statemachine import (
    MachineLogic,
    State,
    StateMachine,
    create_machine as _create_machine,
)

_EDGE = re.compile(r"(\[\*\]|\w+) --> (\[\*\]|\w+)( : \S.*)?")
_DECLARATION = re.compile(r'state "(\w+)" as (\w+)( \{)?')

# 📝 Diagram export never runs logic, but `create_machine` insists that every
#    named guard / action exists, so the fixtures bind inert stand-ins.
_STUB_GUARDS = ("isStale", "isVip", "g", "ready", "ok", "fatal")


def create_machine(config: Dict[str, Any], **kwargs: Any) -> Any:
    """Build a machine whose guards and the ``tick`` action are inert."""
    logic: MachineLogic[Any] = MachineLogic(
        guards={name: (lambda ctx, event: True) for name in _STUB_GUARDS},
        actions={"tick": lambda interpreter, ctx, event, action: None},
    )
    return _create_machine(config, logic=logic, **kwargs)


def assert_valid_mermaid(test: unittest.TestCase, text: str) -> None:
    """Check the Mermaid ``stateDiagram-v2`` grammar rules we rely on.

    * the header is the first line and appears once;
    * every ``state "x" as x {`` block is closed, and the contents of a
      block are indented one level (4 spaces) deeper than its header;
    * ``--`` sits alone on its line, directly between two sibling blocks of
      a ``type: parallel`` state, and never at the top level;
    * every other line is a declaration or a ``a --> b [: label]`` edge,
      where ``[*]`` is the literal start/end pseudo-state.
    """
    lines = text.splitlines()
    test.assertEqual(lines[0], "stateDiagram-v2")
    test.assertEqual(text.count("stateDiagram-v2"), 1)
    depth = 0
    for number, line in enumerate(lines[1:], start=1):
        body = line.strip()
        test.assertTrue(body, f"blank line {number}")
        if body == "}":
            depth -= 1
            test.assertGreaterEqual(depth, 0, line)
        test.assertEqual(len(line) - len(line.lstrip(" ")), 4 * depth, line)
        if body == "}":
            continue
        if body == "--":
            test.assertGreater(depth, 0, "divider outside a block")
            test.assertEqual(lines[number - 1].strip(), "}")
            test.assertTrue(lines[number + 1].lstrip().startswith("state "))
            continue
        declaration = _DECLARATION.fullmatch(body)
        if declaration:
            depth += 1 if declaration.group(3) else 0
            continue
        test.assertIsNotNone(_EDGE.fullmatch(body), line)
    test.assertEqual(depth, 0, "unbalanced braces")


def _edges(text: str) -> List[str]:
    """Labelled edge lines of an export, stripped of indentation."""
    return [line.strip() for line in text.splitlines() if " : " in line]


def _dividers(text: str) -> List[str]:
    """Every region-divider line (``--`` alone), indentation preserved."""
    return [line for line in text.splitlines() if line.strip() == "--"]


class AfterEdgeTests(unittest.TestCase):
    """`after` (delayed) transitions are drawn as ``after <delay>`` edges."""

    def _mermaid(self, after: Dict[str, Any]) -> str:
        machine = create_machine(
            {
                "id": "order",
                "initial": "created",
                "states": {
                    "created": {"after": after},
                    "cancelled": {},
                    "escalated": {},
                },
            }
        )
        text = machine.to_mermaid()
        assert_valid_mermaid(self, text)
        return text

    def test_numeric_delay_is_labelled_in_milliseconds(self) -> None:
        text = self._mermaid({"100": "cancelled"})
        self.assertEqual(_edges(text), ["created --> cancelled : after 100ms"])

    def test_named_delay_keeps_its_name(self) -> None:
        text = self._mermaid({"TIMEOUT": "cancelled"})
        self.assertEqual(
            _edges(text), ["created --> cancelled : after TIMEOUT"]
        )

    def test_object_form_with_guard_shows_the_guard(self) -> None:
        text = self._mermaid(
            {"100": {"target": "cancelled", "guard": "isStale"}}
        )
        self.assertEqual(
            _edges(text), ["created --> cancelled : after 100ms [isStale]"]
        )

    def test_array_form_draws_every_alternative(self) -> None:
        text = self._mermaid(
            {
                "250": [
                    {"target": "escalated", "guard": "isVip"},
                    {"target": "cancelled"},
                ]
            }
        )
        self.assertEqual(
            _edges(text),
            [
                "created --> escalated : after 250ms [isVip]",
                "created --> cancelled : after 250ms",
            ],
        )

    def test_several_delays_are_each_drawn(self) -> None:
        text = self._mermaid({"100": "cancelled", "SLOW": "escalated"})
        self.assertEqual(
            _edges(text),
            [
                "created --> cancelled : after 100ms",
                "created --> escalated : after SLOW",
            ],
        )

    def test_targetless_after_is_not_drawn(self) -> None:
        text = self._mermaid({"100": {"actions": "tick"}})
        self.assertEqual(_edges(text), [])

    def test_plantuml_draws_the_same_edges(self) -> None:
        machine = create_machine(
            {
                "id": "order",
                "initial": "created",
                "states": {
                    "created": {
                        "after": {
                            "100": "cancelled",
                            "TIMEOUT": {"target": "cancelled", "guard": "g"},
                        }
                    },
                    "cancelled": {},
                },
            }
        )
        self.assertEqual(
            _edges(machine.to_plantuml()),
            [
                "order_created --> order_cancelled : after 100ms",
                "order_created --> order_cancelled : after TIMEOUT [g]",
            ],
        )


class FinalMarkerTests(unittest.TestCase):
    """Every ``type: final`` state ends its region with ``--> [*]``."""

    def test_top_level_final_gets_an_end_marker(self) -> None:
        machine = create_machine(
            {
                "id": "parcel",
                "initial": "sent",
                "states": {
                    "sent": {"on": {"DELIVER": "shipped"}},
                    "shipped": {"type": "final"},
                },
            }
        )
        text = machine.to_mermaid()
        assert_valid_mermaid(self, text)
        self.assertIn("\n    shipped --> [*]\n", text)
        self.assertEqual(text.count("--> [*]"), 1)

    def test_nested_final_is_marked_inside_its_parents_block(self) -> None:
        machine = create_machine(
            {
                "id": "order",
                "initial": "paid",
                "states": {
                    "paid": {
                        "initial": "packing",
                        "states": {
                            "packing": {"on": {"SHIP": "shipped"}},
                            "shipped": {"type": "final"},
                        },
                    },
                },
            }
        )
        lines = machine.to_mermaid().splitlines()
        assert_valid_mermaid(self, "\n".join(lines))
        marker = lines.index("        shipped --> [*]")
        self.assertEqual(
            lines[marker - 1], '        state "shipped" as shipped'
        )
        self.assertEqual(lines[marker + 1], "    }")

    def test_non_final_states_and_atomic_root_have_no_marker(self) -> None:
        machine = create_machine({"id": "solo", "states": {}})
        self.assertNotIn("--> [*]", machine.to_mermaid())

    def test_one_marker_per_final_state(self) -> None:
        machine = create_machine(
            {
                "id": "m",
                "initial": "a",
                "states": {
                    "a": {"on": {"X": "b"}},
                    "b": {"type": "final"},
                    "c": {"type": "final"},
                },
            }
        )
        text = machine.to_mermaid()
        self.assertEqual(text.count("b --> [*]"), 1)
        self.assertEqual(text.count("c --> [*]"), 1)
        self.assertEqual(text.count("--> [*]"), 2)

    def test_plantuml_marks_finals_inside_the_enclosing_block(self) -> None:
        machine = create_machine(
            {
                "id": "order",
                "initial": "paid",
                "states": {
                    "paid": {
                        "initial": "packing",
                        "states": {
                            "packing": {},
                            "shipped": {"type": "final"},
                        },
                    },
                },
            }
        )
        lines = machine.to_plantuml().splitlines()
        marker = lines.index("    order_paid_shipped --> [*]")
        self.assertEqual(
            lines[marker - 1], '    state "shipped" as order_paid_shipped'
        )
        self.assertEqual(lines[marker + 1], "  }")


def _parallel_config() -> Dict[str, Any]:
    return {
        "id": "player",
        "initial": "playing",
        "states": {
            "playing": {
                "type": "parallel",
                "states": {
                    "video": {
                        "initial": "loading",
                        "states": {"loading": {}},
                    },
                    "audio": {"initial": "muted", "states": {"muted": {}}},
                    "controls": {
                        "initial": "visible",
                        "states": {"visible": {}},
                    },
                },
            },
        },
    }


class ParallelDividerTests(unittest.TestCase):
    """Regions of a parallel state are separated by a lone ``--`` line."""

    def test_divider_sits_between_each_pair_of_regions(self) -> None:
        text = create_machine(_parallel_config()).to_mermaid()
        assert_valid_mermaid(self, text)
        lines = text.splitlines()
        dividers = [i for i, line in enumerate(lines) if line.strip() == "--"]
        self.assertEqual(len(dividers), 2)
        for index in dividers:
            self.assertEqual(lines[index], "        --")
            self.assertEqual(lines[index - 1], "        }")
        self.assertEqual(
            lines[dividers[0] + 1], '        state "audio" as audio {'
        )
        self.assertEqual(
            lines[dividers[1] + 1], '        state "controls" as controls {'
        )

    def test_single_region_gets_no_divider(self) -> None:
        config = _parallel_config()
        del config["states"]["playing"]["states"]["audio"]
        del config["states"]["playing"]["states"]["controls"]
        text = create_machine(config).to_mermaid()
        self.assertEqual(_dividers(text), [])

    def test_compound_siblings_are_not_divided(self) -> None:
        text = create_machine(
            {
                "id": "m",
                "initial": "a",
                "states": {
                    "a": {"initial": "x", "states": {"x": {}}},
                    "b": {"initial": "y", "states": {"y": {}}},
                },
            }
        ).to_mermaid()
        self.assertEqual(_dividers(text), [])

    def test_parallel_root_is_divided_at_the_top_block(self) -> None:
        config = _parallel_config()["states"]["playing"]
        config["id"] = "root"
        text = create_machine(config).to_mermaid()
        assert_valid_mermaid(self, text)
        self.assertEqual(_dividers(text), ["    --", "    --"])

    def test_nested_parallel_inside_a_region_is_divided_in_place(self) -> None:
        config = _parallel_config()
        inner = copy.deepcopy(config["states"]["playing"])
        config["states"]["playing"]["states"]["audio"] = {
            "initial": "inner",
            "states": {"inner": inner},
        }
        text = create_machine(config).to_mermaid()
        assert_valid_mermaid(self, text)
        # 🔀 Two dividers for the outer parallel, two for the inner one.
        self.assertEqual(len(_dividers(text)), 4)

    def test_plantuml_separates_regions_with_a_divider(self) -> None:
        lines = create_machine(_parallel_config()).to_plantuml().splitlines()
        dividers = [i for i, line in enumerate(lines) if line.strip() == "--"]
        self.assertEqual(len(dividers), 2)
        for index in dividers:
            self.assertEqual(lines[index], "    --")
            self.assertEqual(lines[index - 1], "    }")


class OtherEdgeKindTests(unittest.TestCase):
    """`always`, `onDone` and `invoke` edges are drawn, in the same style."""

    def test_always_edges_are_labelled_not_blank(self) -> None:
        machine = create_machine(
            {
                "id": "m",
                "initial": "a",
                "states": {
                    "a": {
                        "always": [
                            {"target": "b", "guard": "ready"},
                            {"target": "c"},
                        ]
                    },
                    "b": {},
                    "c": {},
                },
            }
        )
        text = machine.to_mermaid()
        assert_valid_mermaid(self, text)
        self.assertEqual(
            _edges(text), ["a --> b : always [ready]", "a --> c : always"]
        )

    def test_on_edges_keep_their_bare_event_label(self) -> None:
        machine = create_machine(
            {
                "id": "m",
                "initial": "a",
                "states": {
                    "a": {"on": {"GO": {"target": "b", "guard": "ok"}}},
                    "b": {},
                },
            }
        )
        self.assertEqual(_edges(machine.to_mermaid()), ["a --> b : GO"])

    def test_invoke_on_done_and_on_error_are_drawn(self) -> None:
        machine = create_machine(
            {
                "id": "m",
                "initial": "loading",
                "states": {
                    "loading": {
                        "invoke": {
                            "src": "fetch",
                            "onDone": "ready",
                            "onError": {"target": "failed", "guard": "fatal"},
                        },
                    },
                    "ready": {},
                    "failed": {},
                },
            }
        )
        text = machine.to_mermaid()
        assert_valid_mermaid(self, text)
        self.assertEqual(
            _edges(text),
            [
                "loading --> ready : invoke onDone",
                "loading --> failed : invoke onError [fatal]",
            ],
        )
        self.assertEqual(
            _edges(machine.to_plantuml()),
            [
                "m_loading --> m_ready : invoke onDone",
                "m_loading --> m_failed : invoke onError [fatal]",
            ],
        )

    def test_compound_on_done_is_still_drawn(self) -> None:
        machine = create_machine(
            {
                "id": "m",
                "initial": "work",
                "states": {
                    "work": {
                        "initial": "x",
                        "onDone": "end",
                        "states": {"x": {"type": "final"}},
                    },
                    "end": {"type": "final"},
                },
            }
        )
        text = machine.to_mermaid()
        assert_valid_mermaid(self, text)
        self.assertEqual(_edges(text), ["work --> end : onDone"])
        self.assertIn("m_work --> m_end : onDone", machine.to_plantuml())

    def test_unresolvable_targets_are_skipped(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            machine = create_machine(
                {
                    "id": "m",
                    "initial": "a",
                    "states": {"a": {"after": {"10": "nowhere"}}},
                },
                strict_targets=False,
            )
        self.assertEqual(_edges(machine.to_mermaid()), [])


_ORDER_CONFIG: Dict[str, Any] = {
    "id": "Order",
    "initial": "created",
    "states": {
        "created": {"after": {"100": "cancelled"}, "on": {"PAY": "paid"}},
        "paid": {
            "initial": "packing",
            "onDone": "fulfil",
            "states": {
                "packing": {"on": {"SHIP": "shipped"}},
                "shipped": {"type": "final"},
            },
        },
        "fulfil": {
            "type": "parallel",
            "on": {"CLOSE": "closed"},
            "states": {
                "payment": {
                    "initial": "pending",
                    "states": {
                        "pending": {"on": {"SETTLE": "settled"}},
                        "settled": {"type": "final"},
                    },
                },
                "notify": {
                    "initial": "idle",
                    "states": {
                        "idle": {"on": {"SEND_MAIL": "sent"}},
                        "sent": {"type": "final"},
                    },
                },
            },
        },
        "closed": {"type": "final"},
        "cancelled": {"type": "final"},
    },
}

_ORDER_MERMAID = """\
stateDiagram-v2
[*] --> Order
state "Order" as Order {
    [*] --> created
    state "created" as created
    state "paid" as paid {
        [*] --> packing
        state "packing" as packing
        state "shipped" as shipped
        shipped --> [*]
    }
    state "fulfil" as fulfil {
        state "payment" as payment {
            [*] --> pending
            state "pending" as pending
            state "settled" as settled
            settled --> [*]
        }
        --
        state "notify" as notify {
            [*] --> idle
            state "idle" as idle
            state "sent" as sent
            sent --> [*]
        }
    }
    state "closed" as closed
    closed --> [*]
    state "cancelled" as cancelled
    cancelled --> [*]
}
created --> paid : PAY
created --> cancelled : after 100ms
paid --> fulfil : onDone
packing --> shipped : SHIP
fulfil --> closed : CLOSE
pending --> settled : SETTLE
idle --> sent : SEND_MAIL"""


class OrderExampleTests(unittest.TestCase):
    """The documented ``Order`` chart renders all three missing features."""

    def test_json_equivalent_renders_exactly(self) -> None:
        text = create_machine(copy.deepcopy(_ORDER_CONFIG)).to_mermaid()
        assert_valid_mermaid(self, text)
        self.assertEqual(text, _ORDER_MERMAID)

    def test_pythonic_dsl_order_renders_after_markers_and_divider(
        self,
    ) -> None:
        if not hasattr(State, "Compound"):
            self.skipTest("nested-class DSL (State.Compound) not available")

        class Order(StateMachine):
            created = State(initial=True, after={100: "cancelled"})

            class paid(State.Compound, on_done="fulfil"):  # type: ignore
                packing = State(initial=True)
                shipped = State(final=True)
                ship = packing.to(shipped)

            class fulfil(State.Parallel):  # type: ignore
                class payment(State.Compound):  # type: ignore
                    pending = State(initial=True)
                    settled = State(final=True)
                    settle = pending.to(settled)

                class notify(State.Compound):  # type: ignore
                    idle = State(initial=True)
                    sent = State(final=True)
                    send_mail = idle.to(sent)

            closed = State(final=True)
            cancelled = State(final=True)
            pay = created.to(paid)
            close = fulfil.to(closed)

        text = Order.create_machine().to_mermaid()
        assert_valid_mermaid(self, text)
        self.assertIn("created --> cancelled : after 100ms", text)
        self.assertIn("        shipped --> [*]", text.splitlines())
        self.assertIn("            settled --> [*]", text.splitlines())
        self.assertIn("            sent --> [*]", text.splitlines())
        self.assertEqual(_dividers(text), ["        --"])
        self.assertEqual(text.count("--> [*]"), 5)


if __name__ == "__main__":
    unittest.main()
