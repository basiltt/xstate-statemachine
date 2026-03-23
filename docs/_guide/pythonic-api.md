---
title: "Pythonic API"
description: "Define state machines in pure Python with three styles — class-based, builder, or functional."
---

> **New in v0.5.0** — Define state machines in pure Python. No JSON needed.

The Pythonic API lets you define states, transitions, actions, guards, and services using native Python constructs — classes, decorators, and function calls. Under the hood, everything compiles to the same `MachineNode` that the JSON-based `create_machine()` produces.

Three styles, same result. Pick the one that matches your team:

| Style | Best For | Entry Point | Pros |
|-------|----------|-------------|------|
| **Class-Based** | OOP teams, large machines | `class MyMachine(StateMachine)` | Self-contained, IDE-friendly, decorators for logic |
| **Builder** | Fluent/chained construction | `MachineBuilder("id").state(...).build()` | Concise, easy to compose dynamically |
| **Functional** | Simple, explicit assembly | `build_machine(id=..., states=[...])` | Module-level, great for small machines |

All three compile to the same internal `MachineNode` and work with both `Interpreter` (async) and `SyncInterpreter` (sync).

---

## Style 1: Class-Based (`StateMachine`)

The class-based style is the most expressive. States are class attributes, transitions use `.to()`, and logic is defined with `@action`, `@guard`, and `@service` decorators.

### Full TrafficLight Example

```python
from xstate_statemachine import (
    State, StateMachine, SyncInterpreter,
    action, guard, service
)

class TrafficLight(StateMachine):
    machine_id = "trafficLight"
    initial_context = {"cycle_count": 0, "mode": "normal"}

    # ── States ──────────────────────────────────────────────
    green  = State("green",  initial=True)
    yellow = State("yellow")
    red    = State("red")

    # ── Transitions ─────────────────────────────────────────
    slow_down = green.to(yellow, event="TIMER")
    stop      = yellow.to(red,   event="TIMER")
    go        = red.to(green,    event="TIMER")

    # ── Actions ─────────────────────────────────────────────
    @action
    def log_change(self, interpreter, context, event, action_def):
        states = interpreter.active_state_ids
        print(f"🚦 Light changed → {states}")

    @action
    def increment_cycle(self, interpreter, context, event, action_def):
        context["cycle_count"] += 1

    # ── Guards ──────────────────────────────────────────────
    @guard
    def is_rush_hour(self, context, event):
        return context.get("hour", 12) in range(7, 10)

    @guard
    def is_night_mode(self, context, event):
        return context.get("mode") == "night"

    # ── Services ────────────────────────────────────────────
    @service
    def fetch_schedule(self, interpreter, context, event):
        # Could be an API call or database lookup
        return {"rush_hours": [7, 8, 9], "night_start": 22}


# ── Run it ──────────────────────────────────────────────────
machine = TrafficLight.create_machine()
interp = SyncInterpreter(machine).start()

print(interp.active_state_ids)   # {'trafficLight.green'}
interp.send("TIMER")             # green → yellow
print(interp.active_state_ids)   # {'trafficLight.yellow'}
interp.send("TIMER")             # yellow → red
interp.send("TIMER")             # red → green
interp.stop()
```

### Key Points

- `machine_id` sets the machine's ID (defaults to the class name if omitted).
- `initial_context` provides the starting context dictionary.
- States are `State(...)` instances assigned to class attributes.
- Transitions use `source.to(target, event="EVENT_NAME")`.
- `create_machine()` is a classmethod that compiles everything and returns a `MachineNode`.

---

## Style 2: Builder (`MachineBuilder`)

The builder style uses a fluent API with method chaining. Great for constructing machines dynamically or in configuration-driven scenarios.

### Full Example

```python
from xstate_statemachine import MachineBuilder, SyncInterpreter

def log_change(interpreter, context, event, action_def):
    print(f"Now: {interpreter.active_state_ids}")

def validate_input(interpreter, context, event, action_def):
    if not context.get("value"):
        context["errors"] = ["Value is required"]
    else:
        context["errors"] = []

def is_valid(context, event):
    return len(context.get("errors", [])) == 0

def process_data(interpreter, context, event):
    return {"result": f"processed {context['value']}"}

machine = (
    MachineBuilder("formProcessor")
    .context({"value": "", "errors": [], "result": None})
    # ── States ──────────────────────────────────────────
    .state("idle",       initial=True)
    .state("validating")
    .state("processing", invoke={
        "src": "processData",
        "onDone": {"target": "success", "actions": "storeResult"},
        "onError": {"target": "error"}
    })
    .state("success",    final=True)
    .state("error",      on={"RETRY": "idle"})
    # ── Transitions ─────────────────────────────────────
    .transition("idle",       "SUBMIT",   "validating", actions=["validate"])
    .transition("validating", "VALID",    "processing", guard="isValid")
    .transition("validating", "INVALID",  "error")
    # ── Logic Registration ──────────────────────────────
    .action("logChange", log_change)
    .action("validate",  validate_input)
    .guard("isValid",    is_valid)
    .service("processData", process_data)
    .build()
)

interp = SyncInterpreter(machine).start()
interp.send("SUBMIT")
interp.stop()
```

