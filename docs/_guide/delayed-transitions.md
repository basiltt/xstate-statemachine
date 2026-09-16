---
title: "Delayed Transitions"
description: "Timer-based auto-transitions with after — timeouts, polling, and auto-progression."
---

Delayed transitions let a state **automatically transition** after a specified time delay. No event needed — the machine moves on its own when the timer expires. This is perfect for session timeouts, polling loops, auto-save debouncing, and any workflow that involves waiting.

## What Are Delayed Transitions?

In a normal state machine, transitions only fire when an **event** arrives. Delayed transitions break that rule: they fire after a **timer** expires. You configure them with the `after` property on a state, mapping millisecond delays to target states.

```
           5 min              30 sec
  active ─────────► warning ──────────► expired
    ▲                  │
    └── ACTIVITY ──────┘   (user clicks EXTEND → back to active)
```

When the machine enters a state with `after` timers, those timers start immediately. If the machine leaves that state before a timer fires (because of an event), the timer is **cancelled automatically**.

## JSON After Syntax

The `after` property is a dictionary mapping **millisecond delays** (as strings in JSON) to transition targets:

```json
{
  "after": {
    "3000": "nextState"
  }
}
```

After 3000 ms (3 seconds) in this state, the machine transitions to `"nextState"`.

## Basic Example: Session Timeout

A session that warns the user before expiring:

```json
{
  "id": "sessionTimeout",
  "initial": "active",
  "states": {
    "active": {
      "after": {
        "300000": "warning"
      },
      "on": {
        "ACTIVITY": "active"
      }
    },
    "warning": {
      "after": {
        "30000": "expired"
      },
      "on": {
        "EXTEND": "active"
      }
    },
    "expired": {
      "type": "final"
    }
  }
}
```

Running it:

```python
from xstate_statemachine import create_machine, SyncInterpreter, MachineLogic

config = {
    "id": "sessionTimeout",
    "initial": "active",
    "states": {
        "active": {
            "after": {"300000": "warning"},
            "on": {"ACTIVITY": "active"}
        },
        "warning": {
            "after": {"30000": "expired"},
            "on": {"EXTEND": "active"}
        },
        "expired": {"type": "final"}
    }
}

machine = create_machine(config)
interp = SyncInterpreter(machine).start()

print(interp.active_state_ids)
# {'sessionTimeout.active'}

# User does something — timer resets
interp.send("ACTIVITY")
print(interp.active_state_ids)
# {'sessionTimeout.active'}  (timer restarted)

interp.stop()
```

This machine:

1. Starts in `active`
2. After 5 minutes of inactivity, moves to `warning`
3. The user gets 30 seconds to click "EXTEND" or it moves to `expired`
4. Any `ACTIVITY` event re-enters `active`, **resetting** the 5-minute timer

## After with Actions

Delayed transitions can trigger actions, just like event-driven transitions:

```json
{
  "monitoring": {
    "after": {
      "5000": {
        "target": "next",
        "actions": "logTimeout"
      }
    }
  }
}
```

```python
from xstate_statemachine import create_machine, SyncInterpreter, MachineLogic

config = {
    "id": "timedAction",
    "initial": "waiting",
    "states": {
        "waiting": {
            "after": {
                "5000": {
                    "target": "done",
                    "actions": "logTimeout"
                }
            }
        },
        "done": {"type": "final"}
    }
}

class TimedLogic(MachineLogic):
    def logTimeout(self, interpreter, context, event, action_def):
        print("Timer expired — transitioning to done")

machine = create_machine(config, logic=TimedLogic())
interp = SyncInterpreter(machine).start()
# After 5 seconds, "logTimeout" fires and machine moves to "done"
interp.stop()
```

## After with Guards

You can conditionally block a delayed transition using a guard:

```json
{
  "monitoring": {
    "after": {
      "60000": {
        "target": "stale",
        "guard": "noRecentData"
      }
    }
  }
}
```

If the guard `noRecentData` returns `False` when the timer fires, the transition is **skipped** — the machine stays in `monitoring`.

