# src/xstate_statemachine/contrib/_registry.py
# -----------------------------------------------------------------------------
# 🗂️ The single table of integrations: extra -> subpackage -> dependencies
# -----------------------------------------------------------------------------
# 🏛️ One source of truth read by three consumers so they cannot drift:
#      * `tests/contrib/test_extras_matrix.py` -- every listed subpackage
#        must raise `MissingExtraError` when its dependency is blocked;
#      * the CI extras matrix (generated/checked from this table);
#      * `xsm info` / the docs extras table (later issues).
#    Pure data, zero imports beyond `typing`. An entry whose subpackage does
#    not exist yet is a *placeholder*: the extra resolves via pyproject so
#    users can already `pip install xstate-statemachine[django]`, and the
#    matrix test skips it until the owning issue lands.
# -----------------------------------------------------------------------------
"""Registry of optional integrations (extras)."""

from __future__ import annotations

from typing import Dict, NamedTuple, Tuple


class Extra(NamedTuple):
    """One pip extra.

    Attributes:
        subpackage: Module under ``xstate_statemachine.contrib`` (``""`` for
            umbrella extras like ``web`` that install other extras only).
        modules: Top-level third-party modules the subpackage imports --
            what `require_extra` checks and what the matrix test blocks.
        issue: The GitHub issue that ships the code.
    """

    subpackage: str
    modules: Tuple[str, ...]
    issue: int


#: extra name -> Extra. Keep alphabetical; umbrella extras last.
EXTRAS: Dict[str, Extra] = {
    "agents": Extra("agents", ("pydantic",), 287),
    "celery": Extra("celery", ("celery",), 292),
    "channels": Extra("channels", ("channels", "django"), 283),
    "cloudevents": Extra("brokers", ("cloudevents",), 293),
    "django": Extra("django", ("django",), 280),
    "drf": Extra("drf", ("rest_framework", "django"), 283),
    "fastapi": Extra("fastapi", ("fastapi", "pydantic", "starlette"), 276),
    "flask": Extra("flask", ("flask",), 285),
    "kafka": Extra("brokers.kafka", ("aiokafka",), 294),
    "litestar": Extra("litestar", ("litestar",), 278),
    "nats": Extra("brokers.nats", ("nats",), 294),
    "observability": Extra(
        "observability", ("opentelemetry", "prometheus_client"), 273
    ),
    "pydantic": Extra("pydantic", ("pydantic",), 266),
    "rabbitmq": Extra("brokers.rabbitmq", ("aio_pika",), 294),
    "redis": Extra("redis", ("redis",), 306),
    "sqlalchemy": Extra("sqlalchemy", ("sqlalchemy",), 284),
    "sqs": Extra("brokers.sqs", ("boto3",), 294),
    "starlette": Extra("starlette", ("starlette",), 275),
    "testing": Extra("testing", ("pytest", "hypothesis"), 268),
    # umbrella extras -- no subpackage of their own
    "web": Extra("", (), 258),
    "eda": Extra("", (), 258),
    "all": Extra("", (), 258),
}

__all__ = ["EXTRAS", "Extra"]
