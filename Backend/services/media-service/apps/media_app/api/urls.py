from django.urls import path

from apps.media_app.api.views import HealthView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
]
