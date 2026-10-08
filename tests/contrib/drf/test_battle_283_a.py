# tests/contrib/drf/test_battle_283_a.py
"""Battle #283 (adversary A): the DRF API under a hostile, retrying,
concurrent client -- idempotency edges, the status matrix, history /
events / stream, the serializer field, CSRF and lock modes."""

from __future__ import annotations

import threading
from typing import Any, List

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def _user(name: str, *perms: str) -> Any:
    U = get_user_model()
    u = U.objects.create_user(name, password="p")
    for p in perms:
        u.user_permissions.add(Permission.objects.get(codename=p))
    return U.objects.get(pk=u.pk)


@pytest.fixture
def alice(db: Any) -> Any:
    return _user("alice", "view_order", "view_approval", "approve_approval")


def _client(user: Any) -> APIClient:
    c = APIClient()
    c.force_authenticate(user)
    return c


@pytest.fixture
def order(db: Any) -> Any:
    from shop.models import Order

    return Order.objects.create(title="o")


def _url(order: Any, route: str) -> str:
    return f"/api/orders/{order.pk}/{route}/"


def _key(k: str) -> dict:
    return {"HTTP_IDEMPOTENCY_KEY": k}


# -----------------------------------------------------------------------------
# 🔁 Idempotency
# -----------------------------------------------------------------------------
class TestIdempotencyEdges:
    def test_fresh_key_on_finished_row_is_not_poisoned(
        self, order: Any, alice: Any
    ) -> None:
        """🐛 A NEW key sent to a finished machine was claimed by the
        inbox, then dropped by the engine: the claim stayed in flight and
        every retry got 409 in-flight for the inbox TTL, instead of the
        same stopped answer."""
        c = _client(alice)
        assert c.post(_url(order, "cancel"), {}, format="json").status_code
        r1 = c.post(_url(order, "inc"), {}, format="json", **_key("fresh"))
        r2 = c.post(_url(order, "inc"), {}, format="json", **_key("fresh"))
        assert r1.status_code == r2.status_code == 409
        assert r1.json()["error"] == r2.json()["error"]
        assert r2.json()["error"] == "InterpreterStoppedError"

    def test_same_key_other_event_is_422_never_applied(
        self, order: Any, alice: Any
    ) -> None:
        c = _client(alice)
        r = c.post(_url(order, "inc"), {}, format="json", **_key("x"))
        assert r.status_code == 200
        r = c.post(_url(order, "submit"), {}, format="json", **_key("x"))
        assert r.status_code == 422, r.content
        order.refresh_from_db()
        assert order.machine.current_state_ids == {"order.draft"}

    def test_same_key_two_rows_are_independent(
        self, order: Any, alice: Any
    ) -> None:
        from shop.models import Order

        other = Order.objects.create(title="p")
        c = _client(alice)
        for o in (order, other):
            r = c.post(_url(o, "inc"), {}, format="json", **_key("shared"))
            assert r.status_code == 200 and r.json()["duplicate"] is False
        other.refresh_from_db()
        assert other.machine.context["count"] == 1

    def test_replay_after_row_deleted_is_404(
        self, order: Any, alice: Any
    ) -> None:
        c = _client(alice)
        c.post(_url(order, "inc"), {}, format="json", **_key("gone"))
        pk = order.pk
        order.delete()
        r = c.post(f"/api/orders/{pk}/inc/", {}, format="json", **_key("gone"))
        assert r.status_code == 404

    def test_replay_body_is_the_original_state_not_current(
        self, order: Any, alice: Any
    ) -> None:
        c = _client(alice)
        r1 = c.post(_url(order, "submit"), {}, format="json", **_key("s"))
        c.post(_url(order, "send"), {"type": "RESET"}, format="json")
        r2 = c.post(_url(order, "submit"), {}, format="json", **_key("s"))
        assert r2.json()["duplicate"] is True
        assert r2.json()["state"] == r1.json()["state"]
        assert r2.json()["state_ids"] == r1.json()["state_ids"]

    def test_replay_context_is_current_documented(
        self, order: Any, alice: Any
    ) -> None:
        """Decision: a receipt stores ids, not context -- the replay's
        ``context`` (when `xsm_context_serializer` is set) is the row's
        CURRENT context. Documented on the attribute."""
        from shop.api import OrderViewSet

        from xstate_statemachine.contrib.drf import StatechartViewSetMixin

        assert "row's CURRENT" in (StatechartViewSetMixin.__doc__ or "")
        OrderViewSet.xsm_context_serializer = staticmethod(dict)
        try:
            c = _client(alice)
            c.post(_url(order, "inc"), {}, format="json", **_key("c"))
            c.post(_url(order, "inc"), {}, format="json")
            r = c.post(_url(order, "inc"), {}, format="json", **_key("c"))
            assert r.json()["duplicate"] is True
            assert r.json()["context"]["count"] == 2
        finally:
            del OrderViewSet.xsm_context_serializer

    def test_inbox_none_ignores_the_header(
        self, order: Any, alice: Any
    ) -> None:
        from shop.api import OrderViewSet

        OrderViewSet.xsm_inbox = None
        try:
            c = _client(alice)
            for _ in range(2):
                r = c.post(_url(order, "inc"), {}, format="json", **_key("n"))
                assert r.status_code == 200
                assert r.json()["duplicate"] is False
        finally:
            del OrderViewSet.xsm_inbox
        order.refresh_from_db()
        assert order.machine.context["count"] == 2

    @pytest.mark.django_db(transaction=True)
    def test_concurrent_identical_requests_apply_once(self) -> None:
        from django.db import connection

        from shop.models import Order

        alice = _user("alice2", "view_order")
        order = Order.objects.create(title="c")
        codes: List[Any] = []

        def go() -> None:
            try:
                r = _client(alice).post(
                    _url(order, "inc"), {}, format="json", **_key("race")
                )
                codes.append((r.status_code, r.json()))
            finally:
                connection.close()

        ts = [threading.Thread(target=go) for _ in range(8)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        assert all(c in (200, 409) for c, _ in codes), codes
        fresh = [b for c, b in codes if c == 200 and not b["duplicate"]]
        assert len(fresh) == 1, codes
        order.refresh_from_db()
        assert order.machine.context["count"] == 1


# -----------------------------------------------------------------------------
# 🧱 Status matrix
# -----------------------------------------------------------------------------
class TestStatusMatrix:
    @pytest.mark.parametrize(
        "key", ["priority", "wait", "actor", "reason", "idempotency_key"]
    )
    def test_reserved_body_keys_are_422(
        self, order: Any, alice: Any, key: str
    ) -> None:
        for route, body in (("inc", {}), ("send", {"type": "INC"})):
            r = _client(alice).post(
                _url(order, route), {**body, key: 1}, format="json"
            )
            assert r.status_code == 422, (route, key, r.content)

    def test_type_in_per_event_body_does_not_redirect(
        self, order: Any, alice: Any
    ) -> None:
        r = _client(alice).post(
            _url(order, "inc"), {"type": "SUBMIT"}, format="json"
        )
        order.refresh_from_db()
        assert r.status_code in (200, 422)
        assert order.machine.current_state_ids == {"order.draft"}

    @pytest.mark.parametrize("body", ["[1, 2]", '"str"', "5", "null"])
    def test_non_object_body_is_422(
        self, order: Any, alice: Any, body: str
    ) -> None:
        for route in ("inc", "send"):
            r = _client(alice).post(
                _url(order, route), body, content_type="application/json"
            )
            assert r.status_code in (400, 422), (route, body, r.content)

    @pytest.mark.parametrize("etype", ["ÉVÉNEMENT", "X" * 300, " INC"])
    def test_odd_type_on_send_is_422(
        self, order: Any, alice: Any, etype: str
    ) -> None:
        r = _client(alice).post(
            _url(order, "send"), {"type": etype}, format="json"
        )
        assert r.status_code == 422

    def test_large_body_does_not_500(self, order: Any, alice: Any) -> None:
        r = _client(alice).post(
            _url(order, "inc"), {"blob": "x" * 2_000_000}, format="json"
        )
        assert r.status_code < 500

    def test_not_permitted_vs_undeclared(self, alice: Any) -> None:
        """Declared but not permitted → 403 on BOTH routes; undeclared →
        404 per-event (no route) / 422 on send/."""
        from shop.models import Approval

        bob = _user("bob", "view_approval")
        a = Approval.objects.create(title="a")
        c = _client(bob)
        r1 = c.post(f"/api/approvals/{a.pk}/approve/", {}, format="json")
        r2 = c.post(
            f"/api/approvals/{a.pk}/send/", {"type": "APPROVE"}, format="json"
        )
        assert r1.status_code == r2.status_code == 403
        r3 = c.post(f"/api/approvals/{a.pk}/nope/", {}, format="json")
        r4 = c.post(
            f"/api/approvals/{a.pk}/send/", {"type": "NOPE"}, format="json"
        )
        assert (r3.status_code, r4.status_code) == (404, 422)

    def test_events_lists_exactly_permitted(self, alice: Any) -> None:
        from shop.models import Approval

        from xstate_statemachine.contrib.django.permissions import (
            permitted_events,
        )

        bob = _user("bob", "view_approval")
        a = Approval.objects.create(title="a")
        for u in (alice, bob):
            body = _client(u).get(f"/api/approvals/{a.pk}/events/").json()
            assert body["available"] == permitted_events(u, a)
        avail = _client(bob).get(f"/api/approvals/{a.pk}/events/").json()
        assert "APPROVE" not in avail["available"]


# -----------------------------------------------------------------------------
# 📜 history / schema / CSRF
# -----------------------------------------------------------------------------
class TestHistoryAndSchema:
    def test_history_honours_pagination_and_filters(
        self, order: Any, alice: Any
    ) -> None:
        from rest_framework.pagination import PageNumberPagination

        from shop.api import OrderViewSet

        class Two(PageNumberPagination):
            page_size = 2

        class OnlyInc:
            def filter_queryset(self, request: Any, qs: Any, view: Any):
                # the view's backends also filter get_object()'s queryset
                if qs.model._meta.model_name == "order":
                    return qs
                return qs.filter(event="INC")

        c = _client(alice)
        for _ in range(3):
            c.post(_url(order, "inc"), {}, format="json")
        c.post(_url(order, "submit"), {}, format="json")
        OrderViewSet.pagination_class = Two
        OrderViewSet.filter_backends = [OnlyInc]
        try:
            body = c.get(_url(order, "history")).json()
        finally:
            del OrderViewSet.pagination_class, OrderViewSet.filter_backends
        assert body["count"] == 3 and len(body["results"]) == 2
        assert {row["event"] for row in body["results"]} == {"INC"}

    def test_may_send_but_not_read_history(self, order: Any) -> None:
        """Sending needs only the chart's guards; ``history/`` needs the
        model's ``view`` perm -- a separate grant."""
        carol = _user("carol")
        c = _client(carol)
        assert c.post(_url(order, "inc"), {}, format="json").status_code == 200
        r = c.get(_url(order, "history"))
        assert r.status_code == 403
        assert r["Content-Type"].startswith("application/problem+json")

    def test_schema_documents_headers_and_problem_statuses(self) -> None:
        from drf_spectacular.generators import SchemaGenerator
        from drf_spectacular.validation import validate_schema

        schema = SchemaGenerator().get_schema(request=None, public=True)
        validate_schema(schema)
        for path, item in schema["paths"].items():
            op = item.get("post")
            if op is None:
                continue
            assert {"401", "403", "409", "422", "503"} <= set(
                op["responses"]
            ), path
            headers = {
                p["name"] for p in op["parameters"] if p["in"] == "header"
            }
            assert headers == {"Idempotency-Key", "X-XSM-Reason"}, path
        field = schema["components"]["schemas"]["Order"]["properties"][
            "statechart"
        ]
        assert field["type"] == "object"
        assert "state_ids" in field["properties"]

    def test_session_auth_post_without_csrf_is_403(
        self, order: Any, alice: Any
    ) -> None:
        c = APIClient(enforce_csrf_checks=True)
        assert c.login(username="alice", password="p")
        r = c.post(_url(order, "inc"), {}, format="json")
        assert r.status_code == 403
        order.refresh_from_db()
        assert order.statechart_version == 0


# -----------------------------------------------------------------------------
# 🧵 Concurrency
# -----------------------------------------------------------------------------
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("lock", ["pessimistic", "optimistic"])
def test_many_threads_one_row(lock: str) -> None:
    from django.db import connection

    from shop.api import OrderViewSet
    from shop.models import Order

    user = _user(f"u-{lock}", "view_order")
    order = Order.objects.create(title="t")
    out: List[Any] = []
    OrderViewSet.xsm_lock = lock
    try:

        def go() -> None:
            try:
                r = _client(user).post(_url(order, "inc"), {}, format="json")
                out.append((r.status_code, r.json()))
            finally:
                connection.close()

        ts = [threading.Thread(target=go) for _ in range(20)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
    finally:
        del OrderViewSet.xsm_lock
    codes = [c for c, _ in out]
    assert len(codes) == 20 and set(codes) <= {200, 409}, out
    for c, body in out:
        if c == 409:
            assert body["error"] in ("ConflictError", "LockTimeoutError")
    order.refresh_from_db()
    assert order.machine.context["count"] == codes.count(200)
    assert order.statechart_version == codes.count(200)
