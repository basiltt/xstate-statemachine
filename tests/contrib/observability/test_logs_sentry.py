"""structlog / loguru / Sentry plugins (#273, second commit)."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import time

import pytest

from .conftest import pytestmark  # noqa: F401


def _wait(cond, timeout=3.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end and not cond():
        time.sleep(0.01)
    return cond()


class TestStructlog:
    def test_log_line_inside_an_action_carries_context(self, machine_factory):
        structlog = pytest.importorskip("structlog")
        from structlog.testing import capture_logs

        from src.xstate_statemachine import SyncInterpreter
        from src.xstate_statemachine.contrib.observability.logs import (
            StructlogPlugin,
        )

        log = structlog.get_logger()
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.JSONRenderer(),
            ]
        )
        try:
            with capture_logs(
                processors=[structlog.contextvars.merge_contextvars]
            ) as logs:
                i = SyncInterpreter(
                    machine_factory(log=lambda: log.info("charged"))
                ).use(StructlogPlugin())
                i.start()
                i.send("PAY", correlation_id="c-1")
                assert _wait(lambda: "shop.paid" in i.current_state_ids)
                log.info("outside")
                i.stop()
        finally:
            structlog.reset_defaults()
        charged = next(e for e in logs if e["event"] == "charged")
        assert charged["machine_id"] == "shop"
        assert charged["event"] == "charged"  # structlog's own key wins
        assert "state" in charged
        outside = next(e for e in logs if e["event"] == "outside")
        assert "machine_id" not in outside  # unbound after processing

    def test_binds_event_and_correlation_id(self, machine_factory):
        pytest.importorskip("structlog")
        import structlog

        from src.xstate_statemachine import SyncInterpreter
        from src.xstate_statemachine.contrib.observability.logs import (
            StructlogPlugin,
        )

        seen = {}

        def grab():
            seen.update(structlog.contextvars.get_contextvars())

        m = machine_factory()
        m.logic.actions["explode"] = lambda i, c, e, a: grab()
        i = SyncInterpreter(m).use(StructlogPlugin()).start()
        i.send("BOOM", headers={"x-correlation-id": "abc"})
        i.stop()
        assert seen["event"] == "BOOM"
        assert seen["correlation_id"] == "abc"
        assert seen["state"] == ["shop.idle"]
        assert structlog.contextvars.get_contextvars() == {}


class TestLoguru:
    def test_extra_carries_context(self, machine_factory):
        loguru = pytest.importorskip("loguru")
        from src.xstate_statemachine import SyncInterpreter
        from src.xstate_statemachine.contrib.observability.logs import (
            LoguruPlugin,
        )

        records = []
        logger = loguru.logger
        sink = logger.add(lambda m: records.append(m.record), level="INFO")
        try:
            i = SyncInterpreter(
                machine_factory(log=lambda: logger.info("charged"))
            ).use(LoguruPlugin())
            i.start()
            i.send("PAY", correlationId="c-9")
            assert _wait(lambda: "shop.paid" in i.current_state_ids)
            logger.info("outside")
            i.stop()
        finally:
            logger.remove(sink)
        charged = next(r for r in records if r["message"] == "charged")
        assert charged["extra"]["machine_id"] == "shop"
        outside = next(r for r in records if r["message"] == "outside")
        assert "machine_id" not in outside["extra"]


class _FakeScope:
    def __init__(self, tags):
        self.tags = tags

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def set_tag(self, k, v):
        self.tags[k] = v


class _FakeSdk:
    def __init__(self):
        self.breadcrumbs = []
        self.captured = []
        self.tags = {}

    def add_breadcrumb(self, **kw):
        self.breadcrumbs.append(kw)

    def new_scope(self):
        return _FakeScope(self.tags)

    def capture_exception(self, error):
        self.captured.append((error, dict(self.tags)))


class TestSentry:
    def test_breadcrumbs_and_one_capture_on_action_error(
        self, machine_factory
    ):
        from src.xstate_statemachine import SyncInterpreter
        from src.xstate_statemachine.contrib.observability.sentry import (
            SentryPlugin,
        )

        sdk = _FakeSdk()
        i = SyncInterpreter(machine_factory()).use(
            SentryPlugin(sdk=sdk, capture_errors=True)
        )
        i.start()
        i.send("BOOM")
        i.send("PAY")
        assert _wait(lambda: "shop.paid" in i.current_state_ids)
        i.stop()
        msgs = [b["message"] for b in sdk.breadcrumbs]
        assert "shop.idle -> shop.paying (PAY)" in msgs
        assert all(b["category"] == "statechart" for b in sdk.breadcrumbs)
        assert len(sdk.captured) == 1
        err, tags = sdk.captured[0]
        assert isinstance(err, ValueError)
        assert tags["statechart.action"] == "explode"
        assert tags["statechart.machine_id"] == "shop"

    def test_capture_is_opt_in_and_service_errors(self, machine_factory):
        from src.xstate_statemachine import SyncInterpreter
        from src.xstate_statemachine.contrib.observability.sentry import (
            SentryPlugin,
        )

        sdk = _FakeSdk()
        i = SyncInterpreter(machine_factory(charge_fails=True)).use(
            SentryPlugin(sdk=sdk)
        )
        i.start()
        i.send("BOOM")
        i.stop()
        assert sdk.captured == []
        sdk2 = _FakeSdk()
        j = SyncInterpreter(machine_factory(charge_fails=True)).use(
            SentryPlugin(sdk=sdk2, capture_errors=True)
        )
        j.start()
        j.send("PAY")
        assert _wait(lambda: "shop.failed" in j.current_state_ids)
        j.stop()
        assert sdk2.captured[0][1]["statechart.service"] == "charge"

    def test_real_sdk_transport_receives_breadcrumb_and_exception(
        self, machine_factory
    ):
        sentry_sdk = pytest.importorskip("sentry_sdk")
        from src.xstate_statemachine import SyncInterpreter
        from src.xstate_statemachine.contrib.observability.sentry import (
            SentryPlugin,
        )

        envelopes = []

        class Transport(sentry_sdk.transport.Transport):
            def capture_envelope(self, envelope):
                envelopes.append(envelope)

        # 📝 default integrations off: the logging integration would turn
        #    the engine's own ERROR log line into a second event.
        sentry_sdk.init(
            dsn="https://k@o0.ingest.invalid/1",
            transport=Transport(),
            default_integrations=False,
        )
        try:
            i = SyncInterpreter(machine_factory()).use(
                SentryPlugin(capture_errors=True)
            )
            i.start()
            i.send("RESET")
            i.send("BOOM")
            i.stop()
            sentry_sdk.flush()
        finally:
            sentry_sdk.init()
        events = [
            item.payload.json
            for env in envelopes
            for item in env.items
            if item.headers.get("type") == "event"
        ]
        assert len(events) == 1
        ev = events[0]
        assert ev["tags"]["statechart.action"] == "explode"
        crumbs = ev.get("breadcrumbs", {}).get("values", [])
        assert any(c.get("category") == "statechart" for c in crumbs)


@pytest.mark.parametrize(
    "module,package,cls",
    [
        ("structlog", "structlog", "StructlogPlugin"),
        ("loguru", "loguru", "LoguruPlugin"),
        ("sentry_sdk", "sentry-sdk", "SentryPlugin"),
    ],
)
def test_soft_dependency_missing_names_the_package(module, package, cls):
    src = importlib.util.find_spec("src").submodule_search_locations[0]
    code = (
        "import importlib.abc, sys\n"
        f"class B(importlib.abc.MetaPathFinder):\n"
        f"    def find_spec(self, n, p=None, t=None):\n"
        f"        if n.split('.')[0] == {module!r}: raise ImportError(n)\n"
        "sys.meta_path.insert(0, B())\n"
        f"sys.path.insert(0, {src!r})\n"
        "from xstate_statemachine.contrib import observability as o\n"
        "from xstate_statemachine.contrib.observability import logs, sentry\n"
        "from xstate_statemachine.exceptions import MissingExtraError\n"
        f"cls = getattr(logs, {cls!r}, None) or getattr(sentry, {cls!r})\n"
        "try:\n    cls()\nexcept MissingExtraError as e:\n    print(str(e))\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True
    )
    assert out.returncode == 0, out.stderr[-1500:]
    assert f"pip install {package}" in out.stdout
    assert f"`{module}` is not installed" in out.stdout


def test_instrument_all_soft_flags(machine_factory):
    pytest.importorskip("structlog")
    pytest.importorskip("loguru")
    pytest.importorskip("sentry_sdk")
    from src.xstate_statemachine.contrib.observability import (
        instrument_all,
        uninstrument_all,
    )

    attached = instrument_all(structlog=True, loguru=True, sentry=True)
    try:
        assert [type(p).__name__ for p in attached] == [
            "StructlogPlugin",
            "LoguruPlugin",
            "SentryPlugin",
        ]
    finally:
        uninstrument_all(attached)
