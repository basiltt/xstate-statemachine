# tests/contrib/django/project/shop/ws.py
"""Channels routes of the test project (#283)."""

from django.urls import path

from xstate_statemachine.contrib.channels import StatechartConsumer

from .models import Approval, Order


class OrderConsumer(StatechartConsumer):
    model = Order


class ApprovalConsumer(StatechartConsumer):
    model = Approval


websocket_urlpatterns = [
    path("ws/orders/<int:pk>/", OrderConsumer.as_asgi()),
    path("ws/approvals/<int:pk>/", ApprovalConsumer.as_asgi()),
]
