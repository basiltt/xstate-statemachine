---
title: "Actor Model"
description: "Spawn independent child machines from parent machines — isolated state, context, and lifecycle."
---

# Actor Model

The **Actor Model** lets you spawn independent child state machines from a parent machine. Each actor runs in isolation with its own state, context, and lifecycle. This is essential for modeling concurrent workflows, delegation patterns, and task distribution.

## What is the Actor Model?

In the actor model, a running state machine (the **parent**) can create one or more child state machines (the **actors**). Each actor:

- Has its **own state** — independent of the parent
- Has its **own context** — isolated data that the parent cannot directly mutate
- Has its **own lifecycle** — starts, runs, and stops independently
- Receives a reference to the parent via `child.parent`

This pattern is ideal for scenarios where a parent orchestrates multiple independent units of work, such as a task manager dispatching workers or an order system processing multiple items.

## Spawning Actors with the `spawn_` Prefix

To spawn an actor, define an action whose name starts with `spawn_`. The interpreter recognizes this prefix and treats it as a special built-in action. The suffix after `spawn_` becomes the **actor key**, which must match a key in your `MachineLogic.services` dictionary.

The service must be either:

- A `MachineNode` instance (a pre-built child machine), or
- A **factory function** that returns a `MachineNode`

### Basic Example: Spawning a Child Machine

```python
from xstate_statemachine import create_machine, MachineLogic, SyncInterpreter

# 1. Define the child machine configuration
child_config = {
    "id": "worker",
    "initial": "idle",
    "states": {
        "idle": {"on": {"DO_WORK": "working"}},
        "working": {"on": {"FINISH": "done"}},
        "done": {"type": "final"}
    }
}

# 2. Build the child machine
child_machine = create_machine(child_config)

# 3. Define the parent machine configuration
parent_config = {
    "id": "manager",
    "initial": "ready",
    "states": {
        "ready": {
            "on": {
                "HIRE": {"actions": "spawn_worker"}
            }
        }
    }
}

# 4. Register the child machine as a service
parent_logic = MachineLogic(
    services={"worker": child_machine}
)

# 5. Create and run the parent
parent_machine = create_machine(parent_config, logic=parent_logic)
interp = SyncInterpreter(parent_machine).start()

# 6. Spawn the actor by sending the event
interp.send("HIRE")  # Spawns the 'worker' actor

interp.stop()
```

> **Note:** The action name `spawn_worker` maps to the service key `worker`. The interpreter strips the `spawn_` prefix to look up the service.

## Spawning with a Factory Function

Instead of providing a pre-built `MachineNode`, you can provide a factory function. This is useful when the child machine's configuration depends on the parent's context or the triggering event.

```python
from xstate_statemachine import create_machine, MachineLogic, SyncInterpreter

def create_worker(interpreter, context, event):
    """Factory that creates a child machine based on the event payload."""
    worker_type = event.payload.get("type", "default")
    worker_config = {
        "id": f"worker-{worker_type}",
        "initial": "processing",
        "context": {"task_type": worker_type},
        "states": {
            "processing": {"on": {"COMPLETE": "done"}},
            "done": {"type": "final"}
        }
    }
    return create_machine(worker_config)

parent_config = {
    "id": "dispatcher",
    "initial": "listening",
    "states": {
        "listening": {
            "on": {
                "DISPATCH": {"actions": "spawn_taskRunner"}
            }
        }
    }
}

parent_logic = MachineLogic(
    services={"taskRunner": create_worker}
)

machine = create_machine(parent_config, logic=parent_logic)
interp = SyncInterpreter(machine).start()

interp.send("DISPATCH", type="email")  # Creates worker-email
interp.send("DISPATCH", type="sms")    # Creates worker-sms

interp.stop()
```

## Blocking Actors with `spawn_blocking_`

The `SyncInterpreter` supports **blocking actors** using the `spawn_blocking_` prefix. A blocking actor starts immediately and the parent interpreter waits for it to reach a final state before continuing.

```python
from xstate_statemachine import create_machine, MachineLogic, SyncInterpreter

# Child machine that processes and reaches a final state
child_config = {
    "id": "validator",
    "initial": "validating",
    "states": {
        "validating": {
            "on": {"": {"target": "valid"}}
        },
        "valid": {"type": "final"}
    }
}

child_machine = create_machine(child_config)

parent_config = {
    "id": "form",
    "initial": "editing",
    "states": {
        "editing": {
            "on": {
                "VALIDATE": {"actions": "spawn_blocking_validator"}
            }
        }
    }
}

parent_logic = MachineLogic(
    services={"validator": child_machine}
)

machine = create_machine(parent_config, logic=parent_logic)
interp = SyncInterpreter(machine).start()

# This blocks until the validator reaches its final state
interp.send("VALIDATE")

interp.stop()
```

> **Tip:** Use `spawn_blocking_` when you need the child to complete before the parent processes the next event. Use `spawn_` (non-blocking) when the child should run concurrently in a background thread.

## Actor Communication

Actors and parents communicate through events. After spawning, the parent can interact with the child through actions that reference the child via the interpreter's actor management:

