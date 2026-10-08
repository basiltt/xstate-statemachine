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


@pytest.fixture(autouse=True)
def _isolated_post_transition_receivers():
    """#283: `contrib.channels` registers a permanent `post_transition`
    broadcaster on import; the signal tests here count receivers from
    zero. Save and restore the receiver list around every test."""
    try:
        from xstate_statemachine.contrib.django.signals import (
            post_transition,
        )
    except Exception:  # pragma: no cover - extra absent
        yield
        return
    saved = list(post_transition.receivers)
    post_transition.receivers = [
        r for r in saved if "xsm.channels.broadcast" not in str(r[0])
    ]
    post_transition.sender_receivers_cache.clear()
    try:
        yield
    finally:
        post_transition.receivers = saved
        post_transition.sender_receivers_cache.clear()
