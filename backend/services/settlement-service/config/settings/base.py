from pathlib import Path
import os

import environ

BASE_DIR = Path(__file__).resolve().parents[2]

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / ".env")

POSTGRES_DB = os.environ["POSTGRES_DB"]
POSTGRES_USER = os.environ["POSTGRES_USER"]
POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

SERVICE_NAME = "settlement-service"
SERVICE_VERSION = "0.1.0"

IDENTITY_RABBITMQ_EXCHANGE = env("IDENTITY_RABBITMQ_EXCHANGE", default="hamdong.identity")
GROUP_RABBITMQ_EXCHANGE = env("GROUP_RABBITMQ_EXCHANGE", default="hamdong.group")
EXPENSE_RABBITMQ_EXCHANGE = env("EXPENSE_RABBITMQ_EXCHANGE", default="hamdong.expense")
SETTLEMENT_RABBITMQ_EXCHANGE = env("SETTLEMENT_RABBITMQ_EXCHANGE", default="hamdong.settlement")
SETTLEMENT_IDENTITY_QUEUE = env("SETTLEMENT_IDENTITY_QUEUE", default="settlement.identity.user_events")
SETTLEMENT_GROUP_QUEUE = env("SETTLEMENT_GROUP_QUEUE", default="settlement.group.events")
SETTLEMENT_EXPENSE_QUEUE = env("SETTLEMENT_EXPENSE_QUEUE", default="settlement.expense.events")
IDENTITY_JWKS_URL = env("IDENTITY_JWKS_URL", default="http://identity-service:8000/api/v1/auth/.well-known/jwks.json")
IDENTITY_PUBLIC_KEY_PATH = env("IDENTITY_PUBLIC_KEY_PATH", default="/app/keys/public.pem")
JWT_ISSUER = env("JWT_ISSUER", default="hamdong.identity-service")
JWT_AUDIENCE = env("JWT_AUDIENCE", default="hamdong.services")
JWT_ALGORITHM = env("JWT_ALGORITHM", default="RS256")
DEFAULT_CURRENCY = env("DEFAULT_CURRENCY", default="IRR")
MAX_SETTLEMENT_AMOUNT_MINOR = env.int("MAX_SETTLEMENT_AMOUNT_MINOR", default=100000000000)

SECRET_KEY = env("SECRET_KEY", default="change-me")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "apps.settlements",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": POSTGRES_DB,
        "USER": POSTGRES_USER,
        "PASSWORD": POSTGRES_PASSWORD,
        "HOST": POSTGRES_HOST,
        "PORT": POSTGRES_PORT,
        "TEST": {"NAME": f"test_{POSTGRES_DB}"},
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "settlement-service API",
    "VERSION": SERVICE_VERSION,
}

CORS_ALLOW_ALL_ORIGINS = True
