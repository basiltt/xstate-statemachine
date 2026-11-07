"""Configure the example project for pytest (settings via pytest-django),
and skip the suite cleanly unless [django] + [drf] + [channels] (and the
test helpers pytest-django, drf-spectacular, daphne) are installed."""

import os
import sys
from pathlib import Path

import pytest

for mod in (
    "django",
    "rest_framework",
    "drf_spectacular",
    "channels",
    "daphne",
    "pytest_django",
):
    pytest.importorskip(mod)

EXAMPLE_DIR = str(Path(__file__).resolve().parents[1])
if EXAMPLE_DIR not in sys.path:
    sys.path.insert(0, EXAMPLE_DIR)

from django.conf import settings as _settings  # noqa: E402

if _settings.configured and getattr(_settings, "ROOT_URLCONF", None) != (
    "config.urls"
):
    # 📝 Django configures ONE project per process. Collected in the same
    #    session as the library's test project (tests/contrib/django), this
    #    suite cannot run here; `tests/test_examples_integrations.py` runs
    #    it in its own subprocess.
    collect_ignore_glob = ["test_*.py"]
else:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    import django  # noqa: E402

    django.setup()

    def pytest_sessionfinish(session, exitstatus):
        """🧹 #286-a: remove the SQLite test database Django could not.

        On Windows, a connection a worker thread opened (the concurrency
        tests) can still hold the file when pytest-django tears the test
        database down: Django warns ``PermissionError(13 ...)`` and the
        example folder keeps ``approvals.sqlite3.test`` -- hidden by
        ``.gitignore``, but a newcomer's ``ls`` shows it. By session end
        those threads are gone; collect their connections and retry.

        🐛 #591: they are NOT gone when this hook runs. Channels'
        ``database_sync_to_async`` runs the consumer's DB work in
        asgiref's single-thread executor, and that connection survives
        until interpreter shutdown -- after this hook, so the retry could
        never win (measured: the thread is still alive after 150 tries).
        Django's connection handler is per-thread, so a ``close_all()``
        from HERE cannot reach it; submitting the call to that executor
        puts it in the thread that owns the handle.
        """
        import gc
        import time

        test_db = _settings.DATABASES["default"].get("TEST", {}).get("NAME")
        if (
            not test_db
            or "sqlite" not in _settings.DATABASES["default"]["ENGINE"]
        ):
            return
        _close_worker_connections()
        for suffix in ("", "-wal", "-shm", "-journal"):
            path = Path(f"{test_db}{suffix}")
            for _ in range(50):
                if not path.exists():
                    break
                gc.collect()
                try:
                    path.unlink()
                except PermissionError:
                    time.sleep(0.1)


def _close_worker_connections() -> None:
    """Close Django connections in the threads that own them.

    Runs ``connections.close_all()`` in the main thread and inside
    asgiref's single-thread executor (see `pytest_sessionfinish`).
    Best-effort: a run must never fail because the cleanup could not
    reach a thread.
    """
    try:
        from asgiref.sync import SyncToAsync
        from django.db import connections

        connections.close_all()
        SyncToAsync.single_thread_executor.submit(
            connections.close_all
        ).result(timeout=10)
    except Exception:  # noqa: BLE001 - cleanup is best-effort
        pass
