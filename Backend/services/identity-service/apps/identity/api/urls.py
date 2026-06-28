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
    path("password/forgot/request/", views.ForgotPasswordRequestView.as_view(), name="password_forgot_request"),
    path("password/forgot/verify/", views.ForgotPasswordVerifyView.as_view(), name="password_forgot_verify"),
    path("password/reset/", views.PasswordResetView.as_view(), name="password_reset"),
    path("sessions/", views.SessionsView.as_view(), name="sessions"),
    path("sessions/<uuid:session_id>/", views.SessionDetailView.as_view(), name="session_detail"),
    path("jwks/", views.JwksView.as_view(), name="jwks"),
    path(".well-known/jwks.json", views.JwksView.as_view(), name="jwks_well_known"),
]
