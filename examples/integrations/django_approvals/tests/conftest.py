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
        """
        import gc
        import time

        test_db = _settings.DATABASES["default"].get("TEST", {}).get("NAME")
        if (
            not test_db
            or "sqlite" not in _settings.DATABASES["default"]["ENGINE"]
        ):
            return
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
