# examples/integrations/django_approvals/config/urls.py
from django.contrib import admin
from django.urls import include, path

from approvals.views import status

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("approvals.api")),
    path("expenses/<int:pk>/", status, name="expense-status"),
]
