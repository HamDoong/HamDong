"""Django models entrypoint for the identity app.

This module re-exports models defined under the domain package so
Django's model discovery finds them (Django looks for an app's
``models`` module by default).
"""

from .domain.models import *  # noqa: F401,F403
