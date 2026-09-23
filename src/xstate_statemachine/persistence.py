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
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

from .exceptions import SnapshotDriftError, SnapshotVersionError

if TYPE_CHECKING:  # pragma: no cover
    from .models import MachineNode, StateNode, TransitionDefinition

#: Current snapshot payload layout. History:
#:   0 -- unversioned 0.7.x payload (implicit; no ``version`` key)
#:   1 -- 0.8.0: adds ``version``, ``machine_id``, ``machine_hash``,
#:        ``taken_at``, ``pending_events``, ``value``
#:   2 -- 0.9.0: every ``pending_events`` / ``deferred`` record carries a
#:        ``kind`` (``event`` | ``system`` | ``done`` | ``error`` | ``after``)
#:        so engine events and provenance round-trip (#86, #87). ``done``
#:        records add ``data`` + ``src``; ``error`` records add ``error``
#:        (repr) + ``src``.
SNAPSHOT_VERSION: int = 3


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


def check_minimum_version(version: int, minimum: int) -> None:
    """#205: refuse a payload older than the caller's floor.

    ``version`` is the value `check_version` returned. A caller who never
    persisted version-0 payloads (every 0.9.0 writer records ``version``
    and ``machine_hash``) can set ``minimum=1`` so a blob that has had its
    version key stripped -- the one shape the drift check cannot cover --
    is refused instead of restored unchecked.
    """
    if minimum and version < minimum:
        raise SnapshotVersionError(version, SNAPSHOT_VERSION, minimum=minimum)


_VALID_STATUSES = frozenset(
    {"uninitialized", "running", "stopped", "done", "error"}
)


