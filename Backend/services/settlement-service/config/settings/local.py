from .base import *  # noqa: F403
from .base import env

DEBUG = env.bool("DEBUG", default=True)

CORS_ALLOW_ALL_ORIGINS = env.bool("CORS_ALLOW_ALL_ORIGINS", default=True)
EXPOSE_API_DOCS = env.bool("EXPOSE_API_DOCS", default=True)
