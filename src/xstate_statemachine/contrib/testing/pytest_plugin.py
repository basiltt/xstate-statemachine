# src/xstate_statemachine/contrib/testing/pytest_plugin.py
# -----------------------------------------------------------------------------
# 🔌 The pytest plugin: `xstate_machine` marker → `xsm_*` fixtures (#268)
# -----------------------------------------------------------------------------
# 🏛️ Loaded by pytest through the `pytest11` entry point in EVERY project
#    that installed the library, so three rules shape this module:
#      1. It imports only `pytest` and core. No hypothesis, no
#         `contrib.pydantic`; `stub_logic` is the core helper promoted in
#         #304. A user who installed core only must pay nothing for it.
#      2. Without the `xstate_machine` marker on a test nothing happens: no
#         option is required and no fixture is requested by anyone. The
#         fixtures only *exist* -- prefixed `xsm_` so they cannot shadow a
#         user's own `machine` / `clock` / `store`.
#      3. Configuration mistakes fail loudly at the marker, not silently at
#         the assertion: an unknown source, an unloadable `logic=`, or
#         `xstate_guards_false` with real logic (nothing to force) raise
#         `pytest.UsageError`. Silent acceptance is a bug.
#
# 📝 Snapshot files are deterministic by construction: `normalize_snapshot`
#    keeps only the state ids, the `value` tree, the context and the
#    status, and `render_snapshot` writes them with sorted keys, a fixed
#    indent and a trailing newline -- so two runs produce byte-identical
#    files and a mismatch is a real behavioural change, shown as a unified
#    diff. `--xsm-update-snapshots` rewrites; nothing else ever writes.
# -----------------------------------------------------------------------------
"""pytest plugin: markers, ``xsm_*`` fixtures and snapshot assertions."""

from __future__ import annotations

import difflib
import importlib
import json
import pathlib
import sys
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Tuple,
    Union,
)

import pytest

from ... import __version__
from ...clock import SimulatedClock
from ...factory import create_machine
from ...machine_logic import MachineLogic
from ...models import MachineNode
from ...persistence.store import MemoryStore
from ...sync_interpreter import SyncInterpreter
from ...testing_utils import logic_names, stub_logic
from ._coverage import CoverageSession, add_coverage_options
from ._paths import add_path_options, generate_path_tests, xsm_path

__all__ = [
    "PLUGIN_NAME",
    "MARKER",
    "GUARDS_MARKER",
    "SnapshotMismatchError",
    "MachineSpec",
    "parse_marker",
    "normalize_snapshot",
    "render_snapshot",
    "pytest_addoption",
    "pytest_configure",
    "pytest_cmdline_main",
    "pytest_generate_tests",
    "pytest_pycollect_makeitem",
    "pytest_unconfigure",
    "pytest_sessionfinish",
    "pytest_terminal_summary",
    "xsm_path",
]

#: The name pytest knows the plugin by: ``-p no:xstate_statemachine``.
PLUGIN_NAME = "xstate_statemachine"
MARKER = "xstate_machine"
GUARDS_MARKER = "xstate_guards_false"
UPDATE_OPTION = "--xsm-update-snapshots"
#: pytest-asyncio's registered plugin name (``-p no:asyncio`` removes it).
_ASYNCIO_PLUGIN = "asyncio"
_ASYNC_FIXTURES_PLUGIN = "xstate_statemachine_async_fixtures"

#: 📸 What a snapshot file records. Everything else in `get_snapshot()` --
#: `taken_at`, `machine_hash`, `version`, `deadlines` wall times, pending
#: events -- is either non-deterministic or an implementation detail of the
#: persistence layout, and would make files churn without behaviour changing.
SNAPSHOT_KEYS: Tuple[str, ...] = ("state_ids", "value", "context", "status")


class SnapshotMismatchError(AssertionError):
    """The interpreter's state differs from the recorded snapshot file.

    Attributes:
        path: The snapshot file compared against.
        diff: The unified diff (expected → actual) as one string.
    """

    def __init__(self, path: pathlib.Path, diff: str) -> None:
        self.path = path
        self.diff = diff
        super().__init__(
            f"snapshot mismatch: {path}\n"
            f"(run pytest {UPDATE_OPTION} to rewrite it)\n{diff}"
        )


