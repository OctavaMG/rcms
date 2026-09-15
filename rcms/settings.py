"""
Django settings for the rcms project (Architecture v3.1, Track B).

Driven by environment variables (see .env.example) so the same codebase
runs unchanged from a laptop, from `docker compose`, or from CI. No
values are hardcoded here beyond defaults meant only for a first local
smoke test.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default=False):
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


# --- Core -------------------------------------------------------------

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-CHANGE-ME-in-.env-before-any-real-deployment",
)
DEBUG = env_bool("DJANGO_DEBUG", default=True)

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get(
        "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1"
    ).split(",")
    if h.strip()
]

# Behind Caddy, TLS terminates at the proxy. Without this Django sees a
# plain-HTTP request, builds http:// origins from the Host header, and
# rejects the browser's https:// Origin on every POST -- CSRF 403 on
# admin login. Only safe because the proxy is the intended path in; a
# client reaching :8000 directly on the LAN could spoof the header.
if env_bool("DJANGO_TRUST_PROXY_TLS", default=False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Explicit trusted origins, scheme included. Belt-and-braces alongside
# the above, and required if a hostname ever fronts this that is not the
# one in the Host header.
CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if o.strip()
]


# --- Applications -------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "rcms.urls"

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
            ],
        },
    },
]

WSGI_APPLICATION = "rcms.wsgi.application"


# --- Database -------------------------------------------------------------
# Defaults to Postgres per Architecture v3.1 Section 6B. Falls back to
# sqlite only if DB_ENGINE is explicitly set to sqlite3 -- useful for a
# quick local `manage.py check`/test run without a real Postgres server,
# never for anything that touches real data.

if os.environ.get("DB_ENGINE", "postgresql") == "sqlite3":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "rcms"),
            "USER": os.environ.get("POSTGRES_USER", "rcms"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "HOST": os.environ.get("DATABASE_HOST", "db"),
            "PORT": os.environ.get("DATABASE_PORT", "5432"),
        }
    }


# --- Django REST Framework ----------------------------------------------
# Token auth: n8n (and any future caller) authenticates via
# /api-token-auth/ once, then sends `Authorization: Token <key>` on every
# call to /api/jobs/. This is the "token API" called for in Open Item 2.

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}


# --- Password validation -------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# --- Internationalization -------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# --- Static files ----------------------------------------------------------

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
