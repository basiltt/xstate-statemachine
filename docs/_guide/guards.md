---
title: "Guards"
description: "Conditional transitions — control flow with boolean guard functions."
---

Guards are **boolean functions** that control whether a transition is allowed to fire. When an event arrives, the interpreter evaluates each candidate transition's guard in order — the first transition whose guard returns `True` (or has no guard) wins. If every guard returns `False`, the event is discarded.

## What are Guards?

A guard is a pure, synchronous function that answers one question: *"Should this transition happen right now?"* Guards inspect the machine's context and the incoming event data to make that decision.

Key characteristics:

- **Boolean** — must return `True` or `False`.
- **Synchronous** — `async def` guards raise `NotSupportedError`.
- **Side-effect-free** — guards should only *read* context, never *modify* it. Use actions for mutations.
- **Short-circuiting** — the first matching transition wins; remaining guards are not evaluated.

## Guard Signature

```python
def my_guard(context: dict, event: Event) -> bool:
    ...
```

> **Note:** Guard functions receive `(context, event)` — **NOT** `(interpreter, context, event, action_def)`. This is intentionally different from the action signature. Guards should be pure decision functions with no need for the interpreter.

> **Params argument:** Guards may optionally accept a third `params` argument to receive parameters from a [parameterised guard](#parameterised-guards) config: `def my_guard(context, event, params): ...`. The interpreter arity-checks the callable, so existing 2-argument guards keep working unchanged.

## JSON Guards

### The `guard` Key (and Legacy `cond` Alias)

The library accepts both `"guard"` and `"cond"` as the key for conditional transitions:

```json
// Preferred (XState v5 style)
{"target": "allowed", "guard": "isAdult"}

// Also supported (XState v4 style)
{"target": "allowed", "cond": "isAdult"}
```

Both are functionally identical. The `cond` key exists for backward compatibility with XState v4 configs — the library normalizes it to `guard` internally. **Prefer `guard`** in new configs.

### Single Guard

Attach a `guard` key to a transition object:

```json
{
  "id": "ageGate",
  "initial": "checking",
  "context": { "age": 21 },
  "states": {
    "checking": {
      "on": {
        "VERIFY": {
          "target": "allowed",
          "guard": "isAdult"
        }
      }
    },
    "allowed": {},
    "rejected": {}
  }
}
```

If `isAdult` returns `False`, the `VERIFY` event is silently discarded — no transition happens.

### Multiple Guarded Transitions (Array Form)

Use an **array** of transition objects to define multiple candidate transitions for the same event. The interpreter evaluates them top-to-bottom, and the **first matching guard wins**:

```json
{
  "id": "ageGate",
  "initial": "checking",
  "context": { "age": 16 },
  "states": {
    "checking": {
      "on": {
        "VERIFY": [
          { "target": "allowed",  "guard": "isAdult" },
          { "target": "teen",     "guard": "isTeen" },
          { "target": "rejected" }
        ]
      }
    },
    "allowed":  {},
    "teen":     {},
    "rejected": {}
  }
}
```

### Fallback Transition (No Guard)

The last transition in the array has no `guard` key — it acts as a **fallback** that always matches. This is the "else" branch:

```json
"VERIFY": [
  { "target": "allowed",  "guard": "isAdult" },
  { "target": "rejected" }
]
```

> **Tip:** Always include a fallback transition as the last item. Without one, events may be silently discarded if no guard matches.

## Composite Guards (`and` / `or` / `not`)

Guards can be composed from other guards using the built-in `and`, `or`, and `not` operators — no user implementation is needed for the composition itself, only for the leaf guards it references:

```json
{
  "target": "allowed",
  "guard": {
    "type": "and",
    "params": { "guards": ["isAdult", "hasFunds"] }
  }
}
```

- **`and`** — passes only if *every* nested guard passes (short-circuits like Python's `all()`).
- **`or`** — passes if *any* nested guard passes (short-circuits like Python's `any()`).
- **`not`** — inverts a single nested guard; it requires **exactly one** child guard.

```python
from src.xstate_statemachine import create_machine, SyncInterpreter, MachineLogic

config = {
    "id": "checkout",
    "initial": "cart",
    "context": {"age": 20, "hasFunds": True},
    "states": {
        "cart": {
            "on": {
                "SUBMIT": [
                    {
                        "target": "allowed",
                        "guard": {
                            "type": "and",
                            "params": {"guards": ["isAdult", "hasFunds"]},
                        },
                    },
                    {"target": "denied"},
                ]
            }
        },
        "allowed": {},
        "denied": {},
    },
}


class CheckoutLogic(MachineLogic):
    def isAdult(self, context, event):
        return context.get("age", 0) >= 18

    def hasFunds(self, context, event):
        return context.get("hasFunds", False)


machine = create_machine(config, logic=CheckoutLogic())
interp = SyncInterpreter(machine).start()
interp.send("SUBMIT")
print(interp.current_state_ids)  # {"checkout.allowed"}
interp.stop()
```

Nested guards can also be declared inline under `children`, or (for `not`) under `params.guard` — the parser accepts whichever shape you emit.

> **Note:** A *bare string* guard named `"and"`, `"or"`, or `"not"` is always treated as a user predicate, never as a composition — only the object form (`{"type": "and", ...}`) triggers composite behavior. This means you can still register a guard literally called `and` without conflict.


### Shorthand: `"!name"`

`"guard": "!isLocked"` is sugar for `{"type": "not", "children": ["isLocked"]}`
-- the form Stately's editor emits for a negated guard. You implement the
positive guard (`isLocked`) only; the engine inverts it.

```python
from xstate_statemachine import SyncInterpreter, MachineLogic, create_machine

config = {
    "id": "door",
    "initial": "closed",
    "states": {
        "closed": {"on": {"OPEN": {"target": "open", "guard": "!isLocked"}}},
        "open": {},
    },
}
machine = create_machine(config, logic=MachineLogic(guards={"isLocked": lambda c, e: False}))
interp = SyncInterpreter(machine).start()
interp.send("OPEN")
assert interp.matches("door.open")
```

## Built-in `stateIn` Guard

`stateIn` is a built-in guard, satisfied when a given state is part of the machine's active configuration — either as an active leaf or as an ancestor of one. No implementation is required:

```json
{
  "target": "step1",
  "guard": {
    "type": "stateIn",
    "params": { "state": "#wizard.step2" }
  }
}
```

```python
from src.xstate_statemachine import create_machine, SyncInterpreter

config = {
    "id": "wizard",
    "initial": "step1",
    "context": {},
    "states": {
        "step1": {"on": {"NEXT": "step2"}},
        "step2": {
            "on": {
                "BACK_TO_ONE": [
                    {
                        "target": "step1",
                        "guard": {
                            "type": "stateIn",
                            "params": {"state": "#wizard.step2"},
                        },
                    },
                    {"target": "step2"},
                ]
            }
        },
    },
}

machine = create_machine(config)
interp = SyncInterpreter(machine).start()
interp.send("NEXT")
print(interp.current_state_ids)  # {"wizard.step2"}
interp.send("BACK_TO_ONE")
print(interp.current_state_ids)  # {"wizard.step1"}
interp.stop()
```

The state id accepts both the `#machine.a.b` and bare `machine.a.b` spellings.

> **Note:** If you register your own guard named `stateIn` in `MachineLogic.guards`, your implementation takes precedence over the built-in — the same resolution order used for built-in actions.

## Parameterised Guards

A guard can be given a `params` object, which the interpreter resolves and passes to the guard function as an optional **third argument**:

```json
{
  "target": "processing",
  "guard": {
    "type": "hasSufficientFunds",
    "params": { "minAmount": 100 }
  }
}
```

```python
from src.xstate_statemachine import create_machine, SyncInterpreter, MachineLogic, guard

config = {
    "id": "withdrawalMachine",
    "initial": "idle",
    "context": {"balance": 500.00},
    "states": {
        "idle": {
            "on": {
                "WITHDRAW": [
                    {
                        "target": "processing",
                        "guard": {
                            "type": "hasSufficientFunds",
                            "params": {"minAmount": 100},
                        },
                    },
                    {"target": "denied"},
                ]
            }
        },
        "processing": {},
        "denied": {},
    },
}


class BankLogic(MachineLogic):
    @guard
    def hasSufficientFunds(self, context, event, params):
        min_amount = (params or {}).get("minAmount", 0)
        amount = event.payload.get("amount", 0)
        return amount >= min_amount and context["balance"] >= amount


machine = create_machine(config, logic=BankLogic())
interp = SyncInterpreter(machine).start()
interp.send("WITHDRAW", amount=200.00)
print(interp.current_state_ids)  # {"withdrawalMachine.processing"}
interp.stop()

interp2 = SyncInterpreter(machine).start()
interp2.send("WITHDRAW", amount=50.00)
print(interp2.current_state_ids)  # {"withdrawalMachine.denied"} — below minAmount
interp2.stop()
```

The interpreter arity-checks the guard callable, so a plain two-argument `(context, event)` guard keeps working unchanged even if it's never given `params`. `params` may also be a function of `{context, event}`, re-evaluated on every use, instead of a static dict.

## Guard Implementation with MachineLogic

When using the JSON configuration approach, implement guards as methods on a `MachineLogic` subclass:

> **Note:** A plain, undecorated method is auto-registered by its **arity** — 2 arguments (`self, context, event`) is registered as a guard. Because a 2-argument callable is also a valid service signature, this arity is ambiguous and `create_machine(...)` emits a `UserWarning` recommending an explicit decorator. The method still runs correctly; use `@guard` (see [Pythonic Guards](#pythonic-guards) below) on the method to silence the warning.

```python
from xstate_statemachine import create_machine, SyncInterpreter, MachineLogic

config = {
    "id": "ageGate",
    "initial": "checking",
    "context": {"age": 16},
    "states": {
        "checking": {
            "on": {
                "VERIFY": [
                    {"target": "allowed",  "guard": "isAdult"},
                    {"target": "teen",     "guard": "isTeen"},
                    {"target": "rejected"}
                ]
            }
        },
        "allowed":  {},
        "teen":     {},
        "rejected": {}
    }
}

class AgeLogic(MachineLogic):
    def isAdult(self, context, event):
        return context.get("age", 0) >= 18

    def isTeen(self, context, event):
        return 13 <= context.get("age", 0) < 18

machine = create_machine(config, logic=AgeLogic())
interp = SyncInterpreter(machine).start()

interp.send("VERIFY")
print(interp.current_state_ids)  # {"ageGate.teen"} — age is 16
interp.stop()
```

## Pythonic Guards

### `@guard` Decorator

The `@guard` decorator marks a function as a guard for any Pythonic API style:

```python
from xstate_statemachine import guard

@guard
def is_adult(context, event):
    return context.get("age", 0) >= 18
```

### Auto-Naming (snake_case → camelCase)

The decorator automatically converts `snake_case` function names to `camelCase` for the guard registry:

```python
@guard
def is_valid_email(context, event):
    return "@" in context.get("email", "")
# Registered as "isValidEmail"
```

### Explicit Naming with `@guard("customName")`

Override the auto-generated name by passing a string argument:

```python
@guard("checkAge")
def verify_user_age(context, event):
    return context.get("age", 0) >= 18
# Registered as "checkAge" (not "verifyUserAge")
```

### Multiple Guarded Transitions with `|` Operator

In the class-based API, combine transitions using `|` to create guarded routing:

```python
from xstate_statemachine import State, StateMachine, SyncInterpreter, guard

class AgeGate(StateMachine):
    machine_id = "ageGate"
    initial_context = {"age": 16}

    checking = State("checking", initial=True)
    allowed  = State("allowed")
    rejected = State("rejected")

    # First matching guard wins; last transition is the fallback
    verify = (
        checking.to(allowed,  event="VERIFY", guard="isAdult")
        | checking.to(rejected, event="VERIFY")
    )

    @guard
    def is_adult(self, context, event):
        return context.get("age", 0) >= 18

machine = AgeGate.create_machine()
interp = SyncInterpreter(machine).start()
interp.send("VERIFY")
print(interp.current_state_ids)  # {"ageGate.rejected"} — age is 16
interp.stop()
```

## Guard Evaluation Order

**The FIRST matching guard wins.** Order matters. The interpreter evaluates candidate transitions from top to bottom (in arrays) or first to last (in `|` chains):

```python
# Order matters! isVIP is checked first.
verify = (
    checking.to(vip_lounge, event="ENTER", guard="isVIP")
    | checking.to(allowed,  event="ENTER", guard="isAdult")
    | checking.to(rejected, event="ENTER")  # fallback
)
```

If a user is both VIP *and* adult, they go to `vip_lounge` because `isVIP` is evaluated first.

> **Warning:** Placing the fallback (no-guard) transition before guarded transitions means the fallback always wins and the guards are never checked. Always put fallbacks last.

## Guards with Context

Guards commonly read context to make decisions:

```python
from xstate_statemachine import create_machine, SyncInterpreter, MachineLogic

config = {
    "id": "withdrawalMachine",
    "initial": "idle",
    "context": {"balance": 500.00},
    "states": {
        "idle": {
            "on": {
                "WITHDRAW": [
                    {"target": "processing", "guard": "hasSufficientFunds"},
                    {"target": "denied"}
                ]
            }
        },
        "processing": {},
        "denied": {}
    }
}

class BankLogic(MachineLogic):
    def hasSufficientFunds(self, context, event):
        amount = event.payload.get("amount", 0)
        return context["balance"] >= amount

machine = create_machine(config, logic=BankLogic())
interp = SyncInterpreter(machine).start()

interp.send("WITHDRAW", amount=200.00)
print(interp.current_state_ids)  # {"withdrawalMachine.processing"}
interp.stop()
```

## Guards with Event Data

Guards can also inspect the incoming event payload:

```python
class RegistrationLogic(MachineLogic):
    def isValidAge(self, context, event):
        age = event.payload.get("age", 0)
        return isinstance(age, int) and 0 < age < 150

    def hasAcceptedTerms(self, context, event):
        return event.payload.get("termsAccepted", False) is True
```

```python
interp.send("REGISTER", age=25, termsAccepted=True)
```

## Combining Guards

When you need to check multiple conditions, you have two approaches:

### Approach 1: Single guard with compound logic

```python
class Logic(MachineLogic):
    def canPurchase(self, context, event):
        has_funds = context["balance"] >= event.payload.get("price", 0)
        is_in_stock = context.get("stock", 0) > 0
        return has_funds and is_in_stock
```

### Approach 2: Multiple guarded transitions (more readable)

```json
"BUY": [
  { "target": "outOfStock",    "guard": "isOutOfStock" },
  { "target": "insufficientFunds", "guard": "insufficientBalance" },
  { "target": "purchased" }
]
```

> **Tip:** Use approach 1 when conditions are closely related. Use approach 2 when each failure case needs a different target state.

## Guards Must Be Synchronous

Guards **cannot** be `async def`. Attempting to register an async guard raises `NotSupportedError` immediately:

```python
from xstate_statemachine import guard, NotSupportedError

# This raises NotSupportedError at decoration time!
try:
    @guard
    async def is_valid(context, event):
        return True
except NotSupportedError as e:
    print(e)  # "Guard 'is_valid' must be synchronous (guards cannot be async)"
```

This restriction exists because guard evaluation happens in the hot path of transition resolution. Async guards would introduce unpredictable timing into the state machine's deterministic flow.

## Guards vs Actions

| | Guards | Actions |
|--|--------|---------|
| **Purpose** | Control flow — decide *if* a transition happens | Side effects — *do something* during a transition |
| **Return value** | `bool` (required) | `None` |
| **Signature** | `(context, event) -> bool` | `(interpreter, context, event, action_def) -> None` |
| **Side effects** | Should have none | Expected to have side effects |
| **Timing** | Evaluated *before* the transition | Executed *during* the transition |
| **Context mutation** | Never — read only | Allowed and common |

## Error Handling in Guards

If a guard raises an exception, the interpreter substitutes a result and moves on to the next candidate. What it substitutes is controlled by the machine-config key **`guardErrorPolicy`**:

| Value | Behavior |
|-------|----------|
| `"false"` (default) | The raise is treated as `False` — the transition is skipped, matching pre-0.8.0 behavior. |
| `"true"` | The raise is treated as `True` — the transition is taken despite the error. |
| `"raise"` | The exception propagates. In `SyncInterpreter` it reaches the `send()` caller; in the async `Interpreter` the run loop contains it and stays alive. Either way the machine is left in its pre-event state and remains usable. |

```json
{
  "id": "m",
  "guardErrorPolicy": "false",
  "initial": "a",
  "states": { "a": {} }
}
```

Whatever the policy, the raise is observable via the `on_guard_error(interpreter, guard_name, event, error)` plugin hook, fired *before* the substituted result is reported — previously a raising guard was indistinguishable from one that legitimately returned `False`. See [Plugins](../plugins/#plugin-hooks-reference).

```python
class Logic(MachineLogic):
    def isValid(self, context, event):
        # If "data" key is missing, KeyError is raised
        # guardErrorPolicy="false" (the default) treats this guard as False
        return context["data"]["value"] > 0
```

> **Tip:** Prefer defensive coding with `.get()` to avoid relying on exception-as-False behavior. It makes guards easier to debug:

```python
class Logic(MachineLogic):
    def isValid(self, context, event):
        data = context.get("data")
        if data is None:
            return False
        return data.get("value", 0) > 0
```

## Complete Example: Age Verification Gate

A full example with multiple paths based on age ranges:

```python
from xstate_statemachine import create_machine, SyncInterpreter, MachineLogic

config = {
    "id": "ageVerification",
    "initial": "verifying",
    "context": {},
    "states": {
        "verifying": {
            "on": {
                "SUBMIT_AGE": [
                    {"target": "senior",   "guard": "isSenior"},
                    {"target": "adult",    "guard": "isAdult"},
                    {"target": "teen",     "guard": "isTeen"},
                    {"target": "child",    "guard": "isChild"},
                    {"target": "invalid"}
                ]
            }
        },
        "senior":  {},
        "adult":   {},
        "teen":    {},
        "child":   {},
        "invalid": {}
    }
}

class AgeVerificationLogic(MachineLogic):
    def isSenior(self, context, event):
        age = event.payload.get("age", -1)
        return age >= 65

    def isAdult(self, context, event):
        age = event.payload.get("age", -1)
        return 18 <= age < 65

    def isTeen(self, context, event):
        age = event.payload.get("age", -1)
        return 13 <= age < 18

    def isChild(self, context, event):
        age = event.payload.get("age", -1)
        return 0 <= age < 13

machine = create_machine(config, logic=AgeVerificationLogic())

# Test with different ages
for test_age in [70, 30, 15, 8, -5]:
    interp = SyncInterpreter(machine).start()
    interp.send("SUBMIT_AGE", age=test_age)
    state = next(iter(interp.current_state_ids)).split(".")[-1]
    print(f"Age {test_age:>3} -> {state}")
    interp.stop()

# Output:
# Age  70 -> senior
# Age  30 -> adult
# Age  15 -> teen
# Age   8 -> child
# Age  -5 -> invalid
```

## Complete Example: Role-Based Routing

A role-based access control machine using guards on event payload:

```python
from xstate_statemachine import (
    State, StateMachine, SyncInterpreter, guard, action
)

class RoleRouter(StateMachine):
    machine_id = "roleRouter"
    initial_context = {"auditLog": []}

    gate       = State("gate", initial=True)
    admin_area = State("adminArea")
    user_area  = State("userArea")
    guest_area = State("guestArea")

    # Route based on role — first matching guard wins
    access = (
        gate.to(admin_area, event="ACCESS", guard="isAdmin", actions=["logAccess"])
        | gate.to(user_area, event="ACCESS", guard="isUser", actions=["logAccess"])
        | gate.to(guest_area, event="ACCESS", actions=["logAccess"])
    )

    @guard
    def is_admin(self, context, event):
        return event.payload.get("role") == "admin"

    @guard
    def is_user(self, context, event):
        return event.payload.get("role") == "user"

    @action
    def log_access(self, interpreter, context, event, action_def):
        role = event.payload.get("role", "guest")
        name = event.payload.get("name", "anonymous")
        context["auditLog"].append(f"{name} ({role})")

machine = RoleRouter.create_machine()

# Test admin access
interp = SyncInterpreter(machine).start()
interp.send("ACCESS", role="admin", name="Alice")
print(interp.current_state_ids)  # {"roleRouter.adminArea"}
print(interp.context["auditLog"])  # ["Alice (admin)"]
interp.stop()

# Test guest access (no role specified)
interp = SyncInterpreter(machine).start()
interp.send("ACCESS", name="Bob")
print(interp.current_state_ids)  # {"roleRouter.guestArea"}
print(interp.context["auditLog"])  # ["Bob (guest)"]
interp.stop()
```

## See Also

- **[Context](../context/)** — guards often read context values to make decisions
- **[Actions](../actions/)** — actions that run alongside guarded transitions
- **[Pythonic API](../pythonic-api/)** — `@guard` decorator and the `|` operator for combining guarded transitions
- **[JSON Configuration](../json-config/)** — full schema reference for the `guard`/`cond` keys and the `guardErrorPolicy` machine-level option
- **[Core Concepts](../core-concepts/)** — guard evaluation order and how guards fit into the transition lifecycle
- **[Troubleshooting](../troubleshooting/)** — common guard-related errors