# -----------------------------------------------------------------------------
# 🏷️ Marker parsing
# -----------------------------------------------------------------------------
class MachineSpec:
    """What the ``xstate_machine`` marker asked for, validated.

    Attributes:
        source: A JSON path, a config dict, or a built `MachineNode`.
        logic: Dotted ``"pkg.module:callable"`` returning a `MachineLogic`,
            or ``None`` for stub logic.
        strict_config: Passed through to `create_machine`.
        strict: Overrides the config's ``"strict"`` key when not ``None``.
        guards_false: Guard names the ``xstate_guards_false`` marker forces
            to ``False`` (only meaningful with stub logic).
    """

    __slots__ = ("source", "logic", "strict_config", "strict", "guards_false")

    def __init__(
        self,
        source: Union[str, pathlib.Path, Mapping[str, Any], MachineNode],
        *,
        logic: Optional[str] = None,
        strict_config: Optional[bool] = None,
        strict: Optional[bool] = None,
        guards_false: Tuple[str, ...] = (),
    ) -> None:
        self.source = source
        self.logic = logic
        self.strict_config = strict_config
        self.strict = strict
        self.guards_false = guards_false


def _usage_error(item: Any, message: str) -> "pytest.UsageError":
    return pytest.UsageError(f"{item.nodeid}: {message}")


def parse_marker(item: Any) -> Optional[MachineSpec]:
    """Read the ``xstate_machine`` / ``xstate_guards_false`` markers.

    Returns ``None`` when the test carries no ``xstate_machine`` marker --
    the signal that every ``xsm_*`` fixture must stay inert.

    Raises:
        pytest.UsageError: malformed marker arguments, or
            ``xstate_guards_false`` combined with ``logic=`` (real logic
            has no stub guards to force -- refusing beats a test that
            silently exercises the wrong thing).
    """
    marker = item.get_closest_marker(MARKER)
    if marker is None:
        if item.get_closest_marker(GUARDS_MARKER) is not None:
            raise _usage_error(
                item,
                f"@pytest.mark.{GUARDS_MARKER} needs an "
                f"@pytest.mark.{MARKER}(...) marker on the same test",
            )
        return None
    if len(marker.args) != 1:
        raise _usage_error(
            item,
            f"@pytest.mark.{MARKER} takes exactly one positional argument "
            f"(a JSON path, a config dict or a MachineNode), got "
            f"{len(marker.args)}",
        )
    allowed = {"logic", "strict_config", "strict"}
    unknown = sorted(set(marker.kwargs) - allowed)
    if unknown:
        raise _usage_error(
            item,
            f"@pytest.mark.{MARKER}: unknown keyword(s) {unknown}; "
            f"allowed: {sorted(allowed)}",
        )
    source = marker.args[0]
    if not isinstance(source, (str, pathlib.Path, Mapping, MachineNode)):
        raise _usage_error(
            item,
            f"@pytest.mark.{MARKER}: source must be a JSON path, a dict or "
            f"a MachineNode, got {type(source).__name__}",
        )
    logic = marker.kwargs.get("logic")
    if logic is not None and not (
        isinstance(logic, str) and ":" in logic and not logic.startswith(":")
    ):
        raise _usage_error(
            item,
            f"@pytest.mark.{MARKER}: logic= must be a dotted "
            f"'package.module:callable' string, got {logic!r}",
        )
    guards_false: Tuple[str, ...] = ()
    guards_marker = item.get_closest_marker(GUARDS_MARKER)
    if guards_marker is not None:
        if guards_marker.kwargs:
            raise _usage_error(
                item,
                f"@pytest.mark.{GUARDS_MARKER} takes guard names as "
                f"positional arguments only",
            )
        if not guards_marker.args or not all(
            isinstance(g, str) and g for g in guards_marker.args
        ):
            raise _usage_error(
                item,
                f"@pytest.mark.{GUARDS_MARKER} needs one or more guard "
                f"names, e.g. @pytest.mark.{GUARDS_MARKER}('isPaid')",
            )
        if logic is not None:
            # 🛑 Real logic owns its guards; the stub table would be
            #    ignored. Refuse instead of pretending the guards flipped.
            raise _usage_error(
                item,
                f"@pytest.mark.{GUARDS_MARKER} only applies to stub logic; "
                f"this test passes logic={logic!r}. Make the real guard "
                f"return False instead, or drop logic= to use stubs.",
            )
        guards_false = tuple(guards_marker.args)
    for flag in ("strict_config", "strict"):
        # 🛑 `strict="false"` is truthy; only a real bool (or None) is
        #    unambiguous.
        value = marker.kwargs.get(flag)
        if value is not None and not isinstance(value, bool):
            raise _usage_error(
                item,
                f"@pytest.mark.{MARKER}: {flag}= must be True, False or "
                f"None, got {value!r}",
            )
    return MachineSpec(
        source,
        logic=logic,
        strict_config=marker.kwargs.get("strict_config"),
        strict=marker.kwargs.get("strict"),
        guards_false=guards_false,
    )


