# Pythonic API Examples

The same machine — a download manager — expressed three ways, with **no JSON
needed at runtime**. Each directory was generated from
[`download_manager.json`](download_manager.json) and then verified to build a
machine structurally identical to it.

```bash
python class_style/download_manager_runner.py
python builder_style/download_manager_runner.py
python functional_style/download_manager_runner.py
```

## Which style?

| Style | Machine is defined | Reach for it when |
|:--|:--|:--|
| [`class_style`](class_style/) | class attributes on a `StateMachine` subclass | you want states and their logic in one namespace, with IDE autocomplete |
| [`builder_style`](builder_style/) | a fluent `MachineBuilder` chain | the machine's shape is decided at runtime, e.g. from config or a database |
| [`functional_style`](functional_style/) | `State` objects passed to `build_machine()` | you prefer plain data and explicit wiring |

All three compile to the same `MachineNode` and run on the same interpreters, so
the choice is about how the definition *reads*, not what it can do.

## What this machine exercises

Deliberately more than a toggle, because these are the features that used to be
dropped silently by the generator:

- **`invoke`** with `onDone` / `onError` — `fetchFile` decides the outcome
- **`after`** timers — a 30s timeout on `downloading`
- **guarded transitions** — `RETRY` only fires while `canRetry` allows it
- **`tags`** — `downloading` and `paused` are both `busy`, so a UI can show a
  spinner with one check instead of enumerating state ids
- **`meta`** — `failed` carries `{"alert": true}` for the UI layer
- **a final state** — `complete` ends the machine

## Regenerating

The `*_logic.py` files are generated. The machine structure in them is derived
from the JSON and **will be overwritten**; your action, guard and service bodies
are the parts you own.

```bash
xsm generate-template download_manager.json \
    --template pythonic-functional --async-mode no -o functional_style
```

Each file's header records the exact command that produced it.

> **Note:** the runners here are **hand-written** to tell a story, so they differ
> from what the CLI would emit. `--check` compares *both* generated files and
> will therefore report the runner as out of date — that is expected for this
> directory. In a project where both files are generated, `--check` exits 0 while
> the code matches its JSON and 1 once it drifts, which makes it a useful CI gate:
>
> ```bash
> xsm generate-template machine.json --template pythonic-builder -o src/ --check
> ```

