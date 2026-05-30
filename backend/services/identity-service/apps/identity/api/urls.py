"""URL routing for identity service API."""

from django.urls import path

from apps.identity.api import views

app_name = "identity"

urlpatterns = [
    # Auth endpoints
    path("otp/request/", views.RequestOtpView.as_view(), name="otp_request"),
    path("otp/verify/", views.VerifyOtpView.as_view(), name="otp_verify"),
    path("token/refresh/", views.RefreshTokenView.as_view(), name="token_refresh"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("jwks/", views.JwksView.as_view(), name="jwks"),
    path(".well-known/jwks.json", views.JwksView.as_view(), name="jwks_well_known"),
]
