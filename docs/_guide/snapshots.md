---
title: "Snapshots & State Restoration"
description: "Save and restore machine state — persistence, crash recovery, and testing."
---

# Snapshots & State Restoration

Snapshots let you **capture** and **restore** a machine's state at any point in time. This implements the **Memento pattern**, enabling persistence, crash recovery, workflow checkpointing, and targeted testing.

## What are Snapshots?

A snapshot is a JSON string that captures the essential runtime state of an interpreter:

- **`status`** — the interpreter's lifecycle status (`"running"`, `"stopped"`, etc.)
- **`context`** — the full context dictionary (all mutable data)
- **`state_ids`** — the list of all currently active state IDs

You create a snapshot with `get_snapshot()` and restore from one with `from_snapshot()`.

## `get_snapshot()` — Capturing State

The `get_snapshot()` method returns a JSON string representing the interpreter's current state. Call it on any running interpreter at any time.

```python
from xstate_statemachine import create_machine, SyncInterpreter

config = {
    "id": "workflow",
    "initial": "step1",
    "context": {"progress": 0, "data": {}},
    "states": {
        "step1": {"on": {"NEXT": {"target": "step2", "actions": "updateProgress"}}},
        "step2": {"on": {"NEXT": {"target": "step3", "actions": "updateProgress"}}},
        "step3": {"on": {"NEXT": {"target": "step4", "actions": "updateProgress"}}},
        "step4": {"type": "final"}
    }
}

from xstate_statemachine import MachineLogic

logic = MachineLogic(
    actions={
        "updateProgress": lambda i, ctx, e, a: ctx.update(
            {"progress": ctx["progress"] + 25}
        )
    }
)

machine = create_machine(config, logic=logic)
interp = SyncInterpreter(machine).start()

# Advance to step2
interp.send("NEXT")
interp.context["data"]["step1_result"] = "validated"

# Capture a snapshot
snapshot_json = interp.get_snapshot()
print(snapshot_json)
```

**Output:**

```json
{
  "status": "running",
  "context": {
    "progress": 25,
    "data": {
      "step1_result": "validated"
    }
  },
  "state_ids": [
    "workflow.step2"
  ]
}
```

The snapshot is a standard JSON string — you can store it anywhere: files, databases, message queues, or environment variables.

```python
interp.stop()
```

## `from_snapshot()` — Restoring State

The `from_snapshot()` class method creates a **new** interpreter instance pre-configured with the saved state. You provide the snapshot JSON string and the **same machine definition** that was used to create the original interpreter.

```python
import json

# Re-create the same machine definition
machine = create_machine(config, logic=logic)

# Restore from the snapshot
restored = SyncInterpreter.from_snapshot(snapshot_json, machine)

print(restored.current_state_ids)  # {'workflow.step2'}
print(restored.context["progress"])  # 25
print(restored.context["data"])  # {'step1_result': 'validated'}
print(restored.status)  # 'running'

# Continue from where we left off
restored.send("NEXT")  # step2 -> step3
print(restored.current_state_ids)  # {'workflow.step3'}
print(restored.context["progress"])  # 50

restored.send("NEXT")  # step3 -> step4 (final)
restored.stop()
```

> **Note:** `from_snapshot()` is a class method on both `SyncInterpreter` and `Interpreter`. Call it on the class you want to create:
> ```python
> restored_sync = SyncInterpreter.from_snapshot(snapshot_json, machine)
> restored_async = Interpreter.from_snapshot(snapshot_json, machine)
> ```

## Important Limitations

> **Warning:** `from_snapshot()` performs a **static restoration**. Be aware of these constraints:
>
> - **Entry actions are NOT re-run** — The restored interpreter is placed directly into the saved states without executing their `entry` actions.
> - **Services are NOT restarted** — Any `invoke` services that were running when the snapshot was taken are not re-invoked.
> - **Timers are NOT resumed** — Any `after` delayed transitions are not rescheduled. The countdown does not persist across snapshots.
> - **Context is restored by value** — The context dictionary is deserialized from JSON. Non-serializable values (functions, class instances, file handles) will be lost or converted to strings.
> - **Machine definition must match** — The `machine` argument to `from_snapshot()` must have the same structure as the original. If state IDs have changed, restoration will fail with `StateNotFoundError`.

