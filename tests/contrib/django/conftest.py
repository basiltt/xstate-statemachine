# tests/contrib/django/conftest.py
"""[django] fixtures: the shared test project, via pytest-django.

The project is configured here (not with ``--ds``) so the folder runs on
its own in the per-extra CI cell AND alongside the rest of the suite.
Without Django or pytest-django every test here is skipped.
"""

from __future__ import annotations

import pytest

from ..conftest import requires_extra
from . import bootstrap

pytestmark = requires_extra("django")

if bootstrap.available():
    bootstrap.ensure()
else:  # pragma: no cover - bare checkout
    collect_ignore_glob = ["test_*.py"]


@pytest.fixture
def order(db):
    from shop.models import Order

    return Order.objects.create(title="t")
