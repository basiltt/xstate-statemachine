# tests/test_examples_integrations.py
"""#277: smoke-test every `examples/integrations/*` app.

* Every ``machine.json`` passes ``xsm validate --plain`` (strict config)
  and builds with `stub_logic` -- no extra needed, default job.
* Every example with a ``tests/`` folder runs its own suite in a
  subprocess (the example dir on ``sys.path`` via its conftest). Each
  suite needs its own extra (`REQUIRES`) and skips cleanly without it;
  the matching contrib CI cell (``[fastapi]``, ``[sqlalchemy]``,
  ``[flask]``) runs it.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from src.xstate_statemachine import create_machine, stub_logic

ROOT = Path(__file__).resolve().parents[1]
INTEGRATIONS = ROOT / "examples" / "integrations"
MACHINES = sorted(INTEGRATIONS.glob("*/machine.json"))
SUITES = sorted(p.parent for p in INTEGRATIONS.glob("*/tests"))
#: #286: the importable modules each example suite needs; anything not
#: listed needs the web stack (the original #277 rule).
REQUIRES = {
    "sqlalchemy_orders": ("sqlalchemy", "alembic"),
    "flask_wizard": ("flask",),
    # 🦄 #280-#283: the Django app needs all three extras + test helpers.
    "django_approvals": (
        "django",
        "rest_framework",
        "drf_spectacular",
        "channels",
        "daphne",
        "pytest_django",
    ),
    # 📡 G2/G3/G7: the EDA core needs no extra. Every broker / Celery /
    #    observability test inside the app importorskips its own client,
    #    so a [kafka]-only cell runs the Kafka tests (and the core demo)
    #    and skips the rest -- never the whole suite.
    "eda_fulfilment": (),
}
DEFAULT_REQUIRES = ("fastapi", "httpx")


def _env() -> dict:
    env = dict(os.environ)
    # 📝 A Django test project configured earlier in this session (#280)
    #    sets DJANGO_SETTINGS_MODULE; each example suite is its own
    #    process and must pick its own settings.
    env.pop("DJANGO_SETTINGS_MODULE", None)
    src = str(ROOT / "src")
    env["PYTHONPATH"] = os.pathsep.join(
        [src, str(ROOT)] + [p for p in [env.get("PYTHONPATH")] if p]
    )
    return env


def test_there_are_integration_examples():
    assert MACHINES, "examples/integrations/*/machine.json disappeared"


def test_every_example_has_a_readme_and_a_suite():
    """#286: each app is documented and tested, not just a chart."""
    for name in (
        "fastapi_orders",
        "sqlalchemy_orders",
        "flask_wizard",
        "django_approvals",
        "eda_fulfilment",
    ):
        assert (INTEGRATIONS / name / "README.md").is_file(), name
        assert (INTEGRATIONS / name / "tests").is_dir(), name
    assert set(REQUIRES) <= {p.name for p in SUITES}


def test_sqlalchemy_orders_ships_its_alembic_migration():
    ex = INTEGRATIONS / "sqlalchemy_orders"
    assert (ex / "alembic.ini").is_file()
    assert sorted((ex / "migrations" / "versions").glob("0001_*.py"))
    readme = (ex / "README.md").read_text("utf-8")
    assert "alembic upgrade head" in readme
    assert "#293" in readme  # the outbox is not faked


@pytest.mark.parametrize("path", MACHINES, ids=lambda p: p.parent.name)
def test_machine_validates_plain(path):
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "xstate_statemachine",
            "validate",
            str(path),
            "--plain",
        ],
        capture_output=True,
        text=True,
        env=_env(),
        timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


@pytest.mark.parametrize("path", MACHINES, ids=lambda p: p.parent.name)
def test_machine_builds_with_stub_logic(path):
    cfg = json.loads(path.read_text("utf-8"))
    machine = create_machine(cfg, logic=stub_logic(cfg), strict_config=True)
    assert machine.id == cfg["id"]


@pytest.mark.parametrize("example", SUITES, ids=lambda p: p.name)
def test_example_suite_passes(example):
    for module in REQUIRES.get(example.name, DEFAULT_REQUIRES):
        pytest.importorskip(module)
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(example / "tests"),
            "-q",
            "-p",
            "no:cacheprovider",
        ],
        cwd=str(example),
        capture_output=True,
        text=True,
        env=_env(),
        timeout=600,
    )
    assert proc.returncode == 0, proc.stdout[-4000:] + proc.stderr[-2000:]
