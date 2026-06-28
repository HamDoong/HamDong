from django.conf import settings
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.settlements.api.views import HealthView
from apps.settlements.api.admin_views import AdminFailedEventsListView, AdminOutboxListView, AdminSettlementListView, AdminSystemHealthView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("api/v1/settlements/health/", HealthView.as_view(), name="settlements_health"),
    path("api/v1/", include("apps.settlements.api.urls")),
    path("api/v1/admin/settlements/", AdminSettlementListView.as_view(), name="admin_settlements"),
    path("api/v1/admin/outbox/", AdminOutboxListView.as_view(), name="admin_outbox"),
    path("api/v1/admin/failed-events/", AdminFailedEventsListView.as_view(), name="admin_failed_events"),
    path("api/v1/admin/system/health/", AdminSystemHealthView.as_view(), name="admin_system_health"),
]

if settings.EXPOSE_API_DOCS:
    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path(
            "api/docs/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="docs",
        ),
    ]
