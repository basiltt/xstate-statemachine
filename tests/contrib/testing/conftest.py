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


@pytest.fixture
def xsm_pytester(pytester: pytest.Pytester) -> pytest.Pytester:
    """A `pytester` whose sessions can import the package from `src/` and
    have the plugin loaded, whatever the install state."""
    pytester.syspathinsert(str(SRC))
    # 📝 A minimal ini keeps the repo's own `addopts` / `testpaths` out of
    #    the throw-away session; `asyncio_mode` matters only when
    #    pytest-asyncio is installed (the CI cell installs it).
    pytester.makeini(
        "[pytest]\n"
        "asyncio_mode = strict\n"
        "asyncio_default_fixture_loop_scope = function\n"
    )
    return pytester


def run(pytester: pytest.Pytester, *args: str) -> pytest.RunResult:
    """Run the throw-away session in-process with the plugin loaded."""
    return pytester.runpytest_inprocess(*PLUGIN_ARGS, "-q", *args)
