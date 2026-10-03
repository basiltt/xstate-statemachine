# src/xstate_statemachine/cli/commands/snapshots.py
# -----------------------------------------------------------------------------
# 📸 `xsm snapshots` -- what is in a store, and what is stale (#263)
# -----------------------------------------------------------------------------
"""The `snapshots` subcommand: list keys in a persistence store; `--stale`
finds instances written by a different machine version."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import unquote, urlparse

from ..ui import Column, Table
from . import get_console

__all__ = ["open_store", "run_snapshots"]


#: 🛡️ #263 battle: a machine JSON is a chart, not a data dump; refuse a
#: larger file before reading it (a 100 MB `[[[[` must not be parsed).
MAX_MACHINE_JSON_BYTES = 16 * 1024 * 1024
#: Exit status of `--fail-if-stale` when stale keys exist (a CI/deploy
#: gate); 2 is argparse's usage error and every refused input below.
EXIT_STALE = 1
EXIT_USAGE = 2
#: `--stale` scans the label index of every key (cheap), then caps output.
_SCAN_ALL = 2**62


def _fail(msg: str) -> "SystemExit":
    # 📝 stderr, so `--json > out.json` never captures an error line.
    print(f"xsm snapshots: error: {msg}", file=sys.stderr)
    return SystemExit(EXIT_USAGE)


def open_store(url: str, *, must_exist: bool = False) -> Any:
    """``sqlite:///path.db`` → `SQLiteStore`; ``file:///dir`` → `FileStore`;
    ``memory://`` → a fresh (empty) `MemoryStore`.

    Args:
        url: The store URL.
        must_exist: Refuse a database file / directory that does not exist
            (the `xsm snapshots` inspection path must never create one).
    """
    from ...persistence import FileStore, MemoryStore, SQLiteStore

    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    # 🪟 `sqlite:///C:/x.db` parses to path "/C:/x.db"; strip the slash.
    path = unquote(parsed.path)
    if parsed.netloc and scheme != "memory":
        path = f"//{parsed.netloc}{path}"
    if len(path) >= 3 and path[0] == "/" and path[2] == ":":
        path = path[1:]
    elif scheme == "sqlite" and path.startswith("/") and not parsed.netloc:
        # 🐛 #263 battle: the guide's `sqlite:///app.db` opened `/app.db`
        #    at the filesystem root. SQLAlchemy's rule: three slashes is
        #    relative, four (`sqlite:////abs/app.db`) is absolute.
        path = path[1:]
    if scheme == "memory":
        if must_exist:
            # 📝 #263 battle: a fresh in-process store is always empty --
            #    listing it answered "store is empty", exit 0, a lie.
            raise _fail("memory:// is a new empty store in this process")
        return MemoryStore()
    if scheme not in ("sqlite", "file"):
        raise _fail(
            f"unsupported store URL {url!r}: use sqlite:///path.db or "
            f"file:///dir"
        )
    if must_exist:
        # 📝 #263 battle: SQLiteStore/FileStore CREATE a missing target --
        #    a typo in --store silently reported "store is empty".
        p = Path(path)
        ok = p.is_file() if scheme == "sqlite" else p.is_dir()
        if not ok:
            what = "database file" if scheme == "sqlite" else "directory"
            raise _fail(f"no such {what}: {path!r}")
    return SQLiteStore(path) if scheme == "sqlite" else FileStore(path)


def _machine_version(json_file: str) -> Optional[str]:
    """The chart's ``version`` -- every bad input is exit 2, no traceback."""
    from ...exceptions import XStateMachineError
    from ...factory import create_machine
    from ...testing_utils import stub_logic

    p = Path(json_file)
    try:
        if not p.is_file():
            raise _fail(f"machine JSON {json_file!r} is not a file")
        if p.stat().st_size > MAX_MACHINE_JSON_BYTES:
            raise _fail(
                f"machine JSON {json_file!r} is larger than "
                f"{MAX_MACHINE_JSON_BYTES} bytes"
            )
        cfg = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(cfg, dict):
            raise _fail(f"{json_file!r} is not a machine (not an object)")
        return create_machine(cfg, logic=stub_logic(cfg)).version
    except (OSError, ValueError, RecursionError, XStateMachineError) as exc:
        raise _fail(f"cannot read machine JSON {json_file!r}: {exc}") from None
    except (TypeError, AttributeError, KeyError) as exc:
        # ⚠️ #263 battle: `create_machine` lets some malformed configs
        #    (`"states": 5`) escape as a bare TypeError/AttributeError --
        #    reported to the maintainer; never a traceback here.
        raise _fail(
            f"{json_file!r} is not a valid machine: "
            f"{type(exc).__name__}: {exc}"
        ) from None


