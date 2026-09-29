> **DRAFT — do not post without maintainer approval**

# Awesome-list PR drafts

One PR per list. Each PR should touch only the relevant line(s) in that
list's README, in the correct alphabetical/category position.

## awesome-langchain

**PR title:** Add xstate-statemachine (statechart-based agent loops, composes with LangGraph)

**Entry line:**
```
- [xstate-statemachine](https://github.com/basiltt/xstate-statemachine) - Runs XState v5 statecharts in Python; an `[agents]` extra models LLM agent loops with tool allow-lists, budgets, timeouts, and durable human-in-the-loop, and composes with LangGraph (as a node, or the reverse).
```

**PR body:**
Adding `xstate-statemachine` under the agent-frameworks / tooling section.
It's a pure-Python statechart runtime (XState v5 JSON compatible) with an
optional `[agents]` extra for LLM agent loops. It's explicitly designed to
complement LangGraph rather than replace it — a statechart can run as one
LangGraph node with checkpointer-persisted state, or a compiled LangGraph
graph can be invoked as a service inside a statechart. See
`/guide/vs-langgraph/` in the docs for the detailed comparison. Repo:
https://github.com/basiltt/xstate-statemachine

---

## awesome-llm-agents

**Target repo:** verify before submitting — likely `kyrolabs/awesome-agents`
or an equivalent "awesome LLM agents" list; confirm the current canonical
list and its contribution guidelines before opening a PR, since these
lists get renamed/forked periodically.

**PR title:** Add xstate-statemachine — statechart-based agent loops (budgets, tool allow-lists, human-in-the-loop)

**Entry line:**
```
- [xstate-statemachine](https://github.com/basiltt/xstate-statemachine) - Python library that runs LLM agent loops as XState v5 statecharts: enforced tool allow-lists, token/cost/turn budgets, timeouts, durable human-in-the-loop, and structured output validation.
```

**PR body:**
Adding `xstate-statemachine`'s `[agents]` extra. The core idea is "the
model proposes, the machine decides" — the LLM is invoked as one service
inside a statechart, and the statechart (not the model's output) decides
what happens next. Notably, tool allow-lists are enforced both as a guard
and again inside the tool-execution service, so a prompt-injected tool
call outside the allow-list is refused rather than silently executed.
Repo: https://github.com/basiltt/xstate-statemachine

---

## awesome-python (vinta/awesome-python)

**PR title:** Add xstate-statemachine to State Machines / relevant section

**Entry line:**
```
* [xstate-statemachine](https://github.com/basiltt/xstate-statemachine) - Runs XState v5-compatible JSON statecharts in Python; async and sync interpreters, zero runtime deps.
```

**PR body:**
Adding a statechart/state-machine library. `xstate-statemachine` parses and
runs XState v5 JSON config, has both an async `Interpreter` and a blocking
`SyncInterpreter`, zero runtime dependencies, and supports Python 3.9–3.14.
Charts can be authored visually in the free Stately editor. Repo:
https://github.com/basiltt/xstate-statemachine — please advise if there's
a more specific section than "State Machines" this should go under.

---

## awesome-fastapi (mjhea0/awesome-fastapi)

**PR title:** Add xstate-statemachine (statechart runtime, FastAPI integration example)

**Entry line:**
```
* [xstate-statemachine](https://github.com/basiltt/xstate-statemachine) - XState v5-compatible statechart runtime for Python; includes a FastAPI example app (order lookup + human-gated refund via an agent statechart).
```

**PR body:**
Adding `xstate-statemachine`, which ships a runnable FastAPI integration
example (`examples/integrations/agents_support_bot`) demonstrating an LLM
agent loop as a statechart with a human-in-the-loop refund step, plus a
`--fake` mode that runs fully offline for review without an API key.
Repo: https://github.com/basiltt/xstate-statemachine

---

## awesome-django (wsvincent/awesome-django)

**PR title:** Add xstate-statemachine (statechart runtime usable from Django views/tasks)

**Entry line:**
```
* [xstate-statemachine](https://github.com/basiltt/xstate-statemachine) - XState v5-compatible statechart runtime for Python; the sync interpreter drops into Django views, management commands, and Celery tasks without asyncio.
```

**PR body:**
Adding `xstate-statemachine`. The `SyncInterpreter` is a blocking runtime
suited to Django's request/response cycle and worker tasks without
requiring asyncio. Zero runtime dependencies, Python 3.9–3.14. Repo:
https://github.com/basiltt/xstate-statemachine — happy to adjust wording
or section placement per maintainer preference.

---

## Before posting

- [ ] Verify current PyPI version number if mentioned in any entry
- [ ] Verify all links resolve, including confirming the correct
      awesome-llm-agents target repo
- [ ] Read each target list's CONTRIBUTING guidelines before opening a PR
- [ ] Maintainer approval obtained