## Persistence: Save to File

The simplest persistence pattern writes the snapshot to a JSON file:

```python
from pathlib import Path
from xstate_statemachine import create_machine, SyncInterpreter, MachineLogic

config = {
    "id": "onboarding",
    "initial": "welcome",
    "context": {"user": "alice", "steps_completed": []},
    "states": {
        "welcome": {"on": {"CONTINUE": "profile"}},
        "profile": {"on": {"CONTINUE": "preferences"}},
        "preferences": {"on": {"CONTINUE": "complete"}},
        "complete": {"type": "final"}
    }
}

machine = create_machine(config)
interp = SyncInterpreter(machine).start()

interp.send("CONTINUE")  # welcome -> profile
interp.context["steps_completed"].append("welcome")

# Save to file
snapshot = interp.get_snapshot()
Path("onboarding_state.json").write_text(snapshot)
interp.stop()

# --- Later, in a different process or after a restart ---

# Load from file
saved = Path("onboarding_state.json").read_text()
machine = create_machine(config)  # Same definition
restored = SyncInterpreter.from_snapshot(saved, machine)

print(restored.current_state_ids)  # {'onboarding.profile'}
print(restored.context["steps_completed"])  # ['welcome']

# Continue the workflow
restored.send("CONTINUE")  # profile -> preferences
restored.context["steps_completed"].append("profile")
restored.stop()
```

## Database Persistence: SQLite Example

For production systems, store snapshots in a database:

```python
import sqlite3
import json
from xstate_statemachine import create_machine, SyncInterpreter

# --- Database Setup ---
def init_db(db_path="machines.db"):
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS machine_snapshots (
            machine_id TEXT PRIMARY KEY,
            snapshot TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn

def save_snapshot(conn, machine_id, interpreter):
    """Save the interpreter's current state to the database."""
    snapshot = interpreter.get_snapshot()
    conn.execute(
        """INSERT OR REPLACE INTO machine_snapshots
           (machine_id, snapshot, updated_at)
           VALUES (?, ?, CURRENT_TIMESTAMP)""",
        (machine_id, snapshot)
    )
    conn.commit()
    print(f"Saved snapshot for '{machine_id}'")

def load_snapshot(conn, machine_id):
    """Load a saved snapshot from the database."""
    cursor = conn.execute(
        "SELECT snapshot FROM machine_snapshots WHERE machine_id = ?",
        (machine_id,)
    )
    row = cursor.fetchone()
    return row[0] if row else None

# --- Usage ---
config = {
    "id": "order-42",
    "initial": "placed",
    "context": {"items": ["widget"], "total": 29.99},
    "states": {
        "placed": {"on": {"CONFIRM": "confirmed"}},
        "confirmed": {"on": {"SHIP": "shipped"}},
        "shipped": {"on": {"DELIVER": "delivered"}},
        "delivered": {"type": "final"}
    }
}

conn = init_db()
machine = create_machine(config)
interp = SyncInterpreter(machine).start()

interp.send("CONFIRM")
save_snapshot(conn, "order-42", interp)
interp.stop()

# --- Later ---
saved_json = load_snapshot(conn, "order-42")
if saved_json:
    machine = create_machine(config)
    restored = SyncInterpreter.from_snapshot(saved_json, machine)
    print(f"Restored state: {restored.current_state_ids}")
    # {'order-42.confirmed'}
    restored.send("SHIP")
    save_snapshot(conn, "order-42", restored)
    restored.stop()

conn.close()
```

## Async Snapshots

Snapshots work identically with the async `Interpreter`:

