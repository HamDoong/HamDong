from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.notifications.api.views import HealthView
from apps.notifications.api.admin_views import AdminNotificationListView, AdminSystemHealthView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("api/v1/notifications/health/", HealthView.as_view(), name="notifications_health"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="docs",
    ),
    path("api/v1/notifications/", include("apps.notifications.api.urls")),
    path("api/v1/admin/notifications/", AdminNotificationListView.as_view(), name="admin_notifications"),
    path("api/v1/admin/system/health/", AdminSystemHealthView.as_view(), name="admin_system_health"),
]
