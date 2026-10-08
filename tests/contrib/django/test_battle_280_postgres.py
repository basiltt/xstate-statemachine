# tests/contrib/django/test_battle_280_postgres.py
"""#280 battle: the `django_approvals` scenario on a REAL Postgres.

Django configures one project per process, so the example suite runs in
a subprocess; this driver gives it a Postgres via `DATABASE_URL` (yours)
or a throwaway testcontainer (``XSM_CONTAINERS=1`` + Docker + psycopg).
Skipped otherwise. The SQLite run of the same tests happens through
`tests/test_examples_integrations.py`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from ..conftest import requires_extra

pytestmark = [requires_extra("django"), pytest.mark.timeout(1800)]

ROOT = Path(__file__).resolve().parents[3]
EXAMPLE = ROOT / "examples" / "integrations" / "django_approvals"


def _pg_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if url.startswith("postgres"):
        return url
    if os.environ.get("XSM_CONTAINERS") != "1":
        pytest.skip("no Postgres: set DATABASE_URL or XSM_CONTAINERS=1")
    pytest.importorskip("psycopg")
    return ""


def test_django_approvals_scenario_on_postgres() -> None:
    for mod in (
        "django",
        "rest_framework",
        "drf_spectacular",
        "channels",
        "daphne",
        "pytest_django",
    ):
        pytest.importorskip(mod)
    url = _pg_url()
    if url:
        _run(url)
        return
    tc = pytest.importorskip("testcontainers.postgres")
    with tc.PostgresContainer("postgres:16-alpine", driver="psycopg") as pg:
        _run(pg.get_connection_url().replace("+psycopg", ""))


def _run(url: str) -> None:
    env = dict(os.environ)
    env.pop("DJANGO_SETTINGS_MODULE", None)
    env.pop("XSM_CONTAINERS", None)  # the example must not start brokers
    env.update(
        DATABASE_URL=url,
        PYTHONUTF8="1",
        PYTHONPATH=os.pathsep.join(
            [str(ROOT / "src"), str(ROOT), env.get("PYTHONPATH", "")]
        ).rstrip(os.pathsep),
    )
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_battle_280_scenario.py",
            "tests/test_battle_281_scenario.py",
            "tests/test_battle_282_scenario.py",
            "tests/test_approvals.py",
            "-q",
            "-p",
            "no:cacheprovider",
            "-o",
            "addopts=",
        ],
        cwd=str(EXAMPLE),
        env=env,
        capture_output=True,
        text=True,
        timeout=1500,
    )
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-1500:]
    assert "passed" in proc.stdout
