# src/xstate_statemachine/contrib/brokers/sqs.py
# -----------------------------------------------------------------------------
# 🟧 Amazon SQS broker (boto3) -- FIFO MessageGroupId = subject (#294)
# -----------------------------------------------------------------------------
# 🏛️ topic = queue NAME (resolved once with ``GetQueueUrl``).
#
#    * FIFO queues (``*.fifo``): ``MessageGroupId = subject`` (per-subject
#      order is SQS's per-group order) and ``MessageDeduplicationId =
#      envelope.id`` (a re-published outbox row inside the 5-minute window
#      is dropped by SQS). STANDARD queues give no order at all -- use
#      them only where the chart tolerates reordering (documented).
#    * ``ack`` / ``nack(requeue=False)`` = ``DeleteMessage`` (dead-
#      lettering is the dispatcher's, X0.8; an SQS redrive policy is a
#      second net for consumers that crash in a loop).
#    * Long polling: ``WaitTimeSeconds`` up to 20 s. The visibility
#      timeout is SQS's redelivery clock: a message held longer is
#      redelivered to someone else (at-least-once; dedup). Size it above
#      your processing time, or call `extend_visibility`.
#    * attempts = ``ApproximateReceiveCount - 1``.
#    * boto3 is synchronous: `SyncSqsBroker` calls it directly;
#      `SqsBroker` runs the same calls on a worker thread. Credentials come
#      from boto3's own chain (never arguments, never ``repr``).
# -----------------------------------------------------------------------------
"""`SqsBroker` (async) and `SyncSqsBroker` over boto3."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .._compat import require_extra

require_extra("sqs", "boto3")

from ...eda.envelope import Envelope  # noqa: E402
from ._base import (  # noqa: E402
    AsyncBroker,
    Raw,
    SyncBroker,
    ThreadedTransport,
    structured,
)

__all__ = ["SqsBroker", "SqsTransport", "SyncSqsBroker"]

_MAX_BATCH = 10  # SQS ReceiveMessage limit
_MAX_WAIT_S = 20  # SQS long-poll limit


class SqsTransport:
    """The four native operations over a boto3 SQS client."""

    def __init__(
        self,
        client: Any,
        *,
        visibility_timeout_s: Optional[int] = None,
        max_bytes: int,
    ) -> None:
        self.client = client
        self.visibility_timeout_s = visibility_timeout_s
        self.max_bytes = max_bytes
        self._urls: Dict[str, str] = {}

    def url(self, topic: str) -> str:
        u = self._urls.get(topic)
        if u is None:
            u = self.client.get_queue_url(QueueName=topic)["QueueUrl"]
            self._urls[topic] = u
        return u

    def send(self, topic: str, envelope: Envelope) -> None:
        kw: Dict[str, Any] = {
            "QueueUrl": self.url(topic),
            "MessageBody": structured(envelope, self.max_bytes).decode(),
            "MessageAttributes": {
                "ce_type": {"DataType": "String", "StringValue": envelope.type}
            },
        }
        if topic.endswith(".fifo"):
            kw["MessageGroupId"] = envelope.subject or "_"
            kw["MessageDeduplicationId"] = envelope.id
        self.client.send_message(**kw)

    def fetch(self, topic: str, wait_s: float) -> List[Raw]:
        url = self.url(topic)
        kw: Dict[str, Any] = {
            "QueueUrl": url,
            "MaxNumberOfMessages": _MAX_BATCH,
            "WaitTimeSeconds": min(_MAX_WAIT_S, int(wait_s)),
            "AttributeNames": ["ApproximateReceiveCount"],
        }
        if self.visibility_timeout_s is not None:
            kw["VisibilityTimeout"] = int(self.visibility_timeout_s)
        msgs = self.client.receive_message(**kw).get("Messages", [])
        out: List[Raw] = []
        for m in msgs:
            count = int(
                (m.get("Attributes") or {}).get("ApproximateReceiveCount", 1)
            )
            out.append(
                Raw(m["Body"], (url, m["ReceiptHandle"]), max(0, count - 1))
            )
        return out

    def ack(self, native: Any) -> None:
        url, handle = native
        self.client.delete_message(QueueUrl=url, ReceiptHandle=handle)

    drop = ack

    def extend(self, native: Any, seconds: int) -> None:
        url, handle = native
        self.client.change_message_visibility(
            QueueUrl=url, ReceiptHandle=handle, VisibilityTimeout=int(seconds)
        )


def _client(client: Any, region_name: Optional[str]) -> Any:
    if client is not None:
        return client
    import boto3

    return boto3.client("sqs", region_name=region_name)


class SyncSqsBroker(SyncBroker):
    """Blocking `SyncBrokerAdapter` over SQS.

    Args:
        client: A boto3 SQS client (default ``boto3.client("sqs")``).
        region_name: Used only when *client* is omitted.
        visibility_timeout_s: Per-receive visibility timeout override.
        max_bytes / on_disconnect / on_reconnect / on_undecodable: See
            `contrib.brokers`. SQS caps a message at 256 KiB anyway.
    """

    def __init__(
        self,
        client: Any = None,
        *,
        region_name: Optional[str] = None,
        visibility_timeout_s: Optional[int] = None,
        **kw: Any,
    ) -> None:
        super().__init__(None, **kw)
        self.sqs = SqsTransport(
            _client(client, region_name),
            visibility_timeout_s=visibility_timeout_s,
            max_bytes=self.max_bytes,
        )
        self.transport = self.sqs

    def extend_visibility(self, delivery: Any, seconds: int) -> None:
        """Keep an in-flight delivery invisible for *seconds* more."""
        with self._lock:
            entry = self._inflight.get(id(delivery))
        if entry is not None:
            self.sqs.extend(entry[1], seconds)

    def __repr__(self) -> str:
        return "SyncSqsBroker()"


class SqsBroker(AsyncBroker):
    """Async `BrokerAdapter` over SQS (boto3 calls on a worker thread);
    same arguments as `SyncSqsBroker`."""

    def __init__(
        self,
        client: Any = None,
        *,
        region_name: Optional[str] = None,
        visibility_timeout_s: Optional[int] = None,
        **kw: Any,
    ) -> None:
        super().__init__(None, **kw)
        self.sqs = SqsTransport(
            _client(client, region_name),
            visibility_timeout_s=visibility_timeout_s,
            max_bytes=self.max_bytes,
        )
        self.transport = ThreadedTransport(self.sqs)

    def __repr__(self) -> str:
        return "SqsBroker()"
