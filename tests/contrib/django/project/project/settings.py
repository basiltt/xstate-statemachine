# tests/contrib/django/project/project/settings.py
"""Settings of the [django] / [drf] / [channels] test project.

SQLite in a per-process temp file by default (threads need a real file:
the concurrency tests open one connection per thread). Set
``DATABASE_URL=postgres://user:pass@host:5432/name`` to run the same
suite on Postgres (``select_for_update`` is then a real row lock).
"""

from __future__ import annotations

import importlib.util
import os
import tempfile
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = "xsm-test-project-not-a-secret"  # noqa: S105 - test only
DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
ROOT_URLCONF = "project.urls"


def _has(mod: str) -> bool:
    return importlib.util.find_spec(mod) is not None


HAS_DRF = _has("rest_framework")
HAS_SPECTACULAR = HAS_DRF and _has("drf_spectacular")
HAS_CHANNELS = _has("channels")
HAS_FSM = _has("django_fsm") and (BASE_DIR / "legacy").is_dir()

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "xstate_statemachine.contrib.django",
    "shop",
]
if HAS_DRF:
    INSTALLED_APPS.append("rest_framework")
if HAS_SPECTACULAR:
    INSTALLED_APPS.append("drf_spectacular")
if HAS_CHANNELS:
    INSTALLED_APPS.append("channels")
if HAS_FSM:
    INSTALLED_APPS.append("legacy")

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]


def _database() -> dict:
    url = os.environ.get("DATABASE_URL")
    if url:
        u = urlparse(url)
        if u.scheme.startswith("postgres"):
            return {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": u.path.lstrip("/"),
                "USER": u.username or "",
                "PASSWORD": u.password or "",
                "HOST": u.hostname or "",
                "PORT": str(u.port or ""),
            }
    tmp = Path(tempfile.gettempdir())
    pid = os.getpid()
    return {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(tmp / f"xsm_django_{pid}.sqlite3"),
        "OPTIONS": {"timeout": 60},
        "TEST": {"NAME": str(tmp / f"xsm_django_test_{pid}.sqlite3")},
    }


DATABASES = {"default": _database()}
if DATABASES["default"]["ENGINE"].endswith("sqlite3"):
    # 📝 #361 M3: a second alias proves the inbox follows the row's DB.
    _other = dict(DATABASES["default"])
    _other["NAME"] = _other["NAME"].replace(".sqlite3", "_other.sqlite3")
    _other["TEST"] = {
        "NAME": _other["TEST"]["NAME"].replace(".sqlite3", "_other.sqlite3")
    }
    DATABASES["other"] = _other

STATIC_URL = "/static/"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_SCHEMA_CLASS": (
        "drf_spectacular.openapi.AutoSchema"
        if HAS_SPECTACULAR
        else "rest_framework.schemas.openapi.AutoSchema"
    ),
}
SPECTACULAR_SETTINGS = {"TITLE": "xsm test project", "VERSION": "1.0.0"}

ASGI_APPLICATION = "project.asgi.application"
CHANNEL_LAYERS = {
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
}
