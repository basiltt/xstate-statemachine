# tests/tests_cli/test_battle_295_b.py
"""#295 battle (adversary B): `xsm asyncapi` / `xsm validate` / `xsm docs`
as an operator types them against sagas and the EDA example.

Every refused input is ONE stderr line and exit code 2 -- never a
traceback. A built saga is plain XState JSON, so the strict validator,
`inspect`, `diagram` and `docs` must all accept it."""

from __future__ import annotations

import importlib.util
import io
import json
import pathlib
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from typing import List, Tuple
from unittest import mock

from src.xstate_statemachine.cli.__main__ import main
from src.xstate_statemachine.cli.commands import reset_console
from src.xstate_statemachine.patterns import RetryPolicy, SagaBuilder

_EXAMPLE = (
    pathlib.Path(__file__).resolve().parents[2]
    / "examples"
    / "integrations"
    / "eda_fulfilment"
    / "machine.json"
)


def _run(argv: List[str]) -> Tuple[int, str]:
    reset_console()
    saved, sys.argv = sys.argv, ["xsm", "--plain", *argv]
    buf, err = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(buf), redirect_stderr(err):
            main()
        code = 0
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
    finally:
        sys.argv = saved
        reset_console()
    return code, buf.getvalue() + err.getvalue()


def _saga() -> SagaBuilder:
    return (
        SagaBuilder("fulfil", start_event="START")
        .step(
            "reserve",
            invoke="reserveStock",
            compensate="releaseStock",
            timeout_ms=5000,
            retry=RetryPolicy(max_attempts=3, jitter="none"),
        )
        .step("charge", invoke="chargeCard", compensate="refundCard")
        .step("ship", invoke="ship")
        .on_failure("notifyOps")
    )


class _Base(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = pathlib.Path(tempfile.mkdtemp())
        self.saga = self.dir / "saga.json"
        self.saga.write_text(json.dumps(_saga().build()), encoding="utf-8")

    def assert_refused(self, argv: List[str], needle: str) -> str:
        code, out = _run(argv)
        self.assertEqual(code, 2, out)
        self.assertNotIn("Traceback", out)
        self.assertIn(needle, out)
        return out


class TestAsyncapiOperatorInput(_Base):
    def test_output_into_a_missing_directory_is_one_line(self) -> None:
        target = self.dir / "no" / "such" / "dir" / "a.json"
        self.assert_refused(
            ["asyncapi", str(self.saga), "-o", str(target)], "cannot write"
        )

    def test_output_onto_a_directory_is_one_line(self) -> None:
        self.assert_refused(
            ["asyncapi", str(self.saga), "-o", str(self.dir)], "cannot write"
        )

    def test_validate_without_jsonschema_is_one_line(self) -> None:
        with mock.patch.dict(sys.modules, {"jsonschema": None}):
            out = self.assert_refused(
                ["asyncapi", str(self.saga), "--validate"], "jsonschema"
            )
        self.assertIn("pip install", out)

    def test_empty_server_is_refused_not_silently_dropped(self) -> None:
        self.assert_refused(
            ["asyncapi", str(self.saga), "--server", ""], "--server"
        )

    def test_empty_topics_are_refused(self) -> None:
        self.assert_refused(
            ["asyncapi", str(self.saga), "--inbound", ""], "--inbound"
        )
        self.assert_refused(
            ["asyncapi", str(self.saga), "--outbound", " "], "--outbound"
        )

    def test_same_inbound_and_outbound_topic_is_valid(self) -> None:
        # 📝 One shared bus topic is a legitimate deployment.
        code, out = _run(
            [
                "asyncapi",
                str(self.saga),
                "--inbound",
                "events",
                "--outbound",
                "events",
            ]
        )
        self.assertEqual(code, 0, out)
        doc = json.loads(out)
        self.assertEqual(doc["channels"]["inbound"]["address"], "events")
        self.assertEqual(doc["channels"]["outbound"]["address"], "events")

    def test_directory_as_machine_is_one_line(self) -> None:
        self.assert_refused(["asyncapi", str(self.dir)], "cannot load")

    def test_saga_document_names_every_step_event(self) -> None:
        code, out = _run(["asyncapi", str(self.saga)])
        self.assertEqual(code, 0, out)
        names = {
            m["name"]
            for m in json.loads(out)["components"]["messages"].values()
        }
        for step in ("reserve", "charge"):
            for what in ("completed", "failed", "compensated"):
                self.assertIn(f"fulfil.{step}.{what}", names)
        self.assertIn("xsm.fulfil.START", names)

    def test_write_then_validate_round_trip(self) -> None:
        if importlib.util.find_spec("jsonschema") is None:
            self.skipTest("jsonschema not installed")
        target = self.dir / "asyncapi.json"
        code, out = _run(
            [
                "asyncapi",
                str(self.saga),
                "-o",
                str(target),
                "--server",
                "localhost:9092",
                "--validate",
            ]
        )
        self.assertEqual(code, 0, out)
        doc = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(doc["servers"]["default"]["protocol"], "kafka")

    def test_a_document_the_schema_rejects_is_one_line(self) -> None:
        if importlib.util.find_spec("jsonschema") is None:
            self.skipTest("jsonschema not installed")
        with mock.patch(
            "src.xstate_statemachine.eda.asyncapi.asyncapi_document",
            return_value={"asyncapi": "3.0.0"},  # no info / no channels
        ):
            self.assert_refused(
                ["asyncapi", str(self.saga), "--validate"],
                "not valid AsyncAPI 3.0",
            )


class TestSagaJsonIsPlainXState(_Base):
    def test_strict_validate_accepts_the_built_saga(self) -> None:
        code, out = _run(["validate", str(self.saga)])
        self.assertEqual(code, 0, out)
        self.assertIn("fulfil", out)

    def test_inspect_and_docs_show_the_whole_shape(self) -> None:
        code, out = _run(["inspect", str(self.saga)])
        self.assertEqual(code, 0, out)
        self.assertIn("compensationFailed", out)
        code, out = _run(["docs", str(self.saga)])
        self.assertEqual(code, 0, out)
        self.assertIn("## Integration events", out)
        self.assertIn("fulfil.charge.compensated", out)

    def test_diagram_runs_on_a_saga(self) -> None:
        # ⚠️ #295-b cross-area note: `MachineNode.to_mermaid` draws only
        #    `on` / `onDone` edges, so a saga's invoke / after edges are
        #    absent from the diagram (use `xsm docs` / `xsm inspect` for
        #    the full transition table). This pins "runs, exit 0".
        code, out = _run(["diagram", str(self.saga)])
        self.assertEqual(code, 0, out)
        self.assertIn("idle --> steps : START", out)


class TestDocsOnTheExample(unittest.TestCase):
    def test_docs_lists_published_events(self) -> None:
        code, out = _run(["docs", str(_EXAMPLE)])
        self.assertEqual(code, 0, out)
        self.assertIn("## Integration events", out)
        self.assertIn("| Published type |", out)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
