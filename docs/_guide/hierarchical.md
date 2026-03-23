---
title: "Hierarchical States"
description: "Nested compound states — organize complex flows without spaghetti."
---

Hierarchical (compound) states let you **nest states inside other states**, creating a tree structure. Instead of a flat explosion of states with duplicated transitions, you organize related states under a parent — and the parent's transitions automatically apply to **all** its children.

## What Are Hierarchical States?

A **compound state** is a state that contains its own child states. When the machine is "in" the parent state, it is always in exactly one of its children. The parent can define transitions that catch events from _any_ child, eliminating repetitive transition definitions.

Think of it like folders in a file system: a file is always inside a folder, and operations on the folder affect everything inside it.

```
┌──────────────────── loggedIn ────────────────────┐
│                                                   │
│   ┌───────────┐   VIEW_PROFILE   ┌────────────┐  │
│   │ dashboard │ ──────────────► │   profile   │  │
│   │  (init)   │ ◄────────────── │            │  │
│   └───────────┘      BACK       └────────────┘  │
│        │                                          │
│   VIEW_SETTINGS                                   │
│        ▼                                          │
│   ┌──────────┐                                    │
│   │ settings │                                    │
│   └──────────┘                                    │
│                                                   │
└────────── LOGOUT ─────────────────────────────────┘
                │
                ▼
┌──────────────────┐
│    loggedOut      │
└──────────────────┘
```

The `LOGOUT` event on the parent `loggedIn` catches the event **no matter which child** is active — `dashboard`, `profile`, or `settings`. This is the power of hierarchy.

## JSON Example: Authentication Flow

```json
{
  "id": "auth",
  "initial": "loggedOut",
  "states": {
    "loggedOut": {
      "on": {
        "LOGIN": "loggedIn"
      }
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
          "on": {
            "BACK": "dashboard"
          }
        },
        "settings": {
          "on": {
            "BACK": "dashboard"
          }
        }
      },
      "on": {
        "LOGOUT": "loggedOut"
      }
    }
  }
}
```

```python
from xstate_statemachine import create_machine, SyncInterpreter

config = {
    "id": "auth",
    "initial": "loggedOut",
    "states": {
        "loggedOut": {"on": {"LOGIN": "loggedIn"}},
        "loggedIn": {
            "initial": "dashboard",
            "states": {
                "dashboard": {
                    "on": {
                        "VIEW_PROFILE": "profile",
                        "VIEW_SETTINGS": "settings"
                    }
                },
                "profile": {"on": {"BACK": "dashboard"}},
                "settings": {"on": {"BACK": "dashboard"}}
            },
            "on": {"LOGOUT": "loggedOut"}
        }
    }
}

machine = create_machine(config)
interp = SyncInterpreter(machine).start()

print(interp.active_state_ids)
# {'auth.loggedOut'}

interp.send("LOGIN")
print(interp.active_state_ids)
# {'auth.loggedIn.dashboard'}  — entered loggedIn, then its initial child

interp.send("VIEW_PROFILE")
print(interp.active_state_ids)
# {'auth.loggedIn.profile'}

# LOGOUT works from ANY child state
interp.send("LOGOUT")
print(interp.active_state_ids)
# {'auth.loggedOut'}

interp.stop()
```

**Key behavior:** The `LOGOUT` event is defined on the parent `loggedIn` — it fires regardless of whether the user is on `dashboard`, `profile`, or `settings`. Without hierarchy, you'd need a `LOGOUT` transition on every single child state.

## Initial Child State

Every compound state **must** specify which child to enter first using the `initial` field:

```json
{
  "loggedIn": {
    "initial": "dashboard",
    "states": {
      "dashboard": {},
      "profile": {},
      "settings": {}
    }
  }
}
```

When the machine transitions to `loggedIn`, it automatically enters `dashboard` (the initial child). The machine is never "just" in `loggedIn` — it's always in `loggedIn.dashboard`, `loggedIn.profile`, or `loggedIn.settings`.

> **Warning:** Forgetting `initial` on a compound state will raise an `InvalidConfigError`.

## Nested Transitions

### Child-to-Child Transitions

Children can transition between each other freely:

```json
{
  "loggedIn": {
    "initial": "dashboard",
    "states": {
      "dashboard": {
        "on": {"VIEW_PROFILE": "profile"}
      },
      "profile": {
        "on": {"BACK": "dashboard"}
      }
    }
  }
}
```

