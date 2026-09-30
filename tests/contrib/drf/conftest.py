# tests/contrib/drf/conftest.py
"""[drf] fixtures: the shared Django test project (tests/contrib/django)."""

from __future__ import annotations

from ..conftest import requires_extra
from ..django import bootstrap

pytestmark = requires_extra("drf")

if bootstrap.available():
    bootstrap.ensure()
else:  # pragma: no cover - bare checkout
    collect_ignore_glob = ["test_*.py"]
