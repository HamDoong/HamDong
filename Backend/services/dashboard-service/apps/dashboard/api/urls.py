from django.urls import path

from apps.dashboard.api.views import (
    DashboardActionItemsView,
    DashboardActivityFeedView,
    DashboardSummaryView,
)

urlpatterns = [
    path("summary/", DashboardSummaryView.as_view(), name="dashboard_summary"),
    path("action-items/", DashboardActionItemsView.as_view(), name="dashboard_action_items"),
    path("activity-feed/", DashboardActivityFeedView.as_view(), name="dashboard_activity_feed"),
]
