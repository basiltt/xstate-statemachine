---
title: "Hierarchical Machine Generation"
description: "Generate parent-child machine code with the CLI — actor model code generation."
---

# Hierarchical Machine Generation

When your system involves a **parent machine** that orchestrates one or more **child machines** (the actor model), the CLI can generate wiring code that creates and manages all interpreters together. This page explains when and how to use hierarchical generation.

## When to Use Hierarchical Generation

Use hierarchical generation when:

- A parent machine **spawns child machines** via `invoke` with a machine source
- You have **multiple JSON files** representing different machines that work together
- You want the CLI to generate **bootstrap code** that starts the parent, spawns actors, simulates events on each, and shuts everything down gracefully

> **Note:** Hierarchical generation is about code generation structure — it does not change how the state machine library handles actors internally. The generated runner simply creates multiple interpreters and orchestrates them.

## Setup with `--json-parent` and `--json-child`

The most explicit way to declare hierarchy is with the `-jp` and `-jc` flags:

```bash
xsm gt --json-parent orchestrator.json --json-child payment.json --json-child shipping.json
```

This tells the CLI:

- `orchestrator.json` is the **parent** machine
- `payment.json` and `shipping.json` are **child** (actor) machines

The generated runner will:

1. Create the parent machine and interpreter
2. Load each child JSON and create child interpreters
3. Start all interpreters
4. Simulate events on the parent, then on each child
5. Shut down children first, then the parent

## Auto-Detection: How the CLI Guesses Hierarchy

When you pass multiple JSON files **without** explicit `-jp` / `-jc` flags, the CLI uses a heuristic to guess which machine is the parent:

```bash
xsm gt orchestrator.json payment.json shipping.json
```

The heuristic works by counting `invoke` occurrences in each JSON config. The machine with the most `invoke` blocks is likely the parent (since parents invoke child actors).

The CLI presents its guess and asks for confirmation:

```
Found 3 machines:
  1. orchestrator (looks like parent, score: 2)
  2. payment (looks like child, score: 0)
  3. shipping (looks like child, score: 0)
Is this correct? [Y/n]
```

- Press **Enter** or **Y** to accept
- Press **N** to manually select the parent from the list (or select `0` for no hierarchy)

> **Tip:** To skip the interactive prompt entirely, use explicit `--json-parent` and `--json-child` flags.

## Complete Example: Order Processing System

### JSON Files

**`order_orchestrator.json`** (parent):

```json
{
  "id": "orderOrchestrator",
  "initial": "pending",
  "context": { "orderId": null },
  "states": {
    "pending": {
      "on": {
        "START_ORDER": { "target": "processing", "actions": "assignOrderId" }
      }
    },
    "processing": {
      "invoke": { "src": "paymentActor" },
      "on": {
        "PAYMENT_DONE": { "target": "shipping" }
      }
    },
    "shipping": {
      "invoke": { "src": "shippingActor" },
      "on": {
        "SHIPPED": { "target": "complete" }
      }
    },
    "complete": { "type": "final" }
  }
}
```

**`payment.json`** (child):

```json
{
  "id": "payment",
  "initial": "idle",
  "states": {
    "idle": {
      "on": { "CHARGE": { "target": "charging", "actions": "initiateCharge" } }
    },
    "charging": {
      "invoke": {
        "src": "chargeCard",
        "onDone": { "target": "charged" },
        "onError": { "target": "failed" }
      }
    },
    "charged": { "type": "final" },
    "failed": {
      "on": { "RETRY": "idle" }
    }
  }
}
```

**`shipping.json`** (child):

```json
{
  "id": "shipping",
  "initial": "waiting",
  "states": {
    "waiting": {
      "on": { "DISPATCH": { "target": "dispatched", "actions": "createLabel" } }
    },
    "dispatched": {
      "on": { "DELIVER": "delivered" }
    },
    "delivered": { "type": "final" }
  }
}
```

### Generation Command

```bash
xsm gt \
  --json-parent order_orchestrator.json \
  --json-child payment.json \
  --json-child shipping.json \
  --template class-json \
  --async-mode no
```

### Generated Runner Structure

The generated `order_orchestrator_runner.py` follows this structure:

