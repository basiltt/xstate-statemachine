# tests/contrib/pydantic/test_battle_266_config.py
"""#266 battle (agent B): `validate_machine_json` -- the static gate -- vs
the parser, pinned.

* **parity, both directions**, over the 104 Stately charts and every
  machine JSON shipped under ``examples/``: the gate accepts a chart iff
  `create_machine` does;
* **corpus mutation fuzz** (fixed seed, 20 charts x 30 single-key
  mutations): the parser never escapes with a bare ``TypeError`` /
  ``KeyError`` / ``AttributeError`` / ``RecursionError`` /
  ``ValueError``, and the gate never crashes;
* the gate refuses what the engine refuses: non-object ``context``,
  duplicate custom state ``id``, string ``strict`` flags (the parser
  reads ``"false"`` as true);
* core escapes fixed: non-dict ``states`` on an initial-less compound,
  non-numeric ``maxIterations`` / ``spawnBlockingTimeout``, a 600-deep
  chart -- each is now `InvalidConfigError`;
* input forms: ``bytes``, BOM, malformed JSON, duplicate JSON keys;
  error paths read ``PAY[0].target``; the nesting cap says what it is.
"""

from __future__ import annotations

import copy
import json
import logging
import random
from pathlib import Path
from typing import Any, Dict, Iterator, List, Tuple

import pytest

pytest.importorskip("pydantic")

from src.xstate_statemachine import create_machine  # noqa: E402
from src.xstate_statemachine.contrib.pydantic import (  # noqa: E402
    validate_machine_json,
)
from src.xstate_statemachine.exceptions import (  # noqa: E402
    InvalidConfigError,
    XStateMachineError,
)
from src.xstate_statemachine.testing_utils import stub_logic  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
CORPUS = ROOT / "tests" / "tests_cli" / "stately_machines"


def _charts() -> List[Tuple[str, Dict[str, Any]]]:
    paths = sorted(CORPUS.glob("*.json")) + sorted(
        (ROOT / "examples").rglob("*.json")
    )
    out = []
    for p in paths:
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if isinstance(raw, dict) and "states" in raw and "id" in raw:
            out.append((str(p.relative_to(ROOT)), raw))
    return out


def _gate(cfg: Any, **kw: Any) -> bool:
    try:
        validate_machine_json(cfg, **kw)
        return True
    except InvalidConfigError:
        return False


def _parse(cfg: Any) -> bool:
    try:
        create_machine(cfg, logic=stub_logic(cfg))
        return True
    except XStateMachineError:
        return False


@pytest.fixture(autouse=True)
def _quiet() -> Iterator[None]:
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)


# -----------------------------------------------------------------------------
# 1. parity over the corpus + examples
# -----------------------------------------------------------------------------
def test_gate_and_parser_agree_on_every_shipped_chart() -> None:
    charts = _charts()
    assert len(charts) > 150  # 104 corpus + examples
    disagree = [
        (name, g, p)
        for name, cfg in charts
        for g, p in [(_gate(cfg), _parse(cfg))]
        if g != p
    ]
    assert disagree == []


# -----------------------------------------------------------------------------
# 1b. mutation fuzz
# -----------------------------------------------------------------------------
_VALUES: List[Any] = [
    1, -1, 1.5, "", True, None, [], {}, "x", 10**30, ["a", "b"],
    {"a": 1}, "ü€", "1s", -100, 0, [None], [{}], {"type": 1},
]  # fmt: skip
_KEYS = [
    "id", "initial", "states", "type", "on", "entry", "exit", "after",
    "always", "invoke", "onDone", "output", "history", "target",
    "context", "maxIterations", "spawnBlockingTimeout", "strict", "tags",
    "meta", "description",
]  # fmt: skip


