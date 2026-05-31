from django.urls import path

from apps.settlements.api.views import (
    CancelSettlementView,
    ConfirmSettlementView,
    GroupBalancesView,
    GroupDebtsView,
    GroupSettlementsView,
    HealthView,
    MyBalanceView,
    RejectSettlementView,
)

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path(
        "groups/<uuid:group_id>/balances/",
        GroupBalancesView.as_view(),
        name="group_balances",
    ),
    path(
        "groups/<uuid:group_id>/balances/me/",
        MyBalanceView.as_view(),
        name="my_balance",
    ),
    path("groups/<uuid:group_id>/debts/", GroupDebtsView.as_view(), name="group_debts"),
    path(
        "groups/<uuid:group_id>/settlements/",
        GroupSettlementsView.as_view(),
        name="group_settlements",
    ),
    path(
        "settlements/<uuid:settlement_id>/confirm/",
        ConfirmSettlementView.as_view(),
        name="confirm_settlement",
    ),
    path(
        "settlements/<uuid:settlement_id>/reject/",
        RejectSettlementView.as_view(),
        name="reject_settlement",
    ),
    path(
        "settlements/<uuid:settlement_id>/cancel/",
        CancelSettlementView.as_view(),
        name="cancel_settlement",
    ),
]
