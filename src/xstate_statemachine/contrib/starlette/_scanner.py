# src/xstate_statemachine/contrib/starlette/_scanner.py
# -----------------------------------------------------------------------------
# ⏰ The registry's `DueTimerScanner` lifecycle (split out of registry.py
#    to keep it under the 800-line rule; battle #275)
# -----------------------------------------------------------------------------
"""`_ScannerMixin`: start / stop the persisted-timer scanner thread."""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any

from ._fanout import TimerPublisher
from ._http import receipt_body

logger = logging.getLogger("xstate_statemachine.contrib.starlette")


class _ScannerMixin:
    """Mixed into `StatechartRegistry`; expects its attributes."""

    _sync_store: Any
    plugins: Any
    subscribers: Any
    lock: Any
    migrator: Any
    scanner: Any
    scanner_now: Any
    scanner_interval_s: float
    _scanner_thread: Any

    def _reg(self, name: str) -> Any:  # pragma: no cover -- registry's
        raise NotImplementedError

    def machine_for_store_key(self, store_key: str) -> Any:  # pragma: no cover
        raise NotImplementedError

    def _start_scanner(self) -> None:
        from ...persistence.timers import DueTimerScanner

        if self._sync_store is None:
            raise RuntimeError(
                "run_timers=True needs a sync StateStore (the scanner runs "
                "in a thread); pass the sync store to the registry."
            )
        # 🔥 battle #275 (B): the scanner saves through `persisted()` in
        #    its thread, never through `act()`, so open SSE / WebSocket
        #    streams never heard about `after` transitions. A
        #    `TimerPublisher` on the scanner's OWN plugin list publishes
        #    committed receipts onto this loop (`act()` publishes its
        #    own; never twice). Attached here, at lifespan startup, on
        #    the loop that will serve the streams.
        plugins = list(self.plugins)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:  # pragma: no cover -- sync caller
            loop = None
        if loop is not None:

            def body_of(interp: Any, receipt: Any, name: str):
                reg = self._reg(name)
                return receipt_body(
                    interp, receipt, context_serializer=reg.context_serializer
                )

            plugins.append(TimerPublisher(self.subscribers, loop, body_of))
        self.scanner = DueTimerScanner(
            self._sync_store,
            self.machine_for_store_key,
            lock=self.lock,
            plugins=plugins,
            now=self.scanner_now,
            migrator=self.migrator,
        )
        scanner = self.scanner
        self._scanner_thread = threading.Thread(
            target=scanner.run_forever,
            args=(self.scanner_interval_s,),
            name="xsm-timer-scanner",
            daemon=True,
        )
        self._scanner_thread.start()

    def _stop_scanner(self, timeout: float) -> None:
        if self.scanner is not None:
            self.scanner.stop()
        if self._scanner_thread is not None:
            self._scanner_thread.join(timeout)
            if self._scanner_thread.is_alive():
                logger.warning(
                    "⚠️ timer scanner did not stop in %.1fs", timeout
                )
        self.scanner = None
        self._scanner_thread = None
