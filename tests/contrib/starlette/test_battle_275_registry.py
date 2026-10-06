# tests/contrib/starlette/test_battle_275_registry.py
"""#275 battle, adversary A: `StatechartRegistry` act / peek / residents /
lifespan / idempotency and the `_http` status mapping.

Skips without the [starlette] extra (module-level importorskip)."""

from __future__ import annotations

import asyncio
import json
import logging

import pytest

from src.xstate_statemachine import MachineLogic, create_machine
from src.xstate_statemachine.exceptions import (
    ConflictError,
    InvalidEventPayloadError,
    InvalidKeyError,
    StoreUnavailableError,
    UnknownEventError,
)
from src.xstate_statemachine.persistence import (
    MemoryInbox,
    MemoryStore,
    SQLiteStore,
)
from src.xstate_statemachine.persistence.locking import PessimisticLock

from ..conftest import requires_extra
from ._support import build_app, counter_machine

pytestmark = requires_extra("starlette")
pytest.importorskip("starlette")
pytest.importorskip("httpx")

from starlette.testclient import TestClient  # noqa: E402

from src.xstate_statemachine.contrib.starlette import (  # noqa: E402
    StatechartRegistry,
    allow_all,
    problem_for_exception,
    receipt_to_status,
    registry as registry_mod,
    status_for_exception,
)

JSON = {"content-type": "application/json"}


def make(store=None, *, machine=None, name="c", **kw):
    reg = StatechartRegistry(store or MemoryStore(), **kw)
    reg.register(name, machine or counter_machine(), authorize=allow_all)
    return reg


def entry_counting_machine(counter):
    def hello(i, ctx, e, a):
        counter.append(1)

    def inc(i, ctx, e, a):
        ctx["n"] += 1

    return create_machine(
        {
            "id": "ent",
            "initial": "on",
            "context": {"n": 0},
            "states": {
                "on": {
                    "entry": "hello",
                    "on": {"INC": {"actions": "inc"}, "END": "done"},
                },
                "done": {"type": "final"},
            },
        },
        logic=MachineLogic(actions={"hello": hello, "inc": inc}),
    )


# -----------------------------------------------------------------------------
# 1. act() concurrency + validation
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("backend", ["memory", "sqlite"])
def test_pessimistic_act_50_concurrent_no_lost_update(tmp_path, backend):
    store = (
        MemoryStore()
        if backend == "memory"
        else SQLiteStore(str(tmp_path / "s.db"))
    )
    reg = make(store, lock=PessimisticLock(timeout=30))

    async def one():
        async with reg.act("c", "k") as i:
            await i.send("INC", wait=True)

    async def main():
        await asyncio.wait_for(asyncio.gather(*(one() for _ in range(50))), 60)

    asyncio.run(main())
    rec = store.load("c.k")
    assert rec.version == 50
    assert "50" in json.dumps(json.loads(rec.snapshot)["context"])


def test_pessimistic_lock_released_when_body_raises():
    store = MemoryStore()
    reg = make(store, lock=PessimisticLock(timeout=1))

    async def main():
        with pytest.raises(RuntimeError):
            async with reg.act("c", "k") as i:
                await i.send("INC", wait=True)
                raise RuntimeError("boom")
        assert store.load("c.k") is None  # nothing saved
        async with reg.act("c", "k") as i:  # lock free again, no timeout
            await i.send("INC", wait=True)

    asyncio.run(main())
    assert store.load("c.k").version == 1


def test_act_on_final_instance_does_not_bump_version():
    """A refused send (instance finished) changed nothing: the save must
    not bump the version (it would 409 a concurrent real writer)."""
    store = MemoryStore()
    reg = make(store, machine=entry_counting_machine([]))
    with TestClient(build_app(reg, "c")) as c:
        assert c.post("/m/k/events/END", headers=JSON).status_code == 200
        v = store.load("c.k").version
        r = c.post("/m/k/events/INC", headers=JSON)
        assert r.status_code == 409
        assert store.load("c.k").version == v


def test_unchanged_event_does_not_bump_version():
    store = MemoryStore()
    reg = make(store, machine=entry_counting_machine([]))
    with TestClient(build_app(reg, "c")) as c:
        c.post("/m/k/events/INC", headers=JSON)
        v = store.load("c.k").version
        r = c.post("/m/k/events/NOPE", headers=JSON)
        assert r.status_code == 200 and r.json()["changed"] is False
        assert store.load("c.k").version == v


@pytest.mark.parametrize("key", ["", "x" * 1000, "\x00"])
def test_store_key_refuses_bad_keys(key):
    with pytest.raises(InvalidKeyError):
        make().store_key("c", key)


