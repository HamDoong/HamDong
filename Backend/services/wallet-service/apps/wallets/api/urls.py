
from django.urls import path

from apps.wallets.api.views import (
    HealthView,
    WalletMeView,
    WalletSettlementPayView,
    WalletSummaryView,
    WalletTransactionDetailView,
    WalletTransactionListView,
    WalletWithdrawalCancelView,
    WalletWithdrawalDetailView,
    WalletWithdrawalListCreateView,
)

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("api/v1/wallets/me/", WalletMeView.as_view(), name="wallet-me"),
    path("api/v1/wallets/me/transactions/", WalletTransactionListView.as_view(), name="wallet-transactions"),
    path("api/v1/wallets/me/transactions/<uuid:transaction_id>/", WalletTransactionDetailView.as_view(), name="wallet-transaction-detail"),
    path("api/v1/wallets/settlement-plan-items/<uuid:item_id>/pay/", WalletSettlementPayView.as_view(), name="wallet-pay-settlement-item"),
    path("api/v1/wallets/me/summary/", WalletSummaryView.as_view(), name="wallet-summary"),
    path("api/v1/wallets/me/withdrawals/", WalletWithdrawalListCreateView.as_view(), name="wallet-withdrawals"),
    path("api/v1/wallets/me/withdrawals/<uuid:withdrawal_id>/", WalletWithdrawalDetailView.as_view(), name="wallet-withdrawal-detail"),
    path("api/v1/wallets/me/withdrawals/<uuid:withdrawal_id>/cancel/", WalletWithdrawalCancelView.as_view(), name="wallet-withdrawal-cancel"),
]
