# tests/test_perf_regressions_307.py
# -----------------------------------------------------------------------------
# 📏 #307 perf gate: the two regressions the nightly caught, pinned cheaply
# -----------------------------------------------------------------------------
# 🏛️ Why these are shape tests and not timing tests: a microsecond
#    assertion on a shared runner is flaky by construction. Each regression
#    has a deterministic SHAPE, so it is pinned here for every default test
#    run, while the opt-in budgets test (`tests/test_perf_budgets.py`)
#    measures the microseconds on the nightly:
#
#    1. The per-event context before-image deep-copied the idempotency
#       plugin's 64-entry bookkeeping ring twice per event. `__xsm_*`
#       context keys are reserved for the library, so they are excluded
#       from the before-image and from the receipt's "changed" compare.
#    2. `persisted()` / `apersisted()` resolved `from_snapshot`'s signature
#       with `inspect.signature` on EVERY round trip (~40 us each). The
#       accepted keyword names are a fixed library API: resolve once.
# -----------------------------------------------------------------------------
"""Regression shapes for the two #307 perf-gate findings."""

from __future__ import annotations

import unittest
from typing import Any, Dict
from unittest import mock

from src.xstate_statemachine import (
    MachineLogic,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.persistence import helpers


def _inc(
    interp: Any, context: Dict[str, int], event: Any, action: Any
) -> None:
    context["n"] += 1


def _touch_internal(
    interp: Any, context: Dict[str, Any], event: Any, action: Any
) -> None:
    """Write only to the library's reserved bookkeeping key."""
    context.setdefault("__xsm_processed_ids__", []).append("x")


def _machine(actions: Dict[str, Any]) -> Any:
    return create_machine(
        {
            "id": "perf",
            "initial": "a",
            "context": {"n": 0},
            "states": {
                "a": {
                    "on": {
                        "TICK": {"actions": ["inc"]},
                        "PING": {"actions": ["touch"]},
                    }
                }
            },
        },
        logic=MachineLogic(actions=actions),
    )


class TestInternalContextKeysAreNotState(unittest.TestCase):
    """`__xsm_*` keys are bookkeeping: never copied, never "changed"."""

    def test_before_image_excludes_internal_keys(self) -> None:
        interp = SyncInterpreter(_machine({"inc": _inc})).start()
        try:
            interp.context["__xsm_processed_ids__"] = ["s|k"] * 64
            interp.context["__xsm_processed_at__"] = {"s|k": [1.0, "fp"]}
            self.assertEqual(interp._context_before_image(), {"n": 0})
        finally:
            interp.stop()

    def test_only_internal_writes_are_not_a_change(self) -> None:
        interp = SyncInterpreter(
            _machine({"inc": _inc, "touch": _touch_internal})
        ).start()
        try:
            receipt = interp.send("PING", wait=True)
            self.assertFalse(receipt.changed)
        finally:
            interp.stop()

    def test_user_changes_are_still_reported(self) -> None:
        interp = SyncInterpreter(_machine({"inc": _inc})).start()
        try:
            interp.context["__xsm_processed_ids__"] = ["s|k"]
            receipt = interp.send("TICK", wait=True)
            self.assertTrue(receipt.changed)
        finally:
            interp.stop()

    def test_non_mapping_context_is_copied_whole(self) -> None:
        """A context replaced by a non-dict object keeps the old compare."""
        interp = SyncInterpreter(_machine({"inc": _inc})).start()
        try:
            interp.context = [1, 2]
            image = interp._context_before_image()
            self.assertEqual(image, [1, 2])
            self.assertIsNot(image, interp.context)
            interp.context.append(3)
            self.assertTrue(interp._context_changed(image))
        finally:
            interp.stop()


class TestIdempotencyRingStaysCheap(unittest.TestCase):
    """The ring/evidence update is in place and bounded (#307)."""

    @staticmethod
    def _plugin() -> Any:
        from src.xstate_statemachine.persistence import MemoryInbox
        from src.xstate_statemachine.persistence.idempotency import (
            IdempotencyPlugin,
        )

        return IdempotencyPlugin(MemoryInbox(), principal=lambda e: "p")

    def test_remember_is_a_no_op_without_a_mapping_context(self) -> None:
        plugin = self._plugin()
        fake = type("I", (), {"context": []})()
        self.assertEqual(plugin._ring(fake), [])
        plugin._remember(fake, "s|k", "fp")
        plugin._store_ring(fake, ["s|k"])
        self.assertEqual(fake.context, [])

    def test_remember_updates_the_ring_in_place(self) -> None:
        """⚡ The shape that keeps the row cheap: append, never rebuild.

        A refactor back to "copy the ring, append, store a fresh list and a
        fresh evidence dict" would pass every other test in this file --
        and put the nightly `plugins_sync` row back at 2x its reference.
        """
        from src.xstate_statemachine.persistence.idempotency import (
            PROCESSED_AT_KEY,
            PROCESSED_IDS_KEY,
        )

        plugin = self._plugin()
        fake = type("I", (), {"context": {}})()
        plugin._remember(fake, "s|a", "fp")
        ring = fake.context[PROCESSED_IDS_KEY]
        at = fake.context[PROCESSED_AT_KEY]
        plugin._remember(fake, "s|b", "fp")
        self.assertIs(fake.context[PROCESSED_IDS_KEY], ring)
        self.assertIs(fake.context[PROCESSED_AT_KEY], at)
        self.assertEqual(ring, ["s|a", "s|b"])

    def test_eviction_keeps_evidence_while_a_duplicate_remains(self) -> None:
        """🛡️ A key re-processed after its TTL sits twice in the ring.

        Evicting the OLDER copy must not drop the FRESH evidence: the id is
        still ringed, and `_ring_evidence` would otherwise admit a
        redelivery the snapshot still covers (keys are reusable after
        `ttl_s`, so the duplicate is legitimate).
        """
        from src.xstate_statemachine.persistence.idempotency import (
            PROCESSED_AT_KEY,
            PROCESSED_IDS_KEY,
            PROCESSED_RING_SIZE,
        )

        plugin = self._plugin()
        ring = (
            ["p|k"]
            + [f"p|{i}" for i in range(PROCESSED_RING_SIZE - 2)]
            + ["p|k"]
        )
        fake = type("I", (), {"context": {}})()
        fake.context[PROCESSED_IDS_KEY] = list(ring)
        fake.context[PROCESSED_AT_KEY] = {
            "p|k": [1.0, "fresh"],
            "p|0": [0.0, "old"],
        }
        plugin._remember(fake, "p|new", "fp")
        self.assertEqual(
            fake.context[PROCESSED_AT_KEY].get("p|k"),
            [1.0, "fresh"],
        )
        self.assertEqual(
            len(fake.context[PROCESSED_IDS_KEY]), PROCESSED_RING_SIZE
        )
        # ... and the evidence IS dropped once no occurrence remains.
        plugin._remember(fake, "p|next", "fp")
        self.assertNotIn("p|0", fake.context[PROCESSED_AT_KEY])


class TestRestoreKwargsAreResolvedOnce(unittest.TestCase):
    """`inspect.signature` must not run per `persisted()` round trip."""

    def test_the_signature_is_not_recomputed_per_call(self) -> None:
        helpers._check_restore_kwargs({})
        with mock.patch.object(helpers.inspect, "signature") as signature:
            helpers._check_restore_kwargs({"restart_timers": "resume"})
        signature.assert_not_called()

    def test_unknown_options_still_raise(self) -> None:
        with self.assertRaises(TypeError):
            helpers._check_restore_kwargs({"nope": True})

    def test_the_cached_names_are_the_documented_ones(self) -> None:
        for name in (
            "restart_timers",
            "restart_services",
            "verify_machine_hash",
            "expected_machine_hash",
            "migrator",
        ):
            self.assertIn(name, helpers._RESTORE_KWARGS)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