@pytest.mark.parametrize("key", ["../x", "ü/ñ", "a.b"])
def test_store_key_accepts_opaque_keys(key):
    assert make().store_key("c", key) == f"c.{key}"


def test_bad_key_over_http_is_400_not_500():
    reg = make()
    with TestClient(build_app(reg, "c")) as c:
        r = c.post("/m/" + "x" * 1000 + "/events/INC", headers=JSON)
        assert r.status_code == 400


@pytest.mark.parametrize("who", ["a:b", "a\nb", "p" * 300])
def test_act_principal_odd_but_valid_is_scoped(who):
    reg = make(inbox=MemoryInbox())

    async def main():
        async with reg.act("c", "k", principal=who) as i:
            await i.send("INC", wait=True, idempotency_key="k1")

    asyncio.run(main())


def test_register_twice_and_authorize_none():
    reg = make()
    with pytest.raises(ValueError):
        reg.register("c", counter_machine(), authorize=allow_all)
    with pytest.raises(TypeError):
        reg.register("d", counter_machine(), authorize=None)


def test_allow_all_warns_once_per_process(caplog, monkeypatch):
    monkeypatch.setattr(
        registry_mod, "_allow_all_warned", __import__("threading").Event()
    )
    caplog.set_level(logging.WARNING, registry_mod.logger.name)
    for _ in range(3):
        reg = make()
        with TestClient(build_app(reg, "c")) as c:
            c.post("/m/k/events/INC", headers=JSON)
    hits = [r for r in caplog.records if "allow_all" in r.getMessage()]
    assert len(hits) == 1


def test_act_body_raising_is_500_without_text():
    reg = make()
    reg2 = make(
        machine=create_machine(
            {
                "id": "b",
                "initial": "a",
                "states": {"a": {"on": {"GO": {"actions": "boom"}}}},
            },
            logic=MachineLogic(actions={"boom": _boom}),
        )
    )
    del reg
    with TestClient(build_app(reg2, "c")) as c:
        r = c.post("/m/k/events/GO", headers=JSON)
        assert r.status_code == 500
        assert "SECRET" not in r.text


def _boom(i, ctx, e, a):
    raise RuntimeError("SECRET")


# -----------------------------------------------------------------------------
# 2. idempotency
# -----------------------------------------------------------------------------
def _idem_app(store=None):
    reg = make(
        store,
        inbox=MemoryInbox(),
        principal=lambda conn: conn.headers.get("x-user") or None,
    )
    return reg, build_app(reg, "c")


def test_same_idem_key_two_principals_two_sends():
    store = MemoryStore()
    reg, app = _idem_app(store)
    with TestClient(app) as c:
        for u in ("alice", "bob"):
            r = c.post(
                "/m/k/events/INC",
                headers={**JSON, "x-user": u, "Idempotency-Key": "K"},
            )
            assert r.status_code == 200 and r.json()["duplicate"] is False
    assert store.load("c.k").version == 2


def test_same_idem_key_different_body_422_and_replay_200():
    store = MemoryStore()
    reg, app = _idem_app(store)
    h = {**JSON, "x-user": "a", "Idempotency-Key": "K"}
    with TestClient(app) as c:
        assert (
            c.post("/m/k/events/INC", headers=h, json={"x": 1}).json()[
                "duplicate"
            ]
            is False
        )
        r = c.post("/m/k/events/INC", headers=h, json={"x": 1})
        assert r.status_code == 200 and r.json()["duplicate"] is True
        r = c.post("/m/k/events/INC", headers=h, json={"x": 2})
        assert r.status_code == 422
    assert store.load("c.k").version == 1


@pytest.mark.parametrize("key", ["x" * 10_000, "naïve"])
def test_bad_idempotency_header_is_4xx(key):
    reg, app = _idem_app()
    with TestClient(app) as c:
        r = c.post(
            "/m/k/events/INC",
            headers={**JSON, "x-user": "a", "Idempotency-Key": "K"},
        )
        hdr = {"x-user": "a", "Idempotency-Key": key.encode("utf-8")}
        r = c.post("/m/k/events/INC", headers={**JSON, **hdr})
        assert 400 <= r.status_code < 500, r.status_code


def test_concurrent_identical_requests_commit_once():
    store = MemoryStore()
    reg = make(store, inbox=MemoryInbox())

    async def one():
        try:
            async with reg.act("c", "k", principal="a") as i:
                return await i.send("INC", wait=True, idempotency_key="K")
        except ConflictError:
            return "conflict"

    async def main():
        return await asyncio.gather(*(one() for _ in range(10)))

    asyncio.run(main())
    assert store.load("c.k").version == 1


