"""battle #274 (adversary B): JSON Lines, replay, page."""

import re
import threading
import urllib.request

import pytest

from xstate_statemachine.inspect import (
    JsonLinesSink,
    MemorySink,
    SseSink,
    read_jsonl,
    replay_messages,
)
from xstate_statemachine.inspect._page import APP_JS, INDEX_HTML

EV = "@xstate.event"


def _msgs(*ats):
    return [
        {"type": EV, "createdAt": str(a), "i": n} for n, a in enumerate(ats)
    ]


# ----------------------------------------------------------- JsonLinesSink
def test_eight_threads_never_interleave_lines(tmp_path):
    p = tmp_path / "r.jsonl"
    sink = JsonLinesSink(p)
    pad = "x" * 4000

    def work(t):
        for i in range(200):
            sink.send({"type": EV, "t": t, "i": i, "pad": pad})

    ts = [threading.Thread(target=work, args=(t,)) for t in range(8)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    sink.close()
    got = list(read_jsonl(p))
    assert len(got) == 1600
    assert {(m["t"], m["i"]) for m in got} == {
        (t, i) for t in range(8) for i in range(200)
    }


def test_lone_surrogate_is_written_and_round_trips(tmp_path):
    p = tmp_path / "r.jsonl"
    with JsonLinesSink(p) as sink:
        sink.send({"type": EV, "s": "\udcff café"})
        sink.send({"type": EV, "s": "next"})
    assert all(b < 128 for b in p.read_bytes())
    got = list(read_jsonl(p))
    assert [m["s"] for m in got] == ["\udcff café", "next"]


def test_send_after_close_raises_a_clear_error(tmp_path):
    sink = JsonLinesSink(tmp_path / "r.jsonl")
    sink.close()
    sink.close()  # idempotent
    with pytest.raises(ValueError, match="closed"):
        sink.send({"type": EV})


def test_missing_directory_fails_at_construction(tmp_path):
    with pytest.raises(FileNotFoundError):
        JsonLinesSink(tmp_path / "nope" / "r.jsonl")


def test_read_jsonl_is_lazy(tmp_path):
    p = tmp_path / "r.jsonl"
    p.write_text('{"type":"x"}\nnot json\n{}\n', encoding="utf-8")
    it = read_jsonl(p)
    assert next(it) == {"type": "x"}  # streamed: line 2 not read yet
    with pytest.raises(ValueError):
        next(it)


# ----------------------------------------------------------------- replay
def test_replay_accepts_a_pathlib_path(tmp_path):
    p = tmp_path / "r.jsonl"
    with JsonLinesSink(p) as s:
        for m in _msgs(1, 2):
            s.send(m)
    out = MemorySink()
    assert replay_messages(p, out) == 2
    assert replay_messages(str(p), out) == 2


@pytest.mark.parametrize("speed", [-1.0, float("nan")])
def test_replay_refuses_negative_or_nan_speed(speed):
    with pytest.raises(ValueError, match="speed"):
        replay_messages(_msgs(1), MemorySink(), speed=speed)


def test_replay_clock_step_backwards_never_sleeps_negative():
    naps = []
    n = replay_messages(
        _msgs(1000, 3000, 500, 1500),
        MemorySink(),
        speed=2.0,
        sleep=naps.append,
    )
    assert n == 4
    assert naps == [1.0, 0.5]


def test_replay_skips_unknown_types_and_bad_created_at():
    msgs = [{"type": "junk"}, {"type": EV, "createdAt": "abc"}]
    naps = []
    n = replay_messages(msgs, MemorySink(), speed=1, sleep=naps.append)
    assert n == 1
    assert naps == []


def test_replay_sink_error_propagates():
    def boom(m):
        raise RuntimeError("sink down")

    with pytest.raises(RuntimeError, match="sink down"):
        replay_messages(_msgs(1), boom)


# ------------------------------------------------------------------- page
def test_page_has_no_inline_script_and_pins_the_frame_origin():
    html = INDEX_HTML.decode()
    scripts = re.findall(r"<script([^>]*)>(.*?)</script>", html, re.S)
    assert scripts
    for attrs, body in scripts:
        assert 'src="/app.js"' in attrs and not body.strip()
    js = APP_JS.decode()
    assert "postMessage(msg, STATELY)" in js
    assert "'*'" not in js and '"*"' not in js
    assert "e.origin !== new URL(STATELY).origin" in js
    assert "new EventSource('/events')" in js
    assert "token" not in js.lower()


def test_served_page_csp_and_no_token_in_bodies():
    sink = SseSink(port=0).start()
    try:
        base = f"http://127.0.0.1:{sink.port}"
        hdrs = {"X-XSM-Token": sink.token}
        for path, ctype in (
            ("/", "text/html"),
            ("/app.js", "text/javascript"),
        ):
            req = urllib.request.Request(base + path, headers=hdrs)
            with urllib.request.urlopen(req, timeout=5) as r:
                body = r.read().decode()
                assert r.headers["Content-Type"].startswith(ctype)
                csp = r.headers["Content-Security-Policy"]
                assert "script-src 'self'" in csp
                assert "connect-src 'self'" in csp
                assert "frame-src https://stately.ai" in csp
                assert r.headers["X-Content-Type-Options"] == "nosniff"
                assert sink.token not in body
    finally:
        sink.close()


# -------------------------------------------------------- WebSocketSink
def test_websocket_sink_cuts_a_client_that_lags():
    pytest.importorskip("starlette")
    import asyncio

    from xstate_statemachine.contrib.starlette import inspector as wsmod

    sink = wsmod.WebSocketSink(max_queue=3)
    with pytest.raises(ValueError):
        wsmod.WebSocketSink(max_queue=0)

    async def scenario():
        loop = asyncio.get_running_loop()
        q = asyncio.Queue()
        sink._clients.append((loop, q))
        for i in range(10):
            sink.send({"type": EV, "i": i})
        await asyncio.sleep(0)
        return q

    q = asyncio.run(scenario())
    assert sink.dropped == 1
    assert sink._clients == []
    assert q.qsize() == 1 and q.get_nowait() is wsmod._CUT
    assert len(sink.messages) == 10  # history unaffected
