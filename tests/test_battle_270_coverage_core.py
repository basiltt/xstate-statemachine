# tests/test_battle_270_coverage_core.py
# -----------------------------------------------------------------------------
# ⚔️ Battle test #270 (adversary A): coverage core -- collector identity,
#    renderers, `below`, the global plugin registry.
# -----------------------------------------------------------------------------
"""Battle-test regressions for `xstate_statemachine.coverage`."""

import gc
import threading

import pytest

from xstate_statemachine import SyncInterpreter, create_machine, plugins
from xstate_statemachine.coverage import (
    TEXT_LIST_LIMIT,
    CoverageCollector,
    CoverageReport,
    below,
    machine_key,
    reports_from_json,
    reports_to_html,
    reports_to_json,
    reports_to_text,
)
from xstate_statemachine.plugins import PluginBase

BASE = {
    "id": "m",
    "initial": "a",
    "states": {"a": {"on": {"GO": "b"}}, "b": {"on": {"BACK": "a"}}},
}
OTHER = {
    "id": "m",
    "initial": "a",
    "states": {"a": {"on": {"GO": "b"}}, "b": {"on": {"BACK2": "a"}}},
}
PAR = {
    "id": "p",
    "initial": "a",
    "states": {
        "a": {"on": {"GO": "c"}},
        "c": {
            "type": "parallel",
            "states": {
                "p": {
                    "initial": "x",
                    "states": {
                        "x": {"on": {"N": "y"}},
                        "y": {},
                        "h": {"type": "history", "history": "deep"},
                    },
                },
                "q": {"initial": "z", "states": {"z": {}}},
            },
            "on": {"OUT": "a", "BACK": "#p.c.p.h"},
        },
    },
}


def _drive(machine, cov, *events):
    i = SyncInterpreter(machine).use(cov).start()
    for e in events:
        i.send(e)
    i.stop()


# --------------------------------------------------------------- identity
def test_builds_are_not_kept_alive_and_ids_never_alias():
    """10 000 short-lived builds of two charts: earlier builds are freed
    (no session-long leak) and a recycled ``id()`` never credits a hit
    to the wrong chart."""
    cov = CoverageCollector()
    for n in range(10_000):
        _drive(create_machine(BASE if n % 2 else OTHER), cov, "GO")
    gc.collect()
    # 📝 One live build per key at most (the one `_MachineData` holds).
    assert len(cov._by_obj) <= 2
    for r in cov.reports():
        assert r.transitions_hit == 1
        assert r.unhit[0][1] in ("on 'BACK'", "on 'BACK2'")


def test_rebuilt_machine_hits_are_credited():
    cov = CoverageCollector()
    _drive(create_machine(BASE), cov, "GO")
    _drive(create_machine(BASE), cov, "GO", "BACK")
    r = cov.report(create_machine(BASE))
    assert (r.transitions_hit, r.transitions_total) == (2, 2)


def test_collector_itself_is_collectable():
    import weakref

    cov = CoverageCollector()
    m = create_machine(BASE)
    _drive(m, cov, "GO")
    ref = weakref.ref(cov)
    del cov
    gc.collect()
    assert ref() is None


# ------------------------------------------------------------ configuration
def test_parallel_and_deep_history_accounting():
    m = create_machine(PAR)
    cov = CoverageCollector()
    _drive(m, cov, "GO", "N", "BACK")
    r = cov.report(m)
    assert r.unvisited == ()
    assert r.unhit == (("p.c", "on 'OUT'", "p.a"),)


def test_same_path_same_report_on_both_targets_regardless_of_order():
    a, b = CoverageCollector(), CoverageCollector()
    _drive(create_machine(PAR), a, "GO", "N", "OUT")
    _drive(create_machine(PAR), b, "GO", "N")
    _drive(create_machine(PAR), b, "GO", "OUT")
    b.merge(a)
    assert b.report(create_machine(PAR)).unhit == (
        ("p.c", "on 'BACK'", "p.c.p.h"),
    )


