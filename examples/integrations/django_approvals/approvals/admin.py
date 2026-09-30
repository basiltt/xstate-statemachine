# examples/integrations/django_approvals/approvals/admin.py
"""Admin: transition buttons (CSRF POST forms, permission-computed),
confirm + reason for REJECT (meta.confirm), audit history inline."""

from django.contrib import admin

from xstate_statemachine.contrib.django import StatechartAdminMixin

from .models import Expense


@admin.register(Expense)
class ExpenseAdmin(StatechartAdminMixin, admin.ModelAdmin):
    list_display = ("id", "title", "amount")
