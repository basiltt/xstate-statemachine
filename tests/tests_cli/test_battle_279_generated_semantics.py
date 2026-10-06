# tests/tests_cli/test_battle_279_generated_semantics.py
"""#279 battle (adversary A): the SEMANTICS of the generated companions.

The generated router must not be worse than `StatechartRouter` over the
same registry. Before this battle it routed sends through
`get_interpreter` + `interp.send(**payload)` under a hand-rolled route
class, which -- unlike the library router --

* parsed a 2 MB body (no `max_body_bytes`: 200, not 413);
* accepted ``text/plain`` (422 instead of 415);
* splatted ``{"wait": false}`` into ``send()`` (500) and let
  ``{"priority": true}`` jump the queue;
* SAVED an idempotent replay (the version bumped on every retry, so the
  original writer could lose with 409);
* did not cap the 422 error list (no ``errors_total``).

It now delegates to `registry.send_event` under `bounded_route_class`.
Pinned below as a parity table, plus the models / verification /
provenance edges. In-process (`_run`), Windows-safe.
"""

from __future__ import annotations

import importlib
import io
import json
import logging
import pathlib
import sys
from contextlib import redirect_stdout
from typing import Any, Dict, List, Tuple

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("pydantic")

from src.xstate_statemachine.cli.__main__ import main  # noqa: E402

pytestmark = pytest.mark.timeout(300)

SHOP = {
    "id": "shop",
    "initial": "a",
    "context": {"n": 0},
    "states": {
        "a": {
            "on": {
                "GO": {"target": "a", "actions": "inc"},
                "pay now": "b",
                "pay-now": "b",
                "LOCKED": "a",
            }
        },
        "b": {"on": {"BACK": "a"}},
    },
}


def _run(argv: List[str]) -> Tuple[int, str]:
    saved, sys.argv = sys.argv, ["xsm", *argv]
    buf = io.StringIO()
    logging.disable(logging.CRITICAL)
    try:
        with redirect_stdout(buf):
            main()
        code = 0
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
        buf.write(str(exc.code))
    finally:
        sys.argv = saved
        logging.disable(logging.NOTSET)
    return code, buf.getvalue()


def _gen(
    cfg: Dict[str, Any], out: pathlib.Path, stem: str, *extra: str
) -> Tuple[int, str]:
    src = out / f"{stem}.json"
    src.write_text(json.dumps(cfg), encoding="utf-8")
    return _run(
        [
            "gt",
            str(src),
            "-t",
            "pythonic-class",
            "--with-api",
            "--with-models",
            "-o",
            str(out),
            "-f",
            "--plain",
            *extra,
        ]
    )


def _import(out: pathlib.Path, name: str) -> Any:
    for mod in [m for m in sys.modules if m.endswith(("_api", "_models"))]:
        sys.modules.pop(mod, None)
    importlib.invalidate_caches()
    sys.path.insert(0, str(out))
    try:
        return importlib.import_module(name)
    finally:
        sys.path.remove(str(out))


def _app(router: Any, registry: Any) -> Any:
    from fastapi import FastAPI

    from xstate_statemachine.contrib.fastapi import instrument_app

    app = FastAPI()
    app.include_router(router)
    instrument_app(app, registry)
    return app


def _machine() -> Any:
    from xstate_statemachine import MachineLogic, create_machine

    def inc(i: Any, ctx: Any, e: Any, a: Any) -> None:
        ctx["n"] += 1

    return create_machine(SHOP, logic=MachineLogic(actions={"inc": inc}))


def _registry() -> Any:
    from xstate_statemachine.contrib.fastapi import StatechartRegistry
    from xstate_statemachine.persistence import MemoryInbox, MemoryStore

    return StatechartRegistry(
        MemoryStore(),
        inbox=MemoryInbox(),
        principal=lambda c: "u",
        max_body_bytes=1000,
    )


def _deny_locked(conn: Any, *, name: str, key: str, event: Any) -> bool:
    return event != "LOCKED"


# -----------------------------------------------------------------------------
# 1. parity with StatechartRouter
# -----------------------------------------------------------------------------
PARITY = [
    # (case, request kwargs, status, problem title fragment)
    ("ok", {"json": {}}, 200, None),
    (
        "oversized",
        {
            "content": b'{"x":"' + b"a" * 5000 + b'"}',
            "headers": {"content-type": "application/json"},
        },
        413,
        "Too Large",
    ),
    (
        "not json",
        {"content": b"hi", "headers": {"content-type": "text/plain"}},
        415,
        "application/json",
    ),
    ("wait key", {"json": {"wait": False}}, 422, "Reserved"),
    ("priority key", {"json": {"priority": True}}, 422, "Reserved"),
    (
        "bad idem key",
        {"json": {}, "headers": {"Idempotency-Key": "x" * 500}},
        400,
        "",
    ),
]


