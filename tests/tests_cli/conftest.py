"""Test-environment pins for the CLI suite.

🎨 GitHub Actions (and some local shells) export ``FORCE_COLOR=1``. The
CLI honours that on purpose -- a piped ``xsm`` under ``FORCE_COLOR`` keeps
its colours -- but the tests in this package pin plain-text output and
would otherwise see ANSI escapes wrapped around every label. Strip the
override for the duration of each test; tests that want forced colour set
it explicitly with ``mock.patch.dict``.
"""

from __future__ import annotations

import os

import pytest

_FORCE = ("FORCE_COLOR", "XSM_FORCE_COLOR", "CLICOLOR_FORCE")


@pytest.fixture(autouse=True)
def _no_forced_color(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _FORCE:
        monkeypatch.delenv(key, raising=False)
