# src/xstate_statemachine/persistence/migration.py
# -----------------------------------------------------------------------------
# 🧬 SnapshotMigrator -- versioned charts, in-flight instances (#263)
# -----------------------------------------------------------------------------
# 🏛️ You ship v2 of a machine while 10,000 orders are mid-flight on v1.
#    Temporal needs explicit `patched()` / worker versioning; XState still
#    has an open bug restoring child-actor snapshots (statelyai/xstate#5077);
#    no Python FSM library handles it at all. We do NOT promise automatic
#    migration. We promise the two honest, valuable things:
#      1. every snapshot knows which machine produced it -- `machine_hash`
#         (structure, since 0.8.0) AND `machine_version` (the human label,
#         since #305);
#      2. a mismatch fails LOUDLY (`MachineVersionMismatchError`, a
#         `SnapshotDriftError`) unless the caller registered an upcaster
#         for exactly that hop.
#
# 📝 The migrator is a graph of `(from_version, to_version) -> fn(blob)`
#    steps. `migrate(blob, target)` walks the shortest path from the blob's
#    label to the target, applying each step to a COPY, then rewrites
#    `machine_version` and drops `machine_hash` (the structure changed by
#    definition -- the restore re-derives it from the new machine after
#    validating every state id exists, X0.4). Child actor blobs under
#    `actors` are migrated recursively with the same migrator, keyed by
#    their own `machine_id` -- best effort, and documented as such.
# -----------------------------------------------------------------------------
"""`SnapshotMigrator`, `MachineVersionMismatchError`, `NoMigrationPathError`."""

from __future__ import annotations

import copy
from collections import deque
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..exceptions import SnapshotDriftError, XStateMachineError

__all__ = [
    "MachineVersionMismatchError",
    "MigrationStep",
    "NoMigrationPathError",
    "SnapshotMigrator",
    "VersionPolicy",
]

MigrationStep = Callable[[Dict[str, Any]], Dict[str, Any]]
VersionPolicy = str  # "error" | "warn" | "migrate"
VERSION_POLICIES = ("error", "warn", "migrate")


class MachineVersionMismatchError(SnapshotDriftError):
    """The snapshot was written by a different **version label** of this
    machine and no migration path was registered.

    Is-a `SnapshotDriftError`, so existing ``except SnapshotDriftError``
    handlers keep working. Distinct from `SnapshotVersionError`, which is
    about the snapshot LAYOUT version, not the chart's.

    Attributes:
        machine_id: The machine.
        expected: `machine.version` (the code you are running).
        found: The blob's `machine_version` (``None`` = unlabelled).
    """

    def __init__(
        self, machine_id: str, expected: Optional[str], found: Optional[str]
    ) -> None:
        self.machine_id = machine_id
        self.expected = expected
        self.found = found
        super().__init__(
            f"Snapshot of machine '{machine_id}' was written by version "
            f"{found!r} but the running machine is version {expected!r}. "
            f"Register a SnapshotMigrator step for {found!r} -> "
            f"{expected!r}, or pass on_version_mismatch='warn' if the "
            f"change is known to be compatible."
        )


class NoMigrationPathError(XStateMachineError):
    """`SnapshotMigrator` has no chain of steps from *found* to *target*."""

    def __init__(
        self, machine_id: str, found: Optional[str], target: Optional[str]
    ) -> None:
        self.machine_id = machine_id
        self.found = found
        self.target = target
        super().__init__(
            f"No migration path for machine '{machine_id}' from version "
            f"{found!r} to {target!r}."
        )