### Parent-Level Transitions (Catch-All)

Transitions defined on the parent apply to **all** children. If a child doesn't handle an event, it bubbles up to the parent:

```json
{
  "loggedIn": {
    "initial": "dashboard",
    "states": {
      "dashboard": {
        "on": {"REFRESH": {"actions": "loadDashboard"}}
      },
      "profile": {},
      "settings": {}
    },
    "on": {
      "LOGOUT": "loggedOut",
      "SHOW_HELP": {"actions": "openHelpPanel"}
    }
  }
}
```

- `REFRESH` is only handled in `dashboard` — it won't fire from `profile` or `settings`
- `LOGOUT` and `SHOW_HELP` work from **any** child state, because they're on the parent

### Event Bubbling

When an event arrives, the machine checks the **current leaf state** first. If it doesn't handle the event, the event **bubbles up** to the parent, then the grandparent, and so on — just like DOM events in a browser.

```python
# Machine is in auth.loggedIn.profile
interp.send("SHOW_HELP")
# 1. profile doesn't handle SHOW_HELP → bubble up
# 2. loggedIn handles SHOW_HELP → fires openHelpPanel action
```

### Targeting Specific Child States

From outside the hierarchy, you can target a specific child directly by name:

```json
{
  "loggedOut": {
    "on": {
      "LOGIN": "loggedIn",
      "LOGIN_TO_SETTINGS": "settings"
    }
  }
}
```

> **Note:** When targeting a child state directly, the machine still enters the parent first (firing its entry actions), then enters the specified child.

## Deep Nesting (3+ Levels)

Hierarchical states can be nested to any depth:

```json
{
  "id": "deepNest",
  "initial": "app",
  "states": {
    "app": {
      "initial": "main",
      "states": {
        "main": {
          "initial": "home",
          "states": {
            "home": {
              "on": {"VIEW_DETAIL": "detail"}
            },
            "detail": {
              "on": {"BACK": "home"}
            }
          }
        }
      },
      "on": {
        "CRASH": "error"
      }
    },
    "error": {
      "on": {"RESTART": "app"}
    }
  }
}
```

```python
from xstate_statemachine import create_machine, SyncInterpreter

config = {
    "id": "deepNest",
    "initial": "app",
    "states": {
        "app": {
            "initial": "main",
            "states": {
                "main": {
                    "initial": "home",
                    "states": {
                        "home": {"on": {"VIEW_DETAIL": "detail"}},
                        "detail": {"on": {"BACK": "home"}}
                    }
                }
            },
            "on": {"CRASH": "error"}
        },
        "error": {"on": {"RESTART": "app"}}
    }
}

machine = create_machine(config)
interp = SyncInterpreter(machine).start()

print(interp.active_state_ids)
# {'deepNest.app.main.home'}  — drills down through all initial states

interp.send("VIEW_DETAIL")
print(interp.active_state_ids)
# {'deepNest.app.main.detail'}

# CRASH bubbles up from detail → main → app (which handles it)
interp.send("CRASH")
print(interp.active_state_ids)
# {'deepNest.error'}

interp.stop()
```

> **Tip:** Keep nesting to 2-3 levels. Deeper than that usually means your machine should be split into separate machines using services/actors.

## State ID Format

Every state gets a fully qualified ID: `"machineId.parent.child.grandchild"`. This dot-separated path uniquely identifies each state in the tree:

| State | Fully Qualified ID |
|-------|-------------------|
| loggedOut | `auth.loggedOut` |
| dashboard | `auth.loggedIn.dashboard` |
| profile | `auth.loggedIn.profile` |
| settings | `auth.loggedIn.settings` |

```python
interp.send("LOGIN")
print(interp.active_state_ids)
# {'auth.loggedIn.dashboard'}

# Check if we're logged in (regardless of which child)
is_logged_in = any(
    sid.startswith("auth.loggedIn")
    for sid in interp.active_state_ids
)
print(is_logged_in)  # True
```

## Pythonic Hierarchical States

### Using `State` with `states=[]`

