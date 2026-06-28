from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.groups.api.urls import recipient_invitation_urlpatterns
from apps.groups.api.views import HealthView
from apps.groups.api.admin_views import AdminGroupListView, AdminSystemHealthView

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
    path("api/v1/admin/groups/", AdminGroupListView.as_view(), name="admin_groups"),
    path("api/v1/admin/system/health/", AdminSystemHealthView.as_view(), name="admin_system_health"),
    path("api/v1/", include((recipient_invitation_urlpatterns, "groups"))),
]
