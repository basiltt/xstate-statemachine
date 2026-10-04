# tests/contrib/pydantic/test_battle_266_core.py
"""#266 battle: the defects the typed-boundary scenario found in core and
in the `[pydantic]` extra, pinned as unit tests.

* a chart whose static ``context`` the model refuses is refused at
  `create_machine` (`InvalidConfigError`), not started;
* `TypedContextPlugin` on an invalid RESTORED context fails the machine
  (`status == "error"`) instead of being swallowed by plugin containment;
* `{"type": 1}` actions and list / non-string transition targets are
  `InvalidConfigError` from both the static gate and the parser (they
  escaped as bare ``AttributeError``);
* the FastAPI `instrument_app` maps every `RequestValidationError` to the
  422 problem shape (field path + type, never the offending value).
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, Literal

import pytest

pytest.importorskip("pydantic")

from pydantic import BaseModel  # noqa: E402

from src.xstate_statemachine import (  # noqa: E402
    MachineLogic,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.contrib.pydantic import (  # noqa: E402
    ContextValidationError,
    TypedContextPlugin,
    context_model,
    validate_machine_json,
)
from src.xstate_statemachine.exceptions import InvalidConfigError  # noqa: E402


class Ctx(BaseModel):
    total: Decimal = Decimal("0")
    currency: Literal["USD", "EUR"] = "USD"


class _In(BaseModel):
    token: str


CFG = {
    "id": "c",
    "initial": "a",
    "actionErrorPolicy": "rollback",
    "context": {"total": "0", "currency": "USD"},
    "states": {"a": {"on": {"BUMP": {"actions": "bump"}}}},
}


def logic() -> MachineLogic:
    return MachineLogic(
        actions={
            "bump": lambda i, c, e, a: c.__setitem__(
                "total", c["total"] + Decimal("1")
            )
        }
    )


class TestInitialContext:
    def test_static_context_the_model_refuses_is_a_config_error(self) -> None:
        bad = json.loads(json.dumps(CFG))
        bad["context"]["currency"] = "GBP"
        with pytest.raises(InvalidConfigError) as ei:
            create_machine(
                bad, logic=logic(), context_validator=context_model(Ctx)
            )
        msg = str(ei.value)
        assert "currency" in msg and "GBP" not in msg  # path, not value

    def test_plain_validator_is_not_called_at_build(self) -> None:
        # the #305 contract: a bare callable runs after mutations only
        calls = {"n": 0}

        def v(ctx: Any) -> None:
            calls["n"] += 1

        create_machine(CFG, logic=logic(), context_validator=v)
        assert calls["n"] == 0

    def test_context_factory_is_not_checked_statically(self) -> None:
        cfg = dict(CFG, context=lambda: {"total": "0", "currency": "GBP"})
        create_machine(
            cfg, logic=logic(), context_validator=context_model(Ctx)
        )

    def test_chart_is_not_mutated_by_write_back_at_build(self) -> None:
        cfg = json.loads(json.dumps(CFG))
        create_machine(
            cfg, logic=logic(), context_validator=context_model(Ctx)
        )
        assert cfg["context"]["total"] == "0"  # still the JSON string

    def test_restored_invalid_context_fails_the_machine(self) -> None:
        m = create_machine(
            CFG, logic=logic(), context_validator=context_model(Ctx)
        )
        i = SyncInterpreter(m).use(TypedContextPlugin(Ctx)).start()
        blob = json.loads(i.get_snapshot())
        i.stop()
        blob["context"]["currency"] = "GBP"  # edited at rest
        r = (
            SyncInterpreter.from_snapshot(json.dumps(blob), m)
            .use(TypedContextPlugin(Ctx))
            .start()
        )
        assert r.status == "error"
        assert isinstance(r.error, ContextValidationError)
        r.send("BUMP")
        assert r.context["total"] == "0"  # nothing ran


class TestParserShapes:
    @pytest.mark.parametrize(
        "path, value",
        [
            ("states.a.on.BUMP.target", ["b"]),
            ("states.a.on.BUMP.target", 7),
            ("states.a.entry", {"type": 1}),
            ("states.a.entry", [{"type": None}]),
        ],
    )
    def test_bad_shapes_are_invalid_config_in_gate_and_parser(
        self, path: str, value: Any
    ) -> None:
        cfg = json.loads(json.dumps(CFG))
        cfg["states"]["b"] = {}
        cfg["states"]["a"]["on"]["BUMP"] = {"target": "b", "actions": "bump"}
        d: Any = cfg
        parts = path.split(".")
        for p in parts[:-1]:
            d = d[p]
        d[parts[-1]] = value
        with pytest.raises(InvalidConfigError) as ei:
            validate_machine_json(cfg)
        assert parts[-1] in str(ei.value) or parts[-2] in str(ei.value)
        with pytest.raises(InvalidConfigError):  # not AttributeError
            create_machine(cfg, logic=logic())


class TestFastAPIValidationProblem:
    def test_app_added_route_gets_the_problem_shape(self) -> None:
        pytest.importorskip("fastapi")
        from fastapi import Body, FastAPI
        from fastapi.testclient import TestClient

        from src.xstate_statemachine.contrib.fastapi import instrument_app
        from src.xstate_statemachine.contrib.starlette import (
            StatechartRegistry,
        )
        from src.xstate_statemachine.persistence import MemoryStore

        reg = StatechartRegistry(MemoryStore())
        app = FastAPI()

        @app.post("/pay")
        async def pay(body: _In = Body(...)) -> dict:
            return {"ok": True}

        instrument_app(app, reg)
        with TestClient(app) as c:
            r = c.post("/pay", json={"token": 123, "x": "s3cr3t-value-here"})
        assert r.status_code == 422
        body = r.json()
        assert body["title"] == "Request validation failed"
        assert body["errors"][0]["loc"] == ["body", "token"]
        assert "s3cr3t" not in r.text and "123" not in r.text


# -----------------------------------------------------------------------------
# reviewer follow-ups (#266): C1 scrub leaks, H1 exclude write-back, H2 start
# -----------------------------------------------------------------------------
class TestReviewerFollowUps:
    def test_scrub_hides_values_from_custom_validators_and_ctx(self) -> None:
        """C1: a `ValueError(f"... {v}")` / `PydanticCustomError` from a
        field_validator carried the value in `ctx["error"]` / `msg`."""
        import traceback

        from pydantic import field_validator
        from pydantic_core import PydanticCustomError

        class M(BaseModel):
            tok: str
            cur: Literal["USD"] = "USD"

            @field_validator("tok")
            @classmethod
            def v(cls, v: str) -> str:
                if v.startswith("S"):
                    raise ValueError(f"bad token {v}")
                if v.startswith("C"):
                    raise PydanticCustomError("bad", "bad {v}", {"v": v})
                return v

        validate = context_model(M)
        for raw in (
            {"tok": "SECRET123"},
            {"tok": "CUSTOM456"},
            {"tok": "ok", "cur": "GBPSECRET"},
        ):
            with pytest.raises(ContextValidationError) as ei:
                validate(dict(raw))
            exc = ei.value
            blob = str(exc) + repr(exc.errors)
            blob += "".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)
            )
            for v in raw.values():
                assert v not in blob, (raw, blob)
            # the field path survives
            assert any(k in str(exc) for k in raw)

    def test_excluded_field_write_back_does_not_crash(self) -> None:
        """H1: `model_dump()` omits `exclude=True` fields; the write-back
        loop raised KeyError on every validation."""
        from pydantic import Field

        class M(BaseModel):
            a: int = 1
            secret: str = Field(default="s", exclude=True)

        ctx = {"a": 2, "secret": "tok"}
        context_model(M)(ctx)
        assert ctx == {"a": 2, "secret": "tok"}

    def test_failed_start_runs_no_entry_actions_both_engines(self) -> None:
        """H2: the machine went to `error`, but the initial entry actions
        (and services / timers) still ran on the refused context."""
        import asyncio

        from src.xstate_statemachine import Interpreter

        class N(BaseModel):
            n: int = 0

        ran: list = []
        cfg = {
            "id": "m",
            "initial": "a",
            "context": {"n": "x"},
            "states": {"a": {"entry": "e", "on": {"GO": "b"}}, "b": {}},
        }
        m = create_machine(
            cfg, logic=MachineLogic(actions={"e": lambda *a: ran.append(1)})
        )
        i = SyncInterpreter(m).use(TypedContextPlugin(N)).start()
        i.send("GO")
        assert i.status == "error" and not ran and not i.current_state_ids

        async def go() -> Any:
            a = await Interpreter(m).use(TypedContextPlugin(N)).start()
            await asyncio.sleep(0.05)
            task = a._event_loop_task
            out = (a.status, bool(ran), task is None or task.done())
            await a.stop()
            return out

        assert asyncio.run(go()) == ("error", False, True)

    def test_instrument_app_keeps_a_user_validation_handler(self) -> None:
        """M2: a handler the app registered first is not replaced."""
        pytest.importorskip("fastapi")
        from fastapi import Body, FastAPI
        from fastapi.exceptions import RequestValidationError
        from fastapi.responses import JSONResponse
        from fastapi.testclient import TestClient

        from src.xstate_statemachine.contrib.fastapi import instrument_app
        from src.xstate_statemachine.contrib.starlette import (
            StatechartRegistry,
        )
        from src.xstate_statemachine.persistence import MemoryStore

        app = FastAPI()

        @app.exception_handler(RequestValidationError)
        async def mine(request: Any, exc: Exception) -> JSONResponse:
            return JSONResponse({"mine": True}, status_code=400)

        @app.post("/pay")
        async def pay(body: _In = Body(...)) -> dict:
            return {"ok": True}

        instrument_app(app, StatechartRegistry(MemoryStore()))
        with TestClient(app) as c:
            r = c.post("/pay", json={"token": 1})
        assert r.status_code == 400 and r.json() == {"mine": True}
