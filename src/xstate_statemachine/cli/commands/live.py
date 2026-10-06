# src/xstate_statemachine/cli/commands/live.py
# -----------------------------------------------------------------------------
# 📡 `xsm inspect --live`, `xsm sim --record`, `xsm replay` (#274)
# -----------------------------------------------------------------------------
# 🏛️ The live inspector reuses the simulator's `Session` (stub logic on a
#    `SimulatedClock`), with an `InspectorPlugin` registered GLOBALLY so the
#    session's interpreter -- and every restore after undo/reset, and every
#    child actor -- is seen. The page is served by the stdlib `SseSink`.
#
# 🔐 X0.7: loopback by default; `--host` other than loopback requires
#    `--token`; context is shown only for keys in `--context` (deny by
#    default); recordings are written 0600.
# -----------------------------------------------------------------------------
"""Live inspector, session recording and replay."""

from __future__ import annotations

import json
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any, Callable, List, Optional

from ...inspect import (
    InspectorPlugin,
    JsonLinesSink,
    SseSink,
    read_jsonl,
    replay_messages,
)
from . import get_console

__all__ = ["run_inspect_live", "run_replay", "recording_plugin"]


_SLICE = 0.25


def _allowlist(context: Optional[str]) -> List[str]:
    return [k.strip() for k in (context or "").split(",") if k.strip()]


def _serve(
    *,
    host: str,
    port: int,
    token: Optional[str],
    open_browser: bool,
) -> SseSink:
    c = get_console()
    try:
        sink = SseSink(host, port, token=token).start()
    except ValueError as exc:
        c.error(str(exc) + " -- pass --token")
        raise SystemExit(2)
    except OSError as exc:
        c.error(f"cannot bind {host}:{port}: {exc}")
        raise SystemExit(1)
    c.info(f"live inspector: {sink.url}")
    c.print(
        c.style(
            "the token is single-use in the URL: the page swaps it for an "
            "HttpOnly cookie on first load",
            "muted",
        )
    )
    if open_browser:
        # battle #274: a headless box has no browser; that is not a
        #    reason to tear down a server whose URL was just printed.
        try:
            opened = webbrowser.open(sink.url)
        except Exception:  # noqa: BLE001 -- any browser failure
            opened = False
        if not opened:
            c.warn("could not open a browser; open the URL above")
    return sink


def _block(stop: Optional[threading.Event], seconds: Optional[float]) -> None:
    # battle #274: one long `Event.wait(None)` is not interruptible by
    #    Ctrl-C on Windows (the lock acquire ignores SIGINT); short slices
    #    let KeyboardInterrupt land so the server shuts down cleanly.
    ev = stop or threading.Event()
    deadline = None if seconds is None else time.monotonic() + seconds
    try:
        while not ev.is_set():
            left = _SLICE if deadline is None else deadline - time.monotonic()
            if left <= 0:
                return
            ev.wait(min(left, _SLICE))
    except KeyboardInterrupt:  # pragma: no cover -- interactive
        pass


def run_inspect_live(
    path: str,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    token: Optional[str] = None,
    open_browser: bool = False,
    context: Optional[str] = None,
    events: Optional[str] = None,
    duration: Optional[float] = None,
    stop: Optional[threading.Event] = None,
    on_ready: Optional[Callable[[SseSink], None]] = None,
    source: Any = None,
) -> None:
    """`xsm inspect machine.json --live`.

    With *events* the script runs once and the server stays up for
    *duration* seconds (or until *stop*); without, the interactive
    simulator drives the machine while the page follows it.
    """
    from .simulate import (
        Session,
        interactive,
        parse_events_arg,
        run_script,
    )

    c = get_console()
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    sink = _serve(host=host, port=port, token=token, open_browser=open_browser)
    plugin = InspectorPlugin(
        sink, context_allowlist=_allowlist(context)
    ).install()
    session = None
    try:
        session = Session(config)
        if on_ready is not None:
            on_ready(sink)
        if events is not None:
            run_script(session, parse_events_arg(events, None))
            _block(stop, duration)
        elif c.interactive or source is not None:
            interactive(session, source=source)
        else:
            _block(stop, duration)
    finally:
        plugin.uninstall()
        if session is not None:
            session.stop()
        sink.close()


def recording_plugin(
    path: str, *, context: Optional[str] = None, append: bool = False
) -> "tuple[InspectorPlugin, JsonLinesSink]":
    """A globally-installed `InspectorPlugin` writing to *path* (0600).

    battle #274: a second `--record` to the same file used to APPEND
    silently -- `xsm replay` then showed two unrelated sessions as one.
    A non-empty existing file is refused (`FileExistsError`) unless
    *append*.
    """
    p = Path(path)
    if not append and p.is_file() and p.stat().st_size > 0:
        raise FileExistsError(
            f"{path} already holds a recording; pass --append to add "
            "to it, or choose another file"
        )
    sink = JsonLinesSink(path)
    plugin = InspectorPlugin(
        sink, context_allowlist=_allowlist(context)
    ).install()
    return plugin, sink


def run_replay(
    path: str,
    *,
    live: bool = False,
    host: str = "127.0.0.1",
    port: int = 8765,
    token: Optional[str] = None,
    open_browser: bool = False,
    speed: float = 0.0,
    duration: Optional[float] = None,
    stop: Optional[threading.Event] = None,
    on_ready: Optional[Callable[[SseSink], None]] = None,
) -> None:
    """`xsm replay session.jsonl [--live]`."""
    c = get_console()
    if not speed >= 0:
        c.error(f"--speed must be >= 0, got {speed!r}")
        raise SystemExit(2)
    if not Path(path).is_file():
        c.error(f"{path}: no such file")
        raise SystemExit(1)
    # battle #274: the recording used to be `list()`-ed whole before the
    #    first line printed; a multi-GB flight recording is now streamed.
    #    A corrupt middle line still fails loudly (exit 1) -- after the
    #    lines before it were shown.
    if not live:
        try:
            for m in read_jsonl(path):
                ev = (m.get("event") or {}).get("type", "")
                snap = m.get("snapshot") or {}
                c.print(
                    f"{m.get('type', '?'):<17} {m.get('sessionId', '')}  "
                    f"{ev}  {json.dumps(snap.get('value', ''))}"
                )
        except (ValueError, OSError) as exc:
            c.error(f"{path}: {type(exc).__name__}: {exc}")
            raise SystemExit(1)
        return
    sink = _serve(host=host, port=port, token=token, open_browser=open_browser)
    try:
        if on_ready is not None:
            on_ready(sink)
        try:
            n = replay_messages(path, sink, speed=speed)
        except (ValueError, OSError) as exc:
            c.error(f"{path}: {type(exc).__name__}: {exc}")
            raise SystemExit(1)
        c.info(f"replayed {n} messages")
        _block(stop, duration)
    finally:
        sink.close()
