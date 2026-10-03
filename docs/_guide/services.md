---
title: "Services & Invoke"
description: "Async operations — API calls, database queries, and external integrations."
---

Services represent **external operations** — API calls, database queries, file reads, computations — that a state invokes when it is entered. When the service completes, the machine automatically transitions via `onDone`; if it fails, the machine transitions via `onError`.

## 📞 What are Services?

A service is a callable that runs when a state is entered and produces a result (or an error). Services bridge the gap between your state machine's declarative flow and the imperative world of I/O operations.

Key characteristics:

- **Invoked by states** — services are tied to a state's `invoke` property, not to transitions.
- **Result-driven** — the return value becomes `event.data` in the `onDone` handler.
- **Error-aware** — exceptions are caught and routed to `onError` handlers.
- **Sync or async** — `SyncInterpreter` requires sync services; `Interpreter` supports async.

## 🧱 JSON Invoke Structure

```mermaid
flowchart LR
    S["state <b>loading</b>"] --> I["invoke<br/><small>src: fetchUser · id · input</small>"]
    I -- "resolves" --> D["onDone<br/><small>event.data = return value</small>"]
    I -- "raises" --> E["onError<br/><small>ErrorEvent · event.error = exception</small>"]
    S -. "leave state early" .-> X["service cancelled"]
```

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
| `input` | `any` \| `callable` | Static data (or a `fn(context, event)` / `fn({"context": ..., "event": ...})` callable, resolved fresh on every spawn) forwarded to the invoked service or child. A callable service receives it at `event.payload["input"]`; a spawned child machine receives it at `context["input"]`. |
| `systemId` | `string` | Registers the invocation under a global actor address so it can be addressed from anywhere in the tree with `send_to` — see [Actors](../actors/). |
| `onDone` | `object` | Transition to take on successful completion |
| `onError` | `object` | Transition to take on failure (exception) |

For example, to pass a per-spawn value to a service:

```json
{
  "invoke": {
    "src": "fetchUser",
    "input": {"userId": 42},
    "onDone": {"target": "loaded", "actions": "storeUser"}
  }
}
```

```python
def fetch_user(interpreter, context, event):
    user_id = event.payload["input"]["userId"]
    return {"id": user_id, "name": "Ada"}
```

## 🚀 Basic Invoke Example

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
    def fetch_user(self, interpreter, context, event):
        # Simulate an API call (sync version)
        return {"id": 1, "name": "Alice", "email": "alice@example.com"}

    def store_user(self, interpreter, context, event, action_def):
        context["user"] = event.data

    def store_error(self, interpreter, context, event, action_def):
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

## 🧠 Service Implementation

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
    def fetch_user(self, interpreter, context, event):
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
    async def fetch_user(self, interpreter, context, event):
        import aiohttp
        user_id = context.get("userId", 1)
        async with aiohttp.ClientSession() as session:
            resp = await session.get(
                f"https://jsonplaceholder.typicode.com/users/{user_id}"
            )
            return await resp.json()
```

> **Warning:** The `SyncInterpreter` raises `NotSupportedError` when the state that invokes an `async def` service is entered (e.g. on the `send()` call that triggers the transition) — not when the machine is created or started. Use the async `Interpreter` for async services.

## ✅ onDone Handling

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

## ❌ onError Handling

When a service raises an exception, the interpreter:

1. Catches the exception
2. Wraps it in an **`ErrorEvent`** with `type="error.platform.<id>"` and the exception on `.error` (0.9.0, #80 — before that it was a `DoneEvent` carrying the exception in `data`)
3. Sends that event to the machine
4. The machine matches it against the `onError` transition

If **no** `onError` (and no matching `on`) handles it, the failure is not swallowed: the *parent* interpreter fails — `status` becomes `"error"`, `last_error` holds the exception and `on_error` fires — on **both** engines (0.9.0, #99; before, only the sync engine did this). An unhandled invoked-child failure behaves the same way. Declare an `onError` on every `invoke` whose failure you want to survive.

### Error State and Error Actions

```json
"onError": {
    "target": "error",
    "actions": "storeError"
}
```

## 📦 Accessing Service Results

In `onDone` actions, the service's return value is available on `event.data`:

```python
class Logic(MachineLogic):
    def fetch_user(self, interpreter, context, event):
        return {"id": 1, "name": "Alice", "role": "admin"}

    def store_user(self, interpreter, context, event, action_def):
        # event.data is the return value from fetch_user
        user = event.data
        context["user"] = user
        context["userName"] = user["name"]
        print(f"Loaded user: {user['name']}")
