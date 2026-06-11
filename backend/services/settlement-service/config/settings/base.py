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
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_DEFAULT_USER = os.getenv("RABBITMQ_DEFAULT_USER", "guest")
RABBITMQ_DEFAULT_PASS = os.getenv("RABBITMQ_DEFAULT_PASS", "guest")

SERVICE_NAME = "settlement-service"
SERVICE_VERSION = "0.1.0"

IDENTITY_RABBITMQ_EXCHANGE = env(
    "IDENTITY_RABBITMQ_EXCHANGE", default="hamdong.identity"
)
GROUP_RABBITMQ_EXCHANGE = env("GROUP_RABBITMQ_EXCHANGE", default="hamdong.group")
EXPENSE_RABBITMQ_EXCHANGE = env("EXPENSE_RABBITMQ_EXCHANGE", default="hamdong.expense")
SETTLEMENT_RABBITMQ_EXCHANGE = env(
    "SETTLEMENT_RABBITMQ_EXCHANGE", default="hamdong.settlement"
)
SETTLEMENT_IDENTITY_QUEUE = env(
    "SETTLEMENT_IDENTITY_QUEUE", default="settlement.identity.user_events"
)
SETTLEMENT_GROUP_QUEUE = env(
    "SETTLEMENT_GROUP_QUEUE", default="settlement.group.events"
)
SETTLEMENT_EXPENSE_QUEUE = env(
    "SETTLEMENT_EXPENSE_QUEUE", default="settlement.expense.events"
)
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
DEFAULT_CURRENCY = env("DEFAULT_CURRENCY", default="IRR")
MAX_SETTLEMENT_AMOUNT_MINOR = env.int(
    "MAX_SETTLEMENT_AMOUNT_MINOR", default=100000000000
)
EVENT_OUTBOX_BATCH_SIZE = env.int("EVENT_OUTBOX_BATCH_SIZE", default=50)
EVENT_MAX_RETRY_COUNT = env.int("EVENT_MAX_RETRY_COUNT", default=5)
EVENT_RETRY_DELAY_SECONDS = env("EVENT_RETRY_DELAY_SECONDS", default="10,30,60")
EVENT_DLQ_SUFFIX = env("EVENT_DLQ_SUFFIX", default=".dlq")
REMINDER_ENABLED = env.bool("REMINDER_ENABLED", default=True)
REMINDER_MIN_INTERVAL_HOURS = env.int("REMINDER_MIN_INTERVAL_HOURS", default=24)
SETTLEMENT_REMINDER_QUEUE = env(
    "SETTLEMENT_REMINDER_QUEUE", default="notification.settlement.reminders"
)
SETTLEMENT_REMINDER_DLX = env(
    "SETTLEMENT_REMINDER_DLX", default="notification.settlement.reminders.dlx"
)
SETTLEMENT_REMINDER_DLQ = env(
    "SETTLEMENT_REMINDER_DLQ", default="notification.settlement.reminders.dlq"
)
SMS_TEMPLATE_SETTLEMENT_REMINDER = env(
    "SMS_TEMPLATE_SETTLEMENT_REMINDER", default="SETTLEMENT_REMINDER"
)

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
    "EXCEPTION_HANDLER": "apps.settlements.infrastructure.exception_handlers.api_exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "settlement-service API",
    "VERSION": SERVICE_VERSION,
}

CORS_ALLOW_ALL_ORIGINS = True

EVENT_OUTBOX_POLL_INTERVAL_SECONDS = env.int("EVENT_OUTBOX_POLL_INTERVAL_SECONDS", default=5)
EVENT_RETRY_DELAY_SECONDS = env("EVENT_RETRY_DELAY_SECONDS", default="10,30,60")
REMINDER_SCHEDULER_INTERVAL_SECONDS = env.int("REMINDER_SCHEDULER_INTERVAL_SECONDS", default=3600)
PAYMENT_REMINDER_MIN_AMOUNT_MINOR = env.int("PAYMENT_REMINDER_MIN_AMOUNT_MINOR", default=1000)
PENDING_SETTLEMENT_REMINDER_AFTER_HOURS = env.int("PENDING_SETTLEMENT_REMINDER_AFTER_HOURS", default=24)
PLAN_ITEM_REMINDER_AFTER_HOURS = env.int("PLAN_ITEM_REMINDER_AFTER_HOURS", default=24)
NOTIFICATION_REMINDER_QUEUE = env("NOTIFICATION_REMINDER_QUEUE", default="notification.reminders")
SETTLEMENT_REMINDER_EXCHANGE = env("SETTLEMENT_REMINDER_EXCHANGE", default="hamdong.settlement")