### Builder Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `.context(ctx)` | `dict → self` | Set initial context. |
| `.state(name, ...)` | `str, **kwargs → self` | Add a state. Supports `initial`, `final`, `parallel`, `on`, `entry`, `exit`, `after`, `invoke`, `on_done`, `always`. |
| `.transition(src, event, target, ...)` | `str, str, str, **kwargs → self` | Add a transition. Supports `guard`, `actions`, `reenter`, `internal`. |
| `.action(name, fn)` | `str, callable → self` | Register an action function. |
| `.guard(name, fn)` | `str, callable → self` | Register a guard function. |
| `.service(name, fn)` | `str, callable → self` | Register a service function. |
| `.child_states(parent, ...)` | `str, **kwargs → self` | Add child states to a parent. Supports `initial`, `states`, `parallel`. |
| `.build(context=None)` | `dict? → MachineNode` | Compile and return the machine. Optional context override. |

### Adding Child States (Hierarchy)

```python
machine = (
    MachineBuilder("app")
    .state("loggedOut",  initial=True)
    .state("loggedIn")
    .child_states("loggedIn", initial="dashboard", states={
        "dashboard": {"on": {"VIEW_PROFILE": "profile"}},
        "profile":   {"on": {"BACK": "dashboard"}},
        "settings":  {"on": {"BACK": "dashboard"}},
    })
    .transition("loggedOut", "LOGIN",  "loggedIn")
    .transition("loggedIn",  "LOGOUT", "loggedOut")
    .build()
)
```

### Builder with Delayed Transitions and Invoke

```python
machine = (
    MachineBuilder("orderProcessor")
    .context({"orderId": None, "result": None, "error": None})
    .state("idle", initial=True)
    .state("processing", invoke={
        "src": "processOrder",
        "onDone": {"target": "completed", "actions": "storeResult"},
        "onError": {"target": "failed", "actions": "storeError"}
    }, after={
        30000: {"target": "timeout"}  # 30s timeout
    })
    .state("completed", final=True)
    .state("failed", on={"RETRY": "processing"})
    .state("timeout", on={"RETRY": "processing"})
    .transition("idle", "PROCESS", "processing", actions=["setOrderId"])
    .action("setOrderId", lambda i, ctx, e, a: ctx.update({"orderId": e.payload.get("id")}))
    .action("storeResult", lambda i, ctx, e, a: ctx.update({"result": e.data}))
    .action("storeError", lambda i, ctx, e, a: ctx.update({"error": str(e.data)}))
    .service("processOrder", lambda i, ctx, e: {"status": "shipped", "tracking": "TRK-001"})
    .build()
)
```

### Builder with Parallel Child States

```python
machine = (
    MachineBuilder("dashboard")
    .state("loading", initial=True)
    .state("active")
    .child_states("active", parallel=True, states={
        "notifications": {
            "initial": "unread",
            "states": {
                "unread": {"on": {"MARK_READ": "read"}},
                "read":   {}
            }
        },
        "feed": {
            "initial": "loading",
            "states": {
                "loading": {"on": {"LOADED": "showing"}},
                "showing": {}
            }
        }
    })
    .transition("loading", "READY", "active")
    .build()
)
```

---

## Style 3: Functional (`build_machine`)

The functional style defines states and transitions at module level, then assembles them with a single `build_machine()` call. It's the most explicit — nothing is hidden in class magic.

### Full Example

