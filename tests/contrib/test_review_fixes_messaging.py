# tests/contrib/test_review_fixes_messaging.py
"""Regression tests for the 0.12.0 code-quality review (group
contrib-messaging): CM-01 .. CM-13 and CM-29."""

from __future__ import annotations

import asyncio
import datetime
import decimal
import json
import unittest
from typing import Any, List

import pytest

from src.xstate_statemachine.contrib.brokers._base import Raw, SyncBroker
from src.xstate_statemachine.eda import Envelope

from .redis import conftest as _redis_conftest

r = _redis_conftest.r  # fixtures shared with tests/contrib/redis
prefix = _redis_conftest.prefix


# ---------------------------------------------------------------- brokers
class _FlakyAck:
    def __init__(self) -> None:
        self.sent: List[Any] = []
        self.fail_ack = 1
        self.acked: List[Any] = []

    def send(self, topic: str, env: Envelope) -> None:
        self.sent.append(env.to_json())

    def fetch(self, topic: str, wait_s: float) -> List[Raw]:
        out = [Raw(b, ("n", i), 0) for i, b in enumerate(self.sent)]
        self.sent = []
        return out

    def ack(self, native: Any) -> None:
        if self.fail_ack:
            self.fail_ack -= 1
            raise ConnectionError("down")
        self.acked.append(native)

    drop = ack


class TestCM09FailedAckIsRetriable(unittest.TestCase):
    def test_ack_retry_after_transport_failure(self) -> None:
        t = _FlakyAck()
        b = SyncBroker(t)
        b.publish("t", Envelope.new(type="x.y", subject="k", data={}))
        d = next(iter(b.subscribe("t", timeout=0)))
        with self.assertRaises(ConnectionError):
            d.ack()
        self.assertEqual(b.in_flight, 1)  # still ours: retriable
        d.ack()
        self.assertEqual(len(t.acked), 1)
        self.assertEqual(b.in_flight, 0)


class TestCM02RabbitUnackedRecovers(unittest.TestCase):
    def test_failed_ack_still_decrements(self) -> None:
        pytest.importorskip("aio_pika")
        from src.xstate_statemachine.contrib.brokers.rabbitmq import (
            RabbitMQTransport,
        )

        class Native:
            async def ack(self) -> None:
                raise RuntimeError("stale delivery tag")

            async def reject(self, requeue: bool = False) -> None:
                raise RuntimeError("stale delivery tag")

        t = RabbitMQTransport(channel=object(), max_bytes=1000)
        t.unacked = 2
        with self.assertRaises(RuntimeError):
            asyncio.run(t.ack(Native()))
        self.assertEqual(t.unacked, 1)
        with self.assertRaises(RuntimeError):
            asyncio.run(t.drop(Native()))
        self.assertEqual(t.unacked, 0)


class TestCM13StreamsAckDiscardsHeld(unittest.TestCase):
    def test_held_cleared_when_xack_raises(self) -> None:
        from src.xstate_statemachine.contrib.brokers.redis_streams import (
            RedisStreamsTransport,
        )

        class Client:
            def xack(self, *a: Any) -> None:
                raise ConnectionError("down")

        t = RedisStreamsTransport.__new__(RedisStreamsTransport)
        t.client = Client()
        t.group = "g"
        t._held = {("s", "1-0")}
        with self.assertRaises(ConnectionError):
            t.ack(("s", "1-0"))
        self.assertEqual(t._held, set())


# ------------------------------------------------------------------ redis
class TestCM29Prefix(unittest.TestCase):
    def test_colons_only_prefix_refused(self) -> None:
        pytest.importorskip("redis")
        from src.xstate_statemachine.contrib.redis._keys import (
            validate_prefix,
        )

        for bad in (":", ":::"):
            with self.assertRaises(Exception):
                validate_prefix(bad)
        self.assertEqual(validate_prefix("app::"), "app")


class TestCM10ErrorOmitsHost(unittest.TestCase):
    def test_message_has_class_name_only(self) -> None:
        redis = pytest.importorskip("redis")
        from src.xstate_statemachine.contrib.redis._errors import typed

        err = typed(redis.ConnectionError("Error connecting to db-9:6379"))
        self.assertNotIn("db-9", str(err))
        self.assertIn("ConnectionError", str(err))
        err2 = typed(redis.ResponseError("boom redis://u:pw@h"))
        self.assertNotIn("pw", str(err2))