```python
import asyncio
from xstate_statemachine import create_machine, Interpreter

config = {
    "id": "asyncWorkflow",
    "initial": "phase1",
    "context": {"results": []},
    "states": {
        "phase1": {"on": {"ADVANCE": "phase2"}},
        "phase2": {"on": {"ADVANCE": "phase3"}},
        "phase3": {"type": "final"}
    }
}

async def main():
    machine = create_machine(config)
    interp = await Interpreter(machine).start()

    await interp.send("ADVANCE")
    await asyncio.sleep(0.1)  # Let the event process

    # Capture snapshot (synchronous method — no await needed)
    snapshot = interp.get_snapshot()
    await interp.stop()

    # Restore into an async interpreter
    machine = create_machine(config)
    restored = Interpreter.from_snapshot(snapshot, machine)
    print(restored.current_state_ids)  # {'asyncWorkflow.phase2'}
    print(restored.status)  # 'running'

asyncio.run(main())
```

## Testing with Snapshots

Snapshots are powerful for testing because they let you jump directly to a specific state without replaying the full event sequence:

```python
import json
from xstate_statemachine import create_machine, SyncInterpreter, MachineLogic

config = {
    "id": "checkout",
    "initial": "cart",
    "context": {"items": [], "total": 0, "payment_status": None},
    "states": {
        "cart": {"on": {"PROCEED": "shipping"}},
        "shipping": {"on": {"CONFIRM_ADDRESS": "payment"}},
        "payment": {
            "on": {
                "PAY": {"target": "processing", "actions": "startPayment"}
            }
        },
        "processing": {
            "on": {
                "SUCCESS": "confirmed",
                "FAILURE": "payment"
            }
        },
        "confirmed": {"type": "final"}
    }
}

logic = MachineLogic(
    actions={
        "startPayment": lambda i, ctx, e, a: ctx.update(
            {"payment_status": "processing"}
        )
    }
)

# --- Test: Jump directly to the payment state ---
def test_payment_flow():
    """Test the payment flow without navigating through cart and shipping."""
    # Create a snapshot that puts us directly in the payment state
    snapshot = json.dumps({
        "status": "running",
        "context": {
            "items": [{"name": "Widget", "price": 29.99}],
            "total": 29.99,
            "payment_status": None
        },
        "state_ids": ["checkout.payment"]
    })

    machine = create_machine(config, logic=logic)
    interp = SyncInterpreter.from_snapshot(snapshot, machine)

    # Test: send PAY event
    interp.send("PAY")
    assert interp.context["payment_status"] == "processing"
    assert interp.current_state_ids == {"checkout.processing"}

    # Test: payment succeeds
    interp.send("SUCCESS")
    assert interp.current_state_ids == {"checkout.confirmed"}

    interp.stop()
    print("test_payment_flow PASSED")

def test_payment_failure_retry():
    """Test that payment failure returns to the payment state."""
    snapshot = json.dumps({
        "status": "running",
        "context": {"items": [], "total": 0, "payment_status": None},
        "state_ids": ["checkout.processing"]
    })

    machine = create_machine(config, logic=logic)
    interp = SyncInterpreter.from_snapshot(snapshot, machine)

    interp.send("FAILURE")
    assert interp.current_state_ids == {"checkout.payment"}

    interp.stop()
    print("test_payment_failure_retry PASSED")

test_payment_flow()
test_payment_failure_retry()
```

## Complete Example: Long-Running Workflow with Checkpointing

This pattern saves a snapshot after each step, enabling crash recovery:

