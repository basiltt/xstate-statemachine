# tests/persistence/test_battle_263_migration_semantics.py
"""Battle test #263 part A (1/2): restore + migrate SEMANTICS.

The issue's own acceptance recipe, the structural-hash contract (plus a
Stately-corpus sample), version-label coercion, the migrator graph, user
steps that misbehave, and child actors. The runtime half (both engines
under `persisted()`, the scanner, leaks, cross-engine) lives in
`test_battle_263_migration_runtime.py`.
"""

from __future__ import annotations

import copy
import gc
import glob
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List

import pytest

from src.xstate_statemachine import (
    Interpreter,
    MachineLogic,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.exceptions import (
    InvalidConfigError,
    SnapshotCorruptError,
    StateNotFoundError,
    XStateMachineError,
)
from src.xstate_statemachine.persistence import (
    MachineVersionMismatchError,
    MemoryStore,
    NoMigrationPathError,
    SnapshotMigrator,
    persisted,
)
from src.xstate_statemachine.testing_utils import stub_logic

ROOT = Path(__file__).resolve().parents[2]

V1: Dict[str, Any] = {
    "id": "o",
    "version": "1.0",
    "initial": "paying",
    "states": {"paying": {"on": {"OK": "done"}}, "done": {"type": "final"}},
}
V2: Dict[str, Any] = {
    "id": "o",
    "version": "2.0",
    "initial": "payment",
    "states": {
        "payment": {
            "initial": "card",
            "states": {"card": {"on": {"OK": "#o.done"}}},
        },
        "done": {"type": "final"},
    },
}


def blob_v1(cfg: Dict[str, Any] = V1) -> str:
    i = SyncInterpreter(create_machine(cfg)).start()
    try:
        return i.get_snapshot()
    finally:
        i.stop()


def rename_ids(b: Dict[str, Any]) -> Dict[str, Any]:
    # 📝 The issue's verbatim step: rewrites `state_ids` ONLY.
    b["state_ids"] = [
        "o.payment.card" if s == "o.paying" else s for s in b["state_ids"]
    ]
    return b


def _mig(fn: Any, f: str = "1.0", t: str = "2.0", **kw: Any) -> Any:
    m = SnapshotMigrator()
    m.add(f, t, fn, **kw)
    return m


# -----------------------------------------------------------------------------
# 1. The issue's acceptance recipe
# -----------------------------------------------------------------------------
class TestIssueRecipe:
    def test_issue_verbatim_recipe_restores_both_engines(self) -> None:
        # Arrange -- exactly the issue body: only `state_ids` is rewritten.
        mig = SnapshotMigrator()

        @mig.register("1.0", "2.0")
        def up(b: Dict[str, Any]) -> Dict[str, Any]:
            b["state_ids"] = [
                "o.payment.card" if s == "o.paying" else s
                for s in b["state_ids"]
            ]
            b["context"].setdefault("currency", "USD")
            return b

        m2 = create_machine(V2)
        blob = blob_v1()
        with pytest.raises(MachineVersionMismatchError):
            SyncInterpreter.from_snapshot(blob, m2)

        # Act
        s = SyncInterpreter.from_snapshot(blob, m2, migrator=mig)
        a = Interpreter.from_snapshot(blob, m2, migrator=mig)

        # Assert -- 🐛 was "the two fields contradict each other".
        assert "o.payment.card" in s.current_state_ids
        assert a.current_state_ids == s.current_state_ids
        assert s.context["currency"] == "USD"
        s.start()
        s.send("OK")
        assert s.current_state_ids == {"o.done"}
        s.stop()

    def test_derived_configuration_includes_new_ancestors(self) -> None:
        i = SyncInterpreter.from_snapshot(
            blob_v1(), create_machine(V2), migrator=_mig(rename_ids)
        )
        conf = json.loads(i.get_snapshot())["configuration"]
        assert set(conf) == {"o", "o.payment", "o.payment.card"}

    def test_step_setting_configuration_none_is_derived(self) -> None:
        def step(b: Dict[str, Any]) -> Dict[str, Any]:
            return {
                **rename_ids(b),
                "configuration": None,
            }

        i = SyncInterpreter.from_snapshot(
            blob_v1(), create_machine(V2), migrator=_mig(step)
        )
        assert i.current_state_ids == {"o.payment.card"}

    def test_step_rewriting_both_inconsistently_names_the_hop(self) -> None:
        def step(b: Dict[str, Any]) -> Dict[str, Any]:
            b = rename_ids(b)
            b["configuration"] = ["o", "o.done"]
            return b

        with pytest.raises(SnapshotCorruptError) as ei:
            SyncInterpreter.from_snapshot(
                blob_v1(), create_machine(V2), migrator=_mig(step)
            )
        assert "'1.0'->'2.0'" in str(ei.value) and "'o'" in str(ei.value)

    def test_derived_unknown_id_is_state_not_found(self) -> None:
        step = lambda b: {**b, "state_ids": ["o.ghost"]}  # noqa: E731
        with pytest.raises(StateNotFoundError):
            SyncInterpreter.from_snapshot(
                blob_v1(), create_machine(V2), migrator=_mig(step)
            )

    def test_ancestor_only_state_id_is_refused(self) -> None:
        # 📝 "o.payment" is compound; no leaf -> not a legal configuration.
        step = lambda b: {**b, "state_ids": ["o.payment"]}  # noqa: E731
        with pytest.raises(SnapshotCorruptError):
            SyncInterpreter.from_snapshot(
                blob_v1(), create_machine(V2), migrator=_mig(step)
            )


# -----------------------------------------------------------------------------
# 2. Structural hash contract
# -----------------------------------------------------------------------------
BASE: Dict[str, Any] = {
    "id": "h",
    "initial": "a",
    "states": {
        "a": {
            "entry": ["e1", "e2"],
            "on": {
                "GO": {
                    "target": "b",
                    "guard": "g1",
                    "actions": ["x1", "x2"],
                }
            },
            "after": {"1000": "b"},
            "invoke": {"src": "svc", "id": "inv"},
        },
        "b": {"on": {"BACK": "a"}},
    },
}


def _h(cfg: Dict[str, Any]) -> str:
    return create_machine(cfg, logic=stub_logic(cfg)).structure_hash


def _edit(path: List[Any], value: Any) -> Dict[str, Any]:
    cfg = copy.deepcopy(BASE)
    node: Any = cfg
    for p in path[:-1]:
        node = node[p]
    node[path[-1]] = value
    return cfg


GO = ["states", "a", "on", "GO"]


class TestStructureHash:
    @pytest.mark.parametrize(
        "cfg",
        [
            json.loads(json.dumps(BASE, sort_keys=True, indent=7)),
            {k: BASE[k] for k in reversed(list(BASE))},
            _edit(["description"], "docs"),
            _edit(["states", "a", "meta"], {"x": 1}),
            _edit(["states", "a", "tags"], ["busy"]),
            _edit(["states", "a", "description"], "the a state"),
            _edit(
                GO + ["actions"],
                [{"type": "x1", "params": {"n": 9}}, "x2"],
            ),
        ],
    )
    def test_hash_is_stable_across_cosmetic_edits(self, cfg: Any) -> None:
        assert _h(cfg) == _h(BASE)

    @pytest.mark.parametrize(
        "cfg",
        [
            _edit(GO + ["target"], "a"),
            _edit(GO + ["guard"], "g2"),
            _edit(GO + ["guard"], {"type": "and", "children": ["g1", "g2"]}),
            _edit(
                GO + ["guard"],
                {"type": "stateIn", "params": {"stateValue": "b"}},
            ),
            _edit(GO + ["actions"], ["x2", "x1"]),
            _edit(GO + ["reenter"], True),
            _edit(["states", "a", "invoke"], {"src": "svc2", "id": "inv"}),
            _edit(["states", "a", "after"], {"2000": "b"}),
            _edit(["initial"], "b"),
            _edit(["states", "b", "type"], "final"),
        ],
    )
    def test_hash_changes_on_behavioural_edits(self, cfg: Any) -> None:
        assert _h(cfg) != _h(BASE)

    def test_composite_guard_child_change_changes_hash(self) -> None:
        a = _edit(GO + ["guard"], {"type": "and", "children": ["g1", "g2"]})
        b = _edit(GO + ["guard"], {"type": "and", "children": ["g1", "g3"]})
        assert _h(a) != _h(b)

    def test_stately_corpus_sample_hash_is_deterministic(self) -> None:
        # 📝 Some corpus charts are intentionally broken (template
        #    placeholders, missing `states`); count only those that build.
        ok = 0
        files = sorted(
            glob.glob(str(ROOT / "tests/tests_cli/stately_machines/*.json"))
        )
        logging.disable(logging.CRITICAL)
        try:
            for f in files:
                cfg = json.loads(Path(f).read_text(encoding="utf-8"))
                try:
                    h1 = _h(cfg)
                except XStateMachineError:
                    continue
                cfg2 = json.loads(json.dumps(cfg, sort_keys=True))
                assert _h(cfg) == h1 == _h(cfg2), f
                ok += 1
        finally:
            logging.disable(logging.NOTSET)
        assert ok >= 30, ok


# -----------------------------------------------------------------------------
# 3. Label coercion
# -----------------------------------------------------------------------------
class TestLabelCoercion:
    @pytest.mark.parametrize(
        "raw,label", [(1, "1"), ("1", "1"), (1.0, "1.0"), (True, "True")]
    )
    def test_chart_version_is_str_of_raw(self, raw: Any, label: str) -> None:
        cfg = {**V1, "version": raw}
        assert create_machine(cfg).version == label

    def test_int_and_str_label_are_the_same_version(self) -> None:
        blob = blob_v1({**V1, "version": 1})
        i = SyncInterpreter.from_snapshot(
            blob, create_machine({**V1, "version": "1"})
        )
        assert i.current_state_ids == {"o.paying"}

    def test_int_and_float_labels_differ_documented(self) -> None:
        # 📝 DOCUMENTED: 1 -> "1" and 1.0 -> "1.0" are different labels.
        with pytest.raises(MachineVersionMismatchError) as ei:
            SyncInterpreter.from_snapshot(
                blob_v1({**V1, "version": 1}),
                create_machine({**V1, "version": 1.0}),
            )
        assert (ei.value.found, ei.value.expected) == ("1", "1.0")
        assert all(
            isinstance(v, str) for v in (ei.value.found, ei.value.expected)
        )

    def test_store_column_is_text(self) -> None:
        store = MemoryStore()
        with persisted(store, "k", create_machine({**V1, "version": 1})):
            pass
        assert store.load("k").machine_version == "1"

    @pytest.mark.parametrize("mode", ["absent", "null"])
    def test_unlabelled_blob_restores(self, mode: str) -> None:
        # 🐛 `null` used to be a MISMATCH ("None" vs "1.0") although the
        #    library itself writes null for an unlabelled chart.
        raw = json.loads(blob_v1())
        if mode == "absent":
            del raw["machine_version"]
        else:
            raw["machine_version"] = None
        i = SyncInterpreter.from_snapshot(json.dumps(raw), create_machine(V1))
        assert i.current_state_ids == {"o.paying"}

    def test_empty_string_label_is_a_mismatch(self) -> None:
        # 📝 "" is a label the store writes for unlabelled charts but never
        #    the engine; treating it as a real (different) label is loud.
        raw = json.loads(blob_v1())
        raw["machine_version"] = ""
        with pytest.raises(MachineVersionMismatchError) as ei:
            SyncInterpreter.from_snapshot(json.dumps(raw), create_machine(V1))
        assert ei.value.found == ""

    def test_non_string_label_in_blob_is_corrupt_not_typeerror(self) -> None:
        raw = json.loads(blob_v1())
        raw["machine_version"] = ["1.0"]
        with pytest.raises(XStateMachineError):
            SyncInterpreter.from_snapshot(json.dumps(raw), create_machine(V1))


# -----------------------------------------------------------------------------
# 4. Migrator graph
# -----------------------------------------------------------------------------
def ident(b: Dict[str, Any]) -> Dict[str, Any]:
    return b


class TestMigratorGraph:
    def test_cycles_terminate_and_find_forward_path(self) -> None:
        m = SnapshotMigrator()
        for f, t in (("1", "2"), ("2", "1"), ("2", "3")):
            m.add(f, t, ident)
        assert m.path("o", "1", "3") == [("1", "2"), ("2", "3")]
        assert m.path("o", "3", "3") == []
        assert not m.can_migrate("o", "3", "1")

    def test_diamond_takes_shortest_then_earliest_registered(self) -> None:
        m = SnapshotMigrator()
        m.add("1", "2a", ident)
        m.add("1", "2b", ident)
        m.add("2b", "3", ident)
        m.add("2a", "3", ident)
        m.add("1", "x", ident)
        m.add("x", "y", ident)
        m.add("y", "3", ident)
        assert m.path("o", "1", "3") == [("1", "2a"), ("2a", "3")]

    def test_self_loop_rejected_including_int_vs_str(self) -> None:
        m = SnapshotMigrator()
        with pytest.raises(ValueError):
            m.register("1", "1")
        with pytest.raises(ValueError):  # 🐛 was silently accepted
            m.register(1, "1")  # type: ignore[arg-type]

    def test_duplicate_registration_last_wins(self) -> None:
        m = SnapshotMigrator()
        m.add("1", "2", lambda b: {**b, "tag": "first"})
        m.add("1", "2", lambda b: {**b, "tag": "second"})
        assert m.migrate({"machine_version": "1"}, "2")["tag"] == "second"

    def test_scoped_and_unscoped_hops_chain(self) -> None:
        m = SnapshotMigrator()
        m.add("1", "2", lambda b: {**b, "a": 1}, machine_id="o")
        m.add("2", "3", lambda b: {**b, "b": 1})
        out = m.migrate({"machine_version": "1"}, "3", machine_id="o")
        assert (out["a"], out["b"], out["machine_version"]) == (1, 1, "3")
        assert not m.can_migrate("other", "1", "3")

    def test_can_migrate_with_none_and_int_labels(self) -> None:
        m = _mig(ident, "1", "2")
        assert not m.can_migrate("o", None, "2")
        assert not m.can_migrate("o", "1", None)
        assert m.can_migrate("o", None, None)
        assert m.can_migrate("o", 1, 2)  # type: ignore[arg-type]

    def test_thousand_step_chain_plans_fast(self) -> None:
        m = SnapshotMigrator()
        for n in range(1000):
            m.add(str(n), str(n + 1), ident)
        t0 = time.perf_counter()
        hops = m.path("o", "0", "1000")
        assert time.perf_counter() - t0 < 0.05
        assert len(hops) == 1000


# -----------------------------------------------------------------------------
# 5. Steps are user code
# -----------------------------------------------------------------------------
def _restore_with(step: Any) -> Any:
    return SyncInterpreter.from_snapshot(
        blob_v1(), create_machine(V2), migrator=_mig(step)
    )


def _bad(**over: Any) -> Any:
    def step(b: Dict[str, Any]) -> Dict[str, Any]:
        return {**rename_ids(b), **over}

    return step


class _Boom(Exception):
    pass


def _raise(b: Dict[str, Any]) -> Dict[str, Any]:
    raise _Boom("disk on fire")


class TestUserSteps:
    def test_raising_step_is_typed_and_leaks_no_interpreter(self) -> None:
        gc.collect()
        before = sum(
            1 for o in gc.get_objects() if issubclass(type(o), SyncInterpreter)
        )
        for _ in range(20):
            with pytest.raises(SnapshotCorruptError) as ei:
                _restore_with(_raise)
            assert isinstance(ei.value.__cause__, _Boom)
            assert "'1.0'->'2.0'" in str(ei.value)
        del ei
        gc.collect()
        after = sum(
            1 for o in gc.get_objects() if issubclass(type(o), SyncInterpreter)
        )
        assert after <= before

    def test_library_error_from_step_passes_through(self) -> None:
        def step(b: Dict[str, Any]) -> Dict[str, Any]:
            raise StateNotFoundError(target="x")

        with pytest.raises(StateNotFoundError):
            _restore_with(step)

    @pytest.mark.parametrize(
        "step",
        [
            lambda b: "nope",
            lambda b: None,
            lambda b: [b],
            _bad(context=[1, 2]),
            _bad(status="zombie"),
            _bad(state_ids="o.payment.card"),
            _bad(state_ids=["o.payment.card", 7]),
            _bad(configuration="o"),
            _bad(
                deadlines=[
                    {
                        "state_id": "o.payment.card",
                        "entry_seq": 1,
                        "due_at_wall": float("nan"),
                        "delay_ms": 1,
                        "event_type": "after.1.o",
                    }
                ]
            ),
            _bad(pending_events=[{"type": 5}]),
            _bad(actors={"k": {"src": "nope"}}),
            _bad(actors={"k": {"src": "nope", "snapshot": "x"}}),
            _bad(actors=[1]),
            lambda b: {"machine_version": "1.0"},
            lambda b: {k: v for k, v in b.items() if k != "status"},
            lambda b: {k: v for k, v in b.items() if k != "context"},
            lambda b: {k: v for k, v in b.items() if k != "state_ids"},
        ],
    )
    def test_every_bad_step_output_is_a_typed_library_error(
        self, step: Any
    ) -> None:
        with pytest.raises(XStateMachineError) as ei:
            _restore_with(step)
        assert not isinstance(ei.value, (KeyError, AttributeError))

    def test_nul_and_huge_state_ids_are_refused_typed(self) -> None:
        with pytest.raises(StateNotFoundError):
            _restore_with(_bad(state_ids=["o.pay\x00ment.card"]))
        big = ["o.payment.card"] + [f"o.ghost{n}" for n in range(200_000)]
        with pytest.raises(StateNotFoundError):
            _restore_with(_bad(state_ids=big))

    def test_duplicate_configuration_entries_are_harmless(self) -> None:
        conf = ["o", "o", "o.payment", "o.payment.card", "o.payment.card"]
        i = _restore_with(_bad(configuration=conf))
        assert i.current_state_ids == {"o.payment.card"}

    def test_reserved_kwargs_in_pending_payload_are_inert(self) -> None:
        ev = {
            "kind": "event",
            "type": "OK",
            "payload": {"wait": True, "timeout": 0, "priority": True},
        }
        i = _restore_with(_bad(pending_events=[ev])).start()
        assert i.current_state_ids == {"o.done"}
        i.stop()

    def test_unknown_actor_src_is_parked_not_crashed(self) -> None:
        rec = {"src": "nope", "snapshot": json.loads(blob_v1())}
        i = _restore_with(_bad(actors={"k": rec}))
        assert "k" in i._pending_actor_snapshots

    def test_step_mutation_never_reaches_callers_blob(self) -> None:
        raw = json.loads(blob_v1())
        raw["context"] = {"nested": {"x": [1]}}
        frozen = copy.deepcopy(raw)

        def step(b: Dict[str, Any]) -> Dict[str, Any]:
            b["context"]["nested"]["x"].append(2)
            b["context"]["nested"]["y"] = 1
            return rename_ids(b)

        out = _mig(step).migrate(raw, "2.0", machine_id="o")
        assert raw == frozen
        assert out["context"]["nested"] == {"x": [1, 2], "y": 1}


# -----------------------------------------------------------------------------
# 6. Child actors
# -----------------------------------------------------------------------------
def _kid(cid: str, ver: str, leaf: str) -> Dict[str, Any]:
    return {
        "id": cid,
        "version": ver,
        "initial": leaf,
        "states": {leaf: {}},
    }


def _parent(services: Dict[str, Any], entry: List[str]) -> Any:
    cfg = {
        "id": "p",
        "version": "1",
        "initial": "a",
        "states": {"a": {"entry": entry}},
    }
    return create_machine(cfg, logic=MachineLogic(services=services))


def _two_kid_blob() -> str:
    m = _parent(
        {
            "k1": create_machine(_kid("k1", "1", "x")),
            "k2": create_machine(_kid("k2", "5", "x")),
        },
        ["spawn_k1", "spawn_k2"],
    )
    i = SyncInterpreter(m).start()
    try:
        return i.get_snapshot()
    finally:
        i.stop()


def _to(leaf: str, mid: str) -> Any:
    return lambda b: {
        **b,
        "state_ids": [f"{mid}.{leaf}"],
        "configuration": None,
    }


class TestChildActors:
    def test_one_child_without_path_fails_whole_restore_naming_it(
        self,
    ) -> None:
        m2 = _parent(
            {
                "k1": create_machine(_kid("k1", "2", "y")),
                "k2": create_machine(_kid("k2", "6", "y")),
            },
            ["spawn_k1", "spawn_k2"],
        )
        mig = _mig(_to("y", "k1"), "1", "2", machine_id="k1")
        with pytest.raises(MachineVersionMismatchError) as ei:
            SyncInterpreter.from_snapshot(_two_kid_blob(), m2, migrator=mig)
        assert ei.value.machine_id == "k2" and "'k2'" in str(ei.value)
        mig.add("5", "6", _to("y", "k2"), machine_id="k2")
        r = SyncInterpreter.from_snapshot(_two_kid_blob(), m2, migrator=mig)
        states = sorted(
            next(iter(c.current_state_ids)) for c in r._actors.values()
        )
        assert states == ["k1.y", "k2.y"]

    def test_parent_step_can_rename_child_src(self) -> None:
        m1 = _parent(
            {"old": create_machine(_kid("kid", "1", "x"))}, ["spawn_old"]
        )
        i = SyncInterpreter(m1).start()
        blob = i.get_snapshot()
        i.stop()
        m2 = create_machine(
            {
                "id": "p",
                "version": "2",
                "initial": "a",
                "states": {"a": {"entry": "spawn_new"}},
            },
            logic=MachineLogic(
                services={"new": create_machine(_kid("kid", "1", "x"))}
            ),
        )

        def step(b: Dict[str, Any]) -> Dict[str, Any]:
            for rec in b["actors"].values():
                rec["src"] = "new"
            return b

        r = SyncInterpreter.from_snapshot(
            blob, m2, migrator=_mig(step, "1", "2", machine_id="p")
        )
        (child,) = r._actors.values()
        assert child.current_state_ids == {"kid.x"}
        assert not r._pending_actor_snapshots

    def test_three_level_nesting_migrates_grandchild(self) -> None:
        def chain(gver: str, gleaf: str) -> Any:
            g = create_machine(_kid("g", gver, gleaf))
            c = create_machine(
                {
                    "id": "c",
                    "version": "1",
                    "initial": "a",
                    "states": {"a": {"entry": "spawn_g"}},
                },
                logic=MachineLogic(services={"g": g}),
            )
            return _parent({"c": c}, ["spawn_c"])

        i = SyncInterpreter(chain("1", "x")).start()
        blob = i.get_snapshot()
        i.stop()
        mig = _mig(_to("y", "g"), "1", "2", machine_id="g")
        r = SyncInterpreter.from_snapshot(blob, chain("2", "y"), migrator=mig)
        (c,) = r._actors.values()
        (g,) = c._actors.values()
        assert g.current_state_ids == {"g.y"}
        # ✅ A migrated child re-persists with its OWN new label.
        out = json.loads(r.get_snapshot())
        (crec,) = out["actors"].values()
        (grec,) = crec["snapshot"]["actors"].values()
        assert grec["snapshot"]["machine_version"] == "2"
        assert crec["snapshot"]["machine_version"] == "1"

    def test_migrate_does_not_touch_child_blobs(self) -> None:
        # 📝 Docstring reconciled: children are migrated by from_snapshot.
        raw = json.loads(_two_kid_blob())
        raw["machine_version"] = "1"
        mig = _mig(ident, "1", "2")
        out = mig.migrate(raw, "2", machine_id="p")
        assert out["actors"] == raw["actors"]
        assert "recursively" not in (SnapshotMigrator.migrate.__doc__ or "")

    def test_actor_record_without_snapshot_is_corrupt(self) -> None:
        raw = json.loads(_two_kid_blob())
        rec = next(iter(raw["actors"].values()))
        del rec["snapshot"]
        m = _parent(
            {
                "k1": create_machine(_kid("k1", "1", "x")),
                "k2": create_machine(_kid("k2", "5", "x")),
            },
            ["spawn_k1", "spawn_k2"],
        )
        with pytest.raises(SnapshotCorruptError):  # 🐛 was bare KeyError
            SyncInterpreter.from_snapshot(json.dumps(raw), m)


def test_invalid_config_is_still_library_family() -> None:
    # 📝 Sanity: the families the brief names share one base.
    assert issubclass(InvalidConfigError, XStateMachineError)
