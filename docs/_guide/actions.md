---
title: "Actions"
description: "Side effects on entry, exit, and transitions — logging, context updates, notifications."
---

Actions are **side effects** that execute at specific moments in a state machine's lifecycle. They don't control flow — they *do* things: update context, log messages, send notifications, or trigger external systems.

## What are Actions?

An action is a callable that the interpreter invokes at a well-defined point during a transition. Actions are the primary mechanism for making your state machine *do* something beyond simply switching states.

Key characteristics:

- **Fire-and-forget** — actions don't return meaningful values.
- **Context-mutating** — actions are the *only* place you should modify context.
- **Deterministic ordering** — the interpreter runs actions in a predictable, documented order.
- **Synchronous** (in `SyncInterpreter`) — async actions raise `NotSupportedError`.

## Action Signature

```python
def my_action(interpreter, context, event, action_def) -> None:
    ...
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `interpreter` | `SyncInterpreter` or `Interpreter` | The running interpreter instance |
| `context` | `dict` | The machine's mutable context dictionary |
| `event` | `Event` | The event that triggered this action |
| `action_def` | `ActionDefinition` | Metadata about the action (name, params) |

> **Note:** The action signature `(interpreter, context, event, action_def)` is different from the guard signature `(context, event)`. Actions get the interpreter and action definition; guards do not.

## When Actions Run

| Trigger | When It Fires | Defined In |
|---------|---------------|------------|
| **Entry actions** | When a state is entered | `"entry"` on the state |
| **Exit actions** | When a state is exited | `"exit"` on the state |
| **Transition actions** | During a transition (between exit and entry) | `"actions"` on the transition |

## Execution Order

When a transition fires from state A to state B, actions execute in this strict order:

```
1. Exit actions on state A          ← source state's "exit"
2. Transition actions               ← the transition's "actions"
3. Entry actions on state B         ← target state's "entry"
```

This order is guaranteed and consistent across all interpreter types.

```python
# Example: editing → submitting
# 1. saveDraft     (exit action on "editing")
# 2. validate      (transition action)
# 3. clearErrors   (transition action)
# 4. showSpinner   (entry action on "submitting")
```

## JSON Actions

### Single Action (String)

```json
{
  "on": {
    "SUBMIT": {
      "target": "submitting",
      "actions": "validate"
    }
  }
}
```

### Multiple Actions (Array)

```json
{
  "on": {
    "SUBMIT": {
      "target": "submitting",
      "actions": ["validate", "clearErrors", "logSubmission"]
    }
  }
}
```

### Entry and Exit Actions on States

```json
{
  "states": {
    "editing": {
      "entry": "loadDraft",
      "exit": "saveDraft",
      "on": {
        "SUBMIT": {
          "target": "submitting",
          "actions": ["validate", "clearErrors"]
        }
      }
    },
    "submitting": {
      "entry": "showSpinner"
    }
  }
}
```

### Multiple Entry/Exit Actions

Entry and exit support arrays too:

```json
{
  "states": {
    "editing": {
      "entry": ["loadDraft", "startAutoSave"],
      "exit":  ["saveDraft", "stopAutoSave"]
    }
  }
}
```

## Action Implementation with MachineLogic

When using JSON configuration, implement actions as methods on a `MachineLogic` subclass:

```python
from xstate_statemachine import create_machine, SyncInterpreter, MachineLogic

config = {
    "id": "formMachine",
    "initial": "editing",
    "context": {"draft": "", "errors": [], "isValid": False},
    "states": {
        "editing": {
            "entry": "loadDraft",
            "exit": "saveDraft",
            "on": {
                "SUBMIT": {
                    "target": "submitting",
                    "actions": ["validate", "clearErrors"]
                }
            }
        },
        "submitting": {
            "entry": "showSpinner",
            "on": {
                "SUCCESS": {"target": "done"},
                "FAILURE": {"target": "editing", "actions": "setError"}
            }
        },
        "done": {"type": "final"}
    }
}

