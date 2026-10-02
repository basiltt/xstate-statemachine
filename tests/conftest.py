"""Suite-wide fixtures."""

import logging
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


@pytest.fixture(scope="session", autouse=True)
def _no_root_logging_handler_leak():
    """Fail the session if a test left a non-pytest handler on the ROOT
    logger.

    🏛️ Battle #262 integration: Litestar's default `LoggingConfig` put a
    `QueueHandler` on the root logger at app construction and never
    removed it. Every `logger.info` the library emitted for the rest of
    the session was then retained in that queue, and the tracemalloc
    leak tests in tests/persistence read ~800 KB of "library growth" --
    one `from_snapshot` record per cycle -- whenever the Litestar file ran
    first. That is the kind of cross-test contamination that turns an
    honest leak test into a flake; make it loud at the source.
    """
    root = logging.getLogger()
    before = {id(h) for h in root.handlers}
    yield
    added = [
        h
        for h in root.handlers
        if id(h) not in before
        and type(h).__module__.split(".")[0] not in ("_pytest", "logging")
    ]
    assert not added, (
        "a test left handler(s) on the ROOT logger (they retain every log "
        f"record for the rest of the session): {added!r}. Remove them in "
        "the fixture's teardown, or construct the framework app with its "
        "logging disabled (Litestar: logging_config=None)."
    )
