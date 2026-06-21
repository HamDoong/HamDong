from pathlib import Path
import os

import environ

BASE_DIR = Path(__file__).resolve().parents[2]

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / ".env")

POSTGRES_DB = os.environ.get("POSTGRES_DB") or os.environ.get("DJANGO_DB_NAME", "media_db")
POSTGRES_USER = os.environ.get("POSTGRES_USER") or os.environ.get("DJANGO_DB_USER", "postgres")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD") or os.environ.get("DJANGO_DB_PASSWORD", "postgres")
POSTGRES_HOST = os.getenv("POSTGRES_HOST") or os.getenv("DJANGO_DB_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT") or os.getenv("DJANGO_DB_PORT", "5432")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_DEFAULT_USER = os.getenv("RABBITMQ_DEFAULT_USER", "guest")
RABBITMQ_DEFAULT_PASS = os.getenv("RABBITMQ_DEFAULT_PASS", "guest")

SERVICE_NAME = "media-service"
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
    "apps.media_files.apps.MediaFilesConfig",
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
    "EXCEPTION_HANDLER": "apps.media_files.infrastructure.exception_handlers.api_exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "media-service API",
    "VERSION": SERVICE_VERSION,
    "DESCRIPTION": "Secure receipt upload and media management for HamDong.",
    "COMPONENT_SPLIT_REQUEST": True,
}

CORS_ALLOW_ALL_ORIGINS = True

MEDIA_ROOT = os.getenv("MEDIA_ROOT", "/media/uploads")
MEDIA_URL = "/media/uploads/"

MEDIA_STORAGE_PROVIDER = os.getenv("MEDIA_STORAGE_PROVIDER", "local")
MEDIA_MAX_FILE_SIZE_BYTES = int(os.getenv("MEDIA_MAX_FILE_SIZE_BYTES", "5242880"))
MEDIA_ALLOWED_EXTENSIONS = [
    ext.strip().lower()
    for ext in os.getenv("MEDIA_ALLOWED_EXTENSIONS", "jpg,jpeg,png,webp,pdf").split(",")
    if ext.strip()
]
MEDIA_ALLOWED_CONTENT_TYPES = [
    content_type.strip().lower()
    for content_type in os.getenv(
        "MEDIA_ALLOWED_CONTENT_TYPES",
        "image/jpeg,image/png,image/webp,application/pdf",
    ).split(",")
    if content_type.strip()
]
MEDIA_SIGNED_URL_EXPIRES_SECONDS = int(os.getenv("MEDIA_SIGNED_URL_EXPIRES_SECONDS", "300"))

EXPENSE_RABBITMQ_EXCHANGE = os.getenv("EXPENSE_RABBITMQ_EXCHANGE", "hamdong.expense")
MEDIA_RABBITMQ_EXCHANGE = os.getenv("MEDIA_RABBITMQ_EXCHANGE", "hamdong.media")
IDENTITY_RABBITMQ_EXCHANGE = os.getenv("IDENTITY_RABBITMQ_EXCHANGE", "hamdong.identity")
GROUP_RABBITMQ_EXCHANGE = os.getenv("GROUP_RABBITMQ_EXCHANGE", "hamdong.group")
MEDIA_IDENTITY_QUEUE = os.getenv("MEDIA_IDENTITY_QUEUE", "media.identity.user_events")
MEDIA_GROUP_QUEUE = os.getenv("MEDIA_GROUP_QUEUE", "media.group.events")

IDENTITY_JWKS_URL = os.getenv("IDENTITY_JWKS_URL", "")
IDENTITY_PUBLIC_KEY_PATH = os.getenv("IDENTITY_PUBLIC_KEY_PATH", "")
JWT_ISSUER = os.getenv("JWT_ISSUER", "hamdong.identity-service")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "hamdong.services")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "RS256")

EVENT_OUTBOX_BATCH_SIZE = int(os.getenv("EVENT_OUTBOX_BATCH_SIZE", "50"))
EVENT_OUTBOX_POLL_INTERVAL_SECONDS = int(os.getenv("EVENT_OUTBOX_POLL_INTERVAL_SECONDS", "5"))
EVENT_MAX_RETRY_COUNT = int(os.getenv("EVENT_MAX_RETRY_COUNT", "5"))
EVENT_DLQ_SUFFIX = os.getenv("EVENT_DLQ_SUFFIX", ".dlq")
EVENT_RETRY_DELAY_SECONDS = os.getenv("EVENT_RETRY_DELAY_SECONDS", "10,30,60")
NOTIFICATION_REMINDER_QUEUE = os.getenv("NOTIFICATION_REMINDER_QUEUE", "notification.reminders")
