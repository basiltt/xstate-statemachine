#!/usr/bin/env python
# scripts/verify/django_fsm_migration.py
# -----------------------------------------------------------------------------
# ✅ #310 verification: xsm_migrate_fsm on a real django-fsm-2 model
# -----------------------------------------------------------------------------
# Boots the [django] test project on a throwaway SQLite file, seeds 2,000
# `legacy.Ticket` rows across the four FSM states, runs the data migration
# interrupted after two batches, then the command twice, and asserts: every
# row migrated exactly once, the second run is a no-op, and each row's
# `statechart_state` equals its old FSM `state`. Prints ALL OK.
#
#   pip install -e ".[django]" django-fsm-2 pytest-django
#   python scripts/verify/django_fsm_migration.py
# -----------------------------------------------------------------------------
"""Verify the django-fsm → statechart migration end to end."""

from __future__ import annotations

import io
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "tests" / "contrib" / "django" / "project"


def main() -> int:
    sys.path[:0] = [str(ROOT / "src"), str(PROJECT)]
    os.environ["DJANGO_SETTINGS_MODULE"] = "project.settings"
    tmp = Path(tempfile.mkdtemp(prefix="xsm-fsm-"))
    import django
    from django.conf import settings

    settings.DATABASES["default"]["NAME"] = str(tmp / "db.sqlite3")
    django.setup()
    from django.core.management import call_command

    call_command("migrate", verbosity=0)
    from legacy.models import Ticket

    from xstate_statemachine.contrib.django.fsm import migrate_rows

    states = ["new", "in_progress", "resolved", "closed"]
    Ticket.objects.bulk_create(
        [Ticket(state=states[i % 4]) for i in range(2000)]
    )
    done, batches = migrate_rows(Ticket, batch=500, stop_after_batches=2)
    assert (done, batches) == (1000, 2), (done, batches)
    print(f"interrupted after {batches} batches: {done} rows")

    def run() -> str:
        buf = io.StringIO()
        call_command(
            "xsm_migrate_fsm", "legacy.Ticket", "--batch", "500", stdout=buf
        )
        return buf.getvalue().strip()

    first, second = run(), run()
    print(first)
    print(second)
    assert "migrated 1000 row(s) in 2 batch(es); 0 remaining" in first
    assert "migrated 0 row(s) in 0 batch(es); 0 remaining" in second
    bad = sum(
        1
        for s, sc in Ticket.objects.values_list("state", "statechart_state")
        if sc != f"ticket.{s}"
    )
    assert bad == 0, f"{bad} rows disagree with their FSM state"
    assert Ticket.objects.filter(statechart__isnull=True).count() == 0
    print("ALL OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
