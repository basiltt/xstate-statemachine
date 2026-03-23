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
| `Interpreter` (async) | Uses `asyncio.create_task` / `asyncio.sleep` — timers run concurrently with your event loop |
| `SyncInterpreter` | Timers are scheduled and processed on `send()` calls — they fire when you next interact with the machine |

> **Tip:** For real-time timer behavior (actual wall-clock delays), use the async `Interpreter` with `asyncio`. The `SyncInterpreter` is best for testing and non-real-time workflows.

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