class FormLogic(MachineLogic):
    def loadDraft(self, interpreter, context, event, action_def):
        context["draft"] = "Loaded from storage"
        print("Loading saved draft...")

    def saveDraft(self, interpreter, context, event, action_def):
        print(f"Auto-saving draft: '{context['draft']}'")

    def validate(self, interpreter, context, event, action_def):
        context["isValid"] = len(context["draft"]) > 0
        print(f"Validating... valid={context['isValid']}")

    def clearErrors(self, interpreter, context, event, action_def):
        context["errors"] = []
        print("Errors cleared.")

    def showSpinner(self, interpreter, context, event, action_def):
        print("Showing loading spinner...")

    def setError(self, interpreter, context, event, action_def):
        error_msg = event.payload.get("message", "Unknown error")
        context["errors"].append(error_msg)
        print(f"Error: {error_msg}")

machine = create_machine(config, logic=FormLogic())
interp = SyncInterpreter(machine).start()
# Output: Loading saved draft...

interp.send("SUBMIT")
# Output (in order):
#   Auto-saving draft: 'Loaded from storage'   (exit: saveDraft)
#   Validating... valid=True                     (transition: validate)
#   Errors cleared.                              (transition: clearErrors)
#   Showing loading spinner...                   (entry: showSpinner)

interp.send("SUCCESS")
interp.stop()
```

## Pythonic Actions

### `@action` Decorator

The `@action` decorator marks a function as a state machine action:

```python
from xstate_statemachine import action

@action
def increment_counter(interpreter, context, event, action_def):
    context["count"] += 1
# Registered as "incrementCounter" (auto snake_case → camelCase)
```

### Explicit Naming

Override the auto-generated name:

```python
@action("myCustomAction")
def some_function(interpreter, context, event, action_def):
    print("Custom action executed")
# Registered as "myCustomAction"
```

### `@state.enter` — Entry Actions (Class-Based)

Register entry actions using the `@state.enter` decorator:

```python
from xstate_statemachine import State, StateMachine, SyncInterpreter

class FormMachine(StateMachine):
    machine_id = "form"

    editing    = State("editing", initial=True)
    submitting = State("submitting")

    submit = editing.to(submitting, event="SUBMIT")

    @editing.enter
    def on_enter_editing(self, interpreter, context, event, action_def):
        print("Entered editing mode")

    @submitting.enter
    def on_enter_submitting(self, interpreter, context, event, action_def):
        print("Entered submitting mode")

machine = FormMachine.create_machine()
interp = SyncInterpreter(machine).start()
# Output: Entered editing mode

interp.send("SUBMIT")
# Output: Entered submitting mode
interp.stop()
```

### `@state.exit` — Exit Actions (Class-Based)

Register exit actions using the `@state.exit` decorator:

```python
class FormMachine(StateMachine):
    machine_id = "form"

    editing    = State("editing", initial=True)
    submitting = State("submitting")

    submit = editing.to(submitting, event="SUBMIT")

    @editing.exit
    def on_exit_editing(self, interpreter, context, event, action_def):
        print("Left editing mode — auto-saving draft...")

    @editing.enter
    def on_enter_editing(self, interpreter, context, event, action_def):
        print("Entered editing mode")
```

### Transition Actions in `.to()`

Attach actions directly to transitions using the `actions` parameter:

```python
class FormMachine(StateMachine):
    machine_id = "form"

    editing    = State("editing", initial=True)
    submitting = State("submitting")

    submit = editing.to(
        submitting,
        event="SUBMIT",
        actions=["validate", "clearErrors"]
    )
```

## Modifying Context in Actions

Actions are the designated place to mutate context. Modify the dictionary directly:

```python
from xstate_statemachine import create_machine, SyncInterpreter, MachineLogic

config = {
    "id": "todoApp",
    "initial": "active",
    "context": {"todos": [], "completedCount": 0},
    "states": {
        "active": {
            "on": {
                "ADD_TODO":      {"actions": "addTodo"},
                "COMPLETE_TODO": {"actions": "completeTodo"}
            }
        }
    }
}

class TodoLogic(MachineLogic):
    def addTodo(self, interpreter, context, event, action_def):
        title = event.payload.get("title", "Untitled")
        context["todos"].append({"title": title, "done": False})

    def completeTodo(self, interpreter, context, event, action_def):
        index = event.payload.get("index", 0)
        if 0 <= index < len(context["todos"]):
            context["todos"][index]["done"] = True
            context["completedCount"] += 1

machine = create_machine(config, logic=TodoLogic())
interp = SyncInterpreter(machine).start()

interp.send("ADD_TODO", title="Buy milk")
interp.send("ADD_TODO", title="Write docs")
interp.send("COMPLETE_TODO", index=0)

