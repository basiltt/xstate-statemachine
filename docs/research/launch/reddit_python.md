> **DRAFT — do not post without maintainer approval**

# r/Python draft

**Suggested flair:** Projects (or "I Made This")

## Title

xstate-statemachine: XState-compatible statecharts in Python, now with an `[agents]` extra for LLM agent loops

## Body

Hi r/Python — maintainer of `xstate-statemachine` here.

It's a pure-Python library (`pip install xstate-statemachine`, zero runtime
deps, Python 3.9–3.14) that parses and runs XState v5 JSON statecharts.
Two interpreters ship: an async `Interpreter` for asyncio apps and a
blocking `SyncInterpreter` for scripts, CLIs, and threads. Charts can be
designed visually in the free Stately editor and exported as JSON — no
proprietary format, no vendor lock-in on the runtime side.

What's new: an optional `[agents]` extra
(`pip install "xstate-statemachine[agents]"`) that models an LLM agent loop
as a statechart instead of an ad hoc `while` loop with `if`/`elif` branches
scattered around tool calls. The core idea is "the model proposes, the
machine decides" — the LLM only ever proposes a next action; the statechart
enforces what's actually allowed.

Things this gives you for free, as statechart primitives rather than
custom code:

- Per-state tool allow-lists (`meta.tools`), enforced both as a guard and
  again inside the tool-execution service — so a prompt-injected tool call
  outside the allow-list is refused, not executed.
- Budgets (tokens/cost/turns) as guards on the one transition that invokes
  the model.
- `after` timeouts on model calls, tool calls, and waiting on a human.
- A durable `awaiting_human` state that survives a process restart
  (SQLite or Redis-backed snapshot).
- Structured output validation per state with an automatic re-prompt state.
- JSONL traces with no message content by default, plus secret redaction.

There's a reference multi-agent setup (supervisor / pipeline / debate)
using `spawn_agent` and a shared `BudgetPlugin`, a `FakeModel` for fully
offline deterministic tests, and soft-imported OpenAI/Anthropic adapters.
It also plugs into existing stacks rather than replacing them — see
`/guide/vs-langgraph/` and `/guide/vs-burr/` for how it composes with
LangGraph and Burr, and a runnable FastAPI example
(`examples/integrations/agents_support_bot`, `python run.py --fake`).

Repo: https://github.com/basiltt/xstate-statemachine
Docs: https://basiltt.github.io/xstate-statemachine/

Feedback on the API, especially the guard/service split for tool
enforcement, is very welcome.

---

## Before posting

- [ ] Verify current PyPI version number
- [ ] Verify all links resolve (repo, docs, guide pages, example path)
- [ ] Maintainer approval obtained
