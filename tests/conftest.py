"""Suite-wide fixtures."""

import sys

import pytest


@pytest.fixture(autouse=True)
def _fresh_deprecation_sites():
    """#296: `deprecated()` warns once per call site per PROCESS. Tests that
    assert a warning must not depend on whether an earlier test already hit
    the same library call site, so each test starts with a clean record.

    📝 Parts of the suite import `src.xstate_statemachine` -- a distinct
    module object with its own record -- so reset every loaded copy.
    """
    for name in (
        "xstate_statemachine.deprecations",
        "src.xstate_statemachine.deprecations",
    ):
        mod = sys.modules.get(name)
        if mod is not None:
            mod.reset_deprecation_warnings()
    yield
