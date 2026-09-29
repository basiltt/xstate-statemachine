> **DRAFT — do not post without maintainer approval**

# Stately community post draft

Target: Stately Discord (#showcase or similar channel) and/or Stately
GitHub Discussions. Adjust tone slightly per venue — Discord shorter and
more casual, GitHub Discussions can keep the full version below.

## Post

Hey all — wanted to share a Python runtime for XState-exported charts,
in case it's useful to anyone building outside JS/TS.

`xstate-statemachine` (`pip install xstate-statemachine`) parses and runs
XState v5-compatible JSON statecharts. Design in the Stately editor,
export the JSON, run it in Python with either an async `Interpreter` or a
blocking `SyncInterpreter` — no rewriting the chart, no reimplementing the
semantics by hand. Zero runtime dependencies, Python 3.9–3.14, and there's
a CLI (`xsm`) that generates action/guard/service boilerplate straight
from the JSON so you're not hand-typing function stubs.

The reason I'm posting here specifically: the newest piece is an
`[agents]` extra that uses a statechart to govern an LLM agent loop —
`idle → checking_budget → awaiting_model → awaiting_tool /
awaiting_human → done/error`, with `after` timeouts and retries as
first-class states. It's designed around "the model proposes, the machine
decides": the LLM only ever proposes an action, and the chart enforces
what's actually allowed (tool allow-lists per state, token/cost/turn
budgets as guards, a durable persisted `awaiting_human` state that
survives a restart). It felt like a natural extension of what statecharts
are already good at, and the Stately editor works for authoring/reviewing
these agent charts the same as any other chart.

There's a fully offline example (FastAPI order-lookup + human-gated
refund, runs via `--fake` with no API key) if anyone wants to see the
whole flow end to end:
`examples/integrations/agents_support_bot` in the repo.

Repo: https://github.com/basiltt/xstate-statemachine
Docs: https://basiltt.github.io/xstate-statemachine/

Would love feedback from people who've designed charts in Stately and run
them elsewhere — especially anything Python-runtime-specific that felt
off compared to the JS/TS runtimes.

---

## Before posting

- [ ] Verify current PyPI version number
- [ ] Verify all links resolve (repo, docs, example path)
- [ ] Check current channel/etiquette norms in Stately Discord before
      posting (self-promo channel vs. general)
- [ ] Maintainer approval obtained
