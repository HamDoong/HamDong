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

SERVICE_NAME = "identity-service"
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
    "apps.identity",
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
    "EXCEPTION_HANDLER": "apps.identity.infrastructure.exception_handlers.api_exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "identity-service API",
    "VERSION": SERVICE_VERSION,
}

CORS_ALLOW_ALL_ORIGINS = True

# Use the custom user model defined in apps.identity.domain.models *
AUTH_USER_MODEL = "identity.User"

# JWT Configuration
JWT_ALGORITHM = env("JWT_ALGORITHM", default="RS256")
JWT_ISSUER = env("JWT_ISSUER", default="hamdong.identity-service")
JWT_AUDIENCE = env("JWT_AUDIENCE", default="hamdong.services")
JWT_ACCESS_TOKEN_LIFETIME_SECONDS = env(
    "JWT_ACCESS_TOKEN_LIFETIME_SECONDS", default=900, cast=int
)
JWT_REFRESH_TOKEN_LIFETIME_SECONDS = env(
    "JWT_REFRESH_TOKEN_LIFETIME_SECONDS", default=604800, cast=int
)
JWT_PRIVATE_KEY_PATH = env("JWT_PRIVATE_KEY_PATH", default="/app/keys/private.pem")
JWT_PUBLIC_KEY_PATH = env("JWT_PUBLIC_KEY_PATH", default="/app/keys/public.pem")

# OTP Configuration
OTP_LENGTH = env("OTP_LENGTH", default=6, cast=int)
OTP_TTL_SECONDS = env("OTP_TTL_SECONDS", default=120, cast=int)
OTP_RESEND_COOLDOWN_SECONDS = env("OTP_RESEND_COOLDOWN_SECONDS", default=60, cast=int)
OTP_MAX_VERIFY_ATTEMPTS = env("OTP_MAX_VERIFY_ATTEMPTS", default=5, cast=int)
OTP_MAX_REQUESTS_PER_WINDOW = env("OTP_MAX_REQUESTS_PER_WINDOW", default=3, cast=int)
OTP_RATE_LIMIT_WINDOW_SECONDS = env(
    "OTP_RATE_LIMIT_WINDOW_SECONDS", default=600, cast=int
)
OTP_DEBUG_RETURN_CODE = env.bool("OTP_DEBUG_RETURN_CODE", default=True)

# RabbitMQ Configuration
IDENTITY_RABBITMQ_EXCHANGE = env(
    "IDENTITY_RABBITMQ_EXCHANGE", default="hamdong.identity"
)

# Redis Configuration
REDIS_HOST = env("REDIS_HOST", default="localhost")
REDIS_PORT = env("REDIS_PORT", default=6379, cast=int)
REDIS_DB = env("REDIS_DB", default=0, cast=int)

# RabbitMQ Configuration
RABBITMQ_HOST = env("RABBITMQ_HOST", default="localhost")
RABBITMQ_PORT = env("RABBITMQ_PORT", default=5672, cast=int)
RABBITMQ_DEFAULT_USER = env("RABBITMQ_DEFAULT_USER", default="guest")
RABBITMQ_DEFAULT_PASS = env("RABBITMQ_DEFAULT_PASS", default="guest")

EVENT_OUTBOX_BATCH_SIZE = env.int("EVENT_OUTBOX_BATCH_SIZE", default=50)
EVENT_OUTBOX_POLL_INTERVAL_SECONDS = env.int("EVENT_OUTBOX_POLL_INTERVAL_SECONDS", default=5)
EVENT_MAX_RETRY_COUNT = env.int("EVENT_MAX_RETRY_COUNT", default=5)
EVENT_DLQ_SUFFIX = env("EVENT_DLQ_SUFFIX", default=".dlq")
EVENT_RETRY_DELAY_SECONDS = env("EVENT_RETRY_DELAY_SECONDS", default="10,30,60")