```python
from xstate_statemachine import (
    State, build_machine, SyncInterpreter,
    action, guard, service
)

# ── Define States ───────────────────────────────────────────
idle     = State("idle",     initial=True)
loading  = State("loading",  invoke={
    "src": "fetchItems",
    "onDone":  {"target": "loaded",  "actions": "storeItems"},
    "onError": {"target": "error",   "actions": "storeError"},
})
loaded   = State("loaded")
error    = State("error")

# ── Define Transitions ─────────────────────────────────────
idle.to(loading, event="FETCH")
loaded.to(loading, event="REFRESH")
error.to(loading,  event="RETRY", guard="hasRetriesLeft")
error.to(idle,     event="CANCEL")

# ── Define Logic ────────────────────────────────────────────
@action
def store_items(interpreter, context, event, action_def):
    context["items"] = event.data

@action
def store_error(interpreter, context, event, action_def):
    context["error"] = str(event.data)

@guard
def has_retries_left(context, event):
    return context.get("retries", 0) < 3

@service
def fetch_items(interpreter, context, event):
    import requests
    resp = requests.get("https://api.example.com/items")
    return resp.json()

# ── Build and Run ───────────────────────────────────────────
machine = build_machine(
    id="itemLoader",
    states=[idle, loading, loaded, error],
    actions=[store_items, store_error],
    guards=[has_retries_left],
    services=[fetch_items],
    context={"items": [], "error": None, "retries": 0},
)

interp = SyncInterpreter(machine).start()
interp.send("FETCH")
print(interp.active_state_ids)
interp.stop()
```

### `build_machine()` Parameters

| Parameter | Type | Required | Description |
|-----------|------|:--------:|-------------|
| `id` | `str` | **Yes** | Machine identifier. |
| `states` | `list[State]` | **Yes** | All top-level states. |
| `transitions` | `list[Transition]` | No | Additional transitions (beyond those created by `.to()`). |
| `actions` | `list[callable]` | No | Action functions (decorated with `@action` or raw). |
| `guards` | `list[callable]` | No | Guard functions (decorated with `@guard` or raw). |
| `services` | `list[callable]` | No | Service functions (decorated with `@service` or raw). |
| `context` | `dict` | No | Initial context. |

---

## Decorator Details

The `@action`, `@guard`, and `@service` decorators mark functions for automatic registration. They work in all three API styles.

### Auto-Naming: `snake_case` → `camelCase`

When used without arguments, the function name is automatically converted from `snake_case` to `camelCase`:

```python
@action
def increment_counter(interpreter, context, event, action_def):
    context["count"] += 1
# Registered as "incrementCounter"

@guard
def is_valid_email(context, event):
    return "@" in context.get("email", "")
# Registered as "isValidEmail"

@service
def fetch_user_data(interpreter, context, event):
    return {"name": "Alice"}
# Registered as "fetchUserData"
```

### Explicit Naming

Pass a string to override the auto-generated name:

```python
@action("myCustomAction")
def some_function(interpreter, context, event, action_def):
    pass
# Registered as "myCustomAction"

@guard("canProceed")
def check_requirements(context, event):
    return context.get("ready", False)
# Registered as "canProceed"

@service("loadProfile")
def get_profile_data(interpreter, context, event):
    return {"profile": "data"}
# Registered as "loadProfile"
```

### Decorator Signatures

Each decorator type has a specific function signature:

```python
# @action — receives interpreter, context, event, and action_def
@action
def my_action(interpreter, context, event, action_def):
    context["count"] += 1          # modify context
    print(event.type)              # read event info
    # No return value needed

# @guard — receives context and event, returns bool
@guard
def my_guard(context, event):
    return context.get("value", 0) > 0
    # MUST return True or False
    # MUST be synchronous (async guards raise NotSupportedError)

# @service — receives interpreter, context, event, returns Any
@service
def my_service(interpreter, context, event):
    result = do_some_work()
    return result
    # Return value becomes event.data in onDone
    # Can be sync or async
```

> **Warning:** Guard functions **must be synchronous**. Async guards will raise `NotSupportedError`. If you need async logic, use a service with `invoke` instead.

### Class-Based Decorator Signatures

In `StateMachine` subclasses, all decorated methods receive `self` as the first argument:

```python
class MyMachine(StateMachine):
    @action
    def my_action(self, interpreter, context, event, action_def):
        pass  # self is the StateMachine instance

    @guard
    def my_guard(self, context, event):
        return True

    @service
    def my_service(self, interpreter, context, event):
        return {"data": "value"}
```

---

## Entry/Exit Actions (Class-Based)

Use the `@state.enter` and `@state.exit` decorators to bind actions to state entry and exit:

```python
from xstate_statemachine import State, StateMachine, SyncInterpreter

class DocumentEditor(StateMachine):
    machine_id = "editor"

    editing    = State("editing", initial=True)
    saving     = State("saving")
    saved      = State("saved")

    # Transitions
    save     = editing.to(saving, event="SAVE")
    complete = saving.to(saved,   event="DONE")
    edit     = saved.to(editing,  event="EDIT")

    # Entry/Exit decorators
    @editing.enter
    def on_enter_editing(self, interpreter, context, event, action_def):
        print("📝 Entered editing mode")
        context["dirty"] = False

    @editing.exit
    def on_exit_editing(self, interpreter, context, event, action_def):
        print("💾 Auto-saving draft before leaving editing...")
        context["draft_saved"] = True

    @saving.enter
    def on_enter_saving(self, interpreter, context, event, action_def):
        print("⏳ Saving document...")

    @saved.enter
    def on_enter_saved(self, interpreter, context, event, action_def):
        print("✅ Document saved successfully!")


machine = DocumentEditor.create_machine()
interp = SyncInterpreter(machine).start()
# Output: 📝 Entered editing mode

interp.send("SAVE")
# Output: 💾 Auto-saving draft before leaving editing...
# Output: ⏳ Saving document...

interp.send("DONE")
# Output: ✅ Document saved successfully!

interp.stop()
```