```python
from xstate_statemachine import create_machine, MachineLogic, SyncInterpreter

child_config = {
    "id": "processor",
    "initial": "waiting",
    "context": {"items_processed": 0},
    "states": {
        "waiting": {"on": {"PROCESS": "processing"}},
        "processing": {
            "on": {
                "ITEM_DONE": {"actions": "countItem"},
                "STOP": "done"
            }
        },
        "done": {"type": "final"}
    }
}

child_logic = MachineLogic(
    actions={
        "countItem": lambda i, ctx, e, a: ctx.update(
            {"items_processed": ctx["items_processed"] + 1}
        )
    }
)
child_machine = create_machine(child_config, logic=child_logic)

# Parent machine: spawns a processor and tracks it in context
parent_config = {
    "id": "coordinator",
    "initial": "idle",
    "states": {
        "idle": {
            "on": {
                "START": {
                    "target": "running",
                    "actions": "spawn_processor"
                }
            }
        },
        "running": {
            "on": {
                "DONE": "completed"
            }
        },
        "completed": {"type": "final"}
    }
}

parent_logic = MachineLogic(
    services={"processor": child_machine}
)

machine = create_machine(parent_config, logic=parent_logic)
interp = SyncInterpreter(machine).start()

interp.send("START")  # Spawns the processor actor
interp.stop()
```

> **Note:** Communication between parent and child actors happens through the event system. The parent sends events that trigger child transitions, and child completion emits `done` events back to the parent.

## Actors with the Async Interpreter

Actors work seamlessly with the async `Interpreter`. The child machine is spawned as another `Interpreter` instance running its own event loop:

```python
import asyncio
from xstate_statemachine import create_machine, Interpreter, MachineLogic

child_config = {
    "id": "asyncWorker",
    "initial": "running",
    "states": {
        "running": {"on": {"COMPLETE": "done"}},
        "done": {"type": "final"}
    }
}

child_machine = create_machine(child_config)

parent_config = {
    "id": "asyncManager",
    "initial": "ready",
    "states": {
        "ready": {
            "on": {"SPAWN": {"actions": "spawn_worker"}}
        }
    }
}

parent_logic = MachineLogic(
    services={"worker": child_machine}
)

async def main():
    machine = create_machine(parent_config, logic=parent_logic)
    interp = await Interpreter(machine).start()
    await interp.send("SPAWN")  # Spawns async child actor
    await asyncio.sleep(0.1)    # Give the actor time to start
    await interp.stop()         # Stops parent and all children

asyncio.run(main())
```

## Complete Example: Task Manager with Worker Actors

This example demonstrates a task manager that spawns worker actors to process tasks concurrently:

```python
from xstate_statemachine import create_machine, MachineLogic, SyncInterpreter

# --- Worker Machine ---
worker_config = {
    "id": "worker",
    "initial": "processing",
    "context": {"task_id": None, "result": None},
    "states": {
        "processing": {
            "on": {"FINISH": {"target": "completed", "actions": "saveResult"}}
        },
        "completed": {"type": "final"}
    }
}

worker_logic = MachineLogic(
    actions={
        "saveResult": lambda i, ctx, e, a: ctx.update(
            {"result": f"Task {ctx['task_id']} done"}
        )
    }
)
worker_machine = create_machine(worker_config, logic=worker_logic)

# --- Manager Machine ---
def create_task_worker(interpreter, context, event):
    """Factory: creates a worker configured for the specific task."""
    task_id = event.payload.get("task_id", "unknown")
    config = {
        "id": f"worker-{task_id}",
        "initial": "processing",
        "context": {"task_id": task_id, "result": None},
        "states": {
            "processing": {
                "on": {"FINISH": {"target": "completed", "actions": "saveResult"}}
            },
            "completed": {"type": "final"}
        }
    }
    logic = MachineLogic(
        actions={
            "saveResult": lambda i, ctx, e, a: ctx.update(
                {"result": f"Task {ctx['task_id']} completed"}
            )
        }
    )
    return create_machine(config, logic=logic)

def log_spawn(interpreter, context, event, action_def):
    """Track spawned tasks in the parent context."""
    task_id = event.payload.get("task_id", "unknown")
    context["active_tasks"].append(task_id)
    print(f"Dispatched task: {task_id}")

manager_config = {
    "id": "taskManager",
    "initial": "accepting",
    "context": {"active_tasks": []},
    "states": {
        "accepting": {
            "on": {
                "SUBMIT_TASK": {"actions": ["logSpawn", "spawn_taskWorker"]},
                "SHUTDOWN": "shutDown"
            }
        },
        "shutDown": {"type": "final"}
    }
}

manager_logic = MachineLogic(
    actions={"logSpawn": log_spawn},
    services={"taskWorker": create_task_worker}
)

machine = create_machine(manager_config, logic=manager_logic)
interp = SyncInterpreter(machine).start()

interp.send("SUBMIT_TASK", task_id="001")
interp.send("SUBMIT_TASK", task_id="002")

print(f"Active tasks: {interp.context['active_tasks']}")
# Active tasks: ['001', '002']

interp.send("SHUTDOWN")
interp.stop()
```

## Best Practices for Actor Design

1. **Keep actors self-contained** — Each actor should have its own complete logic. Avoid tight coupling between parent and child.

2. **Use factory functions** for dynamic actors — When child machines depend on runtime data, use factory functions in `services` rather than pre-built `MachineNode` instances.

3. **Prefer `spawn_` (non-blocking)** for concurrent work — Non-blocking actors run in background threads, ideal for parallel processing.

4. **Use `spawn_blocking_` sparingly** — Blocking actors halt the parent's event processing. Only use them when sequential completion is required.

5. **Clean up actors** — The interpreter automatically stops all child actors when `stop()` is called. For long-running actors, send explicit shutdown events before stopping the parent.

6. **Error handling** — If the service lookup fails or the factory returns a non-`MachineNode` value, an `ActorSpawningError` is raised. Always ensure your service keys match your `spawn_` action names.

> **Warning:** Async actions and services are not supported in `SyncInterpreter`. If you need async actors, use the async `Interpreter` instead.