```python
from xstate_statemachine import State, StateMachine, SyncInterpreter

class AuthMachine(StateMachine):
    machine_id = "auth"

    logged_out = State("loggedOut", initial=True)
    logged_in  = State("loggedIn", states=[
        State("dashboard", initial=True,
              on={"VIEW_PROFILE": "profile", "VIEW_SETTINGS": "settings"}),
        State("profile",  on={"BACK": "dashboard"}),
        State("settings", on={"BACK": "dashboard"}),
    ])

    login  = logged_out.to(logged_in,  event="LOGIN")
    logout = logged_in.to(logged_out, event="LOGOUT")

machine = AuthMachine.create_machine()
interp = SyncInterpreter(machine).start()

interp.send("LOGIN")
print(interp.active_state_ids)
# {'auth.loggedIn.dashboard'}

interp.send("VIEW_SETTINGS")
print(interp.active_state_ids)
# {'auth.loggedIn.settings'}

interp.send("LOGOUT")
print(interp.active_state_ids)
# {'auth.loggedOut'}

interp.stop()
```

### Using `MachineBuilder.child_states()`

```python
from xstate_statemachine import MachineBuilder, SyncInterpreter

machine = (
    MachineBuilder("auth")
    .state("loggedOut", initial=True)
    .state("loggedIn")
    .child_states("loggedIn", initial="dashboard", states={
        "dashboard": {
            "on": {
                "VIEW_PROFILE": "profile",
                "VIEW_SETTINGS": "settings"
            }
        },
        "profile": {"on": {"BACK": "dashboard"}},
        "settings": {"on": {"BACK": "dashboard"}},
    })
    .transition("loggedOut", "LOGIN", "loggedIn")
    .transition("loggedIn", "LOGOUT", "loggedOut")
    .build()
)

interp = SyncInterpreter(machine).start()

interp.send("LOGIN")
print(interp.active_state_ids)
# {'auth.loggedIn.dashboard'}

interp.stop()
```

### Using Functional API

```python
from xstate_statemachine import State, build_machine, SyncInterpreter

logged_out = State("loggedOut", initial=True, on={"LOGIN": "loggedIn"})
logged_in  = State("loggedIn", states=[
    State("dashboard", initial=True,
          on={"VIEW_PROFILE": "profile", "VIEW_SETTINGS": "settings"}),
    State("profile",  on={"BACK": "dashboard"}),
    State("settings", on={"BACK": "dashboard"}),
], on={"LOGOUT": "loggedOut"})

machine = build_machine(id="auth", states=[logged_out, logged_in])
interp = SyncInterpreter(machine).start()

interp.send("LOGIN")
interp.send("VIEW_PROFILE")
print(interp.active_state_ids)
# {'auth.loggedIn.profile'}

interp.stop()
```

## onDone for Compound States

When a compound state's child reaches a **final** state, a `done.state.*` event fires on the parent. Use `onDone` to react:

```json
{
  "id": "workflow",
  "initial": "processing",
  "states": {
    "processing": {
      "initial": "step1",
      "states": {
        "step1": {
          "on": {"NEXT": "step2"}
        },
        "step2": {
          "on": {"NEXT": "complete"}
        },
        "complete": {
          "type": "final"
        }
      },
      "onDone": "finished"
    },
    "finished": {
      "type": "final"
    }
  }
}
```

```python
from xstate_statemachine import create_machine, SyncInterpreter

config = {
    "id": "workflow",
    "initial": "processing",
    "states": {
        "processing": {
            "initial": "step1",
            "states": {
                "step1": {"on": {"NEXT": "step2"}},
                "step2": {"on": {"NEXT": "complete"}},
                "complete": {"type": "final"}
            },
            "onDone": "finished"
        },
        "finished": {"type": "final"}
    }
}

machine = create_machine(config)
interp = SyncInterpreter(machine).start()

print(interp.active_state_ids)
# {'workflow.processing.step1'}

interp.send("NEXT")  # step1 → step2
interp.send("NEXT")  # step2 → complete (final) → triggers onDone → finished

print(interp.active_state_ids)
# {'workflow.finished'}

interp.stop()
```

## Mixing Hierarchy with Guards

Guards work normally inside nested states:

```json
{
  "checkout": {
    "initial": "cart",
    "states": {
      "cart": {
        "on": {
          "PROCEED": [
            {"target": "payment", "guard": "cartNotEmpty"},
            {"target": "cart",    "actions": "showEmptyError"}
          ]
        }
      },
      "payment": {}
    }
  }
}
```

