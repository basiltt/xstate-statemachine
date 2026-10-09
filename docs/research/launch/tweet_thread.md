> **DRAFT — do not post without maintainer approval**

# Tweet thread draft

1/ Most LLM agent loops are a `while True` with `if`/`elif` branches for
tools, retries, budgets, and human approval. Nothing enforces the rules —
the model's output *is* the control flow. We think that's backwards.

2/ `xstate-statemachine[agents]` runs your agent loop as an XState v5
statechart instead: idle → checking_budget → awaiting_model →
awaiting_tool / awaiting_human → done/error. The model proposes. The
machine decides.

3/ Tool allow-lists (`meta.tools`) are enforced *twice*: once as a guard,
and again inside the tool-execution service. A prompt-injected tool call
outside the allow-list gets a `ToolDeniedError`, not silent execution.

4/ Budgets (tokens/cost/turns) are guards on the single transition that's
allowed to call the model. One path in, one place enforcing the limit —
not a counter checked inconsistently across the codebase.

5/ Human-in-the-loop is a durable, persisted state (`awaiting_human`), not
a pending row you poll. It survives a process restart via SQLite or Redis,
including an escalation deadline.

6/ Structured output is validated per state (`meta.output_model`). On
failure a guarded `RETRY_OUTPUT` transition re-prompts —
bounded, not an infinite loop.

7/ Traces are JSONL/OTel-style, no message content by default, with secret
redaction on. Multi-agent patterns (supervisor, pipeline, debate) share a
`BudgetPlugin` via `spawn_agent`.

8/ It composes with what you already use: LangGraph (statechart as a node,
checkpointer-persisted; or a compiled graph as an invoke service) and
pydantic-ai (`Agent` as a service, or the statechart as a `Tool`). Not a
replacement for either.

9/ Fully offline demo, no API key: `pip install
"xstate-statemachine[agents]"`, then `python run.py --fake --prompt
"refund order 42"` in `examples/integrations/agents_support_bot`. Repo:
https://github.com/basiltt/xstate-statemachine Docs:
https://basiltt.github.io/xstate-statemachine/

---

## Before posting

- [ ] Verify current PyPI version number
- [ ] Verify all links resolve (repo, docs)
- [ ] Check every tweet is under 280 characters after final edits
- [ ] Maintainer approval obtained
