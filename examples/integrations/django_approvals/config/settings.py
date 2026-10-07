# examples/integrations/django_approvals/config/settings.py
"""Settings of the django_approvals example (SQLite next to this file)."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = "example-only-change-me"  # noqa: S105 - example
DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]
ROOT_URLCONF = "config.urls"
ASGI_APPLICATION = "config.asgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True

INSTALLED_APPS = [
    "daphne",  # `manage.py runserver` serves HTTP + WebSocket
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "channels",
    "xstate_statemachine.contrib.django",
    "approvals",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
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
    """SQLite by default; ``DATABASE_URL=postgresql://u:p@host:5432/db``
    switches to Postgres (the battle tests run both)."""
    import os
    from urllib.parse import urlparse

    url = os.environ.get("DATABASE_URL", "")
    if url.startswith("postgres"):
        u = urlparse(url)
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": u.path.lstrip("/"),
            "USER": u.username or "",
            "PASSWORD": u.password or "",
            "HOST": u.hostname or "",
            "PORT": str(u.port or ""),
        }
    name = os.environ.get("APPROVALS_DB", str(BASE_DIR / "approvals.sqlite3"))
    return {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": name,
        # 📝 #280 battle: the test database is a FILE, not Django's default
        #    shared-cache ":memory:" -- threads on a shared-cache memory
        #    DB hit "database table is locked" instead of waiting on
        #    busy_timeout, which no production deployment ever sees.
        "OPTIONS": {"timeout": 60},
        "TEST": {"NAME": f"{name}.test"},
    }


DATABASES = {"default": _database()}

STATIC_URL = "/static/"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}
SPECTACULAR_SETTINGS = {"TITLE": "Expense approvals", "VERSION": "1.0.0"}
CHANNEL_LAYERS = {
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
}