# -----------------------------------------------------------------------------
# 🏗️ Building the machine
# -----------------------------------------------------------------------------
def _resolve_path(item: Any, source: Union[str, pathlib.Path]) -> pathlib.Path:
    """A relative JSON path is tried next to the test file, then rootdir."""
    path = pathlib.Path(source)
    if path.is_absolute():
        if path.is_file():
            return path
        raise _usage_error(item, f"machine file not found: {path}")
    candidates = [pathlib.Path(str(item.path)).parent / path]
    rootdir = getattr(item.config, "rootpath", None)
    if rootdir is not None:
        candidates.append(pathlib.Path(str(rootdir)) / path)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    tried = ", ".join(str(c) for c in candidates)
    raise _usage_error(
        item,
        f"machine file {str(source)!r} not found (tried {tried})",
    )


def _load_config(item: Any, path: pathlib.Path) -> Dict[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise _usage_error(item, f"cannot read machine JSON {path}: {exc}")
    if not isinstance(loaded, dict):
        raise _usage_error(
            item, f"{path}: top level must be a JSON object (the machine)"
        )
    return loaded


def _load_logic(item: Any, dotted: str) -> MachineLogic:
    """Import ``pkg.module:callable`` and call it; must yield MachineLogic."""
    module_name, _, attr = dotted.partition(":")
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise _usage_error(
            item, f"logic={dotted!r}: cannot import {module_name!r}: {exc}"
        )
    factory: Any = module
    for part in attr.split("."):
        factory = getattr(factory, part, None)
        if factory is None:
            raise _usage_error(
                item, f"logic={dotted!r}: {module_name!r} has no {attr!r}"
            )
    if not callable(factory):
        raise _usage_error(item, f"logic={dotted!r}: {attr!r} is not callable")
    logic = _call_logic_factory(item, dotted, factory)
    if not isinstance(logic, MachineLogic):
        raise _usage_error(
            item,
            f"logic={dotted!r}: callable must return a MachineLogic, got "
            f"{type(logic).__name__}",
        )
    return logic


def _call_logic_factory(item: Any, dotted: str, factory: Any) -> Any:
    """Call the ``logic=`` factory; a raising factory is a usage error."""
    try:
        return factory()
    except Exception as exc:  # noqa: BLE001 -- surface as a usage error
        raise _usage_error(
            item,
            f"logic={dotted!r}: the factory raised "
            f"{type(exc).__name__}: {exc}",
        ) from exc


class _Built:
    """A built machine plus the stub bookkeeping the fixtures hand out."""

    __slots__ = ("machine", "ran", "guards", "stubbed")

    def __init__(
        self,
        machine: MachineNode,
        ran: List[str],
        guards: Dict[str, bool],
        stubbed: bool,
    ) -> None:
        self.machine = machine
        self.ran = ran
        self.guards = guards
        self.stubbed = stubbed


def _build(item: Any, spec: MachineSpec) -> _Built:
    ran: List[str] = []
    guards: Dict[str, bool] = {name: False for name in spec.guards_false}
    if isinstance(spec.source, MachineNode):
        if (
            spec.logic is not None
            or spec.strict_config is not None
            or spec.strict is not None
        ):
            # 🛑 Never mutate the caller's node: a module-level MachineNode
            #    would leak `strict` into every later test.
            raise _usage_error(
                item,
                "a MachineNode source is already built; logic=, "
                "strict_config= and strict= cannot be applied to it",
            )
        if spec.guards_false:
            raise _usage_error(
                item,
                f"@pytest.mark.{GUARDS_MARKER} cannot force guards on an "
                f"already-built MachineNode; pass the config dict or JSON "
                f"path instead",
            )
        return _Built(spec.source, ran, guards, stubbed=False)

    if isinstance(spec.source, Mapping):
        config: Dict[str, Any] = dict(spec.source)
    else:
        config = _load_config(item, _resolve_path(item, spec.source))
    if spec.strict is not None:
        config["strict"] = bool(spec.strict)
    try:
        # 📝 `stub_logic` validates the chart too (battle #304), so an
        #    invalid config now surfaces HERE, not in `create_machine`
        #    below -- both must become the same usage error.
        if spec.logic is None:
            if spec.guards_false:
                # 🛑 #268 battle: a misspelt guard name was silently
                #    accepted (the stub table just gained a key nobody
                #    read) and the test exercised the TRUE branch while
                #    claiming to force False.
                _, known, _ = logic_names(config)
                unknown = sorted(set(spec.guards_false) - set(known))
                if unknown:
                    raise _usage_error(
                        item,
                        f"@pytest.mark.{GUARDS_MARKER}: the chart declares "
                        f"no guard named {unknown}; known guards: "
                        f"{sorted(known)}",
                    )
            logic = stub_logic(config, ran=ran, guards=guards)
            stubbed = True
        else:
            logic = _load_logic(item, spec.logic)
            stubbed = False
        machine = create_machine(
            config, logic=logic, strict_config=spec.strict_config
        )
    except pytest.UsageError:
        raise  # `_load_logic` already phrased its own
    except Exception as exc:  # noqa: BLE001 -- surface as a usage error
        raise _usage_error(
            item, f"create_machine failed: {type(exc).__name__}: {exc}"
        ) from exc
    return _Built(machine, ran, guards, stubbed)


# -----------------------------------------------------------------------------
# 📸 Snapshots
# -----------------------------------------------------------------------------
def normalize_snapshot(
    snapshot: Union[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    """Reduce a ``get_snapshot()`` blob to its deterministic, behavioural
    part: ``state_ids``, ``value``, ``context`` and ``status``."""
    data = json.loads(snapshot) if isinstance(snapshot, str) else snapshot
    return {key: data.get(key) for key in SNAPSHOT_KEYS if key in data}


def render_snapshot(normalized: Mapping[str, Any]) -> str:
    """The byte-exact file form: sorted keys, two-space indent, newline."""
    return json.dumps(normalized, indent=2, sort_keys=True, default=str) + "\n"


def _snapshot_path(item: Any, path: Union[str, pathlib.Path]) -> pathlib.Path:
    p = pathlib.Path(path)
    base = pathlib.Path(str(item.path)).parent
    if not p.is_absolute():
        p = base / p
    resolved = p.resolve()
    root = pathlib.Path(str(getattr(item.config, "rootpath", base))).resolve()
    # 🛡️ #268 battle (X0.10): `--xsm-update-snapshots` WRITES this path.
    #    A relative path with enough `..` escaped the project; refuse
    #    anything outside the rootdir (and the test's own tree).
    if root not in resolved.parents and resolved != root:
        if base.resolve() not in resolved.parents:
            raise _usage_error(
                item,
                f"snapshot path {str(path)!r} resolves outside the project "
                f"({resolved}); keep snapshot files under the rootdir",
            )
    return resolved


def _assert_snapshot(
    item: Any, interp: Any, path: Union[str, pathlib.Path]
) -> None:
    target = _snapshot_path(item, path)
    actual = render_snapshot(normalize_snapshot(interp.get_snapshot()))
    if item.config.getoption(UPDATE_OPTION):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(actual, encoding="utf-8")
        return
    if not target.is_file():
        raise SnapshotMismatchError(
            target,
            f"no snapshot file at {target}; run pytest {UPDATE_OPTION} "
            f"to record it",
        )
    expected_text = target.read_text(encoding="utf-8")
    try:
        expected = render_snapshot(normalize_snapshot(expected_text))
    except ValueError as exc:
        raise SnapshotMismatchError(
            target, f"snapshot file is not valid JSON: {exc}"
        ) from exc
    if expected == actual:
        return
    diff = "".join(
        difflib.unified_diff(
            expected.splitlines(keepends=True),
            actual.splitlines(keepends=True),
            fromfile=f"{target.name} (recorded)",
            tofile=f"{target.name} (actual)",
        )
    )
    raise SnapshotMismatchError(target, diff)


# -----------------------------------------------------------------------------
# ⌨️ Options, markers, hooks
# -----------------------------------------------------------------------------
def pytest_addoption(parser: Any) -> None:
    group = parser.getgroup("xstate", "xstate-statemachine")
    group.addoption(
        "--xsm-version",
        action="store_true",
        default=False,
        help="print the xstate-statemachine version and exit",
    )
    group.addoption(
        UPDATE_OPTION,
        action="store_true",
        default=False,
        help="rewrite snapshot files asserted with the xsm_snapshot fixture",
    )
    add_path_options(group)
    add_coverage_options(group)
    group.addoption(
        "--xsm-failing-dir",
        default=None,
        metavar="DIR",
        help="where model_test() writes the minimal failing sequence "
        "(failing.json); default: next to the test module",
    )


def pytest_cmdline_main(config: Any) -> Optional[int]:
    """``pytest --xsm-version``: print the library version, exit 0.

    📝 Implemented as a ``cmdline_main`` short-circuit (the way
    ``--version`` / ``--fixtures`` are), so it works in an empty directory
    and under in-process runners alike. ``-p no:xstate_statemachine``
    removes the option together with the plugin.
    """
    if config.getoption("--xsm-version", default=False):
        sys.stdout.write(f"xstate-statemachine {__version__}\n")
        return 0
    return None


def pytest_configure(config: Any) -> None:
    config.addinivalue_line(
        "markers",
        f"{MARKER}(source, *, logic=None, strict_config=None, strict=None): "
        "build the machine the xsm_* fixtures serve. `source` is a JSON "
        "path (relative to the test file, then rootdir), a config dict or "
        "a MachineNode; `logic` a 'pkg.module:callable' returning a "
        "MachineLogic (stub logic when omitted).",
    )
    config.addinivalue_line(
        "markers",
        f"{GUARDS_MARKER}(*names): with stub logic, make the named guards "
        "return False (others stay True); flip them live via xsm_guards.",
    )
    # 🔌 The async fixture needs `pytest_asyncio.fixture`, so its module is
    #    imported only when the pytest-asyncio plugin is ACTIVE in this
    #    session -- never at plugin load, never under `-p no:asyncio`.
    if _pytest_asyncio_active(config) and not config.pluginmanager.hasplugin(
        _ASYNC_FIXTURES_PLUGIN
    ):
        from . import _async_fixtures

        config.pluginmanager.register(_async_fixtures, _ASYNC_FIXTURES_PLUGIN)
    CoverageSession.configure(config)
    failing_dir = config.getoption("--xsm-failing-dir", default=None)
    if failing_dir:
        # 📝 `model` is hypothesis-free at import time.
        from . import model

        model.FAILING_DIR = pathlib.Path(failing_dir).resolve()


def pytest_unconfigure(config: Any) -> None:
    CoverageSession.unconfigure(config)
    if config.getoption("--xsm-failing-dir", default=None):
        from . import model

        model.FAILING_DIR = None


def pytest_generate_tests(metafunc: Any) -> None:
    """Parametrise ``xsm_path`` over the machine's paths (#269)."""
    generate_path_tests(metafunc)


def pytest_pycollect_makeitem(collector: Any, name: str, obj: Any) -> Any:
    """Collect ``TestX = model_test(...)`` through its ``TestCase`` (#271).

    📝 A ``RuleBasedStateMachine`` has an ``__init__``, so pytest would
    skip it with a warning; its generated ``TestCase`` is the runnable
    unittest class. Detected by a marker attribute -- no hypothesis
    import here.
    """
    if (
        isinstance(obj, type)
        and getattr(obj, "_xsm_model_test", False)
        and collector.classnamefilter(name)
    ):
        cls = _model_test_case_class(collector.config)
        if cls is None:  # `-p no:unittest`: nothing can run a TestCase
            return None
        return cls.from_parent(collector, name=name)
    return None


_MODEL_TEST_CASE: Any = None


def _model_test_case_class(config: Any) -> Any:
    # 📝 pytest's unittest collector class, taken from its REGISTERED
    #    `unittest` plugin rather than imported: this module imports only
    #    `pytest` and core.
    global _MODEL_TEST_CASE
    if _MODEL_TEST_CASE is not None:
        return _MODEL_TEST_CASE
    plugin = config.pluginmanager.get_plugin("unittest")
    if plugin is None:
        return None
    base = plugin.UnitTestCase

    class ModelTestCase(base):  # type: ignore[misc, valid-type]
        """pytest resolves a class node's object by NAME on its parent
        module; the name is bound to the state machine, so answer with
        its generated ``TestCase`` instead."""

        def _getobj(self) -> Any:
            return getattr(self.parent.obj, self.name).TestCase

    _MODEL_TEST_CASE = ModelTestCase
    return ModelTestCase


def pytest_sessionfinish(session: Any, exitstatus: Any) -> None:
    cov = CoverageSession.get(session.config)
    if cov is not None:
        cov.finish(session)


def pytest_terminal_summary(terminalreporter: Any) -> None:
    cov = CoverageSession.get(terminalreporter.config)
    if cov is not None:
        cov.summary(terminalreporter)


# -----------------------------------------------------------------------------
# 🧪 Fixtures
# -----------------------------------------------------------------------------
def _spec_or_fail(request: Any) -> MachineSpec:
    spec = parse_marker(request.node)
    if spec is not None:
        return spec
    # 📝 Name the fixture the TEST asked for (`xsm_interp`), not the
    #    internal one that noticed (`_xsm_built`).
    wanted = [
        name
        for name in getattr(request.node, "fixturenames", ())
        if name.startswith("xsm_")
    ]
    asked = wanted[0] if wanted else request.fixturename
    # 🧷 `pytest.fail` never returns; the explicit raise keeps the return
    #    type provable under every mypy / pytest-stub combination.
    pytest.fail(
        f"{request.node.nodeid}: the {asked} fixture needs an "
        f"@pytest.mark.{MARKER}(...) marker on the test",
        pytrace=False,
    )
    raise AssertionError("unreachable")  # pragma: no cover


@pytest.fixture
def _xsm_built(request: Any) -> _Built:
    """Internal: the machine built from the marker, once per test."""
    return _build(request.node, _spec_or_fail(request))


@pytest.fixture
def xsm_machine(_xsm_built: _Built) -> MachineNode:
    """The `MachineNode` the ``xstate_machine`` marker describes."""
    return _xsm_built.machine


@pytest.fixture
def xsm_ran(_xsm_built: _Built) -> List[str]:
    """Names of the stub actions that ran, in order.

    Empty (and never appended to) when the marker passes ``logic=`` or a
    built `MachineNode` source -- real actions do not report here.
    """
    return _xsm_built.ran


@pytest.fixture
def xsm_guards(_xsm_built: _Built) -> Dict[str, bool]:
    """The live stub-guard table (``name -> bool``); unlisted guards are
    ``True``. Mutate it between sends to flip a guard. Empty (and inert)
    with ``logic=`` or a built `MachineNode` source."""
    return _xsm_built.guards


@pytest.fixture
def xsm_clock() -> SimulatedClock:
    """A `SimulatedClock`; ``increment(ms)`` fires due ``after`` timers.

    On the async engine ``increment`` returns an awaitable -- ``await`` it.
    """
    return SimulatedClock()


@pytest.fixture
def xsm_interp(xsm_machine: MachineNode, xsm_clock: SimulatedClock) -> Any:
    """A started `SyncInterpreter` on ``xsm_clock``; stopped at teardown."""
    interp = SyncInterpreter(xsm_machine, clock=xsm_clock).start()
    yield interp
    if interp.status == "running":
        interp.stop()


def _pytest_asyncio_active(config: Any) -> bool:
    # 📝 Ask the plugin manager, per session: the runner must be *active*,
    #    not merely installed, so `-p no:asyncio` gives a clean skip.
    return bool(config.pluginmanager.hasplugin(_ASYNCIO_PLUGIN))


async def _start_async(machine: MachineNode, clock: SimulatedClock) -> Any:
    from ...interpreter import Interpreter

    return await Interpreter(machine, clock=clock).start()


async def _stop_async(interp: Any) -> None:
    if interp.status == "running":
        await interp.stop()


@pytest.fixture
def xsm_ainterp(request: Any) -> Any:
    """A started async `Interpreter` on ``xsm_clock``; stopped at teardown.

    Needs ``pytest-asyncio`` (mark the test ``@pytest.mark.asyncio`` or
    run with ``asyncio_mode = auto``); skipped with the package to install
    otherwise. The interpreter itself comes from ``_xsm_ainterp_async``.
    """
    # 📝 Touch the marker first so a mis-marked test still gets the
    #    marker error rather than an unrelated skip.
    _spec_or_fail(request)
    if not _pytest_asyncio_active(request.config):
        pytest.skip(
            "xsm_ainterp needs pytest-asyncio: pip install pytest-asyncio "
            "and mark the test @pytest.mark.asyncio"
        )
    return request.getfixturevalue("_xsm_ainterp_async")


@pytest.fixture
def xsm_store() -> MemoryStore:
    """A fresh `persistence.MemoryStore`."""
    return MemoryStore()


def _steps(args: Tuple[Any, ...]) -> List[Dict[str, Any]]:
    """Turn ``("A", "+500", "B")`` into simulate-style commands."""
    # 📝 Reuse the `xsm simulate --events` grammar instead of re-implementing
    #    it; the CLI module is pure stdlib.
    from ...cli.commands.simulate import parse_events_arg

    tokens = []
    for arg in args:
        if isinstance(arg, (int, float)) and not isinstance(arg, bool):
            # 📝 `f"{1_000_000:g}"` is "1e+06", which the grammar rejects.
            if float(arg).is_integer():
                tokens.append(f"+{int(arg)}")
            else:
                tokens.append(f"+{arg}")
        elif isinstance(arg, str):
            tokens.append(arg)
        else:
            raise TypeError(
                f"xsm_send_all steps must be event names or '+ms' strings, "
                f"got {arg!r}"
            )
    return parse_events_arg(",".join(tokens), None)


@pytest.fixture
def xsm_send_all(xsm_clock: SimulatedClock) -> Callable[..., None]:
    """``xsm_send_all(interp, "A", "+500", "B")``: send events in order;
    a ``"+N"`` token advances ``xsm_clock`` by N ms (the ``xsm simulate
    --events`` grammar). Sync interpreters only."""

    def _send_all(interp: Any, *steps: Any) -> None:
        for cmd in _steps(steps):
            if "send" in cmd:
                interp.send(cmd["send"])
            else:
                xsm_clock.increment(cmd["clock"])

    return _send_all


@pytest.fixture
def xsm_asend_all(
    xsm_clock: SimulatedClock,
) -> Callable[..., Awaitable[None]]:
    """Async twin of ``xsm_send_all``: ``await xsm_asend_all(ainterp,
    "A", "+500", "B")`` awaits each send and each clock advance."""

    async def _asend_all(interp: Any, *steps: Any) -> None:
        for cmd in _steps(steps):
            if "send" in cmd:
                await interp.send(cmd["send"], wait=True)
            else:
                pending = xsm_clock.increment(cmd["clock"])
                if pending is not None:
                    await pending

    return _asend_all


@pytest.fixture
def xsm_snapshot(
    request: Any,
) -> Callable[[Any, Union[str, pathlib.Path]], None]:
    """``xsm_snapshot(interp, "snapshots/paid.json")``: assert the
    interpreter's state ids, value, context and status match the file.
    ``--xsm-update-snapshots`` (re)writes it; a mismatch raises
    `SnapshotMismatchError` with a unified diff. Relative paths are
    resolved next to the test file."""

    def _snapshot(interp: Any, path: Union[str, pathlib.Path]) -> None:
        _assert_snapshot(request.node, interp, path)

    return _snapshot
