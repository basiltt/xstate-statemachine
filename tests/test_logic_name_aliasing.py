"""Snake_case ↔ camelCase logic-name resolution (#snake-alias).

The library's promise: a PEP 8 ``snake_case`` Python function implements
the ``camelCase`` name an XState JSON config uses. These tests pin the
contract for every authoring path and for the cases a forward
``snake -> camel`` conversion gets wrong (acronyms, digits,
non-identifier names), which is why matching is done on a normalised key.
"""

from __future__ import annotations

import time
import types
import unittest
from typing import Any, Dict, List

from xstate_statemachine import (
    InvalidConfigError,
    MachineLogic,
    SyncInterpreter,
    create_machine,
)
from xstate_statemachine.machine_logic import (
    normalize_logic_name,
    resolve_aliases,
)

CONFIG: Dict[str, Any] = {
    "id": "fetchMachine",
    "initial": "idle",
    "context": {"log": []},
    "states": {
        "idle": {
            "entry": "showSpinner",
            "on": {
                "GO": {
                    "target": "loading",
                    "guard": "isReady",
                    "actions": ["resetError", "logHTTPStatus"],
                }
            },
        },
        "loading": {
            "entry": "hideSpinner",
            "invoke": {
                "src": "fetchUser",
                "onDone": "done",
                "onError": "idle",
            },
        },
        "done": {"type": "final"},
    },
}
EXPECTED_LOG = ["show", "reset", "http", "hide"]


def _snake_functions() -> Dict[str, Any]:
    def show_spinner(i, c, e, a):  # noqa: ANN001
        c["log"].append("show")

    def hide_spinner(i, c, e, a):  # noqa: ANN001
        c["log"].append("hide")

    def reset_error(i, c, e, a):  # noqa: ANN001
        c["log"].append("reset")

    def log_http_status(i, c, e, a):  # noqa: ANN001
        c["log"].append("http")

    def is_ready(c, e):  # noqa: ANN001
        return True

    def fetch_user(i, c, e):  # noqa: ANN001
        return {"id": 1}

    return {
        f.__name__: f
        for f in (
            show_spinner,
            hide_spinner,
            reset_error,
            log_http_status,
            is_ready,
            fetch_user,
        )
    }


def _run(machine: Any) -> List[str]:
    interp = SyncInterpreter(machine).start()
    interp.send("GO")
    for _ in range(100):
        if interp.matches("done"):
            break
        time.sleep(0.01)
    log = list(interp.context["log"])
    interp.stop()
    return log


class TestNormalizeLogicName(unittest.TestCase):
    def test_acronyms_and_separators_collapse_to_one_key(self) -> None:
        for spelling in (
            "logHTTPStatus",
            "log_http_status",
            "logHttpStatus",
            "log-http-status",
            "LOG_HTTP_STATUS",
        ):
            self.assertEqual(normalize_logic_name(spelling), "loghttpstatus")

    def test_non_identifier_config_names(self) -> None:
        self.assertEqual(
            normalize_logic_name("inline:machine.state#entry[0]"),
            normalize_logic_name("inline_machine_state_entry_0"),
        )
        self.assertEqual(
            normalize_logic_name("fetch-data"),
            normalize_logic_name("fetch_data"),
        )

    def test_digits_are_preserved(self) -> None:
        self.assertEqual(normalize_logic_name("fetchUserV2"), "fetchuserv2")
        self.assertNotEqual(
            normalize_logic_name("step1"), normalize_logic_name("step2")
        )


