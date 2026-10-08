"""#280 battle: every command of the README's "Run it" block, run
literally from a fresh copy of the example (its own SQLite file, or the
``DATABASE_URL`` Postgres when set).

``pip install`` and ``cd`` are skipped (the environment is the test's);
``runserver`` and ``xsm_deadlines --forever`` are started in the
background, probed, and stopped; ``python -m pytest tests`` is not
re-entered (this IS that suite).
"""

import os
import re
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

EXAMPLE = Path(__file__).resolve().parents[1]
ROOT = EXAMPLE.parents[2]

pytestmark = pytest.mark.timeout(600)


def _commands():
    text = (EXAMPLE / "README.md").read_text(encoding="utf-8")
    block = re.search(r"## Run it\s+```bash\n(.*?)```", text, re.S).group(1)
    cmds = []
    for line in block.splitlines():
        line = line.split("  #", 1)[0].strip()
        if line:
            cmds.append(line)
    return cmds


def _split(cmd):
    """``A=1 B=2 python manage.py ...`` -> (env, argv)."""
    parts = shlex.split(cmd)
    env = {}
    while parts and re.match(r"^[A-Z_]+=", parts[0]):
        k, v = parts.pop(0).split("=", 1)
        env[k] = v
    return env, parts


@pytest.fixture(scope="module")
def copy(tmp_path_factory):
    dst = tmp_path_factory.mktemp("approvals") / "django_approvals"
    shutil.copytree(
        EXAMPLE,
        dst,
        ignore=shutil.ignore_patterns(
            "*.sqlite3*", "__pycache__", ".pytest_cache"
        ),
    )
    return dst


def _env(extra):
    env = dict(os.environ)
    env.pop("DJANGO_SETTINGS_MODULE", None)
    env.pop("APPROVALS_DB", None)
    env["PYTHONUTF8"] = "1"
    env["PYTHONPATH"] = os.pathsep.join(
        [str(ROOT / "src"), env.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)
    env.update(extra)
    return env


def _argv(parts):
    assert parts[0] == "python", parts
    return [sys.executable, *parts[1:]]


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _stop(proc):
    if sys.platform == "win32":
        proc.send_signal(signal.CTRL_BREAK_EVENT)
    else:
        proc.send_signal(signal.SIGINT)
    try:
        return proc.communicate(timeout=30)
    except subprocess.TimeoutExpired:  # pragma: no cover
        proc.kill()
        return proc.communicate()


def _background(argv, cwd, env):
    flags = (
        subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    )
    return subprocess.Popen(
        argv,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=flags,
    )


def test_readme_has_the_commands_this_test_runs():
    cmds = " | ".join(_commands())
    for needle in (
        "manage.py migrate",
        "createsuperuser --noinput",
        "manage.py runserver",
        "xsm_deadlines --forever",
        "xsm_inspect approvals.Expense",
        "xsm_diagram approvals.Expense -f mermaid",
        "xsm_snapshots approvals.Expense",
        "xsm_refresh_columns approvals.Expense --dry-run",
        "manage.py relay_outbox",
        "python -m pytest tests",
    ):
        assert needle in cmds, needle
    text = (EXAMPLE / "README.md").read_text(encoding="utf-8")
    assert "DATABASE_URL=postgresql://" in text
    assert "## What it does not do" in text


def test_run_it_literally(copy):
    httpx = pytest.importorskip("httpx")
    ran = []
    for cmd in _commands():
        extra, parts = _split(cmd)
        env = _env(extra)
        if parts[0] in ("pip", "cd") or parts[:3] == [
            "python",
            "-m",
            "pytest",
        ]:
            continue
        if "runserver" in parts:
            port = _free_port()
            argv = _argv(parts[:-1] + [f"127.0.0.1:{port}", "--noreload"])
            proc = _background(argv, copy, env)
            try:
                body = _wait_for_login(httpx, port, proc)
            finally:
                _stop(proc)
            assert 'name="username"' in body and "csrfmiddlewaretoken" in body
            ran.append("runserver")
            continue
        if "--forever" in parts:
            proc = _background(_argv(parts), copy, env)
            time.sleep(4)
            assert proc.poll() is None, proc.communicate()
            out, err = _stop(proc)
            assert b"Traceback" not in err, err.decode(errors="replace")
            ran.append("forever")
            continue
        p = subprocess.run(
            _argv(parts), cwd=copy, env=env, capture_output=True, timeout=300
        )
        assert p.returncode == 0, (cmd, p.stdout, p.stderr)
        assert b"Traceback" not in p.stderr, (cmd, p.stderr)
        _check_output(parts[2], p.stdout.decode("utf-8", "replace"))
        ran.append(parts[2])
    assert ran.count("xsm_deadlines") == 1 and "forever" in ran
    assert {
        "migrate",
        "createsuperuser",
        "xsm_inspect",
        "xsm_diagram",
        "xsm_snapshots",
        "xsm_refresh_columns",
        "relay_outbox",
        "runserver",
    } <= set(ran)
    _superuser_can_log_in(copy)


_ANSI = re.compile("\x1b\\[[0-9;]*m")


def _check_output(cmd, out):
    """#282 battle B: each README command prints what the README says.
    CI exports FORCE_COLOR=1, so piped output may carry ANSI colour."""
    out = _ANSI.sub("", out)
    if cmd == "xsm_diagram":
        assert out.lstrip().startswith("stateDiagram"), out[:200]
    elif cmd == "xsm_snapshots":
        assert out.startswith("approvals.Expense snapshots"), out[:200]
    elif cmd == "xsm_refresh_columns":
        assert "approvals.Expense: would change" in out, out


def _wait_for_login(httpx, port, proc):
    url = f"http://127.0.0.1:{port}/admin/login/"
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise AssertionError(proc.communicate())
        try:
            r = httpx.get(url, timeout=5)
        except httpx.HTTPError:
            time.sleep(0.5)
            continue
        assert r.status_code == 200, r.status_code
        return r.text
    raise AssertionError("runserver did not answer")


def _superuser_can_log_in(copy):
    code = (
        "from django.contrib.auth import authenticate;"
        "u = authenticate(username='admin', password='change-me');"
        "assert u is not None and u.is_superuser; print('LOGIN OK')"
    )
    p = subprocess.run(
        [sys.executable, "manage.py", "shell", "-c", code],
        cwd=copy,
        env=_env({}),
        capture_output=True,
        timeout=120,
    )
    assert b"LOGIN OK" in p.stdout, p.stderr
