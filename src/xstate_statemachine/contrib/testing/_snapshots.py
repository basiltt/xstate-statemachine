# src/xstate_statemachine/contrib/testing/_snapshots.py
# -----------------------------------------------------------------------------
# 📸 Snapshot files for the `xsm_snapshot` fixture (#268)
# -----------------------------------------------------------------------------
# 🏛️ Split out of `pytest_plugin.py` (#268 battle). A snapshot file records
#    only `state_ids`, `value`, `context` and `status`, rendered with sorted
#    keys, a fixed indent and a trailing newline: two runs, two machines,
#    two hash seeds produce byte-identical files.
# -----------------------------------------------------------------------------
"""Internal: snapshot normalisation, rendering and assertion."""

from __future__ import annotations

import difflib
import json
import os
import pathlib
import tempfile
from typing import Any, Dict, Mapping, Tuple, Union

import pytest

from ._marker import _usage_error

UPDATE_OPTION = "--xsm-update-snapshots"

#: 📝 What a snapshot file records. Everything else in `get_snapshot()` --
#: `taken_at`, `machine_hash`, `version`, `deadlines` wall times, pending
#: events -- is either non-deterministic or an implementation detail of the
#: persistence layout, and would make files churn without behaviour changing.
SNAPSHOT_KEYS: Tuple[str, ...] = ("state_ids", "value", "context", "status")

#: Per-session record of which test wrote which snapshot file.
_WRITERS = pytest.StashKey[Dict[pathlib.Path, Tuple[str, str]]]()
#: Windows extended-length path prefixes `resolve()` may return.
_LONG_PREFIX = "\\\\?\\"
_UNC_PREFIX = "\\\\?\\UNC\\"


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


def _canonical(value: Any) -> Any:
    """JSON ``default=`` hook with a hash-seed-independent result.

    📝 #268 battle: ``default=str`` rendered a ``set`` in hash order, so a
    snapshot recorded under one ``PYTHONHASHSEED`` failed under the next.
    Sets become sorted lists; everything else ``str`` (as before).
    """
    if isinstance(value, (set, frozenset)):
        items = [json.loads(json.dumps(v, default=_canonical)) for v in value]
        return sorted(items, key=lambda v: json.dumps(v, sort_keys=True))
    return str(value)


def normalize_snapshot(
    snapshot: Union[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    """Reduce a ``get_snapshot()`` blob to its deterministic, behavioural
    part: ``state_ids``, ``value``, ``context`` and ``status``."""
    data = json.loads(snapshot) if isinstance(snapshot, str) else snapshot
    return {key: data.get(key) for key in SNAPSHOT_KEYS if key in data}


def render_snapshot(normalized: Mapping[str, Any]) -> str:
    """The byte-exact file form: sorted keys, two-space indent, newline.

    Non-JSON values render deterministically (see ``_canonical``)."""
    return (
        json.dumps(
            normalized,
            indent=2,
            sort_keys=True,
            default=_canonical,
        )
        + "\n"
    )


def _interp_snapshot(interp: Any) -> Dict[str, Any]:
    """Normalised state of a live interpreter, context taken un-stringified
    (``get_snapshot()`` has already applied ``default=str``)."""
    normalized = normalize_snapshot(interp.get_snapshot())
    if "context" in normalized:
        normalized["context"] = interp.context
    return normalized


def _real(path: pathlib.Path) -> pathlib.Path:
    """``resolve()`` without Windows' extended-length prefix.

    📝 #268 battle: under ``-n 4`` on Windows, ``resolve()`` of a path
    another worker was creating came back with the ``\\\\?\\`` prefix, which
    is never "inside" the plain rootdir -- a correct snapshot path was
    refused as an escape, intermittently.
    """
    text = str(path.resolve())
    if text.startswith(_UNC_PREFIX):
        text = "\\\\" + text[len(_UNC_PREFIX) :]
    elif text.startswith(_LONG_PREFIX):
        text = text[len(_LONG_PREFIX) :]
    return pathlib.Path(text)


def _snapshot_path(item: Any, path: Union[str, pathlib.Path]) -> pathlib.Path:
    p = pathlib.Path(path)
    base = pathlib.Path(str(item.path)).parent
    if not p.is_absolute():
        p = base / p
    resolved = _real(p)
    root = _real(pathlib.Path(str(getattr(item.config, "rootpath", base))))
    # 🛡️ #268 battle (X0.10): `--xsm-update-snapshots` WRITES this path.
    #    `resolve()` follows symlinks, so a link pointing out is refused too.
    if root not in resolved.parents and resolved != root:
        if _real(base) not in resolved.parents:
            raise _usage_error(
                item,
                f"snapshot path {str(path)!r} resolves outside the project "
                f"({resolved}); keep snapshot files under the rootdir",
            )
    return resolved


def _atomic_write(target: pathlib.Path, text: str) -> None:
    """Write via a sibling temp file + ``os.replace`` so a reader (or a
    second xdist worker) never sees a torn file."""
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        dir=str(target.parent), prefix=f".{target.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        # 📝 `mkstemp` creates 0o600; a recorded snapshot is a normal file.
        os.chmod(tmp, 0o644)
        os.replace(tmp, target)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def _claim(item: Any, target: pathlib.Path, text: str) -> None:
    """Refuse two different tests recording DIFFERENT content to one file
    in the same session (the last would win silently)."""
    writers = item.config.stash.setdefault(_WRITERS, {})
    previous = writers.get(target)
    if previous is not None and previous[0] != item.nodeid:
        if previous[1] != text:
            raise _usage_error(
                item,
                f"snapshot {target} was already recorded with different "
                f"content by {previous[0]}; give each test its own file",
            )
    elif previous is None and _written_this_session(item, target):
        # 📝 reviewer H2 (#268 battle): under `-n 4` the stash is per
        #    WORKER, so two tests on different workers writing different
        #    content to one path last-won silently. Another worker's write
        #    is visible on disk (atomic `os.replace`): a file newer than
        #    this session that already differs is the same collision.
        on_disk = target.read_text(encoding="utf-8")
        if on_disk != text:
            raise _usage_error(
                item,
                f"snapshot {target} was already recorded with different "
                f"content in this session (another xdist worker); give "
                f"each test its own file",
            )
    writers[target] = (item.nodeid, text)


def _written_this_session(item: Any, target: pathlib.Path) -> bool:
    """``True`` when *target* exists and was modified after this pytest
    session started (so a stale file from an older run never trips the
    cross-worker check -- updating it is the point of the flag)."""
    try:
        mtime = target.stat().st_mtime
    except OSError:
        return False
    started = getattr(item.session, "_xsm_started_at", None)
    if started is None:
        return False
    return mtime >= started


def _assert_snapshot(
    item: Any, interp: Any, path: Union[str, pathlib.Path]
) -> None:
    target = _snapshot_path(item, path)
    actual = render_snapshot(_interp_snapshot(interp))
    if item.config.getoption(UPDATE_OPTION):
        _claim(item, target, actual)
        _atomic_write(target, actual)
        return
    if not target.is_file():
        raise SnapshotMismatchError(
            target,
            f"no snapshot file at {target}; run pytest {UPDATE_OPTION} "
            f"to record it",
        )
    # 📝 `read_text` translates CRLF (git autocrlf) to LF.
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
