from django.urls import path

from apps.identity.api.views import HealthView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
]
