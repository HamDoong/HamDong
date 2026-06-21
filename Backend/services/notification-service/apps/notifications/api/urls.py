from django.urls import path

from apps.notifications.api.views import (
    HealthView,
    MessagesView,
    NotificationDetailView,
    NotificationListCreateView,
    NotificationReadAllView,
    NotificationReadView,
    NotificationUnreadCountView,
    TestEmailView,
)

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("sms/test/", TestEmailView.as_view(), name="sms_test"),
    path("email/test/", TestEmailView.as_view(), name="email_test"),
    path("messages/", MessagesView.as_view(), name="messages"),
    path("unread-count/", NotificationUnreadCountView.as_view(), name="notifications_unread_count"),
    path("read-all/", NotificationReadAllView.as_view(), name="notifications_read_all"),
    path("<uuid:notification_id>/read/", NotificationReadView.as_view(), name="notification_read"),
    path("", NotificationListCreateView.as_view(), name="notifications"),
    path("<uuid:notification_id>/", NotificationDetailView.as_view(), name="notification_detail"),
]
