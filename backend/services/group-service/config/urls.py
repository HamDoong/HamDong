from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.groups.api.views import HealthView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("api/v1/groups/health/", HealthView.as_view(), name="groups_health"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="docs",
    ),
    path("api/v1/groups/", include("apps.groups.api.urls")),
]