```python
from xstate_statemachine import create_machine, SyncInterpreter, MachineLogic

config = {
    "id": "guardedTimer",
    "initial": "monitoring",
    "context": {"lastPing": 0},
    "states": {
        "monitoring": {
            "after": {
                "60000": {
                    "target": "stale",
                    "guard": "noRecentData"
                }
            },
            "on": {
                "PING": {"actions": "recordPing"}
            }
        },
        "stale": {
            "on": {"RESET": "monitoring"}
        }
    }
}

class MonitorLogic(MachineLogic):
    def noRecentData(self, context, event):
        """Returns True if no PING has ever been received (lastPing is still 0)."""
        return context.get("lastPing", 0) == 0

    def recordPing(self, interpreter, context, event, action_def):
        import time
        context["lastPing"] = time.time()

machine = create_machine(config, logic=MonitorLogic())
interp = SyncInterpreter(machine).start()

# If PING arrives before 60s, lastPing becomes non-zero
# and the guard returns False, preventing the stale transition
interp.send("PING")
print(interp.active_state_ids)
# {'guardedTimer.monitoring'}

interp.stop()
```

> **Note:** Guard functions receive `(context, event)` and must return a `bool`. They must be synchronous.

## Multiple Timers per State

A single state can have **multiple** `after` timers running simultaneously:

```json
{
  "monitoring": {
    "after": {
      "5000":   {"target": "monitoring", "actions": "heartbeat"},
      "60000":  {"target": "stale",      "guard": "noRecentData"},
      "300000": "timeout"
    }
  }
}
```

All three timers start when `monitoring` is entered:

- **5 seconds:** self-transition with `heartbeat` action (re-enters, restarting all timers)
- **60 seconds:** conditional move to `stale` (only if guard passes)
- **5 minutes:** unconditional move to `timeout`

> **Tip:** The shortest timer fires first. If the 5-second heartbeat re-enters the state, **all** timers reset — so the 60s and 300s timers effectively restart too.

## Timer Reset

When a state is **re-entered** (via an event transition or a self-transition), all `after` timers for that state are **cancelled and restarted**. This is key to implementing patterns like "idle timeout" — every user action resets the clock.

```json
{
  "active": {
    "after": {
      "300000": "warning"
    },
    "on": {
      "ACTIVITY": "active"
    }
  }
}
```

Every `ACTIVITY` event re-enters `active`, which cancels the existing 5-minute timer and starts a fresh one.

> **Warning:** Self-transitions (targeting the same state) will cause exit actions, timer cancellation, entry actions, and timer restart. This is intentional — it's how XState works.

## Pythonic After

The `State` class accepts an `after` parameter — a dict mapping millisecond delays to targets:

```python
from xstate_statemachine import State, StateMachine, SyncInterpreter, action

class SessionMachine(StateMachine):
    machine_id = "session"

    active  = State("active",  initial=True, after={300000: "warning"},
                     on={"ACTIVITY": "active"})
    warning = State("warning", after={30000: "expired"},
                     on={"EXTEND": "active"})
    expired = State("expired", final=True)

machine = SessionMachine.create_machine()
interp = SyncInterpreter(machine).start()

print(interp.active_state_ids)
# {'session.active'}

interp.send("ACTIVITY")
print(interp.active_state_ids)
# {'session.active'}

interp.stop()
```

Using the functional API:

```python
from xstate_statemachine import State, build_machine, SyncInterpreter

active  = State("active",  initial=True, after={300000: "warning"},
                on={"ACTIVITY": "active"})
warning = State("warning", after={30000: "expired"},
                on={"EXTEND": "active"})
expired = State("expired", final=True)

machine = build_machine(id="session", states=[active, warning, expired])
interp = SyncInterpreter(machine).start()
interp.stop()
```

Using the builder API:

```python
from xstate_statemachine import MachineBuilder, SyncInterpreter

machine = (
    MachineBuilder("session")
    .state("active",  initial=True, after={300000: "warning"},
           on={"ACTIVITY": "active"})
    .state("warning", after={30000: "expired"},
           on={"EXTEND": "active"})
    .state("expired", final=True)
    .build()
)

interp = SyncInterpreter(machine).start()
interp.stop()
```

## After in Nested States

Delayed transitions work inside compound (hierarchical) states. Timers in a child state are cancelled when the parent state is exited:

```json
{
  "id": "nestedTimer",
  "initial": "loggedIn",
  "states": {
    "loggedIn": {
      "initial": "dashboard",
      "states": {
        "dashboard": {
          "after": {
            "60000": {"target": "dashboard", "actions": "refreshData"}
          }
        },
        "settings": {}
      },
      "on": {
        "LOGOUT": "loggedOut"
      }
    },
    "loggedOut": {}
  }
}
```

When `LOGOUT` fires, the machine exits `dashboard` (cancelling its 60-second refresh timer) and then exits `loggedIn`.

## Sync vs Async Timers

| Interpreter | Timer Behavior |
|-------------|----------------|
| `Interpreter` (async) | Schedules through the interpreter's `Clock`. By default (`RealClock`) that's `loop.call_later`, the same primitive `asyncio.sleep` uses, so timers run concurrently with your event loop. |
| `SyncInterpreter` | Also schedules through a `Clock`. With the default `RealClock` a timer is a deadline recorded in a heap — **no thread is started**. Due timers fire when `send()` or `tick()` next runs, on the caller's own thread. |

> **Tip:** For real-time timer behavior (actual wall-clock delays), use the async `Interpreter` with `asyncio`, or call `RealClock.pump()` / `SyncInterpreter.tick()` periodically to fire due `SyncInterpreter` timers if you aren't calling `send()` often enough on your own.

