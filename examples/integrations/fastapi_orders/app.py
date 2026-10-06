# examples/integrations/fastapi_orders/app.py
# -----------------------------------------------------------------------------
# 🛒 Order-lifecycle service: FastAPI + a statechart, N workers, one store
# -----------------------------------------------------------------------------
# 🏛️ What you are looking at: every request loads the order's snapshot from
#    the store, runs ONE interpreter over it, saves it with an expected
#    version and throws the interpreter away (create → act → persist →
#    discard). No worker holds an order in memory, so `--workers 4` is
#    safe. Racing writers produce one winner and a 409 -- never a lost
#    update. Timers (`after`, the payment-retry backoff) are persisted
#    deadlines woken by ONE `--role scheduler` process.
#
#    Run:  uvicorn app:app --workers 4          (from this directory)
#          python app.py --role scheduler       (exactly one of these)
# -----------------------------------------------------------------------------
"""FastAPI order service over `StatechartRegistry` + `StatechartRouter`."""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import sys
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from fastapi import APIRouter, BackgroundTasks, Body, FastAPI, Request
from fastapi.responses import FileResponse, Response

from xstate_statemachine import create_machine
from xstate_statemachine.contrib.fastapi import (
    StatechartRegistry,
    StatechartRouter,
    bounded_route_class,
    instrument_app,
)
from xstate_statemachine.contrib.pydantic import context_model
from xstate_statemachine.contrib.starlette import mount_inspector
from xstate_statemachine.patterns import DeadLetterPlugin
from xstate_statemachine.persistence import DueTimerScanner, SQLiteInbox

from logic import build_logic, gateway_breaker
from migrations import build_migrator
from models import EVENT_MODELS, EVENT_SCHEMAS, OrderContext, Pay
from models import public_context

logger = logging.getLogger("fastapi_orders")

HERE = Path(__file__).resolve().parent
MACHINE_NAME = "order"
CUSTOMER_HEADER = "x-customer"
CUSTOMER_COOKIE = "customer"

#: ``(order_id, charge_id, customer) -> None`` -- the confirmation mailer.
EmailSender = Callable[[str, Optional[str], str], None]


# -----------------------------------------------------------------------------
# 🏗️ Machine, store, identity
# -----------------------------------------------------------------------------
def chart_path(version: Optional[str] = None) -> Path:
    """``machine.json`` (v1) or ``machine_v2.json``; ``XSM_ORDERS_CHART``
    selects the one a deployment runs (``1`` default, ``2``)."""
    v = version or os.environ.get("XSM_ORDERS_CHART", "1")
    return HERE / ("machine_v2.json" if str(v) == "2" else "machine.json")


def build_machine(
    version: Optional[str] = None, *, breaker: Any = None
) -> Any:
    config = json.loads(chart_path(version).read_text("utf-8"))
    # ⏱️ `XSM_PAYMENT_TIMEOUT_MS` shortens the 15-minute payment timeout
    #    (the fleet tests wait for the scheduler process to fire it).
    override = os.environ.get("XSM_PAYMENT_TIMEOUT_MS")
    if override:
        after = config["states"]["awaitingPayment"]["after"]
        (old_key,) = after
        after[str(int(override))] = after.pop(old_key)
    return create_machine(
        config,
        logic=build_logic(breaker),
        event_schemas=EVENT_SCHEMAS,
        # 📝 write_back=False: the context stays plain JSON (the snapshot
        #    is stored as JSON); the model only VALIDATES it.
        context_validator=context_model(OrderContext, write_back=False),
    )


def build_store() -> Tuple[Any, Any]:
    """``(store, inbox)`` from the environment.

    ``XSM_REDIS_URL`` → `RedisStore` + `RedisInbox` (multi-host; imported
    lazily so redis is not needed by default). Otherwise `SQLiteStore` at
    ``XSM_ORDERS_DB`` (default ``orders.db``) with an inbox sharing its
    connection, so an inbox mark commits with the snapshot.
    """
    url = os.environ.get("XSM_REDIS_URL")
    if url:
        from xstate_statemachine.contrib.redis import RedisInbox, RedisStore

        return (
            RedisStore(url, prefix="orders"),
            RedisInbox(url, prefix="orders"),
        )
    from xstate_statemachine.persistence import SQLiteStore

    store = SQLiteStore(os.environ.get("XSM_ORDERS_DB", "orders.db"))
    return store, SQLiteInbox(store)


def build_dead_letter_store(store: Any) -> Any:
    """Dead letters live next to the snapshots: in the same SQLite file
    (one `xsm dlq` target), or in memory for Redis deployments (use
    `BrokerDeadLetterSink` / your queue there)."""
    from xstate_statemachine.persistence import SQLiteStore

    if isinstance(store, SQLiteStore):
        from xstate_statemachine.eda import SQLiteDeadLetterStore

        return SQLiteDeadLetterStore(store)
    from xstate_statemachine.patterns import MemoryDeadLetterStore

    return MemoryDeadLetterStore()


