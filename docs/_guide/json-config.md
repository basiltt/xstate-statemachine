---
title: "JSON Configuration Reference"
description: "Every field in the XState JSON format, fully documented with examples."
---

XState JSON is the universal format for defining state machines. You can design machines visually at [stately.ai](https://stately.ai), export JSON, and run them directly with this library — or write the JSON by hand.

This page documents **every field** in the configuration format, with complete, runnable examples.

---

## Complete JSON Structure

Here is a fully annotated machine configuration showing all top-level and state-level fields:

```json
{
  "id": "orderMachine",
  "initial": "idle",
  "context": {
    "retries": 0,
    "orderId": null,
    "items": [],
    "error": null
  },
  "states": {
    "idle": {
      "on": {
        "PLACE_ORDER": {
          "target": "validating",
          "actions": "captureOrder",
          "guard": "hasItems"
        }
      },
      "entry": "resetForm",
      "exit": "clearErrors"
    },
    "validating": {
      "always": [
        { "target": "processing", "guard": "isValid" },
        { "target": "idle", "actions": "showValidationError" }
      ]
    },
    "processing": {
      "invoke": {
        "src": "submitOrder",
        "onDone": {
          "target": "confirmed",
          "actions": "storeOrderId"
        },
        "onError": {
          "target": "error",
          "actions": "storeError"
        }
      },
      "after": {
        "10000": "error"
      }
    },
    "confirmed": {
      "type": "final"
    },
    "error": {
      "on": {
        "RETRY": {
          "target": "processing",
          "guard": "hasRetriesLeft",
          "actions": "incrementRetry"
        },
        "CANCEL": "idle"
      }
    }
  }
}
```

This machine has:

- **`id`** — a unique identifier for the machine
- **`initial`** — the state the machine starts in
- **`context`** — mutable data that travels with the machine
- **`states`** — a map of every state and its configuration
- Entry/exit actions, guards, services, delayed transitions, eventless transitions, and a final state

---

## Field-by-Field Reference

### Top-Level Fields

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `id` | `string` | **Yes** | Unique machine identifier. Used as a prefix in state IDs (e.g., `"orderMachine.idle"`). |
| `initial` | `string` | **Yes** | The name of the starting state. Must match a key in `states`. |
| `context` | `object` | No | Initial mutable data. Accessible in actions, guards, and services. Deep-copied on each interpreter start. |
| `states` | `object` | **Yes** | A map of state name → state configuration. At least one state is required. |

**Example — minimal machine:**

```json
{
  "id": "toggle",
  "initial": "off",
  "states": {
    "off": { "on": { "FLIP": "on" } },
    "on":  { "on": { "FLIP": "off" } }
  }
}
```

**Example — with context:**

```json
{
  "id": "counter",
  "initial": "counting",
  "context": {
    "count": 0,
    "maxCount": 100,
    "history": []
  },
  "states": {
    "counting": {
      "on": {
        "INCREMENT": { "actions": "addOne" },
        "DECREMENT": { "actions": "subtractOne" },
        "RESET":     { "actions": "resetCount" }
      }
    }
  }
}
```

---

### State Fields

Every value in the `states` object is a **state configuration** with the following optional fields:

| Field | Type | Description |
|-------|------|-------------|
| `on` | `object` | Map of event name → transition(s). The core of state machine behavior. |
| `entry` | `string \| string[]` | Action(s) to run when entering this state. |
| `exit` | `string \| string[]` | Action(s) to run when leaving this state. |
| `invoke` | `object \| object[]` | Service(s) to start when entering this state. |
| `after` | `object` | Delayed transitions: `{ "milliseconds": target_or_transition }`. |
| `type` | `string` | One of `"atomic"`, `"compound"`, `"parallel"`, or `"final"`. Default: `"atomic"`. |
| `initial` | `string` | Initial child state name (required for compound states). |
| `states` | `object` | Nested child state configurations (makes this a compound state). |
| `onDone` | `string \| object` | Transition when a compound state's child reaches a final state. |
| `always` | `object \| object[]` | Eventless (transient) transitions — evaluated immediately on entry. |

**Example — state with all fields:**

```json
"loading": {
  "entry": ["showSpinner", "logStart"],
  "exit": "hideSpinner",
  "invoke": {
    "src": "fetchData",
    "onDone":  { "target": "success", "actions": "storeResult" },
    "onError": { "target": "failure", "actions": "storeError" }
  },
  "on": {
    "CANCEL": "idle"
  },
  "after": {
    "15000": { "target": "failure", "actions": "logTimeout" }
  }
}
```

---

## Transition Formats

Transitions are defined inside a state's `on` field. The library supports **four formats**, from simplest to most expressive.

### Format 1: Simple String Shorthand

The most concise form — just the target state name:

```json
"on": {
  "CLICK": "active",
  "HOVER": "highlighted",
  "RESET": "idle"
}
```

No guard, no actions — just move to the target state.

### Format 2: Object with Options

Add a `target`, `guard`, and/or `actions`:

```json
"on": {
  "SUBMIT": {
    "target": "submitting",
    "guard": "isFormValid",
    "actions": "logSubmission"
  }
}
```

| Property | Type | Description |
|----------|------|-------------|
| `target` | `string` | Destination state name. |
| `guard` | `string` | Guard function name — transition only fires if this returns `true`. |
| `actions` | `string \| string[]` | Action(s) to execute during the transition. |

### Format 3: Array Form (Multiple Transitions)

When an event has multiple possible outcomes, use an array. **The first transition whose guard passes wins:**

```json
"on": {
  "SUBMIT": [
    { "target": "premium",  "guard": "isPremiumUser" },
    { "target": "standard", "guard": "isVerified" },
    { "target": "rejected" }
  ]
}
```

> **Tip:** Always put the most specific guard first. The **last entry without a guard** acts as the fallback (default) transition.

### Format 4: Multiple Actions

A single transition can run multiple actions:

```json
"on": {
  "CHECKOUT": {
    "target": "processing",
    "actions": ["validateCart", "captureAddress", "startPayment"]
  }
}
```

Actions execute **in order** — `validateCart` first, then `captureAddress`, then `startPayment`.

**Combining all formats:**

```json
"on": {
  "LOGIN": [
    {
      "target": "admin",
      "guard": "isAdmin",
      "actions": ["logLogin", "loadAdminDashboard"]
    },
    {
      "target": "dashboard",
      "actions": ["logLogin", "loadUserDashboard"]
    }
  ]
}
```

---

## Eventless Transitions (`always`)

Eventless transitions fire **immediately** when a state is entered — no event needed. They are evaluated in order, and the **first matching guard wins**.

### Router Example

```json
{
  "id": "router",
  "initial": "checking",
  "context": { "role": "admin", "authenticated": true },
  "states": {
    "checking": {
      "always": [
        { "target": "adminPanel",    "guard": "isAdmin" },
        { "target": "userDashboard", "guard": "isUser" },
        { "target": "login" }
      ]
    },
    "adminPanel":    {},
    "userDashboard": {},
    "login":         {}
  }
}
```

When the machine enters `"checking"`:

1. It evaluates `isAdmin` — if `true`, immediately transitions to `"adminPanel"`.
2. Otherwise, evaluates `isUser` — if `true`, transitions to `"userDashboard"`.
3. Otherwise, falls through to `"login"` (no guard = always matches).

> **Note:** Eventless transitions happen **synchronously** during state entry. The machine never "rests" in the `"checking"` state — it passes through instantly.

### Eventless with Actions

```json
"checking": {
  "always": [
    {
      "target": "premium",
      "guard": "hasPremiumPlan",
      "actions": "loadPremiumFeatures"
    },
    {
      "target": "free",
      "actions": "loadBasicFeatures"
    }
  ]
}
```

---

## Invoke / Service Fields

The `invoke` field starts an async operation (service) when a state is entered. When the service resolves or rejects, the machine transitions via `onDone` or `onError`.

### Invoke Field Reference

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `src` | `string` | **Yes** | The name of the service function to call. |
| `onDone` | `string \| object` | No | Transition when the service resolves successfully. |
| `onError` | `string \| object` | No | Transition when the service throws an error. |
| `id` | `string` | No | Optional identifier for the invoked service. |

### Basic Invoke

```json
"loading": {
  "invoke": {
    "src": "fetchUserProfile",
    "onDone": {
      "target": "loaded",
      "actions": "storeProfile"
    },
    "onError": {
      "target": "error",
      "actions": "storeError"
    }
  }
}
```

### Invoke with ID

```json
"polling": {
  "invoke": {
    "id": "pollService",
    "src": "pollForUpdates",
    "onDone": {
      "target": "updated",
      "actions": ["storeUpdate", "logRefresh"]
    },
    "onError": "error"
  }
}
```

### Multiple Invocations

A state can invoke multiple services simultaneously using an array:

```json
"initializing": {
  "invoke": [
    {
      "src": "loadConfig",
      "onDone": { "actions": "storeConfig" }
    },
    {
      "src": "loadUser",
      "onDone": { "actions": "storeUser" }
    }
  ]
}
```

> **Note:** The `onDone` event carries the return value of the service. Access it in your action via `event.data`.

---

## After (Delayed Transitions)

The `after` field defines timer-based automatic transitions. Keys are **milliseconds** (as strings), values are target states or full transition objects.

### Simple Timeout

```json
"notification": {
  "entry": "showToast",
  "after": {
    "5000": "hidden"
  }
}
```

After 5 seconds, the machine automatically transitions from `"notification"` to `"hidden"`.

### Timeout with Guard

```json
"warning": {
  "after": {
    "30000": {
      "target": "expired",
      "guard": "noUserActivity"
    }
  },
  "on": {
    "EXTEND": "active"
  }
}
```

### Multiple Timers

A state can have multiple `after` timers running simultaneously:

```json
"monitoring": {
  "after": {
    "5000":   { "target": "monitoring", "actions": "heartbeat" },
    "60000":  { "target": "stale",      "guard": "noRecentData" },
    "300000": "timeout"
  }
}
```

This state:
1. Sends a heartbeat every 5 seconds (self-transition re-enters the state, restarting all timers).
2. Transitions to `"stale"` after 60 seconds if no recent data.
3. Hard-timeouts at 5 minutes regardless.

### Session Timeout Example

```json
{
  "id": "sessionTimeout",
  "initial": "active",
  "states": {
    "active": {
      "after": { "300000": "warning" },
      "on": { "ACTIVITY": "active" }
    },
    "warning": {
      "after": { "30000": "expired" },
      "on": { "EXTEND": "active" }
    },
    "expired": {
      "type": "final"
    }
  }
}
```

> **Tip:** The `ACTIVITY` event on `"active"` triggers a self-transition, which **restarts the 5-minute timer**. This is how you implement "idle timeout with reset on activity".

---

## State Types

Every state has a `type` that determines its behavior:

| Type | Description | Has Children? | Outgoing Transitions? |
|------|-------------|:---:|:---:|
| `"atomic"` | Simple leaf state (default). | No | Yes |
| `"compound"` | Parent state with nested children. Automatically inferred when `states` is present. | Yes | Yes |
| `"parallel"` | All child regions active simultaneously. | Yes | Yes |
| `"final"` | Terminal state — the machine (or region) is done. | No | No |

### Atomic (default)

```json
"idle": {
  "on": { "START": "running" }
}
```

No `type` field needed — atomic is the default.

### Final

```json
"completed": {
  "type": "final"
}
```

When a final state is entered inside a compound state, it triggers a `done.state.*` event on the parent.

### Parallel

```json
"playing": {
  "type": "parallel",
  "states": {
    "video": {
      "initial": "loading",
      "states": {
        "loading": { "on": { "LOADED": "showing" } },
        "showing": {}
      }
    },
    "audio": {
      "initial": "muted",
      "states": {
        "muted":   { "on": { "UNMUTE": "playing" } },
        "playing": { "on": { "MUTE": "muted" } }
      }
    }
  }
}
```

---

## Nested (Compound) States

When a state has a `states` field, it becomes a **compound state**. It must also have an `initial` field to specify which child state is entered first.

### Example: Authentication Flow

```json
{
  "id": "auth",
  "initial": "loggedOut",
  "states": {
    "loggedOut": {
      "on": { "LOGIN": "loggedIn" }
    },
    "loggedIn": {
      "initial": "dashboard",
      "states": {
        "dashboard": {
          "on": {
            "VIEW_PROFILE": "profile",
            "VIEW_SETTINGS": "settings"
          }
        },
        "profile": {
          "on": { "BACK": "dashboard" }
        },
        "settings": {
          "on": { "BACK": "dashboard" }
        }
      },
      "on": {
        "LOGOUT": "loggedOut"
      }
    }
  }
}
```

**Key behavior:** The `LOGOUT` event on the parent `"loggedIn"` state catches the event **no matter which child state is active**. This is the power of hierarchy — parent transitions apply to all children.

### Multi-Level Nesting

States can be nested multiple levels deep:

```json
"app": {
  "initial": "main",
  "states": {
    "main": {
      "initial": "home",
      "states": {
        "home":     { "on": { "NAV_PROFILE": "profile" } },
        "profile":  { "on": { "NAV_HOME": "home" } }
      }
    }
  }
}
```

---

## `onDone` for Compound States

When a compound state's child enters a `final` state, the parent can react via `onDone`:

```json
{
  "id": "wizard",
  "initial": "step1",
  "states": {
    "step1": {
      "initial": "editing",
      "states": {
        "editing": {
          "on": { "NEXT": "complete" }
        },
        "complete": { "type": "final" }
      },
      "onDone": "step2"
    },
    "step2": {
      "initial": "editing",
      "states": {
        "editing": {
          "on": { "NEXT": "complete" }
        },
        "complete": { "type": "final" }
      },
      "onDone": "finished"
    },
    "finished": { "type": "final" }
  }
}
```

When `step1.complete` is entered (a final state), it fires a `done.state.step1` event, which triggers `onDone` and moves the machine to `step2`.

> **Note:** `onDone` supports the same formats as transitions — a string target, or an object with `target`, `guard`, and `actions`.

---

## Complete Real-World Example: Fetch Machine

This machine models a complete data-fetching flow with retries, timeout, and context tracking:

```json
{
  "id": "fetchMachine",
  "initial": "idle",
  "context": {
    "data": null,
    "error": null,
    "retries": 0,
    "maxRetries": 3,
    "lastFetchedAt": null
  },
  "states": {
    "idle": {
      "entry": "resetError",
      "on": {
        "FETCH": {
          "target": "loading",
          "actions": "logFetchStart"
        }
      }
    },
    "loading": {
      "entry": "showSpinner",
      "exit": "hideSpinner",
      "invoke": {
        "src": "fetchData",
        "onDone": {
          "target": "success",
          "actions": ["storeData", "recordTimestamp"]
        },
        "onError": {
          "target": "error",
          "actions": "storeError"
        }
      },
      "after": {
        "15000": {
          "target": "error",
          "actions": "logTimeout"
        }
      },
      "on": {
        "CANCEL": {
          "target": "idle",
          "actions": "logCancellation"
        }
      }
    },
    "success": {
      "entry": "notifySuccess",
      "on": {
        "REFRESH": "loading",
        "RESET": {
          "target": "idle",
          "actions": "clearData"
        }
      }
    },
    "error": {
      "entry": "notifyError",
      "on": {
        "RETRY": [
          {
            "target": "loading",
            "guard": "hasRetriesLeft",
            "actions": "incrementRetry"
          },
          {
            "target": "failed",
            "actions": "logMaxRetries"
          }
        ],
        "RESET": {
          "target": "idle",
          "actions": ["clearData", "resetRetries"]
        }
      }
    },
    "failed": {
      "type": "final"
    }
  }
}
```

### Running It

```python
from xstate_statemachine import create_machine, SyncInterpreter, MachineLogic

class FetchLogic(MachineLogic):
    # Actions
    def resetError(self, interpreter, context, event, action_def):
        context["error"] = None

    def showSpinner(self, interpreter, context, event, action_def):
        print("⏳ Loading...")

    def hideSpinner(self, interpreter, context, event, action_def):
        print("   Spinner hidden")

    def storeData(self, interpreter, context, event, action_def):
        context["data"] = event.data

    def recordTimestamp(self, interpreter, context, event, action_def):
        from datetime import datetime
        context["lastFetchedAt"] = datetime.now().isoformat()

    def storeError(self, interpreter, context, event, action_def):
        context["error"] = str(event.data)

    def incrementRetry(self, interpreter, context, event, action_def):
        context["retries"] += 1
        print(f"🔄 Retry #{context['retries']}")

    def logFetchStart(self, interpreter, context, event, action_def):
        print("📡 Fetch started")

    def logTimeout(self, interpreter, context, event, action_def):
        context["error"] = "Request timed out"

    def logCancellation(self, interpreter, context, event, action_def):
        print("❌ Fetch cancelled")

    def logMaxRetries(self, interpreter, context, event, action_def):
        print("💀 Max retries reached")

    def notifySuccess(self, interpreter, context, event, action_def):
        print(f"✅ Data loaded: {context['data']}")

    def notifyError(self, interpreter, context, event, action_def):
        print(f"⚠️ Error: {context['error']}")

    def clearData(self, interpreter, context, event, action_def):
        context["data"] = None

    def resetRetries(self, interpreter, context, event, action_def):
        context["retries"] = 0

    # Guards
    def hasRetriesLeft(self, context, event):
        return context["retries"] < context["maxRetries"]

    # Services
    def fetchData(self, interpreter, context, event):
        import requests
        resp = requests.get("https://api.example.com/data")
        return resp.json()

config = { ... }  # The JSON config above

machine = create_machine(config, logic=FetchLogic())
interp = SyncInterpreter(machine).start()

interp.send("FETCH")       # idle -> loading -> (service runs) -> success or error
interp.send("RETRY")       # error -> loading (if retries left)
interp.stop()

print(interp.context)
```

---

## Tips: Common Mistakes and Best Practices

> **Tip:** Always give your machine a descriptive `id`. State IDs are prefixed with it (e.g., `"fetchMachine.loading"`), which makes debugging and logging much clearer.

> **Tip:** Use context for data that changes — like counters, user objects, and error messages. Use states for _modes_ — like "idle", "loading", "error".

> **Warning:** Don't put the same event name in both a parent and a child state unless you intend for the child to "shadow" the parent's handler. The child's `on` handler takes priority.

> **Warning:** Final states cannot have outgoing transitions (`on`), child states (`states`), or delayed transitions (`after`). If you need to leave a final state, redesign your state hierarchy so the final state is inside a compound state with an `onDone` handler.

> **Tip:** When using multiple guarded transitions (array form), always include a fallback transition without a guard as the last entry. Otherwise, the event is silently dropped if no guard matches.

> **Note:** JSON doesn't support comments. If you need to annotate your config, keep it in a Python dict or use a `.jsonc` file and strip comments before parsing.

> **Tip:** Start with the [Stately visual editor](https://stately.ai) to design your machine, then export the JSON. It validates your config and catches structural errors before you write any code.

---

## Quick Reference Cheat Sheet

```
Top level:       id, initial, context, states
State fields:    on, entry, exit, invoke, after, type, initial, states, onDone, always
Transition:      "EVENT": "target"                         (string shorthand)
                 "EVENT": { target, guard, actions }       (object form)
                 "EVENT": [ { ... }, { ... } ]             (array — first guard wins)
Invoke:          { src, onDone, onError, id }
After:           { "ms": "target" } or { "ms": { target, guard, actions } }
Types:           "atomic" (default), "compound", "parallel", "final"
Eventless:       "always": [ { target, guard }, ... ]
```
