from django.urls import path

from apps.notifications.api.views import HealthView, MessagesView, TestSmsView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("sms/test/", TestSmsView.as_view(), name="sms_test"),
    path("messages/", MessagesView.as_view(), name="messages"),
]
