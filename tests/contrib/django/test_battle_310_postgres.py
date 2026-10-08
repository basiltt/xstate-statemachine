# tests/contrib/django/test_battle_310_postgres.py
"""#310 battle: the migrate-fsm scenario on a REAL Postgres.

The library's test project honours ``DATABASE_URL``; this driver runs the
scenario (and the existing migrate tests) in a subprocess against yours
or a throwaway testcontainer (``XSM_CONTAINERS=1`` + Docker + psycopg).
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


def _pg_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if url.startswith("postgres"):
        return url
    if os.environ.get("XSM_CONTAINERS") != "1":
        pytest.skip("no Postgres: set DATABASE_URL or XSM_CONTAINERS=1")
    pytest.importorskip("psycopg")
    return ""


def test_migrate_fsm_scenario_on_postgres() -> None:
    pytest.importorskip("django_fsm")
    pytest.importorskip("pytest_django")
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
    env.pop("XSM_CONTAINERS", None)
    env.update(DATABASE_URL=url, PYTHONUTF8="1")
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/contrib/django/test_battle_310_scenario.py",
            "tests/contrib/django/test_migrate_fsm.py",
            "-q",
            "-p",
            "no:cacheprovider",
        ],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=1500,
    )
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-1500:]
    assert "passed" in proc.stdout