# ------------------------------------------------------------- renderers
def _rep(**kw):
    base = dict(
        machine_id="m",
        key="m@1",
        states_visited=0,
        states_total=0,
        unvisited=(),
        transitions_hit=0,
        transitions_total=0,
        unhit=(),
    )
    base.update(kw)
    return CoverageReport(**base)


def test_empty_chart_is_100_percent_not_zero_division():
    r = _rep()
    assert (r.state_percent, r.transition_percent) == (100.0, 100.0)
    assert below([r], state=100, transition=100) == []


def test_json_round_trip_every_field():
    r = _rep(
        states_visited=1,
        states_total=3,
        unvisited=("m.b", "m.ü"),
        transitions_hit=1,
        transitions_total=2,
        unhit=(("m.a", "after 1000", "m.b"),),
    )
    assert reports_from_json(reports_to_json([r])) == [r]


def test_text_lists_are_capped():
    unhit = tuple((f"m.s{k:03}", "on 'E'", "m.t") for k in range(500))
    r = _rep(transitions_total=500, unhit=unhit)
    text = reports_to_text([r])
    assert f"... and {500 - TEXT_LIST_LIMIT} more" in text
    assert len(text) < 2000
    # 📝 The machine-readable reports stay complete.
    assert len(reports_from_json(reports_to_json([r]))[0].unhit) == 500


def test_html_escapes_hostile_ids():
    evil = "<script>alert(1)</script>'\""
    r = _rep(
        machine_id=evil,
        key=evil,
        states_total=1,
        unvisited=(evil,),
        transitions_total=1,
        unhit=((evil, "on '<b>'", evil),),
    )
    out = reports_to_html([r], title=evil)
    assert "<script>" not in out
    assert "<b>" not in out
    assert "'\"" not in out


@pytest.mark.parametrize("bad", [float("nan"), -1, 100.5, float("inf")])
def test_below_refuses_nonsense_thresholds(bad):
    with pytest.raises(ValueError):
        below([_rep()], state=bad)
    with pytest.raises(ValueError):
        below([_rep()], transition=bad)


def test_below_bounds():
    r = _rep(states_total=2, states_visited=1)
    assert below([r], state=0) == []
    assert below([r], state=100) == ["m: state coverage 50% < 100%"]


def test_machine_key_ignores_prose_tracks_structure():
    k = machine_key(create_machine(BASE))
    assert machine_key(create_machine({**BASE, "description": "x"})) == k
    assert machine_key(create_machine(OTHER)) != k


# --------------------------------------------------------- global registry
class _Boom(PluginBase):
    def on_transition(self, *a):
        raise RuntimeError("boom")


def test_global_plugin_dedupe_containment_and_unregister():
    boom, cov = _Boom(), CoverageCollector()
    try:
        plugins.register_global(boom)
        plugins.register_global(boom)
        plugins.register_global(cov)
        assert plugins.global_plugins() == [boom, cov]
        m = create_machine(BASE)
        i = SyncInterpreter(m).start()
        i.send("GO")
        assert i.current_state_ids == {"m.b"} and i.status == "running"
        plugins.unregister_global(cov)
        i.send("BACK")  # 📝 keeps its own copy of the plugin list
        assert cov.report(m).transitions_hit == 2
    finally:
        plugins.clear_global_plugins()
    assert plugins.global_plugins() == []


def test_global_registry_race_with_construction():
    m = create_machine(BASE)
    errs = []
    bar = threading.Barrier(32)

    def work(k):
        bar.wait()
        try:
            for _ in range(100):
                if k % 2:
                    p = CoverageCollector()
                    plugins.register_global(p)
                    plugins.unregister_global(p)
                else:
                    SyncInterpreter(m).start().send("GO")
        except Exception as exc:  # pragma: no cover - the failure path
            errs.append(exc)

    ts = [threading.Thread(target=work, args=(k,)) for k in range(32)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert errs == [] and plugins.global_plugins() == []