def customer_of(conn: Any) -> str:
    """The caller's identity: ``X-Customer`` header, else the ``customer``
    cookie (an `EventSource` cannot set headers). Replace with your real
    authentication -- this is the idempotency scope (X0.2)."""
    return str(
        conn.headers.get(CUSTOMER_HEADER)
        or conn.cookies.get(CUSTOMER_COOKIE)
        or ""
    )


#: Set on `request.state` by the ONE route allowed to send PAY.
PAY_GATE_ATTR = "xsm_pay_gate"


def authorize(conn: Any, *, name: str, key: str, event: Optional[str]) -> bool:
    """Demo policy: any identified customer. A real service would also
    check that the order belongs to them.

    🔐 battle #276: the PAY gate (the email hook) used to live only on
    the generated router's `per_event_dependencies` -- a second router
    on another prefix (an admin API) that forgot it exposed PAY without
    the hook. The gate belongs HERE, on the registry's authorize, which
    every route goes through: PAY is allowed only when the confirmation
    route marked the request.
    """
    if not customer_of(conn):
        return False
    if event == "PAY":
        return bool(
            getattr(getattr(conn, "state", None), PAY_GATE_ATTR, False)
        )
    return True


def log_email(order_id: str, charge_id: Optional[str], customer: str) -> None:
    logger.info(
        "📧 confirmation for order %s (charge %s) to %s",
        order_id,
        charge_id,
        customer,
    )


def build_registry(
    store: Any = None,
    inbox: Any = None,
    *,
    chart: Optional[str] = None,
    **kw: Any,
) -> StatechartRegistry:
    if store is None:
        store, inbox = build_store()
    # 🧬 #263: the migrator rides on the registry, so BOTH the request path
    #    (`apersisted`) and the scheduler (`DueTimerScanner`) migrate a v1
    #    order lazily the first time a v2 process touches it. Harmless on
    #    a v1 deployment: a v1 blob into the v1 chart never mismatches.
    kw.setdefault("migrator", build_migrator())
    # 💀 #265: a `DeadLetterPlugin` on the registry writes ONE record --
    #    machine, last event, attempt count, the chain of gateway errors,
    #    a redacted snapshot -- when an order enters `paymentFailed` (tagged
    #    `dead-letter` in the chart). The store shares the orders database
    #    so `xsm dlq --dlq sqlite:///orders.db list` is the triage view,
    #    and `replay` re-drives the order once the gateway is back. Both
    #    the request path and the scheduler carry it (the retry loop is
    #    usually exhausted BY the scheduler's wake).
    dlq = kw.pop("dead_letters", None)
    if dlq is None:
        dlq = build_dead_letter_store(store)
    plugins = list(kw.pop("plugins", ()))
    if dlq is not None:
        plugins.append(DeadLetterPlugin(dlq))
    registry = StatechartRegistry(
        store, inbox=inbox, principal=customer_of, plugins=plugins, **kw
    )
    registry.dead_letters = dlq  # type: ignore[attr-defined]
    # ⚡ #265: one CircuitBreaker per registry (= per process) in front of
    #    the gateway, on the registry's clock so a SimulatedClock in tests
    #    drives the cooldown. `registry.breaker` for dashboards / tests.
    breaker = gateway_breaker(clock=kw.get("clock"))
    registry.breaker = breaker  # type: ignore[attr-defined]
    registry.register(
        MACHINE_NAME,
        build_machine(chart, breaker=breaker),
        authorize=authorize,
        context_serializer=public_context,
    )
    return registry


def build_scanner(registry: StatechartRegistry, **kw: Any) -> DueTimerScanner:
    """The ONE process that wakes persisted `after` deadlines.

    Keyword arguments override the registry-derived defaults (tests pass
    extra `plugins=`, a `limit=`, a `prefix=`).
    """
    defaults: Dict[str, Any] = dict(
        lock=registry.lock,
        plugins=registry.plugins,
        prefix=f"{MACHINE_NAME}.",
        # 🧬 #263 battle: the scheduler restores snapshots too. Without the
        #    registry's migrator every matured timer on a v1 order failed
        #    with MachineVersionMismatchError after the v2 deploy -- a
        #    retry that never fires, a 15-minute timeout that never
        #    expires -- while the web workers (which had it) were fine.
        migrator=registry.migrator,
    )
    defaults.update(kw)
    return DueTimerScanner(
        registry.store, registry.machine_for_store_key, **defaults
    )


# -----------------------------------------------------------------------------
# 🌐 The app
# -----------------------------------------------------------------------------
def _should_confirm(response: Response) -> Tuple[bool, Optional[str]]:
    """Email only for a COMMITTED, first-time, successful payment."""
    if response.status_code != 200:
        return False, None
    body = json.loads(bytes(response.body))
    ok = (
        body.get("changed")
        and body.get("error") is None
        and not body.get("duplicate")
        and body.get("state") == "paid"
    )
    charge = (body.get("context") or {}).get("charge_id")
    return bool(ok), charge


