# tests/tests_cli/test_inline_action_names.py
# -----------------------------------------------------------------------------
# 🏷️ Stately "inline:" action names must survive the Pythonic templates
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: Stately exports name anonymous actions like
# `inline:machine.state#entry[0]`. The pythonic-class and pythonic-functional
# templates turned that into a method name (snake_case, identifier-safe) and
# then relied on the bare `@action` decorator, which REGISTERS the method
# under `_snake_to_camel(fn.__name__)` -- `inlineMachineStateEntry0`. The
# machine config still says `inline:machine.state#entry[0]`, so start()
# raised ImplementationMissingError on every Stately machine with an inline
# action: 26 of the 104 real-world corpus machines. The existing tests
# compiled and imported the generated module but never STARTED it, so the
# name mismatch was invisible. These tests start the machine.
#
# The fix: whenever the identifier-safe method name does not round-trip to
# the original, emit `@action("<original>")` -- the explicit-name form the
# decorators already support. The pythonic-builder template was immune
# because it binds by explicit string (`builder.action("<original>", fn)`).
# -----------------------------------------------------------------------------
"""Generated pythonic code must bind actions under the names the config uses."""

import logging
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict

from src.xstate_statemachine.cli.extractor import extract_logic_names
from src.xstate_statemachine.cli.strategies import get_strategy
from src.xstate_statemachine.cli.strategies.base import GenerationContext
from src.xstate_statemachine.cli.utils import camel_to_snake
from src.xstate_statemachine.cli.__main__ import _combined_output

from .golden import exec_generated, find_machine

# Names Stately actually emits, plus the other shapes that do not round-trip
# through snake_case -> camelCase: dots, hashes, brackets, digits, leading
# capitals, and an already-camelCase name that DOES round-trip (control).
CONFIG: Dict[str, Any] = {
    "id": "inl",
    "initial": "a",
    "context": {"hits": []},
    "states": {
        "a": {
            "entry": [
                {"type": "inline:inl.a#entry[0]"},
                {"type": "Already_Weird-Name.v2"},
                {"type": "plainCamelCase"},
            ],
            "on": {
                "GO": {
                    "target": "b",
                    "guard": "inline:inl.a#GO[-1]#guard[0]",
                    "actions": [{"type": "inline:inl.a#GO[-1]#transition[0]"}],
                }
            },
        },
        "b": {
            "invoke": {
                "src": "inline:inl.b#invoke[0]",
                "onDone": "c",
            }
        },
        "c": {"type": "final"},
    },
}

PYTHONIC = ("pythonic-class", "pythonic-functional", "pythonic-builder")
JSON_TEMPLATES = ("class-json", "function-json")


class TestInlineNamesBindOnEveryPythonicTemplate(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

    def _generate(self, template: str) -> str:
        actions, guards, services = extract_logic_names(CONFIG)
        ctx = GenerationContext(
            actions=actions,
            guards=guards,
            services=services,
            is_async=False,
            log=False,
            machine_name=camel_to_snake(CONFIG["id"]),
            machine_id=CONFIG["id"],
            machine_names=[camel_to_snake(CONFIG["id"])],
            machine_ids=[CONFIG["id"]],
            file_count=1,
            configs=[CONFIG],
            json_filenames=["inl.json"],
            hierarchy=False,
            sleep=False,
            sleep_time=0,
            loader=False,
            style=None,
        )
        strategy = get_strategy(template)
        return _combined_output(
            strategy.generate_logic(ctx), strategy.generate_runner(ctx)
        )

    def test_json_templates_bind_inline_names_through_the_logic_loader(
        self,
    ) -> None:
        """class-json / function-json ship plain methods that `create_machine
        (logic_providers=...)` matches by NAME. A lossy name must therefore
        carry its original as an explicit marker the loader honours."""
        import json
        import os
        import subprocess
        import sys

        for template in JSON_TEMPLATES:
            with self.subTest(template=template):
                code = self._generate(template)
                with tempfile.TemporaryDirectory() as tmp:
                    Path(tmp, "inl.json").write_text(
                        json.dumps(CONFIG), encoding="utf-8"
                    )
                    runner = Path(tmp, "inl.py")
                    runner.write_text(
                        code.replace(
                            "from xstate_statemachine",
                            "from src.xstate_statemachine",
                        ),
                        encoding="utf-8",
                    )
                    root = Path(__file__).resolve().parents[2]
                    proc = subprocess.run(
                        [sys.executable, "-X", "utf8", str(runner)],
                        cwd=tmp,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        env={**os.environ, "PYTHONPATH": str(root)},
                        timeout=60,
                    )
                    self.assertEqual(
                        proc.returncode,
                        0,
                        f"{template} runner failed: {proc.stderr[-800:]}",
                    )

    def test_every_config_name_has_an_implementation(self) -> None:
        """The machine must START and run GO -> b -> (invoke) without
        ImplementationMissingError -- i.e. every action, guard and service
        the config names is bound under EXACTLY that name."""
        from src.xstate_statemachine import SyncInterpreter

        for template in PYTHONIC:
            with self.subTest(template=template):
                code = self._generate(template)
                # Strip the demo `main()` invocation so import has no side
                # effects; we drive the machine ourselves.
                code = code.replace('if __name__ == "__main__":', "if False:")
                module = exec_generated(code, label=template)
                machine = find_machine(module)
                expected = set(
                    CONFIG["states"]["a"]["entry"][i]["type"] for i in range(3)
                ) | {"inline:inl.a#GO[-1]#transition[0]"}
                self.assertTrue(
                    expected <= set(machine.logic.actions),
                    f"{template}: unbound actions "
                    f"{sorted(expected - set(machine.logic.actions))}",
                )
                self.assertIn(
                    "inline:inl.a#GO[-1]#guard[0]", machine.logic.guards
                )
                self.assertIn("inline:inl.b#invoke[0]", machine.logic.services)
                interp = SyncInterpreter(machine).start()  # entry actions run
                interp.send("GO")
                self.assertIn(interp.current_state_ids, ({"inl.b"}, {"inl.c"}))
                interp.stop()

    def test_explicit_name_only_when_needed(self) -> None:
        """A name that round-trips (`plainCamelCase`) keeps the bare
        decorator, so generated code for ordinary machines is unchanged."""
        for template in ("pythonic-class", "pythonic-functional"):
            with self.subTest(template=template):
                code = self._generate(template)
                self.assertIn('@action("inline:inl.a#entry[0]")', code)
                self.assertNotIn('@action("plainCamelCase")', code)
                self.assertRegex(
                    code, r"@action\s*\n\s*def plain_camel_case\("
                )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
