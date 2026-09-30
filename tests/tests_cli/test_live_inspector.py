"""`xsm inspect --live`, `xsm sim --record`, `xsm replay` (#274)."""

from __future__ import annotations

import http.client
import io
import json
import logging
import os
import pathlib
import stat
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from typing import List

from src.xstate_statemachine import plugins
from src.xstate_statemachine.cli.__main__ import main
from src.xstate_statemachine.cli.commands import reset_console
from src.xstate_statemachine.cli.commands.live import (
    run_inspect_live,
    run_replay,
)

ROOT = pathlib.Path(__file__).resolve().parents[2]
PAYMENT = (
    ROOT / "tests" / "tests_cli" / "stately_machines" / "AdvancePayment.json"
)


def _run(argv: List[str]) -> tuple:
    reset_console()
    saved, sys.argv = sys.argv, ["xsm", "--plain", *argv]
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            main()
        code = 0
    except SystemExit as exc:
        code = exc.code or 0
    finally:
        sys.argv = saved
        reset_console()
    return code, buf.getvalue()


def _messages(sink):
    conn = http.client.HTTPConnection("127.0.0.1", sink.port, timeout=5)
    conn.request(
        "GET",
        "/messages",
        headers={
            "Host": f"127.0.0.1:{sink.port}",
            "X-XSM-Token": sink.token,
        },
    )
    resp = conn.getresponse()
    return resp.status, json.loads(resp.read())


class _Base(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)
        reset_console()
        self.addCleanup(reset_console)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        before = plugins.global_plugins()
        self.addCleanup(
            lambda: [
                plugins.unregister_global(p)
                for p in plugins.global_plugins()
                if not any(p is b for b in before)
            ]
        )


class TestRecordAndReplay(_Base):
    def test_sim_record_writes_protocol_jsonl_0600(self) -> None:
        out = os.path.join(self.tmp.name, "s.jsonl")
        code, _ = _run(
            ["sim", str(PAYMENT), "-e", "SUBMIT,+2001", "--record", out]
        )
        self.assertEqual(code, 0)
        lines = pathlib.Path(out).read_text("utf-8").splitlines()
        msgs = [json.loads(ln) for ln in lines]
        self.assertEqual(msgs[0]["type"], "@xstate.actor")
        types = {(m["type"], (m.get("event") or {}).get("type")) for m in msgs}
        self.assertIn(("@xstate.event", "SUBMIT"), types)
        self.assertIn(("@xstate.snapshot", "SUBMIT"), types)
        for m in msgs:  # deny-by-default context
            if "snapshot" in m:
                self.assertEqual(m["snapshot"]["context"], {})
        if sys.platform != "win32":
            self.assertEqual(stat.S_IMODE(os.stat(out).st_mode), 0o600)
        self.assertEqual(plugins.global_plugins(), [])  # uninstalled

    def test_record_context_allowlist(self) -> None:
        out = os.path.join(self.tmp.name, "s.jsonl")
        _run(
            [
                "sim",
                str(PAYMENT),
                "-e",
                "SUBMIT",
                "--record",
                out,
                "--context",
                "amount,cardNumber",
            ]
        )
        snap = next(
            json.loads(ln)
            for ln in pathlib.Path(out).read_text("utf-8").splitlines()
            if '"@xstate.snapshot"' in ln
        )
        self.assertEqual(
            snap["snapshot"]["context"],
            {"amount": 149900, "cardNumber": "***"},
        )

    def test_record_to_bad_path_fails_cleanly(self) -> None:
        bad = os.path.join(self.tmp.name, "no", "such", "dir.jsonl")
        code, _ = _run(["sim", str(PAYMENT), "-e", "SUBMIT", "--record", bad])
        self.assertEqual(code, 1)
        self.assertEqual(plugins.global_plugins(), [])

    def test_replay_prints_and_missing_file(self) -> None:
        out = os.path.join(self.tmp.name, "s.jsonl")
        _run(["sim", str(PAYMENT), "-e", "SUBMIT", "--record", out])
        code, text = _run(["replay", out])
        self.assertEqual(code, 0)
        self.assertIn("@xstate.snapshot", text)
        self.assertIn("SUBMIT", text)
        code, _ = _run(["replay", out + ".nope"])
        self.assertEqual(code, 1)
        broken = os.path.join(self.tmp.name, "b.jsonl")
        pathlib.Path(broken).write_text("{not json\n", encoding="utf-8")
        code, _ = _run(["replay", broken])
        self.assertEqual(code, 1)

    def test_replay_live_streams_the_recording(self) -> None:
        out = os.path.join(self.tmp.name, "s.jsonl")
        _run(["sim", str(PAYMENT), "-e", "SUBMIT", "--record", out])
        n = len(pathlib.Path(out).read_text("utf-8").splitlines())
        got = {}
        stop = threading.Event()

        def ready(sink):
            got["sink"] = sink

        t = threading.Thread(
            target=run_replay,
            args=(out,),
            kwargs=dict(live=True, port=0, stop=stop, on_ready=ready),
            daemon=True,
        )
        t.start()
        for _ in range(200):
            if "sink" in got and len(got["sink"].messages) == n:
                break
            threading.Event().wait(0.01)
        status, msgs = _messages(got["sink"])
        stop.set()
        t.join(5)
        self.assertEqual(status, 200)
        self.assertEqual(len(msgs), n)


class TestInspectLive(_Base):
    def test_live_serves_the_scripted_session(self) -> None:
        got = {}
        stop = threading.Event()
        t = threading.Thread(
            target=run_inspect_live,
            args=(str(PAYMENT),),
            kwargs=dict(
                port=0,
                events="SUBMIT",
                stop=stop,
                on_ready=lambda s: got.setdefault("sink", s),
            ),
            daemon=True,
        )
        t.start()
        for _ in range(300):
            sink = got.get("sink")
            if sink and any(
                (m.get("event") or {}).get("type") == "SUBMIT"
                for m in sink.messages
            ):
                break
            threading.Event().wait(0.01)
        status, msgs = _messages(got["sink"])
        stop.set()
        t.join(5)
        self.assertEqual(status, 200)
        kinds = [m["type"] for m in msgs]
        self.assertEqual(kinds[0], "@xstate.actor")
        self.assertIn("@xstate.snapshot", kinds)
        self.assertFalse(t.is_alive())
        self.assertEqual(plugins.global_plugins(), [])

    def test_public_host_without_token_is_refused(self) -> None:
        code, _ = _run(
            ["inspect", str(PAYMENT), "--live", "--host", "0.0.0.0"]
        )
        self.assertEqual(code, 2)

    def test_cli_live_with_duration(self) -> None:
        code, text = _run(
            [
                "inspect",
                str(PAYMENT),
                "--live",
                "--port",
                "0",
                "-e",
                "SUBMIT",
                "--duration",
                "0.05",
            ]
        )
        self.assertEqual(code, 0)
        self.assertIn("http://127.0.0.1:", text)
        self.assertIn("?token=", text)

    def test_replay_live_cli_with_duration(self) -> None:
        out = os.path.join(self.tmp.name, "s.jsonl")
        _run(["sim", str(PAYMENT), "-e", "SUBMIT", "--record", out])
        code, text = _run(
            ["replay", out, "--live", "--port", "0", "--duration", "0.05"]
        )
        self.assertEqual(code, 0)
        self.assertIn("replayed", text)


if __name__ == "__main__":
    unittest.main()
