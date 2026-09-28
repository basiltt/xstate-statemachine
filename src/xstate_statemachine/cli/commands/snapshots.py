# src/xstate_statemachine/cli/commands/snapshots.py
# -----------------------------------------------------------------------------
# 📸 `xsm snapshots` -- what is in a store, and what is stale (#263)
# -----------------------------------------------------------------------------
"""The `snapshots` subcommand: list keys in a persistence store; `--stale`
finds instances written by a different machine version."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import unquote, urlparse

from ..ui import Column, Table
from . import get_console

__all__ = ["open_store", "run_snapshots"]


def open_store(url: str) -> Any:
    """``sqlite:///path.db`` → `SQLiteStore`; ``file:///dir`` → `FileStore`;
    ``memory://`` → a fresh (empty) `MemoryStore`."""
    from ...persistence import FileStore, MemoryStore, SQLiteStore

    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    # 🪟 `sqlite:///C:/x.db` parses to path "/C:/x.db"; strip the slash.
    path = unquote(parsed.path)
    if parsed.netloc and scheme != "memory":
        path = f"//{parsed.netloc}{path}"
    if len(path) >= 3 and path[0] == "/" and path[2] == ":":
        path = path[1:]
    if scheme == "sqlite":
        return SQLiteStore(path)
    if scheme == "file":
        return FileStore(path)
    if scheme == "memory":
        return MemoryStore()
    raise SystemExit(
        f"unsupported store URL {url!r}: use sqlite:///path.db, "
        f"file:///dir or memory://"
    )


def _rows(
    store: Any, *, prefix: str, limit: int, now: float
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for key in store.list_keys(prefix=prefix, limit=limit):
        rec = store.load(key)
        if rec is None:
            continue
        try:
            blob = json.loads(rec.snapshot)
            status = blob.get("status")
            leaves = blob.get("state_ids") or []
        except ValueError:
            status, leaves = "?", []
        out.append(
            {
                "key": key,
                "version": rec.version,
                "machine_version": rec.machine_version or None,
                "status": status,
                "state_ids": leaves,
                "age_s": max(0.0, now - rec.updated_at),
                "deadlines": len(rec.deadlines),
            }
        )
    return out


def _age(seconds: float) -> str:
    if seconds < 90:
        return f"{seconds:.0f}s"
    if seconds < 5400:
        return f"{seconds / 60:.0f}m"
    if seconds < 172800:
        return f"{seconds / 3600:.1f}h"
    return f"{seconds / 86400:.1f}d"


def run_snapshots(
    store_url: str,
    *,
    json_file: Optional[str] = None,
    stale: bool = False,
    prefix: str = "",
    limit: int = 1000,
    as_json: bool = False,
) -> None:
    c = get_console()
    if stale and not json_file:
        raise SystemExit("--stale needs the machine JSON to compare against")
    machine_version: Optional[str] = None
    if json_file:
        from ...factory import create_machine
        from ...testing_utils import stub_logic

        cfg = json.loads(Path(json_file).read_text(encoding="utf-8"))
        machine_version = create_machine(cfg, logic=stub_logic(cfg)).version
    store = open_store(store_url)
    try:
        rows = _rows(store, prefix=prefix, limit=limit, now=time.time())
    finally:
        close = getattr(store, "close", None)
        if callable(close):
            close()
    if stale:
        rows = [r for r in rows if r["machine_version"] != machine_version]

    if as_json:
        c.print(
            json.dumps(
                {
                    "store": store_url,
                    "machine_version": machine_version,
                    "stale_only": stale,
                    "count": len(rows),
                    "snapshots": rows,
                },
                indent=2,
            )
        )
        return

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
        mv_txt = mv if mv is not None else c.style("-", "muted")
        if stale or (machine_version and mv != machine_version):
            mv_txt = c.style(str(mv), "warn")
        t.add(
            r["key"],
            str(r["version"]),
            mv_txt,
            str(r["status"]),
            ", ".join(s.rsplit(".", 1)[-1] for s in r["state_ids"]),
            _age(r["age_s"]),
        )
    c.rule(f"{title} ({len(rows)})  {c.style(subtitle, 'muted')}")
    c.table(t)
    c.blank()
