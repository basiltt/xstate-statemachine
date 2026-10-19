"""Import-time guardrails for ``import xstate_statemachine``.

The package is imported by every user, so it must not drag in subpackages and
stdlib modules only a few of them need (CLI, contrib adapters, EDA, patterns,
file / SQLite stores, graph analysis, ...). These tests pin that contract
*deterministically*: they count and name the modules a fresh interpreter
loads, rather than timing anything (timings are flaky on shared CI runners).

Each check runs in a fresh subprocess because this test process has long
since imported everything.
"""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
from typing import Any, Dict, List

import pytest

import xstate_statemachine

# 📝 Baseline before the lazy-import work (CPython 3.14, Windows): the import
# added 179 modules to `sys.modules`, 36 of them our own; now 132 / 27. About
# 100 of what remains is `asyncio` and its transitive stdlib imports, which
# the async engine genuinely needs. The ceilings leave a little headroom but
# fail loudly if a heavy import creeps back into the eager path.
MAX_ADDED_MODULES = 150
MAX_PACKAGE_MODULES = 32

# 🏛️ Modules that must NOT be loaded by a bare `import xstate_statemachine`.
LAZY_PACKAGE_MODULES = [
    "xstate_statemachine.cli",
    "xstate_statemachine.contrib",
    "xstate_statemachine.eda",
    "xstate_statemachine.patterns",
    "xstate_statemachine.inspect",
    "xstate_statemachine.coverage",
    "xstate_statemachine.graph",
    "xstate_statemachine._graph_explorer",
    "xstate_statemachine.testing_utils",
    "xstate_statemachine.helpers",
    "xstate_statemachine.receipts",
    "xstate_statemachine.persistence.file_store",
    "xstate_statemachine.persistence.sqlite_store",
    "xstate_statemachine.persistence.async_store",
    "xstate_statemachine.persistence.locking",
    "xstate_statemachine.persistence.log",
    "xstate_statemachine.persistence.idempotency",
]

# 💡 Stdlib modules only the lazy parts need; none of the core imports them.
LAZY_STDLIB_MODULES = ["sqlite3", "tempfile", "uuid", "hashlib"]


def _fresh_import_report() -> Dict[str, Any]:
    """Import the package in a clean interpreter and report what it loaded.

    💡 Only modules *added by the import* are reported, so site hooks or
    coverage plugins that pre-load their own modules cannot skew the result.
    """
    code = (
        "import json, sys\n"
        "before = set(sys.modules)\n"
        "import xstate_statemachine\n"
        "print(json.dumps(sorted(set(sys.modules) - before)))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
    )
    modules: List[str] = json.loads(result.stdout)
    return {
        "modules": set(modules),
        "package": [m for m in modules if m.startswith("xstate_statemachine")],
    }


@pytest.fixture(scope="module")
def report() -> Dict[str, Any]:
    return _fresh_import_report()


@pytest.mark.parametrize("module", LAZY_PACKAGE_MODULES)
def test_heavy_package_module_is_not_imported_eagerly(
    report: Dict[str, Any], module: str
) -> None:
    assert module not in report["modules"]


@pytest.mark.parametrize("module", LAZY_STDLIB_MODULES)
def test_heavy_stdlib_module_is_not_imported_eagerly(
    report: Dict[str, Any], module: str
) -> None:
    assert module not in report["modules"]


def test_core_modules_are_still_eager(report: Dict[str, Any]) -> None:
    for module in (
        "xstate_statemachine.factory",
        "xstate_statemachine.interpreter",
        "xstate_statemachine.sync_interpreter",
        "xstate_statemachine.pythonic",
        "xstate_statemachine.plugins",
    ):
        assert module in report["modules"]


def test_module_count_stays_below_budget(report: Dict[str, Any]) -> None:
    assert len(report["package"]) <= MAX_PACKAGE_MODULES, report["package"]
    assert len(report["modules"]) <= MAX_ADDED_MODULES


def test_all_names_resolve_via_getattr() -> None:
    missing = [
        name
        for name in xstate_statemachine.__all__
        if not hasattr(xstate_statemachine, name)
    ]
    assert missing == []


def test_all_names_resolve_via_from_import() -> None:
    namespace: Dict[str, Any] = {}
    for name in xstate_statemachine.__all__:
        exec(f"from xstate_statemachine import {name}", namespace)
        assert name in namespace


def test_star_import_resolves_every_public_name() -> None:
    namespace: Dict[str, Any] = {}
    exec("from xstate_statemachine import *", namespace)
    assert set(xstate_statemachine.__all__) <= set(namespace)


def test_all_names_are_listed_by_dir() -> None:
    assert set(xstate_statemachine.__all__) <= set(dir(xstate_statemachine))


def test_lazy_names_resolve_to_the_real_objects() -> None:
    from xstate_statemachine import graph, helpers, receipts, testing_utils

    assert xstate_statemachine.shortest_paths is graph.shortest_paths
    assert xstate_statemachine.wait_for is helpers.wait_for
    assert xstate_statemachine.pure_transition is helpers.transition
    assert xstate_statemachine.stub_logic is testing_utils.stub_logic
    assert xstate_statemachine.receipt_to_json is receipts.receipt_to_json
    # 🔥 `transition` is the Pythonic DSL's, never the pure reducer.
    # the DSL `transition()` lives in `_pythonic_core`, re-exported by `pythonic`
    assert xstate_statemachine.transition.__module__.endswith("_pythonic_core")


def test_lazy_name_is_cached_after_first_access() -> None:
    code = (
        "import xstate_statemachine as x\n"
        "assert 'reachable_states' not in vars(x)\n"
        "fn = x.reachable_states\n"
        "assert vars(x)['reachable_states'] is fn\n"
    )
    subprocess.run([sys.executable, "-c", code], check=True)


def test_unknown_attribute_raises_attribute_error() -> None:
    with pytest.raises(AttributeError, match="no_such_name"):
        xstate_statemachine.no_such_name  # noqa: B018
    assert not hasattr(xstate_statemachine, "no_such_name")


def test_persistence_lazy_backends_keep_their_public_names() -> None:
    persistence = importlib.import_module("xstate_statemachine.persistence")
    for name in ("FileStore", "SQLiteStore", "AsyncStoreAdapter", "as_async"):
        assert getattr(persistence, name) is not None
    assert persistence.file_store.FileStore is persistence.FileStore
    with pytest.raises(AttributeError):
        persistence.no_such_name  # noqa: B018


def test_persistence_backends_not_loaded_by_the_package_import() -> None:
    code = (
        "import sys, xstate_statemachine\n"
        "from xstate_statemachine import persistence\n"
        "assert 'xstate_statemachine.persistence.file_store' not in "
        "sys.modules\n"
        "persistence.FileStore\n"
        "assert 'xstate_statemachine.persistence.file_store' in sys.modules\n"
    )
    subprocess.run([sys.executable, "-c", code], check=True)


def test_global_plugins_are_not_registered_at_import_time() -> None:
    code = (
        "import xstate_statemachine as x\n"
        "assert list(x.global_plugins()) == []\n"
    )
    subprocess.run([sys.executable, "-c", code], check=True)
