"""JSON Lines + SSE sinks and their X0.7 hardening (#274)."""

from __future__ import annotations

import http.client
import json
import os
import stat
import sys
import threading
import time

import pytest


def _drive(sink, family):
    from src.xstate_statemachine import SyncInterpreter
    from src.xstate_statemachine.inspect import InspectorPlugin

    plugin = InspectorPlugin(sink).install()
    try:
        i = SyncInterpreter(family).start()
        i.send("GO")
        i.stop()
    finally:
        plugin.uninstall()


# =============================================================================
# JSON Lines
# =============================================================================
class TestJsonLines:
    def test_round_trip_and_mode_0600(self, family, tmp_path):
        from src.xstate_statemachine.inspect import (
            JsonLinesSink,
            MemorySink,
            read_jsonl,
            replay_messages,
        )

        path = tmp_path / "s.jsonl"
        with JsonLinesSink(path) as sink:
            _drive(sink, family)
        if sys.platform != "win32":
            assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
        msgs = list(read_jsonl(str(path)))
        assert [m["type"] for m in msgs][:2] == ["@xstate.actor"] * 2
        mem = MemorySink()
        assert replay_messages(str(path), mem) == len(msgs)
        assert mem.messages == msgs

    def test_replay_skips_non_protocol_lines_and_honours_speed(self, tmp_path):
        from src.xstate_statemachine.inspect import (
            MemorySink,
            replay_messages,
        )

        p = tmp_path / "x.jsonl"
        p.write_text(
            '{"type":"@xstate.event","createdAt":"1000","sessionId":"a",'
            '"event":{"type":"A"}}\n\n[1,2]\n{"type":"evil"}\n'
            '{"type":"@xstate.event","createdAt":"3000","sessionId":"a",'
            '"event":{"type":"B"}}\n',
            encoding="utf-8",
        )
        slept = []
        mem = MemorySink()
        n = replay_messages(str(p), mem, speed=2.0, sleep=slept.append)
        assert n == 2 and slept == [1.0]

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX modes")
    def test_existing_file_mode_untouched(self, tmp_path):
        from src.xstate_statemachine.inspect import JsonLinesSink

        p = tmp_path / "x.jsonl"
        p.write_text("")
        os.chmod(p, 0o640)
        JsonLinesSink(p).close()
        assert stat.S_IMODE(os.stat(p).st_mode) == 0o640


# =============================================================================
# SSE
# =============================================================================
def _get(sink, path, headers=None, host=None):
    conn = http.client.HTTPConnection("127.0.0.1", sink.port, timeout=5)
    h = {"Host": host or f"127.0.0.1:{sink.port}"}
    h.update(headers or {})
    conn.request("GET", path, headers=h)
    resp = conn.getresponse()
    body = resp.read() if resp.status != 200 or path != "/events" else b""
    return resp, body, conn


def _auth(sink):
    return {"Authorization": f"Bearer {sink.token}"}


