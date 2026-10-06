# examples/integrations/fastapi_orders/tests/test_battle_277_readme.py
"""#277-b: every Python-side command in the README, executed.

* ``python app.py --role init`` then ``uvicorn app:app --workers 4`` and
  the ``curl`` walkthrough (as httpx) -- every state / flag the README's
  comments claim.
* ``python app.py --role scheduler`` starts, scans and stops on signal.
* ``xsm simulate machine.json --events ADD_ITEM,CHECKOUT,PAY --json``
  prints ``"value": "paid"``.
* ``python loadtest.py --json`` prints machine-readable rows including
  the conflict-retry count.
* The Dockerfile copies every module ``app.py`` imports; the compose file
  wires the env var ``app.py`` reads and runs ONE scheduler.

Process-spawning tests skip (with a reason) when ``uvicorn`` is absent.
"""

from __future__ import annotations

import ast
import json
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[2]
README = (HERE / "README.md").read_text(encoding="utf-8")

try:
    import uvicorn  # noqa: F401

    HAS_UVICORN = True
except ImportError:  # pragma: no cover - depends on the CI cell
    HAS_UVICORN = False

needs_uvicorn = pytest.mark.skipif(
    not HAS_UVICORN,
    reason="uvicorn not installed: the README's multi-worker commands "
    "need a real server (pip install uvicorn)",
)
# see test_battle_277_fleet.WINDOWS_UVICORN_STALL: a burst at N Windows
# workers can park one request on a frozen accept() -- not ours
windows_multiworker_stall = pytest.mark.skipif(
    sys.platform == "win32",
    reason="uvicorn --workers N on Windows: shared-socket accept() stall",
)


def _env(tmp_path: Path) -> dict:
    env = dict(os.environ)
    env.pop("XSM_REDIS_URL", None)
    env["XSM_ORDERS_DB"] = str(tmp_path / "orders.db")
    env["PYTHONUTF8"] = "1"
    env["PYTHONPATH"] = os.pathsep.join(
        [str(ROOT / "src")] + [p for p in [env.get("PYTHONPATH")] if p]
    )
    return env


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _stop(proc: subprocess.Popen) -> None:
    proc.terminate()
    try:
        proc.wait(20)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(10)


# -----------------------------------------------------------------------------
# 📜 The README still says what this file tests
# -----------------------------------------------------------------------------
def test_readme_lists_the_commands_tested_here():
    for cmd in (
        "python app.py --role init",
        "uvicorn app:app --port 8000 --workers 4",
        "python app.py --role scheduler",
        "xsm simulate machine.json --events ADD_ITEM,CHECKOUT,PAY --json",
        "python loadtest.py --workers 4 --requests 200",
    ):
        assert cmd in README, cmd


