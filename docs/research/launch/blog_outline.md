> **DRAFT — do not post without maintainer approval**

# Blog outline: "The model proposes, the machine decides"

Working title. Target length: ~1800–2400 words. Audience: Python devs
building LLM agents who are past the toy-demo stage and hitting reliability
problems.

## 1. The problem with `while True` agent loops

- Ad hoc loops accumulate special-case branches for tools, retries, human
  approval, timeouts — no single place enforces the rules.
- Failure mode: a tool call slips through outside its intended phase
  (prompt injection, model hallucination, or just a missed `if`).

## 2. The core idea: the model proposes, the machine decides

- LLM output is *never* trusted as the source of control flow.
- A statechart's current state + guards decide what's actually allowed to
  happen next; the model's output is one input to that decision, not the
  decision itself.

## 3. What a minimal agent statechart looks like

- Walk through TOOL_LOOP states: `idle → checking_budget →
  awaiting_model → awaiting_tool / awaiting_human → done/error`,
  `timed_out` + retry.
- Show the JSON config for 2–3 states, kept short.

## 4. Enforcing tool allow-lists twice, on purpose

- `meta.tools` per state as the declared allow-list.
- Guard check is advisory (defense in depth, fails fast, cheap).
- The `run_tool` service re-checks the allow-list itself — this is the
  actual enforcement boundary, because guards can be bypassed by a bug
  elsewhere but the service is the last line before a tool executes.
- Concrete example: a prompt-injected tool call outside the allow-list →
  `ToolDeniedError`, not silent execution.

## 5. Budgets as guards, not side-channel bookkeeping

- Token/cost/turn budgets expressed as guards on the single transition
  that invokes the model.
- Why this is safer than checking a counter inside the model-calling code:
  there's exactly one path in, so exactly one place enforces the limit.

## 6. Timeouts and durable human-in-the-loop

- `after` timeouts for model calls, tool calls, waiting on a human.
- `awaiting_human` as a state that's actually persisted (SQLiteStore /
  Redis) — the process can restart and resume waiting, including an
  escalation deadline.
- Why "durable state" beats "a pending row in a database plus manual
  polling logic."

## 7. Structured output that retries itself

- `meta.output_model` validated per state.
- On validation failure, transition to a `RETRY_OUTPUT` state that
  re-prompts, optionally via `instructor`.
- Trade-off: bounded retries, not infinite re-prompt loops.

## 8. Traces without leaking your prompts

- JSONL / OTel-style traces, no message content by default.
- Secret redaction as a default, not an opt-in.
- Why this matters for shipping agent logs to a shared observability
  backend.

## 9. Where this fits next to LangGraph and pydantic-ai

- Not a replacement for either — it plugs in.
- LangGraph: statechart as one node (checkpointer-backed snapshot,
  `route_by_statechart`), or a compiled graph as an invoke service.
- pydantic-ai: `Agent` as an invoke service (usage counted against
  budgets), or the statechart exposed as a pydantic-ai `Tool`.
- Link out to `/guide/vs-langgraph/`, `/guide/vs-burr/`,
  `/guide/vs-statelyai-agent/` for people who want the detailed comparison.

## 10. Try it: the offline example

- `pip install "xstate-statemachine[agents]"`.
- `examples/integrations/agents_support_bot`: FastAPI order-lookup +
  refund gated by `awaiting_human`.
- `python run.py --fake --prompt "refund order 42"` runs fully offline via
  `FakeModel` — no API key needed to see the whole flow, including the
  human-approval gate.
- Close with links: repo, docs, comparison pages.

---

## Before posting

- [ ] Verify current PyPI version number referenced in install commands
- [ ] Verify all links resolve (repo, docs, three comparison pages)
- [ ] Maintainer approval obtained
