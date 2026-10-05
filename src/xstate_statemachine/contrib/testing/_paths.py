# src/xstate_statemachine/contrib/testing/_paths.py
# -----------------------------------------------------------------------------
# 🗺️ The `xsm_path` fixture: one test case per reachable configuration (#269)
# -----------------------------------------------------------------------------
# 🏛️ `graph.shortest_paths` already executes the real engine (stub logic,
#    simulated clock) to find a path to every configuration. This module
#    turns that into test generation: a test that requests `xsm_path` under
#    an `xstate_machine` marker is parametrised over those paths at
#    collection time, and `xsm_path.replay(xsm_interp, xsm_clock)` drives
#    the fixture's interpreter down one of them.
#
# 📝 Imported by `pytest_plugin` (which re-exports the hooks and fixture so
#    pytest finds them on the entry-point module). pytest + core only.
# -----------------------------------------------------------------------------
"""``xsm_path`` parametrisation (``pytest_generate_tests``)."""

from __future__ import annotations

import json
import pathlib
from typing import Any, List, Mapping

import pytest

from ...graph import Path, shortest_paths, simple_paths

__all__ = ["PATH_FIXTURE", "add_path_options", "generate_path_tests"]

PATH_FIXTURE = "xsm_path"


def _non_negative_int(text: str) -> int:
    """argparse type: ``0`` or more (a negative bound is a typo)."""
    import argparse

    value = int(text)
    if value < 0:
        raise argparse.ArgumentTypeError(f"must be >= 0, got {value}")
    return value


def add_path_options(group: Any) -> None:
    group.addoption(
        "--xsm-full-paths",
        action="store_true",
        default=False,
        help="parametrise xsm_path over every simple (acyclic) path "
        "instead of one shortest path per reachable configuration",
    )
    group.addoption(
        "--xsm-max-paths",
        type=_non_negative_int,
        default=1000,
        help="cap for --xsm-full-paths (default 1000)",
    )
    group.addoption(
        "--xsm-max-depth",
        type=_non_negative_int,
        default=50,
        help="maximum steps in a generated xsm_path (default 50)",
    )
    group.addoption(
        "--xsm-path-guards",
        choices=["true", "false", "both"],
        default="true",
        help="what stub guards return while generating xsm_path cases; "
        "'both' also explores every guard forced False",
    )


def _leaf(state_id: str) -> str:
    return state_id.rsplit(".", 1)[-1]


def _config_name(config: Any) -> str:
    return "+".join(sorted(_leaf(s) for s in config)) or "(none)"


def path_id(path: Path, initial: Any) -> str:
    """``path[editing->authenticating3DS->challenge]``."""
    configs = [initial] + [s.to_states for s in path.steps]
    names: List[str] = []
    for cfg in configs:
        name = _config_name(cfg)
        if not names or names[-1] != name:
            names.append(name)
    return f"path[{'->'.join(names)}]"


def generate_path_tests(metafunc: Any) -> None:
    """Body of ``pytest_generate_tests`` for ``xsm_path``."""
    if PATH_FIXTURE not in metafunc.fixturenames:
        return
    # 📝 Late import: `pytest_plugin` imports this module.
    from .pytest_plugin import _build, parse_marker

    item = metafunc.definition
    spec = parse_marker(item)
    if spec is None:
        # The fixture itself fails with the marker message at run time.
        return
    try:
        found = _cached_explore(item, spec, metafunc.config, _build)
    except pytest.UsageError:
        raise
    except Exception as exc:  # noqa: BLE001 -- reported per test, below
        # 🔥 #269 battle: a chart that cannot start used to abort the WHOLE
        #    collection with an engine traceback. Now it is one clear error
        #    on this test only; the rest of the session still runs.
        metafunc.parametrize(
            PATH_FIXTURE,
            [_PathError(f"{type(exc).__name__}: {exc}")],
            ids=["path[error]"],
            indirect=True,
        )
        return
    initial = found[0].final_states if found else frozenset()
    if found and found[0].steps:
        initial = found[0].steps[0].from_states
    metafunc.parametrize(
        PATH_FIXTURE,
        found,
        ids=[path_id(p, initial) for p in found],
        indirect=True,
    )


class _PathError:
    """Stand-in parameter: path generation failed for this test."""

    def __init__(self, message: str) -> None:
        self.message = message


#: ⚡ #269 battle: two test functions on one chart used to explore it twice
#:    (seconds each on a wide parallel chart). Keyed on everything that can
#:    change the result; a built `MachineNode` source keys on identity.
_CACHE_ATTR = "_xsm_path_cache"


def _cache_key(spec: Any, config: Any) -> Any:
    src = spec.source
    if isinstance(src, Mapping):
        try:
            src_key: Any = ("cfg", json.dumps(src, sort_keys=True))
        except (TypeError, ValueError):
            return None
    elif isinstance(src, (str, pathlib.Path)):
        src_key = ("file", str(src))
    else:
        src_key = ("node", id(src))
    opt = config.getoption
    return (
        src_key,
        spec.logic,
        spec.strict,
        spec.strict_config,
        tuple(spec.guards_false),
        opt("--xsm-path-guards"),
        opt("--xsm-max-depth"),
        opt("--xsm-full-paths"),
        opt("--xsm-max-paths"),
    )


def _cached_explore(
    item: Any, spec: Any, config: Any, build: Any
) -> List[Path]:
    cache = getattr(config, _CACHE_ATTR, None)
    if cache is None:
        cache = {}
        setattr(config, _CACHE_ATTR, cache)
    key = _cache_key(spec, config)
    if key is not None and str(key[0][0]) == "file":
        # 📝 Relative JSON paths resolve against the test file's dir.
        key = (str(item.path.parent),) + key
    if key is not None and key in cache:
        return list(cache[key])
    found = _explore(build(item, spec).machine, config)
    if key is not None:
        cache[key] = tuple(found)
    return found


def _explore(machine: Any, config: Any) -> List[Path]:
    opt = config.getoption
    guards = opt("--xsm-path-guards")
    depth = opt("--xsm-max-depth")
    found: List[Path]
    if opt("--xsm-full-paths"):
        found = simple_paths(
            machine,
            guards=guards,
            max_paths=opt("--xsm-max-paths"),
            max_depth=depth,
        )
    else:
        found = sorted(
            shortest_paths(machine, guards=guards, max_depth=depth).values(),
            key=lambda p: (len(p.steps), sorted(p.final_states)),
        )
    return list(found)


@pytest.fixture
def xsm_path(request: Any) -> Path:
    """The `graph.Path` this parametrised case covers. Call
    ``xsm_path.replay(xsm_interp, xsm_clock)`` to drive it; the
    interpreter then sits in ``xsm_path.final_states``."""
    param = getattr(request, "param", None)
    if isinstance(param, Path):
        return param
    if isinstance(param, _PathError):
        pytest.fail(
            f"{request.node.nodeid}: cannot generate {PATH_FIXTURE} cases "
            f"-- the machine does not start: {param.message}",
            pytrace=False,
        )
    from .pytest_plugin import MARKER

    pytest.fail(
        f"{request.node.nodeid}: the {PATH_FIXTURE} fixture needs an "
        f"@pytest.mark.{MARKER}(...) marker on the test",
        pytrace=False,
    )
    raise AssertionError("unreachable")  # pragma: no cover
