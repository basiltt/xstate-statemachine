# src/xstate_statemachine/cli/commands/dlq.py
# -----------------------------------------------------------------------------
# 💀 `xsm dlq` -- operate the dead-letter store (#293)
# -----------------------------------------------------------------------------
# 🔐 X0.8 guard rails -- a replay re-injects a message into production:
#
#    * ``replay`` is a DRY RUN unless ``--no-dry-run`` is given, and then
#      also requires ``--yes`` AND a non-empty ``--reason``;
#    * the envelope id is reused, so a store's inbox dedups a double replay;
#    * a record captured under a different machine structure / version is
#      refused without ``--force``;
#    * ``replay`` and ``purge`` write an audit row (who, why, when, what).
#
#    Records are redacted before they were written; ``show`` prints them
#    as stored.
# -----------------------------------------------------------------------------
"""The `dlq` subcommand: list, show, replay and purge dead letters."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, List, Optional

from ..ui import Column, Table
from . import get_console
from .snapshots import open_store

__all__ = ["open_dlq", "parse_age", "run_dlq"]

_AGE = re.compile(r"^(\d+(?:\.\d+)?)([smhd])$")
_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def parse_age(text: str) -> float:
    """``90s`` / ``15m`` / ``12h`` / ``7d`` → seconds."""
    m = _AGE.match(text.strip())
    if not m:
        raise SystemExit(f"invalid age {text!r}: use e.g. 90s, 15m, 12h, 7d")
    return float(m.group(1)) * _UNITS[m.group(2)]


def open_dlq(url: str) -> Any:
    """``sqlite:///path.db`` (or a bare path) → `SQLiteDeadLetterStore`."""
    from ...eda.dead_letter import SQLiteDeadLetterStore

    path = url
    if url.startswith("sqlite:"):
        store = open_store(url)
        return SQLiteDeadLetterStore(store)
    if "://" in url:
        raise SystemExit(
            f"unsupported dead-letter store {url!r}: use sqlite:///path.db"
        )
    return SQLiteDeadLetterStore(Path(path))


def _dispatcher(
    store_url: str, machine_files: List[str], logic: Optional[str]
) -> Any:
    from ...eda.dispatcher import InboundDispatcher
    from ...factory import create_machine
    from ...persistence import SQLiteInbox, SQLiteStore

    machines = {}
    for f in machine_files:
        cfg = json.loads(Path(f).read_text(encoding="utf-8"))
        m = create_machine(cfg, logic_modules=[logic] if logic else None)
        machines[str(m.id)] = m

    def machine_for(envelope_type: str) -> Any:
        parts = envelope_type.split(".")
        if len(parts) >= 3 and parts[0] == "xsm" and parts[1] in machines:
            return machines[parts[1]]
        if len(machines) == 1:
            return next(iter(machines.values()))
        return None

    store = open_store(store_url)
    inbox = SQLiteInbox(store) if isinstance(store, SQLiteStore) else None
    return InboundDispatcher(store, machine_for, inbox=inbox, max_attempts=1)


def _row(r: Any) -> List[str]:
    return [
        r.id,
        r.reason,
        r.machine_id,
        str(r.event.get("type")),
        str(r.attempts or ""),
        time.strftime("%Y-%m-%d %H:%M", time.gmtime(r.taken_at)),
        "yes" if r.resolved_at else "",
    ]


def _list(dlq: Any, *, include_resolved: bool, limit: int, as_json: bool):
    c = get_console()
    rows = dlq.list(include_resolved=include_resolved, limit=limit)
    if as_json:
        c.print(
            json.dumps(
                {
                    "count": len(rows),
                    "dead_letters": [r.to_dict() for r in rows],
                },
                indent=2,
                default=str,
            )
        )
        return
    c.blank()
    if not rows:
        c.print(c.style("no dead letters", "muted"))
        c.blank()
        return
    t = Table(
        [
            Column("Id", role="key", min_width=36, shrink=False),
            Column("Reason", min_width=6, shrink=False),
            Column("Machine", min_width=7),
            Column("Event", min_width=5, max_width=40),
            Column("Tries", min_width=5),
            Column("Captured (UTC)", min_width=16),
            Column("Resolved", min_width=8),
        ],
        zebra=True,
    )
    for r in rows:
        t.add(*_row(r))
    c.rule(f"dead letters ({len(rows)})")
    c.table(t)
    c.blank()


def _show(dlq: Any, record_id: str) -> None:
    rec = dlq.get(record_id)
    if rec is None:
        raise SystemExit(f"no dead letter with id {record_id!r}")
    get_console().print(json.dumps(rec.to_dict(), indent=2, default=str))


def _replay(dlq: Any, args: Any) -> None:
    from ...eda.dispatcher import ReplayRefusedError, replay_dead_letter

    c = get_console()
    dry_run = not bool(args.no_dry_run)
    if not dry_run and not args.yes:
        raise SystemExit("refusing to replay without --yes")
    if not (args.reason or "").strip():
        raise SystemExit('a replay needs --reason "why this is safe now"')
    if not args.store or not args.machine:
        raise SystemExit("replay needs --store URL and --machine FILE")
    disp = _dispatcher(args.store, args.machine, args.logic)
    try:
        res = replay_dead_letter(
            dlq,
            args.record_id,
            disp,
            reason=args.reason,
            dry_run=dry_run,
            force=bool(args.force),
        )
    except ReplayRefusedError as exc:
        c.error(str(exc))
        raise SystemExit(2) from exc
    for w in res.warnings:
        c.warn(w)
    if args.json:
        c.print(json.dumps(res.__dict__, indent=2))
    elif dry_run:
        c.info(
            f"dry run: {res.record_id} would be replayed "
            f"(re-run with --no-dry-run --yes)"
        )
    else:
        c.print(f"{res.record_id}: {res.outcome}")
    if not dry_run and res.outcome not in ("processed", "duplicate"):
        raise SystemExit(1)


def _purge(dlq: Any, args: Any) -> None:
    c = get_console()
    if not args.yes:
        raise SystemExit("refusing to purge without --yes")
    if not (args.reason or "").strip():
        raise SystemExit("a purge needs --reason")
    if bool(args.record_id) == bool(args.older_than):
        raise SystemExit("purge needs exactly one of --id or --older-than")
    if args.record_id:
        n = 1 if dlq.delete(args.record_id) else 0
        detail = {"id": args.record_id}
    else:
        cutoff = time.time() - parse_age(args.older_than)
        n = dlq.purge_older_than(cutoff)
        detail = {"older_than": args.older_than}
    detail["deleted"] = n
    audit = getattr(dlq, "audit", None)
    if callable(audit):
        audit("purge", args.record_id, args.reason, detail)
    if args.json:
        c.print(json.dumps({"deleted": n}))
    else:
        c.print(f"purged {n} dead letter(s)")


def run_dlq(args: Any) -> None:
    dlq = open_dlq(args.dlq)
    try:
        if args.dlq_command == "list":
            _list(
                dlq,
                include_resolved=bool(args.all),
                limit=args.limit,
                as_json=bool(args.json),
            )
        elif args.dlq_command == "show":
            _show(dlq, args.record_id)
        elif args.dlq_command == "replay":
            _replay(dlq, args)
        elif args.dlq_command == "purge":
            _purge(dlq, args)
        else:  # pragma: no cover - argparse enforces the choice
            raise SystemExit("usage: xsm dlq {list,show,replay,purge}")
    finally:
        dlq.close()
