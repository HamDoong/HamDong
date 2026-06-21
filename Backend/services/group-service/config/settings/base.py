from pathlib import Path
import os

import environ

BASE_DIR = Path(__file__).resolve().parents[2]

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / ".env")

POSTGRES_DB = os.environ.get("POSTGRES_DB") or os.environ.get("DJANGO_DB_NAME", "group_db")
POSTGRES_USER = os.environ.get("POSTGRES_USER") or os.environ.get("DJANGO_DB_USER", "postgres")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD") or os.environ.get("DJANGO_DB_PASSWORD", "postgres")
POSTGRES_HOST = os.getenv("POSTGRES_HOST") or os.getenv("DJANGO_DB_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT") or os.getenv("DJANGO_DB_PORT", "5432")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_DEFAULT_USER = os.getenv("RABBITMQ_DEFAULT_USER", "guest")
RABBITMQ_DEFAULT_PASS = os.getenv("RABBITMQ_DEFAULT_PASS", "guest")

SERVICE_NAME = "group-service"
SERVICE_VERSION = "0.1.0"

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
    "apps.groups",
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
        "ENGINE": os.getenv("DJANGO_DB_ENGINE", "django.db.backends.postgresql"),
        "NAME": POSTGRES_DB,
        "USER": POSTGRES_USER,
        "PASSWORD": POSTGRES_PASSWORD,
        "HOST": POSTGRES_HOST,
        "PORT": POSTGRES_PORT,
        "TEST": {"NAME": os.environ.get("DJANGO_TEST_DB_NAME", f"test_{POSTGRES_DB}")},
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
    "EXCEPTION_HANDLER": "apps.groups.infrastructure.exception_handlers.api_exception_handler",
}


IDENTITY_JWKS_URL = env(
    "IDENTITY_JWKS_URL",
    default="http://identity-service:8000/api/v1/auth/.well-known/jwks.json",
)
IDENTITY_PUBLIC_KEY_PATH = env(
    "IDENTITY_PUBLIC_KEY_PATH", default="/app/keys/public.pem"
)
JWT_ISSUER = env("JWT_ISSUER", default="hamdong.identity-service")
JWT_AUDIENCE = env("JWT_AUDIENCE", default="hamdong.services")
JWT_ALGORITHM = env("JWT_ALGORITHM", default="RS256")

SPECTACULAR_SETTINGS = {
    "TITLE": "group-service API",
    "VERSION": SERVICE_VERSION,
}

CORS_ALLOW_ALL_ORIGINS = True

GROUP_RABBITMQ_EXCHANGE = os.getenv("GROUP_RABBITMQ_EXCHANGE", "hamdong.group")
IDENTITY_RABBITMQ_EXCHANGE = os.getenv("IDENTITY_RABBITMQ_EXCHANGE", "hamdong.identity")
EVENT_OUTBOX_BATCH_SIZE = int(os.getenv("EVENT_OUTBOX_BATCH_SIZE", "50"))
EVENT_OUTBOX_POLL_INTERVAL_SECONDS = int(os.getenv("EVENT_OUTBOX_POLL_INTERVAL_SECONDS", "5"))
EVENT_MAX_RETRY_COUNT = int(os.getenv("EVENT_MAX_RETRY_COUNT", "5"))
EVENT_DLQ_SUFFIX = os.getenv("EVENT_DLQ_SUFFIX", ".dlq")
EVENT_RETRY_DELAY_SECONDS = os.getenv("EVENT_RETRY_DELAY_SECONDS", "10,30,60")
