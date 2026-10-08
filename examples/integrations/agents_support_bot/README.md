# Support bot — an LLM agent as a statechart

A customer-support agent built on the `TOOL_LOOP` reference chart from
`xstate-statemachine[agents]`. It looks orders up, proposes refunds, and **cannot
issue a refund until a human approves it**. The model proposes, the machine
decides.

| Piece | Where |
|:--|:--|
| Chart | `machine.json`: `TOOL_LOOP` with `meta.tools` narrowed to `lookup_order` and `refund_order` |
| Tools | `bot.py`: `lookup_order` calls the [FastAPI orders example](../fastapi_orders/) `GET /orders/{id}` through an in-process `TestClient` (or a local stub when it cannot be imported); `refund_order` is `side_effect=True` |
| Human approval | `refund_order` parks the agent in `awaiting_human`, a normal persisted state with a one-hour escalation deadline |
| Budgets | 6 turns, 20k tokens, $0.05 per ticket (`BUDGETS`) |
| Persistence | `SQLiteStore("support.db")`: each ticket is a key, and approval resumes the stored run |
| Trace | `support-trace.jsonl`: one JSON line per model/tool step, `gen_ai.*` field names, no prompt content |

## 2-minute walkthrough (no API key)

```bash
pip install "xstate-statemachine[agents,fastapi]" httpx
cd examples/integrations/agents_support_bot
python run.py --fake --prompt "refund order 42"
```

```text
[ticket:1a2b3c4d] state=supportBot.awaiting_human waiting=True
  needs approval: {"id": "call_2_0", "name": "refund_order", "arguments": {"order_id": 42, "amount_cents": 2400}}
  human reviewer: approved
[ticket:1a2b3c4d] state=supportBot.done
answer: Order 42 has been refunded (24.00).
refunds executed: [{'order_id': 42, 'amount_cents': 2400}]
usage: {'turns': 3, 'input_tokens': 30, 'output_tokens': 15, 'cost_usd': 0.0}
```

What happened:

1. `FakeModel` (scripted and offline) asked for `lookup_order(42)`. That tool is in the state's allow-list, so `run_tool` ran it.
2. It then proposed `refund_order(42, 2400)`, a side-effect tool, so the chart moved to **`awaiting_human`** and `run_agent` returned. The snapshot, including the escalation deadline, is in `support.db`.
3. `run.py` played the reviewer. `bot.decide(key, approve=True)` sent `HUMAN_APPROVED` naming exactly the pending call id, and the refund ran once.

Run it again with `--reject`: the refund never executes, and the model is told it was declined.

In a real deployment, steps 2 and 3 are two HTTP requests, possibly hours apart and on different workers. See the FastAPI recipe in the [LLM agents guide](https://basiltt.github.io/xstate-statemachine/guide/integration-agents/).

## Real model (opt-in)

```bash
pip install openai        # or anthropic
export OPENAI_API_KEY=... # or ANTHROPIC_API_KEY
python run.py --provider openai --prompt "Where is order 42? Please refund it."
```

Without the SDK or the key, `run.py` exits with status 2 and one line naming
the fix (`pip install openai` / `OPENAI_API_KEY`); no ticket is started.

Only the model changes. The allow-list, budgets and human gate stay exactly as they were.

## Tests

```bash
python -m pytest tests -q       # FakeModel only; no key, no network
```

They cover: approval runs the refund exactly once, a rejected refund never runs, a
prompt-injected tool outside the allow-list ends in `error` (`tool_denied`), a looping
model is stopped by the turn budget, lookup goes through the FastAPI example, and
`run.py --fake` finishes offline.
