from django.apps import AppConfig


class MediaFilesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.media_files"
    verbose_name = "Media Files"
    def ready(self):
        from .api import schema_extensions  # noqa: F401
