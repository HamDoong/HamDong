"""URL routing for identity service API."""

from django.urls import path

from apps.identity.api import views

app_name = "identity"

urlpatterns = [
    path("otp/request/", views.RequestOtpView.as_view(), name="otp_request"),
    path("otp/verify/", views.VerifyOtpView.as_view(), name="otp_verify"),
    path("token/refresh/", views.RefreshTokenView.as_view(), name="token_refresh"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("password/set/", views.PasswordSetView.as_view(), name="password_set"),
    path("password/login/", views.PasswordLoginView.as_view(), name="password_login"),
    path("password/change/", views.PasswordChangeView.as_view(), name="password_change"),
    path("jwks/", views.JwksView.as_view(), name="jwks"),
    path(".well-known/jwks.json", views.JwksView.as_view(), name="jwks_well_known"),
]
