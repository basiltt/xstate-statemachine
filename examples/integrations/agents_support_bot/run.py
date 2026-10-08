# examples/integrations/agents_support_bot/run.py
"""Run one support ticket end to end.

    python run.py --fake --prompt "refund order 42"
    python run.py --provider openai --prompt "..."   # needs OPENAI_API_KEY

The refund parks in ``awaiting_human``; ``--approve`` (default) or
``--reject`` plays the human reviewer and resumes the same ticket from
SQLite.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import uuid
from pathlib import Path
from typing import List, Optional

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from bot import (  # noqa: E402
    ProviderUnavailable,
    SupportBot,
    fake_model,
    provider_model,
)
from xstate_statemachine.contrib.agents import pending_approval  # noqa: E402


def _args(argv: Optional[List[str]]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--fake", action="store_true", help="offline FakeModel")
    src.add_argument("--provider", choices=["openai", "anthropic"])
    p.add_argument("--prompt", default="refund order 42")
    p.add_argument("--db", default="support.db")
    p.add_argument("--trace", default="support-trace.jsonl")
    p.add_argument("--reject", action="store_true", help="human says no")
    return p.parse_args(argv)


async def main(argv: Optional[List[str]] = None) -> int:
    a = _args(argv)
    if a.fake:
        m = re.search(r"\d+", a.prompt)
        model = fake_model(int(m.group()) if m else 42, approve=not a.reject)
    else:
        try:
            model = provider_model(a.provider)
        except ProviderUnavailable as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
    bot = SupportBot(model, db=a.db, trace=a.trace)
    key = f"ticket:{uuid.uuid4().hex[:8]}"
    try:
        res = await bot.ticket(key, a.prompt)
        print(f"[{key}] state={res.final_state} waiting={res.waiting}")
        if res.waiting:
            for call in pending_approval(res.context):
                print(f"  needs approval: {json.dumps(call)}")
            verdict = "rejected" if a.reject else "approved"
            print(f"  human reviewer: {verdict}")
            res = await bot.decide(key, approve=not a.reject)
        print(f"[{key}] state={res.final_state}")
        print(f"answer: {res.output}")
        print(f"refunds executed: {bot.refunds}")
        print(f"usage: {res.usage}")
        return 0 if res.error is None else 1
    finally:
        bot.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
