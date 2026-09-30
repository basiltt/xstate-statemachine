# tests/inspect/fixtures/README.md

`stately_inspect_messages.json` is **recorded from the real npm package**,
not hand-written:

| | |
|---|---|
| Package | `@statelyai/inspect@0.7.2` with `xstate@5.33.2` (see `_provenance` in the JSON) |
| Recorder | `record.mjs` in this folder: `createInspector({ send })` with a collecting adapter, a parent machine that `invoke`s a child, `sendTo` → child, child `sendParent` → parent |
| Recorded | 2026-09-30, Node v24 |

## Regenerate

In a scratch directory **outside** the repository:

```bash
npm init -y && npm i @statelyai/inspect xstate
cp <repo>/tests/inspect/fixtures/record.mjs .
node record.mjs
cp stately_inspect_messages.json <repo>/tests/inspect/fixtures/
```

## What the tests pin

`tests/inspect/test_protocol_fixtures.py` compares, per message kind, the
**key set** and the **value types** of our messages against the recording,
and the **sequence** of `(kind, event.type, receiver role, sender role)` for
the same parent/child scenario. Fields listed in `_provenance.volatile_fields`
(`createdAt`, session ids, `id`) are compared by type only.

Known, deliberate differences (asserted, not ignored):

- `snapshot.context` is `{}` unless the key is in `context_allowlist`
  (X0.7 deny-by-default); XState sends the full context.
- `snapshot.children` values are `{"id": ...}`; XState's actor-ref
  serialisation adds an internal `xstate$$type` marker the UI does not need.
- `@xstate.actor.snapshot` is captured at start (`value: {}`), where the JS
  recorder serialises the actor lazily and shows its *final* value.