```python
from xstate_statemachine import create_machine, SyncInterpreter, MachineLogic

config = {
    "id": "shop",
    "initial": "checkout",
    "states": {
        "checkout": {
            "initial": "cart",
            "states": {
                "cart": {
                    "on": {
                        "PROCEED": [
                            {"target": "payment", "guard": "cartNotEmpty"},
                            {"target": "cart", "actions": "showEmptyError"}
                        ]
                    }
                },
                "payment": {
                    "on": {"PAY": "confirmation"}
                },
                "confirmation": {"type": "final"}
            },
            "on": {"CANCEL": "cancelled"}
        },
        "cancelled": {}
    }
}

class ShopLogic(MachineLogic):
    def cartNotEmpty(self, context, event):
        return len(context.get("items", [])) > 0

    def showEmptyError(self, interpreter, context, event, action_def):
        print("Cart is empty!")

machine = create_machine(config, logic=ShopLogic())
interp = SyncInterpreter(machine, context={"items": []}).start()

interp.send("PROCEED")
print(interp.active_state_ids)
# {'shop.checkout.cart'}  — guard blocked, showed error

interp.stop()
```

## Mixing Hierarchy with Actions

Entry and exit actions fire in the correct order when entering/exiting nested states:

```json
{
  "loggedIn": {
    "entry": "loadUserSession",
    "exit":  "cleanupSession",
    "initial": "dashboard",
    "states": {
      "dashboard": {
        "entry": "loadDashboardData",
        "exit":  "clearDashboardCache"
      },
      "profile": {
        "entry": "loadProfileData"
      }
    }
  }
}
```

When transitioning from `loggedOut` to `loggedIn`:

1. `loadUserSession` (entry on `loggedIn`)
2. `loadDashboardData` (entry on `dashboard`, the initial child)

When transitioning from `dashboard` to `profile`:

1. `clearDashboardCache` (exit on `dashboard`)
2. `loadProfileData` (entry on `profile`)

When transitioning via `LOGOUT`:

1. Exit current child (e.g., `profile`)
2. `cleanupSession` (exit on `loggedIn`)

## Mixing Hierarchy with Services

Services (invoked operations) work inside nested states:

```json
{
  "loggedIn": {
    "initial": "loading",
    "states": {
      "loading": {
        "invoke": {
          "src": "fetchUserData",
          "onDone": {
            "target": "dashboard",
            "actions": "storeUserData"
          },
          "onError": "error"
        }
      },
      "dashboard": {},
      "error": {
        "on": {"RETRY": "loading"}
      }
    }
  }
}
```

The service `fetchUserData` is invoked when `loading` is entered. On success, the machine moves to `dashboard` (within `loggedIn`). On failure, it moves to `error` (also within `loggedIn`).

## Complete Example: E-Commerce Checkout Flow

