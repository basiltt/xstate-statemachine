# examples/integrations/django_approvals/approvals/api.py
"""REST: one @action per event + drf-spectacular schema at /api/schema/."""

from __future__ import annotations

from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView
from rest_framework import mixins, serializers, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.routers import DefaultRouter

from xstate_statemachine.contrib.drf import (
    StatechartSerializerField,
    StatechartViewSetMixin,
)

from .models import Expense


class ExpenseSerializer(serializers.ModelSerializer):
    statechart = StatechartSerializerField()

    class Meta:
        model = Expense
        fields = ["id", "title", "amount", "statechart"]


class ExpenseViewSet(
    StatechartViewSetMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated]  # closed by default (X0.1)


router = DefaultRouter()
router.register("expenses", ExpenseViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
]
