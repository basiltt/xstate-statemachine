> **DRAFT — do not post without maintainer approval**

# Show HN draft

## Title (<80 chars)

Show HN: Statecharts for LLM agents – "the model proposes, the machine decides"

## Body (~250 words)

`xstate-statemachine` is a Python library (`pip install xstate-statemachine`)
that runs XState v5-compatible JSON statecharts, with an async `Interpreter`
and a blocking `SyncInterpreter`. It's pure Python, zero runtime deps,
supports 3.9–3.14, and charts can be designed visually in the Stately editor
and dropped straight into your codebase.

The new `xstate-statemachine[agents]` extra applies the same idea to LLM
agent loops. Instead of letting the model decide what happens next, the
model is invoked as *one service* inside a statechart: `idle →
checking_budget → awaiting_model → awaiting_tool / awaiting_human →
done/error`, with a `timed_out` state and retries.

Concretely this buys you things that are usually hand-rolled and easy to
get wrong:

- Per-state tool allow-lists (`meta.tools`) enforced twice — once as an
  advisory guard, and again inside the tool-running service, so a
  prompt-injected tool call outside the allow-list is refused
  (`ToolDeniedError`), not silently executed.
- Token/cost/turn budgets as guards on the single transition that's allowed
  to call the model.
- `after` timeouts for model calls, tool calls, and human responses.
- Human-in-the-loop as a durable, persisted state (`awaiting_human`) that
  survives a process restart via SQLite or Redis.
- Structured output validated per state, with an automatic re-prompt state
  (`RETRY_OUTPUT`) on validation failure.
- Traces with no message content by default, plus secret redaction.

It composes with LangGraph (as a node, or the reverse) and pydantic-ai
(as a tool, or the reverse) rather than replacing them. There's a runnable
example (FastAPI order-lookup + human-gated refund) that works fully
offline with a `FakeModel`.

Repo: https://github.com/basiltt/xstate-statemachine
Docs: https://basiltt.github.io/xstate-statemachine/

## Code snippet

```python
from xstate_statemachine import create_machine
from xstate_statemachine.agents import run_agent, FakeModel

# TOOL_LOOP-style chart: idle -> checking_budget -> awaiting_model -> ...
machine = create_machine(tool_loop_config, logic=agent_logic)

model = FakeModel(script=[
    {"tool_call": "lookup_order", "args": {"order_id": 42}},
    {"content": "Your order ships tomorrow."},
])

result = run_agent(machine, model=model, prompt="Where is order 42?")
print(result.output)
```

## Notes for maintainer

- Confirm current PyPI version before posting.
- HN prefers no marketing language; keep the title as literal as possible.
- Be ready to answer "how is this different from LangGraph?" — link
  `/guide/vs-langgraph/`.

---

## Before posting

- [ ] Verify current PyPI version number matches text/snippets
- [ ] Verify all links resolve (repo, docs, comparison pages)
- [ ] Maintainer approval obtained
