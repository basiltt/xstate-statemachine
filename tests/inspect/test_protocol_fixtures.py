"""Our messages vs the fixtures recorded from `@statelyai/inspect` (#274)."""

from __future__ import annotations

import asyncio

import pytest

from .conftest import recorded


def _run_sync(machine, **kw):
    from src.xstate_statemachine import SyncInterpreter
    from src.xstate_statemachine.inspect import InspectorPlugin, MemorySink

    sink = MemorySink()
    plugin = InspectorPlugin(sink, **kw).install()
    try:
        i = SyncInterpreter(machine).start()
        i.send("GO")
        i.stop()
    finally:
        plugin.uninstall()
    return sink.messages


def _run_async(machine, **kw):
    from src.xstate_statemachine import Interpreter
    from src.xstate_statemachine.inspect import InspectorPlugin, MemorySink

    sink = MemorySink()
    plugin = InspectorPlugin(sink, **kw).install()

    async def go():
        i = await Interpreter(machine).start()
        await i.send("GO", wait=True)
        for _ in range(200):
            if i.value == "c":
                break
            await asyncio.sleep(0.01)
        await i.stop()

    try:
        asyncio.run(go())
    finally:
        plugin.uninstall()
    return sink.messages


def _type_shape(value):
    if value is None:
        return "null"
    return type(value).__name__


def _role(session, root):
    if session is None:
        return None
    return "root" if session == root else "child"


def _sequence(messages):
    """(kind, event type, receiver role, sender role) per message."""
    if not messages:
        return []
    root = messages[0]["sessionId"]
    out = []
    for m in messages:
        ev = (m.get("event") or {}).get("type")
        out.append(
            (
                m["type"],
                ev,
                _role(m["sessionId"], root),
                _role(m.get("sourceId"), root),
            )
        )
    return out


class TestRecordedFixtures:
    def test_fixture_has_provenance(self):
        prov = recorded()["_provenance"]
        assert prov["package"].startswith("@statelyai/inspect@")
        assert prov["xstate"].startswith("xstate@")
        assert "record.mjs" in prov["recorded_with"]

    @pytest.mark.parametrize("engine", ["sync", "async"])
    def test_key_sets_and_value_types_match(self, family, engine):
        ours = (_run_sync if engine == "sync" else _run_async)(family)
        theirs = recorded()["messages"]
        volatile = set(recorded()["_provenance"]["volatile_fields"])
        for kind in ("@xstate.actor", "@xstate.event", "@xstate.snapshot"):
            ref = [m for m in theirs if m["type"] == kind]
            got = [m for m in ours if m["type"] == kind]
            assert got, kind
            # every key the JS package EVER emits for this kind; optional
            # ones (parentId, sourceId) may be absent, exactly as in JS
            ref_keys = set().union(*(m.keys() for m in ref))
            always = set.intersection(*(set(m) for m in ref))
            for m in got:
                assert set(m) <= ref_keys, (kind, set(m) - ref_keys)
                assert always <= set(m), (kind, always - set(m))
                for key in m:
                    sample = next(r[key] for r in ref if key in r)
                    if key in volatile and sample is not None:
                        assert isinstance(m[key], type(sample)), key
                    else:
                        assert _type_shape(m[key]) == _type_shape(sample), (
                            kind,
                            key,
                        )
            if kind != "@xstate.event":
                snap_keys = set(ref[0]["snapshot"])
                for m in got:
                    assert set(m["snapshot"]) == snap_keys

    @pytest.mark.parametrize("engine", ["sync", "async"])
    def test_sequence_matches_the_recording(self, family, engine):
        ours = (_run_sync if engine == "sync" else _run_async)(family)
        theirs = recorded()["messages"]
        # actor registrations first (parent, then child with parentId)
        assert [m["type"] for m in ours[:2]] == ["@xstate.actor"] * 2
        assert ours[1]["parentId"] == ours[0]["sessionId"]
        assert theirs[1]["parentId"] == theirs[0]["sessionId"]

        # the event traffic -- who sent what to whom -- is identical.
        # 📝 One ordering difference, by engine design: an `invoke`d child
        #    starts DURING the parent's initial entry here, so the child's
        #    `xstate.init` is reported before the parent's (XState reports
        #    the parent first). The init events are compared as a set; all
        #    later traffic in order.
        def split(seq):
            init = sorted(s for s in seq if s[1] == "xstate.init")
            rest = [s for s in seq if s[1] != "xstate.init"]
            return init, rest

        ev = split([s for s in _sequence(ours) if s[0] == "@xstate.event"])
        ref = split([s for s in _sequence(theirs) if s[0] == "@xstate.event"])
        assert ev == ref
        # every processed event is followed by a snapshot for its receiver
        snaps = sorted(
            s for s in _sequence(ours) if s[0] == "@xstate.snapshot"
        )
        ref_snaps = sorted(
            s for s in _sequence(theirs) if s[0] == "@xstate.snapshot"
        )
        assert snaps == ref_snaps
        # final values agree
        final = [
            m["snapshot"]["value"]
            for m in ours
            if m["type"] == "@xstate.snapshot"
            and m["sessionId"] == ours[0]["sessionId"]
        ]
        assert final[-1] == "c"

    def test_definition_is_the_machine_config_json(self, family):
        import json

        msgs = _run_sync(family)
        actor = msgs[0]
        definition = json.loads(actor["definition"])
        assert definition["id"] == "parent"
        assert "states" in definition
        assert actor["name"] == "parent"
        assert msgs[1]["name"] == "kid"  # invoke id, as in the recording