> **Note:** `@state.enter` and `@state.exit` decorators are **only valid inside a `StateMachine` class**. Using them in the functional API will raise `InvalidConfigError`.

---

## Multiple Guarded Transitions

Use the `|` (pipe) operator to combine multiple transitions for the same event. The first matching guard wins:

```python
from xstate_statemachine import State, StateMachine, guard, SyncInterpreter

class SubscriptionRouter(StateMachine):
    machine_id = "subscriptionRouter"
    initial_context = {"plan": "premium", "trial_expired": False}

    checking   = State("checking", initial=True)
    premium    = State("premium")
    basic      = State("basic")
    trial      = State("trial")
    expired    = State("expired")

    # Multiple guarded transitions — first match wins
    route = (
        checking.to(premium, event="ROUTE", guard="isPremium")
        | checking.to(basic, event="ROUTE", guard="isBasic")
        | checking.to(trial, event="ROUTE", guard="hasActiveTrial")
        | checking.to(expired, event="ROUTE")  # fallback — no guard
    )

    @guard
    def is_premium(self, context, event):
        return context.get("plan") == "premium"

    @guard
    def is_basic(self, context, event):
        return context.get("plan") == "basic"

    @guard
    def has_active_trial(self, context, event):
        return not context.get("trial_expired", True)


machine = SubscriptionRouter.create_machine()
interp = SyncInterpreter(machine).start()
interp.send("ROUTE")
print(interp.active_state_ids)
# {'subscriptionRouter.premium'}
interp.stop()
```

> **Tip:** The `|` operator creates a `TransitionGroup` internally. The transitions are evaluated **in order** — put the most specific guards first, and leave the fallback (no guard) last.

---

## Internal Transitions

Internal transitions run actions **without exiting and re-entering** the current state. Entry and exit actions do NOT fire:

```python
from xstate_statemachine import State, StateMachine, action, SyncInterpreter

class Counter(StateMachine):
    machine_id = "counter"
    initial_context = {"count": 0}

    counting = State("counting", initial=True)
    done     = State("done", final=True)

    # Internal transition — stays in "counting", runs action
    increment = counting.internal("INCREMENT", actions=["addOne"])
    decrement = counting.internal("DECREMENT", actions=["subtractOne"])

    # External transition — exits "counting" and enters "done"
    finish = counting.to(done, event="FINISH")

    @action
    def add_one(self, interpreter, context, event, action_def):
        context["count"] += 1

    @action
    def subtract_one(self, interpreter, context, event, action_def):
        context["count"] -= 1


machine = Counter.create_machine()
interp = SyncInterpreter(machine).start()

interp.send("INCREMENT")  # count: 1 (no exit/entry actions fire)
interp.send("INCREMENT")  # count: 2
interp.send("DECREMENT")  # count: 1
interp.send("FINISH")     # counting → done

print(interp.context["count"])  # 1
interp.stop()
```

> **Note:** Internal transitions are created with `state.internal(event, ...)` instead of `state.to(target, event=...)`. They have no target state — the machine stays where it is.

---

## Reenter Transitions

By default, a self-transition (same source and target) is treated as internal — no exit/entry actions fire. Use `reenter=True` to force a full exit and re-entry:

```python
from xstate_statemachine import State, StateMachine, SyncInterpreter

class Poller(StateMachine):
    machine_id = "poller"

    polling = State("polling", initial=True, entry=["startPolling"])
    stopped = State("stopped")

    # reenter=True forces exit + re-entry, restarting the entry action
    refresh = polling.to(polling, event="REFRESH", reenter=True)
    stop    = polling.to(stopped, event="STOP")


machine = Poller.create_machine()
```

With `reenter=True`, sending `REFRESH` while in `"polling"` will:
1. Run exit actions on `"polling"`
2. Run entry actions on `"polling"` (e.g., restart a timer)

Without `reenter=True`, the state would stay in `"polling"` and **no entry/exit actions would fire**.

---

## Hierarchy in the Pythonic API

Nested (compound) states are created by passing `states=[...]` to a parent `State`:

