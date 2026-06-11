from django.apps import AppConfig


class SettlementsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.settlements"
    def ready(self):
        from .api import schema_extensions  # noqa: F401
