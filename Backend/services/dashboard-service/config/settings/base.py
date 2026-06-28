from pathlib import Path
import os

import environ

BASE_DIR = Path(__file__).resolve().parents[2]

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / ".env")

POSTGRES_DB = os.environ.get("POSTGRES_DB") or os.environ.get("DJANGO_DB_NAME", "dashboard_db")
POSTGRES_USER = os.environ.get("POSTGRES_USER") or os.environ.get("DJANGO_DB_USER", "postgres")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD") or os.environ.get("DJANGO_DB_PASSWORD", "postgres")
POSTGRES_HOST = os.getenv("POSTGRES_HOST") or os.getenv("DJANGO_DB_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT") or os.getenv("DJANGO_DB_PORT", "5432")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_DEFAULT_USER = os.getenv("RABBITMQ_DEFAULT_USER", "guest")
RABBITMQ_DEFAULT_PASS = os.getenv("RABBITMQ_DEFAULT_PASS", "guest")

SERVICE_NAME = "dashboard-service"
SERVICE_VERSION = "0.1.0"

IDENTITY_RABBITMQ_EXCHANGE = env("IDENTITY_RABBITMQ_EXCHANGE", default="hamdong.identity")
GROUP_RABBITMQ_EXCHANGE = env("GROUP_RABBITMQ_EXCHANGE", default="hamdong.group")
EXPENSE_RABBITMQ_EXCHANGE = env("EXPENSE_RABBITMQ_EXCHANGE", default="hamdong.expense")
MEDIA_RABBITMQ_EXCHANGE = env("MEDIA_RABBITMQ_EXCHANGE", default="hamdong.media")
SETTLEMENT_RABBITMQ_EXCHANGE = env("SETTLEMENT_RABBITMQ_EXCHANGE", default="hamdong.settlement")

DASHBOARD_IDENTITY_QUEUE = env("DASHBOARD_IDENTITY_QUEUE", default="dashboard.identity.user_events")
DASHBOARD_GROUP_QUEUE = env("DASHBOARD_GROUP_QUEUE", default="dashboard.group.events")
DASHBOARD_EXPENSE_QUEUE = env("DASHBOARD_EXPENSE_QUEUE", default="dashboard.expense.events")
DASHBOARD_MEDIA_QUEUE = env("DASHBOARD_MEDIA_QUEUE", default="dashboard.media.events")
DASHBOARD_SETTLEMENT_QUEUE = env("DASHBOARD_SETTLEMENT_QUEUE", default="dashboard.settlement.events")

IDENTITY_JWKS_URL = env(
    "IDENTITY_JWKS_URL",
    default="http://identity-service:8000/api/v1/auth/.well-known/jwks.json",
)
IDENTITY_PUBLIC_KEY_PATH = env("IDENTITY_PUBLIC_KEY_PATH", default="/app/keys/public.pem")
JWT_ISSUER = env("JWT_ISSUER", default="hamdong.identity-service")
JWT_AUDIENCE = env("JWT_AUDIENCE", default="hamdong.services")
JWT_ALGORITHM = env("JWT_ALGORITHM", default="RS256")

SETTLEMENT_SERVICE_URL = env("SETTLEMENT_SERVICE_URL", default="http://settlement-service:8000")
GROUP_SERVICE_URL = env("GROUP_SERVICE_URL", default="http://group-service:8000")
NOTIFICATION_SERVICE_URL = env("NOTIFICATION_SERVICE_URL", default="http://notification-service:8000")

INTERNAL_HTTP_TIMEOUT_SECONDS = env.float("INTERNAL_HTTP_TIMEOUT_SECONDS", default=5.0)

SECRET_KEY = env("SECRET_KEY", default="change-me")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "dashboard-service"])

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "apps.dashboard",
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
    "EXCEPTION_HANDLER": "apps.dashboard.infrastructure.exception_handlers.api_exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "dashboard-service API",
    "VERSION": SERVICE_VERSION,
}

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_ALL_ORIGINS = False
EXPOSE_API_DOCS = env.bool("EXPOSE_API_DOCS", default=DEBUG)

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=False)
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=False)
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=False)
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
