from .base import *  # noqa: F403
from .base import env

DEBUG = False
CORS_ALLOW_ALL_ORIGINS = False
EXPOSE_API_DOCS = False
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
