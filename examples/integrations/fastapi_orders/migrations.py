# examples/integrations/fastapi_orders/migrations.py
# -----------------------------------------------------------------------------
# 🧬 Chart v1 -> v2 while orders are mid-flight (#263)
# -----------------------------------------------------------------------------
# 🏛️ v2 splits `paying` (one gateway call) into `payment.authorising` ->
#    `payment.capturing` (authorise, then capture) and adds a `currency`
#    context key. Thousands of v1 orders are persisted when v2 deploys;
#    none of them is re-written in bulk. Instead this `SnapshotMigrator`
#    step is applied LAZILY, the first time a v1 blob is touched by a v2
#    worker (a request, or the scheduler waking a retry deadline), and the
#    re-save happens at the new label inside the same optimistic save, so
#    two workers racing on one stale order still produce exactly one
#    migrated record (the other gets 409, as for any lost race).
#
# 📝 What the step must rewrite, and why:
#    * `state_ids` / `configuration`: a v1 order in `order.paying` was in
#      the middle of a charge whose outcome we do not have (the invoke
#      died with the v1 process). The honest v2 state is
#      `order.payment.authorising` -- the charge is re-attempted; the fake
#      gateway's charge id is derived from (order, total) so a real
#      gateway's idempotency key would recognise the replay (X0.6).
#    * `context.currency`: a new key with a default. The restore layers
#      the blob over the chart's defaults, so this line is belt-and-braces;
#      it documents the intent.
#    * `deadlines`: v1 deadlines are keyed by STATE ID. A deadline parked
#      on `order.paying`'s invoke does not exist (invokes are not
#      deadlines); the `retrying` and `awaitingPayment` deadlines keep
#      their ids, which v2 kept too. Nothing to do -- asserted by the test.
#    Everything else (`pending_events`, `history`, `actors`) is untouched.
# -----------------------------------------------------------------------------
"""The `SnapshotMigrator` for the orders chart: v1 -> v2."""

from __future__ import annotations

from typing import Any, Dict

from xstate_statemachine.persistence import SnapshotMigrator

V1_PAYING = "order.paying"
V2_AUTHORISING = "order.payment.authorising"


def v1_to_v2(blob: Dict[str, Any]) -> Dict[str, Any]:
    """Rewrite a v1 order snapshot into v2 shape.

    The library validates the result against the v2 chart (every state id
    must exist, the configuration must be legal, the context model still
    applies) -- a mistake here is refused loudly, never half-restored.
    """
    blob["state_ids"] = [
        V2_AUTHORISING if s == V1_PAYING else s for s in blob["state_ids"]
    ]
    # 📝 `configuration` (leaves + ancestors) is rebuilt by the restore
    #    from `state_ids` against the v2 chart when a step leaves it
    #    untouched (#263 battle) -- so rewriting the leaves is enough.
    #    Rewrite it too if you prefer to be explicit; a step that sets
    #    the two fields to DISAGREE is refused with `SnapshotCorruptError`.
    blob.setdefault("context", {}).setdefault("currency", "USD")
    return blob


def build_migrator() -> SnapshotMigrator:
    migrator = SnapshotMigrator()
    migrator.add("1", "2", v1_to_v2, machine_id="order")
    return migrator
