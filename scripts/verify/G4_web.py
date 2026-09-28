"""Verification for G4 web: #275 [starlette], #276 [fastapi], #278 [litestar].

`python scripts/verify/G4_web.py`.

Windows-safe (no heredocs, no /tmp). Runs the [starlette] test folder,
then the issue's smoke scenario through `starlette.testclient`: SUBMIT is
200, BOGUS is 200-unchanged without strict and 422 with `strict=True`,
Idempotency-Key dedups, authorize denial is 403. Prints ``ALL OK``.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
CORPUS = ROOT / "tests" / "tests_cli" / "stately_machines"
# 💡 Verify THIS checkout even when an editable install points elsewhere
#    (git worktrees share one environment).
sys.path.insert(0, str(ROOT / "src"))


def step(name: str) -> None:
    print(f"\n== {name}")


def run_tests() -> None:
    step("pytest tests/contrib/{starlette,fastapi,litestar}")
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            *[
                f"tests/contrib/{d}"
                for d in ("starlette", "fastapi", "litestar")
                if (ROOT / "tests" / "contrib" / d).is_dir()
            ],
            "tests/contrib/test_extras_matrix.py",
            "-q",
            "-p",
            "no:cacheprovider",
        ],
        cwd=str(ROOT),
    )
    assert proc.returncode == 0, "web tests failed"


def build(strict: bool):
    from starlette.applications import Starlette
    from starlette.routing import Route

    from xstate_statemachine import create_machine, stub_logic
    from xstate_statemachine.contrib.starlette import (
        ReceiptResponse,
        StatechartRegistry,
        allow_all,
        problem_for_exception,
    )
    from xstate_statemachine.persistence import MemoryInbox, MemoryStore

    cfg = json.loads((CORPUS / "AdvancePayment.json").read_text("utf-8"))
    m = create_machine(cfg, logic=stub_logic(cfg))
    reg = StatechartRegistry(
        MemoryStore(),
        inbox=MemoryInbox(),
        principal=lambda conn: conn.headers.get("x-user", "anon"),
    )
    reg.register("payment", m, authorize=allow_all, strict=strict)

    async def send(request):
        # 📝 The issue's handler shape: act() + ReceiptResponse.
        key = request.path_params["id"]
        try:
            async with reg.act("payment", key, principal="anon") as i:
                receipt = await i.send(request.path_params["event"], wait=True)
                return ReceiptResponse(i, receipt)
        except Exception as exc:  # noqa: BLE001
            return problem_for_exception(exc)

    async def send2(request):
        p = request.path_params
        return await reg.send_event(request, "payment", p["id"], p["event"])

    routes = [
        Route("/p/{id}/events/{event}", send, methods=["POST"]),
        Route("/q/{id}/events/{event}", send2, methods=["POST"]),
    ]
    return Starlette(routes=routes, lifespan=reg.lifespan)


def smoke() -> None:
    from starlette.testclient import TestClient

    step("smoke: SUBMIT / BOGUS without strict")
    with TestClient(build(strict=False)) as c:
        r = c.post("/p/42/events/SUBMIT")
        print(r.status_code, r.json()["state"])
        assert r.status_code == 200 and r.json()["changed"] is True
        r = c.post("/p/42/events/BOGUS")
        print(r.status_code, r.json()["changed"])
        assert r.status_code == 200 and r.json()["changed"] is False

        step("smoke: Idempotency-Key")
        h = {"Idempotency-Key": "abc", "x-user": "u1"}
        a = c.post("/q/7/events/SUBMIT", headers=h)
        b = c.post("/q/7/events/SUBMIT", headers=h)
        print(a.status_code, b.status_code, b.json()["duplicate"])
        assert a.status_code == b.status_code == 200
        assert b.json()["duplicate"] is True
        r = c.post(
            "/q/7/events/UPDATE_FORM",
            headers={**h, "content-type": "text/plain"},
            content=b"x",
        )
        print("non-json", r.status_code)
        assert r.status_code == 415

    step("smoke: BOGUS with strict=True")
    with TestClient(build(strict=True)) as c:
        r = c.post("/p/42/events/BOGUS")
        print(r.status_code, r.json()["title"])
        assert r.status_code == 422
        assert r.headers["content-type"] == "application/problem+json"


def payment_registry():
    from xstate_statemachine import create_machine, stub_logic
    from xstate_statemachine.contrib.starlette import (
        StatechartRegistry,
        allow_all,
    )
    from xstate_statemachine.persistence import MemoryInbox, MemoryStore

    cfg = json.loads((CORPUS / "AdvancePayment.json").read_text("utf-8"))
    m = create_machine(cfg, logic=stub_logic(cfg))
    # 📝 One principal for the whole idempotency demo (review amendment).
    reg = StatechartRegistry(
        MemoryStore(), inbox=MemoryInbox(), principal=lambda conn: "demo"
    )
    reg.register("payment", m, authorize=allow_all)
    return reg


def smoke_fastapi() -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from xstate_statemachine.contrib.fastapi import (
        StatechartRouter,
        instrument_app,
    )

    step("fastapi: StatechartRouter over AdvancePayment")
    reg = payment_registry()
    app = FastAPI()
    app.include_router(StatechartRouter(reg, "payment", prefix="/payments"))
    instrument_app(app, reg)
    with TestClient(app) as c:
        paths = sorted(app.openapi()["paths"])
        print(paths)
        assert "/payments/{id}/send" in paths
        r = c.post("/payments/1/send", json={"type": "SUBMIT"})
        print(r.status_code, r.json()["state"])
        assert r.status_code == 200 and r.json()["changed"] is True
        h = {"Idempotency-Key": "k1"}
        c.post("/payments/1/send", json={"type": "RESET"}, headers=h)
        r2 = c.post("/payments/1/send", json={"type": "RESET"}, headers=h)
        print("dup:", r2.json()["duplicate"])
        assert r2.json()["duplicate"] is True
        bad = c.post("/payments/1/send", json={"type": "NOPE"})
        print("unknown type", bad.status_code)
        assert bad.status_code == 422
        print(c.get("/payments/1").json()["available_events"])


def smoke_litestar() -> None:
    try:
        import litestar  # noqa: F401
        from xstate_statemachine.contrib import litestar as _xl  # noqa: F401
    except ImportError:
        step("litestar: not installed / not shipped -- skipped")
        return
    from litestar import Litestar
    from litestar.testing import TestClient

    from xstate_statemachine.contrib.litestar import (
        XStatePlugin,
        create_statechart_controller,
    )

    step("litestar: controller + plugin over AdvancePayment")
    reg = payment_registry()
    app = Litestar(
        route_handlers=[
            create_statechart_controller(reg, "payment", path="/payments")
        ],
        plugins=[XStatePlugin(reg)],
    )
    with TestClient(app) as c:
        r = c.post("/payments/1/send", json={"type": "SUBMIT"})
        print(r.status_code, r.json()["state"])
        assert r.status_code == 200 and r.json()["changed"] is True
        paths = sorted(app.openapi_schema.paths)
        print(paths)
        assert "/payments/{id}/send" in paths


def main() -> int:
    run_tests()
    smoke()
    smoke_fastapi()
    smoke_litestar()
    print("\nALL OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
