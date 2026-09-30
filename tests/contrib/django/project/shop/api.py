# tests/contrib/django/project/shop/api.py
"""DRF routes of the test project (#283)."""

from __future__ import annotations

from django.urls import include, path
from rest_framework import mixins, serializers, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.routers import DefaultRouter

from xstate_statemachine.contrib.drf import (
    StatechartSerializerField,
    StatechartViewSetMixin,
    event_serializer,
)

from .models import Approval, Order


class OrderSerializer(serializers.ModelSerializer):
    statechart = StatechartSerializerField()

    class Meta:
        model = Order
        fields = ["id", "title", "statechart"]


class OrderViewSet(
    StatechartViewSetMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    xsm_event_serializers = {
        "PAY": event_serializer(
            "PAY", {"amount": serializers.IntegerField(min_value=0)}
        )
    }


class ApprovalSerializer(serializers.ModelSerializer):
    statechart = StatechartSerializerField()

    class Meta:
        model = Approval
        fields = ["id", "title", "statechart"]


class ApprovalViewSet(
    StatechartViewSetMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Approval.objects.all()
    serializer_class = ApprovalSerializer
    permission_classes = [IsAuthenticated]


router = DefaultRouter()
router.register("orders", OrderViewSet)
router.register("approvals", ApprovalViewSet)

urlpatterns = [path("", include(router.urls))]

try:  # the schema endpoint when drf-spectacular is installed
    from drf_spectacular.views import SpectacularAPIView

    urlpatterns.append(
        path("schema/", SpectacularAPIView.as_view(), name="schema")
    )
except ImportError:  # pragma: no cover
    pass