```python
from pathlib import Path
from xstate_statemachine import create_machine, SyncInterpreter, MachineLogic

CHECKPOINT_FILE = Path("workflow_checkpoint.json")

config = {
    "id": "dataProcessing",
    "initial": "ingesting",
    "context": {
        "records_ingested": 0,
        "records_transformed": 0,
        "records_loaded": 0,
        "errors": []
    },
    "states": {
        "ingesting": {
            "on": {
                "INGEST_DONE": {"target": "transforming", "actions": "markIngested"}
            }
        },
        "transforming": {
            "on": {
                "TRANSFORM_DONE": {"target": "loading", "actions": "markTransformed"}
            }
        },
        "loading": {
            "on": {
                "LOAD_DONE": {"target": "complete", "actions": "markLoaded"}
            }
        },
        "complete": {"type": "final"}
    }
}

logic = MachineLogic(
    actions={
        "markIngested": lambda i, ctx, e, a: ctx.update(
            {"records_ingested": e.payload.get("count", 0)}
        ),
        "markTransformed": lambda i, ctx, e, a: ctx.update(
            {"records_transformed": e.payload.get("count", 0)}
        ),
        "markLoaded": lambda i, ctx, e, a: ctx.update(
            {"records_loaded": e.payload.get("count", 0)}
        ),
    }
)

def checkpoint(interp):
    """Save current state to disk after each step."""
    CHECKPOINT_FILE.write_text(interp.get_snapshot())
    print(f"Checkpoint saved: {interp.current_state_ids}")

def resume_or_start():
    """Resume from checkpoint if available, otherwise start fresh."""
    machine = create_machine(config, logic=logic)

    if CHECKPOINT_FILE.exists():
        saved = CHECKPOINT_FILE.read_text()
        print("Resuming from checkpoint...")
        return SyncInterpreter.from_snapshot(saved, machine)
    else:
        print("Starting fresh...")
        return SyncInterpreter(machine).start()

# --- Main workflow ---
interp = resume_or_start()
current = interp.current_state_ids

# Only process steps that haven't been completed
if "dataProcessing.ingesting" in current:
    print("Running ingest phase...")
    interp.send("INGEST_DONE", count=1500)
    checkpoint(interp)

if "dataProcessing.transforming" in interp.current_state_ids:
    print("Running transform phase...")
    interp.send("TRANSFORM_DONE", count=1450)
    checkpoint(interp)

if "dataProcessing.loading" in interp.current_state_ids:
    print("Running load phase...")
    interp.send("LOAD_DONE", count=1450)
    checkpoint(interp)

print(f"Final context: {interp.context}")
interp.stop()

# Clean up checkpoint on success
if CHECKPOINT_FILE.exists():
    CHECKPOINT_FILE.unlink()
    print("Checkpoint cleaned up.")
```

## Complete Example: Crash Recovery Pattern

```python
import json
import sys
from pathlib import Path
from xstate_statemachine import create_machine, SyncInterpreter, MachineLogic

class RecoverableWorkflow:
    """A workflow wrapper that automatically persists and recovers state."""

    def __init__(self, config, logic=None, storage_path="workflow_state.json"):
        self.config = config
        self.logic = logic
        self.storage_path = Path(storage_path)
        self.interp = None

    def start(self):
        """Start or resume the workflow."""
        machine = create_machine(self.config, logic=self.logic)

        if self.storage_path.exists():
            snapshot = self.storage_path.read_text()
            self.interp = SyncInterpreter.from_snapshot(snapshot, machine)
            print(f"Recovered workflow at state: {self.interp.current_state_ids}")
        else:
            self.interp = SyncInterpreter(machine).start()
            print(f"Started new workflow at state: {self.interp.current_state_ids}")

        return self

    def send(self, event_type, **payload):
        """Send an event and auto-save the state."""
        self.interp.send(event_type, **payload)
        self._save()
        return self

    def _save(self):
        """Persist current state to disk."""
        self.storage_path.write_text(self.interp.get_snapshot())

    def finish(self):
        """Stop the interpreter and clean up persistence."""
        self.interp.stop()
        if self.storage_path.exists():
            self.storage_path.unlink()
        print("Workflow completed and cleaned up.")

    @property
    def state(self):
        return self.interp.current_state_ids

    @property
    def context(self):
        return self.interp.context

# Usage
config = {
    "id": "deploy",
    "initial": "building",
    "context": {"version": "1.2.3", "status": "pending"},
    "states": {
        "building": {"on": {"BUILD_OK": "testing"}},
        "testing": {"on": {"TESTS_PASS": "deploying", "TESTS_FAIL": "failed"}},
        "deploying": {"on": {"DEPLOY_OK": "done"}},
        "done": {"type": "final"},
        "failed": {"type": "final"}
    }
}

workflow = RecoverableWorkflow(config).start()
workflow.send("BUILD_OK")
print(f"State: {workflow.state}")  # {'deploy.testing'}

# If the process crashes here, the next run will resume at 'testing'

workflow.send("TESTS_PASS")
workflow.send("DEPLOY_OK")
workflow.finish()
```