```python
from xstate_statemachine import State, StateMachine, SyncInterpreter

class AuthMachine(StateMachine):
    machine_id = "auth"

    logged_out = State("loggedOut", initial=True)
    logged_in  = State("loggedIn", states=[
        State("dashboard", initial=True),
        State("profile"),
        State("settings"),
    ])

    login  = logged_out.to(logged_in,  event="LOGIN")
    logout = logged_in.to(logged_out, event="LOGOUT")


machine = AuthMachine.create_machine()
interp = SyncInterpreter(machine).start()

interp.send("LOGIN")
print(interp.active_state_ids)
# {'auth.loggedIn', 'auth.loggedIn.dashboard'}

interp.send("LOGOUT")
print(interp.active_state_ids)
# {'auth.loggedOut'}
interp.stop()
```

### Deep Nesting

```python
app = State("app", initial=True, states=[
    State("main", initial=True, states=[
        State("home", initial=True),
        State("search"),
    ]),
    State("settings", states=[
        State("general", initial=True),
        State("privacy"),
    ]),
])
```

---

## Parallel States in the Pythonic API

Create parallel states with `parallel=True`:

```python
from xstate_statemachine import State, StateMachine, SyncInterpreter

class MediaPlayer(StateMachine):
    machine_id = "player"

    player = State("player", initial=True, parallel=True, states=[
        State("video", states=[
            State("loading", initial=True),
            State("playing"),
            State("paused"),
        ]),
        State("audio", states=[
            State("muted", initial=True),
            State("unmuted"),
        ]),
        State("controls", states=[
            State("visible", initial=True),
            State("hidden"),
        ]),
    ])


machine = MediaPlayer.create_machine()
interp = SyncInterpreter(machine).start()

print(interp.active_state_ids)
# All three regions are active simultaneously:
# {'player.player', 'player.player.video', 'player.player.video.loading',
#  'player.player.audio', 'player.player.audio.muted',
#  'player.player.controls', 'player.player.controls.visible'}
interp.stop()
```

> **Note:** Children of parallel states should **not** have `initial=True` — all regions are active simultaneously. Each child region must define its own `initial` child state.

---

## Delayed Transitions (`after`) in the Pythonic API

The `after` parameter on `State` defines timer-based transitions. Keys are delay times in milliseconds; values are target state names (or transition dicts with guards and actions):

### Basic Timeout

```python
from xstate_statemachine import State, StateMachine, SyncInterpreter, action

class SessionTimeout(StateMachine):
    machine_id = "session"
    initial_context = {"warnings": 0}

    active = State("active", initial=True, after={
        300000: "warning"   # 5 minutes → show warning
    })
    warning = State("warning", after={
        60000: "expired"    # 1 minute after warning → expire
    })
    expired = State("expired", final=True)

    # User activity resets the timer by re-entering 'active'
    activity = active.to(active, event="USER_ACTIVITY", reenter=True)
    dismiss  = warning.to(active, event="DISMISS_WARNING")

    @expired.enter
    def on_expire(self, interpreter, context, event, action_def):
        print("Session expired — please log in again")


machine = SessionTimeout.create_machine()
interp = SyncInterpreter(machine).start()
# Timer-based transitions fire automatically
# (SyncInterpreter processes pending timers on each send())
interp.stop()
```

### Delayed Transition with Guard and Actions

```python
from xstate_statemachine import State, StateMachine, SyncInterpreter, guard, action

class AutoSave(StateMachine):
    machine_id = "autosave"
    initial_context = {"dirty": False, "save_count": 0}

    editing = State("editing", initial=True, after={
        2000: {
            "target": "saving",
            "guard": "isDirty",
            "actions": ["markClean"]
        }
    })
    saving  = State("saving", after={
        500: "editing"  # Return to editing after save completes
    })

    @guard
    def is_dirty(self, context, event):
        return context.get("dirty", False)

    @action
    def mark_clean(self, interpreter, context, event, action_def):
        context["dirty"] = False
        context["save_count"] += 1
        print(f"Auto-saved (save #{context['save_count']})")


machine = AutoSave.create_machine()
```

### Multiple Timers on One State

```python
notification = State("notification", initial=True, after={
    3000:  {"actions": ["fadeIn"]},           # Fade in after 3s
    8000:  {"actions": ["startFadeOut"]},      # Start fading at 8s
    10000: "dismissed"                         # Dismiss at 10s
})
```

> **Tip:** In the Builder API, use `.state("name", after={...})` — the syntax is identical. In JSON config, use the `"after"` key on a state definition.

---

## Eventless Transitions (`always`) in the Pythonic API

Eventless (transient) transitions fire automatically when a state is entered, without waiting for an event. They're defined with the `always` parameter on `State`:

### Basic Auto-Transition

```python
from xstate_statemachine import State, StateMachine, SyncInterpreter, guard

class AgeRouter(StateMachine):
    machine_id = "ageRouter"
    initial_context = {"age": 25}

    # This state immediately routes to the correct target
    checking = State("checking", initial=True, always=[
        {"target": "senior",  "guard": "isSenior"},
        {"target": "adult",   "guard": "isAdult"},
        {"target": "minor"}   # fallback
    ])
    senior = State("senior")
    adult  = State("adult")
    minor  = State("minor")

    @guard
    def is_senior(self, context, event):
        return context.get("age", 0) >= 65

    @guard
    def is_adult(self, context, event):
        return context.get("age", 0) >= 18


machine = AgeRouter.create_machine()
interp = SyncInterpreter(machine).start()
print(interp.active_state_ids)
# {'ageRouter.adult'} — immediately routed based on context
interp.stop()
```

### Single Always Target

When there's only one unconditional target, pass a string:

```python
# Immediately transition to "processing" upon entering "submitted"
submitted = State("submitted", always="processing")
```

Or a dict for actions:

```python
submitted = State("submitted", always={
    "target": "processing",
    "actions": ["logSubmission"]
})
```

> **Note:** Eventless transitions are evaluated **immediately** when the state is entered. If guards are used, they're evaluated in order — the first match wins. If no guard matches, the state remains active until an event triggers a normal transition.

---

## Completion Transitions (`on_done`) in the Pythonic API

The `on_done` parameter defines a transition that fires when all child states of a compound state reach a final state. This is essential for multi-step workflows:

### Basic Completion

```python
from xstate_statemachine import State, StateMachine, SyncInterpreter

class Pipeline(StateMachine):
    machine_id = "pipeline"

    # Each step has a "working" and "done" child
    step1 = State("step1", initial=True, states=[
        State("working", initial=True),
        State("done", final=True),
    ], on_done="step2")    # When step1's child reaches "done" → go to step2

    step2 = State("step2", states=[
        State("working", initial=True),
        State("done", final=True),
    ], on_done="complete")

    complete = State("complete", final=True)


machine = Pipeline.create_machine()
interp = SyncInterpreter(machine).start()
print(interp.active_state_ids)
# {'pipeline.step1', 'pipeline.step1.working'}
interp.stop()
```

### Completion with Actions

```python
step1 = State("step1", initial=True, states=[
    State("working", initial=True),
    State("finished", final=True),
], on_done={
    "target": "step2",
    "actions": ["logStepComplete", "saveProgress"]
})
```

### Completion in Parallel States

In parallel states, `on_done` fires when **all regions** reach a final state:

```python
from xstate_statemachine import State, StateMachine, SyncInterpreter

class ParallelPipeline(StateMachine):
    machine_id = "parallelPipeline"

    processing = State("processing", initial=True, parallel=True, states=[
        State("validation", states=[
            State("validating", initial=True),
            State("valid", final=True),
        ]),
        State("enrichment", states=[
            State("enriching", initial=True),
            State("enriched", final=True),
        ]),
    ], on_done="complete")  # Fires when BOTH regions reach final

    complete = State("complete", final=True)


machine = ParallelPipeline.create_machine()
```

> **Tip:** `on_done` is the Pythonic equivalent of the JSON `"onDone"` key on compound states. It's distinct from `invoke`'s `onDone`, which fires when a service completes.

---

## Context in the Pythonic API

### Class-Based

```python
class ShoppingCart(StateMachine):
    machine_id = "cart"
    initial_context = {
        "items": [],
        "total": 0.0,
        "discount": None,
        "coupon_code": None
    }

    browsing  = State("browsing", initial=True)
    checkout  = State("checkout")
    # ...
```

### Builder

```python
machine = (
    MachineBuilder("cart")
    .context({"items": [], "total": 0.0})
    .state("browsing", initial=True)
    # ...
    .build()
)
```

### Functional

```python
machine = build_machine(
    id="cart",
    states=[browsing, checkout],
    context={"items": [], "total": 0.0},
)
```

### Overriding Context at Runtime

All three styles support context overrides when creating the machine:

```python
# Class-based
machine = ShoppingCart.create_machine(context={"items": ["preset"], "total": 9.99})

# Builder — pass context to .build()
machine = builder.build(context={"items": ["preset"], "total": 9.99})
```

---

## Complete Real-World Example: Form Wizard

This example demonstrates a multi-step form wizard using the class-based API with hierarchy, guards, actions, entry/exit actions, and context:

