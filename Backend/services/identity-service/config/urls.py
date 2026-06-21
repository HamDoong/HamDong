from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.identity.api.views import HealthView, MeView


urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("api/v1/auth/health/", HealthView.as_view(), name="auth_health"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="docs",
    ),
    path("api/v1/auth/", include("apps.identity.api.urls")),
    path("api/v1/users/me/", MeView.as_view(), name="get_current_user"),
]