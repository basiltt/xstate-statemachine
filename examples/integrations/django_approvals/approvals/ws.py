# examples/integrations/django_approvals/approvals/ws.py
"""Channels: /ws/expenses/<pk>/ streams the live state (auth required)."""

from django.urls import path

from xstate_statemachine.contrib.channels import StatechartConsumer

from .models import Expense


class ExpenseConsumer(StatechartConsumer):
    model = Expense


websocket_urlpatterns = [
    path("ws/expenses/<int:pk>/", ExpenseConsumer.as_asgi()),
]
