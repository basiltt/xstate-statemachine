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


if __name__ == "__main__":
    unittest.main()