print(interp.context["todos"])
# [{"title": "Buy milk", "done": True}, {"title": "Write docs", "done": False}]
print(interp.context["completedCount"])  # 1
interp.stop()
```

## Accessing Event Data in Actions

The `event` parameter carries the payload that was sent with the event:

```python
class Logic(MachineLogic):
    def storeUser(self, interpreter, context, event, action_def):
        # Access payload sent via: interp.send("LOGIN", username="alice", role="admin")
        context["username"] = event.payload.get("username", "unknown")
        context["role"] = event.payload.get("role", "guest")
```

For `DoneEvent` from services, the result is on `event.data`:

```python
class Logic(MachineLogic):
    def saveResult(self, interpreter, context, event, action_def):
        # event.data holds the service's return value
        context["result"] = event.data
```

## Multiple Actions on One Transition

When multiple actions are defined on a single transition, they execute **in order**, left-to-right:

```json
"SUBMIT": {
  "target": "submitted",
  "actions": ["validate", "sanitize", "log", "submit"]
}
```

```python
class Logic(MachineLogic):
    def validate(self, interpreter, context, event, action_def):
        print("1. Validating...")

    def sanitize(self, interpreter, context, event, action_def):
        print("2. Sanitizing...")

    def log(self, interpreter, context, event, action_def):
        print("3. Logging...")

    def submit(self, interpreter, context, event, action_def):
        print("4. Submitting...")

# Output when SUBMIT fires:
# 1. Validating...
# 2. Sanitizing...
# 3. Logging...
# 4. Submitting...
```

## Action Definition (`action_def` Parameter)

The `action_def` parameter is an `ActionDefinition` object that carries metadata about the action:

| Attribute | Type | Description |
|-----------|------|-------------|
| `action_def.type` | `str` | The action's registered name (e.g., `"addOne"`) |
| `action_def.params` | `dict` or `None` | Static parameters from the JSON config |

### Using `action_def.params`

You can define static parameters in the JSON config:

```json
{
  "actions": {
    "type": "showNotification",
    "params": {
      "message": "Form submitted successfully!",
      "level": "success"
    }
  }
}
```

```python
class Logic(MachineLogic):
    def showNotification(self, interpreter, context, event, action_def):
        msg = action_def.params.get("message", "")
        level = action_def.params.get("level", "info")
        print(f"[{level.upper()}] {msg}")
```

## Error Handling in Actions

Actions can raise exceptions. Use `try/except` to handle errors gracefully without crashing the interpreter:

```python
class Logic(MachineLogic):
    def saveToDatabase(self, interpreter, context, event, action_def):
        try:
            # Simulate database save
            data = context.get("formData", {})
            if not data:
                raise ValueError("No form data to save")
            # ... perform save ...
            context["saveStatus"] = "success"
            print("Data saved successfully")
        except Exception as e:
            context["saveStatus"] = "error"
            context["lastError"] = str(e)
            print(f"Save failed: {e}")
```

> **Warning:** Unhandled exceptions in actions will propagate up to the `send()` call. In production, always wrap risky operations in `try/except` and store error information in context for the machine to react to.

## Best Practices

### Keep Actions Simple

Each action should do one thing. If an action is getting complex, split it into multiple smaller actions:

```python
# Instead of one monolithic action:
# def processOrder(self, interpreter, context, event, action_def):
#     validate + calculate + save + notify + log

# Split into focused actions:
"actions": ["validateOrder", "calculateTotal", "saveOrder", "notifyUser", "logOrder"]
```

### Use Context for Data Flow

Pass data between actions through context, not through side channels:

```python
class Logic(MachineLogic):
    def validateForm(self, interpreter, context, event, action_def):
        # Store validation result in context
        context["validationResult"] = {
            "isValid": True,
            "errors": []
        }

    def submitForm(self, interpreter, context, event, action_def):
        # Read from context — don't recompute
        if context["validationResult"]["isValid"]:
            print("Submitting valid form...")
```

### Log Important Actions

Use the interpreter ID for traceable logs in multi-machine systems:

```python
import logging

class Logic(MachineLogic):
    def processPayment(self, interpreter, context, event, action_def):
        logging.info(
            "[%s] Processing payment of $%.2f",
            interpreter.id,
            event.payload.get("amount", 0)
        )
