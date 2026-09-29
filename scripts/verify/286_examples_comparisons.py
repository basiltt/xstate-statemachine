"""Verification for #286 (D7): the sqlalchemy_orders and flask_wizard
example apps + the vs django-fsm / transitions / python-statemachine
comparison pages.

`python scripts/verify/286_examples_comparisons.py`.

Windows-safe (no heredocs, no /tmp: every database lives in a
``tempfile.mkdtemp()`` directory; subprocesses get ``sys.executable``).

* Both example suites and the smoke/data/docs tests pass.
* sqlalchemy_orders, run as its README says: ``alembic upgrade head`` on a
  fresh file, ``alembic check`` finds no diff, ``sync_app.py demo`` then
  ``scan --at-offset 901`` wakes exactly the unpaid order, and the async
  variant runs on the same file.
* flask_wizard: ``flask xsm inspect wizard --plain`` exits 0 and lists
  the steps; two test clients hold independent wizards.
* comparisons.json: three new entries, 15 rows each, every row sourced;
  every "theirs" fence is ``text``.

Prints ``ALL OK``.
"""

import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
from typing import Dict, List, Optional

ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "examples" / "integrations"
TMP = pathlib.Path(tempfile.mkdtemp(prefix="xsm-286-"))


def step(name: str) -> None:
    print(f"\n== {name}")


def env(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Child env that imports THIS checkout (worktrees share one venv)."""
    e = dict(os.environ)
    parts = [str(ROOT / "src"), str(ROOT)]
    if e.get("PYTHONPATH"):
        parts.append(e["PYTHONPATH"])
    e["PYTHONPATH"] = os.pathsep.join(parts)
    e["PYTHONIOENCODING"] = "utf-8"
    e.update(extra or {})
    return e


def run(args: List[str], cwd: pathlib.Path, **kw: str) -> str:
    proc = subprocess.run(
        [sys.executable, *args],
        cwd=str(cwd),
        env=env(kw or None),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=600,
    )
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, f"{args} failed:\n{out[-3000:]}"
    return out


def run_tests() -> None:
    step("pytest: example suites + smoke, comparison, docs tests")
    out = run(
        [
            "-m",
            "pytest",
            "tests/test_examples_integrations.py",
            "examples/integrations/sqlalchemy_orders/tests",
            "examples/integrations/flask_wizard/tests",
            "tests/test_comparisons.py",
            "tests/test_docs_site.py",
            "-q",
            "-p",
            "no:cacheprovider",
        ],
        ROOT,
    )
    print(out.strip().splitlines()[-1])


def sqlalchemy_orders() -> None:
    step("sqlalchemy_orders: alembic upgrade/check, demo, scan, async")
    ex = EXAMPLES / "sqlalchemy_orders"
    db = TMP / "orders.db"
    url = f"sqlite:///{db.as_posix()}"
    run(["-m", "alembic", "upgrade", "head"], ex, ORDERS_DB_URL=url)
    out = run(["-m", "alembic", "check"], ex, ORDERS_DB_URL=url)
    assert "No new upgrade operations detected" in out, out
    out = run(["sync_app.py", "demo", "--url", url], ex)
    assert "order 1: order.paid" in out, out
    assert "order 2: order.awaitingPayment" in out, out
    out = run(["sync_app.py", "scan", "--url", url], ex)
    assert "woke 0 order(s)" in out, out  # still inside the window
    out = run(["sync_app.py", "scan", "--url", url, "--at-offset", "901"], ex)
    assert "woke 1 order(s)" in out, out
    out = run(["async_app.py"], ex, ORDERS_DB_PATH=str(db))
    assert "order-1: order.paid" in out, out
    print("   migrated, no drift; timeout fired once; async variant ran")


def flask_wizard() -> None:
    step("flask_wizard: flask xsm inspect wizard --plain")
    ex = EXAMPLES / "flask_wizard"
    out = run(
        ["-m", "flask", "--app", "app", "xsm", "inspect", "wizard", "--plain"],
        ex,
    )
    for s in ("account", "profile", "plan", "confirm", "done"):
        assert s in out, s
    code = (
        "import app\n"
        "a = app.create_app({'TESTING': True, 'WTF_CSRF_ENABLED': False,"
        " 'WIZARD_STORE': 'sqlite', 'WIZARD_DB': %r})\n"
        "c1, c2 = a.test_client(), a.test_client()\n"
        "c1.post('/next', data={'name': 'Ada', 'email': 'a@x.io'})\n"
        "s = lambda c: c.get('/').get_data(as_text=True)\n"
        "assert 'data-step=\"profile\"' in s(c1)\n"
        "assert 'data-step=\"account\"' in s(c2)\n"
        "print('independent')\n" % str(TMP / "wizard.db")
    )
    out = run(["-c", code], ex)
    assert "independent" in out, out
    print("   CLI inspect OK; two sessions, two wizards")


def comparisons() -> None:
    step("comparisons.json + pages")
    data = json.loads(
        (ROOT / "docs" / "_data" / "comparisons.json").read_text("utf-8")
    )
    pages = {
        "django_fsm": "vs-django-fsm",
        "transitions": "vs-transitions",
        "python_statemachine": "vs-python-statemachine",
    }
    for key, slug in pages.items():
        rows = data[key]["rows"]
        assert len(rows) == 15, (key, len(rows))
        assert all(r["source"].strip() for r in rows), key
        text = (
            ROOT / "docs" / "_guide" / "comparisons" / f"{slug}.md"
        ).read_text("utf-8")
        theirs = text.split("### Theirs", 1)[1].split("### Ours", 1)[0]
        fences = re.findall(r"^```(\w*)", theirs, flags=re.M)
        assert fences and set(fences) <= {"text", ""}, (slug, fences)
        assert "```text" in theirs, slug
    # 📝 the pre-existing agent comparison data is untouched
    assert {"competitors", "rows"} <= set(data)
    print("   3 pages x 15 sourced rows; theirs fenced as text")


def main() -> None:
    run_tests()
    sqlalchemy_orders()
    flask_wizard()
    comparisons()
    print("\nALL OK")


if __name__ == "__main__":
    main()
