"""Battle #273 (adversary B): structlog / loguru / Sentry / instrument_all."""

import asyncio
import contextlib
import logging
import sys
from types import SimpleNamespace

import pytest

pytest.importorskip("opentelemetry")
pytest.importorskip("prometheus_client")

from xstate_statemachine import (  # noqa: E402
    Interpreter,
    MachineLogic,
    SyncInterpreter,
    create_machine,
    plugins,
)
from xstate_statemachine.contrib.observability import (  # noqa: E402
    instrument_all,
    uninstrument_all,
)
from xstate_statemachine.contrib.observability import logs  # noqa: E402
from xstate_statemachine.contrib.observability.sentry import (  # noqa: E402
    SentryPlugin,
)
from xstate_statemachine.exceptions import MissingExtraError  # noqa: E402
from xstate_statemachine.plugins import PluginBase  # noqa: E402


def _slow_machine(name):
    async def slow(i, c, e, a):
        await asyncio.sleep(0.01 if c["n"] == "A" else 0.05)
        sl = sys.modules["structlog"]
        c["seen"] = sl.contextvars.get_contextvars().get("machine_id")

    return create_machine(
        {
            "id": name,
            "initial": "a",
            "context": {"n": name},
            "states": {"a": {"on": {"GO": {"actions": ["slow"]}}}},
        },
        logic=MachineLogic(actions={"slow": slow}),
    )


def test_interleaved_async_interpreters_do_not_share_the_stack():
    """A thread-local stack let A's `processed` unwind B's entry on the
    same loop: B's entry leaked forever (one per round)."""
    pytest.importorskip("structlog")
    plugin = logs.StructlogPlugin()

    async def main():
        a = await Interpreter(_slow_machine("A")).use(plugin).start()
        b = await Interpreter(_slow_machine("B")).use(plugin).start()
        for _ in range(5):
            await a.send("GO")
            await asyncio.sleep(0.005)
            await b.send("GO")
            await asyncio.sleep(0.1)
        assert a.context["seen"] == "A" and b.context["seen"] == "B"
        await a.stop()
        await b.stop()

    asyncio.run(main())
    assert plugin._stack() == []


@pytest.mark.parametrize("policy", ["fail", "continue", "rollback"])
def test_raising_action_unwinds_context_every_policy(policy):
    sl = pytest.importorskip("structlog")

    def boom(i, c, e, a):
        raise RuntimeError("x")

    m = create_machine(
        {
            "id": "m",
            "initial": "a",
            "actionErrorPolicy": policy,
            "states": {
                "a": {"on": {"GO": {"target": "b", "actions": ["boom"]}}},
                "b": {},
            },
        },
        logic=MachineLogic(actions={"boom": boom}),
    )
    plugin = logs.StructlogPlugin()
    it = SyncInterpreter(m).use(plugin).start()
    with contextlib.suppress(Exception):
        it.send("GO")
    assert sl.contextvars.get_contextvars() == {}
    assert plugin._stack() == []


def test_user_binding_inside_action_survives_reset():
    sl = pytest.importorskip("structlog")
    sl.contextvars.clear_contextvars()

    def bind(i, c, e, a):
        sl.contextvars.bind_contextvars(request_id="r1")

    m = create_machine(
        {
            "id": "m",
            "initial": "a",
            "states": {"a": {"on": {"G": {"actions": ["bind"]}}}},
        },
        logic=MachineLogic(actions={"bind": bind}),
    )
    SyncInterpreter(m).use(logs.StructlogPlugin()).start().send("G")
    assert sl.contextvars.get_contextvars() == {"request_id": "r1"}
    sl.contextvars.clear_contextvars()


@pytest.mark.parametrize(
    "payload",
    [
        SimpleNamespace(),
        {"headers": [1, 2]},
        {"headers": "x"},
        {"correlation_id": None},
    ],
)
def test_correlation_id_never_raises(payload):
    logs._correlation_id(SimpleNamespace(payload=payload))


def test_huge_correlation_id_is_capped():
    cid = logs._correlation_id(
        SimpleNamespace(payload={"correlation_id": "x" * 500_000})
    )
    assert len(cid) == logs.MAX_CORRELATION_ID_LEN


def test_loguru_rejects_non_loguru_logger():
    with pytest.raises(TypeError, match="contextualize"):
        logs.LoguruPlugin(logger=logging.getLogger("x"))


@pytest.mark.parametrize(
    "factory,pkg",
    [
        (lambda: logs.StructlogPlugin(), "structlog"),
        (lambda: logs.LoguruPlugin(), "loguru"),
        (lambda: SentryPlugin(), "sentry-sdk"),
    ],
)
def test_soft_import_absent_names_the_package(monkeypatch, factory, pkg):
    mod = pkg.replace("-", "_")
    monkeypatch.setitem(sys.modules, mod, None)
    with pytest.raises(MissingExtraError, match=f"pip install {pkg}"):
        factory()


class _Scope:
    def set_tag(self, k, v):
        pass