def _row(store: Any, key: str, now: float) -> Optional[Dict[str, Any]]:
    rec = store.load(key)
    if rec is None:
        return None
    try:
        blob = json.loads(rec.snapshot)
        status = blob.get("status")
        leaves = blob.get("state_ids") or []
    except (ValueError, AttributeError):
        status, leaves = "?", []
    # 🛡️ X0.5: never `context` -- it is user data (PII).
    return {
        "key": key,
        "version": rec.version,
        "machine_version": rec.machine_version or None,
        "status": status,
        "state_ids": leaves,
        "age_s": max(0.0, now - rec.updated_at),
        "deadlines": len(rec.deadlines),
    }


def _label_pairs(store: Any, prefix: str, limit: int) -> List[Any]:
    # 💡 Duck-typed: third-party stores without `list_versions` fall back
    #    to one full `load()` per key.
    lv = getattr(store, "list_versions", None)
    if callable(lv):
        return list(lv(prefix=prefix, limit=limit))
    pairs = []
    for key in store.list_keys(prefix=prefix, limit=limit):
        rec = store.load(key)
        if rec is not None:
            pairs.append((key, rec.machine_version))
    return pairs


def _is_stale(found: str, expected: Optional[str]) -> bool:
    # 🏛️ #263 battle: agree with restore (`_check_machine_version`): a
    #    chart with no version never mismatches, and an unlabelled record
    #    (0.10.x) cannot be checked -- restore warns, it does not refuse.
    return bool(expected is not None and found and found != expected)


def _rows(
    store: Any,
    *,
    prefix: str,
    limit: int,
    now: float,
    stale_against: Any = None,
    stale: bool = False,
) -> Tuple[List[Dict[str, Any]], int]:
    """Rows to show and the total number of matching keys."""
    if stale:
        # 📝 #263 battle: the limit used to cap the keys SCANNED, so
        #    `--stale` silently missed every stale key past the first 1000.
        keys = [
            k
            for k, mv in _label_pairs(store, prefix, _SCAN_ALL)
            if _is_stale(mv, stale_against)
        ]
    else:
        keys = list(store.list_keys(prefix=prefix, limit=limit))
    out = []
    for key in keys[:limit]:
        row = _row(store, key, now)
        if row is not None:
            out.append(row)
    return out, len(keys)


def _age(seconds: float) -> str:
    if seconds < 90:
        return f"{seconds:.0f}s"
    if seconds < 5400:
        return f"{seconds / 60:.0f}m"
    if seconds < 172800:
        return f"{seconds / 3600:.1f}h"
    return f"{seconds / 86400:.1f}d"


def _cell(text: str) -> str:
    # 🛡️ #263 battle: a key/label with "\n", "\r" or another control char
    #    split one row across lines (and let a key forge a fake row); the
    #    plain table shows its escaped form. `--json` carries it verbatim.
    if text.isprintable():
        return text
    return "".join(ch if ch.isprintable() else repr(ch)[1:-1] for ch in text)


