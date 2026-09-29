"""#279 (C5): the `fastapi-router` / `pydantic-models` companions against a
real FastAPI.

* 3 corpus machines: the generated router mounts on `FastAPI()` and
  `openapi()` lists exactly one route per declared event;
* a generated router is driven through `TestClient` in a SUBPROCESS
  (generated modules never enter the test interpreter): an enabled event
  → 200, an undeclared one → 404 problem+json, the untouched `authorize`
  stub → a 500 problem (closed by default, X0.1);
* `--check` / `--diff` report drift when an event is added to the JSON;
* golden files for the documented checkout example.
"""

from __future__ import annotations

import io
import json
import logging
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from typing import List, Tuple

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from src.xstate_statemachine.cli.__main__ import main  # noqa: E402
from src.xstate_statemachine.cli.utils import (  # noqa: E402
    camel_to_snake,
    module_safe_name,
)

ROOT = pathlib.Path(__file__).resolve().parents[2]
CORPUS = ROOT / "tests" / "tests_cli" / "stately_machines"
GOLDEN = ROOT / "tests" / "tests_cli" / "golden_web"
SRC = str(ROOT / "src")
#: Chosen for variety: payload-typed events (car_sales), a plain chart
#: (AdvancePayment), and one with odd event names (APA_LogicSM: spaces,
#: colons, `!`, `/` -- slugged into URL segments).
SAMPLE = ("AdvancePayment.json", "car_sales.json", "APA_LogicSM.json")


def _run(argv: List[str]) -> Tuple[int, str]:
    saved, sys.argv = sys.argv, ["xsm", *argv]
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            main()
        code = 0
    except SystemExit as exc:
        code = int(exc.code or 0)
    finally:
        sys.argv = saved
    return code, buf.getvalue()


def _module(cfg_path: pathlib.Path) -> str:
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    raw = str(cfg.get("id", cfg_path.stem)).replace(" ", "_")
    return module_safe_name(camel_to_snake(raw))


def _generate(src: pathlib.Path, out: str, *extra: str) -> Tuple[int, str]:
    return _run(
        [
            "gt",
            str(src),
            "-t",
            "pydantic-models",
            "--with-api",
            "-o",
            out,
            "--plain",
            *extra,
        ]
    )


_PROBE = r"""
import json, sys
sys.path.insert(0, OUT)
from fastapi import FastAPI
from fastapi.testclient import TestClient
from xstate_statemachine import MachineLogic, create_machine
from xstate_statemachine.cli.extractor import extract_logic_names
from xstate_statemachine.contrib.fastapi import allow_all
from xstate_statemachine.cli.strategies._web import collect_events
import importlib
api = importlib.import_module(MOD + "_api")
models = importlib.import_module(MOD + "_models")

app = FastAPI()
app.include_router(api.router)
paths = [p for p in app.openapi()["paths"] if "/events/" in p]
assert len(paths) == len(api.DECLARED_EVENTS) == len(models.EVENT_MODELS), (
    paths, api.DECLARED_EVENTS)
if not DRIVE:
    print("MOUNTED", len(paths))
    raise SystemExit(0)

cfg = json.load(open(CFG, encoding="utf-8"))
_idents = {e.type: e.ident for e in collect_events(cfg)}
api_ident = _idents.__getitem__
a, g, s = extract_logic_names(cfg)
logic = MachineLogic(
    actions={x: (lambda *z: None) for x in a},
    guards={x: (lambda *z: True) for x in g},
    services={x: (lambda *z: None) for x in s},
)
machine = create_machine(cfg, logic=logic)
with TestClient(app, raise_server_exceptions=False) as c:
    # X0.1: the generated stub raises -> nothing is served.
    api.register(machine)
    r = c.get("/" + MOD + "/k1")
    assert r.status_code == 500, r.status_code
    assert r.headers["content-type"].startswith("application/problem+json")
    api.registry._regs.clear()
    api.register(machine, authorize=allow_all)

    state = c.get("/" + MOD + "/k1").json()
    first = state["available_events"][0]
    # the chart's event -> its route (segments may be slugged)
    path = next(
        r.path for r in api.router.routes
        if getattr(r, "name", "") == "send_" + api_ident(first)
    )
    r = c.post(path.replace("{id}", "k1"), json={})
    assert r.status_code in (200, 422), (r.status_code, r.text)
    if r.status_code == 422:  # a typed payload: required fields missing
        assert r.headers["content-type"].startswith("application/problem+json")
        print("TYPED", first)
    else:
        assert r.json()["changed"] is True, r.json()
        print("SENT", first)
    r = c.post("/" + MOD + "/k1/events/NOT_AN_EVENT", json={})
    assert r.status_code == 404, r.status_code
    assert r.headers["content-type"].startswith("application/problem+json")
print("OK")
"""


