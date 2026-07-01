from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.identity.api.views import (
    DeactivateAccountView,
    HealthView,
    InternalPaymentContextBankCardsView,
    MeAvatarView,
    MeBankCardDetailView,
    MeBankCardsBulkView,
    MeBankCardsView,
    MeView,
    PublicUserLookupView,
    UserSearchView,
)
from apps.identity.api.admin_views import (
    AdminSystemHealthView,
    AdminUserDetailView,
    AdminUserListView,
)

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
    path(
        "api/v1/admin/system/health/",
        AdminSystemHealthView.as_view(),
        name="admin_system_health",
    ),
    path("api/v1/admin/users/", AdminUserListView.as_view(), name="admin_users"),
    path(
        "api/v1/admin/users/<uuid:user_id>/",
        AdminUserDetailView.as_view(),
        name="admin_user_detail",
    ),
    path("api/v1/users/me/", MeView.as_view(), name="get_current_user"),
    path("api/v1/users/me/avatar/", MeAvatarView.as_view(), name="me_avatar"),
    path(
        "api/v1/users/me/bank-cards/", MeBankCardsView.as_view(), name="me_bank_cards"
    ),
    path(
        "api/v1/users/me/bank-cards/bulk/",
        MeBankCardsBulkView.as_view(),
        name="me_bank_cards_bulk",
    ),
    path(
        "api/v1/users/me/bank-cards/<uuid:card_id>/",
        MeBankCardDetailView.as_view(),
        name="me_bank_card_detail",
    ),
    path(
        "api/v1/users/me/deactivate/",
        DeactivateAccountView.as_view(),
        name="deactivate_account",
    ),
    path("api/v1/users/search/", UserSearchView.as_view(), name="user_search"),
    path(
        "api/v1/users/<str:user_id>/public/",
        PublicUserLookupView.as_view(),
        name="public_user_lookup",
    ),
    path(
        "api/v1/internal/bank-cards/payment-context/",
        InternalPaymentContextBankCardsView.as_view(),
        name="internal_payment_context_bank_cards",
    ),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