```python
from xstate_statemachine import create_machine, SyncInterpreter, MachineLogic

config = {
    "id": "checkout",
    "initial": "cart",
    "context": {
        "items": [],
        "shippingAddress": None,
        "paymentMethod": None,
        "orderId": None
    },
    "states": {
        "cart": {
            "on": {
                "ADD_ITEM": {"actions": "addItem"},
                "REMOVE_ITEM": {"actions": "removeItem"},
                "CHECKOUT": {
                    "target": "shipping",
                    "guard": "cartNotEmpty"
                }
            }
        },
        "shipping": {
            "initial": "entering",
            "states": {
                "entering": {
                    "on": {
                        "SET_ADDRESS": {
                            "target": "validating",
                            "actions": "setAddress"
                        }
                    }
                },
                "validating": {
                    "invoke": {
                        "src": "validateAddress",
                        "onDone": "confirmed",
                        "onError": {
                            "target": "entering",
                            "actions": "showAddressError"
                        }
                    }
                },
                "confirmed": {
                    "type": "final"
                }
            },
            "onDone": "payment",
            "on": {"BACK": "cart"}
        },
        "payment": {
            "initial": "selecting",
            "states": {
                "selecting": {
                    "on": {
                        "SET_PAYMENT": {
                            "target": "ready",
                            "actions": "setPayment"
                        }
                    }
                },
                "ready": {
                    "type": "final"
                }
            },
            "onDone": "processing",
            "on": {"BACK": "shipping"}
        },
        "processing": {
            "invoke": {
                "src": "submitOrder",
                "onDone": {
                    "target": "confirmation",
                    "actions": "storeOrderId"
                },
                "onError": {
                    "target": "payment",
                    "actions": "showPaymentError"
                }
            }
        },
        "confirmation": {
            "type": "final"
        }
    }
}

class CheckoutLogic(MachineLogic):
    def addItem(self, interpreter, context, event, action_def):
        context["items"].append(event.data.get("item", "unknown"))

    def removeItem(self, interpreter, context, event, action_def):
        item = event.data.get("item")
        if item in context["items"]:
            context["items"].remove(item)

    def cartNotEmpty(self, context, event):
        return len(context["items"]) > 0

    def setAddress(self, interpreter, context, event, action_def):
        context["shippingAddress"] = event.data.get("address")

    def validateAddress(self, interpreter, context, event):
        return {"valid": True}

    def showAddressError(self, interpreter, context, event, action_def):
        print("Invalid shipping address")

    def setPayment(self, interpreter, context, event, action_def):
        context["paymentMethod"] = event.data.get("method")

    def submitOrder(self, interpreter, context, event):
        return {"orderId": "ORD-12345"}

    def storeOrderId(self, interpreter, context, event, action_def):
        context["orderId"] = event.data.get("orderId")

    def showPaymentError(self, interpreter, context, event, action_def):
        print("Payment failed, please try again")

machine = create_machine(config, logic=CheckoutLogic())
interp = SyncInterpreter(machine).start()

# Add items to cart
interp.send({"type": "ADD_ITEM", "item": "Widget"})
interp.send({"type": "ADD_ITEM", "item": "Gadget"})
print(interp.context["items"])
# ['Widget', 'Gadget']

# Start checkout
interp.send("CHECKOUT")
print(interp.active_state_ids)
# {'checkout.shipping.entering'}

# Set shipping address
interp.send({"type": "SET_ADDRESS", "address": "123 Main St"})
# validateAddress runs → succeeds → confirmed (final) → onDone → payment
print(interp.active_state_ids)
# {'checkout.payment.selecting'}

# Set payment
interp.send({"type": "SET_PAYMENT", "method": "credit_card"})
# ready (final) → onDone → processing → submitOrder → confirmation
print(interp.active_state_ids)
# {'checkout.confirmation'}

print(interp.context["orderId"])
# ORD-12345

interp.stop()
```

## Complete Example: Multi-Step Form Wizard

```python
from xstate_statemachine import State, StateMachine, SyncInterpreter, action, guard

class FormWizard(StateMachine):
    machine_id = "wizard"
    initial_context = {
        "personal": {},
        "address": {},
        "preferences": {},
        "currentStep": 1
    }

    # Top-level states
    filling = State("filling", initial=True, states=[
        State("personal", initial=True, on={
            "NEXT": {"target": "address", "guard": "personalComplete"}
        }),
        State("address", on={
            "PREV": "personal",
            "NEXT": {"target": "preferences", "guard": "addressComplete"}
        }),
        State("preferences", on={
            "PREV": "address",
            "NEXT": "done"
        }),
        State("done", final=True),
    ], on={
        "UPDATE": {"actions": "updateField"}
    }, on_done="reviewing")

    reviewing = State("reviewing", on={
        "EDIT": "filling",
        "SUBMIT": "submitting"
    })

    submitting = State("submitting", invoke={
        "src": "submitForm",
        "onDone": "success",
        "onError": {"target": "reviewing", "actions": "showError"}
    })

    success = State("success", final=True)

    # Guards
    @guard
    def personal_complete(self, context, event):
        p = context.get("personal", {})
        return bool(p.get("name") and p.get("email"))

    @guard
    def address_complete(self, context, event):
        a = context.get("address", {})
        return bool(a.get("street") and a.get("city"))

    # Actions
    @action
    def update_field(self, interpreter, context, event, action_def):
        section = event.data.get("section", "personal")
        field = event.data.get("field")
        value = event.data.get("value")
        if section in context and field:
            context[section][field] = value

machine = FormWizard.create_machine()
interp = SyncInterpreter(machine).start()

print(interp.active_state_ids)
# {'wizard.filling.personal'}

# Fill personal info
interp.send({"type": "UPDATE", "section": "personal",
             "field": "name", "value": "Alice"})
interp.send({"type": "UPDATE", "section": "personal",
             "field": "email", "value": "alice@example.com"})

# Advance to address
interp.send("NEXT")
print(interp.active_state_ids)
# {'wizard.filling.address'}

# Go back
interp.send("PREV")
print(interp.active_state_ids)
# {'wizard.filling.personal'}

interp.stop()
```