class _SDK:
    def __init__(self, crumb_error=None, new=False):
        self.caps, self.crumbs, self.crumb_error = [], [], crumb_error
        if new:
            self.new_scope = self.push_scope

    def add_breadcrumb(self, **kw):
        self.crumbs.append(kw)
        if self.crumb_error:
            raise self.crumb_error

    def capture_exception(self, e):
        self.caps.append(e)

    @contextlib.contextmanager
    def push_scope(self):
        yield _Scope()


def _toggle():
    return create_machine(
        {
            "id": "t",
            "initial": "a",
            "context": {"secret": "s3"},
            "states": {"a": {"on": {"T": "b"}}, "b": {"on": {"T": "a"}}},
        }
    )


def test_raising_sentry_sdk_is_reported_once_and_chart_runs(caplog):
    sdk = _SDK(crumb_error=ConnectionError("net"))
    it = SyncInterpreter(_toggle()).use(SentryPlugin(sdk=sdk)).start()
    with caplog.at_level(logging.WARNING):
        for _ in range(50):
            it.send("T")
    assert it.status == "running"
    assert len(sdk.crumbs) == 1
    assert sum("reported once" in r.message for r in caplog.records) == 1


@pytest.mark.parametrize("new", [False, True])
@pytest.mark.parametrize("policy", ["fail", "continue", "rollback"])
def test_one_capture_per_action_error(policy, new):
    sdk = _SDK(new=new)

    def boom(i, c, e, a):
        raise RuntimeError("x")

    m = create_machine(
        {
            "id": "m",
            "initial": "a",
            "actionErrorPolicy": policy,
            "states": {
                "a": {"on": {"GO": {"target": "b", "actions": ["boom"]}}},
                "b": {},
            },
        },
        logic=MachineLogic(actions={"boom": boom}),
    )
    it = SyncInterpreter(m).use(SentryPlugin(capture_errors=True, sdk=sdk))
    it.start()
    with contextlib.suppress(Exception):
        it.send("GO")
    assert len(sdk.caps) == 1


def test_breadcrumbs_never_carry_context():
    sdk = _SDK()
    it = SyncInterpreter(_toggle()).use(SentryPlugin(sdk=sdk)).start()
    it.send("T")
    assert set(sdk.crumbs[0]["data"]) == {"machine_id", "event"}
    assert "s3" not in repr(sdk.crumbs)


class _Count(PluginBase):
    def __init__(self):
        self.starts, self.n = [], 0

    def on_interpreter_start(self, i):
        self.starts.append(i.id)

    def on_transition(self, *a):
        self.n += 1


def test_instrument_running_interpreter_replays_start():
    it = SyncInterpreter(_toggle()).start()
    c = _Count()
    from xstate_statemachine.contrib.observability import _instrument

    _instrument._use(it, c)
    assert c.starts == [it.id]
    idle = SyncInterpreter(_toggle())
    _instrument._use(idle, c)
    assert c.starts == [it.id]  # not running: start fires normally later


def test_instrument_running_interpreter_prometheus_polls_it():
    from prometheus_client import CollectorRegistry

    from xstate_statemachine.contrib.observability import PrometheusPlugin

    reg = CollectorRegistry()
    it = SyncInterpreter(_toggle()).start()
    instrument_all(it, prometheus=PrometheusPlugin(registry=reg))
    v = reg.get_sample_value(
        "xstatemachine_active_interpreters", {"machine": "t"}
    )
    assert v == 1


def test_global_and_use_same_plugin_fires_once():
    """🔥 battle #273: global AND `.use()` of one instance (or `.use()`
    twice) doubled every hook -- every metric doubled. The engine now
    dedupes by identity in `use()`, both engines."""
    base = _Count()
    SyncInterpreter(_toggle()).use(base).start().send("T")
    c = _Count()
    plugins.register_global(c)
    try:
        SyncInterpreter(_toggle()).use(c).use(c).start().send("T")
        assert c.n == base.n
        it = SyncInterpreter(_toggle())
        instrument_all(it, otel=c)
        c.n = 0
        it.start().send("T")
    finally:
        plugins.unregister_global(c)
    assert c.n == base.n


def test_use_twice_is_once_on_the_async_engine():
    import asyncio

    from src.xstate_statemachine import Interpreter

    base = _Count()
    SyncInterpreter(_toggle()).use(base).start().send("T")
    c = _Count()

    async def go():
        i = await Interpreter(_toggle()).use(c).use(c).start()
        await i.send("T")
        await asyncio.sleep(0.02)
        await i.stop()

    asyncio.run(go())
    assert c.n == base.n


def test_uninstrument_unknown_plugin_is_a_noop():
    assert uninstrument_all([_Count()]) is None


def test_tuple_plugins_app_is_refused_loudly():
    with pytest.raises(TypeError, match="plugins` list"):
        instrument_all(SimpleNamespace(plugins=()), otel=True)


def test_observability_import_does_not_pull_soft_deps():
    import subprocess

    code = (
        "import sys, xstate_statemachine.contrib.observability;"
        "print([m for m in ('structlog','loguru','sentry_sdk')"
        " if m in sys.modules])"
    )
    out = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env={**__import__("os").environ},
    )
    assert out.stdout.strip() == "[]", out.stderr