def add_pay_route(
    app: FastAPI, registry: StatechartRegistry, email: EmailSender
) -> None:
    """``POST /orders/{id}/events/PAY`` with a `BackgroundTasks` bridge.

    Registered BEFORE the router so it shadows the generated PAY route;
    the router refuses PAY on ``/send`` (``per_event_dependencies``), so
    this is the only way in -- no payment can skip the email hook.

    The route lives on an `APIRouter` with `bounded_route_class` so it gets
    the same 413 / 415 / problem-shaped 422 envelope as the generated
    routes (#266 battle: a 1 MB body was parsed and answered 422).
    """
    extra = APIRouter(route_class=bounded_route_class(registry))

    @extra.post(
        "/orders/{id}/events/PAY",
        tags=["orders"],
        operation_id="order_pay_with_confirmation",
        summary="Pay; emails a confirmation after the response",
    )
    async def pay(
        request: Request,
        id: str,  # noqa: A002 -- the router's key_param
        background: BackgroundTasks,
        body: Pay = Body(...),
    ) -> Response:
        payload = body.model_dump(mode="python", exclude={"type"})
        setattr(request.state, PAY_GATE_ATTR, True)  # see `authorize`
        response = await registry.send_event(
            request, MACHINE_NAME, id, "PAY", payload
        )
        confirm, charge = _should_confirm(response)
        if confirm:
            # ✅ Runs after the response is sent, only once the save
            #    committed (send_event returned a 200 receipt).
            background.add_task(email, id, charge, customer_of(request))
        return response

    app.include_router(extra)


def create_app(
    registry: Optional[StatechartRegistry] = None,
    *,
    email: EmailSender = log_email,
    debug: Optional[bool] = None,
) -> FastAPI:
    registry = registry or build_registry()
    app = FastAPI(title="Orders (xstate-statemachine)")
    add_pay_route(app, registry, email)
    app.include_router(
        StatechartRouter(
            registry,
            MACHINE_NAME,
            prefix="/orders",
            tags=["orders"],
            event_models=EVENT_MODELS,
            per_event_dependencies={"PAY": []},
        )
    )

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(HERE / "static" / "index.html")

    if debug is None:
        debug = os.environ.get("XSM_DEBUG") == "1"
    if debug:
        mount_inspector(app, registry, debug=True)
    app.state.registry = registry
    return instrument_app(app, registry)


_APP: Optional[FastAPI] = None


def __getattr__(name: str) -> Any:
    """``uvicorn app:app`` -- built on first access, so importing this
    module (tests, the scheduler role) never opens the default database."""
    global _APP
    if name == "app":
        if _APP is None:
            _APP = create_app()
        return _APP
    raise AttributeError(name)


# -----------------------------------------------------------------------------
# â° `--role scheduler`
# -----------------------------------------------------------------------------
def init_store() -> None:
    """Create the store's schema ONCE, before starting N workers: SQLite
    switching an empty file to WAL is a write, and N processes racing to
    do it see `database is locked`."""
    store, _inbox = build_store()
    close = getattr(store, "close", None)
    if callable(close):
        close()
    logger.info("✅ store initialised")


def run_scheduler(interval_s: float = 1.0) -> None:
    """Run the `DueTimerScanner` until SIGINT/SIGTERM. Start EXACTLY one."""
    scanner = build_scanner(build_registry())
    stop = threading.Event()

    def _stop(*_: Any) -> None:
        stop.set()
        scanner.stop()

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    logger.info("â° scheduler: scanning every %.1fs", interval_s)
    scanner.run_forever(interval_s)


#: battle #277-a: the event loop for `--workers N` on Windows. uvicorn
#: picks `SelectorEventLoop` for its spawned workers there; with the
#: listening socket shared into N processes (`socket.share`), a few
#: accepted connections in some fleets never report readable -- the
#: request's body is never delivered and the client times out (7 of 25
#: fleets with a no-op ASGI app, 0 of 25 on the Proactor loop).
WINDOWS_WORKER_LOOP = "asyncio:ProactorEventLoop"


def worker_loop(workers: int) -> str:
    """uvicorn's ``--loop`` for *workers* processes on this platform."""
    if sys.platform == "win32" and workers > 1:
        return WINDOWS_WORKER_LOOP
    return "auto"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--role", choices=["web", "scheduler", "init"], default="web"
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--interval", type=float, default=1.0)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    if args.role == "init":
        init_store()
        return 0
    if args.role == "scheduler":
        run_scheduler(args.interval)
        return 0
    import uvicorn

    uvicorn.run(
        "app:app",
        host=args.host,
        port=args.port,
        workers=args.workers,
        loop=worker_loop(args.workers),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