```

> **Invoked child machines are different.** When `src` is a `MachineNode` rather than a callable, `event.data` on `done.invoke.<id>` is the child's **declared `output`** — the machine-level `output` if there is one, else the final state's `output` — never the child's private `context` (0.9.0, #109). Declare what the parent is allowed to see.

## 🐛 Accessing Error Info

In `onError` actions the event is an `ErrorEvent` and the exception object is on `event.error`:

```python
from xstate_statemachine import ErrorEvent, MachineLogic

class Logic(MachineLogic):
    def fetch_user(self, interpreter, context, event):
        raise ConnectionError("API server unreachable")

    def store_error(self, interpreter, context, event, action_def):
        assert isinstance(event, ErrorEvent)      # branch on type, not on a string prefix
        error = event.error                       # the exception object
        context["error"] = str(error)
        context["errorType"] = type(error).__name__
        print(f"Service failed: {error}")
        # Output: Service failed: API server unreachable
```

> **Migrating from 0.8.0:** `event.data` still returns the exception on an `ErrorEvent`, with a `DeprecationWarning`; it is removed in 0.9. Success events are unchanged — `onDone` still receives a `DoneEvent` whose `data` is the service's return value.

## 🔗 Multiple Services (Array Form)

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
    def fetch_user(self, interpreter, context, event):
        return {"name": "Alice"}

    def fetch_orders(self, interpreter, context, event):
        return [{"id": 1, "total": 29.99}]

    def store_user(self, interpreter, context, event, action_def):
        context["user"] = event.data

    def store_orders(self, interpreter, context, event, action_def):
        context["orders"] = event.data

    def store_user_error(self, interpreter, context, event, action_def):
        context["userError"] = str(event.data)

    def store_orders_error(self, interpreter, context, event, action_def):
        context["ordersError"] = str(event.data)
```

## 🛡️ Service with Guards

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
    def fetch_user(self, interpreter, context, event):
        return {"name": "Alice", "role": "admin"}

    def store_user(self, interpreter, context, event, action_def):
        context["user"] = event.data

    def is_admin(self, context, event):
        # event.data holds the service result
        user = event.data
        return isinstance(user, dict) and user.get("role") == "admin"
```

## ⏱️ Invoke with Timeout

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

## 🐍 Pythonic Services

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

## 🔁 Service Lifecycle

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

```mermaid
stateDiagram-v2
    direction LR
    [*] --> idle
    idle --> loading : LOAD
    state "loading<br/>invoke: fetchUser" as loading
    loading --> loaded : done.invoke.fetchUser
    loading --> error : error.platform.fetchUser
    error --> loading : RETRY
    loaded --> [*]
