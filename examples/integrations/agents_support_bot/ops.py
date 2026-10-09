# examples/integrations/agents_support_bot/ops.py
"""Operate the support bot: the day after the walkthrough.

    python ops.py open --key t-1 --prompt "refund order 42"
    python ops.py pending
    python ops.py approve t-1
    python ops.py reject t-1
    python ops.py scan

Every command is a separate process on the same ``support.db`` -- the way
the ticket, the reviewer and the timeout worker run in production (on
different replicas, hours apart). Offline: the model is the scripted
`FakeModel`. ``open`` scripts the first two turns; ``approve`` /
``reject`` script only the CLOSING answer, because a resumed run
continues the conversation stored in the snapshot.
"""

# -----------------------------------------------------------------------------
# 🏛️ Why a second script: `run.py` plays the whole ticket in one process.
#    An operator never does -- approval arrives later, from another process,
#    and an unanswered ticket is escalated by ONE `DueTimerScanner`, never by
#    a reload (a reload re-arms the timer on the new clock).
# -----------------------------------------------------------------------------

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import List, Optional

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from bot import SupportBot, fake_model, stub_orders  # noqa: E402
from xstate_statemachine.contrib.agents import (  # noqa: E402
    FakeModel,
    pending_approval,
)
from xstate_statemachine.persistence import DueTimerScanner  # noqa: E402

#: How many store keys `pending` / `scan` look at in one go.
LIST_LIMIT = 1000


def _args(argv: Optional[List[str]]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--db", default="support.db")
    p.add_argument("--trace", default="support-trace.jsonl")
    sub = p.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("open", help="start a ticket (parks on a refund)")
    o.add_argument("--key", required=True)
    o.add_argument("--prompt", default="refund order 42")
    o.add_argument("--order", type=int, default=42)
    sub.add_parser("pending", help="tickets waiting for a human")
    for verb in ("approve", "reject"):
        sub.add_parser(verb, help=f"{verb} a parked ticket").add_argument(
            "key"
        )
    s = sub.add_parser("scan", help="escalate matured human deadlines")
    s.add_argument(
        "--at",
        type=float,
        default=None,
        help="pretend wall-clock time (epoch seconds); default now",
    )
    return p.parse_args(argv)


def _bot(a: argparse.Namespace, model: FakeModel) -> SupportBot:
    return SupportBot(model, fetch=stub_orders(), db=a.db, trace=a.trace)


def _waiting(bot: SupportBot) -> List[str]:
    keys = bot.store.list_keys(limit=LIST_LIMIT)
    out = []
    for key in keys:
        rec = bot.store.load(key)
        if rec is None:
            continue
        snap = json.loads(rec.snapshot)
        if any(s.endswith("awaiting_human") for s in snap["state_ids"]):
            out.append(key)
    return out


async def _open(a: argparse.Namespace) -> int:
    bot = _bot(a, fake_model(a.order))
    try:
        res = await bot.ticket(a.key, a.prompt)
        print(f"[{a.key}] state={res.final_state} waiting={res.waiting}")
        return 0
    finally:
        bot.close()


def _pending(a: argparse.Namespace) -> int:
    bot = _bot(a, FakeModel([]))
    try:
        for key in _waiting(bot):
            snap = json.loads(bot.store.load(key).snapshot)
            for call in pending_approval(snap["context"]):
                print(f"{key}  {call['name']} {json.dumps(call['arguments'])}")
        return 0
    finally:
        bot.close()


async def _decide(a: argparse.Namespace, approve: bool) -> int:
    # 📝 Only the closing answer: the conversation so far is in the store.
    text = "Refund done." if approve else "Sorry, the refund was declined."
    bot = _bot(a, FakeModel([{"text": text}]))
    try:
        if a.key not in _waiting(bot):
            print(
                f"error: {a.key} is not waiting for a human", file=sys.stderr
            )
            return 2
        res = await bot.decide(a.key, approve=approve)
        print(f"[{a.key}] state={res.final_state} answer={res.output}")
        print(f"refunds executed: {bot.refunds}")
        return 0
    finally:
        bot.close()


def _scan(a: argparse.Namespace) -> int:
    bot = _bot(a, FakeModel([]))
    try:
        scanner = DueTimerScanner(bot.store, lambda key: bot.machine)
        woke = scanner.run_once(now=a.at if a.at is not None else time.time())
        print(f"escalated: {woke}")
        return 0
    finally:
        bot.close()


def main(argv: Optional[List[str]] = None) -> int:
    a = _args(argv)
    if a.cmd == "open":
        return asyncio.run(_open(a))
    if a.cmd == "pending":
        return _pending(a)
    if a.cmd in ("approve", "reject"):
        return asyncio.run(_decide(a, a.cmd == "approve"))
    return _scan(a)


if __name__ == "__main__":
    raise SystemExit(main())
