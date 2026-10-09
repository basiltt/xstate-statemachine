"""#294 battle (B): no adapter shows a URL or credential in repr/str."""

# -------------------------------------------------------------------------
# 📦 Standard Library Imports
# -------------------------------------------------------------------------
from typing import Any, Callable

# -------------------------------------------------------------------------
# 📥 Third-party Imports
# -------------------------------------------------------------------------
import pytest

SECRET = "S3CRETpw"


def _redis() -> Any:
    pytest.importorskip("redis")
    from xstate_statemachine.contrib.brokers import redis_streams as rs

    url = f"redis://user:{SECRET}@redis-host:6379/0"
    return [
        rs.RedisStreamsBroker(url=url, prefix="p"),
        rs.SyncRedisStreamsBroker(url=url, prefix="p"),
    ]


def _kafka() -> Any:
    pytest.importorskip("aiokafka")
    from xstate_statemachine.contrib.brokers.kafka import KafkaBroker

    return [
        KafkaBroker(
            bootstrap_servers=f"user:{SECRET}@kafka:9092",
            client_kw={"sasl_plain_password": SECRET},
        )
    ]


def _rabbit() -> Any:
    pytest.importorskip("aio_pika")
    from xstate_statemachine.contrib.brokers.rabbitmq import RabbitMQBroker

    return [RabbitMQBroker(url=f"amqps://user:{SECRET}@rabbit/")]


def _nats() -> Any:
    pytest.importorskip("nats")
    from xstate_statemachine.contrib.brokers.nats import NatsBroker

    return [
        NatsBroker(
            servers=f"nats://user:{SECRET}@nats:4222",
            connect_kw={"password": SECRET},
        )
    ]


def _sqs() -> Any:
    pytest.importorskip("boto3")
    import boto3

    from xstate_statemachine.contrib.brokers.sqs import SqsBroker

    client = boto3.client(
        "sqs",
        region_name="eu-west-1",
        aws_access_key_id="AKIAEXAMPLE",
        aws_secret_access_key=SECRET,
    )
    return [SqsBroker(client)]


@pytest.mark.parametrize(
    "build", [_redis, _kafka, _rabbit, _nats, _sqs], ids=lambda f: f.__name__
)
def test_repr_never_shows_url_or_credential(build: Callable[[], Any]):
    for broker in build():
        for text in (repr(broker), str(broker)):
            assert SECRET not in text, text
            assert "@" not in text, text
            assert "://" not in text, text