```

## ✂️ Service Cancellation

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

## 🏷️ Event Naming for Done and Error

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

A plain-`def` service on the async `Interpreter` runs on a private thread pool so it cannot block the event loop — `Interpreter(service_pool_size=4)` (`DEFAULT_SERVICE_POOL_SIZE`) sizes it, or pass your own `service_executor=`. Its completion is delivered with exactly the standing an `async def` service's has (engine-minted, charged to `maxIterations` only when it continues a self-fed chain).

If a `maxIterations` cut discards a service's completion while its state is still active, nothing will ever complete for it: `on_invocation_stranded(interpreter, state_id, invoke_id, error)` fires, `RunawayChainError.stranded` names the ids, and `has_dormant_invocations` is `True` (0.9.0, #207).

| Feature | `SyncInterpreter` | `Interpreter` (async) |
|---------|-------------------|----------------------|
| **Service type** | Regular `def` | `async def` |
| **Execution** | Blocks until complete | Awaited concurrently |
| **HTTP library** | `requests`, `urllib` | `aiohttp`, `httpx` |
| **Multiple invokes** | Sequential | Can run concurrently |
| **Async service?** | Raises `NotSupportedError` | Fully supported |

Engine parity note (0.9.0, #116): a plain `def` service — one that returns a value, not an awaitable — completes at the **same point** on both engines. The async `Interpreter` runs it inline instead of on a separate task, and the sync engine queues its completion behind the current macrostep, so a script such as `send("GO"); send("CANCEL")` lands in the same state whichever interpreter you use. A `def` that returns a coroutine, or an `AsyncMock`, still takes the awaited path.

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
    def fetch_user_data(self, interpreter, context, event):
        self._call_count += 1
        user_id = context.get("userId", 1)

        # Simulate: fail first 2 attempts, succeed on 3rd
        if self._call_count < 3:
            raise ConnectionError(
                f"Attempt {self._call_count}: Connection refused"
            )
        return {"id": user_id, "name": "Alice", "email": "alice@example.com"}

    # ---- Actions ----
    def store_user(self, interpreter, context, event, action_def):
        context["user"] = event.data
        context["error"] = None
        print(f"User loaded: {event.data['name']}")

    def increment_retry(self, interpreter, context, event, action_def):
        context["retryCount"] = context.get("retryCount", 0) + 1
        print(f"Loading attempt #{context['retryCount']}...")

    def log_retry(self, interpreter, context, event, action_def):
        print(f"  Retrying... ({event.data})")

    def store_final_error(self, interpreter, context, event, action_def):
        context["error"] = str(event.data)
        print(f"All retries exhausted. Error: {event.data}")

    def reset_retry_count(self, interpreter, context, event, action_def):
        context["retryCount"] = 0

    def reset_all(self, interpreter, context, event, action_def):
        context["user"] = None
        context["error"] = None
        context["retryCount"] = 0

    # ---- Guards ----
    def can_retry(self, context, event):
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
    def validate_payment(self, interpreter, context, event):
        amount = context.get("amount", 0)
        method = context.get("paymentMethod")
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if not method:
            raise ValueError("Payment method is required")
        return {"valid": True, "method": method}

    def charge_payment(self, interpreter, context, event):
        amount = context["amount"]
        print(f"Charging ${amount:.2f}...")
        # Simulate a charge — returns a transaction ID
        return {"transactionId": "TXN-20260323-001", "charged": amount}

    def generate_receipt(self, interpreter, context, event):
        txn_id = context.get("transactionId", "UNKNOWN")
        return {
            "receiptId": f"RCP-{txn_id}",
            "amount": context["amount"],
            "currency": context["currency"],
            "status": "paid"
        }

    # ---- Actions ----
    def store_payment_details(self, interpreter, context, event, action_def):
        context["amount"] = event.payload.get("amount", 0)
        context["currency"] = event.payload.get("currency", "USD")
        context["paymentMethod"] = event.payload.get("method")

    def store_transaction_id(self, interpreter, context, event, action_def):
        context["transactionId"] = event.data.get("transactionId")

    def store_receipt(self, interpreter, context, event, action_def):
        context["receipt"] = event.data

    def store_error(self, interpreter, context, event, action_def):
        context["error"] = str(event.data)

    def clear_error(self, interpreter, context, event, action_def):
        context["error"] = None

    def log_receipt_error(self, interpreter, context, event, action_def):
        print(f"Receipt generation failed (non-critical): {event.data}")

    def notify_success(self, interpreter, context, event, action_def):
        txn = context.get("transactionId", "N/A")
        amt = context.get("amount", 0)
        print(f"Payment complete! Transaction: {txn}, Amount: ${amt:.2f}")

    def notify_validation_error(self, interpreter, context, event, action_def):
        print(f"Validation failed: {context.get('error', 'Unknown')}")

    def notify_charge_error(self, interpreter, context, event, action_def):
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

## Services and Snapshots

Restoring an interpreter from a snapshot (`from_snapshot()`) is, by default, a **static restoration**: entry actions are not re-run and no invoked service or `after` timer is restarted. If the snapshot was taken while a state had an active `invoke`, the restored machine comes back parked in that state with the service *not* running.

Use `interpreter.pending_invocations()` to see what's parked — it lists every `invoke` in the active configuration that has no live service behind it. To re-drive them, pass `restart_services=True` to `from_snapshot()`, which makes `start()` re-invoke every pending service **from scratch, not resumed**. For a side-effecting service (e.g. placing an order or charging a card), that means the service call happens again, so pair it with a client-supplied idempotency key.

```python
interp = SyncInterpreter.from_snapshot(snapshot_str, machine, restart_services=True).start()
```

See [Snapshots](../snapshots/) for the full persistence model.

## Actor logic helpers

A service is "just a callable" — fine for a one-shot coroutine, awkward for **callback-style SDKs** (a websocket client, paho-mqtt, a GUI toolkit) that push many events into the machine over time, and for **streams** (an async iterator of LLM chunks, a Kafka consumer). XState v5 unified these under *actor logic*: `fromPromise`, `fromCallback`, `fromObservable`, `fromActor`. The Python twins live in `xstate_statemachine.actor_logic` and are exported at the top level.

| XState v5 | Python | Engine | Completes? |
|:--|:--|:--|:--|
| `fromPromise(fn)` | `from_coroutine(async_fn)` | async | `onDone` with the return value |
| — | `from_callable(fn)` | both | `onDone` with the return value |
| `fromCallback(setup)` | `from_callback(setup)` | both | never on its own — cleanup on state exit |
| `fromObservable(factory)` | `from_async_iterator(factory)` | async | `onDone` with the last item |
| — | `from_iterator(factory)` | both (a daemon thread) | `onDone` with the last item |
| `fromActor(ref)` | `from_interpreter(interp)` | both | when the child reaches a final state |

They are ordinary services: `xsm inspect` lists them under *services*, `sendTo(<invoke id>)` addresses a running callback, and exiting the invoking state cleans up. Every `send_back` is **thread-safe** — from any thread or loop — because it routes through the engine's `send_threadsafe()`: on the async engine that is `call_soon_threadsafe`; on the sync engine the event lands in a mailbox the owning thread drains on its next `send()` / `tick()` (the same rule as sync timers).

### `from_callback` — a callback-style client

```python
import threading
from xstate_statemachine import MachineLogic, SyncInterpreter, create_machine, from_callback