```

## Complete Example: Form Machine with Full Action Lifecycle

A comprehensive form machine demonstrating entry, exit, and transition actions working together:

```python
from xstate_statemachine import create_machine, SyncInterpreter, MachineLogic

config = {
    "id": "contactForm",
    "initial": "editing",
    "context": {
        "formData": {"name": "", "email": "", "message": ""},
        "errors": [],
        "draft": None,
        "submissionId": None,
        "isLoading": False
    },
    "states": {
        "editing": {
            "entry": ["loadDraft", "clearErrors"],
            "exit": "saveDraft",
            "on": {
                "UPDATE_FIELD": {"actions": "updateField"},
                "SUBMIT": [
                    {"target": "validating", "guard": "hasRequiredFields"},
                    {"target": "editing", "actions": "showFieldErrors"}
                ]
            }
        },
        "validating": {
            "entry": "validateAll",
            "on": {
                "VALIDATION_PASS": {"target": "submitting"},
                "VALIDATION_FAIL": {"target": "editing", "actions": "setErrors"}
            }
        },
        "submitting": {
            "entry": "showSpinner",
            "exit": "hideSpinner",
            "on": {
                "SUCCESS": {
                    "target": "success",
                    "actions": ["storeSubmissionId", "clearDraft"]
                },
                "FAILURE": {
                    "target": "editing",
                    "actions": "setErrors"
                }
            }
        },
        "success": {
            "entry": "showConfirmation",
            "type": "final"
        }
    }
}

class ContactFormLogic(MachineLogic):
    # ---- Entry Actions ----
    def loadDraft(self, interpreter, context, event, action_def):
        if context["draft"]:
            context["formData"] = dict(context["draft"])
            print("Draft restored from auto-save.")
        else:
            print("Starting with empty form.")

    def showSpinner(self, interpreter, context, event, action_def):
        context["isLoading"] = True
        print("Loading...")

    def showConfirmation(self, interpreter, context, event, action_def):
        sid = context["submissionId"]
        print(f"Thank you! Your submission ID is: {sid}")

    def validateAll(self, interpreter, context, event, action_def):
        errors = []
        fd = context["formData"]
        if not fd.get("name"):
            errors.append("Name is required")
        if "@" not in fd.get("email", ""):
            errors.append("Valid email is required")
        if not fd.get("message"):
            errors.append("Message is required")

        if errors:
            context["errors"] = errors
            interpreter.send("VALIDATION_FAIL")
        else:
            interpreter.send("VALIDATION_PASS")

    # ---- Exit Actions ----
    def saveDraft(self, interpreter, context, event, action_def):
        context["draft"] = dict(context["formData"])
        print("Draft auto-saved.")

    def hideSpinner(self, interpreter, context, event, action_def):
        context["isLoading"] = False

    # ---- Transition Actions ----
    def updateField(self, interpreter, context, event, action_def):
        field = event.payload.get("field")
        value = event.payload.get("value", "")
        if field and field in context["formData"]:
            context["formData"][field] = value

    def clearErrors(self, interpreter, context, event, action_def):
        context["errors"] = []

    def setErrors(self, interpreter, context, event, action_def):
        if event.payload.get("errors"):
            context["errors"] = event.payload["errors"]

    def showFieldErrors(self, interpreter, context, event, action_def):
        context["errors"] = ["Please fill in all required fields"]
        print(f"Errors: {context['errors']}")

    def storeSubmissionId(self, interpreter, context, event, action_def):
        context["submissionId"] = event.payload.get("id", "UNKNOWN")

    def clearDraft(self, interpreter, context, event, action_def):
        context["draft"] = None

    # ---- Guards ----
    def hasRequiredFields(self, context, event):
        fd = context["formData"]
        return bool(fd.get("name") and fd.get("email") and fd.get("message"))

# Run the form machine
machine = create_machine(config, logic=ContactFormLogic())
interp = SyncInterpreter(machine).start()
# Output: Starting with empty form.

# Fill in the form
interp.send("UPDATE_FIELD", field="name", value="Alice")
interp.send("UPDATE_FIELD", field="email", value="alice@example.com")
interp.send("UPDATE_FIELD", field="message", value="Hello!")

# Submit the form
interp.send("SUBMIT")
# Output: Draft auto-saved.  (exit action on editing)
# The machine transitions: editing → validating → submitting

