from apps.dashboard.application.dashboard_service import (
    DashboardActivityService,
    DashboardAggregationService,
)


class GetDashboardSummaryUseCase:
    def __init__(self, service=None):
        self.service = service or DashboardAggregationService()

    def execute(self, token, *, currency=None):
        return self.service.get_summary(token, currency=currency)


class ListDashboardActionItemsUseCase:
    def __init__(self, service=None):
        self.service = service or DashboardAggregationService()

    def execute(self, token, filters=None):
        return self.service.list_action_items(token, filters=filters)


class ListDashboardActivityFeedUseCase:
    def __init__(self, service=None):
        self.service = service or DashboardActivityService()

    def execute(self, requester_user_id, filters=None):
        return self.service.list_feed(requester_user_id, filters=filters)
