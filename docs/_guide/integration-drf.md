---
title: "DRF & Channels integration"
description: "Django REST framework actions generated from the chart, receipt-to-status like FastAPI, drf-spectacular schemas, and a Channels WebSocket consumer with auth on connect."
---

# Django REST framework & Channels

The DRF convention for a state machine is one hand-written `@action` per transition, each wrapping `can_proceed`. `StatechartViewSetMixin` generates those actions from the chart. It maps each `Receipt` to an HTTP status with the same core table FastAPI and Flask use, gates every event with the [Django](../integration-django/) permission guards, and describes all of it to drf-spectacular. `StatechartConsumer` is the Channels version of the Starlette WebSocket bridge: you get the current state on connect, and every committed transition is pushed to each connection watching that row.

## Install

```bash
pip install "xstate-statemachine[drf]"        # + djangorestframework
pip install "xstate-statemachine[channels]"   # + channels
pip install drf-spectacular                    # optional: the OpenAPI schema
```

Requires Django REST framework `>=3.14` and Channels `>=4`. Both also need the [`[django]`](../integration-django/) app in `INSTALLED_APPS`. Tested versions are in the [compatibility table](#compatibility).

For a complete, runnable project that uses this viewset mixin and the Channels consumer together with the admin and signals, see the [`django_approvals` example](https://github.com/basiltt/xstate-statemachine/tree/main/examples/integrations/django_approvals).

## Quick start

<!-- doc-requires: django, rest_framework -->
```python
import django
from django.conf import settings

settings.configure(
    INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth",
                    "rest_framework", "xstate_statemachine.contrib.django"],
    DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
    DEFAULT_AUTO_FIELD="django.db.models.BigAutoField", ROOT_URLCONF=__name__,
    REST_FRAMEWORK={"DEFAULT_AUTHENTICATION_CLASSES": []},
)
django.setup()

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection, models
from django.urls import include, path
from rest_framework import mixins, serializers, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.routers import DefaultRouter
from rest_framework.test import APIClient
from xstate_statemachine.contrib.django import StatechartField, StatechartModelMixin
from xstate_statemachine.contrib.drf import StatechartSerializerField, StatechartViewSetMixin

class Order(StatechartModelMixin, models.Model):
    statechart_machine = {"id": "order", "initial": "cart", "states": {
        "cart": {"on": {"CHECKOUT": "paying"}},
        "paying": {"on": {"PAY": "paid", "CANCEL": "cart"}},
        "paid": {"type": "final"}}}
    statechart = StatechartField()

    class Meta:
        app_label = "shop"

class OrderSerializer(serializers.ModelSerializer):
    statechart = StatechartSerializerField()
    class Meta:
        model, fields = Order, ["id", "statechart"]

class OrderViewSet(StatechartViewSetMixin, mixins.RetrieveModelMixin,
                   viewsets.GenericViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]      # required: closed by default

router = DefaultRouter()
router.register("orders", OrderViewSet)
urlpatterns = [path("api/", include(router.urls))]

call_command("migrate", verbosity=0)
with connection.schema_editor() as editor:
    editor.create_model(Order)

client = APIClient()
client.force_authenticate(get_user_model().objects.create_user("alice"))
order = Order.objects.create()
r = client.post(f"/api/orders/{order.pk}/checkout/", {}, format="json")
assert r.status_code == 200 and r.json()["state"] == "paying"
r = client.post(f"/api/orders/{order.pk}/send/", {"type": "PAY"}, format="json")
assert r.status_code == 200 and r.json()["changed"] is True
r = client.post(f"/api/orders/{order.pk}/cancel/", {}, format="json")
assert r.status_code == 409                       # finished: refused
assert client.get(f"/api/orders/{order.pk}/").json()["statechart"]["state"] == "paid"
```

## Reference

### `StatechartViewSetMixin`

Mix it into a `GenericViewSet` over a `StatechartModelMixin` model. The model comes from `queryset.model`, or you can set `statechart_model`.

| Route | Method | What |
|:--|:--|:--|
| `{pk}/<event-slug>/` | `POST` | one generated `@action` per declared event (`SUBMIT` → `submit/`, `LEGAL_OK` → `legal-ok/`); the body is the payload |
| `{pk}/send/` | `POST` | `{"type": "EVENT", ...payload}`; an undeclared type is 422 |
| `{pk}/events/` | `GET` | `{"available": [...events this user may send now], "declared": [...]}` |
| `{pk}/history/` | `GET` | `TransitionLog` rows, through the view's `pagination_class` and `filter_backends`; guarded by `xsm_history_permission_classes` (default: the model's `view` permission), separate from send permission |
| `{pk}/stream/` | `GET` | Server-Sent Events: the state now, then after every committed change (`xsm_stream_poll_s`, `xsm_heartbeat_s`, `xsm_stream_max_s`) |

The status of a send is the core [`receipts`](../persistence/) table (#305), the same one FastAPI, Flask and Starlette use:

| Outcome | Status |
|:--|:--|
| transition taken, or a clean no-op | 200 |
| deferred (`onUnhandled: "defer"`) | 202 |
| a permission guard refuses **this user** (`has_event_permission`) | 403 problem |
| a guard refused it, or the instance is finished / stopped | 409 (receipt body) |
| `Idempotency-Key` reused with a different body | 422 problem |
| payload fails the event serializer / unknown event on `send/` | 422 problem |
| `ConflictError` / `LockTimeoutError` | 409 problem |
| `StoreUnavailableError` (the store's backend is down, e.g. a Redis failover) | 503 problem -- retryable |

The receipt body is FastAPI's `ReceiptModel`: `state`, `state_ids`, `available_events`, `machine_version`, `changed`, `denied`, `deferred`, `duplicate`, `error` (a class name).

Attributes: `xsm_event_serializers = {"PAY": PaySerializer}` (validation, and the request schema), `xsm_context_serializer` (off by default, X0.1), `xsm_inbox` (default `DjangoInbox()`; `None` turns `Idempotency-Key` off), `xsm_history_permission_classes`, `xsm_history_filter_backends`, `xsm_lock`.

**Filter backends.** DRF also runs a view's `filter_backends` over `get_object()`'s queryset, not only over `history/`. A backend written for `TransitionLog` rows must return any other queryset unchanged, or every detail route (`history/` included) fails. To filter `history/` only, put the backend in `xsm_history_filter_backends` instead.

**Idempotency.** A replayed `Idempotency-Key` returns the original receipt's `state` and `state_ids`. It does not return the row's state now; `GET /{pk}/` gives that. `context` (when `xsm_context_serializer` is set) is the row's **current** context. A replay still answers after the machine has finished. A **new** key sent to a finished machine gets the normal 409 receipt and is not left marked as in flight. With `xsm_inbox = None` the `Idempotency-Key` header is ignored. An `Idempotency-Key` with no authenticated user is 401. The audit reason for a send goes in the `X-XSM-Reason` header (`reason` is a reserved payload key). The OpenAPI schema documents both headers and the 401 and 503 responses.

**`event_serializer(event, fields=None, *, model=None)`** builds a `Serializer` for one event's payload from DRF fields or from a pydantic model (A9).

### `StatechartSerializerField`

A read-only field (`source="*"`) that renders the instance as FastAPI's `GET /{id}` body: `{"state", "state_ids", "available_events", "machine_version"}`. A shared golden fixture keeps the two identical. `available_events` is computed for `request.user` (`per_user=True`). Context is included only through `context_serializer=` (X0.1).

### Permissions

`StatechartEventPermission` is a DRF `BasePermission`: `has_object_permission` checks `has_event_permission(request.user, obj, view.xsm_event)`. `StatechartHistoryPermission` requires the model's `view` permission. The mixin already applies both. Use them yourself in hand-written actions.

### OpenAPI (drf-spectacular)

When drf-spectacular is installed, every generated action carries its own `operationId` (`orderviewset_submit`), its event serializer as the request body, and 200/202/403/409/422 responses built from `Receipt` and `Problem` components. `events/`, `history/` and `stream/` are typed too. The test suite runs `validate_schema` on the generated document. Without drf-spectacular the decorators are no-ops.

### `StatechartConsumer` (Channels)

```text
class OrderConsumer(StatechartConsumer):
    model = Order                       # or override get_instance()

application = ProtocolTypeRouter({
    "websocket": AuthMiddlewareStack(URLRouter([
        path("ws/orders/<int:pk>/", OrderConsumer.as_asgi())])),
})
```

| Direction | Message |
|:--|:--|
| server → client, on connect | `{"kind": "snapshot", "state", "state_ids", "available_events", "machine_version"}` |
| client → server | `{"type": "PAY", "payload": {...}}`; `{"type": "xsm.ping"}` → `{"kind": "pong"}` |
| server → sender | `{"kind": "receipt", ...receipt body, "status": 200}` or `{"kind": "error", "status", "title", "error"}` |
| server → every connection on the row | `{"kind": "transition", "event", "version", ...state}` (group `xsm.<app>.<model>.<pk>`) |
| server → client, every `heartbeat_s` | `{"kind": "ping"}` |

Sends run the model's `send()` inside `database_sync_to_async`, so the row lock never blocks the event loop. Hooks: `get_instance()`, `authorize(user, instance)` (default: the model's `view` permission), `group_name(instance)` (a `@staticmethod`; an override is registered with the broadcaster, so its group still receives pushes -- a plain instance-method override keeps working too, but if it genuinely needs `self` the broadcaster cannot call it and that consumer only sees its own sockets' transitions, logged once), `context_serializer`. `live_consumers()` reports how many consumers are connected in this process.

**Where pushes come from.** The `transition` push is sent by a `post_transition(on_commit=True)` receiver (`xstate_statemachine.contrib.channels.broadcast`, connected when the consumer module is imported). It is not sent by the socket that made the change. A transition committed anywhere (the admin, a REST call, a management command, another socket) reaches every subscriber on the row once. A rolled-back send reaches nobody. A socket sender gets its `receipt` first, then the same `transition` push as everyone else. If the channel layer is down, the failure is logged (`channels: could not broadcast ...`) and the commit still succeeds. A subscriber that does not read loses pushes once its channel is full (the in-memory layer holds 100). The sender is never blocked. Every push re-reads the row, so the body is always current. `version` is the version that was committed.

**Frames and close codes.**

| Situation | Result |
|:--|:--|
| malformed JSON, a binary frame, no string `type`, a non-object `payload`, an unknown event | `{"kind": "error", "status": 422, ...}`; the socket stays open |
| an event the user may not send | `{"kind": "error", "status": 403, ...}` |
| no `AuthMiddlewareStack` (logged as a warning), anonymous user, no `view` permission, no such row | closed with **1008** before any state is sent |
| permission revoked, user deactivated or deleted | closed with **1008** on the next push or heartbeat |

**Origins.** `AllowedHostsOriginValidator` takes its list from `ALLOWED_HOSTS`, so `ALLOWED_HOSTS = ["*"]` accepts every origin. For a frontend on a separate origin, use `OriginValidator(app, ["https://app.example.com"])` instead.

## Guarantees

> **What this does:** every generated action goes through the same model `send()`, in one transaction with the audit row. The response status is the core receipt mapping, shared with FastAPI and Flask. `Idempotency-Key` replays return the original receipt with `duplicate: true` and write nothing. A replay with a different body is 422. Keys are scoped per user (X0.2). A committed transition reaches every Channels connection on that row, including connections on other workers through the channel layer. Consumers leave nothing behind: after 100 connect/disconnect cycles, zero consumers and no stray tasks are left (a pinned test).
>
> **What this does not do:** it does not authenticate anyone. That is DRF's authentication classes and Channels' `AuthMiddlewareStack`. It does not push to a client whose socket dropped. Reconnect and read the snapshot. The SSE `stream/` action polls the row and holds a worker for its whole lifetime (run it under ASGI or a threaded server).
>
> See the programme-wide [Guarantees](../guarantees/) and [Security](../security/) pages ([#303](https://github.com/basiltt/xstate-statemachine/issues/303)).

## Threat model

> **Who can call this:** whoever passes the viewset's `permission_classes`. **Closed by default (X0.1):** a concrete viewset **without explicit `permission_classes` raises `ImproperlyConfigured`** at import. Write `[AllowAny]` if you really mean it. Each event is then re-checked per object with `has_event_permission` (403). Over WebSocket, an unauthenticated scope (no `AuthMiddlewareStack`, or an anonymous user), a user without `view` permission, or an unknown row is **closed with 1008** before any state is sent.
>
> **What it exposes:** state ids, the XState value, the events the caller may send, and the machine version. **Context only through an explicit serializer.** Errors are RFC 9457 problems with a fixed title and the exception **class name**, never its message (X0.7). `history/` exposes actors and reasons, so it needs a separate permission (the model's `view` permission by default).
>
> **You must configure:** `permission_classes` on every viewset, and an authentication class. With `SessionAuthentication`, DRF enforces **CSRF** on unsafe methods, so browser clients must send the `X-CSRFToken` header (a test pins the 403 without it). Configure `AuthMiddlewareStack` (and `AllowedHostsOriginValidator` for cookie-authenticated sockets) around the Channels router. Set a `context_serializer` only for fields the caller may see.

## Compatibility

| Package | Python | Tested in CI |
|:--|:--|:--|
| Django REST framework 3.14 – 3.x | 3.9 – 3.14 | ✅ |
| Channels 4.0 – 4.x | 3.9 – 3.14 | ✅ |

See the generated [compatibility table](../compatibility/).

## Troubleshooting

| Symptom | Cause | Fix |
|:--|:--|:--|
| `MissingExtraError: ... pip install "xstate-statemachine[drf]"` | extra not installed | run the command (`[channels]` likewise) |
| `ImproperlyConfigured: ... must set permission_classes explicitly` | closed by default (X0.1) | set `permission_classes` on the viewset |
| `ImproperlyConfigured: event 'SEND' maps to URL 'send', which is reserved` | an event collides with `send/`, `events/`, `history/` or `stream/` | rename the event |
| 403 `CSRF Failed` from a browser | `SessionAuthentication` enforces CSRF | send the `X-CSRFToken` header |
| 403 problem `PermissionDenied` on an event | a permission guard refuses this user | grant the permission, or check `permitted_events(user, obj)` |
| WebSocket closes with 1008 | no `AuthMiddlewareStack`, anonymous user, no `view` permission, or no such row | wrap the router; log in; grant `view_<model>` |
| `ModuleNotFoundError: daphne` in tests | `channels.testing` imports daphne | `pip install daphne` (test-only) |
