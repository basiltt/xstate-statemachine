# src/xstate_statemachine/contrib/brokers/__init__.py
# -----------------------------------------------------------------------------
# 📡 contrib.brokers -- real `BrokerAdapter`s for the EDA core (#294)
# -----------------------------------------------------------------------------
# 🏛️ One module per broker, each gated by its own extra:
#
#      brokers.redis_streams  [redis]     RedisStreamsBroker / Sync...
#      brokers.kafka          [kafka]     KafkaBroker          (aiokafka)
#      brokers.rabbitmq       [rabbitmq]  RabbitMQBroker       (aio-pika)
#      brokers.nats           [nats]      NatsBroker           (nats-py)
#      brokers.sqs            [sqs]       SqsBroker / SyncSqsBroker (boto3)
#
#    This package itself imports NOTHING third-party, so
#    ``import xstate_statemachine.contrib.brokers`` always works and each
#    submodule raises `MissingExtraError` for its own extra only. The
#    shared bookkeeping (settle-once, local buffer, attempt counting,
#    health callbacks) lives in `_base.py`; adapters stay thin over their
#    client -- no new consistency model (#294).
# -----------------------------------------------------------------------------
"""Broker adapters for `xstate_statemachine.eda` (one extra each)."""

from __future__ import annotations

from typing import List

__all__: List[str] = []