class FakeMqttClient:                         # stands in for paho.mqtt.client.Client
    def __init__(self):
        self.on_message = None
        self.published = []
    def connect(self):
        # the broker "delivers" two messages on its own thread
        def deliver():
            for topic in ("sensors/temp", "sensors/humidity"):
                self.on_message(topic)
        t = threading.Thread(target=deliver); t.start(); t.join()
    def publish(self, topic, body):
        self.published.append((topic, body))
    def disconnect(self):
        self.published.append(("__disconnected__", None))

client = FakeMqttClient()

def mqtt_logic(send_back, receive, ctx, event):
    """Runs once when the invoking state is entered."""
    client.on_message = lambda topic: send_back("MESSAGE", topic=topic)   # broker -> machine, any thread
    receive(lambda ev: client.publish(ev.payload["topic"], ev.payload["body"]))  # machine -> broker
    client.connect()
    return client.disconnect                                             # cleanup on state exit

cfg = {"id": "gateway", "initial": "connected", "context": {"topics": []},
       "states": {"connected": {"invoke": {"src": "mqtt", "id": "broker"},
                                "on": {"MESSAGE": {"actions": "record"},
                                       "ANNOUNCE": {"actions": {"type": "sendTo", "params": {
                                           "to": "broker", "event": {"type": "PUBLISH", "topic": "status", "body": "up"}}}},
                                       "SHUTDOWN": "offline"}},
                  "offline": {"type": "final"}}}
logic = MachineLogic(actions={"record": lambda i, ctx, e, a: ctx["topics"].append(e.payload["topic"])},
                     services={"mqtt": from_callback(mqtt_logic)})

gateway = SyncInterpreter(create_machine(cfg, logic=logic)).start()
gateway.tick()                                              # drains the broker's messages (sync mailbox rule)
assert gateway.context["topics"] == ["sensors/temp", "sensors/humidity"]
gateway.send("ANNOUNCE")                                    # sendTo("broker") reaches receive()
assert client.published == [("status", "up")]
gateway.send("SHUTDOWN")                                    # state exit -> cleanup exactly once
assert client.published[-1] == ("__disconnected__", None)
```

`setup(send_back, receive, ctx, event)` returns a cleanup callable (or `None`). Cleanup runs **exactly once** on state exit, on `stop()`, or when `setup` raised; an exception inside `setup` is `onError`. An `async def` cleanup is awaited by the async engine's `stop()`.

### `from_async_iterator` — a token stream

```python
import asyncio
from xstate_statemachine import Interpreter, MachineLogic, create_machine, from_async_iterator, to_promise

