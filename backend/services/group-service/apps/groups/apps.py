from django.apps import AppConfig


class GroupsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.groups"

    def ready(self):
        from .api import schema_extensions  # noqa: F401