def test_send_without_idem_key_on_inbox_registry_allowed():
    reg, app = _idem_app()
    with TestClient(app) as c:
        r = c.post("/m/k/events/INC", headers={**JSON, "x-user": "a"})
        assert r.status_code == 200


def test_no_principal_on_inbox_registry_401():
    reg, app = _idem_app()
    with TestClient(app) as c:
        r = c.post("/m/k/events/INC", headers=JSON)
        assert r.status_code == 401


# -----------------------------------------------------------------------------
# 5. peek
# -----------------------------------------------------------------------------
def test_peek_missing_instance_runs_no_entry_actions():
    seen = []
    reg = make(machine=entry_counting_machine(seen))

    async def main():
        for _ in range(50):
            body = await reg.peek("c", "nope")
        return body

    body = asyncio.run(main())
    assert seen == []
    assert body["state_ids"] == ["ent.on"]
    assert body["available_events"] == ["END", "INC"]


# -----------------------------------------------------------------------------
# 6. _http mapping
# -----------------------------------------------------------------------------
@pytest.mark.parametrize(
    "exc,status",
    [
        (StoreUnavailableError("secret"), 503),
        (InvalidEventPayloadError("secret", ValueError("secret")), 422),
        (UnknownEventError("secret", "m", []), 422),
        (InvalidKeyError("secret"), 400),
    ],
)
def test_status_table_more(exc, status):
    assert status_for_exception(exc) == status
    assert b"secret" not in bytes(problem_for_exception(exc).body)


def test_json_body_contract():
    reg = make(max_body_bytes=1024)
    with TestClient(build_app(reg, "c")) as c:
        url = "/m/k/events/INC"
        big = b'{"a":"' + b"x" * 2000 + b'"}'
        assert c.post(url, headers=JSON, content=big).status_code == 413
        tp = {"content-type": "text/plain"}
        assert c.post(url, headers=tp, content=b"{}").status_code == 415
        cs = {"content-type": "application/json; charset=utf-8"}
        assert c.post(url, headers=cs, content=b"{}").status_code == 200
        assert c.post(url, headers=JSON, content=b"[1]").status_code == 422
        assert c.post(url, headers=JSON, content=b"{x").status_code == 422
        for k in ("wait", "priority"):
            r = c.post(url, headers=JSON, json={k: True})
            assert r.status_code == 422


def test_receipt_to_status_override_validation():
    from src.xstate_statemachine.events import Receipt

    r = Receipt(frozenset({"x"}), True)
    with pytest.raises((ValueError, TypeError)):
        receipt_to_status(r, changed=600)
    with pytest.raises((ValueError, TypeError)):
        receipt_to_status(r, changed="200")


# -----------------------------------------------------------------------------
# 3. residents
# -----------------------------------------------------------------------------
def test_resident_plus_act_same_key_does_not_lose_silently():
    """A resident and an `act()` on one key are two writers. The act
    commits; the resident's later save is fenced -> the conflict must be
    surfaced to `release_resident`, never swallowed."""
    store = MemoryStore()
    reg = make(store)

    async def main():
        r = await reg.resident("c", "k")
        await r.send("INC", wait=True)
        async with reg.act("c", "k") as i:
            await i.send("INC", wait=True)
        with pytest.raises(ConflictError):
            await reg.release_resident("c", "k")
        assert reg.residents == 0

    asyncio.run(main())
    assert store.load("c.k").version == 1


def test_resident_thrash_no_leak():
    import gc

    store = MemoryStore()
    reg = make(store, max_residents=1)

    async def main():
        for n in range(300):
            r = await reg.resident("c", str(n))
            await r.send("INC", wait=True)
        await reg._retire_all()
        gc.collect()
        return len(asyncio.all_tasks())

    assert asyncio.run(main()) == 1
    assert reg.residents == 0
    assert store.load("c.299").version == 1
    assert store.load("c.0").version == 1


def test_resident_on_draining_registry_is_503():
    reg = make()
    reg.draining = True
    with pytest.raises(RuntimeError) as ei:  # back-compat type
        asyncio.run(reg.resident("c", "k"))
    assert status_for_exception(ei.value) == 503


def test_eviction_persists_deadlines():
    m = create_machine(
        {
            "id": "t",
            "initial": "a",
            "states": {"a": {"after": {"60000": "b"}}, "b": {}},
        }
    )
    store = MemoryStore()
    reg = make(store, machine=m)

    async def main():
        await reg.resident("c", "k")
        await reg.release_resident("c", "k")

    asyncio.run(main())
    assert [k for k, _ in store.due_keys(float("inf"))] == ["c.k"]


