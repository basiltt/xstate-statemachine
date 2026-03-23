---
title: Core Concepts
description: States, events, transitions, guards, actions — the building blocks of every state machine.
---

Every state machine is built from a small set of fundamental concepts. This page covers all of them.

## The Big Picture

```
                    ┌─────────────────────────────────────────┐
                    │            STATE MACHINE                │
                    │                                         │
                    │   ┌─────────┐   TOGGLE   ┌─────────┐   │
                    │   │         │ ─────────► │         │   │
                    │   │   off   │             │   on    │   │
                    │   │ (init)  │ ◄───────── │         │   │
                    │   └─────────┘   TOGGLE   └─────────┘   │
                    │                                         │
                    │   context: { flips: 0 }                 │
                    └─────────────────────────────────────────┘
```

This toggle switch has **2 states** (`off`, `on`), **1 event type** (`TOGGLE`), **2 transitions** (one in each direction), and a **context** tracking flip count.

## Core Vocabulary

| Concept | What It Is | Example |
|---------|-----------|---------|
| **State** | A distinct mode the system can be in | `"off"`, `"loading"`, `"error"` |
| **Event** | Something that happens from the outside | `"TOGGLE"`, `"SUBMIT"`, `"TIMEOUT"` |
| **Transition** | A rule: _"when event X in state A, go to state B"_ | `off --TOGGLE--> on` |
| **Guard** | A boolean condition that must be true for the transition | `"isAdult"` — only transition if age >= 18 |
| **Action** | A side effect that runs during a transition | `"logToggle"` — print a message when toggling |
| **Context** | Mutable data the machine carries with it | `{ "retries": 0, "user": null }` |
| **Service** | An async operation invoked when entering a state | `"fetchUserData"` — API call, DB query |
| **Final State** | A terminal state with no outgoing transitions | `"success"`, `"completed"` |

## The Golden Rule

> **A state machine can only be in ONE state at a time** (unless using parallel states).
> It can ONLY move to another state when it receives an event that matches a defined transition.

This eliminates the "impossible states" problem. No more `isLoading && hasError && isAuthenticated` contradictions. If you're in the `loading` state, you are _only_ loading — not errored, not authenticated, not idle.

```python
# Traditional approach — impossible states are possible
is_loading = True
has_error = True       # Loading AND errored? Bug waiting to happen.
is_authenticated = True

# State machine approach — exactly ONE state at a time
# State is "loading" OR "error" OR "authenticated" — never multiple.
```

---

## How Events Work

Events are the **only** way to trigger state changes. They come from the outside world — user clicks, API responses, timers, or your own code calling `send()`.

```python
# String shorthand — most common
interpreter.send("TOGGLE")

# With payload data
interpreter.send("LOGIN", username="alice", password="secret")

# Event object for full control
from xstate_statemachine import Event
interpreter.send(Event(type="LOGIN", payload={"username": "alice"}))

# Dict form
interpreter.send({"type": "LOGIN", "username": "alice"})

# Multiple events in sequence
interpreter.send_events(["STEP_1", "STEP_2", "STEP_3"])
```

> **Tip:** Event names are conventionally UPPER_CASE (`"TOGGLE"`, `"SUBMIT"`, `"FETCH"`). State names are lowercase (`"idle"`, `"loading"`, `"done"`). This makes it easy to tell them apart at a glance.

---

## How Transitions Work

A transition answers one question: _"When event X happens while in state A, what should happen?"_

### Simple String Target

The most basic form — just specify where to go:

```python
# Pythonic
off.to(on, event="TOGGLE")

# JSON equivalent
{"on": {"TOGGLE": "on"}}
```

### Transition with Actions

Run side effects when the transition fires:

```python
# Pythonic
off.to(on, event="TOGGLE", actions="logToggle")

# JSON equivalent
{"on": {"TOGGLE": {"target": "on", "actions": "logToggle"}}}

# Multiple actions
off.to(on, event="TOGGLE", actions=["validate", "logToggle"])
```

### Guarded Transitions

Only transition if a condition is met:

```python
# Pythonic
checking.to(allowed, event="VERIFY", guard="isAdult")

# JSON equivalent
{"on": {"VERIFY": {"target": "allowed", "guard": "isAdult"}}}
```

### Multiple Guarded Transitions

When the same event can lead to different states depending on conditions, the **first matching guard wins**:

```python
# Pythonic — use the | operator
verify = (
    checking.to(allowed,  event="VERIFY", guard="isAdult")
    | checking.to(rejected, event="VERIFY")  # fallback (no guard)
)

# JSON equivalent — array of transition candidates
{"on": {"VERIFY": [
    {"target": "allowed",  "guard": "isAdult"},
    {"target": "rejected"}
]}}
```

### Self-Transitions

A state can transition to itself — useful for incrementing counters or re-running entry actions:

```python
# Pythonic
counting.to(counting, event="INCREMENT", actions="addOne")

# JSON equivalent
{"on": {"INCREMENT": {"target": "counting", "actions": "addOne"}}}
```

---

## State Types

### Atomic States

Simple leaf states with no children. This is the most common type:

