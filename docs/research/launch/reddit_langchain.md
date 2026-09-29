> **DRAFT — do not post without maintainer approval**

# r/LangChain draft

**Angle:** incremental adoption — drop a statechart into an existing
LangGraph graph, don't ask anyone to rip LangGraph out. Be respectful:
this is a complement, not a "LangGraph is bad" post.

**Suggested flair:** Discussion / Resources (whatever the sub uses)

## Title

Using a statechart as one node in a LangGraph graph, for the parts that need hard guarantees (budgets, tool allow-lists, human-in-the-loop)

## Body

We like LangGraph for orchestrating the graph of an agent system, but for
a few specific problems inside a single agent's loop we wanted stronger,
more declarative guarantees than a Python node function easily gives us:
enforcing a tool allow-list per phase, hard token/cost/turn budgets, and a
human-approval step that has to survive a process restart. So we built
`xstate-statemachine[agents]` (`pip install "xstate-statemachine[agents]"`)
— it runs XState v5-compatible JSON statecharts in pure Python, and has a
small "agent loop" pattern on top: idle → checking_budget →
awaiting_model → awaiting_tool / awaiting_human → done/error, with
timeouts and retries as first-class states.

This is explicitly designed to sit *inside* a LangGraph graph, not replace
it:

- The statechart's snapshot can live in a LangGraph checkpointer, so a
  single LangGraph node can wrap "run this statechart one step" and the
  usual checkpoint/replay/time-travel tooling still works.
- We ship `route_by_statechart` so LangGraph's conditional edges can defer
  to the statechart's current state instead of duplicating that logic in
  a router function.
- The reverse direction also works: a compiled LangGraph graph can be
  invoked as a service inside a statechart state, with streaming, if you
  want the statechart to be the "outer" control layer for just one agent's
  tool-calling loop while LangGraph still owns the rest of the pipeline.

Why not just write the logic in a LangGraph node? You can — this isn't
solving something LangGraph can't do. What we wanted was enforcement that
doesn't rely on every node author remembering to check the allow-list: the
tool-allow-list check happens both as a guard *and* again inside the
tool-execution service, so a prompt-injected tool call outside the
allow-list is refused (`ToolDeniedError`) even if a node forgets to guard
against it.

There's a `/guide/vs-langgraph/` page that tries to be fair about the
trade-offs, and a runnable example
(`examples/integrations/agents_support_bot`, `python run.py --fake`) that
works fully offline via a `FakeModel`.

Repo: https://github.com/basiltt/xstate-statemachine
Docs: https://basiltt.github.io/xstate-statemachine/

Genuinely curious whether others have hit the same "need harder guarantees
inside one node" problem, and how you solved it.

---

## Before posting

- [ ] Verify current PyPI version number
- [ ] Verify all links resolve (repo, docs, `/guide/vs-langgraph/`, example)
- [ ] Re-read for tone — must not read as anti-LangGraph
- [ ] Maintainer approval obtained