async def llm_stream(interp, ctx, event):
    """Stands in for an SDK's streaming completion."""
    for token in ["The ", "answer ", "is ", "42."]:
        await asyncio.sleep(0)
        yield token

cfg = {"id": "chat", "initial": "streaming", "context": {"text": ""},
       "states": {"streaming": {"invoke": {"src": "llm", "onDone": {"target": "done", "actions": "finish"}},
                                "on": {"STREAM": {"actions": "append"}}},
                  "done": {"type": "final"}}}
logic = MachineLogic(actions={"append": lambda i, ctx, e, a: ctx.__setitem__("text", ctx["text"] + e.data),
                              "finish": lambda i, ctx, e, a: ctx.__setitem__("last", e.data)},
                     services={"llm": from_async_iterator(llm_stream)})

async def main():
    chat = await Interpreter(create_machine(cfg, logic=logic)).start()
    await to_promise(chat)
    assert chat.context["text"] == "The answer is 42."
    assert chat.context["last"] == "42."          # onDone carries the last item

asyncio.run(main())
```

Each yielded item is sent as a `StreamEvent("STREAM", {"data": item})` (`event_type=` to rename it): **`e.data` is the item itself**, as it is for `DoneEvent`, and `e.payload["data"]` is the same value for code that works with plain dicts. The machine applies it before the next item is pulled, so stream order and completion order agree. Exhaustion is `onDone` with the last item; an exception is `onError`; leaving the state cancels the task and `aclose()`s the generator, so a `finally:` in it runs. `from_iterator` is the sync twin — the iterator is consumed on a daemon thread and items arrive through the mailbox.

#### What the #267 battle pinned

A market-data feed that flaps for an hour (`tests/recipes/test_battle_267_feed_soak.py`: 20 000 ticks pushed from the socket's own thread across 50 drop/reconnect cycles, both engines) and the adversary suites found these, all fixed in 0.11.0:

* **A producer that outlives its state is ignored.** A WebSocket thread does not know the machine left `connected`; its late `send_back` used to land in whatever state came next (and on the *next* socket's counter). Now a `send_back` whose invocation has been cleaned up is dropped with a debug log — SCXML's rule for a cancelled invocation.
* **`send_back` payload keys that are `send()` controls are refused.** `send_back("TICK", internal=True)` reached the async engine's `send_threadsafe(internal=…)` as a control and the sync engine's as payload. Both now raise `TypeError` for `internal` / `wait` / `priority`; send a dict event to carry such a key.
* **`stop()` cannot hang on an `async def` cleanup.** `drain_pending_cleanups(timeout=30.0)` cancels and logs a cleanup still running after the timeout, and drains only the current loop's cleanups — a task left behind by a closed `asyncio.run()` loop no longer breaks the next one with `ValueError("different loop")`.
* **A delayed `sendTo` whose target invocation has exited is dropped**, reported through `on_event_dropped(reason="unresolved_target")`, never delivered to torn-down logic.
* **`from_iterator` cannot interrupt a blocked `next()`.** A sync iterator stuck in a blocking read stops at its *next* item; the engine logs a warning naming the invocation when a cleanup finds the thread still alive. Give blocking iterators a timeout, or use `from_callback` and let the client's own thread push.
* **The stream item is `e.data`.** The issue's own example read a token as `e.data` and got `{"data": token}` — the `StreamEvent` shape above.

## See Also

- **[Context](../context/)** — services often populate context via `onDone` actions
- **[Guards](../guards/)** — guard `onDone` transitions to route based on service results
- **[Actions](../actions/)** — actions that process service results in `onDone`/`onError`
- **[Delayed Transitions](../delayed-transitions/)** — combine `invoke` with `after` for timeout patterns
- **[Actors](../actors/)** — spawn child machines as invoked services
- **[Interpreters](../interpreters/)** — sync vs async interpreter behavior with services
- **[Pythonic API](../pythonic-api/)** — `@service` decorator and `State(invoke=...)` syntax
- **[Snapshots](../snapshots/)** — persisting and restoring interpreters, and how invoked services behave across a restore