```python
from xstate_statemachine import State, build_machine, SyncInterpreter

idle    = State("idle", initial=True)
loading = State("loading")
done    = State("done")

idle.to(loading, event="FETCH")
loading.to(done, event="SUCCESS")

machine = build_machine(id="fetcher", states=[idle, loading, done])
interp = SyncInterpreter(machine).start()
interp.send("FETCH")     # idle -> loading
interp.send("SUCCESS")   # loading -> done
interp.stop()
```

### Compound States (Hierarchical)

States that contain nested child states. The parent is active whenever any of its children are active:

```python
# A "form" state that has sub-states
editing    = State("editing", initial=True)
submitting = State("submitting")
form = State("form", initial=True, states=[editing, submitting])
success = State("success")

editing.to(submitting, event="SUBMIT")
form.to(success, event="DONE")

machine = build_machine(id="wizard", states=[form, success])
interp = SyncInterpreter(machine).start()
# Active: {'wizard.form', 'wizard.form.editing'}
interp.send("SUBMIT")
# Active: {'wizard.form', 'wizard.form.submitting'}
interp.stop()
```

### Parallel States

All child regions are active simultaneously. Each region has its own independent state:

```python
bold   = State("bold",   initial=True)
normal = State("normal")
bold_region = State("fontWeight", parallel=False, states=[bold, normal])

red   = State("red", initial=True)
blue  = State("blue")
color_region = State("fontColor", parallel=False, states=[red, blue])

editor = State("editor", parallel=True, initial=True, states=[bold_region, color_region])

bold.to(normal, event="TOGGLE_BOLD")
normal.to(bold,  event="TOGGLE_BOLD")
red.to(blue, event="TOGGLE_COLOR")
blue.to(red, event="TOGGLE_COLOR")

machine = build_machine(id="textEditor", states=[editor])
interp = SyncInterpreter(machine).start()
# Active: editor.fontWeight.bold AND editor.fontColor.red
interp.send("TOGGLE_BOLD")
# Active: editor.fontWeight.normal AND editor.fontColor.red
interp.send("TOGGLE_COLOR")
# Active: editor.fontWeight.normal AND editor.fontColor.blue
interp.stop()
```

### Final States

Terminal states. Once a machine enters a final state, it's done — no more transitions:

```python
idle     = State("idle", initial=True)
loading  = State("loading")
success  = State("success", final=True)
failure  = State("failure")

idle.to(loading, event="FETCH")
loading.to(success, event="RESOLVE")
loading.to(failure, event="REJECT")
failure.to(loading, event="RETRY")

machine = build_machine(id="dataLoader", states=[idle, loading, success, failure])
interp = SyncInterpreter(machine).start()
interp.send("FETCH")
interp.send("RESOLVE")
# Machine is now in final state "success" — no further transitions possible
interp.stop()
```

---

## Action Execution Order

When a transition fires, actions execute in a **strict, predictable order**:

1. **Exit actions** on the source state (bottom-up for nested states)
2. **Transition actions** (defined on the transition itself)
3. **Entry actions** on the target state (top-down for nested states)

```python
from xstate_statemachine import State, StateMachine, SyncInterpreter, action

class OrderDemo(StateMachine):
    machine_id = "orderDemo"

    editing    = State("editing", initial=True)
    submitting = State("submitting")

    submit = editing.to(submitting, event="SUBMIT", actions="validate")

    @editing.exit
    def on_exit_editing(self, interpreter, context, event, action_def):
        print("1. EXIT editing (saveDraft)")

    @action
    def validate(self, interpreter, context, event, action_def):
        print("2. TRANSITION action (validate)")

    @submitting.enter
    def on_enter_submitting(self, interpreter, context, event, action_def):
        print("3. ENTRY submitting (showSpinner)")

machine = OrderDemo.create_machine()
interp = SyncInterpreter(machine).start()
interp.send("SUBMIT")
interp.stop()
```

**Output:**

```
1. EXIT editing (saveDraft)
2. TRANSITION action (validate)
3. ENTRY submitting (showSpinner)
```

---

## Guard Evaluation Order

When multiple transitions share the same event, guards are evaluated **top to bottom**. The **first matching guard wins**:

```python
from xstate_statemachine import State, build_machine, SyncInterpreter, guard

checking = State("checking", initial=True)
premium  = State("premium")
standard = State("standard")
rejected = State("rejected")

# Order matters! First match wins.
verify = (
    checking.to(premium,  event="VERIFY", guard="isPremium")
    | checking.to(standard, event="VERIFY", guard="isAdult")
    | checking.to(rejected, event="VERIFY")  # fallback — no guard
)

@guard
def is_premium(context, event):
    return context.get("age", 0) >= 18 and context.get("plan") == "premium"

@guard
def is_adult(context, event):
    return context.get("age", 0) >= 18

machine = build_machine(
    id="accessControl",
    states=[checking, premium, standard, rejected],
    guards=[is_premium, is_adult],
    context={"age": 25, "plan": "premium"},
)

interp = SyncInterpreter(machine).start()
interp.send("VERIFY")
print(interp.active_state_ids)
# {'accessControl.premium'} — isPremium matched first
interp.stop()
```

