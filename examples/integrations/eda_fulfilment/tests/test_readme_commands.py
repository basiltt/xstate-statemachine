"""The README's Python blocks run, and ``python -m eda_fulfilment`` works."""

import json
import pytest
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[2]


def _python_blocks():
    text = (HERE / "README.md").read_text("utf-8")
    return re.findall(r"```python\n(.*?)```", text, flags=re.S)


def test_readme_python_blocks_run(monkeypatch, tmp_path):
    blocks = _python_blocks()
    assert blocks
    monkeypatch.chdir(tmp_path)
    for block in blocks:
        exec(compile(block, "README.md", "exec"), {})  # noqa: S102


def test_readme_links_every_guide_page():
    # 📝 Absolute docs-site URLs: the README is read on GitHub, on PyPI
    #    and from a copied-out folder, where ``../../../docs`` is gone.
    text = (HERE / "README.md").read_text("utf-8")
    assert "../../../docs" not in text
    docs = (HERE / "../../../docs/_guide").resolve()
    for page in ("eda", "brokers", "celery", "observability", "inspector"):
        url = (
            "https://basiltt.github.io/xstate-statemachine/guide/"
            f"integration-{page}/"
        )
        assert url in text, page
        if docs.is_dir():  # in the checkout: the page exists
            assert (docs / f"integration-{page}.md").is_file(), page


def test_python_dash_m_exits_zero():
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(ROOT / "src")] + [p for p in [env.get("PYTHONPATH")] if p]
    )
    proc = subprocess.run(
        [sys.executable, "-m", "eda_fulfilment"],
        cwd=str(HERE.parent),
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "order:o-1" in proc.stdout and "order.shipped" in proc.stdout
    assert "dead_letters           1" in proc.stdout


def _operate_commands():
    """The `xsm dlq` lines of the README's "Operate it" block, joined."""
    text = (HERE / "README.md").read_text("utf-8")
    section = text[text.index("## Operate it") :]
    block = re.search(r"```bash\n(.*?)```", section, flags=re.S).group(1)
    joined = re.sub(r"\\\n\s*", " ", block)
    lines = [ln.split("  #")[0].strip() for ln in joined.splitlines()]
    return [ln for ln in lines if ln.startswith("xsm dlq")]


def test_readme_operate_commands_work(fulfilment):
    # 🐛 #293 battle (B): the README showed no operator flow at all; the
    #    commands it now shows are exactly the ones run here.
    import shlex

    env_ = fulfilment.command("o-9", "PAYMENT_FAILED", reason=12345)
    fulfilment.pump()
    assert [r.id for r in fulfilment.dead_letters.list()] == [env_.id]
    db = f"sqlite:///{(fulfilment.workdir / 'state.db').as_posix()}"
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(ROOT / "src"), str(HERE)]
        + [p for p in [env.get("PYTHONPATH")] if p]
    )
    env["PYTHONUTF8"] = "1"
    commands = _operate_commands()
    assert len(commands) == 6, commands
    for line in commands:
        argv = shlex.split(line.replace("$DB", db).replace("<id>", env_.id))
        proc = subprocess.run(
            [sys.executable, "-m", "xstate_statemachine", "--plain"]
            + argv[1:],
            cwd=str(HERE),
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        out = proc.stdout + proc.stderr
        if "--no-dry-run" in argv:
            # still-poison data: the replay runs (the action's own error
            # is logged with its traceback), is not resolved, exit 1
            assert proc.returncode == 1, out
            assert "dead_lettered" in proc.stdout, out
        else:
            assert "Traceback" not in out, out
            assert proc.returncode == 0, (line, out)
        if "--json" in argv:
            assert json.loads(proc.stdout)["count"] == 1
    assert fulfilment.dead_letters.list() == []