def test_xsm_simulate_reaches_paid():
    out = subprocess.run(
        [
            sys.executable,
            "-c",
            "from xstate_statemachine.cli.__main__ import main; main()",
            "simulate",
            "machine.json",
            "--events",
            "ADD_ITEM,CHECKOUT,PAY",
            "--json",
        ],
        cwd=str(HERE),
        env=_env(HERE),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert out.returncode == 0, out.stderr
    assert json.loads(out.stdout)["value"] == "paid"


# -----------------------------------------------------------------------------
# 🌐 init + 4 workers + the curl walkthrough
# -----------------------------------------------------------------------------
@windows_multiworker_stall
@needs_uvicorn
def test_init_then_four_workers_then_the_walkthrough(tmp_path):
    import httpx

    env = _env(tmp_path)
    init = subprocess.run(
        [sys.executable, "app.py", "--role", "init"],
        cwd=str(HERE),
        env=env,
        timeout=120,
    )
    assert init.returncode == 0
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app:app", "--port", str(port)]
        + ["--workers", "4"],
        cwd=str(HERE),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        base = f"http://127.0.0.1:{port}"
        with httpx.Client(base_url=base, timeout=30) as c:
            deadline = time.monotonic() + 90
            while True:
                try:
                    if c.get("/_xsm/ready").status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                assert time.monotonic() < deadline, "server never ready"
                time.sleep(0.3)
            _walkthrough(c)
    finally:
        _stop(proc)


def _walkthrough(c) -> None:
    h = {"x-customer": "ann"}
    key = dict(h, **{"Idempotency-Key": "pay-o1-1"})
    pay = {"card_token": "tok_ok"}

    def post(path, json=None, headers=h):
        r = c.post(f"/orders/o1{path}", json=json, headers=headers)
        assert r.status_code == 200, (path, r.status_code, r.text)
        return r.json()

    post("/events/ADD_ITEM", {"sku": "tea", "qty": 2})
    post("/events/CHECKOUT")
    first = post("/events/PAY", pay, key)
    assert first["changed"] is True
    again = post("/events/PAY", pay, key)
    assert again["duplicate"] is True
    assert again["changed"] is True  # the ORIGINAL receipt
    nokey = post("/events/PAY", pay)
    assert nokey["changed"] is False
    got = c.get("/orders/o1", headers=h).json()
    assert got["state"] == "paid"
    assert got["available_events"] == ["FULFIL"]
    post("/send", {"type": "FULFIL"})
    post("/events/PACKED")
    assert post("/events/LABEL_PRINTED")["state"] == "shipped"
    # PAY is refused on the generic /send route (README "Side effects")
    r = c.post("/orders/o2/send", json={"type": "PAY"}, headers=h)
    assert r.status_code >= 400
    # SSE: the first frame is a snapshot
    with c.stream("GET", "/orders/o1/stream", headers=h) as s:
        assert s.headers["x-accel-buffering"] == "no"
        for line in s.iter_lines():
            if line.startswith("event:"):
                assert line.split(":", 1)[1].strip() == "snapshot"
                break


@needs_uvicorn
def test_scheduler_role_starts_and_stops(tmp_path):
    env = _env(tmp_path)
    subprocess.run(
        [sys.executable, "app.py", "--role", "init"],
        cwd=str(HERE),
        env=env,
        timeout=120,
        check=True,
    )
    proc = subprocess.Popen(
        [sys.executable, "app.py", "--role", "scheduler"],
        cwd=str(HERE),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    time.sleep(4)
    assert proc.poll() is None, proc.stdout.read()
    _stop(proc)


@windows_multiworker_stall
@needs_uvicorn
def test_loadtest_json_reports_conflict_retries():
    out = subprocess.run(
        [sys.executable, "loadtest.py", "--workers", "2"]
        + ["--requests", "40", "--json"],
        cwd=str(HERE),
        env=_env(HERE),
        capture_output=True,
        text=True,
        timeout=400,
    )
    assert out.returncode == 0, out.stdout + out.stderr
    data = json.loads(out.stdout)
    assert data["ok"] is True
    for row in data["rows"]:
        assert row["changed"] == 1
        assert row["final"] == "paid"
        assert row["conflict_retries"] == row["409"]
        assert row["p95_ms"] >= row["p50_ms"]


# -----------------------------------------------------------------------------
# 🐳 Dockerfile / compose, statically
# -----------------------------------------------------------------------------
def _local_imports() -> set:
    tree = ast.parse((HERE / "app.py").read_text(encoding="utf-8"))
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module.split(".")[0])
        elif isinstance(node, ast.Import):
            mods.update(a.name.split(".")[0] for a in node.names)
    return {m for m in mods if (HERE / f"{m}.py").is_file()}


def test_dockerfile_copies_every_module_app_imports():
    docker = (HERE / "Dockerfile").read_text(encoding="utf-8")
    for mod in _local_imports() | {"app"}:
        assert f"fastapi_orders/{mod}.py" in docker, mod
    for chart in ("machine.json", "machine_v2.json"):
        assert f"fastapi_orders/{chart}" in docker, chart
    extras = re.search(r'pip install "\.\[([^\]]+)\]"', docker).group(1)
    assert {"fastapi", "redis"} <= set(extras.split(","))
    assert "/_xsm/ready" in docker


def test_compose_one_scheduler_and_the_env_var_app_reads():
    yaml = pytest.importorskip("yaml")
    doc = yaml.safe_load(
        (HERE / "docker-compose.yml").read_text(encoding="utf-8")
    )
    app_src = (HERE / "app.py").read_text(encoding="utf-8")
    svcs = doc["services"]
    for name in ("web", "scheduler"):
        env = svcs[name]["environment"]
        assert "XSM_REDIS_URL" in env and "XSM_REDIS_URL" in app_src
    assert svcs["scheduler"]["deploy"]["replicas"] == 1
    assert svcs["scheduler"]["command"][-2:] == ["--role", "scheduler"]
    assert "8000:8000" in svcs["web"]["ports"]


def test_loadtest_redis_flag_reaches_the_workers(monkeypatch, tmp_path):
    """Before #277-b the launcher popped XSM_REDIS_URL, so the README's
    "Redis" load test silently ran SQLite."""
    import argparse

    import loadtest

    seen = []

    class Stop(Exception):
        pass

    def fake_run(cmd, **kw):
        seen.append(kw["env"])

    def fake_start(port, workers, env):
        seen.append(env)
        raise Stop

    monkeypatch.setattr(loadtest.subprocess, "run", fake_run)
    monkeypatch.setattr(loadtest, "start_server", fake_start)
    monkeypatch.setenv("XSM_REDIS_URL", "redis://stray:1/0")
    for redis, want in (
        (None, None),
        ("redis://h:6379/3", "redis://h:6379/3"),
    ):
        seen.clear()
        args = argparse.Namespace(workers=1, requests=1, redis=redis)
        with pytest.raises(Stop):
            loadtest.run_all(args, 1, "http://x", str(tmp_path))
        assert [e.get("XSM_REDIS_URL") for e in seen] == [want, want]
