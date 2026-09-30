# tests/contrib/brokers/conftest.py
"""Broker test options. Live-broker tests are marked ``containers`` and
run only with ``XSM_CONTAINERS=1`` (or ``XSM_LIVE_BROKERS=1``) and Docker;
the default matrix never depends on Docker (#294)."""

from __future__ import annotations

import os

import pytest

LIVE = os.environ.get("XSM_CONTAINERS") == "1" or (
    os.environ.get("XSM_LIVE_BROKERS") == "1"
)


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "containers: live broker via testcontainers (XSM_CONTAINERS=1)",
    )
