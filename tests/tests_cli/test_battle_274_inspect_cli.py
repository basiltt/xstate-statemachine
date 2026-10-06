"""battle #274 (adversary B): the `xsm` live-inspector CLI."""

import json
import os
import subprocess
import sys
import threading

import pytest

from xstate_statemachine.cli.commands.live import (
    recording_plugin,
    run_inspect_live,
    run_replay,
)
from xstate_statemachine.cli.commands.simulate import run_simulate
from xstate_statemachine.inspect import read_jsonl

MACHINE = {
    "id": "m",
    "initial": "a",
    "states": {"a": {"on": {"GO": "b"}}, "b": {}},
}
_MAIN = "from xstate_statemachine.cli.__main__ import main; main()"


@pytest.fixture
def machine(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps(MACHINE), encoding="utf-8")
    return str(p)


def _xsm(*args):
    env = dict(os.environ)
    src = os.path.join(os.path.dirname(__file__), "..", "..", "src")
    env["PYTHONPATH"] = os.path.abspath(src)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["NO_COLOR"] = "1"
    return subprocess.run(
        [sys.executable, "-c", _MAIN, *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


def test_record_refuses_to_append_silently(machine, tmp_path):
    out = str(tmp_path / "r.jsonl")
    run_simulate(machine, events="GO", record=out)
    first = len(list(read_jsonl(out)))
    assert first > 0
    with pytest.raises(SystemExit) as exc:
        run_simulate(machine, events="GO", record=out)
    assert exc.value.code == 2
    assert len(list(read_jsonl(out))) == first
    run_simulate(machine, events="GO", record=out, record_append=True)
    assert len(list(read_jsonl(out))) == 2 * first


def test_recording_plugin_allows_an_empty_existing_file(tmp_path):
    p = tmp_path / "r.jsonl"
    p.write_text("", encoding="utf-8")
    plugin, sink = recording_plugin(str(p))
    plugin.uninstall()
    sink.close()


def test_replay_negative_speed_exits_2(tmp_path):
    p = tmp_path / "r.jsonl"
    p.write_text("", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        run_replay(str(p), live=True, port=0, speed=-1)
    assert exc.value.code == 2


def test_replay_print_streams_then_fails_on_corrupt_middle(tmp_path):
    p = tmp_path / "r.jsonl"
    p.write_text(
        '{"type":"@xstate.event","event":{"type":"FIRST"}}\nbroken\n{}\n',
        encoding="utf-8",
    )
    r = _xsm("replay", str(p))
    assert r.returncode == 1 and "Traceback" not in r.stderr
    assert "FIRST" in r.stdout


def test_open_on_a_headless_box_does_not_kill_the_server(machine, monkeypatch):
    import webbrowser

    def boom(url):
        raise webbrowser.Error("no runnable browser")

    monkeypatch.setattr(webbrowser, "open", boom)
    seen = []
    stop = threading.Event()
    stop.set()
    run_inspect_live(
        machine,
        port=0,
        open_browser=True,
        events="GO",
        stop=stop,
        on_ready=seen.append,
    )
    assert seen and seen[0].url


def test_block_honours_duration_in_slices():
    import time

    from xstate_statemachine.cli.commands.live import _block

    t0 = time.monotonic()
    _block(None, 0.3)
    assert 0.25 <= time.monotonic() - t0 < 2


def test_cli_subprocess_exit_codes(machine, tmp_path):
    r = _xsm(
        "inspect", machine, "--live", "--host", "0.0.0.0",
        "-e", "GO", "--duration", "0",
    )  # fmt: skip
    assert r.returncode == 2 and "Traceback" not in r.stderr
    r = _xsm("replay", str(tmp_path / "missing.jsonl"))
    assert r.returncode == 1 and "Traceback" not in r.stderr
    out = str(tmp_path / "r.jsonl")
    assert _xsm("sim", machine, "-e", "GO", "--record", out).returncode == 0
    r = _xsm("sim", machine, "-e", "GO", "--record", out)
    assert r.returncode == 2 and "--append" in r.stdout + r.stderr
    r = _xsm("replay", out, "--live", "--port", "0", "--duration", "0")
    assert r.returncode == 0, r.stderr
    assert "replayed" in r.stdout + r.stderr


def test_help_mentions_cookie_and_loopback():
    text = " ".join(_xsm("inspect", "--help").stdout.split())
    assert "127.0.0.1" in text and "cookie" in text
    assert "--append" in _xsm("sim", "--help").stdout