def _both(tmp_path: pathlib.Path) -> Dict[str, Tuple[Any, Any, str]]:
    """{kind: (app, registry, events-path-prefix)} over one machine."""
    from xstate_statemachine.contrib.fastapi import StatechartRouter

    assert _gen(SHOP, tmp_path, "shop")[0] == 0
    # 📝 the generated module, its registry configured like the library
    #    one (an inbox, a body cap) -- the edit a team makes in place
    src = (tmp_path / "shop_api.py").read_text(encoding="utf-8")
    src = src.replace(
        "registry = StatechartRegistry(MemoryStore())",
        "from xstate_statemachine.persistence import MemoryInbox\n"
        "registry = StatechartRegistry(MemoryStore(), inbox=MemoryInbox(),"
        " principal=lambda c: 'u', max_body_bytes=1000)",
    )
    (tmp_path / "shopcfg_api.py").write_text(src, encoding="utf-8")
    api = _import(tmp_path, "shopcfg_api")
    api.register(_machine(), authorize=_deny_locked)
    gen_reg = api.registry
    lib_reg = _registry()
    lib_reg.register("shop", _machine(), authorize=_deny_locked)
    return {
        "generated": (_app(api.router, gen_reg), gen_reg, "events"),
        "library": (
            _app(StatechartRouter(lib_reg, "shop"), lib_reg),
            lib_reg,
            "events",
        ),
    }


def test_parity_table_generated_router_vs_statechart_router(
    tmp_path: pathlib.Path,
) -> None:
    from fastapi.testclient import TestClient

    seen: Dict[str, List[int]] = {}
    for kind, (app, reg, _) in _both(tmp_path).items():
        with TestClient(app, raise_server_exceptions=False) as c:
            for case, kw, want, title in PARITY:
                r = c.post("/shop/k/events/GO", **kw)
                seen.setdefault(case, []).append(r.status_code)
                assert r.status_code == want, (kind, case, r.text)
                if title:
                    assert title in r.json()["title"], (kind, case)
                    assert "aaaa" not in r.text  # never the input
    assert all(len(set(v)) == 1 for v in seen.values()), seen


def test_denied_and_replayed_sends_save_nothing(
    tmp_path: pathlib.Path,
) -> None:
    from fastapi.testclient import TestClient

    for kind, (app, reg, _) in _both(tmp_path).items():
        skey = reg.store_key("shop", "k")
        with TestClient(app, raise_server_exceptions=False) as c:
            h = {"Idempotency-Key": "abc"}
            r1 = c.post("/shop/k/events/GO", json={}, headers=h)
            assert r1.status_code == 200 and not r1.json()["duplicate"]
            v1 = reg.store.load(skey).version
            for _ in range(3):  # 🔥 each replay used to save + bump
                r = c.post("/shop/k/events/GO", json={}, headers=h)
                assert r.status_code == 200 and r.json()["duplicate"]
            assert reg.store.load(skey).version == v1, kind
            r = c.post("/shop/k/events/LOCKED", json={})
            assert r.status_code == 403, kind
            assert reg.store.load(skey).version == v1, kind
            snap = json.loads(reg.store.load(skey).snapshot)
            assert snap["context"]["n"] == 1, kind


def test_validation_problem_is_capped_and_never_echoes(
    tmp_path: pathlib.Path,
) -> None:
    from fastapi.testclient import TestClient

    cfg = {
        "id": "typed",
        "initial": "a",
        "states": {
            "a": {
                "on": {
                    "SET": {
                        "target": "a",
                        "meta": {"payload": {"items": "array"}},
                    }
                }
            }
        },
    }
    cfg["states"]["a"]["on"]["SET"]["meta"]["payload"] = {
        f"f{i}": "integer" for i in range(80)
    }
    assert _gen(cfg, tmp_path, "typed")[0] == 0
    api = _import(tmp_path, "typed_api")
    from xstate_statemachine import create_machine
    from xstate_statemachine.contrib.fastapi import allow_all

    api.register(create_machine(cfg), authorize=allow_all)
    with TestClient(_app(api.router, api.registry)) as c:
        body = {f"f{i}": "SECRET-VALUE" for i in range(80)}
        r = c.post("/typed/k/events/SET", json=body)
    assert r.status_code == 422
    doc = r.json()
    assert len(doc["errors"]) == 50 and doc["errors_total"] == 80
    assert "SECRET-VALUE" not in r.text
    assert set(doc["errors"][0]) == {"loc", "type"}


