// tests/inspect/fixtures/record.mjs
// ---------------------------------------------------------------------------
// Records the REAL @statelyai/inspect wire messages that
// `stately_inspect_messages.json` pins (#274 spike).
//
// Regenerate (any scratch directory, NOT inside the repo):
//     npm init -y && npm i @statelyai/inspect xstate
//     cp <repo>/tests/inspect/fixtures/record.mjs . && node record.mjs
//     cp stately_inspect_messages.json <repo>/tests/inspect/fixtures/
// ---------------------------------------------------------------------------
import { createInspector } from "@statelyai/inspect";
import { createActor, createMachine, sendTo, sendParent } from "xstate";
import { writeFileSync, readFileSync } from "node:fs";

const events = [];
const inspector = createInspector({ send: (e) => events.push(e) });

const child = createMachine({
  id: "child",
  initial: "idle",
  states: {
    idle: {
      on: { PING: { target: "pinged", actions: sendParent({ type: "PONG" }) } },
    },
    pinged: {},
  },
});

const parent = createMachine({
  id: "parent",
  initial: "a",
  context: { count: 0 },
  invoke: { id: "kid", src: child },
  states: {
    a: { on: { GO: { target: "b", actions: sendTo("kid", { type: "PING" }) } } },
    b: { on: { PONG: "c" } },
    c: {},
  },
});

const actor = createActor(parent, { inspect: inspector.inspect });
actor.start();
actor.send({ type: "GO" });

setTimeout(() => {
  const pkg = JSON.parse(
    readFileSync("node_modules/@statelyai/inspect/package.json", "utf8")
  );
  const xs = JSON.parse(readFileSync("node_modules/xstate/package.json", "utf8"));
  const out = {
    _provenance: {
      package: `@statelyai/inspect@${pkg.version}`,
      xstate: `xstate@${xs.version}`,
      node: process.version,
      recorded_with:
        "tests/inspect/fixtures/record.mjs: createInspector({send}) " +
        "collecting adapter; parent invokes child, sendTo + sendParent",
      regenerate: "see header of record.mjs",
      volatile_fields: [
        "createdAt",
        "sessionId",
        "rootId",
        "parentId",
        "sourceId",
        "id",
      ],
    },
    messages: events,
  };
  writeFileSync("stately_inspect_messages.json", JSON.stringify(out, null, 2) + "\n");
  console.log("recorded", events.length);
}, 200);
