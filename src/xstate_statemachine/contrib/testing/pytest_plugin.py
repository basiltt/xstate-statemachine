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

import pathlib
import time
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
from ...events import Event
from ...models import MachineNode
from ...persistence.store import MemoryStore
from ...sync_interpreter import SyncInterpreter
from ._coverage import CoverageSession, add_coverage_options
from ._marker import (
    GUARDS_MARKER,
    MARKER,
    MachineSpec,
    _build,
    _Built,
    _load_logic,
    _usage_error,
    parse_marker,
)
from ._snapshots import (
    SNAPSHOT_KEYS,
    UPDATE_OPTION,
    SnapshotMismatchError,
    _assert_snapshot,
    normalize_snapshot,
    render_snapshot,
)
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
#: pytest-asyncio's registered plugin name (``-p no:asyncio`` removes it).
_ASYNCIO_PLUGIN = "asyncio"
_ASYNC_FIXTURES_PLUGIN = "xstate_statemachine_async_fixtures"

#: 📝 Private names kept importable from here for `_paths` and older
#:    callers after the #268 split.
_REEXPORTED = (_build, _Built, _load_logic, _usage_error, SNAPSHOT_KEYS)


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


def pytest_sessionstart(session: Any) -> None:
    # 🕰️ For the cross-worker snapshot collision check (`_snapshots`): a
    #    file written AFTER this instant by another xdist worker is "this
    #    session"; an older file is a stale recording to be updated.
    #    Under xdist every worker starts within the same second, so a
    #    small grace keeps a worker that started late from calling its
    #    peer's first write stale.
    session._xsm_started_at = time.time() - 2.0


def pytest_configure(config: Any) -> None:
    config.addinivalue_line(
        "markers",
        f"{MARKER}(source, *, logic=None, strict_config=None, strict=None): "
        "build the machine the xsm_* fixtures serve. `source` is a JSON "
        "path (relative to the test file, then rootdir), a config dict or "
        "a MachineNode; `logic` a 'pkg.module:callable' string, a "
        "MachineLogic instance or a zero-argument callable returning a "
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
def xsm_machine(_xsm_built: _Built) -> MachineNode[Any]:
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
def xsm_interp(
    xsm_machine: MachineNode[Any], xsm_clock: SimulatedClock
) -> Any:
    """A started `SyncInterpreter` on ``xsm_clock``; stopped at teardown."""
    interp = SyncInterpreter(xsm_machine, clock=xsm_clock).start()
    yield interp
    if interp.status == "running":
        interp.stop()


def _pytest_asyncio_active(config: Any) -> bool:
    # 📝 Ask the plugin manager, per session: the runner must be *active*,
    #    not merely installed, so `-p no:asyncio` gives a clean skip.
    return bool(config.pluginmanager.hasplugin(_ASYNCIO_PLUGIN))


async def _start_async(
    machine: MachineNode[Any], clock: SimulatedClock
) -> Any:
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


def _number_token(arg: Union[int, float]) -> str:
    # 📝 `f"{1_000_000:g}"` is "1e+06", which the grammar rejects.
    if float(arg).is_integer():
        return f"+{int(arg)}"
    return f"+{arg}"


def _event_step(arg: Any) -> Optional[Dict[str, Any]]:
    """An event-with-payload step, or ``None`` when ``arg`` is a token.

    #268 battle: there was no way to send a payload; ``Event``, a
    ``{"type": ...}`` dict and a ``("TYPE", {payload})`` tuple now are.
    """
    if isinstance(arg, Event):
        return {"event": arg}
    if isinstance(arg, Mapping):
        if not isinstance(arg.get("type"), str) or not arg["type"]:
            raise TypeError(
                f"xsm_send_all: a dict step needs a non-empty 'type', "
                f"got {arg!r}"
            )
        return {"event": dict(arg)}
    if isinstance(arg, tuple):
        if (
            len(arg) != 2
            or not isinstance(arg[0], str)
            or not isinstance(arg[1], Mapping)
        ):
            raise TypeError(
                f"xsm_send_all: a tuple step is ('TYPE', {{payload}}), "
                f"got {arg!r}"
            )
        return {"event": {**dict(arg[1]), "type": arg[0]}}
    return None


def _token_steps(arg: Any) -> List[Dict[str, Any]]:
    from ...cli.commands.simulate import parse_events_arg

    if isinstance(arg, (int, float)) and not isinstance(arg, bool):
        return parse_events_arg(_number_token(arg), None)
    if not isinstance(arg, str):
        raise TypeError(
            f"xsm_send_all steps must be event names or '+ms' strings "
            f"(or numbers, Event objects, {{'type': ...}} dicts, "
            f"('TYPE', {{payload}}) tuples), got {arg!r}"
        )
    # 🛑 #268 battle: "A,B" was split into two events and "" sent nothing;
    #    a step is ONE varargs item (the CLI's comma list is a CLI thing).
    if not arg.strip() or "," in arg or arg.lstrip().startswith("++"):
        raise ValueError(
            f"xsm_send_all: bad step {arg!r}; pass one event name or "
            f"'+ms' per argument (no commas, not empty, one '+')"
        )
    return parse_events_arg(arg, None)


def _steps(args: Tuple[Any, ...]) -> List[Dict[str, Any]]:
    """Turn ``("A", "+500", ("B", {...}))`` into simulate-style commands."""
    out: List[Dict[str, Any]] = []
    for arg in args:
        step = _event_step(arg)
        out.extend([step] if step is not None else _token_steps(arg))
    return out


@pytest.fixture
def xsm_send_all(xsm_clock: SimulatedClock) -> Callable[..., None]:
    """``xsm_send_all(interp, "A", "+500", ("PAY", {"amount": 5}))``: send
    events in order; a ``"+N"`` token (or a number) advances ``xsm_clock``
    by N ms. A step is an event name, an `Event`, a ``{"type": ...}``
    dict, a ``("TYPE", {payload})`` tuple, ``"+N"`` or a number -- one
    per argument (no comma lists). Sync interpreters only."""

    def _send_all(interp: Any, *steps: Any) -> None:
        for cmd in _steps(steps):
            if "clock" in cmd:
                xsm_clock.increment(cmd["clock"])
            else:
                interp.send(cmd.get("event", cmd.get("send")))

    return _send_all


@pytest.fixture
def xsm_asend_all(
    xsm_clock: SimulatedClock,
) -> Callable[..., Awaitable[None]]:
    """Async twin of ``xsm_send_all``: ``await xsm_asend_all(ainterp,
    "A", "+500", "B")`` awaits each send and each clock advance."""

    async def _asend_all(interp: Any, *steps: Any) -> None:
        for cmd in _steps(steps):
            if "clock" in cmd:
                pending = xsm_clock.increment(cmd["clock"])
                if pending is not None:
                    await pending
            else:
                await interp.send(cmd.get("event", cmd.get("send")), wait=True)

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