def check_shape(snapshot: Dict[str, Any], *, version: int = 0) -> None:
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
    # 🛡️ #186: `configuration` (leaves + ancestors) and `state_ids`
    #    (leaves) describe the SAME configuration; the library writes both.
    #    When both are present they must agree -- every leaf in `state_ids`
    #    is in `configuration`, and `configuration` is not empty while
    #    `state_ids` is not. A blob where they disagree was edited or
    #    corrupted, and restoring from whichever one "wins" is a guess.
    configuration = snapshot.get("configuration")
    leaves = set(snapshot["state_ids"])
    # 🛡️ #198 (reopen of #186): a `version >= 1` payload DECLARES that it
    #    carries both fields -- every writer since v1 has -- so on such a
    #    payload an absent or empty field is not "no opinion", it is
    #    disagreement, and the strictly simpler mutation of emptying one
    #    field must be refused exactly like contradicting it. Only a v0
    #    payload (no `version` key; written before `configuration`
    #    existed) may carry `state_ids` alone.
    versioned = version >= 1
    if versioned and status == "running":
        if configuration is None:
            fail(
                "version >= 1 snapshot of a running machine has no "
                "'configuration' field -- the writer always records it, so "
                "the field was dropped"
            )
        if not configuration:
            fail(
                "version >= 1 snapshot of a running machine has an empty "
                "'configuration' -- the two fields contradict each other"
            )
        if not leaves:
            fail(
                "version >= 1 snapshot of a running machine has an empty "
                "'state_ids' while 'configuration' names "
                f"{sorted(configuration or [])} -- the two fields "
                f"contradict each other"
            )
    if configuration is not None:
        full = set(configuration)
        if leaves and not full:
            fail(
                "'configuration' is empty while 'state_ids' names "
                f"{sorted(leaves)} -- the two fields contradict each other"
            )
        missing = leaves - full
        if missing:
            fail(
                f"'state_ids' names {sorted(missing)} which 'configuration' "
                f"does not contain -- the two fields contradict each other"
            )
    # 🛡️ #145 (read side): an "error" machine always knows WHY -- `_fail`
    #    and `_die` both set `error`. A blob claiming "error" with nothing
    #    to say is not one this library wrote.
    if status == "error" and not snapshot.get("error"):
        fail("status is 'error' but no 'error' message is recorded")
    for key in ("pending_events", "deferred", "scheduled_sends"):
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
    # 🛡️ #241: the #226 chain-trip fields. They were read and coerced
    #    AFTER this validator had passed the blob, so a malformed value
    #    escaped `from_snapshot` as a bare ValueError / TypeError and broke
    #    the `except SnapshotCorruptError: quarantine` idiom. `chain_trips`
    #    is a non-negative integer (a JSON writer may have stored it as a
    #    numeric string; `bool` is an int subclass and is NOT a count);
    #    `last_chain_error` is the latched message or null.
    trips = snapshot.get("chain_trips")
    if trips is not None:
        if isinstance(trips, bool) or not isinstance(trips, (int, str)):
            fail(
                f"'chain_trips' is {type(trips).__name__}, expected a "
                f"non-negative integer"
            )
        try:
            count = int(trips)
        except ValueError:
            fail(f"'chain_trips' {trips!r} is not an integer")
        else:
            if count < 0:
                fail(f"'chain_trips' {count} is negative")
    latched = snapshot.get("last_chain_error")
    if latched is not None and not isinstance(latched, str):
        fail(
            f"'last_chain_error' is {type(latched).__name__}, expected a "
            f"string message or null"
        )
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
    snapshot: Dict[str, Any],
    machine: "MachineNode",
    *,
    verify_hash: bool,
    version: Optional[int] = None,
    expected_hash: Optional[str] = None,
) -> None:
    """Refuse to restore a snapshot into a machine it was not taken from.

    Version-0 payloads (no ``version`` key) carry neither field and are
    accepted unchecked -- they cannot be drift-checked, which is precisely
    why the fields exist.

    🛡️ #185: the bypass is keyed on the DECLARED VERSION, not on whether
    the field happens to be present. Every ``version >= 1`` payload this
    library writes carries ``machine_hash``; one that arrives with the
    key missing or ``null`` has lost it in transit (a JSON round-trip that
    drops nulls, a column default, a lossy migration) and can no longer be
    drift-checked -- so under ``verify_hash`` it is refused, exactly as a
    wrong hash is. Keying on presence turned "the fingerprint was lost"
    into "skip the fingerprint", and a drifted machine restored silently
    with the wrong active states.

    Args:
        snapshot: The decoded payload.
        machine: The machine being restored into.
        verify_hash: When ``True`` (the default at the call site) the
            structural hash must be present and match.
        version: The payload's declared version (from `check_version`).
            ``None`` / ``0`` selects the legacy unchecked path.
        expected_hash: #205 -- a fingerprint the CALLER holds. When given,
            the payload's ``machine_hash`` must equal it (and it must equal
            the machine's), regardless of version; the payload's own claim
            is never trusted to validate itself.

    Raises:
        SnapshotDriftError: machine id differs, or (when *verify_hash*)
            the structural hash differs or is missing from a versioned
            payload.
    """
    snap_id = snapshot.get("machine_id")
    if snap_id is not None and snap_id != machine.id:
        raise SnapshotDriftError(
            f"snapshot was taken from machine '{snap_id}' but is being "
            f"restored into '{machine.id}'"
        )
    if not verify_hash:
        return
    snap_hash = snapshot.get("machine_hash")
    # 🔐 #205: when the CALLER supplies the fingerprint the payload must
    #    match, it is compared against THAT -- a value the caller holds --
    #    rather than letting an attacker-controlled field validate itself.
    #    Absent or different is drift; the payload's own claim is not
    #    consulted.
    if expected_hash is not None:
        if snap_hash != expected_hash:
            raise SnapshotDriftError(
                f"snapshot 'machine_hash' {snap_hash!r} does not match the "
                f"caller's expected_machine_hash {expected_hash!r} for "
                f"machine '{machine.id}' (#205)."
            )
        if expected_hash != machine.structure_hash:
            raise SnapshotDriftError(
                f"caller's expected_machine_hash {expected_hash!r} does not "
                f"match machine '{machine.id}' ({machine.structure_hash}); "
                f"the machine changed since that fingerprint was recorded."
            )
        return
    versioned = bool(version)
    if snap_hash is None:
        if not versioned:
            return  # v0: nothing to check against, by design
        raise SnapshotDriftError(
            f"snapshot declares version {version} but carries no "
            f"'machine_hash', so it cannot be checked against machine "
            f"'{machine.id}' (#185). The field was lost in transit; "
            f"restore from an intact copy, or pass "
            f"verify_machine_hash=False if the machine is known to be "
            f"unchanged."
        )
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
        # `Event`s the 0.9.0 escalate/sentinel paths wrote. `restore_event`
        # re-derives those by name when `kind` is absent; leave the records
        # untouched and let it decide.
        pass
    if version < 3:
        # 2 -> 3 (#214): records gain `engine` (provenance, #195) and `lane`.
        # A v2 writer had exactly ONE minter of `done` / `error` / `after`
        # records -- the engine itself; the public NamedTuples could not
        # reach `pending_events` except through it. So a v2 record of those
        # kinds IS an engine completion and is upcast as one, keeping the
        # persisted deadline it represents instead of demoting it to inert
        # user traffic (#203's gate then silently dropped a 0.8.0-era
        # `after`). Only a v3 record can carry a deliberately unflagged
        # (hand-written) completion.
        for key in ("pending_events", "deferred"):
            for rec in snapshot.get(key) or []:
                if isinstance(rec, dict) and rec.get("kind") in (
                    "done",
                    "error",
                    "after",
                ):
                    rec.setdefault("engine", True)
    return snapshot
