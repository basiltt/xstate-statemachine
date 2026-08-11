---
title: "CLI Code Generator"
description: "Generate production-ready Python from XState JSON with the xsm command."
---

# CLI Code Generator

The `xsm` CLI tool generates production-ready Python code from XState JSON machine configurations. Instead of manually writing boilerplate action stubs, guard functions, service handlers, and interpreter bootstrap code, you export your machine from [Stately.ai](https://stately.ai) (or write JSON by hand) and let `xsm` scaffold everything for you.

The generated code includes type hints, docstrings, error handling, logging, and is ready to run immediately.

## What Is the CLI?

The CLI is a code generator that reads one or more XState-compatible JSON machine definitions and produces Python source files. It bridges the gap between visual state machine design and production Python code.

**What it does NOT do:** The CLI does not run your state machine. It generates the Python files that you then execute with `python`.

## Basic Usage

```bash
# Generate 2 files: logic + runner (default)
xsm generate-template my_machine.json

# Short alias — identical behavior
xsm gt my_machine.json
```

This produces two files alongside `my_machine.json`:

```
my_machine_logic.py    # Action, guard, and service stubs
my_machine_runner.py   # Interpreter bootstrap + event simulation
```

> **Tip:** If the `xsm` command is not found after installing the package, use `python -m xstate_statemachine.cli` instead. See [CLI Troubleshooting](#using-python--m-if-xsm-is-not-found) below.

## What Gets Generated

### Logic File (`*_logic.py`)

The logic file contains stub implementations for every action, guard, and service referenced in your JSON config. Depending on the template you choose, these are either:

- **Methods on a class** (templates: `pythonic-class`, `class-json`)
- **Module-level functions** (templates: `pythonic-builder`, `pythonic-functional`, `function-json`)

Each stub includes:

- Correct function signature with type hints
- Rich docstring explaining the component
- Logging statement (if `--log yes`)
- Error handling with try/except (for actions and services)
- A `# TODO: implement` marker for you to fill in

### Runner File (`*_runner.py`)

The runner file contains everything needed to instantiate and run your state machine:

- JSON config loading (or Pythonic API construction, depending on template)
- Logic binding (class instance or module reference)
- Interpreter creation and startup
- Event simulation loop with all events found in your config
- Graceful shutdown

You can run it immediately:

```bash
python my_machine_runner.py
```

## All CLI Options

```
xsm generate-template [JSON_FILES...] [OPTIONS]
```

### Complete Options Reference

| Flag | Long Form | Type | Default | Description |
|------|-----------|------|---------|-------------|
| *(positional)* | `json_files` | `FILE...` | — | One or more JSON config files to process |
| `-j` | `--json` | `FILE` | — | Additional JSON input file (repeatable) |
| `-jp` | `--json-parent` | `FILE` | — | Designate the parent machine for hierarchy |
| `-jc` | `--json-child` | `FILE` | — | Designate child machine(s) for hierarchy (repeatable) |
| `-t` | `--template` | `CHOICE` | `class-json` | Code generation template (see below) |
| `-s` | `--style` | `CHOICE` | — | **DEPRECATED** — use `--template` instead |
| `-o` | `--output` | `DIR` | *(same as JSON)* | Output directory for generated files |
| `-fc` | `--file-count` | `{1, 2}` | `2` | Number of output files: 1 = merged, 2 = separate |
| `-f` | `--force` | flag | `false` | Overwrite existing files without prompting |
| `-am` | `--async-mode` | `yes/no` | *(template-dependent)* | Generate async or sync code |
| `-l` | `--loader` | `yes/no` | `yes` | Use LogicLoader auto-discovery in runner |
| — | `--log` | `yes/no` | `yes` | Include logging statements in generated code |
| — | `--sleep` | `yes/no` | `yes` | Add sleep calls between events in simulation |
| — | `--sleep-time` | `INT` | `2` | Sleep duration in seconds between events |
| — | `--check` | flag | `false` | Write nothing; exit 1 if files on disk are out of date |
| — | `--diff` | flag | `false` | Like `--check`, plus a unified diff. Implies `--check` |
| — | `--no-verify` | flag | `false` | Skip the structural fidelity check (syntax is still checked) |
| `-v` | `--version` | flag | — | Show version number and exit |

### Option Details

#### Template (`-t` / `--template`)

Five templates are available:

| Template | Description |
|----------|-------------|
| `pythonic-class` | `StateMachine` subclass with `@action` / `@guard` / `@service` decorators |
| `pythonic-builder` | `MachineBuilder` fluent chain with decorated module-level functions |
| `pythonic-functional` | `State` objects + `build_machine()` call with decorated functions |
| `class-json` | Class with camelCase methods, JSON loaded at runtime *(default)* |
| `function-json` | Module-level functions, JSON loaded at runtime |

> **Note:** The `--style` flag (`class` / `function`) is deprecated and maps to `class-json` / `function-json`. It will be removed in v0.8.0. Use `--template` instead.

#### Async Mode (`-am` / `--async-mode`)

Controls whether the generated code uses `async def` / `await` or plain `def`:

- **Default for JSON templates** (`class-json`, `function-json`): `yes` (async)
- **Default for Pythonic templates** (`pythonic-class`, `pythonic-builder`, `pythonic-functional`): `no` (sync)

```bash
# Force sync mode on a JSON template
xsm gt machine.json --template class-json --async-mode no

# Force async mode on a Pythonic template
xsm gt machine.json --template pythonic-class --async-mode yes
```

#### File Count (`-fc` / `--file-count`)

- `2` (default): Generates separate `*_logic.py` and `*_runner.py` files
- `1`: Merges everything into a single `*.py` file with de-duplicated imports

```bash
# Single merged file
xsm gt machine.json --file-count 1
```

## Template Selection Guide

Choosing the right template depends on your project needs:

| Criterion | `pythonic-class` | `pythonic-builder` | `pythonic-functional` | `class-json` | `function-json` |
|-----------|:---:|:---:|:---:|:---:|:---:|
| JSON needed at runtime | No | No | No | Yes | Yes |
| Logic in a class | Yes | No | No | Yes | No |
| Type hints | Full | Full | Full | Full | Full |
| Decorators (`@action`, etc.) | Yes | Yes | Yes | No | No |
| OOP pattern | Subclass | Builder | Functional | Provider | Module |
| Best for large machines | Yes | Yes | Moderate | Yes | Moderate |
| Default async mode | sync | sync | sync | async | async |

**Recommendations:**

- **New projects** → `pythonic-class` (most Pythonic, no JSON at runtime)
- **Dynamic assembly** → `pythonic-builder` (fluent API, easy to extend)
- **Simple scripts** → `pythonic-functional` (minimal boilerplate)
- **Existing JSON workflows** → `class-json` (keeps JSON as source of truth)
- **Lightweight / prototyping** → `function-json` (no class overhead)

## Common Recipes

### Sync Mode for Scripts

```bash
xsm gt machine.json --template pythonic-class --async-mode no
```

Generates `SyncInterpreter` usage instead of `Interpreter` + `asyncio.run()`.

### Single Merged File

```bash
xsm gt machine.json --template pythonic-functional --file-count 1
```

Produces a single `machine.py` with logic and runner combined. Imports are de-duplicated automatically.

### No Logging, No Sleep

```bash
xsm gt machine.json --template pythonic-class --log no --sleep no
```

Generates clean, minimal code without `logger.info()` calls or `time.sleep()` between events. Useful for production code where you want to add your own logging.

### Force Overwrite + Custom Output Directory

```bash
xsm gt machine.json -o ./generated/ --force
```

Writes to `./generated/` and overwrites any existing files without prompting.

### Multiple JSON Files

```bash
xsm gt auth.json profile.json settings.json
```

Generates combined logic and runner files that wire up all three machines. The CLI will interactively ask you to confirm which machine is the parent if it detects `invoke` configurations.

### Using with `python -m` If `xsm` Not Found

```bash
python -m xstate_statemachine.cli generate-template my_machine.json
python -m xstate_statemachine.cli gt my_machine.json --template pythonic-class
```

This is functionally identical to `xsm` and works even if the entry point script is not on your PATH.

## Workflow: From Design to Running Code

The recommended workflow integrates the CLI into a design-first approach:

```
┌─────────────────────┐
│  1. Design machine  │  Use Stately.ai visual editor
│     in Stately.ai   │  or write JSON by hand
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  2. Export JSON      │  Download the XState JSON config
│                      │  from Stately.ai
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  3. Generate Python  │  xsm gt my_machine.json
│     with CLI         │  --template pythonic-class
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  4. Implement logic  │  Fill in TODO stubs in
│                      │  my_machine_logic.py
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  5. Run & iterate    │  python my_machine_runner.py
│                      │
└─────────────────────┘
```

## Complete Walkthrough: From JSON to Running Machine

Let's walk through the entire process end-to-end.

### Step 1: Create or Export Your JSON Config

Save this as `checkout.json`:

```json
{
  "id": "checkout",
  "initial": "cart",
  "context": { "items": [], "total": 0 },
  "states": {
    "cart": {
      "on": {
        "SUBMIT": {
          "target": "payment",
          "guard": "cartNotEmpty",
          "actions": "calculateTotal"
        }
      }
    },
    "payment": {
      "invoke": {
        "src": "processPayment",
        "onDone": { "target": "confirmed", "actions": "clearCart" },
        "onError": { "target": "cart", "actions": "showError" }
      }
    },
    "confirmed": {
      "type": "final"
    }
  }
}
```

### Step 2: Generate Python Code

```bash
xsm gt checkout.json --template pythonic-class --async-mode no
```

Output:

```
Generated logic file:  checkout_logic.py
Generated runner file: checkout_runner.py
```

### Step 3: Review the Generated Logic File

Open `checkout_logic.py` and you'll find a `StateMachine` subclass with:

- `State()` declarations for `cart`, `payment`, and `confirmed`
- Transition definitions with guard and action references
- `@action` decorated methods for `calculateTotal`, `clearCart`, and `showError`
- `@guard` decorated method for `cartNotEmpty`
- `@service` decorated method for `processPayment`

### Step 4: Implement Your Business Logic

Fill in the `# TODO` stubs with your actual business logic:

```python
@guard
def cart_not_empty(self, context, event) -> bool:
    """Guard: cartNotEmpty — check if the cart has items."""
    return len(context.get("items", [])) > 0

@action
def calculate_total(self, interpreter, context, event, action_def) -> None:
    """Action: calculateTotal — sum up item prices."""
    context["total"] = sum(item["price"] for item in context["items"])

@service
def process_payment(self, interpreter, context, event) -> dict:
    """Service: processPayment — charge the customer."""
    # Call your payment gateway here
    return {"result": "payment_success", "transaction_id": "txn_123"}
```

### Step 5: Run the Machine

```bash
python checkout_runner.py
```

The runner will start the interpreter, send the `SUBMIT` event, invoke the payment service, and transition through the machine states with full logging output.

> **Tip:** After initial generation, you only edit the logic file. The runner file rarely needs changes unless you want custom event sequences.

## All Commands Overview

The `xsm` CLI provides four commands:

```
xsm [-h] [-v]
    {generate-template,gt,list-templates,lt,validate,val,info} ...
```

| Command | Alias | Description |
|---------|-------|-------------|
| `generate-template` | `gt` | Generate Python code from an XState JSON file |
| `list-templates` | `lt` | List all available code generation templates |
| `validate` | `val` | Validate an XState JSON config file |
| `info` | — | Show library version, Python version, and feature summary |

## List Templates

Shows all available code generation templates with descriptions:

```bash
xsm list-templates
# or
xsm lt
```

Output:

```
Available Templates:

  Template                Description
  ----------------------  -------------------------------------------------------
  class-json              Class-based logic with JSON config loaded at runtime
  function-json           Function-based logic with JSON config loaded at runtime
  pythonic-class          StateMachine subclass with @action/@guard decorators
  pythonic-builder        MachineBuilder fluent API with decorated functions
  pythonic-functional     build_machine() with State objects and decorators

Use: xsm gt <json_file> --template <template_name>
```

## Validate

Validates that JSON files are well-formed XState machine configurations:

```bash
xsm validate my_machine.json
# or
xsm val my_machine.json

# Validate multiple files at once
xsm val auth.json profile.json settings.json
```

The validator checks:
- Valid JSON syntax
- Required fields (`id`, `initial`, `states`)
- State structure and transitions
- Reports all actions, guards, and services found in the config

Example output for a valid file:

```
Validating: checkout.json
  Machine ID:  checkout
  States:      cart, payment, confirmed
  Actions:     calculateTotal, clearCart, showError
  Guards:      cartNotEmpty
  Services:    processPayment
  Result:      ok

All 1 file(s) are valid.
```

## Info

Displays library version, Python version, platform, and feature summary:

```bash
xsm info
```

Example output:

```
xstate-statemachine info
  Version:     0.7.0
  Python:      3.12.0
  Platform:    Windows-11
  Install:     C:\...\xstate_statemachine
  Features:    Hierarchical states, Parallel states, Guards,
               Actions, Invoke/Services, Delayed transitions,
               Context, Snapshots, Plugins, Diagram export,
               Pythonic API, CLI code generator
  Homepage:    https://github.com/basiltt/xstate-statemachine
  Docs:        https://basiltt.github.io/xstate-statemachine/
```

## Version and Help

```bash
# Show version
xsm --version

# Show help
xsm --help
xsm generate-template --help
```

---

## Verification: The Generator Refuses to Lie

Since v0.7.0, `xsm` proves its output before writing it. For templates that
build the machine in Python (`pythonic-class`, `pythonic-builder`,
`pythonic-functional`) it:

1. compiles the generated module,
2. executes it and builds the machine,
3. compares that machine structurally against `create_machine(your.json)`.

If anything diverges, **nothing is written** and the command exits 1:

```
❌ Refusing to generate 'pythonic-builder' code for machine 'orders'.

The generated code would not faithfully reproduce the source machine:
  • state 'processing.payment' is missing from the generated code

Nothing was written. This is deliberate: emitting a machine that silently
differs from its source is worse than emitting nothing.
```

The `*-json` templates load your JSON at runtime, so their fidelity is exact by
construction — they get syntax validation only.

Use `--no-verify` to inspect output the generator refuses to write. It does not
disable syntax checking.

> **Why this exists:** before v0.7.0 nothing checked. Three templates shipped
> code that produced a *different machine* than the source described, and two of
> them did it silently with exit code 0. See the
> [changelog](changelog.md) for the details.

---

## Keeping Generated Code Honest in CI

Generated code is often committed so reviewers can see it and consumers don't
need the CLI. The risk is drift: someone edits the machine, forgets to
regenerate, and the repository now describes a machine that no longer exists.

`--check` catches that. It regenerates in memory and compares:

```bash
xsm generate-template order.json --template pythonic-builder --check
```

```
✓ Generated code is up to date.
```

Exit code is 1 when anything differs or is missing. Use `--diff` to see exactly
what changed:

```bash
xsm generate-template order.json --template pythonic-builder --diff
```

Both flags are strictly read-only — they never write, and never prompt for
overwrite confirmation, so they are safe in a non-interactive pipeline.

### GitHub Actions example

```yaml
- name: Verify generated machine code is current
  run: |
    xsm generate-template machines/order.json \
        --template pythonic-builder \
        --output src/machines \
        --check
```

---

## Reading Generated Files

Every generated file starts with a provenance header:

```python
"""Generated state machine logic — DO NOT EDIT BY HAND.

Source:    order.json
Template:  pythonic-builder
Generator: xstate-statemachine 0.7.0

Regenerate with::

    xsm generate-template order.json --template pythonic-builder

Implement your logic in the stubs below; the machine structure
above is derived from the source JSON and will be overwritten.
"""
```

The machine structure is derived from your JSON and **will be overwritten** on
regeneration. Your action, guard and service bodies are the parts you own — keep
them in the logic file and treat the runner as disposable.

Generated code passes `black --check` and `pyflakes` cleanly, so it will not
add lint noise to your project.
