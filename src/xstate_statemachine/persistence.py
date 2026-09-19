# /src/xstate_statemachine/persistence.py
# -----------------------------------------------------------------------------
# 💾 Snapshot Envelope: versioning and machine identity
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: before 0.8.0 a persisted snapshot was a bare dict
# with no version and no record of which machine produced it. Two failure
# modes followed, both silent:
#
#   * a blob written by a NEWER library restored into an older one, which
#     read the keys it knew and ignored the rest -- a half-restore that
#     looked healthy;
#   * a blob written against machine shape A restored into shape B (a guard
#     added, a state renamed) and landed in whatever still fit.
#
# For a machine that owns money (the filer's OMS) both are unacceptable. This
# module owns the envelope: the integer format version, the structural hash
# of a machine, and the two checks `from_snapshot` runs. It is deliberately
# separate from the interpreter so the format contract is one small file.
#
# `SNAPSHOT_VERSION` is bumped ONLY when the payload LAYOUT changes -- never
# on a package release -- so patch/minor releases do not invalidate stored
# snapshots. Older versions are upcast in `upcast()`; newer ones are refused.
# -----------------------------------------------------------------------------
"""Snapshot envelope: format version, machine hash, restore-time checks."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any, Dict, Tuple

from .exceptions import SnapshotDriftError, SnapshotVersionError

if TYPE_CHECKING:  # pragma: no cover
    from .models import MachineNode, StateNode, TransitionDefinition

#: Current snapshot payload layout. History:
#:   0 -- unversioned 0.7.x payload (implicit; no ``version`` key)
#:   1 -- 0.8.0: adds ``version``, ``machine_id``, ``machine_hash``,
#:        ``taken_at``, ``pending_events``, ``value``
#:   2 -- 0.8.1: every ``pending_events`` / ``deferred`` record carries a
#:        ``kind`` (``event`` | ``system`` | ``done`` | ``error`` | ``after``)
#:        so engine events and provenance round-trip (#86, #87). ``done``
#:        records add ``data`` + ``src``; ``error`` records add ``error``
#:        (repr) + ``src``.
SNAPSHOT_VERSION: int = 2


# -----------------------------------------------------------------------------
# 🔏 Structural hash
# -----------------------------------------------------------------------------
def _guard_shape(g: Any) -> Any:
    """Recursive shape of a guard: name, composite children, `stateIn` target.

    🏛️ `t.guard` alone is the ROOT guard's type -- ``"and"`` -- so swapping a
    child of a composite guard, or the target of a `stateIn`, left the hash
    unchanged (review F9). Those are exactly the edits that change which
    transitions fire, i.e. the drift a restore must refuse.
    """
    if g is None:
        return None
    shape: Dict[str, Any] = {"type": g.type}
    if getattr(g, "children", None):
        shape["children"] = [_guard_shape(c) for c in g.children]
    if getattr(g, "is_state_in", False) and isinstance(g.params, dict):
        shape["stateIn"] = g.params.get("stateValue")
    return shape


def _transition_shape(t: "TransitionDefinition") -> Tuple[Any, ...]:
    """The parts of a transition that change its BEHAVIOUR.

    Action ORDER is preserved (a tuple, not a sorted list): running
    ``["debit", "credit"]`` is not the same behaviour as the reverse.
    """
    return (
        t.event,
        t.target_str,
        json.dumps(_guard_shape(t.guard_def), sort_keys=True),
        tuple(a.type for a in t.actions),
        bool(t.reenter),
    )


def _node_shape(node: "StateNode") -> Dict[str, Any]:
    """The behavioural shape of one state node, ordering-insensitive.

    🏛️ Included: id, type, initial, entry/exit action NAMES, every
    transition's event / target / guard NAME / action names / reenter,
    invoke srcs and ids, `after` delays. Deliberately EXCLUDED: `meta`,
    `description`, `tags`, action params and declaration order -- a docstring
    edit or a reordered dict must not invalidate every stored snapshot.
    Guard names ARE included on purpose: adding a guard changes which
    transitions fire, which is exactly the drift a restore must refuse.
    """
    # 🔁 Reuse the validator's walk so "every transition a node owns" has
    #    exactly one definition in the codebase.
    from .validation import transitions_of

    transitions = [_transition_shape(t) for _, t in transitions_of(node)]
    return {
        "id": node.id,
        "type": node.type,
        "initial": node.initial,
        "entry": sorted(a.type for a in node.entry),
        "exit": sorted(a.type for a in node.exit),
        "transitions": sorted(map(repr, transitions)),
        "invoke": sorted((inv.src or "", inv.id) for inv in node.invoke),
        "after": sorted(str(d) for d in node.after),
    }


def structure_hash(machine: "MachineNode") -> str:
    """A 16-hex-char fingerprint of a machine's behavioural structure.

    Two machines hash equal iff they have the same states, transitions,
    guard/action NAMES, invokes and delays -- regardless of `meta`,
    descriptions, or key order. See `_node_shape` for the exact contract.
    """
    from .validation import walk

    shapes = sorted(
        json.dumps(_node_shape(n), sort_keys=True) for n in walk(machine)
    )
    digest = hashlib.sha256("\n".join(shapes).encode("utf-8")).hexdigest()
    return digest[:16]


# -----------------------------------------------------------------------------
# 🛡️ Restore-time checks
# -----------------------------------------------------------------------------
def check_version(snapshot: Dict[str, Any]) -> int:
    """Return the snapshot's version, refusing one from a newer library.

    Raises:
        SnapshotVersionError: ``snapshot["version"] > SNAPSHOT_VERSION``.
    """
    from .exceptions import SnapshotCorruptError

    raw = snapshot.get("version", 0)
    # 🛡️ #146: `int("x")` / `int(None)` escaped as ValueError/TypeError
    #    before `check_shape` ever ran. A `bool` is an int subclass; it is
    #    not a version.
    if isinstance(raw, bool) or not isinstance(raw, (int, float, str)):
        raise SnapshotCorruptError(
            f"Snapshot is malformed: 'version' is {type(raw).__name__}, "
            f"expected an integer."
        )
    try:
        version = int(raw)
    except (TypeError, ValueError):
        raise SnapshotCorruptError(
            f"Snapshot is malformed: 'version' {raw!r} is not an integer."
        ) from None
    if version > SNAPSHOT_VERSION:
        raise SnapshotVersionError(version, SNAPSHOT_VERSION)
    return version


_VALID_STATUSES = frozenset(
    {"uninitialized", "running", "stopped", "done", "error"}
)


def check_shape(snapshot: Dict[str, Any]) -> None:
    """Reject a structurally invalid payload with a typed error (#110).

    Runs after `check_version` / `check_identity` and before any field is
    read, so a corrupted blob cannot surface as a bare ``KeyError`` or be
    restored into an impossible state. Checks are shape-only: required keys
    present, ``context`` a mapping, ``status`` one of the five known values,
    ``configuration`` / ``state_ids`` lists of strings, and a ``running``
    snapshot that names at least one state.
    """
    from .exceptions import SnapshotCorruptError

    def fail(msg: str) -> None:
        raise SnapshotCorruptError(f"Snapshot is malformed: {msg}.")

    if not isinstance(snapshot, dict):
        fail(f"payload is {type(snapshot).__name__}, expected an object")
    for key in ("status", "context", "state_ids"):
        if key not in snapshot:
            fail(f"missing required key '{key}'")
    status = snapshot["status"]
    # 🛡️ #146: an unhashable status (list/dict) raised TypeError from the
    #    set membership test itself.
    if not isinstance(status, str) or status not in _VALID_STATUSES:
        fail(
            f"unknown status {status!r}; expected one of {sorted(_VALID_STATUSES)}"
        )
    if not isinstance(snapshot["context"], dict):
        fail(
            f"'context' is {type(snapshot['context']).__name__}, expected an object"
        )
    for key in ("state_ids", "configuration"):
        val = snapshot.get(key)
        if val is None and key == "configuration":
            continue
        if not isinstance(val, list) or not all(
            isinstance(x, str) for x in val
        ):
            fail(f"'{key}' must be a list of state-id strings")
    if status == "running" and not (
        snapshot.get("configuration") or snapshot["state_ids"]
    ):
        fail("status is 'running' but the configuration is empty")
    # 🛡️ #145 (read side): an "error" machine always knows WHY -- `_fail`
    #    and `_die` both set `error`. A blob claiming "error" with nothing
    #    to say is not one this library wrote.
    if status == "error" and not snapshot.get("error"):
        fail("status is 'error' but no 'error' message is recorded")
    for key in ("pending_events", "deferred"):
        val = snapshot.get(key)
        if val is not None and (
            not isinstance(val, list)
            or not all(
                isinstance(r, dict)
                # 🛡️ #158: the type must be a non-empty str, as `send()`
                #    requires; `restore_event` re-checks per record.
                and isinstance(r.get("type"), str) and r["type"]
                for r in val
            )
        ):
            fail(
                f"'{key}' must be a list of event records whose 'type' is "
                f"a non-empty string"
            )
    # 🛡️ #146: every remaining top-level key `from_snapshot` reads. Each
    #    is optional, but when present it must have the shape the reader
    #    assumes, or the reader's own `.items()` / indexing leaks a bare
    #    AttributeError. `output` and `error` are opaque values and are
    #    deliberately NOT constrained.
    for key in ("history", "actors", "system"):
        val = snapshot.get(key)
        if val is not None and not isinstance(val, dict):
            fail(f"'{key}' is {type(val).__name__}, expected an object")
    history = snapshot.get("history") or {}
    if not all(
        isinstance(k, str)
        and isinstance(v, list)
        and all(isinstance(x, str) for x in v)
        for k, v in history.items()
    ):
        fail("'history' must map state ids to lists of state-id strings")
    actors = snapshot.get("actors") or {}
    if not all(
        isinstance(k, str) and isinstance(v, dict) for k, v in actors.items()
    ):
        fail("'actors' must map actor ids to persisted actor records")
    system = snapshot.get("system") or {}
    if not all(
        isinstance(k, str) and isinstance(v, str) for k, v in system.items()
    ):
        fail("'system' must map system ids to actor-id strings")


def check_identity(
    snapshot: Dict[str, Any], machine: "MachineNode", *, verify_hash: bool
) -> None:
    """Refuse to restore a snapshot into a machine it was not taken from.

    Version-0 payloads carry neither field and are accepted unchecked --
    they cannot be drift-checked, which is precisely why the fields exist.

    Raises:
        SnapshotDriftError: machine id differs, or (when *verify_hash*)
            the structural hash differs.
    """
    snap_id = snapshot.get("machine_id")
    if snap_id is not None and snap_id != machine.id:
        raise SnapshotDriftError(
            f"snapshot was taken from machine '{snap_id}' but is being "
            f"restored into '{machine.id}'"
        )
    snap_hash = snapshot.get("machine_hash")
    if verify_hash and snap_hash is not None:
        current = machine.structure_hash
        if snap_hash != current:
            raise SnapshotDriftError(
                f"machine '{machine.id}' structure changed since this "
                f"snapshot was taken ({snap_hash} != {current}). Migrate the "
                f"snapshot, or pass verify_machine_hash=False if the change "
                f"is known to be compatible."
            )


def upcast(snapshot: Dict[str, Any], version: int) -> Dict[str, Any]:
    """Bring an older-version payload up to `SNAPSHOT_VERSION` in place.

    Each step is a pure layout migration.
    """
    if version < 1:
        # 0 -> 1: the new keys are all optional on read, so nothing to move.
        snapshot.setdefault("pending_events", [])
    if version < 2:
        # 1 -> 2: records gain a `kind`. A v1 record never persisted engine
        # events (they were dropped, #87) and never persisted provenance
        # (#86), so the only thing to recover is the ENGINE-SHAPED plain
        # `Event`s the 0.8.1 escalate/sentinel paths wrote. `restore_event`
        # re-derives those by name when `kind` is absent; leave the records
        # untouched and let it decide.
        pass
    return snapshot
