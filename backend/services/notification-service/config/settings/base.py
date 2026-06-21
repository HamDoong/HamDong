import os
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parents[2]

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / ".env")

APP_ENV = env("APP_ENV", default="local")

POSTGRES_DB = os.environ.get("POSTGRES_DB") or os.environ.get("DJANGO_DB_NAME", "notification_db")
POSTGRES_USER = os.environ.get("POSTGRES_USER") or os.environ.get("DJANGO_DB_USER", "postgres")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD") or os.environ.get("DJANGO_DB_PASSWORD", "postgres")
POSTGRES_HOST = os.getenv("POSTGRES_HOST") or os.getenv("DJANGO_DB_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT") or os.getenv("DJANGO_DB_PORT", "5432")

RABBITMQ_HOST = env("RABBITMQ_HOST", default="rabbitmq")
RABBITMQ_PORT = env("RABBITMQ_PORT", default=5672, cast=int)
RABBITMQ_DEFAULT_USER = env("RABBITMQ_DEFAULT_USER", default="guest")
RABBITMQ_DEFAULT_PASS = env("RABBITMQ_DEFAULT_PASS", default="guest")

SERVICE_NAME = "notification-service"
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
    "apps.notifications",
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
}

IDENTITY_JWKS_URL = env(
    "IDENTITY_JWKS_URL",
    default="http://identity-service:8000/api/v1/auth/.well-known/jwks.json",
)
IDENTITY_PUBLIC_KEY_PATH = env(
    "IDENTITY_PUBLIC_KEY_PATH",
    default="/app/keys/public.pem",
)
JWT_ISSUER = env("JWT_ISSUER", default="hamdong.identity-service")
JWT_AUDIENCE = env("JWT_AUDIENCE", default="hamdong.services")
JWT_ALGORITHM = env("JWT_ALGORITHM", default="RS256")

SPECTACULAR_SETTINGS = {
    "TITLE": "notification-service API",
    "VERSION": SERVICE_VERSION,
    "APPEND_COMPONENTS": {
        "securitySchemes": {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        }
    },
    "SECURITY": [{"BearerAuth": []}],
}

IDENTITY_RABBITMQ_EXCHANGE = env("IDENTITY_RABBITMQ_EXCHANGE", default="hamdong.identity")
NOTIFICATION_RABBITMQ_EXCHANGE = env("NOTIFICATION_RABBITMQ_EXCHANGE", default="hamdong.notification")
IDENTITY_OTP_QUEUE = env("IDENTITY_OTP_QUEUE", default="notification.identity.otp.requested")
IDENTITY_OTP_DLX = env("IDENTITY_OTP_DLX", default="notification.identity.otp.requested.dlx")
IDENTITY_OTP_DLQ = env("IDENTITY_OTP_DLQ", default="notification.identity.otp.requested.dlq")

EMAIL_PROVIDER = env("EMAIL_PROVIDER", default="fake")
EMAIL_TEMPLATE_OTP_LOGIN = env("EMAIL_TEMPLATE_OTP_LOGIN", default="OTP_LOGIN")
EMAIL_TEMPLATE_SETTLEMENT_REMINDER = env("EMAIL_TEMPLATE_SETTLEMENT_REMINDER", default="SETTLEMENT_REMINDER")
EMAIL_TEMPLATE_PAYMENT_REMINDER = env("EMAIL_TEMPLATE_PAYMENT_REMINDER", default="PAYMENT_REMINDER")
EMAIL_TEMPLATE_SETTLEMENT_CONFIRMATION_REMINDER = env(
    "EMAIL_TEMPLATE_SETTLEMENT_CONFIRMATION_REMINDER",
    default="SETTLEMENT_CONFIRMATION_REMINDER",
)
EMAIL_TEMPLATE_PLAN_ITEM_REMINDER = env("EMAIL_TEMPLATE_PLAN_ITEM_REMINDER", default="PLAN_ITEM_REMINDER")
EMAIL_TEMPLATE_DEBT_REMINDER = env("EMAIL_TEMPLATE_DEBT_REMINDER", default="DEBT_REMINDER")
EMAIL_CIRCUIT_FAIL_MAX = env("EMAIL_CIRCUIT_FAIL_MAX", default=5, cast=int)
EMAIL_CIRCUIT_RESET_TIMEOUT_SECONDS = env("EMAIL_CIRCUIT_RESET_TIMEOUT_SECONDS", default=60, cast=int)
EMAIL_OTP_MAX_RETRIES = env("EMAIL_OTP_MAX_RETRIES", default=2, cast=int)
EMAIL_OTP_RETRY_DELAYS_SECONDS = env("EMAIL_OTP_RETRY_DELAYS_SECONDS", default="10,30")

EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = env("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_TIMEOUT_SECONDS = env("EMAIL_TIMEOUT_SECONDS", default=10, cast=int)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="HamDong <no-reply@example.com>")
SERVER_EMAIL = env("SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)

SETTLEMENT_RABBITMQ_EXCHANGE = env("SETTLEMENT_RABBITMQ_EXCHANGE", default="hamdong.settlement")
SETTLEMENT_REMINDER_QUEUE = env("SETTLEMENT_REMINDER_QUEUE", default="notification.settlement.reminders")
SETTLEMENT_REMINDER_DLX = env("SETTLEMENT_REMINDER_DLX", default="notification.settlement.reminders.dlx")
SETTLEMENT_REMINDER_DLQ = env("SETTLEMENT_REMINDER_DLQ", default="notification.settlement.reminders.dlq")

CORS_ALLOW_ALL_ORIGINS = True

EVENT_OUTBOX_BATCH_SIZE = env.int("EVENT_OUTBOX_BATCH_SIZE", default=50)
EVENT_OUTBOX_POLL_INTERVAL_SECONDS = env.int("EVENT_OUTBOX_POLL_INTERVAL_SECONDS", default=5)
EVENT_MAX_RETRY_COUNT = env.int("EVENT_MAX_RETRY_COUNT", default=5)
EVENT_DLQ_SUFFIX = env("EVENT_DLQ_SUFFIX", default=".dlq")
EVENT_RETRY_DELAY_SECONDS = env("EVENT_RETRY_DELAY_SECONDS", default="10,30,60")
REMINDER_ENABLED = env.bool("REMINDER_ENABLED", default=True)
NOTIFICATION_REMINDER_QUEUE = env("NOTIFICATION_REMINDER_QUEUE", default="notification.reminders")
SETTLEMENT_REMINDER_EXCHANGE = env("SETTLEMENT_REMINDER_EXCHANGE", default="hamdong.settlement")
