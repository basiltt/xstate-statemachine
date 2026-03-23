---
title: "Services & Invoke"
description: "Async operations — API calls, database queries, and external integrations."
---

Services represent **external operations** — API calls, database queries, file reads, computations — that a state invokes when it is entered. When the service completes, the machine automatically transitions via `onDone`; if it fails, the machine transitions via `onError`.

## What are Services?

A service is a callable that runs when a state is entered and produces a result (or an error). Services bridge the gap between your state machine's declarative flow and the imperative world of I/O operations.

Key characteristics:

- **Invoked by states** — services are tied to a state's `invoke` property, not to transitions.
- **Result-driven** — the return value becomes `event.data` in the `onDone` handler.
- **Error-aware** — exceptions are caught and routed to `onError` handlers.
- **Sync or async** — `SyncInterpreter` requires sync services; `Interpreter` supports async.

## JSON Invoke Structure

The `invoke` property on a state defines which service to call and how to handle the result:

```json
{
  "invoke": {
    "src": "fetchUser",
    "id": "userFetcher",
    "onDone": {
      "target": "loaded",
      "actions": "storeUser"
    },
    "onError": {
      "target": "error",
      "actions": "storeError"
    }
  }
}
```

| Key | Type | Description |
|-----|------|-------------|
| `src` | `string` | The service name (must match a registered service function) |
| `id` | `string` | Optional unique identifier (defaults to the state's ID) |
| `onDone` | `object` | Transition to take on successful completion |
| `onError` | `object` | Transition to take on failure (exception) |

## Basic Invoke Example

A complete example of a user-loading machine:

```python
from xstate_statemachine import create_machine, SyncInterpreter, MachineLogic

config = {
    "id": "userLoader",
    "initial": "idle",
    "context": {"user": None, "error": None},
    "states": {
        "idle": {
            "on": {"LOAD": "loading"}
        },
        "loading": {
            "invoke": {
                "src": "fetchUser",
                "onDone": {
                    "target": "loaded",
                    "actions": "storeUser"
                },
                "onError": {
                    "target": "error",
                    "actions": "storeError"
                }
            }
        },
        "loaded": {"type": "final"},
        "error":  {"on": {"RETRY": "loading"}}
    }
}

class UserLogic(MachineLogic):
    def fetchUser(self, interpreter, context, event):
        # Simulate an API call (sync version)
        return {"id": 1, "name": "Alice", "email": "alice@example.com"}

    def storeUser(self, interpreter, context, event, action_def):
        context["user"] = event.data

    def storeError(self, interpreter, context, event, action_def):
        context["error"] = str(event.data)

machine = create_machine(config, logic=UserLogic())
interp = SyncInterpreter(machine).start()

interp.send("LOAD")
print(interp.context["user"])
# {"id": 1, "name": "Alice", "email": "alice@example.com"}
print(interp.current_state_ids)
# {"userLoader.loaded"}
interp.stop()
```

## Service Implementation

### Service Signature

```python
def my_service(interpreter, context, event) -> Any:
    ...
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `interpreter` | `SyncInterpreter` or `Interpreter` | The running interpreter instance |
| `context` | `dict` | The machine's context (read-only recommended) |
| `event` | `Event` | A synthetic event with invoke metadata |

> **Note:** The service signature `(interpreter, context, event)` differs from the action signature `(interpreter, context, event, action_def)` — services do **not** receive `action_def`.

### Sync Service (with `requests`)

For use with `SyncInterpreter`:

```python
class UserLogicSync(MachineLogic):
    def fetchUser(self, interpreter, context, event):
        import requests
        user_id = context.get("userId", 1)
        resp = requests.get(f"https://jsonplaceholder.typicode.com/users/{user_id}")
        resp.raise_for_status()
        return resp.json()
```

### Async Service (with `aiohttp`)

For use with the async `Interpreter`:

```python
class UserLogicAsync(MachineLogic):
    async def fetchUser(self, interpreter, context, event):
        import aiohttp
        user_id = context.get("userId", 1)
        async with aiohttp.ClientSession() as session:
            resp = await session.get(
                f"https://jsonplaceholder.typicode.com/users/{user_id}"
            )
            return await resp.json()
```

> **Warning:** The `SyncInterpreter` raises `NotSupportedError` if you attempt to invoke an `async def` service. Use the async `Interpreter` for async services.

## onDone Handling

When a service completes successfully, the interpreter:

1. Wraps the return value in a `DoneEvent` with `type="done.invoke.<id>"`
2. Sends that event to the machine
3. The machine matches it against the `onDone` transition

### Target State and Actions

```json
"onDone": {
    "target": "loaded",
    "actions": "storeUser"
}
```

The `onDone` transition can include both a target state and actions — just like any other transition:

```json
"onDone": {
    "target": "loaded",
    "actions": ["storeUser", "logSuccess", "clearLoading"]
}
```

## onError Handling

When a service raises an exception, the interpreter:

1. Catches the exception
2. Wraps it in a `DoneEvent` with `type="error.platform.<id>"`
3. Sends that event to the machine
4. The machine matches it against the `onError` transition

### Error State and Error Actions

```json
"onError": {
    "target": "error",
    "actions": "storeError"
}
```

## Accessing Service Results

In `onDone` actions, the service's return value is available on `event.data`:

```python
class Logic(MachineLogic):
    def fetchUser(self, interpreter, context, event):
        return {"id": 1, "name": "Alice", "role": "admin"}

    def storeUser(self, interpreter, context, event, action_def):
        # event.data is the return value from fetchUser
        user = event.data
        context["user"] = user
        context["userName"] = user["name"]
        print(f"Loaded user: {user['name']}")
```

## Accessing Error Info

In `onError` actions, the exception object is available on `event.data`:

```python
class Logic(MachineLogic):
    def fetchUser(self, interpreter, context, event):
        raise ConnectionError("API server unreachable")

    def storeError(self, interpreter, context, event, action_def):
        # event.data is the exception object
        error = event.data
        context["error"] = str(error)
        context["errorType"] = type(error).__name__
        print(f"Service failed: {error}")
        # Output: Service failed: API server unreachable
```

## Multiple Services (Array Form)

A state can invoke multiple services simultaneously by using an array:

```json
{
  "loading": {
    "invoke": [
      {
        "src": "fetchUser",
        "id": "userService",
        "onDone": { "actions": "storeUser" },
        "onError": { "actions": "storeUserError" }
      },
      {
        "src": "fetchOrders",
        "id": "ordersService",
        "onDone": { "actions": "storeOrders" },
        "onError": { "actions": "storeOrdersError" }
      }
    ]
  }
}
```

> **Note:** Each invoke in the array needs a unique `id` to distinguish its `onDone`/`onError` events. If no `id` is provided, it defaults to the state's ID, which would cause collisions when multiple services are invoked.

```python
class DataLogic(MachineLogic):
    def fetchUser(self, interpreter, context, event):
        return {"name": "Alice"}

    def fetchOrders(self, interpreter, context, event):
        return [{"id": 1, "total": 29.99}]

    def storeUser(self, interpreter, context, event, action_def):
        context["user"] = event.data

    def storeOrders(self, interpreter, context, event, action_def):
        context["orders"] = event.data

    def storeUserError(self, interpreter, context, event, action_def):
        context["userError"] = str(event.data)

    def storeOrdersError(self, interpreter, context, event, action_def):
        context["ordersError"] = str(event.data)
```

## Service with Guards

You can add guards to `onDone` transitions to route based on the service result:

```json
{
  "loading": {
    "invoke": {
      "src": "fetchUser",
      "onDone": [
        { "target": "adminDashboard", "guard": "isAdmin", "actions": "storeUser" },
        { "target": "userDashboard", "actions": "storeUser" }
      ],
      "onError": {
        "target": "error"
      }
    }
  }
}
```

```python
class Logic(MachineLogic):
    def fetchUser(self, interpreter, context, event):
        return {"name": "Alice", "role": "admin"}

    def storeUser(self, interpreter, context, event, action_def):
        context["user"] = event.data

    def isAdmin(self, context, event):
        # event.data holds the service result
        user = event.data
        return isinstance(user, dict) and user.get("role") == "admin"
```

## Invoke with Timeout

Combine `invoke` with `after` to implement service timeouts. If the service doesn't complete before the timer fires, the machine transitions to a timeout state:

```json
{
  "loading": {
    "invoke": {
      "src": "fetchUser",
      "onDone": { "target": "loaded", "actions": "storeUser" },
      "onError": { "target": "error" }
    },
    "after": {
      "5000": { "target": "timeout" }
    }
  }
}
```

> **Tip:** The `after` timer is cancelled when the state is exited (e.g., when `onDone` fires first), so there is no conflict between the two.

## Pythonic Services

### `@service` Decorator

The `@service` decorator marks a function as a service:

```python
from xstate_statemachine import service

@service
def fetch_user(interpreter, context, event):
    return {"id": 1, "name": "Alice"}
# Registered as "fetchUser" (auto snake_case → camelCase)
```

### Explicit Naming

```python
@service("loadUserProfile")
def get_user(interpreter, context, event):
    return {"id": 1, "name": "Alice"}
# Registered as "loadUserProfile"
```

### Service in StateMachine Class

```python
from xstate_statemachine import State, StateMachine, SyncInterpreter, service, action

class UserLoader(StateMachine):
    machine_id = "userLoader"
    initial_context = {"user": None, "error": None}

    idle    = State("idle", initial=True, on={"LOAD": "loading"})
    loading = State("loading", invoke={
        "src": "fetchUser",
        "onDone": {"target": "loaded", "actions": "storeUser"},
        "onError": {"target": "error", "actions": "storeError"}
    })
    loaded  = State("loaded", final=True)
    error   = State("error", on={"RETRY": "loading"})

    @service
    def fetch_user(self, interpreter, context, event):
        return {"id": 1, "name": "Alice"}

    @action
    def store_user(self, interpreter, context, event, action_def):
        context["user"] = event.data

    @action
    def store_error(self, interpreter, context, event, action_def):
        context["error"] = str(event.data)

machine = UserLoader.create_machine()
interp = SyncInterpreter(machine).start()
interp.send("LOAD")
print(interp.context["user"])  # {"id": 1, "name": "Alice"}
interp.stop()
```

### Service in MachineBuilder

```python
from xstate_statemachine import MachineBuilder, SyncInterpreter

def fetch_user_fn(interpreter, context, event):
    return {"id": 1, "name": "Alice"}

def store_user_fn(interpreter, context, event, action_def):
    context["user"] = event.data

machine = (
    MachineBuilder("userLoader")
    .context({"user": None, "error": None})
    .state("idle", initial=True, on={"LOAD": "loading"})
    .state("loading", invoke={
        "src": "fetchUser",
        "onDone": {"target": "loaded", "actions": "storeUser"},
        "onError": {"target": "error"}
    })
    .state("loaded", final=True)
    .state("error", on={"RETRY": "loading"})
    .service("fetchUser", fetch_user_fn)
    .action("storeUser", store_user_fn)
    .build()
)

interp = SyncInterpreter(machine).start()
interp.send("LOAD")
print(interp.context["user"])  # {"id": 1, "name": "Alice"}
interp.stop()
```

## Service Lifecycle

When the interpreter enters a state with `invoke`, the following sequence occurs:

```
1. Enter the state (run entry actions)
2. Start the service (call the service function)
3. Service completes:
   a. Success → send "done.invoke.<id>" event with return value
   b. Failure → send "error.platform.<id>" event with exception
4. The machine processes the done/error event
5. Transition to onDone/onError target (run exit actions, transition actions, entry actions)
```

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────┐
│    idle      │────▶│     loading       │────▶│    loaded     │
│             │LOAD │  invoke:fetchUser │Done │              │
└─────────────┘     │                  │────▶│  (final)     │
                    │                  │     └──────────────┘
                    │                  │
                    │                  │Error ┌──────────────┐
                    │                  │────▶│    error      │
                    └──────────────────┘     │  RETRY→loading│
                                            └──────────────┘
```

## Service Cancellation

When the machine **exits a state** that has an active invocation, the service is automatically cancelled:

- **Async `Interpreter`**: The invoked task is cancelled via `asyncio.Task.cancel()`. The service's `asyncio.CancelledError` is suppressed — no `onError` is triggered.
- **`SyncInterpreter`**: Since sync services run to completion during `send()`, cancellation applies only to timers associated with the invoked state. If the state exits before a timer fires, the timer is discarded.

This means you can safely combine `invoke` with `after` timeouts: if the service completes first, the timer is cancelled when the state exits. If the timer fires first and causes a transition, the async service task is cancelled.

```python
# Safe pattern: invoke + timeout
"loading": {
    "invoke": {
        "src": "fetchUser",
        "onDone": {"target": "loaded"},
        "onError": {"target": "error"}
    },
    "after": {
        "5000": {"target": "timeout"}
    }
}
# Whichever completes first wins — the loser is automatically cancelled
```

> **Note:** Cancellation is automatic and requires no cleanup code. This is one of the key benefits of using `invoke` over manual service management.

## Event Naming for Done and Error

The interpreter uses a specific naming convention for invoke-related events:

| Event | Format | Example |
|-------|--------|---------|
| **Success** | `done.invoke.<id>` | `done.invoke.userFetcher` |
| **Error** | `error.platform.<id>` | `error.platform.userFetcher` |

The `<id>` defaults to the state's name if no explicit `id` is provided in the invoke config. When using multiple invokes per state, always provide explicit `id` values to avoid event name collisions:

```json
"invoke": [
  { "src": "fetchA", "id": "serviceA", "onDone": ... },
  { "src": "fetchB", "id": "serviceB", "onDone": ... }
]
```

## Sync vs Async Services

| Feature | `SyncInterpreter` | `Interpreter` (async) |
|---------|-------------------|----------------------|
| **Service type** | Regular `def` | `async def` |
| **Execution** | Blocks until complete | Awaited concurrently |
| **HTTP library** | `requests`, `urllib` | `aiohttp`, `httpx` |
| **Multiple invokes** | Sequential | Can run concurrently |
| **Async service?** | Raises `NotSupportedError` | Fully supported |

## Complete Example: User Data Loader with Retry

A production-style pattern with retry logic and error tracking:

```python
from xstate_statemachine import create_machine, SyncInterpreter, MachineLogic

config = {
    "id": "userDataLoader",
    "initial": "idle",
    "context": {
        "userId": 42,
        "user": None,
        "error": None,
        "retryCount": 0,
        "maxRetries": 3
    },
    "states": {
        "idle": {
            "on": {"FETCH": "loading"}
        },
        "loading": {
            "entry": "incrementRetry",
            "invoke": {
                "src": "fetchUserData",
                "onDone": {
                    "target": "success",
                    "actions": "storeUser"
                },
                "onError": [
                    {"target": "loading", "guard": "canRetry", "actions": "logRetry"},
                    {"target": "failed",  "actions": "storeFinalError"}
                ]
            }
        },
        "success": {
            "entry": "resetRetryCount",
            "type": "final"
        },
        "failed": {
            "on": {
                "RESET": {"target": "idle", "actions": "resetAll"}
            }
        }
    }
}

class UserDataLogic(MachineLogic):
    def __init__(self):
        super().__init__()
        self._call_count = 0

    # ---- Service ----
    def fetchUserData(self, interpreter, context, event):
        self._call_count += 1
        user_id = context.get("userId", 1)

        # Simulate: fail first 2 attempts, succeed on 3rd
        if self._call_count < 3:
            raise ConnectionError(
                f"Attempt {self._call_count}: Connection refused"
            )
        return {"id": user_id, "name": "Alice", "email": "alice@example.com"}

    # ---- Actions ----
    def storeUser(self, interpreter, context, event, action_def):
        context["user"] = event.data
        context["error"] = None
        print(f"User loaded: {event.data['name']}")

    def incrementRetry(self, interpreter, context, event, action_def):
        context["retryCount"] = context.get("retryCount", 0) + 1
        print(f"Loading attempt #{context['retryCount']}...")

    def logRetry(self, interpreter, context, event, action_def):
        print(f"  Retrying... ({event.data})")

    def storeFinalError(self, interpreter, context, event, action_def):
        context["error"] = str(event.data)
        print(f"All retries exhausted. Error: {event.data}")

    def resetRetryCount(self, interpreter, context, event, action_def):
        context["retryCount"] = 0

    def resetAll(self, interpreter, context, event, action_def):
        context["user"] = None
        context["error"] = None
        context["retryCount"] = 0

    # ---- Guards ----
    def canRetry(self, context, event):
        return context.get("retryCount", 0) < context.get("maxRetries", 3)


machine = create_machine(config, logic=UserDataLogic())
interp = SyncInterpreter(machine).start()

interp.send("FETCH")
# Output:
# Loading attempt #1...
#   Retrying... (Attempt 1: Connection refused)
# Loading attempt #2...
#   Retrying... (Attempt 2: Connection refused)
# Loading attempt #3...
# User loaded: Alice

print(interp.context["user"])
# {"id": 42, "name": "Alice", "email": "alice@example.com"}
interp.stop()
```

## Complete Example: Payment Processing Flow

A multi-stage payment flow with validation, charging, and confirmation:

```python
from xstate_statemachine import create_machine, SyncInterpreter, MachineLogic

config = {
    "id": "paymentProcessor",
    "initial": "idle",
    "context": {
        "amount": 0,
        "currency": "USD",
        "paymentMethod": None,
        "transactionId": None,
        "error": None,
        "receipt": None
    },
    "states": {
        "idle": {
            "on": {
                "START_PAYMENT": {
                    "target": "validating",
                    "actions": "storePaymentDetails"
                }
            }
        },
        "validating": {
            "invoke": {
                "src": "validatePayment",
                "onDone": {"target": "charging"},
                "onError": {"target": "validationFailed", "actions": "storeError"}
            }
        },
        "charging": {
            "invoke": {
                "src": "chargePayment",
                "onDone": {
                    "target": "confirming",
                    "actions": "storeTransactionId"
                },
                "onError": {"target": "chargeFailed", "actions": "storeError"}
            }
        },
        "confirming": {
            "invoke": {
                "src": "generateReceipt",
                "onDone": {
                    "target": "completed",
                    "actions": "storeReceipt"
                },
                "onError": {
                    "target": "completed",
                    "actions": "logReceiptError"
                }
            }
        },
        "completed": {
            "entry": "notifySuccess",
            "type": "final"
        },
        "validationFailed": {
            "entry": "notifyValidationError",
            "on": {
                "RETRY": {"target": "idle", "actions": "clearError"}
            }
        },
        "chargeFailed": {
            "entry": "notifyChargeError",
            "on": {
                "RETRY": {"target": "idle", "actions": "clearError"}
            }
        }
    }
}

class PaymentLogic(MachineLogic):
    # ---- Services ----
    def validatePayment(self, interpreter, context, event):
        amount = context.get("amount", 0)
        method = context.get("paymentMethod")
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if not method:
            raise ValueError("Payment method is required")
        return {"valid": True, "method": method}

    def chargePayment(self, interpreter, context, event):
        amount = context["amount"]
        print(f"Charging ${amount:.2f}...")
        # Simulate a charge — returns a transaction ID
        return {"transactionId": "TXN-20260323-001", "charged": amount}

    def generateReceipt(self, interpreter, context, event):
        txn_id = context.get("transactionId", "UNKNOWN")
        return {
            "receiptId": f"RCP-{txn_id}",
            "amount": context["amount"],
            "currency": context["currency"],
            "status": "paid"
        }

    # ---- Actions ----
    def storePaymentDetails(self, interpreter, context, event, action_def):
        context["amount"] = event.payload.get("amount", 0)
        context["currency"] = event.payload.get("currency", "USD")
        context["paymentMethod"] = event.payload.get("method")

    def storeTransactionId(self, interpreter, context, event, action_def):
        context["transactionId"] = event.data.get("transactionId")

    def storeReceipt(self, interpreter, context, event, action_def):
        context["receipt"] = event.data

    def storeError(self, interpreter, context, event, action_def):
        context["error"] = str(event.data)

    def clearError(self, interpreter, context, event, action_def):
        context["error"] = None

    def logReceiptError(self, interpreter, context, event, action_def):
        print(f"Receipt generation failed (non-critical): {event.data}")

    def notifySuccess(self, interpreter, context, event, action_def):
        txn = context.get("transactionId", "N/A")
        amt = context.get("amount", 0)
        print(f"Payment complete! Transaction: {txn}, Amount: ${amt:.2f}")

    def notifyValidationError(self, interpreter, context, event, action_def):
        print(f"Validation failed: {context.get('error', 'Unknown')}")

    def notifyChargeError(self, interpreter, context, event, action_def):
        print(f"Charge failed: {context.get('error', 'Unknown')}")


# Run the payment flow
machine = create_machine(config, logic=PaymentLogic())
interp = SyncInterpreter(machine).start()

interp.send("START_PAYMENT", amount=49.99, method="credit_card", currency="USD")
# Output:
# Charging $49.99...
# Payment complete! Transaction: TXN-20260323-001, Amount: $49.99

print(interp.context["transactionId"])  # TXN-20260323-001
print(interp.context["receipt"])
# {"receiptId": "RCP-TXN-20260323-001", "amount": 49.99, "currency": "USD", "status": "paid"}
interp.stop()
```

## See Also

- **[Context](../context/)** — services often populate context via `onDone` actions
- **[Guards](../guards/)** — guard `onDone` transitions to route based on service results
- **[Actions](../actions/)** — actions that process service results in `onDone`/`onError`
- **[Delayed Transitions](../delayed-transitions/)** — combine `invoke` with `after` for timeout patterns
- **[Actors](../actors/)** — spawn child machines as invoked services
- **[Interpreters](../interpreters/)** — sync vs async interpreter behavior with services
- **[Pythonic API](../pythonic-api/)** — `@service` decorator and `State(invoke=...)` syntax
