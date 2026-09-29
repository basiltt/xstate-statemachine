#!/usr/bin/env python
# scripts/verify/279_codegen_api.py
# -----------------------------------------------------------------------------
# ✅ #279 (C5) verification: `xsm gt --with-api --with-models`
# -----------------------------------------------------------------------------
# Generates the FastAPI router + pydantic models for a corpus machine into a
# fresh `tempfile.mkdtemp()` directory, mounts the router on a FastAPI app,
# checks the OpenAPI paths (one per declared event), drives one event
# through TestClient, and checks `--check` reports drift when an event is
# added to the JSON. Prints `ALL OK`.
#
#   python -m pip install -e ".[fastapi]" httpx
#   python scripts/verify/279_codegen_api.py
# -----------------------------------------------------------------------------
"""Issue #279 verification scenario."""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCE = (
    ROOT / "tests" / "tests_cli" / "stately_machines" / "AdvancePayment.json"
)
MODULE = "advance_payment_flow"


def xsm(*argv: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "xstate_statemachine", *argv],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(ROOT),
    )


def drive(out: pathlib.Path) -> None:
    """Mount, list OpenAPI paths, send one enabled event (in a subprocess
    so the generated modules never enter this interpreter)."""
    probe = f"""
import sys
sys.path.insert(0, {str(out)!r})
from fastapi import FastAPI
from fastapi.testclient import TestClient
from xstate_statemachine import MachineLogic, create_machine
from xstate_statemachine.cli.extractor import extract_logic_names
from xstate_statemachine.contrib.fastapi import allow_all
import json, {MODULE}_api as api, {MODULE}_models as models

cfg = json.load(open({str(SOURCE)!r}, encoding="utf-8"))
a, g, s = extract_logic_names(cfg)
logic = MachineLogic(
    actions={{x: (lambda *z: None) for x in a}},
    guards={{x: (lambda *z: True) for x in g}},
    services={{x: (lambda *z: None) for x in s}},
)
api.register(create_machine(cfg, logic=logic), authorize=allow_all)
app = FastAPI()
app.include_router(api.router)
paths = sorted(app.openapi()["paths"])
print(paths)
events = [p for p in paths if "/events/" in p]
assert len(events) == len(api.DECLARED_EVENTS) == len(models.EVENT_MODELS), paths
with TestClient(app) as c:
    state = c.get("/{MODULE}/o1").json()
    first = state["available_events"][0]
    r = c.post("/{MODULE}/o1/events/" + first, json={{}})
    assert r.status_code == 200, (r.status_code, r.text)
    r = c.post("/{MODULE}/o1/events/NOPE", json={{}})
    assert r.status_code == 404, r.status_code
    assert r.headers["content-type"].startswith("application/problem+json")
print("driven", first)
"""
    proc = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    print(proc.stdout.strip())
    assert proc.returncode == 0, proc.stderr[-3000:]


def main() -> None:
    out = pathlib.Path(tempfile.mkdtemp(prefix="xsmapi_"))
    try:
        base = [
            "gt",
            str(SOURCE),
            "-t",
            "pythonic-class",
            "--with-api",
            "--with-models",
            "-o",
            str(out),
            "--plain",
        ]
        proc = xsm(*base, "-f")
        assert proc.returncode == 0, proc.stdout + proc.stderr
        for suffix in ("_api.py", "_models.py"):
            assert (out / f"{MODULE}{suffix}").exists(), sorted(
                p.name for p in out.iterdir()
            )
        drive(out)

        # 🔁 --check: clean now; drift once the JSON gains an event.
        proc = xsm(*base, "--check")
        assert proc.returncode == 0, proc.stdout + proc.stderr
        cfg = json.loads(SOURCE.read_text(encoding="utf-8"))
        first = next(iter(cfg["states"].values()))
        first.setdefault("on", {})["BRAND_NEW_EVENT"] = {}
        edited = out / SOURCE.name
        edited.write_text(json.dumps(cfg), encoding="utf-8")
        base[1] = str(edited)
        proc = xsm(*base, "--diff")
        assert proc.returncode == 1, proc.stdout + proc.stderr
        assert "out of date" in proc.stdout + proc.stderr
        assert "BRAND_NEW_EVENT" in proc.stdout, proc.stdout[-2000:]
        print("drift detected")
    finally:
        shutil.rmtree(out, ignore_errors=True)
    print("ALL OK")


if __name__ == "__main__":
    main()
