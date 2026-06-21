from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.media_files.api.views import HealthView, ListGroupMediaView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("api/v1/media/health/", HealthView.as_view(), name="media_health"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="docs",
    ),
    path("api/v1/media/", include("apps.media_files.api.urls")),
    path(
        "api/v1/groups/<uuid:group_id>/media/",
        ListGroupMediaView.as_view(),
        name="group_media_list_alias",
    ),
]
