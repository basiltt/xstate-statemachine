# src/xstate_statemachine/contrib/redis/_keys.py
"""Key layout shared by the Redis store, inbox and log (#306).

::

    {prefix}:schema              string   layout version
    {prefix}:keys                set      every snapshot key (for list_keys)
    {prefix}:snap:{key}          hash     snapshot, version, machine_version,
                                          updated_at
    {prefix}:dl:{key}            hash     field "state_id|entry_seq|event" ->
                                          JSON Deadline
    {prefix}:deadlines           zset     member "{key}|state_id|entry_seq"
                                          scored by due_at_wall (scanner index)
    {prefix}:lock:{key}          string   random token, PX ttl
    {prefix}:inbox:{scope}       hash     field key -> JSON InboxEntry
    {prefix}:inbox_exp           zset     member "{scope}|{key}" scored by
                                          expires_at (TTL index)
    {prefix}:log:{machine_id}    stream   one entry per TransitionRecord
"""

from __future__ import annotations

from ...exceptions import InvalidConfigError

SCHEMA_VERSION = 1


def validate_prefix(prefix: str) -> str:
    """X0.15: a non-empty, colon-free namespace is mandatory."""
    if not isinstance(prefix, str) or not prefix.strip():
        raise InvalidConfigError(
            "Redis backends need a non-empty `prefix` (the key namespace); "
            "two applications sharing one Redis must never collide by "
            "default."
        )
    if any(c in prefix for c in " \t\n\r"):
        raise InvalidConfigError("Redis `prefix` must not contain whitespace.")
    return prefix.rstrip(":")


class Keys:
    __slots__ = ("p",)

    def __init__(self, prefix: str) -> None:
        self.p = validate_prefix(prefix)

    @property
    def schema(self) -> str:
        return f"{self.p}:schema"

    @property
    def keys(self) -> str:
        return f"{self.p}:keys"

    def snap(self, key: str) -> str:
        return f"{self.p}:snap:{key}"

    def dl(self, key: str) -> str:
        return f"{self.p}:dl:{key}"

    @property
    def deadlines(self) -> str:
        return f"{self.p}:deadlines"

    def lock(self, key: str) -> str:
        return f"{self.p}:lock:{key}"

    def inbox(self, scope: str) -> str:
        return f"{self.p}:inbox:{scope}"

    @property
    def inbox_exp(self) -> str:
        return f"{self.p}:inbox_exp"

    def log(self, machine_id: str) -> str:
        return f"{self.p}:log:{machine_id}"
