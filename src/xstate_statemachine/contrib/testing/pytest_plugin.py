# src/xstate_statemachine/contrib/testing/pytest_plugin.py
# -----------------------------------------------------------------------------
# 🧪 The pytest plugin: markers, `xsm_*` fixtures, snapshot assertions
# -----------------------------------------------------------------------------
# 🏛️ Registered UNCONDITIONALLY through the `pytest11` entry point, so this
#    module is loaded into every pytest session of every project that has
#    the library installed -- including ones that never heard of it. Three
#    rules follow (review amendments on #268):
#      1. Import only pytest and the core. No hypothesis, no contrib.
#      2. Without an `xstate_machine` marker nothing happens: fixtures are
#         defined but inert, no option is required, no output is added.
#      3. Every fixture is prefixed `xsm_` so it cannot shadow a user's own
#         `machine` / `clock` / `store` fixtures.
#    `-p no:xstate_statemachine` disables it entirely.
#
# 📝 Guard flipping and the executed-action record reuse `stub_logic`'s
#    own `ran=` / `guards=` parameters (core `testing_utils`); the plugin
#    adds no second recording mechanism.
# -----------------------------------------------------------------------------
"""pytest plugin for xstate-statemachine (``[testing]`` extra, #268)."""

from __future__ import annotations

import difflib
import importlib
import json
import pathlib
import sys
from typing import Any, Callable, Dict, Iterator, List, Mapping, Optional

import pytest

from ...clock import SimulatedClock
from ...factory import create_machine
from ...models import MachineNode
from ...sync_interpreter import SyncInterpreter
from ...testing_utils import stub_logic

__all__ = [
    "MARKER_MACHINE",
    "MARKER_GUARDS_FALSE",
    "assert_snapshot_matches",
    "comparable_snapshot",
    "send_all",
]

MARKER_MACHINE = "xstate_machine"
MARKER_GUARDS_FALSE = "xstate_guards_false"

#: 📝 Snapshot keys that vary run to run or carry no behavioural meaning
#:    for a test: versions, hashes, wall-clock instants, runtime bookkeeping.
_VOLATILE_KEYS = frozenset(
    {
        "version",
        "machine_hash",
        "machine_version",
        "taken_at",
        "deadlines",
        "scheduled_sends",
        "pending_events",
        "system",
        "chain_trips",
        "last_chain_error",
    }
)


# =============================================================================
# pytest hooks
# =============================================================================
def pytest_addoption(parser: Any) -> None:
    group = parser.getgroup("xstate", "xstate-statemachine")
    group.addoption(
        "--xsm-version",
        action="store_true",
        default=False,
        help="print the xstate-statemachine version and exit",
    )
    group.addoption(
        "--xsm-update-snapshots",
        action="store_true",
        default=False,
        help="rewrite snapshot files asserted with xsm_snapshot",
    )


def pytest_configure(config: Any) -> None:
    config.addinivalue_line(
        "markers",
        f"{MARKER_MACHINE}(source, *, logic=None, strict_config=None, "
        "strict=None): build the xsm_* fixtures from a chart -- a JSON "
        "path (relative to the test file, then rootdir), a dict, or a "
        "MachineNode. `logic` is 'pkg.module:callable' returning a "
        "MachineLogic; omitted -> stub logic.",
    )
    config.addinivalue_line(
        "markers",
        f"{MARKER_GUARDS_FALSE}(*names): with stub logic, force the named "
        "guards to return False. Fails loudly if `logic=` was given.",
    )


@pytest.hookimpl(tryfirst=True)
def pytest_cmdline_main(config: Any) -> Optional[int]:
    """``pytest --xsm-version``: print and return, like ``--version``.

    📝 Returning an int from this hook ends the session with that exit
    status before collection -- the mechanism pytest uses for its own
    ``--version`` / ``--fixtures``; no `SystemExit`, no "Exit:" banner.
    """
    if config.getoption("--xsm-version"):
        from ... import __version__

        sys.stdout.write(f"xstate-statemachine {__version__}\n")
        sys.stdout.flush()
        return 0
    return None


