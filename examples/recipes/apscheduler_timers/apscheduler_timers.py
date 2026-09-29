# examples/recipes/apscheduler_timers/apscheduler_timers.py
# -----------------------------------------------------------------------------
# ⏰ Durable `after` timers woken by an APScheduler job (#308)
# -----------------------------------------------------------------------------
# 🏛️ A 7-day `after` cannot live in process memory -- the process will be
#    redeployed long before it fires. `persisted()` writes each armed timer
#    as a DEADLINE next to the snapshot; `DueTimerScanner.run_once` finds
#    matured deadlines and fires them. APScheduler only supplies the "call
#    this every minute" part, so any scheduler (cron, Celery Beat, a k8s
#    CronJob) is a drop-in replacement.
# ⚠️ Run exactly ONE scheduler role per store -- the same rule as
#    `python app.py --role scheduler` in examples/integrations/fastapi_orders.
#    (Two would be safe -- the optimistic save fences them -- but wasteful.)
# -----------------------------------------------------------------------------
"""Trial reminders on durable timers, scanned by an APScheduler job."""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from xstate_statemachine import MachineLogic, create_machine
from xstate_statemachine.persistence import (
    DueTimerScanner,
    SQLiteStore,
    persisted,
)

HERE = Path(__file__).resolve().parent
logger = logging.getLogger("trial")
PREFIX = "trial."


def build_machine(outbox: Optional[List[str]] = None) -> Any:
    sent = outbox if outbox is not None else []

    def send_reminder(i: Any, ctx: Dict, e: Any, a: Any) -> None:
        ctx["reminders"] += 1
        sent.append(f"reminder:{i.store_key}")

    def send_expiry_email(i: Any, ctx: Dict, e: Any, a: Any) -> None:
        sent.append(f"expired:{i.store_key}")

    config = json.loads((HERE / "machine.json").read_text("utf-8"))
    logic = MachineLogic(
        actions={
            "sendReminder": send_reminder,
            "sendExpiryEmail": send_expiry_email,
        }
    )
    return create_machine(config, logic=logic)


def start_trial(
    store: Any, machine: Any, user: str, clock: Any = None
) -> None:
    """Web role: create the instance; its deadlines are saved with it."""
    with persisted(store, f"{PREFIX}{user}", machine, clock=clock):
        pass


def build_scheduler(scanner: DueTimerScanner, *, cron: bool = False) -> Any:
    """A BackgroundScheduler running `scanner.run_once` every minute.

    ``cron=True`` uses a cron trigger (``minute="*"``) instead of an
    interval -- handy when the ops team thinks in crontab lines.
    """
    from apscheduler.schedulers.background import BackgroundScheduler

    sched = BackgroundScheduler(timezone="UTC")
    trigger = (
        ("cron", {"minute": "*"}) if cron else ("interval", {"seconds": 60})
    )
    sched.add_job(
        scanner.run_once,
        trigger[0],
        id="xsm-due-timers",
        max_instances=1,  # a slow scan is never overlapped by the next
        coalesce=True,  # missed runs collapse into one
        replace_existing=True,
        **trigger[1],
    )
    return sched


def main(argv: Optional[List[str]] = None) -> None:  # pragma: no cover
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", choices=["scheduler"], default="scheduler")
    parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    store = SQLiteStore(os.environ.get("XSM_DB", "trials.db"))
    machine = build_machine()
    scanner = DueTimerScanner(store, lambda key: machine, prefix=PREFIX)
    sched = build_scheduler(scanner)
    sched.start()
    try:
        import time

        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        sched.shutdown()


if __name__ == "__main__":  # pragma: no cover
    main()
