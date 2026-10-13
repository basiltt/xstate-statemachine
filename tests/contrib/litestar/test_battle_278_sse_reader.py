"""📡 Pin the SSE test reader's comment handling and overall deadline."""

from __future__ import annotations

import asyncio
from typing import Any, Optional, Tuple

import pytest

from ..conftest import requires_extra
from ..starlette._support import RawSSE, bounded
from .test_battle_278_orders import _next_sse_data_event

pytestmark = requires_extra("litestar")


@pytest.mark.parametrize("comments", [0, 2])
@pytest.mark.parametrize("kind", ["snapshot", "transition", "unexpected"])
def test_sse_reader_skips_only_comments(comments: int, kind: str) -> None:
    """Data kind, sequence and body survive; unexpected kinds reach callers."""

    async def go() -> Tuple[Optional[int], str, Any]:
        stream = RawSSE(None, "/unused")
        stream.buf = b": heartbeat\n\n" * comments
        stream.buf += (
            f'id: 7\nevent: {kind}\ndata: {{"state":"cart"}}\n\n'
        ).encode()
        return await bounded(_next_sse_data_event(stream))

    assert asyncio.run(go()) == (7, kind, {"state": "cart"})


def test_sse_reader_heartbeats_do_not_reset_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Continuous keepalives cannot hide a missing transition indefinitely."""

    async def go() -> None:
        stream = RawSSE(None, "/unused")
        comments = 0

        async def next_comment() -> Tuple[Optional[int], str, Any]:
            nonlocal comments
            comments += 1
            # 📡 Yield cooperatively; do not wait for a real heartbeat timer.
            await asyncio.sleep(0)
            return None, "comment", ": heartbeat"

        monkeypatch.setattr(stream, "next_event", next_comment)
        with pytest.raises(asyncio.TimeoutError):
            await bounded(_next_sse_data_event(stream), timeout=0.01)
        assert comments > 0

    asyncio.run(go())
