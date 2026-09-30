# tests/contrib/django/project/project/urls.py
"""URLs of the test project; the DRF router joins when DRF is present."""

from __future__ import annotations

from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [path("admin/", admin.site.urls)]

if settings.HAS_DRF and (settings.BASE_DIR / "shop" / "api.py").is_file():
    urlpatterns.append(path("api/", include("shop.api")))
