"""Pytester harness for the `[testing]` plugin tests.

🏛️ `pytester` runs a throw-away pytest session against inline test files,
which is the only honest way to test a plugin: the fixtures, markers and
options are exercised exactly as a user's session would see them. The
plugin is loaded the way the entry point loads it -- by module path -- so
the tests do not depend on the package being *installed* (the CI cell is
an editable install, a bare `pytest` in the checkout is not).

📝 `pytester` itself is enabled from the rootdir (`-p pytester` in
`[tool.pytest.ini_options].addopts`): pytest refuses `pytest_plugins` in a
non-top-level conftest because it would apply to the whole suite.
"""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
CORPUS = ROOT / "tests" / "tests_cli" / "stately_machines"

PLUGIN = "xstate_statemachine.contrib.testing.pytest_plugin"


def _entry_point_registered() -> bool:
    """Is the plugin installed as a `pytest11` entry point in this env?"""
    from importlib.metadata import entry_points

    eps = entry_points()
    group = (
        eps.select(group="pytest11")
        if hasattr(eps, "select")
        else eps.get("pytest11", [])  # Python 3.9
    )
    return any(ep.value == PLUGIN for ep in group)


#: 📝 When the package is installed (CI, an editable dev install) pytest
#:    loads the plugin from the entry point under the name
#:    `xstate_statemachine`; forcing it again by module path would register
#:    the same module twice and pytest refuses. In a bare checkout the entry
#:    point does not exist, so `-p <module>` is how the session gets it.
PLUGIN_ARGS = () if _entry_point_registered() else ("-p", PLUGIN)
#: See `run`: in-process inner sessions never load pytest-django.
NO_DJANGO = (
    ("-p", "no:django")
    if importlib.util.find_spec("pytest_django") is not None
    else ()
)


@pytest.fixture
def xsm_pytester(pytester: pytest.Pytester) -> pytest.Pytester:
    """A `pytester` whose sessions can import the package from `src/` and
    have the plugin loaded, whatever the install state."""
    pytester.syspathinsert(str(SRC))
    # 📝 A minimal ini keeps the repo's own `addopts` / `testpaths` out of
    #    the throw-away session. #268 battle (CI): the asyncio keys are
    #    UNKNOWN ini options when pytest-asyncio is absent (the core Test
    #    cells install no extras) -- an inner session run with `-W error`
    #    died with `PytestConfigWarning`. Emit them only when readable.
    ini = "[pytest]\n"
    if importlib.util.find_spec("pytest_asyncio") is not None:
        ini += "asyncio_mode = strict\n"
        # 📝 compat floor (pytest-asyncio 0.23, #309 CI): the loop-scope
        #    key arrived in 0.24; on 0.23 it is an UNKNOWN option and an
        #    inner `-W error` session dies with PytestConfigWarning.
        if _pytest_asyncio_at_least(0, 24):
            ini += "asyncio_default_fixture_loop_scope = function\n"
    pytester.makeini(ini)
    return pytester


def run(pytester: pytest.Pytester, *args: str) -> pytest.RunResult:
    """Run the throw-away session in-process with the plugin loaded.

    📝 ``-p no:django``: when the suite also runs the [django] test project
    (#280), Django is configured in THIS process, and an in-process inner
    session would make pytest-django call ``setup_test_environment()`` a
    second time. The inner sessions never need Django.
    """
    extra = ("-p", "no:django") if _has_pytest_django() else ()
    return pytester.runpytest_inprocess(*PLUGIN_ARGS, *extra, "-q", *args)


def _pytest_asyncio_at_least(*floor: int) -> bool:
    from importlib.metadata import version

    try:
        parts = tuple(int(x) for x in version("pytest-asyncio").split(".")[:2])
    except Exception:  # pragma: no cover - odd build strings
        return True
    return parts >= floor


def _has_pytest_django() -> bool:
    import importlib.util

    return importlib.util.find_spec("pytest_django") is not None
