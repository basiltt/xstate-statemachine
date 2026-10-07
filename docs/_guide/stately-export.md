---
title: "Stately editor → Python"
description: "Export a machine from the Stately visual editor and run it with xstate-statemachine: export steps, the version key, meta conventions, xsm validate, the editor JSON Schema for VS Code, and the round trip."
---

# Stately editor → Python

Design the chart visually in the [Stately editor](https://stately.ai/editor), export it as JSON, and run that JSON with this library unchanged. Your Python code supplies only the actions, guards and services the chart names.

## Export

1. In the editor, open the machine and choose **Export** (the code icon) → **JSON**.
2. Save it next to your code as `<name>.machine.json` — the `.machine.json` suffix is what the [editor schema](#editor-schema-vs-code) and the [pre-commit hook](../cli/#in-ci-and-pre-commit) match.
3. Make sure the root has an `id`; add a `version` (below).
4. Run `xsm validate` on it.

The export is plain XState JSON: `id`, `initial`, `context`, `states`, `on`, `after`, `always`, `invoke`, `entry`/`exit`, guards, tags, `meta` and `description`. The exact set of keys this library implements is in [JSON config](../json-config/). A key it does not implement is a WARNING with a "did you mean" hint by default and an `InvalidConfigError` under `strictConfig: true` — never silently ignored.

## The `version` key

Add a root `"version"` whenever the chart changes shape:

```json
{ "id": "order", "version": "3", "initial": "cart", "states": { "cart": {} } }
```

The engine never interprets it, but it travels with every snapshot as `machine_version`, and loading a snapshot written by a different `version` is detected so an in-flight instance can be migrated instead of resumed against the wrong chart (see [Versioning in-flight instances](../persistence/#versioning-in-flight-instances)). The HTTP integrations also return it in every response body.

```python
from xstate_statemachine import create_machine

machine = create_machine({"id": "order", "version": 3, "initial": "cart",
                          "states": {"cart": {}}})
assert machine.version == "3"          # coerced to str; None when absent
```

## `meta`, `description` and `x-` keys

| Key | What the library does with it today |
|:--|:--|
| `description` (any state, transition, invoke) | Kept on the node; shown by `xsm inspect` and `xsm docs`. |
| `meta` (any state, transition, invoke) | Kept verbatim as a dict on the node (`machine.get_state_by_id(...).meta`); a non-object is an `InvalidConfigError`. It is not interpreted. |
| `tags` | Kept; queried with `interpreter.has_tag(...)`. |
| `x-…` (any level) | Your own namespace: accepted without a warning, never interpreted. |

Two `meta` conventions are read (both shipped in 0.11.0); every other `meta` key is kept and ignored:

- `meta.publish` (**shipped**) — on a transition, marks it as an integration event: `OutboxPlugin` publishes it and `xsm asyncapi` documents it ([Event-driven architecture](../integration-eda/#outbox), [#293](https://github.com/basiltt/xstate-statemachine/issues/293)). Broker adapters publish the same transitions ([Brokers](../integration-brokers/), [#294](https://github.com/basiltt/xstate-statemachine/issues/294)).
- `meta.tools` (**shipped**) — on a state, the tools an LLM agent may call there; `run_tool` enforces the allow-list ([LLM agents](../integration-agents/), `[agents]` extra, [#287](https://github.com/basiltt/xstate-statemachine/issues/287)).

Any other `meta` key is harmless: kept verbatim and never interpreted.

<!-- doc-fragment -->
```python
state = machine.get_state_by_id("order.cart")
state.meta          # {} or whatever the editor exported
```

## Validate after every export

```bash
xsm validate order.machine.json
```

`xsm validate` builds each file with the real library and lists the logic it needs (actions, guards, services, delays). It exits 1 on any error, so it belongs in CI — use the [`xsm-check` GitHub Action](../cli/#in-ci-and-pre-commit) or the pre-commit hook. `xsm inspect` renders the tree; `xsm diagram` gives you Mermaid back to compare with the editor.

## Editor schema (VS Code)

The repository publishes [`schemas/xstate-machine.schema.json`](https://github.com/basiltt/xstate-statemachine/blob/main/schemas/xstate-machine.schema.json), generated from the same model `validate_machine_json()` uses (`[pydantic]` extra) and regenerated in CI so it cannot drift. Associate it with your machine files in `.vscode/settings.json` for completion and red squiggles while editing JSON by hand:

```json
{
  "json.schemas": [
    {
      "fileMatch": ["*.machine.json"],
      "url": "https://raw.githubusercontent.com/basiltt/xstate-statemachine/main/schemas/xstate-machine.schema.json"
    }
  ]
}
```

The schema checks structure (key names, types, `initial` naming a child). What only the engine can know — targets that resolve, logic that exists — is `xsm validate`'s job.

## The round trip

1. Edit in the Stately editor.
2. Export over `<name>.machine.json`, bump `version` if the shape changed.
3. `xsm validate`, then `xsm gt --check` (with the flags you generated with) to see whether the generated code is stale; regenerate with `xsm gt` if so.
4. Commit the JSON and the generated code together.

To go the other way, paste the JSON file back into the editor (**Import** → JSON): the library never rewrites your machine file, so what you run is what the editor shows.
