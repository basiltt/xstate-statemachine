# tests/contrib/django/bootstrap.py
# -----------------------------------------------------------------------------
# 🚀 One Django test project for [django], [drf] and [channels]
# -----------------------------------------------------------------------------
# 🏛️ `ensure()` points Django at ``project/project/settings.py`` (a real
#    manage.py project under ``tests/contrib/django/project``) and runs
#    ``django.setup()`` once. Every Django-flavoured conftest calls it, and
#    so does the `DjangoStore` factory in the A2 contract suite -- so each
#    folder also runs on its own (the per-extra CI cells do exactly that).
# -----------------------------------------------------------------------------
"""Configure the test project (idempotent)."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PROJECT = Path(__file__).resolve().parent / "project"


def available() -> bool:
    return all(
        importlib.util.find_spec(m) is not None
        for m in ("django", "pytest_django")
    )


def ensure() -> None:
    """Configure settings and populate the app registry (idempotent)."""
    # 📝 `xstate_statemachine` must be THIS checkout's src (an editable
    #    install elsewhere would otherwise win for `INSTALLED_APPS`).
    src = str(ROOT / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    if str(PROJECT) not in sys.path:
        sys.path.insert(0, str(PROJECT))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
    import django
    from django.apps import apps

    if not apps.ready:
        django.setup()
