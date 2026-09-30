"""The README's Python blocks run, and ``python -m eda_fulfilment`` works."""

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
    text = (HERE / "README.md").read_text("utf-8")
    for page in ("eda", "brokers", "celery", "observability", "inspector"):
        target = f"../../../docs/_guide/integration-{page}.md"
        assert target in text, page
        assert (HERE / target).resolve().is_file(), page


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
