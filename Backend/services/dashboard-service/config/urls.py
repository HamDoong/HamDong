from django.conf import settings
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.dashboard.api.views import HealthView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("api/v1/dashboard/health/", HealthView.as_view(), name="dashboard_health"),
    path("api/v1/dashboard/", include("apps.dashboard.api.urls")),
]

if getattr(settings, "EXPOSE_API_DOCS", False):
    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path(
            "api/docs/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="docs",
        ),
    ]