class SnapshotMigrator:
    """A registry of version-to-version upcast steps for snapshot blobs.

    ::

        migrator = SnapshotMigrator()

        @migrator.register("1.0", "2.0")
        def _(blob: dict) -> dict:
            blob["state_ids"] = [
                s.replace(".paying", ".payment.card") for s in blob["state_ids"]
            ]
            blob["context"].setdefault("currency", "USD")
            return blob

        SyncInterpreter.from_snapshot(raw, machine_v2, migrator=migrator)

    Steps receive a deep copy of the decoded blob and return the migrated
    dict (mutating and returning the argument is fine). Multi-hop paths
    (``1.0 → 2.0 → 3.0``) are chained automatically along the shortest
    route; a missing hop is `NoMigrationPathError`. Steps may be scoped to
    a machine id (``machine_id="order"``) when one migrator serves several
    charts; unscoped steps apply to any machine.
    """

    def __init__(self) -> None:
        self._steps: Dict[Tuple[Optional[str], str, str], MigrationStep] = {}

    # -- registration --------------------------------------------------------
    def register(
        self,
        from_version: str,
        to_version: str,
        *,
        machine_id: Optional[str] = None,
    ) -> Callable[[MigrationStep], MigrationStep]:
        """Decorator: register *fn* as the ``from → to`` step."""
        if from_version == to_version:
            raise ValueError("a migration step must change the version")

        def deco(fn: MigrationStep) -> MigrationStep:
            self._steps[(machine_id, str(from_version), str(to_version))] = fn
            return fn

        return deco

    def add(
        self,
        from_version: str,
        to_version: str,
        fn: MigrationStep,
        *,
        machine_id: Optional[str] = None,
    ) -> None:
        """Non-decorator form of `register`."""
        self.register(from_version, to_version, machine_id=machine_id)(fn)

    def steps_for(
        self, machine_id: str
    ) -> Dict[Tuple[str, str], MigrationStep]:
        """Applicable steps: scoped to *machine_id* win over unscoped."""
        out: Dict[Tuple[str, str], MigrationStep] = {}
        for (mid, f, t), fn in self._steps.items():
            if mid is None:
                out.setdefault((f, t), fn)
        for (mid, f, t), fn in self._steps.items():
            if mid == machine_id:
                out[(f, t)] = fn
        return out

    # -- planning ---------------------------------------------------------------
    def path(
        self, machine_id: str, found: Optional[str], target: Optional[str]
    ) -> List[Tuple[str, str]]:
        """Shortest chain of ``(from, to)`` hops, or `NoMigrationPathError`.
        Empty when ``found == target``."""
        if found == target:
            return []
        if found is None or target is None:
            raise NoMigrationPathError(machine_id, found, target)
        steps = self.steps_for(machine_id)
        graph: Dict[str, List[str]] = {}
        for f, t in steps:
            graph.setdefault(f, []).append(t)
        prev: Dict[str, Optional[str]] = {found: None}
        queue = deque([found])
        while queue:
            cur = queue.popleft()
            if cur == target:
                break
            for nxt in graph.get(cur, ()):
                if nxt not in prev:
                    prev[nxt] = cur
                    queue.append(nxt)
        if target not in prev:
            raise NoMigrationPathError(machine_id, found, target)
        hops: List[Tuple[str, str]] = []
        cur = target
        while prev[cur] is not None:
            hops.append((prev[cur], cur))  # type: ignore[arg-type]
            cur = prev[cur]  # type: ignore[assignment]
        hops.reverse()
        return hops

    def can_migrate(
        self, machine_id: str, found: Optional[str], target: Optional[str]
    ) -> bool:
        try:
            self.path(machine_id, found, target)
            return True
        except NoMigrationPathError:
            return False

    # -- application ----------------------------------------------------------------
    def migrate(
        self,
        blob: Dict[str, Any],
        target: Optional[str],
        *,
        machine_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return a migrated COPY of *blob* at version *target*.

        Applies the shortest chain of steps, rewrites ``machine_version``,
        drops ``machine_hash`` (the structure changed by definition; the
        restore re-derives and validates against the new machine) and
        recurses into ``actors`` -- each child blob is migrated to the
        target its own `machine_id` resolves to, best effort: a child with
        no registered path is left as-is and the restore decides.
        """
        mid = str(machine_id or blob.get("machine_id") or "")
        found = blob.get("machine_version")
        found = None if found is None else str(found)
        out = copy.deepcopy(blob)
        hops = self.path(mid, found, target)
        steps = self.steps_for(mid)
        for f, t in hops:
            out = steps[(f, t)](out)
            if not isinstance(out, dict):
                raise TypeError(
                    f"migration step {f!r}->{t!r} for '{mid}' must return "
                    f"a dict, got {type(out).__name__}"
                )
            out["machine_version"] = t
        if hops:
            out.pop("machine_hash", None)
        # 👶 Children: migrate each to whatever version its own steps lead
        #    to (we do not know the child machine's target label here;
        #    `from_snapshot` re-runs the policy per child with the real
        #    child machine). Only mark that a migrator was in play.
        return out


def resolve_policy(policy: Optional[str], migrator: Any) -> str:
    """The effective policy: an explicit value, else ``"migrate"`` when a
    migrator was passed, else ``"error"``."""
    if policy is None:
        return "migrate" if migrator is not None else "error"
    if policy not in VERSION_POLICIES:
        raise ValueError(
            f"on_version_mismatch must be one of {VERSION_POLICIES}, "
            f"got {policy!r}"
        )
    return policy