class TestSse:
    def test_stream_receives_three_kinds_in_order(self, family):
        from src.xstate_statemachine.inspect import SseSink

        with SseSink() as sink:
            conn = http.client.HTTPConnection(
                "127.0.0.1", sink.port, timeout=5
            )
            conn.request(
                "GET",
                "/events",
                headers={
                    "Host": f"127.0.0.1:{sink.port}",
                    "X-XSM-Token": sink.token,
                },
            )
            resp = conn.getresponse()
            assert resp.status == 200
            assert resp.getheader("Content-Type") == "text/event-stream"
            got = []
            done = threading.Event()

            def read():
                while len(got) < 12:
                    line = resp.fp.readline()
                    if not line:
                        break
                    if line.startswith(b"data: "):
                        got.append(json.loads(line[6:]))
                done.set()

            t = threading.Thread(target=read, daemon=True)
            t.start()
            time.sleep(0.1)
            _drive(sink, family)
            done.wait(5)
            conn.close()
        kinds = [m["type"] for m in got]
        first = {k: kinds.index(k) for k in set(kinds)}
        assert (
            first["@xstate.actor"]
            < first["@xstate.event"]
            < first["@xstate.snapshot"]
        )
        assert len(got) == 12

    def test_late_client_gets_the_backlog_and_messages_endpoint(self, family):
        from src.xstate_statemachine.inspect import SseSink

        with SseSink() as sink:
            _drive(sink, family)
            resp, body, _ = _get(sink, "/messages", _auth(sink))
            assert resp.status == 200
            assert len(json.loads(body)) == 12

    def test_page_first_load_sets_cookie_and_redirects(self):
        from src.xstate_statemachine.inspect import COOKIE_NAME, SseSink

        with SseSink() as sink:
            resp, _, _ = _get(sink, f"/?token={sink.token}")
            assert resp.status == 303
            assert resp.getheader("Location") == "/"
            cookie = resp.getheader("Set-Cookie")
            assert f"{COOKIE_NAME}={sink.token}" in cookie
            assert "HttpOnly" in cookie and "SameSite=Strict" in cookie
            page, body, _ = _get(
                sink, "/", {"Cookie": f"{COOKIE_NAME}={sink.token}"}
            )
            assert page.status == 200
            csp = page.getheader("Content-Security-Policy")
            assert "default-src 'none'" in csp
            assert "script-src 'self'" in csp
            assert "frame-ancestors 'none'" in csp
            assert b'<script src="/app.js">' in body
            assert b"<script>" not in body  # no inline script
            js, jbody, _ = _get(
                sink, "/app.js", {"Cookie": f"{COOKIE_NAME}={sink.token}"}
            )
            assert js.status == 200 and b"@statelyai.connected" in jbody
            bad, _, _ = _get(sink, "/?token=nope")
            assert bad.status == 401

    def test_token_required_everywhere(self):
        from src.xstate_statemachine.inspect import SseSink

        with SseSink() as sink:
            for path in ("/", "/events", "/messages", "/app.js"):
                resp, _, _ = _get(sink, path)
                assert resp.status == 401, path
            resp, _, _ = _get(sink, "/messages", {"X-XSM-Token": "wrong"})
            assert resp.status == 401
            resp, _, _ = _get(sink, "/nope", _auth(sink))
            assert resp.status == 404
            resp, _, _ = _get(sink, "/messages", {"Cookie": "bad;;=="})
            assert resp.status == 401

    def test_host_and_origin_checks(self):
        from src.xstate_statemachine.inspect import SseSink

        with SseSink(allowed_origins=["http://localhost:3000"]) as sink:
            resp, _, _ = _get(sink, "/messages", _auth(sink), host="evil.com")
            assert resp.status == 421  # DNS rebinding
            resp, _, _ = _get(
                sink,
                "/messages",
                {**_auth(sink), "Origin": "http://evil.com"},
            )
            assert resp.status == 403
            same = f"http://127.0.0.1:{sink.port}"
            resp, _, _ = _get(
                sink, "/messages", {**_auth(sink), "Origin": same}
            )
            assert resp.status == 200
            resp, _, _ = _get(
                sink,
                "/messages",
                {**_auth(sink), "Origin": "http://localhost:3000"},
            )
            assert resp.status == 200
            resp, _, _ = _get(sink, "/messages", _auth(sink), host="localhost")
            assert resp.status == 200

    def test_non_loopback_requires_explicit_token(self):
        from src.xstate_statemachine.inspect import SseSink

        with pytest.raises(ValueError, match="non-loopback"):
            SseSink(host="0.0.0.0")
        s = SseSink(host="0.0.0.0", token="t" * 43)
        try:
            assert s.token == "t" * 43
            assert s.host_ok("anything.example")  # token is the control
        finally:
            s.close()

    def test_generated_token_is_strong(self):
        from src.xstate_statemachine.inspect import SseSink

        with SseSink() as a, SseSink() as b:
            assert len(a.token) >= 43 and a.token != b.token
            assert a.url.endswith(f"?token={a.token}")