def test_cm01_list_keys_prunes_expired(r: Any, prefix: str) -> None:
    pytest.importorskip("redis")
    from src.xstate_statemachine.contrib.redis import RedisStore

    s = RedisStore(r, prefix=prefix)
    s.save("a", json.dumps({"x": 1}))
    s.save("b", json.dumps({"x": 1}))
    r.delete(f"{prefix}:snap:a")  # what ttl_s expiry does
    assert s.list_keys() == ["b"]
    assert not r.sismember(f"{prefix}:keys", "a")  # pruned, not just hidden


# --------------------------------------------------------------- pydantic
class TestCM03CodecPrivateKeys(unittest.TestCase):
    def test_extra_forbid_model_with_private_key(self) -> None:
        pytest.importorskip("pydantic")
        import warnings

        from pydantic import BaseModel, ConfigDict

        from src.xstate_statemachine.contrib.pydantic.context import (
            PydanticCodec,
        )

        class M(BaseModel):
            model_config = ConfigDict(extra="forbid")
            n: int = 0
            d: decimal.Decimal = decimal.Decimal("1.5")

        blob = json.dumps(
            {"context": {"n": 1, "d": "2.50", "_xsm_celery": {"k": 1}}}
        )
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            out = json.loads(PydanticCodec(M).encode(blob))
        assert out["context"]["_xsm_celery"] == {"k": 1}
        assert out["context"]["d"] == "2.50"


class TestCM04StrictTransitionFlags(unittest.TestCase):
    def test_lax_bool_string_refused(self) -> None:
        pytest.importorskip("pydantic")
        from pydantic import ValidationError

        from src.xstate_statemachine.contrib.pydantic.config import (
            TransitionConfig,
        )

        for key in ("internal", "reenter"):
            with self.assertRaises(ValidationError):
                TransitionConfig(**{key: "false"})
        self.assertIs(TransitionConfig(internal=True).internal, True)


# ----------------------------------------------------------------- agents
class TestCM05CM06Usage(unittest.TestCase):
    def test_nan_usage_round_trips_and_fails_closed(self) -> None:
        pytest.importorskip("pydantic")
        from src.xstate_statemachine.contrib.agents.messages import (
            ModelResponse,
        )
        from src.xstate_statemachine.contrib.agents.multi import BudgetPlugin

        resp = ModelResponse.from_dict(
            {"text": "x", "usage": {"input_tokens": "nan", "cost_usd": "x"}}
        )
        d = resp.to_dict()  # must not raise
        assert d["usage"]["input_tokens"] != d["usage"]["input_tokens"]
        p = BudgetPlugin(max_total_usd=1.0)
        assert p.exceeded({"cost_usd": "NaN"})
        assert p.exceeded({"cost_usd": 1e999})
        assert not p.exceeded({"cost_usd": 0.5})
        p2 = BudgetPlugin(max_total_tokens=10)
        assert p2.exceeded({"input_tokens": "junk", "output_tokens": 0})


class TestCM07CM08Tools(unittest.TestCase):
    def test_json_typed_arguments_validate(self) -> None:
        pytest.importorskip("pydantic")
        from src.xstate_statemachine.contrib.agents.tools import tool_registry

        def f(when: datetime.datetime, amt: decimal.Decimal) -> str:
            """Do it."""
            return f"{when.year}:{amt}"

        reg = tool_registry(f)
        args = reg.get("f").validate(
            {"when": "2024-01-01T00:00:00", "amt": "1.5"}
        )
        assert args["amt"] == decimal.Decimal("1.5")

    def test_sync_tool_in_async_uses_daemon_thread(self) -> None:
        pytest.importorskip("pydantic")
        import threading

        from src.xstate_statemachine.contrib.agents.tools import (
            ToolRegistry,
            tool_registry,
        )

        def whoami() -> bool:
            """Report the thread."""
            return threading.current_thread().daemon

        t = tool_registry(whoami).get("whoami")
        assert asyncio.run(ToolRegistry._acall(t, {})) is True