# -----------------------------------------------------------------------------
# 4. lifespan / probes
# -----------------------------------------------------------------------------
class _AsyncStore:
    def __init__(self):
        from src.xstate_statemachine.persistence.async_store import as_async

        self._a = as_async(MemoryStore())

    async def load(self, key):
        return await self._a.load(key)

    async def save(self, *a, **kw):
        return await self._a.save(*a, **kw)


def test_run_timers_with_async_store_fails_at_construction():
    with pytest.raises((ValueError, TypeError)):
        StatechartRegistry(_AsyncStore(), run_timers=True)


def test_lifespan_twice_and_ready_after_shutdown():
    reg = make()
    app = build_app(reg, "c")
    for _ in range(2):
        with TestClient(app) as c:
            assert c.get("/_xsm/ready").status_code == 200
            assert c.post("/m/k/events/INC", headers=JSON).status_code == 200
    with TestClient(app, raise_server_exceptions=False) as c:
        pass
    reg.started = False
    reg.draining = True
    c = TestClient(app)
    assert c.get("/_xsm/ready").status_code == 503
    assert c.get("/_xsm/health").status_code == 200


def test_drain_timeout_stops_abandoned_residents():
    class Hang(MemoryStore):
        hang = False

        def save(self, *a, **kw):
            if self.hang:
                import time

                time.sleep(1.0)
            return super().save(*a, **kw)

    store = Hang()
    reg = make(store, drain_timeout_s=0.2)
    held = []

    async def main():
        async with reg.lifespan():
            held.append(await reg.resident("c", "a"))
            held.append(await reg.resident("c", "b"))
            store.hang = True
        await asyncio.sleep(1.5)
        return [i.status for i in held]

    assert all(s != "running" for s in asyncio.run(main()))
    assert reg.residents == 0


# --- independent review (#275) ----------------------------------------------
def test_action_only_transition_is_saved_and_marks_flushed():
    """H1: a targetless transition that only RUNS an action left the
    snapshot equal, was classed a no-op and `_SkipSave` discarded the
    outbox / audit marks other plugins collected -- the side effect had
    happened, its record was lost. 'No-op' = no action ran AND nothing
    changed."""
    import asyncio

    from starlette.requests import Request

    from src.xstate_statemachine import MachineLogic, create_machine
    from src.xstate_statemachine.contrib.starlette import (
        StatechartRegistry,
        allow_all,
    )
    from src.xstate_statemachine.persistence import MemoryStore
    from src.xstate_statemachine.plugins import PluginBase

    ran = []

    class Marker(PluginBase):
        def __init__(self):
            self.flushed = 0
            self.discarded = 0

        def flush_marks(self, *a, **k):
            self.flushed += 1

        def discard_marks(self, *a, **k):
            self.discarded += 1

    m = create_machine(
        {
            "id": "n",
            "initial": "a",
            "context": {"x": 0},
            "states": {
                "a": {
                    "on": {
                        "NOTIFY": {"actions": "email"},
                        "NOPE_GUARDED": {"target": "b", "guard": "never"},
                    }
                },
                "b": {},
            },
        },
        logic=MachineLogic(
            actions={"email": lambda i, c, e, a: ran.append(1)},
            guards={"never": lambda c, e: False},
        ),
    )
    store = MemoryStore()
    marker = Marker()
    reg = StatechartRegistry(store, plugins=[marker])
    reg.register("n", m, authorize=allow_all)

    def req(event):
        scope = {
            "type": "http",
            "method": "POST",
            "path": f"/n/k/events/{event}",
            "headers": [(b"content-type", b"application/json")],
            "query_string": b"",
        }

        async def receive():
            return {"type": "http.request", "body": b"{}"}

        return Request(scope, receive)

    async def go():
        async with reg.lifespan():
            r1 = await reg.send_event(req("NOTIFY"), "n", "k", "NOTIFY")
            assert r1.status_code == 200
            v1 = store.load(reg.store_key("n", "k")).version
            assert ran == [1]
            assert marker.flushed >= 1 and marker.discarded == 0
            # a genuinely refused send (guard false): no action ran,
            # nothing changed -> no save, no version bump
            r2 = await reg.send_event(
                req("NOPE_GUARDED"), "n", "k", "NOPE_GUARDED"
            )
            assert r2.status_code in (200, 409)
            assert store.load(reg.store_key("n", "k")).version == v1

    asyncio.run(go())