class TestSnakeCaseImplementations(unittest.TestCase):
    def test_explicit_machine_logic_with_snake_keys(self) -> None:
        fns = _snake_functions()
        logic = MachineLogic(
            actions={
                k: fns[k]
                for k in (
                    "show_spinner",
                    "hide_spinner",
                    "reset_error",
                    "log_http_status",
                )
            },
            guards={"is_ready": fns["is_ready"]},
            services={"fetch_user": fns["fetch_user"]},
        )
        self.assertEqual(
            _run(create_machine(CONFIG, logic=logic)), EXPECTED_LOG
        )

    def test_logic_modules_discovery(self) -> None:
        module = types.ModuleType("snake_logic_mod")
        module.__dict__.update(_snake_functions())
        machine = create_machine(CONFIG, logic_modules=[module])
        self.assertEqual(_run(machine), EXPECTED_LOG)

    def test_logic_providers_discovery(self) -> None:
        class Provider:
            def show_spinner(self, i, c, e, a):  # noqa: ANN001
                c["log"].append("show")

            def hide_spinner(self, i, c, e, a):  # noqa: ANN001
                c["log"].append("hide")

            def reset_error(self, i, c, e, a):  # noqa: ANN001
                c["log"].append("reset")

            def log_http_status(self, i, c, e, a):  # noqa: ANN001
                c["log"].append("http")

            def is_ready(self, c, e):  # noqa: ANN001
                return True

            def fetch_user(self, i, c, e):  # noqa: ANN001
                return {"id": 1}

        machine = create_machine(CONFIG, logic_providers=[Provider()])
        self.assertEqual(_run(machine), EXPECTED_LOG)

    def test_machine_logic_subclass_methods(self) -> None:
        class FetchLogic(MachineLogic):
            def show_spinner(self, i, c, e, a):  # noqa: ANN001
                c["log"].append("show")

            def hide_spinner(self, i, c, e, a):  # noqa: ANN001
                c["log"].append("hide")

            def reset_error(self, i, c, e, a):  # noqa: ANN001
                c["log"].append("reset")

            def log_http_status(self, i, c, e, a):  # noqa: ANN001
                c["log"].append("http")

            def is_ready(self, c, e):  # noqa: ANN001
                return True

            def fetch_user(self, i, c, e):  # noqa: ANN001
                return {"id": 1}

        machine = create_machine(CONFIG, logic=FetchLogic())
        self.assertEqual(_run(machine), EXPECTED_LOG)


class TestAliasPrecedenceAndSafety(unittest.TestCase):
    def test_exact_name_wins_over_alias(self) -> None:
        hits: List[str] = []

        def camel(i, c, e, a):  # noqa: ANN001
            hits.append("camel")

        def snake(i, c, e, a):  # noqa: ANN001
            hits.append("snake")

        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"entry": "logHTTPStatus"}},
        }
        machine = create_machine(
            cfg,
            logic=MachineLogic(
                actions={"logHTTPStatus": camel, "log_http_status": snake}
            ),
        )
        SyncInterpreter(machine).start().stop()
        self.assertEqual(hits, ["camel"])

    def test_ambiguous_aliases_are_rejected(self) -> None:
        def f1(i, c, e, a):  # noqa: ANN001
            pass

        def f2(i, c, e, a):  # noqa: ANN001
            pass

        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"entry": "logHTTPStatus"}},
        }
        with self.assertRaises(InvalidConfigError) as ctx:
            create_machine(
                cfg,
                logic=MachineLogic(
                    actions={"log_http_status": f1, "loghttpstatus": f2}
                ),
            )
        self.assertIn("ambiguous", str(ctx.exception))

    def test_same_callable_under_two_spellings_is_not_ambiguous(self) -> None:
        def f(i, c, e, a):  # noqa: ANN001
            pass

        registry = {"log_http_status": f, "logHttpStatus": f}
        resolve_aliases(registry, ["logHTTPStatus"])
        self.assertIs(registry["logHTTPStatus"], f)

    def test_non_identifier_names_bind_without_decorator(self) -> None:
        log: List[str] = []

        def inline_m_a_entry_0(i, c, e, a):  # noqa: ANN001
            log.append("inline")

        def fetch_data(i, c, e, a):  # noqa: ANN001
            log.append("fetch")

        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"entry": ["inline:m.a#entry[0]", "fetch-data"]}},
        }
        machine = create_machine(
            cfg,
            logic=MachineLogic(
                actions={
                    "inline_m_a_entry_0": inline_m_a_entry_0,
                    "fetch_data": fetch_data,
                }
            ),
        )
        SyncInterpreter(machine).start().stop()
        self.assertEqual(log, ["inline", "fetch"])

    def test_unrelated_names_are_not_aliased(self) -> None:
        registry = {"reset_error": lambda *a: None}
        resolve_aliases(registry, ["showSpinner"])
        self.assertNotIn("showSpinner", registry)


if __name__ == "__main__":
    unittest.main()