def _probe(out: str, mod: str, cfg: pathlib.Path, drive: bool) -> str:
    header = (
        f"OUT = {out!r}\nMOD = {mod!r}\nCFG = {str(cfg)!r}\n"
        f"DRIVE = {drive!r}\n"
    )
    env = {**os.environ, "PYTHONPATH": SRC, "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.run(
        [sys.executable, "-c", header + _PROBE],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-3000:]
    return proc.stdout


class _Quiet(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)


class TestCorpusMountsWithOpenAPI(_Quiet):
    def test_three_corpus_machines_mount_one_route_per_event(self) -> None:
        for name in SAMPLE:
            with self.subTest(fixture=name):
                out = tempfile.mkdtemp(prefix="xsm279_")
                src = CORPUS / name
                code, text = _generate(src, out, "-f")
                self.assertEqual(code, 0, text)
                self.assertIn("MOUNTED", _probe(out, _module(src), src, False))


class TestGeneratedRouterDrives(_Quiet):
    def test_enabled_event_is_200_unknown_is_404_problem(self) -> None:
        out = tempfile.mkdtemp(prefix="xsm279_")
        src = pathlib.Path(out) / "checkout.json"
        src.write_text(
            (GOLDEN / "checkout.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        code, text = _generate(src, out, "-f")
        self.assertEqual(code, 0, text)
        stdout = _probe(out, "checkout", src, True)
        self.assertIn("SENT SUBMIT", stdout)
        self.assertIn("OK", stdout)

    def test_corpus_router_drives_through_testclient(self) -> None:
        src = CORPUS / "AdvancePayment.json"
        out = tempfile.mkdtemp(prefix="xsm279_")
        code, text = _generate(src, out, "-f")
        self.assertEqual(code, 0, text)
        self.assertIn("OK", _probe(out, _module(src), src, True))


class TestDrift(_Quiet):
    def test_adding_an_event_is_reported(self) -> None:
        out = pathlib.Path(tempfile.mkdtemp(prefix="xsm279_"))
        src = out / "checkout.json"
        cfg = json.loads((GOLDEN / "checkout.json").read_text("utf-8"))
        src.write_text(json.dumps(cfg), encoding="utf-8")
        self.assertEqual(_generate(src, str(out), "-f")[0], 0)
        code, text = _generate(src, str(out), "--check")
        self.assertEqual(code, 0, text)
        self.assertIn("up to date", text)

        cfg["states"]["cart"]["on"]["CANCEL"] = {"target": "confirmed"}
        src.write_text(json.dumps(cfg), encoding="utf-8")
        code, text = _generate(src, str(out), "--check")
        self.assertEqual(code, 1, text)
        self.assertIn("out of date", text)
        code, text = _generate(src, str(out), "--diff")
        self.assertEqual(code, 1, text)
        self.assertIn("+class CancelEvent(EventModel):", text)
        self.assertIn("/{id}/events/CANCEL", text)


class TestGolden(_Quiet):
    """The documented checkout output, byte for byte (modulo the version
    line of the provenance banner). Regenerate with
    ``XSM_REGEN_GOLDEN=1 pytest tests/tests_cli/test_fastapi_companions.py``.
    """

    def test_checkout_golden_files(self) -> None:
        out = pathlib.Path(tempfile.mkdtemp(prefix="xsm279_"))
        src = out / "checkout.json"
        src.write_text(
            (GOLDEN / "checkout.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        code, text = _generate(src, str(out), "-f")
        self.assertEqual(code, 0, text)
        for name in ("checkout_models.py", "checkout_api.py"):
            got = _normalise((out / name).read_text(encoding="utf-8"))
            golden = GOLDEN / (name + ".golden")
            if os.environ.get("XSM_REGEN_GOLDEN"):
                golden.write_text(got, encoding="utf-8", newline="\n")
            with self.subTest(file=name):
                self.assertEqual(
                    got,
                    golden.read_text(encoding="utf-8").replace("\r\n", "\n"),
                )


def _normalise(code: str) -> str:
    """Drop the generator-version line so a release bump is not a diff."""
    return "\n".join(
        line
        for line in code.replace("\r\n", "\n").split("\n")
        if not line.startswith("Generator:")
    )


if __name__ == "__main__":
    unittest.main()