def test_slug_collisions_get_distinct_handlers_and_catch_all_is_last(
    tmp_path: pathlib.Path,
) -> None:
    from fastapi.testclient import TestClient

    assert _gen(SHOP, tmp_path, "shop")[0] == 0
    api = _import(tmp_path, "shop_api")
    names = [r.name for r in api.router.routes]
    assert len(names) == len(set(names)), names  # no shadowed handler
    assert {"send_pay_now", "send_pay_now_2"} <= set(names)
    assert api.router.routes[-1].path.endswith("/events/{event}")
    from xstate_statemachine.contrib.fastapi import allow_all

    api.register(_machine(), authorize=allow_all)
    with TestClient(_app(api.router, api.registry)) as c:
        r = c.post("/shop/k/events/pay-now", json={})
        assert r.status_code == 200 and r.json()["state"] == "b"
        c.post("/shop/k/events/BACK", json={})
        r = c.post("/shop/k/events/pay_now", json={})
        assert r.status_code == 200 and r.json()["state"] == "b"
        # the raw (unslugged) name is not a route: 404, not a shadow
        assert c.post("/shop/k/events/pay%20now", json={}).status_code == 404


# -----------------------------------------------------------------------------
# 2. models
# -----------------------------------------------------------------------------
def test_odd_context_keys_and_reserved_payload_fields_alias(
    tmp_path: pathlib.Path,
) -> None:
    cfg = {
        "id": "odd",
        "initial": "a",
        "context": {
            "order-id": 1,
            "class": None,
            "1st": [1, {"a": None}],
            "type": "x",
            "model_config": 2,
        },
        "states": {
            "a": {
                "on": {
                    "GO": {
                        "target": "a",
                        "meta": {
                            "payload": {
                                "model_dump": "integer",
                                "validate": "integer",
                            }
                        },
                    },
                    'it\'s "q"\\x': "a",
                }
            }
        },
    }
    code, text = _gen(cfg, tmp_path, "odd")
    assert code == 0, text
    m = _import(tmp_path, "odd_models")
    ctx = m.OddContext()
    assert ctx.model_dump(by_alias=True) == cfg["context"]
    assert m.OddContext.model_validate({"order-id": 5}).f_order_id == 5
    ev = m.GoEvent.model_validate(
        {"type": "GO", "model_dump": 1, "validate": 2}
    )
    assert ev.type == "GO"
    dumped = ev.model_dump(by_alias=True, exclude={"type"})
    assert dumped == {"model_dump": 1, "validate": 2}
    weird = [c for c in m.EVENT_MODELS if c is not m.GoEvent][0]
    assert weird().type == 'it\'s "q"\\x'  # repr-escaped literal


@pytest.mark.parametrize("field", ["wait", "priority", "type"])
def test_payload_field_named_like_a_send_option_is_refused(
    tmp_path: pathlib.Path, field: str
) -> None:
    cfg = {
        "id": "opt",
        "initial": "a",
        "states": {
            "a": {
                "on": {
                    "GO": {
                        "target": "a",
                        "meta": {"payload": {field: "bool"}},
                    }
                }
            }
        },
    }
    code, text = _gen(cfg, tmp_path, "opt")
    assert code == 1
    assert repr([field]) in text and "send()" in text
    assert not (tmp_path / "opt_models.py").exists()
    assert not (tmp_path / "opt_api.py").exists()


# -----------------------------------------------------------------------------
# 3. verification hygiene
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("mid", ["json", "sys", "fastapi", "tests", "app"])
def test_module_names_never_shadow_and_verification_leaves_no_trace(
    tmp_path: pathlib.Path, mid: str
) -> None:
    before = set(sys.modules)
    cfg = {"id": mid, "initial": "a", "states": {"a": {"on": {"GO": "a"}}}}
    code, text = _gen(cfg, tmp_path, mid)
    assert code == 0, text
    leaked = {
        m for m in set(sys.modules) - before if m.endswith(("_api", "_models"))
    }
    assert not leaked, leaked
    apis = list(tmp_path.glob("*_api.py"))
    assert len(apis) == 1
    api = _import(tmp_path, apis[0].stem)
    assert api.DECLARED_EVENTS == ["GO"]


