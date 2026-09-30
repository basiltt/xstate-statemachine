# src/xstate_statemachine/inspect/_page.py
# -----------------------------------------------------------------------------
# 🖥️ The inspector page served by `SseSink` (no build step, no CDN script)
# -----------------------------------------------------------------------------
# 🏛️ Two views over the same `/events` stream:
#      * "Stately" -- an iframe on https://stately.ai/inspect driven exactly
#        the way `@statelyai/inspect`'s `BrowserAdapter` drives it: wait for
#        the frame to post `{type: "@statelyai.connected"}`, then
#        `postMessage` every protocol message (deferred ones first).
#      * "Local" -- our own minimal fallback: actor list, current value,
#        event log. Works offline and when the hosted UI changes.
#    The script is served from `/app.js` so the CSP can forbid inline JS.
# -----------------------------------------------------------------------------
"""Static assets for the SSE inspector page."""

from __future__ import annotations

__all__ = ["INDEX_HTML", "APP_JS", "STATELY_URL"]

STATELY_URL = "https://stately.ai/inspect"

INDEX_HTML = b"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>xsm live inspector</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
 body{font:14px system-ui,sans-serif;margin:0;display:flex;height:100vh}
 #side{width:340px;overflow:auto;border-right:1px solid #ddd;padding:8px}
 #main{flex:1;display:flex;flex-direction:column}
 #stately{flex:1;border:0}
 .ev{font-family:monospace;font-size:12px;padding:1px 0}
 .actor{margin:6px 0;padding:4px;background:#f4f4f8;border-radius:4px}
 .muted{color:#888}
</style></head>
<body>
<div id="side">
 <h3>xsm inspector <span id="status" class="muted">connecting</span></h3>
 <label><input type="checkbox" id="useStately" checked> Stately UI</label>
 <div id="actors"></div><h4>Events</h4><div id="log"></div>
</div>
<div id="main"><iframe id="stately" title="Stately Inspector"
 referrerpolicy="no-referrer"></iframe></div>
<script src="/app.js"></script>
</body></html>
"""

APP_JS = (
    b"""'use strict';
(function () {
  var STATELY = '"""
    + STATELY_URL.encode()
    + b"""';
  var frame = document.getElementById('stately');
  var connected = false, deferred = [];
  var actors = {};
  function post(msg) {
    if (!document.getElementById('useStately').checked) return;
    if (connected && frame.contentWindow) {
      frame.contentWindow.postMessage(msg, STATELY);
    } else { deferred.push(msg); if (deferred.length > 1000) deferred.shift(); }
  }
  window.addEventListener('message', function (e) {
    if (e.origin !== new URL(STATELY).origin) return;
    if (e.data && e.data.type === '@statelyai.connected') {
      connected = true;
      deferred.splice(0).forEach(post);
    }
  });
  frame.src = STATELY;
  function text(tag, cls, s) {
    var el = document.createElement(tag); el.className = cls;
    el.textContent = s; return el;
  }
  function render() {
    var box = document.getElementById('actors'); box.textContent = '';
    Object.keys(actors).forEach(function (id) {
      var a = actors[id];
      box.appendChild(text('div', 'actor',
        a.name + ' (' + id + ')  ' + JSON.stringify(a.value) +
        '  ' + a.status));
    });
  }
  function local(msg) {
    if (msg.type === '@xstate.actor') {
      actors[msg.sessionId] = {name: msg.name, value: msg.snapshot.value,
                               status: msg.snapshot.status};
    } else if (msg.type === '@xstate.snapshot' && actors[msg.sessionId]) {
      actors[msg.sessionId].value = msg.snapshot.value;
      actors[msg.sessionId].status = msg.snapshot.status;
    } else if (msg.type === '@xstate.event') {
      var who = (msg.sourceId ? msg.sourceId + ' -> ' : '') + msg.sessionId;
      document.getElementById('log').prepend(
        text('div', 'ev', who + '  ' + msg.event.type));
    }
    render();
  }
  var es = new EventSource('/events');
  es.onopen = function () {
    document.getElementById('status').textContent = 'live';
  };
  es.onerror = function () {
    document.getElementById('status').textContent = 'disconnected';
  };
  es.onmessage = function (e) {
    var msg = JSON.parse(e.data); local(msg); post(msg);
  };
})();
"""
)