> **Tip:** Always put your most specific guards first and leave a fallback transition (no guard) last to handle the default case.

---

## Context: Your Machine's Data

Context is a **mutable dictionary** that travels with the machine across all transitions. Actions read and write it freely.

```python
from xstate_statemachine import State, build_machine, SyncInterpreter, action

counting = State("counting", initial=True)
done     = State("done")

counting.to(counting, event="INCREMENT", actions="addOne")
counting.to(done,     event="FINISH")

@action
def add_one(interpreter, context, event, action_def):
    context["count"] += 1
    context["history"].append(f"+1 -> {context['count']}")

machine = build_machine(
    id="counter",
    states=[counting, done],
    actions=[add_one],
    context={"count": 0, "history": []},
)

interp = SyncInterpreter(machine).start()
interp.send("INCREMENT")
interp.send("INCREMENT")
interp.send("INCREMENT")

print(interp.context["count"])      # 3
print(interp.context["history"])    # ['+1 -> 1', '+1 -> 2', '+1 -> 3']

interp.send("FINISH")
interp.stop()
```

> **Tip:** Context is just a Python dictionary. You can store any serializable data — numbers, strings, lists, nested dicts. Keep your context flat when possible for easier debugging and serialization.

---

## The State Machine Lifecycle

Every machine follows the same lifecycle:

```
  create ──► start ──► send events ──► stop
    │          │            │            │
    │          │            │            │
  Define     Enter       Process      Exit all
  states     initial     events &     states,
  & rules    state       transitions  clean up
```

In code:

```python
from xstate_statemachine import State, build_machine, SyncInterpreter

idle   = State("idle", initial=True)
active = State("active")
idle.to(active, event="ACTIVATE")
active.to(idle,  event="DEACTIVATE")

# 1. CREATE — define the machine
machine = build_machine(id="lifecycle", states=[idle, active])

# 2. START — enter the initial state
interp = SyncInterpreter(machine).start()
print(interp.active_state_ids)   # {'lifecycle.idle'}
print(interp.is_running)         # True

# 3. SEND EVENTS — drive state changes
interp.send("ACTIVATE")
print(interp.active_state_ids)   # {'lifecycle.active'}

interp.send("DEACTIVATE")
print(interp.active_state_ids)   # {'lifecycle.idle'}

# 4. STOP — clean up
interp.stop()
print(interp.is_running)         # False
```

---

## Why State Machines?

Consider a simple door that can be opened, closed, and locked. Here's the traditional approach vs. the state machine approach:

### Without State Machines (if/else)

```python
class Door:
    def __init__(self):
        self.is_open = False
        self.is_locked = False

    def open(self):
        if self.is_locked:
            print("Can't open — locked!")
        elif self.is_open:
            print("Already open!")
        else:
            self.is_open = True

    def close(self):
        if not self.is_open:
            print("Already closed!")
        else:
            self.is_open = False

    def lock(self):
        if self.is_open:
            print("Can't lock — door is open!")
        elif self.is_locked:
            print("Already locked!")
        else:
            self.is_locked = True

    def unlock(self):
        if not self.is_locked:
            print("Not locked!")
        else:
            self.is_locked = False

# Problems:
# - What if someone sets is_open=True AND is_locked=True? Invalid state!
# - Every new feature adds more if/else branches
# - Hard to visualize the full set of valid transitions
# - No protection against impossible states
```

### With a State Machine

```python
from xstate_statemachine import State, build_machine, SyncInterpreter

closed   = State("closed", initial=True)
opened   = State("opened")
locked   = State("locked")

closed.to(opened, event="OPEN")
closed.to(locked, event="LOCK")
opened.to(closed, event="CLOSE")
locked.to(closed, event="UNLOCK")

machine = build_machine(id="door", states=[closed, opened, locked])
interp = SyncInterpreter(machine).start()

interp.send("OPEN")     # closed -> opened
interp.send("LOCK")     # ignored! No LOCK transition from "opened"
interp.send("CLOSE")    # opened -> closed
interp.send("LOCK")     # closed -> locked
interp.send("OPEN")     # ignored! No OPEN transition from "locked"
interp.send("UNLOCK")   # locked -> closed
interp.stop()

# Benefits:
# - Impossible states are impossible (can't be open AND locked)
# - Invalid events are silently ignored (no crashes)
# - The full behavior is visible in the transition definitions
# - Easy to add new states or events without breaking existing logic
```

---

## Next Steps

Now that you understand the building blocks:

- [Quick Start](../quick-start/) — Hands-on examples for every API style
- [Pythonic API](../pythonic-api/) — Full reference for class, builder, and functional styles
- [Actions](../actions/) — Deep dive into entry, exit, and transition actions
- [Guards](../guards/) — Conditional transitions in detail
- [Context](../context/) — Working with mutable machine data
- [Hierarchical States](../hierarchical/) — Nested (compound) states
- [Parallel States](../parallel/) — Concurrent state regions
- [Services](../services/) — Async operations invoked by states
- [Final States](../final-states/) — Terminal states and completion
