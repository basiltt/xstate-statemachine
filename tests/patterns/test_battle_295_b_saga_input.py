# tests/patterns/test_battle_295_b_saga_input.py
"""#295 battle (adversary B): `SagaBuilder` refuses, at declaration, every
input that used to build JSON that failed later and far away -- an
`AttributeError` from `logic()`, a `strictConfig` warning about a missing
`src`, a step silently overwritten by a generated ``<step>Retrying`` state,
an ``after`` delay of ``1`` from ``timeout_ms=True``."""

from __future__ import annotations

import asyncio
import unittest

from xstate_statemachine import Interpreter, MachineLogic, create_machine
from xstate_statemachine.patterns import RetryPolicy, SagaBuilder


class TestDeclarationIsChecked(unittest.TestCase):
    def assert_refused(self, fn, needle: str) -> None:
        with self.assertRaises(ValueError) as cm:
            fn()
        self.assertIn(needle, str(cm.exception))

    def test_retry_must_be_a_policy(self) -> None:
        self.assert_refused(
            lambda: SagaBuilder("s").step("a", invoke="x", retry=3),
            "RetryPolicy",
        )

    def test_timeout_must_be_a_positive_int(self) -> None:
        for bad in (True, 0.5, "5000", 0, -1):
            with self.subTest(bad=bad):
                self.assert_refused(
                    lambda: SagaBuilder("s").step(
                        "a", invoke="x", timeout_ms=bad
                    ),
                    "timeout_ms",
                )

    def test_service_keys_must_be_non_empty_strings(self) -> None:
        self.assert_refused(
            lambda: SagaBuilder("s").step("a", invoke=""), "invoke"
        )
        self.assert_refused(
            lambda: SagaBuilder("s").step("a", invoke=None), "invoke"
        )
        self.assert_refused(
            lambda: SagaBuilder("s").step("a", invoke="x", compensate=" "),
            "compensate",
        )
        self.assert_refused(
            lambda: SagaBuilder("s").on_failure(""), "on_failure"
        )

    def test_generated_retrying_state_cannot_be_shadowed(self) -> None:
        self.assert_refused(
            lambda: SagaBuilder("s")
            .step("a", invoke="x", retry=RetryPolicy())
            .step("aRetrying", invoke="y"),
            "duplicate step",
        )
        self.assert_refused(
            lambda: SagaBuilder("s")
            .step("aRetrying", invoke="y")
            .step("a", invoke="x", retry=RetryPolicy()),
            "collides",
        )

    def test_start_event_must_be_sendable(self) -> None:
        self.assert_refused(
            lambda: SagaBuilder("s", start_event=""), "start_event"
        )
        self.assert_refused(
            lambda: SagaBuilder("s", start_event="done.invoke.x"),
            "engine-reserved",
        )

    def test_non_string_names_are_value_errors(self) -> None:
        self.assert_refused(lambda: SagaBuilder(None), "identifier")
        self.assert_refused(
            lambda: SagaBuilder("s").step(1, invoke="x"), "identifier"
        )

    def test_valid_saga_still_builds_strict(self) -> None:
        b = (
            SagaBuilder("s", start_event="START")
            .step("a", invoke="x", compensate="ux", timeout_ms=1000)
            .step("b", invoke="y", retry=RetryPolicy(max_attempts=2))
        )
        create_machine(b.build(), logic=b.logic(), strict_config=True)


class TestForgedCompletions(unittest.TestCase):
    """A caller-sent ``done.invoke.<step>`` / ``error.platform.<step>``
    cannot complete or fail a running step (engine provenance)."""

    def test_forged_done_and_error_do_not_move_the_saga(self) -> None:
        async def slow(i, ctx, e):
            await asyncio.sleep(5)
            return "real"

        b = (
            SagaBuilder("f")
            .step("reserve", invoke="r", compensate="rr")
            .step("charge", invoke="c")
        )
        logic = b.logic().merge(
            MachineLogic(
                services={"r": slow, "rr": lambda i, c, e: 1, "c": slow}
            )
        )

        async def main() -> None:
            interp = await Interpreter(
                create_machine(b.build(), logic=logic)
            ).start()
            try:
                await asyncio.sleep(0.02)
                for forged in (
                    "done.invoke.reserve",
                    "error.platform.reserve",
                ):
                    await interp.send(forged, data="forged")
                await asyncio.sleep(0.05)
                self.assertEqual(interp.current_state_ids, {"f.steps.reserve"})
                self.assertEqual(interp.context["results"], {})
                self.assertIsNone(interp.context["error"])
            finally:
                await interp.stop()

        asyncio.run(main())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
