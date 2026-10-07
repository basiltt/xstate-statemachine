"""battle #285-b: every command in the README's "Run it" block, run
literally in a subprocess from a temporary COPY of the example.

`flask --app app run` is started in the background on a free port, read
over HTTP with httpx, and killed. Skips cleanly when httpx is missing or
no local port can be bound.
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List

import pytest

pytest.importorskip("flask")

HERE = Path(__file__).resolve().parents[1]
SRC = Path(__file__).resolve().parents[4] / "src"
README = HERE / "README.md"

if "cd examples/integrations/flask_wizard" not in README.read_text("utf-8"):
    # 📝 `xsm new --template flask` copies this file into a scaffold whose
    #    README is the scaffold's own; the commands tested here are the
    #    in-repo example's.
    pytest.skip("not the in-repo example", allow_module_level=True)


def _run_it_block() -> List[str]:
    text = README.read_text("utf-8")
    m = re.search(r"## Run it\s+```bash\n(.*?)```", text, re.S)
    assert m, "README has no 'Run it' bash block"
    cmds = []
    for line in m.group(1).splitlines():
        cmd = line.split("#", 1)[0].strip()
        if cmd:
            cmds.append(cmd)
    return cmds


def _env(copy: Path) -> Dict[str, str]:
    env = {**os.environ, "PYTHONUTF8": "1"}
    env["PYTHONPATH"] = os.pathsep.join([str(SRC), str(copy)])
    for k in ("WIZARD_STORE", "WIZARD_DB", "FLASK_APP", "FLASK_RUN_PORT"):
        env.pop(k, None)
    return env


@pytest.fixture
def copy(tmp_path: Path) -> Path:
    dst = tmp_path / "flask_wizard"
    shutil.copytree(
        HERE,
        dst,
        ignore=shutil.ignore_patterns("__pycache__", "*.db", ".pytest_cache"),
    )
    return dst


def _split(cmd: str) -> tuple:
    """``VAR=x prog args`` -> ({VAR: x}, [prog, args]); `flask` and
    `python` resolve to this interpreter (no PATH assumptions)."""
    parts = shlex.split(cmd)
    env = {}
    while parts and re.match(r"^[A-Z_]+=", parts[0]):
        k, v = parts.pop(0).split("=", 1)
        env[k] = v
    if parts[0] == "flask":
        parts = [sys.executable, "-m", "flask"] + parts[1:]
    elif parts[0] == "python":
        parts = [sys.executable] + parts[1:]
    return env, parts


def _free_port() -> int:
    try:
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            return int(s.getsockname()[1])
    except OSError as exc:  # pragma: no cover - sandboxed CI
        pytest.skip(f"cannot bind a local port: {exc}")


def test_run_it_block_is_what_we_test() -> None:
    cmds = _run_it_block()
    assert cmds[0].startswith("pip install")
    assert cmds[1] == "cd examples/integrations/flask_wizard"
    assert "flask --app app run" in cmds
    assert "WIZARD_STORE=sqlite flask --app app run" in cmds
    assert "flask --app app xsm inspect wizard" in cmds
    assert "python -m pytest tests -q" in cmds


@pytest.mark.parametrize(
    "cmd",
    [c for c in _run_it_block() if c.endswith("flask --app app run")],
)
def test_flask_run_serves_the_wizard(copy: Path, cmd: str) -> None:
    httpx = pytest.importorskip("httpx")
    extra, argv = _split(cmd)
    if extra.get("WIZARD_STORE") == "sqlalchemy":
        pytest.importorskip("sqlalchemy")
    port = _free_port()
    env = {**_env(copy), **extra}
    proc = subprocess.Popen(
        argv + ["--port", str(port)],
        cwd=copy,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        url = f"http://127.0.0.1:{port}/"
        deadline = time.monotonic() + 30
        while True:
            try:
                with httpx.Client() as c:
                    r = c.get(url, timeout=2)
                    assert r.status_code == 200, r.text[:500]
                    assert 'data-step="account"' in r.text
                    assert 'name="step" value="account"' in r.text
                    assert 'name="csrf_token"' in r.text
                    # A POST without the CSRF token is refused (CSRF on).
                    assert c.post(url + "next", data={}).status_code == 400
                break
            except httpx.TransportError:
                if proc.poll() is not None or time.monotonic() > deadline:
                    out = proc.stdout.read().decode() if proc.stdout else ""
                    pytest.fail(f"{cmd!r} never served: {out[-2000:]}")
                time.sleep(0.2)
    finally:
        proc.kill()
        proc.wait(timeout=10)
    if extra.get("WIZARD_STORE"):
        assert (copy / "wizard.db").exists()  # the documented file


def test_flask_xsm_inspect(copy: Path) -> None:
    _, argv = _split("flask --app app xsm inspect wizard")
    p = subprocess.run(
        argv + ["--plain"],
        cwd=copy,
        env=_env(copy),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert p.returncode == 0, p.stdout + p.stderr
    for step in ("account", "profile", "plan", "confirm", "done"):
        assert step in p.stdout


def test_python_m_pytest_tests(copy: Path) -> None:
    _, argv = _split("python -m pytest tests -q")
    p = subprocess.run(
        argv
        + ["-p", "no:cacheprovider", "-o", "addopts=", "--rootdir", str(copy)]
        + ["-k", "not test_readme_commands"],
        cwd=copy,
        env=_env(copy),
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert p.returncode == 0, p.stdout[-3000:] + p.stderr[-2000:]
    assert " passed" in p.stdout