# Simulate server response
interp.send("SUCCESS", id="FORM-12345")
# Output: Thank you! Your submission ID is: FORM-12345

print(interp.context["submissionId"])  # FORM-12345
interp.stop()
```

## Auto-Discovery with LogicLoader

The `LogicLoader` is a singleton that automatically discovers actions, guards, and services from Python modules or class instances. It maps `snake_case` Python function names to `camelCase` JSON names.

### Module-Based Discovery

```python
# my_logic.py — separate file with all your logic
from xstate_statemachine import MachineLogic

def validate_input(interpreter, context, event, action_def):
    """Auto-maps to 'validateInput' in JSON config."""
    data = event.data if hasattr(event, 'data') else {}
    context["is_valid"] = bool(data.get("name"))

def is_valid(context, event):
    """Auto-maps to 'isValid' guard in JSON config."""
    return context.get("is_valid", False)

def fetch_data(interpreter, context, event):
    """Auto-maps to 'fetchData' service in JSON config."""
    return {"items": [1, 2, 3]}
```

```python
# main.py — use the module for auto-discovery
import my_logic
from xstate_statemachine import create_machine, SyncInterpreter

config = {
    "id": "autoDiscover",
    "initial": "input",
    "context": {"is_valid": False},
    "states": {
        "input": {
            "on": {
                "SUBMIT": {
                    "target": "validating",
                    "actions": "validateInput"
                }
            }
        },
        "validating": {
            "always": [
                {"target": "fetching", "guard": "isValid"},
                {"target": "input"}
            ]
        },
        "fetching": {
            "invoke": {
                "src": "fetchData",
                "onDone": "done"
            }
        },
        "done": {"type": "final"}
    }
}

# Pass the module — LogicLoader discovers all matching functions
machine = create_machine(config, logic_modules=[my_logic])
interp = SyncInterpreter(machine).start()

interp.send("SUBMIT", name="Alice")
print(interp.active_state_ids)
# {'autoDiscover.done'}

interp.stop()
```

### Class-Based Discovery (logic_providers)

```python
from xstate_statemachine import create_machine, SyncInterpreter

class OrderLogic:
    """Class with methods that auto-map to JSON names."""

    def calculate_total(self, interpreter, context, event, action_def):
        """Maps to 'calculateTotal' in JSON."""
        items = context.get("items", [])
        context["total"] = sum(item["price"] for item in items)

    def has_items(self, context, event):
        """Maps to 'hasItems' guard in JSON."""
        return len(context.get("items", [])) > 0

config = {
    "id": "order",
    "initial": "cart",
    "context": {"items": [{"name": "Widget", "price": 9.99}], "total": 0},
    "states": {
        "cart": {
            "on": {
                "CHECKOUT": {
                    "target": "checkout",
                    "guard": "hasItems",
                    "actions": "calculateTotal"
                }
            }
        },
        "checkout": {"type": "final"}
    }
}

# Pass instances — LogicLoader discovers methods by snake_case matching
machine = create_machine(config, logic_providers=[OrderLogic()])
interp = SyncInterpreter(machine).start()

interp.send("CHECKOUT")
print(interp.context["total"])
# 9.99

interp.stop()
```

### Global Registration

For large applications, register modules globally so all machines can discover them:

```python
from xstate_statemachine import LogicLoader

import my_actions
import my_guards
import my_services

# Register once at startup
loader = LogicLoader.get_instance()
loader.register_logic_module(my_actions)
loader.register_logic_module(my_guards)
loader.register_logic_module(my_services)

# All subsequent create_machine() calls can find these functions
# without passing logic_modules every time
```

> **Naming Convention:** The auto-discovery maps Python `snake_case` to JSON `camelCase`:
> - `validate_input` → `validateInput`
> - `is_admin` → `isAdmin`
> - `fetch_user_data` → `fetchUserData`

## See Also

- **[Guards](../guards/)** — conditional transitions that decide whether actions fire
- **[Context](../context/)** — the data that actions typically mutate
- **[Services & Invoke](../services/)** — actions triggered by `onDone` / `onError` service callbacks
- **[Pythonic API](../pythonic-api/)** — `@action` decorator and `State.enter()`/`State.exit()` decorators
- **[Core Concepts](../core-concepts/)** — action execution order (entry → transition → exit)
- **[Interpreters](../interpreters/)** — how actions interact with sync vs async interpreters
