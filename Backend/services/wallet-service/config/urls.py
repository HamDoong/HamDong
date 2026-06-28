from django.conf import settings
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("", include("apps.wallets.api.urls")),
]

if getattr(settings, "EXPOSE_API_DOCS", False):
    urlpatterns += [
        path(
            "api/schema/",
            SpectacularAPIView.as_view(authentication_classes=[], permission_classes=[]),
            name="schema",
        ),
        path(
            "api/docs/",
            SpectacularSwaggerView.as_view(url_name="schema", authentication_classes=[], permission_classes=[]),
            name="swagger-ui",
        ),
    ]
