# tests/contrib/drf/test_drf.py
"""#283: `StatechartViewSetMixin`, serializer field, permissions, schema."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ImproperlyConfigured
from rest_framework import viewsets
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

GOLDEN = json.loads(
    (Path(__file__).parents[1] / "state_body_golden.json").read_text("utf-8")
)


def _user(name: str, *perms: str) -> Any:
    U = get_user_model()
    u = U.objects.create_user(name, password="p")
    for p in perms:
        u.user_permissions.add(Permission.objects.get(codename=p))
    return U.objects.get(pk=u.pk)


@pytest.fixture
def alice(db: Any) -> Any:
    return _user("alice", "view_order", "view_approval", "approve_approval")


@pytest.fixture
def bob(db: Any) -> Any:
    return _user("bob")


def _client(user: Any = None) -> APIClient:
    c = APIClient()
    if user is not None:
        c.force_authenticate(user)
    return c


@pytest.fixture
def order(db: Any) -> Any:
    from shop.models import Order

    return Order.objects.create(title="o")


class TestRoutes:
    def test_router_exposes_generated_and_generic_routes(
        self, order: Any, alice: Any
    ) -> None:
        c = _client(alice)
        r = c.post(f"/api/orders/{order.pk}/submit/", {}, format="json")
        assert r.status_code == 200, r.content
        body = r.json()
        assert sorted(body) == GOLDEN["receipt_keys"]
        assert body["changed"] is True
        assert body["state"] == {
            "review": {"legal": "pending", "finance": "pending"}
        }
        r = c.post(f"/api/orders/{order.pk}/legal-ok/", {}, format="json")
        assert r.status_code == 200
        r = c.post(
            f"/api/orders/{order.pk}/send/", {"type": "RESET"}, format="json"
        )
        assert r.status_code == 200
        assert r.json()["available_events"] == ["CANCEL", "INC", "SUBMIT"]
        r = c.get(f"/api/orders/{order.pk}/events/")
        assert r.json()["available"] == ["CANCEL", "INC", "SUBMIT"]
        assert "LEGAL_OK" in r.json()["declared"]
        r = c.get(f"/api/orders/{order.pk}/history/")
        assert r.status_code == 200
        assert [h["event"] for h in r.json()] == [
            "SUBMIT",
            "LEGAL_OK",
            "RESET",
        ]
        assert r.json()[0]["actor"] == alice.pk

    def test_serializer_field_matches_the_fastapi_body(
        self, order: Any, alice: Any
    ) -> None:
        r = _client(alice).get(f"/api/orders/{order.pk}/")
        sc = r.json()["statechart"]
        assert sorted(sc) == GOLDEN["keys"]
        assert sc == GOLDEN["order_initial"]

    def test_status_matrix(self, order: Any, alice: Any) -> None:
        c = _client(alice)
        for e in ("SUBMIT", "LEGAL_OK", "FINANCE_OK"):
            order.send(e)
        # 409: a guard refused (amount 0)
        r = c.post(
            f"/api/orders/{order.pk}/pay/", {"amount": 0}, format="json"
        )
        assert r.status_code == 409 and r.json()["denied"] is True
        # 422: payload fails the event serializer
        r = c.post(
            f"/api/orders/{order.pk}/pay/", {"amount": -1}, format="json"
        )
        assert r.status_code == 422
        assert r.headers["Content-Type"].startswith("application/problem+json")
        assert "amount" in r.json()["errors"]
        # 422: unknown event on send/
        r = c.post(
            f"/api/orders/{order.pk}/send/", {"type": "NOPE"}, format="json"
        )
        assert (
            r.status_code == 422 and r.json()["error"] == "UnknownEventError"
        )
        r = c.post(f"/api/orders/{order.pk}/send/", {}, format="json")
        assert r.status_code == 422
        # 200 no-op: declared but not handled here
        r = c.post(f"/api/orders/{order.pk}/submit/", {}, format="json")
        assert r.status_code == 200 and r.json()["changed"] is False
        # 200 changed
        r = c.post(
            f"/api/orders/{order.pk}/pay/", {"amount": 3}, format="json"
        )
        assert r.status_code == 200 and r.json()["changed"] is True
        # 409: the instance is finished
        r = c.post(f"/api/orders/{order.pk}/inc/", {}, format="json")
        assert r.status_code == 409

    def test_202_for_a_deferred_event(self, alice: Any) -> None:
        from shop import logic
        from shop.models import Order

        from xstate_statemachine import create_machine

        cfg = json.loads(
            (
                Path(__file__).parents[1]
                / "django/project/shop/machines/order.json"
            ).read_text("utf-8")
        )
        cfg["onUnhandled"] = "defer"
        old = Order.statechart_machine
        Order.statechart_machine = create_machine(cfg, logic_modules=[logic])
        Order._xsm_machine_cache = None  # type: ignore[attr-defined]
        try:
            o = Order.objects.create()
            r = _client(alice).post(
                f"/api/orders/{o.pk}/pay/", {"amount": 1}, format="json"
            )
            assert r.status_code == 202 and r.json()["deferred"] is True
        finally:
            Order.statechart_machine = old
            del Order._xsm_machine_cache

    def test_permission_guard_403_and_two_users(
        self, alice: Any, bob: Any
    ) -> None:
        from shop.models import Approval

        a = Approval.objects.create()
        r = _client(bob).post(
            f"/api/approvals/{a.pk}/approve/", {}, format="json"
        )
        assert r.status_code == 403
        assert r.json() == {
            "type": "about:blank",
            "title": "Forbidden",
            "status": 403,
            "error": "PermissionDenied",
        }
        assert _client(bob).get(f"/api/approvals/{a.pk}/").json()[
            "statechart"
        ]["available_events"] == ["BOOM", "COMMENT"]
        r = _client(alice).post(
            f"/api/approvals/{a.pk}/approve/", {}, format="json"
        )
        assert r.status_code == 200 and r.json()["state"] == "approved"
        # history is a separate permission (view_approval)
        assert (
            _client(bob).get(f"/api/approvals/{a.pk}/history/").status_code
            == 403
        )
        assert (
            _client(alice).get(f"/api/approvals/{a.pk}/history/").status_code
            == 200
        )

    def test_unauthenticated_is_refused(self, order: Any) -> None:
        r = _client().post(
            f"/api/orders/{order.pk}/submit/", {}, format="json"
        )
        assert r.status_code == 403
        assert _client().get(f"/api/orders/{order.pk}/").status_code == 403

    def test_session_auth_enforces_csrf(self, order: Any, alice: Any) -> None:
        c = APIClient(enforce_csrf_checks=True)
        c.force_login(alice)
        r = c.post(f"/api/orders/{order.pk}/submit/", {}, format="json")
        assert r.status_code == 403
        order.refresh_from_db()
        assert order.state == "order.draft"

    def test_get_on_an_event_route_is_405(
        self, order: Any, alice: Any
    ) -> None:
        assert (
            _client(alice).get(f"/api/orders/{order.pk}/submit/").status_code
            == 405
        )


class TestIdempotency:
    def test_replay_is_duplicate_and_mismatch_is_422(
        self, order: Any, alice: Any, bob: Any
    ) -> None:
        c = _client(alice)
        h = {"HTTP_IDEMPOTENCY_KEY": "k-1"}
        r1 = c.post(
            f"/api/orders/{order.pk}/inc/", {"n": 1}, format="json", **h
        )
        assert r1.status_code == 200 and r1.json()["duplicate"] is False
        r2 = c.post(
            f"/api/orders/{order.pk}/inc/", {"n": 1}, format="json", **h
        )
        assert r2.status_code == 200 and r2.json()["duplicate"] is True
        order.refresh_from_db()
        assert order.machine.context["count"] == 1  # applied once
        assert order.statechart_version == 1
        r3 = c.post(
            f"/api/orders/{order.pk}/inc/", {"n": 2}, format="json", **h
        )
        assert r3.status_code == 422
        assert r3.json()["error"] == "IdempotencyMismatchError"
        # principal-scoped: bob's k-1 is a different key
        bob.user_permissions.add(Permission.objects.get(codename="view_order"))
        r4 = _client(bob).post(
            f"/api/orders/{order.pk}/inc/", {"n": 1}, format="json", **h
        )
        assert r4.status_code == 200 and r4.json()["duplicate"] is False

    def test_anonymous_user_has_no_principal(self, db: Any) -> None:
        """🐛 Battle #303 review H1 (fixed): `_xsm_principal` returned the
        constant "anonymous" for every unauthenticated user, so under an
        `[AllowAny]` policy all of them shared one idempotency scope."""
        from django.contrib.auth.models import AnonymousUser
        from rest_framework.test import APIRequestFactory

        from xstate_statemachine.contrib.drf import StatechartViewSetMixin

        req = APIRequestFactory().post("/x", {}, format="json")
        req.user = AnonymousUser()
        mixin = StatechartViewSetMixin()
        assert mixin._xsm_principal(req) is None
        req.user = _user("carol")
        assert mixin._xsm_principal(req) == f"user:{req.user.pk}"

    def test_idempotency_key_from_anonymous_is_401_not_pooled(
        self, order: Any
    ) -> None:
        """Defence in depth: `has_event_permission` already answers 403 to
        an anonymous user, so this branch is reached only if a subclass
        overrides that check -- and then it must still refuse (401), never
        scope the key to a shared "anonymous"."""
        from unittest import mock

        from django.contrib.auth.models import AnonymousUser
        from rest_framework.test import APIRequestFactory

        from shop.api import OrderViewSet

        req = APIRequestFactory().post(
            "/x", {}, format="json", HTTP_IDEMPOTENCY_KEY="k-anon"
        )
        req.user = AnonymousUser()
        view = OrderViewSet()
        view.request = req
        view.format_kwarg = None
        view.kwargs = {"pk": order.pk}
        with mock.patch(
            "xstate_statemachine.contrib.drf.viewsets.has_event_permission",
            return_value=True,
        ):
            resp = view.xsm_send(req, "INC", {})
        assert resp.status_code == 401, resp.data
        assert resp.data["error"] == "UnauthenticatedError"
        order.refresh_from_db()
        assert order.machine.context["count"] == 0


class TestConfiguration:
    def test_closed_by_default_without_permission_classes(self) -> None:
        from shop.models import Order

        from xstate_statemachine.contrib.drf import StatechartViewSetMixin

        with pytest.raises(ImproperlyConfigured, match="closed by default"):

            class Open(StatechartViewSetMixin, viewsets.GenericViewSet):
                queryset = Order.objects.all()

    def test_reserved_slug_collision(self) -> None:
        from rest_framework.permissions import AllowAny
        from shop.models import Order

        from xstate_statemachine import create_machine
        from xstate_statemachine.contrib.drf import StatechartViewSetMixin

        class Stub(Order):
            class Meta:
                proxy = True
                app_label = "shop"

        Stub.statechart_machine = create_machine(
            {"id": "s", "initial": "a", "states": {"a": {"on": {"SEND": "a"}}}}
        )
        try:
            with pytest.raises(ImproperlyConfigured, match="reserved"):

                class Bad(StatechartViewSetMixin, viewsets.GenericViewSet):
                    queryset = Stub.objects.all()
                    permission_classes = [AllowAny]

        finally:
            from django.apps import apps

            del apps.all_models["shop"]["stub"]
            apps.clear_cache()

    def test_event_slug(self) -> None:
        from xstate_statemachine.contrib.drf.viewsets import event_slug

        assert event_slug("LEGAL_OK") == "legal-ok"
        assert event_slug("order.paid") == "order-paid"
        with pytest.raises(ImproperlyConfigured):
            event_slug("___")


class TestSchema:
    def test_spectacular_schema_has_generated_actions(self) -> None:
        pytest.importorskip("drf_spectacular")
        from drf_spectacular.generators import SchemaGenerator
        from drf_spectacular.validation import validate_schema

        schema = SchemaGenerator().get_schema(request=None, public=True)
        validate_schema(schema)  # OpenAPI 3 validity
        paths = schema["paths"]
        submit = paths["/api/orders/{id}/submit/"]["post"]
        assert set(submit["responses"]) >= {"200", "202", "403", "409", "422"}
        assert submit["operationId"] == "orderviewset_submit"
        pay = paths["/api/orders/{id}/pay/"]["post"]
        body = pay["requestBody"]["content"]["application/json"]["schema"]
        assert body["$ref"].endswith("/PaySerializer") or "Pay" in body["$ref"]
        comps = schema["components"]["schemas"]
        assert {"Receipt", "Problem", "Events"} <= set(comps)
        assert "/api/orders/{id}/send/" in paths
        assert "/api/orders/{id}/history/" in paths
        # golden: the set of statechart paths per viewset
        xsm_paths = sorted(
            p for p in paths if p.startswith("/api/orders/{id}/")
        )
        assert xsm_paths == [
            "/api/orders/{id}/",
            "/api/orders/{id}/cancel/",
            "/api/orders/{id}/events/",
            "/api/orders/{id}/finance-ok/",
            "/api/orders/{id}/history/",
            "/api/orders/{id}/inc/",
            "/api/orders/{id}/legal-ok/",
            "/api/orders/{id}/pay/",
            "/api/orders/{id}/reset/",
            "/api/orders/{id}/send/",
            "/api/orders/{id}/stream/",
            "/api/orders/{id}/submit/",
        ]


def test_sse_stream_sends_state_then_stops(order: Any, alice: Any) -> None:
    from shop.api import OrderViewSet

    OrderViewSet.xsm_stream_max_s = 0.05
    OrderViewSet.xsm_stream_poll_s = 0.01
    try:
        r = _client(alice).get(f"/api/orders/{order.pk}/stream/")
        assert r.status_code == 200
        text = b"".join(r.streaming_content).decode()
    finally:
        OrderViewSet.xsm_stream_max_s = 300.0
        OrderViewSet.xsm_stream_poll_s = 0.5
    assert text.startswith("id: 0\nevent: state\ndata: {")
    assert '"state":"draft"' in text


def test_event_serializer_from_pydantic_model() -> None:
    pydantic = pytest.importorskip("pydantic")

    from xstate_statemachine.contrib.drf import event_serializer

    class Pay(pydantic.BaseModel):
        amount: int

    ser = event_serializer("PAY", model=Pay)(data={"amount": "5"})
    assert ser.is_valid() and ser.validated_data == {"amount": 5}
    bad = event_serializer("PAY", model=Pay)(data={"amount": "x"})
    assert not bad.is_valid() and bad.errors["payload"] == ["ValidationError"]