> **`after` guarantees "not before", never "at".** Both engines route every timer through the same priority lane so a due `after` or delayed send does not queue behind a backlog of already-pending external events — see [Controlling Time](#controlling-time) below. It can still fire late while other machines on the same loop finish their macrosteps — measured in [Production Characteristics § 2](../production-characteristics/#2-after-timers-are-best-effort-and-starve-under-load). On the `SyncInterpreter`, timers now fire on the thread that calls `send()`/`tick()`, never on a background thread ([§ 3](../production-characteristics/#3-the-syncinterpreter-threading-contract)).

### Measuring lateness with `event.lateness_ms`

Every `after` and delayed-`send()` event delivered to your actions is an `AfterEvent`. It carries two raw clock readings — `scheduled_for` (when the timer was due) and `fired_at` (when it actually fired) — plus a convenience property, `lateness_ms`, that computes `max(0.0, (fired_at - scheduled_for) * 1000.0)`. Read it from inside the action that handles the fired timer to alarm on real drift instead of inferring timer starvation from symptoms:

```python
import asyncio
from xstate_statemachine import create_machine, Interpreter, MachineLogic

config = {
    "id": "watchdog",
    "initial": "waiting",
    "states": {
        "waiting": {
            "after": {"50": {"target": "waiting", "actions": "checkLateness"}}
        }
    },
}

def check_lateness(interpreter, context, event, action_def):
    print(f"lateness_ms={event.lateness_ms:.2f}")

async def main():
    machine = create_machine(
        config, logic=MachineLogic(actions={"checkLateness": check_lateness})
    )
    interp = await Interpreter(machine).start()
    await asyncio.sleep(0.2)
    await interp.stop()

asyncio.run(main())
```

If `lateness_ms` trends upward over time, the event loop (or, for the `SyncInterpreter`, the calling thread) isn't being given enough opportunities to `pump()` due timers — see [Production Characteristics § 2](../production-characteristics/#2-after-timers-are-best-effort-and-starve-under-load) for the underlying guarantee.

## Controlling Time

Every timer in the library — `after` transitions and delayed `send()` — is scheduled through an injectable `Clock`, not called directly against `asyncio.sleep()` or a background thread. This is the same seam XState v5 uses (`createActor(machine, { clock })`), and it solves two problems at once:

* **Tests don't have to wait.** A 30-second `after` timeout can be fired in a fraction of a millisecond of real time by advancing a `SimulatedClock` instead of sleeping.
* **A due timer isn't starved by a busy inbox.** Both engines run timers through a dedicated priority lane, so a timer that becomes due is not queued behind thousands of already-pending external events.

### The `Clock` protocol

```python
from xstate_statemachine import Clock, RealClock, SimulatedClock
```

A `Clock` exposes `now()`, `set_timeout(fn, delay_sec, owner=None)`, `clear_timeout(handle)`, and `pump()`. Both `Interpreter` and `SyncInterpreter` accept a `clock=` constructor argument; if you don't pass one, each gets its own `RealClock()`.

### `RealClock` — wall time, the default

* Inside a running event loop (the async `Interpreter`), a timeout is `loop.call_later` — identical to today's `asyncio.sleep`-based timing.
* Outside a loop (the `SyncInterpreter`), a timeout is a deadline in a heap. **No thread is created.** Due callbacks run only when something calls `pump()` — which `SyncInterpreter.send()` and `tick()` do automatically, on the caller's own thread.

```python
from xstate_statemachine import RealClock

clock = RealClock()
clock.set_timeout(lambda: print("fired"), 0.0)
clock.pump()          # runs every due callback now; returns how many fired
clock.pending          # number of deadlines still waiting (sync timers only)
```

If your `SyncInterpreter` isn't receiving events regularly enough for its own `send()` calls to drain due timers, call `interp.clock.pump()` (or `interp.tick()`) yourself on a schedule.

### `SimulatedClock` — virtual time for tests

Time does not pass on its own. Call `increment(ms)` to advance virtual time and fire everything that became due, in due order:

```python
from xstate_statemachine import create_machine, SyncInterpreter, SimulatedClock

config = {
    "id": "sessionTimeout",
    "initial": "active",
    "states": {
        "active": {"after": {"300000": "warning"}, "on": {"ACTIVITY": "active"}},
        "warning": {"after": {"30000": "expired"}, "on": {"EXTEND": "active"}},
        "expired": {"type": "final"},
    },
}
machine = create_machine(config)

clock = SimulatedClock()
interp = SyncInterpreter(machine, clock=clock).start()
print(interp.active_state_ids)   # {'sessionTimeout.active'}

clock.increment(300_000)         # 5 minutes pass, instantly
print(interp.active_state_ids)   # {'sessionTimeout.warning'}

clock.increment(30_000)          # another 30 seconds pass
print(interp.active_state_ids)   # {'sessionTimeout.expired'}

interp.stop()
```

On the async `Interpreter`, `increment()` returns an awaitable so the caller can be sure the fired timer has finished being processed (including any onward transitions) before checking state:

```python
clock = SimulatedClock()
i = await Interpreter(create_machine(config), clock=clock).start()
await clock.increment(300_000)
await clock.increment(30_000)
await i.stop()
```

Calling `increment()`/`set()` inside a running event loop **without** `await` raises a warning at the next garbage collection — a forgotten `await` would otherwise silently race the loop instead of failing loudly.

`set(ms)` jumps to an absolute virtual time instead of advancing by a delta, and refuses to move backwards. `pending` reports how many live timers are still scheduled.

### Sharing one clock across async and sync interpreters

A `Clock` is not tied to one engine. Pass the same instance to a parent and to the children it invokes — including a mix of async and sync interpreters — and they share a single timeline. A parent's invoked child inherits its clock automatically; if you construct a standalone `SyncInterpreter` you want on the same timeline, pass `clock=` explicitly:

```python
from xstate_statemachine import create_machine, SyncInterpreter, Interpreter, SimulatedClock

child = {
    "id": "kid",
    "initial": "w",
    "states": {"w": {"after": {"100": "d"}}, "d": {"type": "final"}},
}
parent = {
    "id": "p",
    "initial": "a",
    "states": {"a": {"after": {"500": "b"}}, "b": {}},
}

clock = SimulatedClock()
kid = SyncInterpreter(create_machine(child), clock=clock).start()

async def main():
    i = await Interpreter(create_machine(parent), clock=clock).start()
    await clock.increment(100)
    print(set(kid.current_state_ids), set(i.current_state_ids))  # {'kid.d'} {'p.a'}
    await clock.increment(400)
    print(set(kid.current_state_ids), set(i.current_state_ids))  # {'kid.d'} {'p.b'}
    await i.stop()
```

One `increment()` call fires timers for **every** interpreter attached to the clock, in due order, regardless of which engine owns each one.

### Why a busy inbox no longer delays a due timer

Before 0.8.0, a fired async timer's continuation had to queue behind every external event already sitting in the inbox, which could add measurable lateness on top of the OS timer floor under heavy load. Both engines now run clock-fired callbacks through a dedicated priority lane, so a due `after` or delayed send is processed promptly even while thousands of `send()` calls are backlogged. This is what makes `after` usable as a watchdog alongside high event volume.

## Complete Example: Polling Machine

A machine that polls an API at regular intervals, with error handling and backoff:

```python
from xstate_statemachine import create_machine, SyncInterpreter, MachineLogic

config = {
    "id": "poller",
    "initial": "idle",
    "context": {"data": None, "errors": 0, "maxErrors": 3},
    "states": {
        "idle": {
            "on": {"START": "polling"}
        },
        "polling": {
            "invoke": {
                "src": "fetchData",
                "onDone": {
                    "target": "waiting",
                    "actions": "storeData"
                },
                "onError": {
                    "target": "retrying",
                    "actions": "incrementErrors"
                }
            }
        },
        "waiting": {
            "after": {
                "10000": "polling"
            },
            "on": {"STOP": "idle"}
        },
        "retrying": {
            "after": {
                "30000": {
                    "target": "polling",
                    "guard": "belowMaxErrors"
                },
                "30001": {
                    "target": "failed",
                    "guard": "atMaxErrors"
                }
            }
        },
        "failed": {
            "on": {"RESET": "idle"}
        }
    }
}

class PollerLogic(MachineLogic):
    def fetchData(self, interpreter, context, event):
        return {"status": "ok", "value": 42}

    def storeData(self, interpreter, context, event, action_def):
        context["data"] = event.data
        context["errors"] = 0

    def incrementErrors(self, interpreter, context, event, action_def):
        context["errors"] += 1

    def belowMaxErrors(self, context, event):
        return context["errors"] < context["maxErrors"]

    def atMaxErrors(self, context, event):
        return context["errors"] >= context["maxErrors"]

machine = create_machine(config, logic=PollerLogic())
interp = SyncInterpreter(machine).start()

interp.send("START")
print(interp.active_state_ids)
# {'poller.waiting'}  (fetchData succeeded, now waiting 10s to poll again)

print(interp.context["data"])
# {'status': 'ok', 'value': 42}

interp.send("STOP")
print(interp.active_state_ids)
# {'poller.idle'}

interp.stop()
```

## Complete Example: Auto-Save with Debounce

A document editor that auto-saves 2 seconds after the last edit:

```python
from xstate_statemachine import create_machine, SyncInterpreter, MachineLogic

config = {
    "id": "autoSave",
    "initial": "clean",
    "context": {"content": "", "lastSaved": None},
    "states": {
        "clean": {
            "on": {
                "EDIT": {
                    "target": "dirty",
                    "actions": "updateContent"
                }
            }
        },
        "dirty": {
            "after": {
                "2000": "saving"
            },
            "on": {
                "EDIT": {
                    "target": "dirty",
                    "actions": "updateContent"
                }
            }
        },
        "saving": {
            "invoke": {
                "src": "saveDocument",
                "onDone": {
                    "target": "clean",
                    "actions": "markSaved"
                },
                "onError": {
                    "target": "dirty"
                }
            }
        }
    }
}

class AutoSaveLogic(MachineLogic):
    def updateContent(self, interpreter, context, event, action_def):
        context["content"] = event.data.get("text", context["content"])
        print(f"Content updated: {context['content']!r}")

    def saveDocument(self, interpreter, context, event):
        print(f"Saving: {context['content']!r}")
        return {"saved": True}

    def markSaved(self, interpreter, context, event, action_def):
        import time
        context["lastSaved"] = time.time()
        print("Document saved!")

machine = create_machine(config, logic=AutoSaveLogic())
interp = SyncInterpreter(machine).start()

# Type something
interp.send({"type": "EDIT", "text": "Hello"})
print(interp.active_state_ids)
# {'autoSave.dirty'}

# Type more — this resets the 2-second debounce timer
interp.send({"type": "EDIT", "text": "Hello, world!"})
print(interp.active_state_ids)
# {'autoSave.dirty'}  (timer restarted)

# After 2 seconds of no edits, auto-save would fire
interp.stop()
```

The key insight: each `EDIT` event **re-enters** `dirty`, which resets the 2-second timer. The save only fires after the user stops typing for 2 full seconds. This is the classic debounce pattern, expressed declaratively.
