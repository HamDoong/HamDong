import os
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parents[2]

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / ".env")

APP_ENV = env("APP_ENV", default="local")

POSTGRES_DB = os.environ["POSTGRES_DB"]
POSTGRES_USER = os.environ["POSTGRES_USER"]
POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

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
        "Backend": "django.template.Backends.django.DjangoTemplates",
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
        "ENGINE": "django.db.Backends.postgresql",
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
    "TITLE": "notification-service API",
    "VERSION": SERVICE_VERSION,
}

IDENTITY_RABBITMQ_EXCHANGE = env(
    "IDENTITY_RABBITMQ_EXCHANGE", default="hamdong.identity"
)
NOTIFICATION_RABBITMQ_EXCHANGE = env(
    "NOTIFICATION_RABBITMQ_EXCHANGE", default="hamdong.notification"
)
IDENTITY_OTP_QUEUE = env(
    "IDENTITY_OTP_QUEUE", default="notification.identity.otp.requested"
)
IDENTITY_OTP_DLX = env(
    "IDENTITY_OTP_DLX", default="notification.identity.otp.requested.dlx"
)
IDENTITY_OTP_DLQ = env(
    "IDENTITY_OTP_DLQ", default="notification.identity.otp.requested.dlq"
)

SMS_PROVIDER = env("SMS_PROVIDER", default="fake")
SMS_API_KEY = env("SMS_API_KEY", default="")
SMS_SENDER = env("SMS_SENDER", default="")
SMS_TEMPLATE_OTP_LOGIN = env("SMS_TEMPLATE_OTP_LOGIN", default="OTP_LOGIN")
SMS_TEMPLATE_SETTLEMENT_REMINDER = env(
    "SMS_TEMPLATE_SETTLEMENT_REMINDER", default="SETTLEMENT_REMINDER"
)

SMS_CIRCUIT_FAIL_MAX = env("SMS_CIRCUIT_FAIL_MAX", default=5, cast=int)
SMS_CIRCUIT_RESET_TIMEOUT_SECONDS = env(
    "SMS_CIRCUIT_RESET_TIMEOUT_SECONDS", default=60, cast=int
)

SMS_OTP_MAX_RETRIES = env("SMS_OTP_MAX_RETRIES", default=2, cast=int)
SMS_OTP_RETRY_DELAYS_SECONDS = env("SMS_OTP_RETRY_DELAYS_SECONDS", default="10,30")

SETTLEMENT_RABBITMQ_EXCHANGE = env(
    "SETTLEMENT_RABBITMQ_EXCHANGE", default="hamdong.settlement"
)
SETTLEMENT_REMINDER_QUEUE = env(
    "SETTLEMENT_REMINDER_QUEUE", default="notification.settlement.reminders"
)
SETTLEMENT_REMINDER_DLX = env(
    "SETTLEMENT_REMINDER_DLX", default="notification.settlement.reminders.dlx"
)
SETTLEMENT_REMINDER_DLQ = env(
    "SETTLEMENT_REMINDER_DLQ", default="notification.settlement.reminders.dlq"
)

CORS_ALLOW_ALL_ORIGINS = True

EVENT_OUTBOX_BATCH_SIZE = env.int("EVENT_OUTBOX_BATCH_SIZE", default=50)
EVENT_OUTBOX_POLL_INTERVAL_SECONDS = env.int("EVENT_OUTBOX_POLL_INTERVAL_SECONDS", default=5)
EVENT_MAX_RETRY_COUNT = env.int("EVENT_MAX_RETRY_COUNT", default=5)
EVENT_DLQ_SUFFIX = env("EVENT_DLQ_SUFFIX", default=".dlq")
EVENT_RETRY_DELAY_SECONDS = env("EVENT_RETRY_DELAY_SECONDS", default="10,30,60")
REMINDER_ENABLED = env.bool("REMINDER_ENABLED", default=True)
NOTIFICATION_REMINDER_QUEUE = env("NOTIFICATION_REMINDER_QUEUE", default="notification.reminders")
SETTLEMENT_REMINDER_EXCHANGE = env("SETTLEMENT_REMINDER_EXCHANGE", default="hamdong.settlement")