```python
from xstate_statemachine import (
    State, StateMachine, SyncInterpreter,
    action, guard
)

class FormWizard(StateMachine):
    machine_id = "wizard"
    initial_context = {
        "current_step": 1,
        "steps_completed": [],
        "form_data": {
            "name": "",
            "email": "",
            "plan": "",
            "payment_method": "",
        },
        "errors": [],
        "submitted": False,
    }

    # ── Top-Level States ────────────────────────────────────
    step1 = State("step1", initial=True, states=[
        State("editing",  initial=True),
        State("complete", final=True),
    ], on_done="step2")

    step2 = State("step2", states=[
        State("editing",  initial=True),
        State("complete", final=True),
    ], on_done="step3")

    step3 = State("step3", states=[
        State("editing",  initial=True),
        State("complete", final=True),
    ], on_done="review")

    review    = State("review")
    submitted = State("submitted", final=True)

    # ── Transitions ─────────────────────────────────────────
    # Going back
    back_to_step1 = step2.to(step1, event="BACK")
    back_to_step2 = step3.to(step2, event="BACK")
    back_to_edit  = review.to(step1, event="EDIT")

    # Submit from review
    submit = review.to(submitted, event="SUBMIT", guard="allStepsValid")

    # ── Entry/Exit Actions ──────────────────────────────────
    @step1.enter
    def on_enter_step1(self, interpreter, context, event, action_def):
        context["current_step"] = 1
        print("📋 Step 1: Personal Information")

    @step2.enter
    def on_enter_step2(self, interpreter, context, event, action_def):
        context["current_step"] = 2
        if 1 not in context["steps_completed"]:
            context["steps_completed"].append(1)
        print("📋 Step 2: Choose Your Plan")

    @step3.enter
    def on_enter_step3(self, interpreter, context, event, action_def):
        context["current_step"] = 3
        if 2 not in context["steps_completed"]:
            context["steps_completed"].append(2)
        print("📋 Step 3: Payment Details")

    @review.enter
    def on_enter_review(self, interpreter, context, event, action_def):
        if 3 not in context["steps_completed"]:
            context["steps_completed"].append(3)
        print("📋 Review Your Submission")
        print(f"   Data: {context['form_data']}")

    @submitted.enter
    def on_enter_submitted(self, interpreter, context, event, action_def):
        context["submitted"] = True
        print("✅ Form submitted successfully!")

    # ── Guards ──────────────────────────────────────────────
    @guard
    def all_steps_valid(self, context, event):
        required_steps = [1, 2, 3]
        return all(s in context["steps_completed"] for s in required_steps)

    @guard
    def has_name(self, context, event):
        return bool(context["form_data"].get("name"))

    @guard
    def has_email(self, context, event):
        return "@" in context["form_data"].get("email", "")

    # ── Actions ─────────────────────────────────────────────
    @action
    def update_form(self, interpreter, context, event, action_def):
        if hasattr(event, "payload") and event.payload:
            context["form_data"].update(event.payload)

    @action
    def clear_errors(self, interpreter, context, event, action_def):
        context["errors"] = []


# ── Run the Wizard ──────────────────────────────────────────
machine = FormWizard.create_machine()
interp = SyncInterpreter(machine).start()
# Output: 📋 Step 1: Personal Information

print(interp.active_state_ids)
# {'wizard.step1', 'wizard.step1.editing'}

interp.stop()
```

---

## Entry/Exit Action Decorators

The class-based style supports `@state.enter` and `@state.exit` decorators that register functions as entry or exit actions directly on a state. This is more readable than listing action names as strings.

### Basic Entry/Exit Example

```python
from xstate_statemachine import State, StateMachine, SyncInterpreter, action

class DoorMachine(StateMachine):
    machine_id = "door"

    closed = State("closed", initial=True)
    opened = State("opened")
    locked = State("locked")

    # ── Transitions ──────────────────────────────────────
    open_door  = closed.to(opened, event="OPEN")
    close_door = opened.to(closed, event="CLOSE")
    lock       = closed.to(locked, event="LOCK")
    unlock     = locked.to(closed, event="UNLOCK")

    # ── Entry/Exit Actions via Decorators ────────────────
    @opened.enter
    def announce_open(self, interpreter, context, event, action_def):
        print("🚪 Door is now OPEN")

    @opened.exit
    def announce_closing(self, interpreter, context, event, action_def):
        print("🚪 Door is closing...")

    @locked.enter
    def announce_locked(self, interpreter, context, event, action_def):
        print("🔒 Door is LOCKED")

    @locked.exit
    def announce_unlocking(self, interpreter, context, event, action_def):
        print("🔓 Unlocking door...")

machine = DoorMachine.create_machine()
interp = SyncInterpreter(machine).start()

interp.send("OPEN")
# 🚪 Door is now OPEN

interp.send("CLOSE")
# 🚪 Door is closing...

interp.send("LOCK")
# 🔒 Door is LOCKED

interp.send("UNLOCK")
# 🔓 Unlocking door...

interp.stop()
```

