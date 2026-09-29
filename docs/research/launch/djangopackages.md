> **DRAFT — do not post without maintainer approval**

# Django Packages listing draft

Target: djangopackages.org (or the relevant grid site) submission fields.

## Name

xstate-statemachine

## Category suggestion

Utilities / State Machines (or "Task Queues & Async" as a secondary grid
if the primary category doesn't exist — verify available categories before
submitting)

## Repo

https://github.com/basiltt/xstate-statemachine

## Docs

https://basiltt.github.io/xstate-statemachine/

## Description (≤ 2 sentences)

A pure-Python runtime for XState v5-compatible JSON statecharts, with a
blocking `SyncInterpreter` that drops into Django views, management
commands, and Celery tasks without asyncio. Zero runtime dependencies,
Python 3.9–3.14, with an optional `[agents]` extra for building
statechart-governed LLM agent loops.

## Grid suggestions

- Add to a "State Machines" grid if one exists; otherwise propose creating
  one, since Django Packages currently has few (if any) statechart-focused
  entries.
- Could also be cross-listed on a "Background Tasks" or "Workflow" grid
  given the durable/human-in-the-loop features, but the primary fit is
  state machines.

## Notes

- This is not a Django-specific package — be upfront about that in the
  submission notes so it's categorized correctly (framework-agnostic,
  sync interpreter is what makes it Django-friendly).
- Django Packages typically pulls metadata (stars, last commit, PyPI
  version) automatically from GitHub/PyPI — no need to hardcode those in
  the submission.

---

## Before posting

- [ ] Verify current PyPI version number is correctly detected/linked
- [ ] Verify all links resolve (repo, docs)
- [ ] Confirm actual available categories/grids on Django Packages before
      choosing one
- [ ] Maintainer approval obtained
