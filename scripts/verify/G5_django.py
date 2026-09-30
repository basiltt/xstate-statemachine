"""Verification for G5: #280-#283 (D1-D4) [django] / [drf] / [channels]
and #310 (D9) xsm_migrate_fsm.

`python scripts/verify/G5_django.py`.

Windows-safe (no heredocs, no /tmp). Runs the three contrib test folders,
the store contract suite (DjangoStore included), `from_state_ids`, the
example app and the doc pages' checks, then walks the issues' own
verification scripts against a throwaway copy of the test project:

* #280: `makemigrations --check` clean; `send("SUBMIT")`; persisted state
  and `available_events`; `in_state()`; a matured `after` fired by
  `xsm_deadlines`.
* #281: a `post_transition` receiver; intern denied vs manager approved;
  `history` rows with actor and reason.
* #282: `xsm_inspect --plain` / `xsm_diagram -f mermaid` output.
* #283: the issue's APIClient script (submit / send / history).
* #310: `scripts/verify/django_fsm_migration.py`.

Prints ``ALL OK``.
"""

from __future__ import annotations

import io
import os
import pathlib
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
PROJECT = ROOT / "tests" / "contrib" / "django" / "project"
# 💡 Verify THIS checkout even when an editable install points elsewhere
#    (git worktrees share one environment).
sys.path[:0] = [str(ROOT / "src"), str(PROJECT)]
TMP = pathlib.Path(tempfile.mkdtemp(prefix="xsm-g5-"))


def step(name: str) -> None:
    print(f"\n== {name}")


def _pytest(*targets: str, cwd: pathlib.Path = ROOT) -> None:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(ROOT / "src"), str(ROOT)]
        + [p for p in [env.get("PYTHONPATH")] if p]
    )
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            *targets,
            "-q",
            "-p",
            "no:cacheprovider",
        ],
        cwd=str(cwd),
        env=env,
    )
    assert proc.returncode == 0, f"tests failed: {targets}"


def run_tests() -> None:
    step("pytest contrib/django + drf + channels + store contract + adopt")
    _pytest(
        "tests/contrib/django",
        "tests/contrib/drf",
        "tests/contrib/channels",
        "tests/persistence/test_store_contract.py",
        "tests/persistence/test_adopt.py",
        "tests/contrib/test_extras_matrix.py",
    )
    step("example app + docs / packaging checks")
    _pytest(
        "tests/test_examples_integrations.py",
        "tests/test_docs_site.py",
        "tests/test_comparisons.py",
        "tests/test_compat_matrix.py",
        "tests/test_security_baseline.py",
        "tests/test_one_point_oh.py",
    )


def setup_project() -> None:
    os.environ["DJANGO_SETTINGS_MODULE"] = "project.settings"
    import django
    from django.conf import settings

    settings.DATABASES["default"]["NAME"] = str(TMP / "db.sqlite3")
    django.setup()
    from django.core.management import call_command

    call_command("makemigrations", "--check", "--dry-run", verbosity=0)
    call_command("migrate", verbosity=0)
    print("makemigrations --check: clean; migrate: ok")


def issue_280() -> None:
    step("#280 model field, mixin, lookups, deadlines")
    from django.core.management import call_command
    from shop.models import Order

    o = Order.objects.create()
    r = o.send("SUBMIT", wait=True)
    print(o.state, r.changed, Order.objects.in_state("order.review").count())
    assert r.changed and Order.objects.in_state("order.review").count() == 1
    o2 = Order.objects.get(pk=o.pk)
    print("persisted:", o2.state, o2.available_events)
    assert o2.available_events == ["FINANCE_OK", "LEGAL_OK", "RESET"]
    o2.send("LEGAL_OK")
    o2.send("FINANCE_OK")
    out = io.StringIO()
    call_command(
        "xsm_deadlines", "shop.Order", now=time.time() + 3600, stdout=out
    )
    print(out.getvalue().strip())
    assert Order.objects.get(pk=o.pk).state == "order.expired"


def issue_281() -> None:
    step("#281 signals, permissions, audit")
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Permission
    from shop.models import Approval

    from xstate_statemachine.contrib.django.signals import post_transition

    seen = []

    def rec(sender, **kw):
        seen.append(kw["event"].type)

    post_transition.connect(rec, weak=False)
    U = get_user_model()
    mgr = U.objects.create_user("mgr", "x@y.z", "p")
    mgr.user_permissions.add(
        Permission.objects.get(codename="approve_approval")
    )
    mgr = U.objects.get(pk=mgr.pk)
    a = Approval.objects.create()
    denied = a.send(
        "APPROVE", actor=U.objects.create_user("intern"), reason="try"
    ).denied
    ok = a.send("APPROVE", actor=mgr, reason="ok").changed
    rows = [(h.event, h.actor_id, h.reason) for h in a.history.all()]
    print(denied, ok, seen, rows)
    post_transition.disconnect(rec)
    assert denied and ok and seen[-1] == "APPROVE"
    assert rows[-1] == ("APPROVE", mgr.pk, "ok")


def issue_282() -> None:
    step("#282 management commands")
    from django.core.management import call_command

    for args in (
        ("xsm_inspect", "shop.Order", "--plain"),
        ("xsm_diagram", "shop.Order", "-f", "mermaid"),
    ):
        out = io.StringIO()
        call_command(*args, stdout=out)
        print("\n".join(out.getvalue().splitlines()[:5]))
        assert out.getvalue().strip()


def issue_283() -> None:
    step("#283 DRF (the issue's script)")
    from django.contrib.auth import get_user_model
    from rest_framework.test import APIClient
    from shop.models import Order

    u = get_user_model().objects.create_superuser("a", "a@b.c", "p")
    c = APIClient()
    c.force_authenticate(u)
    o = Order.objects.create()
    r = c.post(f"/api/orders/{o.pk}/submit/", {}, format="json")
    print(r.status_code, r.json()["state"])
    assert r.status_code == 200
    r = c.post(f"/api/orders/{o.pk}/send/", {"type": "RESET"}, format="json")
    print(r.status_code, r.json()["available_events"])
    assert r.json()["available_events"] == ["CANCEL", "INC", "SUBMIT"]
    first = c.get(f"/api/orders/{o.pk}/history/").json()[0]["event"]
    print(first)
    assert first == "SUBMIT"


def issue_310() -> None:
    step("#310 xsm_migrate_fsm (scripts/verify/django_fsm_migration.py)")
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/verify/django_fsm_migration.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    print(proc.stdout.strip())
    assert proc.returncode == 0 and "ALL OK" in proc.stdout, proc.stderr


def main() -> int:
    run_tests()
    setup_project()
    issue_280()
    issue_281()
    issue_282()
    issue_283()
    issue_310()
    print("\nALL OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