# =============================================================================
# Marker resolution
# =============================================================================
class _Spec:
    """The resolved `xstate_machine` marker of one test item."""

    __slots__ = (
        "source",
        "logic",
        "strict_config",
        "strict",
        "guards_false",
        "item_path",
        "rootdir",
    )

    def __init__(self, item: Any) -> None:
        marker = item.get_closest_marker(MARKER_MACHINE)
        if marker is None:
            raise pytest.UsageError(  # pragma: no cover - guarded by callers
                "xsm_* fixtures need an @pytest.mark.xstate_machine marker"
            )
        if not marker.args:
            raise pytest.UsageError(
                f"{item.nodeid}: @pytest.mark.{MARKER_MACHINE} needs the "
                "chart as its first argument (path, dict or MachineNode)"
            )
        self.source = marker.args[0]
        self.logic = marker.kwargs.get("logic")
        self.strict_config = marker.kwargs.get("strict_config")
        self.strict = marker.kwargs.get("strict")
        unknown = set(marker.kwargs) - {"logic", "strict_config", "strict"}
        if unknown:  # ⚠️ silent acceptance is a bug
            raise pytest.UsageError(
                f"{item.nodeid}: unknown {MARKER_MACHINE} option(s): "
                f"{sorted(unknown)}"
            )
        gf = item.get_closest_marker(MARKER_GUARDS_FALSE)
        self.guards_false = tuple(gf.args) if gf is not None else ()
        if self.guards_false and self.logic is not None:
            raise pytest.UsageError(
                f"{item.nodeid}: @pytest.mark.{MARKER_GUARDS_FALSE} only "
                "applies to stub logic; remove it or drop `logic=`"
            )
        self.item_path = pathlib.Path(str(item.path))
        self.rootdir = pathlib.Path(str(item.config.rootpath))

    def load_config(self) -> Any:
        src = self.source
        if isinstance(src, MachineNode):
            return src
        if isinstance(src, Mapping):
            return dict(src)
        if isinstance(src, (str, pathlib.Path)):
            p = pathlib.Path(src)
            candidates = (
                [p]
                if p.is_absolute()
                else [self.item_path.parent / p, self.rootdir / p]
            )
            for c in candidates:
                if c.is_file():
                    return json.loads(c.read_text(encoding="utf-8"))
            raise pytest.UsageError(
                f"{MARKER_MACHINE}: chart {src!r} not found (tried "
                + ", ".join(str(c) for c in candidates)
                + ")"
            )
        raise pytest.UsageError(
            f"{MARKER_MACHINE}: chart must be a path, dict or MachineNode, "
            f"got {type(src).__name__}"
        )

    def resolve_logic(self) -> Optional[Callable[..., Any]]:
        if self.logic is None:
            return None
        if callable(self.logic):
            return self.logic
        if not isinstance(self.logic, str) or ":" not in self.logic:
            raise pytest.UsageError(
                f"{MARKER_MACHINE}: logic must be 'pkg.module:callable', "
                f"got {self.logic!r}"
            )
        mod_name, _, attr = self.logic.partition(":")
        try:
            fn = getattr(importlib.import_module(mod_name), attr)
        except (ImportError, AttributeError) as exc:
            raise pytest.UsageError(
                f"{MARKER_MACHINE}: cannot import logic {self.logic!r}: {exc}"
            ) from exc
        if not callable(fn):
            raise pytest.UsageError(
                f"{MARKER_MACHINE}: logic {self.logic!r} is not callable"
            )
        return fn


def _spec(request: Any) -> _Spec:
    if request.node.get_closest_marker(MARKER_MACHINE) is None:
        pytest.fail(
            f"{request.fixturename} requires "
            f"@pytest.mark.{MARKER_MACHINE}(<chart>) on the test",
            pytrace=False,
        )
    return _Spec(request.node)


# =============================================================================
# Fixtures
# =============================================================================
@pytest.fixture
def xsm_ran() -> List[str]:
    """Names of every action the stub logic executed, in order."""
    return []


@pytest.fixture
def xsm_guards(request: Any) -> Dict[str, bool]:
    """Live guard table for stub logic; mutate it between sends."""
    if request.node.get_closest_marker(MARKER_MACHINE) is None:
        return {}
    spec = _Spec(request.node)
    return {name: False for name in spec.guards_false}


@pytest.fixture
def xsm_machine(
    request: Any, xsm_ran: List[str], xsm_guards: Dict[str, bool]
) -> MachineNode:
    """The chart named by the marker, with stub or user logic bound."""
    spec = _spec(request)
    cfg = spec.load_config()
    if isinstance(cfg, MachineNode):
        if spec.logic is not None or spec.guards_false:
            raise pytest.UsageError(
                f"{MARKER_MACHINE}: a MachineNode already carries its "
                "logic; `logic=` and guards_false do not apply"
            )
        return cfg
    factory = spec.resolve_logic()
    if factory is not None:
        logic = factory()
    else:
        logic = stub_logic(cfg, ran=xsm_ran, guards=xsm_guards)
    kwargs: Dict[str, Any] = {"logic": logic}
    if spec.strict_config is not None:
        kwargs["strict_config"] = spec.strict_config
    if spec.strict is not None:
        kwargs["strict"] = spec.strict
    return create_machine(cfg, **kwargs)


@pytest.fixture
def xsm_clock() -> SimulatedClock:
    return SimulatedClock()