def _nodes(cfg: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    yield cfg
    for v in (cfg.get("states") or {}).values():
        if isinstance(v, dict):
            yield from _nodes(v)


def _mutate(cfg: Dict[str, Any], rng: random.Random) -> Dict[str, Any]:
    cfg = copy.deepcopy(cfg)
    n = rng.choice(list(_nodes(cfg)))
    kids = list((n.get("states") or {}).keys())
    op = rng.randrange(10)
    if op == 0:
        n[rng.choice(_KEYS)] = rng.choice(_VALUES)
    elif op == 1 and n:
        del n[rng.choice(list(n))]
    elif op == 2 and kids:
        n["initial"] = rng.choice(kids)
        n["states"][n["initial"]]["type"] = rng.choice(["history", "final"])
    elif op == 3:
        delay = rng.choice(["-5", "1.5", "1s", "0", "1e3"])
        n["after"] = {delay: rng.choice(kids or ["#" + str(cfg["id"])])}
    elif op == 4 and len(kids) > 1:
        a, b = kids[:2]
        n["states"][a]["always"] = b
        n["states"][b]["always"] = a
    elif op == 5:
        n["invoke"] = [{"src": "s", "id": "d"}, {"src": "t", "id": "d"}]
    elif op == 6:
        n["type"] = "history"
        n["states"] = {"h": {}}
    elif op == 7 and kids:
        n["type"] = "final"
    elif op == 8 and kids:
        n["states"][kids[0]]["id"] = "dup"
        n["states"][kids[-1]]["id"] = "dup"
    else:
        n["on"] = {rng.choice(["E", "", "*"]): rng.choice(_VALUES)}
    return cfg


def test_mutation_fuzz_never_escapes_as_a_bare_python_error() -> None:
    rng = random.Random(266)
    corpus = [cfg for name, cfg in _charts() if "stately_machines" in name]
    escapes: List[str] = []
    refused_by_both = 0
    for base in rng.sample(corpus, 20):
        for _ in range(30):
            m = _mutate(base, rng)
            try:
                g = _gate(m)
            except Exception as exc:  # noqa: BLE001 -- the finding
                escapes.append(f"gate {type(exc).__name__}: {exc}")
                continue
            try:
                p = _parse(m)
            except Exception as exc:  # noqa: BLE001 -- the finding
                escapes.append(f"parser {type(exc).__name__}: {exc}")
                continue
            refused_by_both += (not g) and (not p)
    assert escapes == []
    assert refused_by_both > 50  # the mutations do bite


# -----------------------------------------------------------------------------
# gate refuses what the engine refuses
# -----------------------------------------------------------------------------
BASE: Dict[str, Any] = {"id": "m", "initial": "a", "states": {"a": {}}}


def _with(**kw: Any) -> Dict[str, Any]:
    cfg = copy.deepcopy(BASE)
    cfg.update(kw)
    return cfg


@pytest.mark.parametrize("ctx", [5, [1], True, 1.5])
def test_non_object_context_refused_by_both(ctx: Any) -> None:
    cfg = _with(context=ctx)
    assert not _parse(cfg)
    with pytest.raises(InvalidConfigError, match="context"):
        validate_machine_json(cfg)


def test_template_string_context_accepted_by_both() -> None:
    cfg = _with(context="{{initialContext}}")
    assert _gate(cfg) and _parse(cfg)


def test_duplicate_custom_state_id_refused_with_both_paths() -> None:
    cfg = _with(states={"a": {"id": "x"}, "b": {"states": {"c": {"id": "x"}}}})
    cfg["states"]["b"]["initial"] = "c"
    assert not _parse(cfg)
    with pytest.raises(InvalidConfigError) as ei:
        validate_machine_json(cfg)
    assert "states.a" in str(ei.value) and "states.b.states.c" in str(ei.value)


@pytest.mark.parametrize("key", ["strict", "strictTargets", "strictConfig"])
def test_string_strict_flag_is_refused(key: str) -> None:
    """The parser does `bool("false")` -> True: the gate must not bless it."""
    with pytest.raises(InvalidConfigError, match=key):
        validate_machine_json(_with(**{key: "false"}))
    assert _gate(_with(**{key: False}))


# -----------------------------------------------------------------------------
# core escapes (models.py / factory.py), now InvalidConfigError
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("states", ["x", [1], 5])
def test_non_dict_states_on_an_initial_less_compound(states: Any) -> None:
    cfg = {"id": "m", "states": {"a": {"type": "compound", "states": states}}}
    with pytest.raises(InvalidConfigError):
        create_machine(cfg)
    with pytest.raises(InvalidConfigError):
        validate_machine_json(cfg)


@pytest.mark.parametrize(
    "key,value",
    [
        ("maxIterations", "abc"),
        ("maxIterations", []),
        ("spawnBlockingTimeout", "x"),
        ("spawnBlockingTimeout", {}),
    ],
)
def test_non_numeric_root_policy_names_the_key(key: str, value: Any) -> None:
    with pytest.raises(InvalidConfigError, match=key):
        create_machine(_with(**{key: value}))
    with pytest.raises(InvalidConfigError, match=key):
        validate_machine_json(_with(**{key: value}))


def test_numeric_string_max_iterations_still_parses() -> None:
    assert create_machine(_with(maxIterations="5")).max_iterations == 5


def _deep(n: int) -> Dict[str, Any]:
    root: Dict[str, Any] = {"id": "m"}
    cur = root
    for _ in range(n):
        cur["initial"] = "s"
        cur["states"] = {"s": {}}
        cur = cur["states"]["s"]
    return root


def test_pathologically_deep_chart_is_a_config_error() -> None:
    with pytest.raises(InvalidConfigError, match="too deeply"):
        create_machine(_deep(3000))


def test_gate_nesting_cap_is_named_not_called_a_cycle() -> None:
    assert _gate(_deep(90)) and _parse(_deep(90))
    with pytest.raises(InvalidConfigError) as ei:
        validate_machine_json(_deep(200))
    msg = str(ei.value)
    assert "nest deeper" in msg and "cyclic" not in msg
    assert len(msg) < 400  # not a 200-segment path


# -----------------------------------------------------------------------------
# input forms and error paths
# -----------------------------------------------------------------------------
def test_bytes_and_bom_are_accepted() -> None:
    text = json.dumps(BASE)
    assert validate_machine_json(text.encode()).id == "m"
    assert validate_machine_json(b"\xef\xbb\xbf" + text.encode()).id == "m"
    assert validate_machine_json(chr(0xFEFF) + text).id == "m"
    assert validate_machine_json(bytearray(text.encode())).id == "m"


@pytest.mark.parametrize("raw", ["{", "", "nul", b"\xff\xfe{"])
def test_malformed_json_is_a_config_error(raw: Any) -> None:
    with pytest.raises(InvalidConfigError, match="JSON|UTF-8"):
        validate_machine_json(raw)


def test_duplicate_json_key_is_refused() -> None:
    raw = '{"id": "m", "initial": "a", "states": {"a": {"on": {"GO": "a", "GO": "b"}}}}'  # noqa: E501
    with pytest.raises(InvalidConfigError, match="'GO'"):
        validate_machine_json(raw)


def test_list_index_paths_read_like_json_pointers() -> None:
    cfg = _with(states={"paying": {"on": {"PAY": [{"target": 1}]}}})
    cfg["initial"] = "paying"
    with pytest.raises(InvalidConfigError) as ei:
        validate_machine_json(cfg)
    lines = str(ei.value).splitlines()[1:]
    assert lines == [
        "  states.paying.on.PAY[0].target: Input should be a valid string"
    ]


def test_unicode_state_and_event_names_appear_in_the_path() -> None:
    cfg = {
        "id": "m",
        "initial": "ü",
        "states": {"ü": {"on": {"É": 5}}},
    }  # noqa: E501
    with pytest.raises(InvalidConfigError, match="states.ü.on.É"):
        validate_machine_json(cfg)


# -----------------------------------------------------------------------------
# 2. strict mirrors strictConfig, Stately export keys included
# -----------------------------------------------------------------------------
STATELY_KEYS = [
    "$schema", "schemas", "types", "tsTypes", "preserveActionOrder",
    "predictableActionArguments", "delays", "guards", "actions",
]  # fmt: skip


@pytest.mark.parametrize("key", STATELY_KEYS)
def test_strict_agrees_with_strict_config_on_stately_keys(key: str) -> None:
    cfg = _with(**{key: {}})
    with pytest.raises(InvalidConfigError, match=key.replace("$", r"\$")):
        validate_machine_json(cfg, strict=True)
    with pytest.raises(InvalidConfigError):
        create_machine(cfg, strict_config=True)
    assert _gate(cfg)  # lenient: accepted, like the parser's default


@pytest.mark.parametrize(
    "extra",
    [
        {"version": "1.0"},
        {"x-stately": {"a": 1}},
        {"description": "d", "tags": ["t"], "meta": {"k": 1}},
        {"output": {"ok": True}},
    ],
)
def test_strict_accepts_what_strict_config_accepts(extra: Any) -> None:
    cfg = _with(**extra)
    validate_machine_json(cfg, strict=True)
    create_machine(cfg, strict_config=True)


def test_strict_reports_nested_unknown_keys_with_list_paths() -> None:
    cfg = _with(
        states={
            "a": {"on": {"E": [{"target": "a", "cnd": "g"}]}, "entyr": "x"}
        }
    )
    with pytest.raises(InvalidConfigError) as ei:
        validate_machine_json(cfg, strict=True)
    assert "states.a.entyr" in str(ei.value)
    assert "states.a.on.E[0].cnd" in str(ei.value)
