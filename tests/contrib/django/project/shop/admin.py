# tests/contrib/django/project/shop/admin.py
"""Admin registrations of the test project."""

from django.contrib import admin

from xstate_statemachine.contrib.django.admin import StatechartAdminMixin

from .models import Approval, Order


@admin.register(Order)
class OrderAdmin(StatechartAdminMixin, admin.ModelAdmin):
    list_display = ("id", "title")
    xsm_confirm_events = ("CANCEL",)


@admin.register(Approval)
class ApprovalAdmin(StatechartAdminMixin, admin.ModelAdmin):
    list_display = ("id", "title")
