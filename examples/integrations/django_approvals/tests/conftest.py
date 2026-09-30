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
