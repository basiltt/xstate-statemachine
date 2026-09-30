"""Verification for G3: #273 B6 `[observability]` + #274 B7 live inspector.

`python scripts/verify/G3_observability.py`.

Windows-safe (no heredocs, no /tmp, no curl). Runs the G3 test folders,
the #273 verification one-liner (PrometheusPlugin on AdvancePayment with
`stub_logic`), and the #274 one: `xsm inspect --live` in a subprocess read
over SSE with `http.client`, then `xsm sim --record` + `xsm replay`.
Prints ``ALL OK``.
"""

from __future__ import annotations

import http.client
import json
import os
import pathlib
import re
import socket
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
PAYMENT = (
    ROOT / "tests" / "tests_cli" / "stately_machines" / "AdvancePayment.json"
)
# 💡 Verify THIS checkout even when an editable install points elsewhere
#    (git worktrees share one environment).
sys.path.insert(0, str(ROOT / "src"))
ENV = dict(os.environ, PYTHONPATH=str(ROOT / "src"))


def step(name: str) -> None:
    print(f"\n== {name}")


def run_tests() -> None:
    step("pytest tests/contrib/observability tests/inspect + CLI")
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/contrib/observability",
            "tests/inspect",
            "tests/tests_cli/test_live_inspector.py",
            "-q",
            "-p",
            "no:cacheprovider",
        ],
        cwd=str(ROOT),
        env=ENV,
    )
    assert proc.returncode == 0, "G3 tests failed"


def prometheus_one_liner() -> None:
    step("#273: PrometheusPlugin on AdvancePayment")
    from prometheus_client import CollectorRegistry, generate_latest

    from xstate_statemachine import SyncInterpreter, create_machine
    from xstate_statemachine.contrib.observability import PrometheusPlugin
    from xstate_statemachine.testing_utils import stub_logic

    cfg = json.loads(PAYMENT.read_text(encoding="utf-8"))
    m = create_machine(cfg, logic=stub_logic(cfg))
    reg = CollectorRegistry()
    i = SyncInterpreter(m).use(PrometheusPlugin(registry=reg)).start()
    i.send("SUBMIT")
    i.send("NOPE")
    out = generate_latest(reg).decode()
    i.stop()
    lines = [
        ln
        for ln in out.splitlines()
        if ln.startswith("xstatemachine_transitions_total")
        or "events_received_total{" in ln
    ]
    print("\n".join(lines[:6]))
    assert "xstatemachine_transitions_total{" in out
    assert 'disposition="unhandled"' in out
    assert "NOPE" not in out  # X0.6: undeclared event -> "unknown"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def inspect_live() -> None:
    step("#274: xsm inspect --live, read /events over SSE")
    port = _free_port()
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "xstate_statemachine",
            "--plain",
            "inspect",
            str(PAYMENT),
            "--live",
            "--port",
            str(port),
            "-e",
            "SUBMIT",
            "--duration",
            "20",
        ],
        cwd=str(ROOT),
        env=ENV,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        token = None
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline and token is None:
            line = proc.stdout.readline()
            m = re.search(r"\?token=([\w-]+)", line or "")
            if m:
                token = m.group(1)
        assert token, "no URL printed"
        # unauthenticated -> 401
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        c.request("GET", "/events", headers={"Host": f"127.0.0.1:{port}"})
        assert c.getresponse().status == 401
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        c.request(
            "GET",
            "/events",
            headers={"Host": f"127.0.0.1:{port}", "X-XSM-Token": token},
        )
        resp = c.getresponse()
        assert resp.status == 200
        kinds = []
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and len(set(kinds)) < 3:
            raw = resp.fp.readline()
            if raw.startswith(b"data: "):
                msg = json.loads(raw[6:])
                kinds.append(msg["type"])
                print(
                    "  ", msg["type"], (msg.get("event") or {}).get("type", "")
                )
        assert set(kinds) >= {
            "@xstate.actor",
            "@xstate.event",
            "@xstate.snapshot",
        }, kinds
    finally:
        proc.terminate()
        proc.wait(10)


def record_and_replay() -> None:
    step("#274: xsm sim --record + xsm replay")
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "session.jsonl")
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "xstate_statemachine",
                "--plain",
                "sim",
                str(PAYMENT),
                "-e",
                "SUBMIT,+2001",
                "--record",
                path,
            ],
            cwd=str(ROOT),
            env=ENV,
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        lines = pathlib.Path(path).read_text("utf-8").splitlines()
        print(f"   {len(lines)} lines; head: {lines[0][:120]}")
        assert json.loads(lines[0])["type"] == "@xstate.actor"
        if sys.platform != "win32":
            assert (os.stat(path).st_mode & 0o777) == 0o600
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "xstate_statemachine",
                "--plain",
                "replay",
                path,
            ],
            cwd=str(ROOT),
            env=ENV,
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0 and "SUBMIT" in proc.stdout


def main() -> None:
    run_tests()
    prometheus_one_liner()
    inspect_live()
    record_and_replay()
    print("\nALL OK")


if __name__ == "__main__":
    main()