def _emit_json(
    store_url: str,
    machine_version: Optional[str],
    stale: bool,
    rows: List[Dict[str, Any]],
    total: int,
) -> None:
    get_console().print(
        json.dumps(
            {
                "store": store_url,
                "machine_version": machine_version,
                "stale_only": stale,
                "count": len(rows),
                # 📝 #263 battle: `total` > `count` means `--limit` cut it.
                "total": total,
                "truncated": total > len(rows),
                "snapshots": rows,
            },
            indent=2,
        )
    )


def _emit_table(
    store_url: str,
    machine_version: Optional[str],
    stale: bool,
    rows: List[Dict[str, Any]],
    total: int,
) -> None:
    c = get_console()
    title = "stale snapshots" if stale else "snapshots"
    subtitle = store_url + (
        f"   machine version {machine_version!r}" if machine_version else ""
    )
    c.blank()
    if not rows:
        c.print(
            c.style(
                "no stale snapshots" if stale else "store is empty", "muted"
            )
        )
        c.blank()
        return
    t = Table(
        [
            Column("Key", role="key", min_width=10, max_width=40),
            Column("Ver", min_width=3),
            Column("Machine", min_width=7),
            Column("Status", min_width=6),
            Column("State", min_width=8, max_width=40),
            Column("Age", min_width=4),
        ],
        zebra=True,
    )
    for r in rows:
        mv = r["machine_version"]
        mv_txt = _cell(mv) if mv is not None else c.style("-", "muted")
        if stale or (machine_version and mv != machine_version):
            mv_txt = c.style(_cell(str(mv)), "warn")
        t.add(
            _cell(r["key"]),
            str(r["version"]),
            mv_txt,
            _cell(str(r["status"])),
            _cell(
                ", ".join(str(s).rsplit(".", 1)[-1] for s in r["state_ids"])
            ),
            _age(r["age_s"]),
        )
    shown = f"{len(rows)}" if total == len(rows) else f"{len(rows)} of {total}"
    c.rule(f"{title} ({shown})  {c.style(subtitle, 'muted')}")
    c.table(t)
    c.blank()


def run_snapshots(
    store_url: str,
    *,
    json_file: Optional[str] = None,
    stale: bool = False,
    prefix: str = "",
    limit: int = 1000,
    as_json: bool = False,
    fail_if_stale: bool = False,
) -> None:
    """List a store's keys; with ``stale`` only those a deploy must migrate.

    Args:
        store_url: ``sqlite:///path.db`` or ``file:///dir``.
        json_file: Machine JSON whose ``version`` is the reference.
        stale: Only keys whose label differs from the chart's.
        prefix: Only keys starting with this.
        limit: Maximum rows printed (``--stale`` still scans every key).
        as_json: Emit JSON instead of a table.
        fail_if_stale: Exit `EXIT_STALE` when any stale key exists.

    Raises:
        SystemExit: `EXIT_USAGE` on bad input; `EXIT_STALE` per above.
    """
    from ...exceptions import XStateMachineError

    if (stale or fail_if_stale) and not json_file:
        raise _fail("--stale needs the machine JSON to compare against")
    if limit < 0:
        raise _fail("--limit must be >= 0")
    stale = stale or fail_if_stale
    machine_version = _machine_version(json_file) if json_file else None
    try:
        store = open_store(store_url, must_exist=True)
        try:
            rows, total = _rows(
                store,
                prefix=prefix,
                limit=limit,
                now=time.time(),
                stale_against=machine_version,
                stale=stale,
            )
        finally:
            close = getattr(store, "close", None)
            if callable(close):
                close()
    except (OSError, XStateMachineError) as exc:
        # 📝 #263 battle: an unreadable directory / corrupt row was a
        #    traceback; it is a one-line error and exit 2 now.
        raise _fail(f"{type(exc).__name__}: {exc}") from None
    emit = _emit_json if as_json else _emit_table
    emit(store_url, machine_version, stale, rows, total)
    if fail_if_stale and total:
        raise SystemExit(EXIT_STALE)