### Entry/Exit with Context Mutation

```python
from xstate_statemachine import State, StateMachine, SyncInterpreter

class SessionMachine(StateMachine):
    machine_id = "session"
    initial_context = {"login_count": 0, "active_since": None}

    logged_out = State("logged_out", initial=True)
    logged_in  = State("logged_in")

    login  = logged_out.to(logged_in,  event="LOGIN")
    logout = logged_in.to(logged_out, event="LOGOUT")

    @logged_in.enter
    def on_login(self, interpreter, context, event, action_def):
        import time
        context["login_count"] += 1
        context["active_since"] = time.time()
        print(f"Login #{context['login_count']}")

    @logged_in.exit
    def on_logout(self, interpreter, context, event, action_def):
        context["active_since"] = None
        print("Session ended")

machine = SessionMachine.create_machine()
interp = SyncInterpreter(machine).start()

interp.send("LOGIN")
# Login #1
print(interp.context["login_count"])
# 1

interp.send("LOGOUT")
# Session ended

interp.send("LOGIN")
# Login #2

interp.stop()
```

> **Note:** `@state.enter` and `@state.exit` decorators are only available in the class-based `StateMachine` style. For builder and functional styles, use the `entry` and `exit` parameters on `State()`.

---

## The `transition()` Standalone Function

The `transition()` function is a module-level alternative to `State.to()`. It creates transitions between existing `State` objects without calling a method on one of them. This is useful in the functional API style.

```python
from xstate_statemachine import State, build_machine, SyncInterpreter, transition

# Define states
idle    = State("idle", initial=True)
loading = State("loading")
success = State("success")
error   = State("error")

# Define transitions using the standalone function
fetch  = transition(idle, "FETCH", loading)
loaded = transition(loading, "SUCCESS", success)
failed = transition(loading, "FAILURE", error)
retry  = transition(error, "RETRY", loading, guard="hasRetries")
reset  = transition(error, "RESET", idle)
reload = transition(success, "REFRESH", loading)

machine = build_machine(
    id="dataFetcher",
    states=[idle, loading, success, error],
    transitions=[fetch, loaded, failed, retry, reset, reload]
)

interp = SyncInterpreter(machine).start()
print(interp.active_state_ids)
# {'dataFetcher.idle'}

interp.send("FETCH")
print(interp.active_state_ids)
# {'dataFetcher.loading'}

interp.stop()
```

### `transition()` with Guards and Actions

```python
from xstate_statemachine import State, build_machine, SyncInterpreter, transition, action, guard

off = State("off", initial=True)
on  = State("on")

toggle_on  = transition(off, "TOGGLE", on, actions=["logToggle"])
toggle_off = transition(on, "TOGGLE", off, actions=["logToggle"])

# With reenter flag
reset = transition(on, "RESET", on, reenter=True, actions=["clearState"])

machine = build_machine(
    id="switch",
    states=[off, on],
    transitions=[toggle_on, toggle_off, reset]
)

interp = SyncInterpreter(machine).start()
interp.stop()
```

> **Tip:** `transition()` is equivalent to `source.to(target, event=event, ...)`. Use whichever reads more naturally in your code. The `.to()` method is more common in class-based code; `transition()` is more common in functional code.

---

## Style Comparison Summary

| Feature | Class-Based | Builder | Functional |
|---------|:-----------:|:-------:|:----------:|
| Self-contained file | ✅ | ✅ | ✅ |
| IDE autocomplete | ✅✅ | ✅ | ✅ |
| Decorators (`@action`, `@guard`) | ✅ | ❌ (use `.action()`) | ✅ |
| `@state.enter` / `@state.exit` | ✅ | ❌ | ❌ |
| `\|` operator for guards | ✅ | ❌ (use multiple `.transition()`) | ✅ |
| `.internal()` transitions | ✅ | ✅ (via `internal=True`) | ✅ |
| Dynamic construction | ❌ | ✅✅ | ✅ |
| Hierarchy | ✅ | ✅ (via `.child_states()`) | ✅ (via `states=[...]`) |
| Parallel states | ✅ | ✅ | ✅ |

> **Tip:** Start with the **class-based** style. It's the most Pythonic, the most readable in code reviews, and the most IDE-friendly. Switch to the builder if you need to construct machines dynamically (e.g., from a database or config file).

> **Tip:** All three styles can be mixed in the same project. A class-based machine and a builder-based machine produce identical `MachineNode` objects and run on the same interpreters.
