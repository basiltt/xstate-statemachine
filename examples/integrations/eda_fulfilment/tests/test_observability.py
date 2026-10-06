"""Prometheus, OpenTelemetry and the inspector over the choreography."""

import pytest

from xstate_statemachine import SyncInterpreter
from xstate_statemachine.inspect import MemorySink, replay_messages


def _run(fulfilment):
    fulfilment.command("o-1", "PAY", orderId="o-1", total=10)
    fulfilment.command("o-2", "PAY", orderId="o-2", total=20)
    fulfilment.pump()


def test_prometheus_counters_and_label_allow_list(fulfilment):
    pytest.importorskip("prometheus_client")
    _run(fulfilment)
    text = fulfilment.instruments.metrics_text()
    assert "xstatemachine_transitions_total{" in text
    assert "xstatemachine_events_received_total{" in text
    assert "xstatemachine_active_interpreters" in text
    assert 'machine="order"' in text and 'machine="warehouse"' in text
    # 🔐 no business key, payload value or envelope id becomes a label.
    for leak in ("o-1", "o-2", "TRK-", "orderId", "trackingId"):
        assert leak not in text, leak
    for cmd in fulfilment.commands:
        assert cmd.id not in text
    assert fulfilment.instruments.transitions_total() > 0


def test_otel_spans_per_event(fulfilment):
    pytest.importorskip("opentelemetry.sdk")
    _run(fulfilment)
    spans = fulfilment.instruments.spans.get_finished_spans()
    assert {s.name for s in spans} == {
        "statechart.transition",
        "statechart.service",  # the shipOrder invoke
    }
    events = {
        s.attributes["statechart.event.type"]
        for s in spans
        if s.name == "statechart.transition"
    }
    assert {"PAY", "PACK", "PACKED"} <= events
    for s in spans:
        assert "o-1" not in str(dict(s.attributes))


def test_inspector_messages_replay_to_the_same_state(fulfilment):
    _run(fulfilment)
    msgs = fulfilment.instruments.inspector.messages
    kinds = {m["type"] for m in msgs}
    assert kinds == {"@xstate.actor", "@xstate.event", "@xstate.snapshot"}
    # 🔐 only allow-listed context keys leave the process.
    for m in msgs:
        ctx = (m.get("snapshot") or {}).get("context") or {}
        assert set(ctx) <= {"orderId", "total", "trackingId"}

    # ⏪ Replay the recording into a fresh sink ...
    copy = MemorySink()
    assert replay_messages(msgs, copy) == len(msgs)
    assert copy.messages == msgs
    # ... and re-drive the order chart with the recorded events: same end.
    events = [
        m["event"]
        for m in msgs
        if m["type"] == "@xstate.event"
        and m["sessionId"] == "order:o-1"  # #274: one session per order
        and not m["event"]["type"].startswith(("xstate.", "done.invoke"))
    ]
    import app

    interp = SyncInterpreter(app.order_machine()).start()
    last = None
    for ev in events:
        payload = {k: v for k, v in ev.items() if k != "type"}
        interp.send(ev["type"], **payload)
        if ev["type"] == "PACKED":
            last = sorted(interp.current_state_ids)
            break
    final = [
        m["snapshot"]["value"]
        for m in msgs
        if m["type"] == "@xstate.snapshot" and m["sessionId"] == "order:o-1"
    ][-1]
    assert last == ["order.shipped"] and final == "shipped"
    interp.stop()
