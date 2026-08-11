# tests/tests_cli/test_validation.py
"""Tests for generation-time validation (M6 -- fail loudly)."""

import unittest
from typing import Any, Dict

from src.xstate_statemachine.cli.ir import parse_machine
from src.xstate_statemachine.cli.strategies import get_strategy
from src.xstate_statemachine.cli.strategies.base import GenerationContext
from src.xstate_statemachine.cli.validation import (
    builds_machine_inline,
    check_representable,
    format_refusal,
    verify_generated,
)

_HEADER = (
    "from typing import Any\n"
    "from xstate_statemachine import State, build_machine\n"
)

NESTED: Dict[str, Any] = {
    "id": "n",
    "initial": "outerA",
    "states": {
        "outerA": {
            "initial": "innerX",
            "states": {"innerX": {"on": {"GO": "innerY"}}, "innerY": {}},
            "on": {"NEXT": "outerB"},
        },
        "outerB": {"type": "final"},
    },
}


def _context(config: Dict[str, Any]) -> GenerationContext:
    """Build a minimal GenerationContext for *config*."""
    return GenerationContext(
        actions=set(),
        guards=set(),
        services=set(),
        is_async=False,
        log=True,
        machine_name="n",
        machine_id=config.get("id", "n"),
        machine_names=["n"],
        machine_ids=[config.get("id", "n")],
        file_count=2,
        configs=[config],
        json_filenames=["n.json"],
        hierarchy=True,
        sleep=False,
        sleep_time=0,
        loader=False,
    )


class TestCatchesRegressions(unittest.TestCase):
    """The gate must catch the exact defects that shipped in v0.6."""

    def test_catches_discarded_transitions_and_flattening(self) -> None:
        """The original pythonic-functional bug, reproduced verbatim.

        `.to()` returns a Transition rather than registering one, and the
        states were emitted flat. This produced an inert machine that
        exited 0.
        """
        code = _HEADER + (
            "\ndef build():\n"
            "    a = State('outerA', initial=True)\n"
            "    x = State('innerX')\n"
            "    y = State('innerY')\n"
            "    b = State('outerB')\n"
            "    a.to(b, event='NEXT')\n"
            "    return build_machine(id='n', states=[a, x, y, b])\n"
        )
        problems = verify_generated(
            NESTED, code, template="pythonic-functional"
        )
        self.assertTrue(problems)
        joined = " ".join(problems)
        self.assertIn("outerA.innerX", joined)
        self.assertIn("missing", joined)

    def test_catches_syntax_error(self) -> None:
        """Defect #7: a state named 'None' emitted `None = none`."""
        code = _HEADER + "\ndef build():\n    None = 1\n    return None\n"
        problems = verify_generated(
            NESTED, code, template="pythonic-functional"
        )
        self.assertEqual(len(problems), 1)
        self.assertIn("not valid Python", problems[0])

    def test_catches_missing_machine(self) -> None:
        """Code that builds nothing must be refused, not written."""
        code = _HEADER + "\nx = 1\n"
        problems = verify_generated(
            NESTED, code, template="pythonic-functional"
        )
        self.assertIn("produced no machine", " ".join(problems))

    def test_catches_build_exception(self) -> None:
        """A build() that raises is reported, not swallowed."""
        code = _HEADER + ("\ndef build():\n    raise ValueError('boom')\n")
        problems = verify_generated(
            NESTED, code, template="pythonic-functional"
        )
        self.assertIn("ValueError", " ".join(problems))


class TestAcceptsCorrectOutput(unittest.TestCase):
    """The gate must not cry wolf on correct generators."""

    def test_real_strategies_pass(self) -> None:
        """All three pythonic templates verify cleanly."""
        for template in (
            "pythonic-functional",
            "pythonic-builder",
            "pythonic-class",
        ):
            with self.subTest(template=template):
                code = get_strategy(template).generate_logic(_context(NESTED))
                self.assertEqual(
                    verify_generated(NESTED, code, template=template), []
                )

    def test_json_templates_are_syntax_only(self) -> None:
        """`*-json` logic modules build no machine -- by design.

        Their runner calls create_machine(source_json) at runtime, so
        fidelity is exact by construction and there is nothing to compare.
        """
        self.assertFalse(builds_machine_inline("class-json"))
        self.assertFalse(builds_machine_inline("function-json"))
        self.assertTrue(builds_machine_inline("pythonic-builder"))

        code = get_strategy("class-json").generate_logic(_context(NESTED))
        self.assertEqual(
            verify_generated(
                NESTED, code, template="class-json", strict=False
            ),
            [],
        )


class TestRepresentability(unittest.TestCase):
    """check_representable refuses what a template cannot express."""

    def test_clean_machine_has_no_problems(self) -> None:
        """A fully supported machine passes."""
        machine = parse_machine(NESTED)
        self.assertEqual(
            check_representable(machine, "pythonic-functional"), []
        )

    def test_unknown_keys_are_reported(self) -> None:
        """Anything the IR does not model must surface, not vanish."""
        config = {
            "id": "x",
            "initial": "a",
            "states": {"a": {"someFutureKey": {"nested": 1}}},
        }
        problems = check_representable(
            parse_machine(config), "pythonic-functional"
        )
        self.assertIn("someFutureKey", " ".join(problems))

    def test_stateless_machine_is_reported(self) -> None:
        """A machine with no states cannot produce a working module."""
        problems = check_representable(
            parse_machine({"id": "x"}), "pythonic-functional"
        )
        self.assertIn("no states", " ".join(problems))


class TestRefusalMessage(unittest.TestCase):
    """The message must tell the user what happened and why."""

    def test_message_names_machine_and_states_nothing_written(self) -> None:
        """A refusal explains itself and confirms no file was written."""
        message = format_refusal(
            "pythonic-builder", "orders", ["state 'x' is missing"]
        )
        self.assertIn("pythonic-builder", message)
        self.assertIn("orders", message)
        self.assertIn("state 'x' is missing", message)
        self.assertIn("Nothing was written", message)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
