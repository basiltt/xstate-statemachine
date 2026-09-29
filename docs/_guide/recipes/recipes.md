---
title: "Recipes"
permalink: /guide/recipes/
description: "Worked, tested recipes: Stripe webhooks, APScheduler durable timers, RQ/arq/Dramatiq workers, a Streamlit/Gradio wizard, chatbot slot filling, feature-flag rollout, WebSocket reconnect, circuit breaker & retry, and a comparison with AWS Step Functions."
---

# Recipes

Each recipe answers a real problem with a chart and the code around it. None needs a plugin. The chart JSON imports into the Stately editor unchanged. The Python is 30–60 lines. Each page includes an `xsm simulate --events …` line that replays the flow from a shell, and each recipe has a test under [`tests/recipes/`](https://github.com/basiltt/xstate-statemachine/tree/main/tests/recipes). The code lives in [`examples/recipes/`](https://github.com/basiltt/xstate-statemachine/tree/main/examples/recipes). Every Python block on these pages runs in CI. Recipes that need a third-party library import it softly and are skipped with a reason when it is missing. No recipe adds a dependency to the package.

| Recipe | The problem | Library pieces | Persistence |
|:--|:--|:--|:--:|
| [Stripe webhooks](../stripe-webhooks/) | Signed, retried, out-of-order webhooks for a subscription lifecycle. FastAPI and Flask endpoints. | `persisted`, `IdempotencyPlugin`, stdlib `hmac` | ✅ |
| [APScheduler durable timers](../apscheduler-timers/) | 7- and 14-day follow-ups that survive deploys | `DueTimerScanner`, persisted deadlines | ✅ |
| [RQ / arq / Dramatiq workers](../task-queue-workers/) | Background jobs advancing one entity without lost updates | `persisted`, `apersisted`, `ConflictError` | ✅ |
| [Streamlit / Gradio wizard](../form-wizard/) | Multi-step forms with back/forward and validation | snapshots in session state, `xsm diagram` | session |
| [Chatbot slot filling](../slot-filling/) | Collect N answers in any order, nudge on silence | `always`, re-entering self-transitions, `after` | — |
| [Feature-flag rollout](../feature-flag-rollout/) | Staged exposure gated by live metrics, with rollback | `after` bake times, action `params`, `SimulatedClock` | optional |
| [WebSocket reconnect](../websocket-reconnect/) | Reconnect with jittered backoff, and never leak a socket | `RetryPolicy`, `from_callback` | — |
| [Circuit breaker & retry](../circuit-breaker-retry/) | An HTTP client that retries the right errors and fails fast | `RetryPolicy`, `CircuitBreaker` | — |
| [vs AWS Step Functions](../vs-step-functions/) | When a managed workflow service is the better tool | comparison | — |

## How to read a recipe

1. **The chart first.** Each page opens with the diagram and the `xsm simulate` line. Run it, then open `machine.json` in [Stately](../stately-export/) to see the same thing.
2. **Then the smallest runnable version.** The page's main Python block is self-contained, so you can paste it into a file and run it.
3. **Then the example folder.** That is the production-shaped version: split into modules, parameterised, and tested on both engines where timing matters.
4. **Guarantees boxes** appear wherever a recipe persists state. They say exactly what is and is not promised, and cite the programme-wide [Guarantees](../guarantees/) and [Security](../security/) items.

Looking for building blocks rather than recipes? See [Resilience patterns](../patterns/) (retry, dead-letter, circuit breaker) and [Persistence](../persistence/) (stores, locking, idempotency, durable timers).