# -----------------------------------------------------------------------------
# 4/5/6. hierarchy, provenance, single-file primary
# -----------------------------------------------------------------------------
def test_hierarchy_generates_one_router_for_the_parent(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent = {
        "id": "parent",
        "initial": "a",
        "states": {"a": {"on": {"P": "a"}}},
    }
    child = {
        "id": "child",
        "initial": "a",
        "states": {"a": {"on": {"C": "a"}}},
    }
    (tmp_path / "parent.json").write_text(json.dumps(parent), "utf-8")
    (tmp_path / "child.json").write_text(json.dumps(child), "utf-8")
    monkeypatch.setattr("builtins.input", lambda *_: "")
    code, text = _run(
        [
            "gt",
            "-jp",
            str(tmp_path / "parent.json"),
            "-jc",
            str(tmp_path / "child.json"),
            "--with-api",
            "--with-models",
            "-o",
            str(tmp_path),
            "-f",
            "--plain",
        ]
    )
    assert code == 0, text
    assert [p.name for p in tmp_path.glob("*_api.py")] == ["parent_api.py"]
    api = _import(tmp_path, "parent_api")
    # the PARENT's router: its own events, the parent's MACHINE_NAME
    assert api.MACHINE_NAME == "parent" and api.DECLARED_EVENTS == ["P"]


def test_provenance_is_relative_and_the_command_reproduces_the_file(
    tmp_path: pathlib.Path,
) -> None:
    out = tmp_path / "my dir"
    out.mkdir()
    code, text = _gen(SHOP, out, "my shop")
    assert code == 0, text
    api = (out / "shop_api.py").read_text(encoding="utf-8")
    assert str(tmp_path) not in api and str(out) not in api
    assert "Source:    my shop.json" in api
    # 🔥 the command omitted --with-models (an UNTYPED router) and did
    #    not quote a name with a space
    assert '"my shop.json" --template fastapi-router --with-models' in api
    models = (out / "shop_models.py").read_text(encoding="utf-8")
    assert "--with-models" not in models
    # following the printed command reproduces the router byte for byte
    code, _ = _run(
        [
            "gt",
            str(out / "my shop.json"),
            "--template",
            "fastapi-router",
            "--with-models",
            "-o",
            str(out),
            "--check",
            "--plain",
        ]
    )
    assert code == 0


def test_single_file_primary_companions_import_the_models_module(
    tmp_path: pathlib.Path,
) -> None:
    code, text = _gen(SHOP, tmp_path, "shop", "-fc", "1")
    assert code == 0, text
    names = sorted(p.name for p in tmp_path.glob("*.py"))
    assert names == ["shop.py", "shop_api.py", "shop_models.py"]
    api = (tmp_path / "shop_api.py").read_text(encoding="utf-8")
    assert "from shop_models import" in api
    assert "register(machine)" in api  # no invented build_* helper
    assert "build_shop_machine" not in api
    _import(tmp_path, "shop_api")


def test_bare_json_schema_object_payload_is_permissive(
    tmp_path: pathlib.Path,
) -> None:
    cfg = {
        "id": "bare",
        "initial": "a",
        "meta": {"eventSchemas": {"GO": {"type": "object"}}},
        "states": {"a": {"on": {"GO": "a"}}},
    }
    code, text = _gen(cfg, tmp_path, "bare")
    assert code == 0, text  # not "a field named `type`"
    m = _import(tmp_path, "bare_models")
    assert m.GoEvent.model_validate({"type": "GO", "x": 1}).x == 1


# --- independent review (#279) ----------------------------------------------
@pytest.mark.parametrize(
    "schema, ok",
    [
        ({"type": "object"}, True),
        ({"type": ["object", "null"]}, True),
        ({"type": "object", "properties": {}}, True),
        ({"type": "object", "additionalProperties": True}, True),
        ({"type": "string"}, False),  # a payload must be an object
        (
            {"type": "object", "properties": {"type": {"type": "string"}}},
            False,
        ),
    ],
)
def test_json_schema_roots_are_not_mistaken_for_a_field_called_type(
    schema, ok
):
    """H1: `{"type": ["object", "null"]}` (a legal JSON-Schema root) was
    read as a flat field map with a field named `type` and refused; a
    non-object root is refused for the right reason; a real property
    named `type` under `properties` is still refused."""
    from src.xstate_statemachine.cli.strategies._web import collect_events
    from src.xstate_statemachine.exceptions import InvalidConfigError

    cfg = {
        "id": "s",
        "initial": "a",
        "meta": {"eventSchemas": {"GO": schema}},
        "states": {"a": {"on": {"GO": "a"}}},
    }
    if ok:
        [spec] = collect_events(cfg)
        assert spec.payload in (None, [])
    else:
        with pytest.raises(InvalidConfigError):
            collect_events(cfg)
