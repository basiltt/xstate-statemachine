# src/xstate_statemachine/contrib/django/management/commands/xsm_deadlines.py
# -----------------------------------------------------------------------------
# ⏰ manage.py xsm_deadlines [app.Model ...] [--forever] [--interval S]
# -----------------------------------------------------------------------------
# 🏛️ `DueTimerScanner.run_once / run_forever` over the deadline index of
#    each named model (default: every `StatechartModelMixin` model). A
#    matured `after` timer fires in a fresh interpreter restored from the
#    row, which is written back under the ``<field>_version`` fence -- so
#    a web request racing the scanner on the same row cannot lose an
#    update (X0.9). Run it from cron / a worker every few seconds.
# -----------------------------------------------------------------------------
"""The ``xsm_deadlines`` management command."""

from __future__ import annotations

import signal
import threading
from typing import Any, List, Optional

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError

from ._resolve import database, model_from_label

__all__ = ["Command"]


def _models(labels: List[str]) -> List[Any]:
    if labels:
        return [model_from_label(label) for label in labels]
    from ...mixin import StatechartModelMixin

    return [
        m
        for m in apps.get_models()
        if issubclass(m, StatechartModelMixin) and not m._meta.abstract
    ]


class Command(BaseCommand):
    help = "Fire matured `after` deadlines of statechart models."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("models", nargs="*", metavar="app.Model")
        parser.add_argument("--forever", action="store_true")
        parser.add_argument("--interval", type=float, default=1.0)
        parser.add_argument("--limit", type=int, default=1000)
        parser.add_argument("--database", default="default")
        parser.add_argument(
            "--now",
            type=float,
            default=None,
            help="Scan as of this epoch time (testing / catch-up).",
        )

    def handle(self, *args: Any, **opts: Any) -> None:
        if opts["limit"] < 1:
            raise CommandError("--limit must be >= 1")
        if opts["interval"] <= 0:
            raise CommandError("--interval must be > 0")
        database(opts["database"])
        scanners = self._scanners(opts)
        try:
            if opts["forever"]:
                self._forever(scanners, opts["interval"])
                return
            self._scan(scanners, opts["now"])
        except DatabaseError as exc:
            # 🔥 #280 battle: an unmigrated database was a raw driver
            #    traceback; it is an operator error with a known fix.
            raise CommandError(
                f"{type(exc).__name__}: {exc} -- run `manage.py migrate` "
                "(is xstate_statemachine.contrib.django in INSTALLED_APPS?)"
            ) from None

    def _scanners(self, opts: Any) -> List[Any]:
        from .....persistence.timers import DueTimerScanner
        from ...stores import DjangoModelStore

        scanners = []
        for model in _models(opts["models"]):
            store = DjangoModelStore(model, using=opts["database"])

            def machine_for(key: str, m: Any = model) -> Any:
                return m().statechart_machine_node()

            scanners.append(
                (
                    model,
                    DueTimerScanner(
                        store,
                        machine_for,
                        limit=opts["limit"],
                        migrator=model.statechart_migrator,
                        on_version_mismatch=(
                            model.statechart_on_version_mismatch
                        ),
                    ),
                )
            )
        return scanners

    def _forever(
        self,
        scanners: List[Any],
        interval: float,
        stop: Optional[threading.Event] = None,
    ) -> None:
        """Scan every *interval* seconds until SIGINT / SIGTERM (or
        *stop*): the current pass finishes, then the command exits 0."""
        stop = stop or threading.Event()
        restore = _on_stop_signals(stop)
        try:
            while not stop.is_set():
                for _model, s in scanners:
                    s.run_once()
                stop.wait(interval)
        except KeyboardInterrupt:  # pragma: no cover - platform timing
            pass
        finally:
            restore()
        self.stdout.write("xsm_deadlines: stopped")

    def _scan(self, scanners: List[Any], now: Optional[float]) -> None:
        total = 0
        for model, s in scanners:
            res = s.scan(now)
            total += res.woken
            self.stdout.write(
                f"{model._meta.label}: woke {res.woken}/{res.due} due "
                f"(skipped {res.skipped_stale}, errors {len(res.errors)})"
            )
            for key, exc in res.errors:
                self.stderr.write(f"  {key}: {type(exc).__name__}: {exc}")
        self.stdout.write(f"total woken: {total}")


def _on_stop_signals(stop: threading.Event) -> Any:
    """Route SIGTERM (and SIGINT) to *stop*; returns the undo callable.
    Off the main thread signals cannot be installed -- a no-op then."""
    if threading.current_thread() is not threading.main_thread():
        return lambda: None
    saved = {}
    for name in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, name, None)
        if sig is not None:
            saved[sig] = signal.signal(sig, lambda *_: stop.set())

    def restore() -> None:
        for sig, handler in saved.items():
            signal.signal(sig, handler)

    return restore