```python
from pathlib import Path
import json
from xstate_statemachine import create_machine, SyncInterpreter
from xstate_statemachine import LoggingInspector
import logging

from order_orchestrator_logic import OrderOrchestratorLogic as LogicProvider

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def main() -> None:
    """Run the parent machine and spawn actor machines."""
    root_dir = Path(__file__).parent
    parent_cfg = json.loads((root_dir / 'order_orchestrator.json').read_text())
    actor_cfgs = {
        'payment': json.loads((root_dir / 'payment.json').read_text()),
        'shipping': json.loads((root_dir / 'shipping.json').read_text()),
    }

    # -----------------------------------------------------------------------
    # Parent machine + logic binding
    # -----------------------------------------------------------------------
    logic_provider = LogicProvider()
    parent_machine = create_machine(parent_cfg, logic_providers=[logic_provider])
    parent = SyncInterpreter(parent_machine)
    parent.use(LoggingInspector())
    parent.start()
    logger.info('Parent started. Initial state(s): %s', parent.current_state_ids)

    # -------------------------------------------------------------------
    # Spawn & start every actor interpreter
    # -------------------------------------------------------------------
    actor_ctor = SyncInterpreter
    actors = {}
    machine_payment = create_machine(actor_cfgs['payment'])
    ai_payment = actor_ctor(machine_payment)
    ai_payment.use(LoggingInspector())
    ai_payment.start()
    actors['payment'] = ai_payment
    machine_shipping = create_machine(actor_cfgs['shipping'])
    ai_shipping = actor_ctor(machine_shipping)
    ai_shipping.use(LoggingInspector())
    ai_shipping.start()
    actors['shipping'] = ai_shipping

    # -------------------------------------------------------------------
    # Simulating Parent Machine
    # -------------------------------------------------------------------
    logger.info('Parent sending %s', 'PAYMENT_DONE')
    parent.send('PAYMENT_DONE')

    logger.info('Parent sending %s', 'SHIPPED')
    parent.send('SHIPPED')

    logger.info('Parent sending %s', 'START_ORDER')
    parent.send('START_ORDER')

    # -------------------------------------------------------------------
    # Simulating Actor: payment
    # -------------------------------------------------------------------
    logger.info('payment sending %s', 'CHARGE')
    actors['payment'].send('CHARGE')

    logger.info('payment sending %s', 'RETRY')
    actors['payment'].send('RETRY')

    # -------------------------------------------------------------------
    # Simulating Actor: shipping
    # -------------------------------------------------------------------
    logger.info('shipping sending %s', 'DELIVER')
    actors['shipping'].send('DELIVER')

    logger.info('shipping sending %s', 'DISPATCH')
    actors['shipping'].send('DISPATCH')

    # -------------------------------------------------------------------
    # Graceful shutdown of actors then parent
    # -------------------------------------------------------------------
    actors['payment'].stop()
    actors['shipping'].stop()
    parent.stop()

if __name__ == '__main__':
    main()
```

### What the Runner Does

1. **Loads all JSON configs** from the same directory as the runner script
2. **Creates the parent machine** with logic binding (class-based or module-based, depending on template)
3. **Creates child machines** from their JSON configs (without custom logic — you can add logic providers manually if needed)
4. **Starts all interpreters** — parent first, then children
5. **Simulates events** — sends all events found in each machine's config
6. **Shuts down gracefully** — children first, then parent

### The Logic File

The generated `order_orchestrator_logic.py` contains stubs for all actions, guards, and services found across **all** provided JSON configs. For child-specific logic, you may want to generate those separately:

```bash
# Generate logic for child machines separately
xsm gt payment.json --template class-json --async-mode no
xsm gt shipping.json --template class-json --async-mode no
```

## Output File Naming

When generating hierarchical code, the output files are named after the **parent** machine:

```
order_orchestrator_logic.py     # Logic stubs (parent + children)
order_orchestrator_runner.py    # Combined runner for parent + children
```

When generating non-hierarchical code with multiple JSON files, the names are joined:

```
auth_profile_settings_logic.py
auth_profile_settings_runner.py
```

## Pythonic Templates with Hierarchy

All 5 templates support hierarchical generation. The Pythonic templates use their native API for the parent machine, while child machines are always loaded from JSON via `create_machine()`:

```bash
# Parent uses StateMachine subclass, children load from JSON
xsm gt \
  --json-parent parent.json \
  --json-child child.json \
  --template pythonic-class \
  --async-mode no
```

The generated runner for `pythonic-class` creates the parent via:

```python
parent_machine = ParentMachine.create_machine()
```

While children are created via:

```python
machine_child = create_machine(child_cfg)
```

## Tips for Hierarchical Generation

1. **Use explicit flags for CI/CD:** In automated pipelines, always use `--json-parent` and `--json-child` to avoid interactive prompts.

2. **Generate child logic separately:** Run `xsm gt` on each child JSON individually if you need customized logic stubs for child machines.

3. **Customize the runner:** The generated runner sends events in alphabetical order for simulation. You'll want to customize the event sequence to match your actual workflow.

4. **Add logic to child machines:** To bind custom logic to child machines, modify the runner to pass `logic_providers` or `logic_modules` to child `create_machine()` calls.

5. **Force overwrite when regenerating:** Use `-f` / `--force` to regenerate without prompts:

    ```bash
    xsm gt --json-parent p.json --json-child c.json --force
    ```

6. **Only one `--json-parent` allowed:** The CLI validates that at most one parent is specified. Passing `-jp` twice will produce an error.