class TestRedaction:
    def test_context_is_deny_by_default(self, family):
        msgs = _run_sync(family)
        for m in msgs:
            if "snapshot" in m:
                assert m["snapshot"]["context"] == {}

    def test_allowlist_passes_only_listed_keys_and_redacts(self, family):
        msgs = _run_sync(family, context_allowlist=["count", "api_token"])
        snap = next(
            m
            for m in msgs
            if m["type"] == "@xstate.snapshot"
            and m["sessionId"] == msgs[0]["sessionId"]
        )
        assert snap["snapshot"]["context"] == {
            "count": 0,
            "api_token": "***",
        }
        assert "email" not in str(msgs)

    def test_payloads_dropped_unless_opted_in(self, family):
        from src.xstate_statemachine import SyncInterpreter
        from src.xstate_statemachine.inspect import (
            InspectorPlugin,
            MemorySink,
        )

        for include, expect in (
            (False, {"type": "GO"}),
            (True, {"type": "GO", "n": 1, "password": "***"}),
        ):
            sink = MemorySink()
            i = SyncInterpreter(family).use(
                InspectorPlugin(sink, include_payloads=include)
            )
            i.start()
            i.send("GO", n=1, password="hunter2")
            i.stop()
            ev = next(
                m
                for m in sink.messages
                if m["type"] == "@xstate.event" and m["event"]["type"] == "GO"
            )
            assert ev["event"] == expect


def test_on_event_sent_fires_on_both_engines(family):
    from src.xstate_statemachine import (
        Interpreter,
        PluginBase,
        SyncInterpreter,
        plugins,
    )

    seen = []

    class P(PluginBase):
        def on_event_sent(self, interp, target_id, event):
            seen.append((interp.id, target_id, event.type))

    p = P()
    plugins.register_global(p)
    try:
        s = SyncInterpreter(family).start()
        s.send("GO")
        s.stop()
        sync_seen, seen[:] = list(seen), []

        async def go():
            a = await Interpreter(family).start()
            await a.send("GO", wait=True)
            for _ in range(200):
                if a.value == "c":
                    break
                await asyncio.sleep(0.01)
            await a.stop()

        asyncio.run(go())
    finally:
        plugins.unregister_global(p)
    for got in (sync_seen, seen):
        assert ("parent", "parent:kid", "PING") in got
        assert ("parent:kid", "parent", "PONG") in got


def test_raising_on_event_sent_is_contained(family):
    from src.xstate_statemachine import PluginBase, SyncInterpreter

    class Bad(PluginBase):
        def on_event_sent(self, interp, target_id, event):
            raise RuntimeError("boom")

    i = SyncInterpreter(family).use(Bad()).start()
    i.send("GO")
    assert i.value == "b" or i.value == "c"
    assert i.last_plugin_error[1] == "on_event_sent"
    i.stop()
