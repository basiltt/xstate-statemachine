# src/xstate_statemachine/contrib/django/apps.py
"""The Django app config (label ``xsm_django``)."""

from __future__ import annotations

from django.apps import AppConfig


class XsmDjangoConfig(AppConfig):
    """``xstate_statemachine.contrib.django`` as an installed app.

    The label is ``xsm_django`` so its tables (``xsm_django_*``) cannot
    collide with an application's own ``django`` label.
    """

    name = "xstate_statemachine.contrib.django"
    label = "xsm_django"
    verbose_name = "Statecharts"
    default_auto_field = "django.db.models.BigAutoField"
