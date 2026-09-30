# tests/contrib/channels/conftest.py
"""[channels] fixtures: the shared Django test project."""

from __future__ import annotations

from ..conftest import requires_extra
from ..django import bootstrap

pytestmark = requires_extra("channels")

if bootstrap.available():
    bootstrap.ensure()
else:  # pragma: no cover - bare checkout
    collect_ignore_glob = ["test_*.py"]