@pytest.fixture
def xsm_interp(
    xsm_machine: MachineNode, xsm_clock: SimulatedClock
) -> Iterator[SyncInterpreter]:
    interp = SyncInterpreter(xsm_machine, clock=xsm_clock).start()
    try:
        yield interp
    finally:
        interp.stop()


@pytest.fixture
def xsm_ainterp(
    request: Any, xsm_machine: MachineNode, xsm_clock: SimulatedClock
) -> Any:
    """Async twin of `xsm_interp`; needs pytest-asyncio.

    📝 Declared as a plain fixture returning a coroutine-driving helper
    rather than an ``async def`` fixture, so the module imports and the
    fixture is *defined* even when pytest-asyncio is absent -- the skip
    then happens at request time with a message naming the package.
    """
    try:
        importlib.import_module("pytest_asyncio")
    except ImportError:
        pytest.skip(
            "xsm_ainterp needs pytest-asyncio "
            "(pip install pytest-asyncio) and an async test"
        )
    from ...interpreter import Interpreter

    started: List[Interpreter] = []

    async def _start() -> Interpreter:
        interp = await Interpreter(xsm_machine, clock=xsm_clock).start()
        started.append(interp)
        return interp

    def _finalize() -> None:
        # 🧹 stop() is a coroutine; when the test's loop is gone, drive a
        #    fresh one just for the shutdown.
        import asyncio

        for interp in started:
            if interp.status == "running":
                try:
                    asyncio.run(interp.stop())
                except RuntimeError:  # pragma: no cover - loop still open
                    pass

    request.addfinalizer(_finalize)
    return _start


@pytest.fixture
def xsm_store() -> Any:
    from ...persistence import MemoryStore

    return MemoryStore()


@pytest.fixture
def xsm_send_all() -> Callable[..., None]:
    return send_all


@pytest.fixture
def xsm_snapshot(request: Any) -> Callable[..., None]:
    update = bool(request.config.getoption("--xsm-update-snapshots"))
    base = pathlib.Path(str(request.node.path)).parent

    def _assert(interp: Any, path: Any) -> None:
        p = pathlib.Path(path)
        if not p.is_absolute():
            p = base / p
        assert_snapshot_matches(interp, p, update=update)

    return _assert


# =============================================================================
# Helpers (importable without the fixtures)
# =============================================================================
def send_all(interp: Any, *tokens: str) -> None:
    """``send_all(interp, "SUBMIT", "+2000", "PAY")`` -- the
    ``xsm simulate --events`` grammar: ``+N`` advances the interpreter's
    `SimulatedClock` by *N* ms, anything else is sent as an event type."""
    from ...cli.commands.simulate import parse_events_arg

    for cmd in parse_events_arg(",".join(tokens), None):
        if "clock" in cmd:
            clock = interp.clock
            if not isinstance(clock, SimulatedClock):
                raise TypeError(
                    "'+N' needs a SimulatedClock; this interpreter runs on "
                    f"{type(clock).__name__}"
                )
            result = clock.increment(cmd["clock"])
            if result is not None:  # pragma: no cover - async engine
                raise TypeError(
                    "send_all drives the sync engine; await "
                    "clock.increment() yourself on the async engine"
                )
        else:
            interp.send(cmd["send"])


def comparable_snapshot(interp: Any) -> Dict[str, Any]:
    """`get_persisted_snapshot()` minus everything that varies run to run."""

    def strip(node: Any) -> Any:
        if isinstance(node, dict):
            return {
                k: strip(v) for k, v in node.items() if k not in _VOLATILE_KEYS
            }
        if isinstance(node, list):
            return [strip(v) for v in node]
        return node

    return strip(interp.get_persisted_snapshot())


def assert_snapshot_matches(
    interp: Any, path: pathlib.Path, *, update: bool = False
) -> None:
    """Compare the deterministic part of a snapshot with *path*.

    With ``update=True`` (``--xsm-update-snapshots``) the file is
    (re)written and the assertion passes. A mismatch fails with a unified
    diff. Files are byte-identical across runs (sorted keys, 2-space
    indent, trailing newline).
    """
    actual = (
        json.dumps(comparable_snapshot(interp), sort_keys=True, indent=2)
        + "\n"
    )
    if update or not path.exists():
        if not update and not path.exists():
            pytest.fail(
                f"snapshot file {path} does not exist; run with "
                "--xsm-update-snapshots to create it",
                pytrace=False,
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(actual, encoding="utf-8")
        return
    expected = path.read_text(encoding="utf-8")
    if expected == actual:
        return
    diff = "".join(
        difflib.unified_diff(
            expected.splitlines(keepends=True),
            actual.splitlines(keepends=True),
            fromfile=str(path),
            tofile="actual",
        )
    )
    pytest.fail(
        f"snapshot mismatch for {path.name} "
        "(--xsm-update-snapshots to accept):\n" + diff,
        pytrace=False,
    )
