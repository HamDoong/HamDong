from django.db import models


class PlaceholderModel(models.Model):
    """Placeholder model to reserve the domain layer."""

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
