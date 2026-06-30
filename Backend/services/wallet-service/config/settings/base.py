from pathlib import Path
import os

import environ

BASE_DIR = Path(__file__).resolve().parents[2]

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / ".env")

POSTGRES_DB = os.environ.get("POSTGRES_DB") or os.environ.get("DJANGO_DB_NAME", "wallet_db")
POSTGRES_USER = os.environ.get("POSTGRES_USER") or os.environ.get("DJANGO_DB_USER", "postgres")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD") or os.environ.get("DJANGO_DB_PASSWORD", "postgres")
POSTGRES_HOST = os.getenv("POSTGRES_HOST") or os.getenv("DJANGO_DB_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT") or os.getenv("DJANGO_DB_PORT", "5432")

SERVICE_NAME = "wallet-service"
SERVICE_VERSION = "0.1.0"

IDENTITY_RABBITMQ_EXCHANGE = env("IDENTITY_RABBITMQ_EXCHANGE", default="hamdong.identity")
SETTLEMENT_RABBITMQ_EXCHANGE = env("SETTLEMENT_RABBITMQ_EXCHANGE", default="hamdong.settlement")
WALLET_RABBITMQ_EXCHANGE = env("WALLET_RABBITMQ_EXCHANGE", default="hamdong.wallet")

WALLET_IDENTITY_QUEUE = env("WALLET_IDENTITY_QUEUE", default="wallet.identity.user_events")
WALLET_SETTLEMENT_QUEUE = env("WALLET_SETTLEMENT_QUEUE", default="wallet.settlement.events")

RABBITMQ_HOST = env("RABBITMQ_HOST", default="localhost")
RABBITMQ_PORT = env.int("RABBITMQ_PORT", default=5672)
RABBITMQ_DEFAULT_USER = env("RABBITMQ_DEFAULT_USER", default="guest")
RABBITMQ_DEFAULT_PASS = env("RABBITMQ_DEFAULT_PASS", default="guest")

IDENTITY_JWKS_URL = env(
    "IDENTITY_JWKS_URL",
    default="http://identity-service:8000/api/v1/auth/.well-known/jwks.json",
)
IDENTITY_PUBLIC_KEY_PATH = env("IDENTITY_PUBLIC_KEY_PATH", default="/app/keys/public.pem")
JWT_ISSUER = env("JWT_ISSUER", default="hamdong.identity-service")
JWT_AUDIENCE = env("JWT_AUDIENCE", default="hamdong.services")
JWT_ALGORITHM = env("JWT_ALGORITHM", default="RS256")

IDENTITY_SERVICE_URL = env("IDENTITY_SERVICE_URL", default="http://identity-service:8000")
INTERNAL_SERVICE_TOKEN = env("INTERNAL_SERVICE_TOKEN", default="hamdong-internal-token")
INTERNAL_HTTP_TIMEOUT_SECONDS = env.float("INTERNAL_HTTP_TIMEOUT_SECONDS", default=5.0)

DEFAULT_CURRENCY = env("DEFAULT_CURRENCY", default="IRR")
MAX_WALLET_OPERATION_AMOUNT_MINOR = env.int("MAX_WALLET_OPERATION_AMOUNT_MINOR", default=100000000000)

PAYMENT_INTENT_EXPIRES_IN_MINUTES = env.int("PAYMENT_INTENT_EXPIRES_IN_MINUTES", default=30)
FAKE_PAYMENT_PROVIDER_BASE_URL = env("FAKE_PAYMENT_PROVIDER_BASE_URL", default="https://fake-gateway/pay")
ZARINPAL_MERCHANT_ID = env("ZARINPAL_MERCHANT_ID", default="00000000-0000-0000-0000-000000000000")
ZARINPAL_SANDBOX = env.bool("ZARINPAL_SANDBOX", default=True)
ZARINPAL_CALLBACK_BASE_URL = env("ZARINPAL_CALLBACK_BASE_URL", default="http://localhost:8080")
ZARINPAL_HTTP_TIMEOUT_SECONDS = env.int("ZARINPAL_HTTP_TIMEOUT_SECONDS", default=10)

EVENT_OUTBOX_BATCH_SIZE = env.int("EVENT_OUTBOX_BATCH_SIZE", default=50)
EVENT_OUTBOX_POLL_INTERVAL_SECONDS = env.int("EVENT_OUTBOX_POLL_INTERVAL_SECONDS", default=5)
EVENT_MAX_RETRY_COUNT = env.int("EVENT_MAX_RETRY_COUNT", default=5)
EVENT_RETRY_DELAY_SECONDS = env("EVENT_RETRY_DELAY_SECONDS", default="10,30,60")
EVENT_DLQ_SUFFIX = env("EVENT_DLQ_SUFFIX", default=".dlq")

SECRET_KEY = env("SECRET_KEY", default="change-me")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "wallet-service"])

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "apps.wallets",
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
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.debug",
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

db_engine = os.environ.get("DJANGO_DB_ENGINE", "django.db.backends.postgresql")
db_name = os.environ.get("DJANGO_TEST_DB_NAME") if os.environ.get("PYTEST_CURRENT_TEST") else POSTGRES_DB
DATABASES = {
    "default": {
        "ENGINE": db_engine,
        "NAME": db_name if db_engine == "django.db.backends.sqlite3" else env("POSTGRES_DB", default="wallet_db"),
        "USER": "" if db_engine == "django.db.backends.sqlite3" else env("POSTGRES_USER", default="postgres"),
        "PASSWORD": "" if db_engine == "django.db.backends.sqlite3" else env("POSTGRES_PASSWORD", default="postgres"),
        "HOST": "" if db_engine == "django.db.backends.sqlite3" else env("POSTGRES_HOST", default="postgres"),
        "PORT": "" if db_engine == "django.db.backends.sqlite3" else env("POSTGRES_PORT", default="5432"),
        "TEST": {
            "NAME": db_name if db_engine == "django.db.backends.sqlite3" else env("POSTGRES_TEST_DB", default="test_wallet_db"),
        },
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.wallets.infrastructure.jwt_authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.wallets.infrastructure.exception_handlers.api_exception_handler",
}


SPECTACULAR_SETTINGS = {
    "TITLE": "HamDong Wallet Service API",
    "DESCRIPTION": "Wallet and payment endpoints.",
    "VERSION": SERVICE_VERSION,
}

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])

EXPOSE_API_DOCS = env.bool("EXPOSE_API_DOCS", default=DEBUG)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_REFERRER_POLICY = "same-origin"
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=not DEBUG)
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=not DEBUG)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"
