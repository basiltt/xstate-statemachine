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
import sys

import pytest

_FORCE = ("FORCE_COLOR", "XSM_FORCE_COLOR", "CLICOLOR_FORCE")

#: 📝 Parts of the suite import the package as `src.xstate_statemachine`
#:    and parts as `xstate_statemachine` -- two module objects, each with
#:    its own cached console -- so every loaded copy is reset (the root
#:    conftest does the same for the deprecation record).
_CONSOLE_MODULES = (
    "xstate_statemachine.cli.commands",
    "src.xstate_statemachine.cli.commands",
)


@pytest.fixture(autouse=True)
def _no_forced_color(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _FORCE:
        monkeypatch.delenv(key, raising=False)


def _reset_every_console() -> None:
    for name in _CONSOLE_MODULES:
        module = sys.modules.get(name)
        if module is not None:
            module.reset_console()


@pytest.fixture(autouse=True)
def _fresh_console() -> None:
    """Forget the process-wide CLI console before and after every test.

    `get_console()` caches a `Console` whose capabilities were probed from
    the first stream it saw and whose `last_error` belongs to whichever
    command set it; neither should leak from one test into the next. (The
    console resolves ``sys.stdout`` at write time, so a stale cache can no
    longer write into a capture stream pytest has closed -- the reset
    keeps the tests independent all the same.)
    """
    _reset_every_console()
    yield
    _reset_every_console()
