# examples/integrations/agents_support_bot/tests/test_readme_commands.py
"""The README's commands, run literally from a copy of this folder.

The copy lives under a path with a space and non-ASCII characters and
the child runs on a cp1252 console (``PYTHONUTF8=0``), the way a
Windows newcomer runs it.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

import pytest

pytest.importorskip("pydantic")

HERE = Path(__file__).resolve().parents[1]
README = (HERE / "README.md").read_text(encoding="utf-8")


def _readme_runs() -> List[str]:
    return re.findall(r"^python run\.py [^\n#]+", README, re.M)


def _env(**extra: str) -> Dict[str, str]:
    env = dict(os.environ)
    env.update(PYTHONUTF8="0", PYTHONIOENCODING="cp1252", **extra)
    for var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        env.pop(var, None)
    import xstate_statemachine

    src = str(Path(xstate_statemachine.__file__).resolve().parents[1])
    env["PYTHONPATH"] = os.pathsep.join(
        p for p in (src, env.get("PYTHONPATH", "")) if p
    )
    return env


@pytest.fixture()
def copy(tmp_path: Path) -> Path:
    dst = tmp_path / "my bots é" / "agents_support_bot"
    shutil.copytree(
        HERE, dst, ignore=shutil.ignore_patterns("__pycache__", "*.db*")
    )
    return dst


def _run(cwd: Path, cmd: str) -> subprocess.CompletedProcess:
    argv = [sys.executable] + _shlex(cmd)[1:]
    return subprocess.run(
        argv,
        cwd=cwd,
        env=_env(),
        capture_output=True,
        text=True,
        encoding="cp1252",
        errors="replace",
        timeout=120,
    )


def _shlex(cmd: str) -> List[str]:
    import shlex

    return shlex.split(cmd.strip())


def test_readme_lists_the_fake_and_provider_runs():
    runs = _readme_runs()
    assert any("--fake" in r for r in runs)
    assert any("--provider openai" in r for r in runs)


def test_fake_walkthrough_matches_the_readme_transcript(copy):
    cmd = next(r for r in _readme_runs() if "--fake" in r)
    res = _run(copy, cmd)
    assert res.returncode == 0, res.stderr
    shown = re.search(r"```text\n(.*?)```", README, re.S).group(1)
    # 📝 ticket ids and FakeModel call ids (unique per instance since
    #    #287) differ run to run; everything else is byte-for-byte
    norm = re.compile(r"ticket:[0-9a-f]{8}|call_[0-9a-f]{8}_")
    assert norm.sub("T", res.stdout) == norm.sub("T", shown)
    assert (copy / "support.db").exists()


def test_fake_run_is_deterministic(copy):
    cmd = next(r for r in _readme_runs() if "--fake" in r)
    norm = re.compile(r"ticket:[0-9a-f]{8}|call_[0-9a-f]{8}_")
    a, b = (norm.sub("T", _run(copy, cmd).stdout) for _ in range(2))
    assert a == b


def test_reject_never_claims_a_refund(copy):
    res = _run(copy, 'python run.py --fake --prompt "refund order 7" --reject')
    assert res.returncode == 0, res.stderr
    assert "refunds executed: []" in res.stdout
    assert "has been refunded" not in res.stdout
    assert "declined" in res.stdout


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_real_model_without_a_key_is_one_clear_line(copy, provider):
    res = _run(copy, f'python run.py --provider {provider} --prompt "hi"')
    assert res.returncode == 2
    assert "Traceback" not in res.stderr
    assert "--fake" in res.stderr or "pip install" in res.stderr
    assert not (copy / "support.db").exists()  # no ticket started


def test_gitignore_covers_what_run_py_writes(copy):
    ignored = (HERE / ".gitignore").read_text(encoding="utf-8").split()
    _run(copy, next(r for r in _readme_runs() if "--fake" in r))
    made = {
        p.name
        for p in copy.iterdir()
        if p.is_file() and not (HERE / p.name).exists()
    }
    assert made and made <= set(ignored)


# -----------------------------------------------------------------------------
# 🛠️ "Operate it": the ops day, literally, in separate processes
# -----------------------------------------------------------------------------
def _ops_block() -> List[str]:
    sec = README.split("## Operate it", 1)[1]
    cmds = re.search(r"```bash\n(.*?)```", sec, re.S).group(1)
    return [c for c in cmds.splitlines() if c.startswith("python ops.py")]


def test_operate_it_commands_match_the_transcript(copy):
    # Arrange
    cmds = _ops_block()
    assert cmds, "README lost its Operate it commands"
    shown = re.search(
        r"```text\n(.*?)```", README.split("## Operate it", 1)[1], re.S
    ).group(1)

    # Act: every command is its own process on the same support.db
    outs, codes = [], []
    for cmd in cmds:
        res = _run(copy, cmd)
        assert "Traceback" not in res.stderr, (cmd, res.stderr)
        codes.append(res.returncode)
        outs.append(res.stdout + res.stderr)

    # Assert: transcript as shown, the double approval refused (exit 2)
    assert "".join(outs) == shown
    assert codes == [0, 0, 0, 0, 2, 0, 0]
