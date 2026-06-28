
from __future__ import annotations

import uuid
from types import SimpleNamespace

from django.utils import timezone
from rest_framework.test import APIClient

from apps.wallets.domain.models import (
    CurrencyChoices,
    LedgerEntry,
    LedgerEntryTypeChoices,
    SettlementItemProjection,
    SettlementItemStatusChoices,
    SettlementPlanStatusChoices,
    UserProjection,
    Wallet,
    WalletTransaction,
    WalletTransactionDirectionChoices,
    WalletTransactionStatusChoices,
    WalletTransactionTypeChoices,
)
from apps.wallets.infrastructure.event_envelope import build_event_envelope
from apps.wallets.infrastructure.repositories import WalletRepository


def auth_user(sub=None, email="user@example.com", role="USER"):
    user_id = str(sub or uuid.uuid4())
    return SimpleNamespace(
        sub=user_id,
        id=user_id,
        email=email,
        role=role,
        token_jti=f"jti-{user_id}",
        is_authenticated=True,
    )


def api_client(user=None):
    client = APIClient()
    if user is not None:
        client.force_authenticate(user=user, token="test-access-token")
    return client


def create_user_projection(user_id=None, art_name="artist", email="user@example.com"):
    user_id = user_id or uuid.uuid4()
    return UserProjection.objects.create(
        identity_user_id=user_id,
        art_name=art_name,
        email=email,
        is_active=True,
    )


def get_or_create_wallet(user_id, currency=CurrencyChoices.IRR, status="ACTIVE"):
    wallet, _ = Wallet.objects.get_or_create(
        user_id=user_id,
        currency=currency,
        defaults={"status": status},
    )
    if wallet.status != status:
        wallet.status = status
        wallet.save(update_fields=["status", "updated_at"])
    return wallet


def seed_available_balance(user_id, amount_minor, *, currency=CurrencyChoices.IRR, description="Top up"):
    wallet = get_or_create_wallet(user_id, currency=currency)
    tx = WalletTransaction.objects.create(
        wallet=wallet,
        type=WalletTransactionTypeChoices.TOP_UP,
        status=WalletTransactionStatusChoices.COMPLETED,
        direction=WalletTransactionDirectionChoices.IN,
        amount_minor=amount_minor,
        currency=currency,
        description=description,
        idempotency_key=f"seed-{uuid.uuid4()}",
        completed_at=timezone.now(),
    )
    LedgerEntry.objects.create(
        wallet=wallet,
        transaction=tx,
        entry_type=LedgerEntryTypeChoices.AVAILABLE_CREDIT,
        amount_minor=amount_minor,
        currency=currency,
    )
    WalletRepository.refresh_balances(wallet)
    return wallet, tx


def create_settlement_item_projection(
    *,
    item_id=None,
    plan_id=None,
    group_id=None,
    payer_user_id=None,
    payee_user_id=None,
    amount_minor=500000,
    currency=CurrencyChoices.IRR,
    item_status=SettlementItemStatusChoices.PENDING,
    plan_status=SettlementPlanStatusChoices.ACTIVE,
):
    return SettlementItemProjection.objects.create(
        item_id=item_id or uuid.uuid4(),
        plan_id=plan_id or uuid.uuid4(),
        group_id=group_id or uuid.uuid4(),
        payer_user_id=payer_user_id or uuid.uuid4(),
        payee_user_id=payee_user_id or uuid.uuid4(),
        amount_minor=amount_minor,
        currency=currency,
        item_status=item_status,
        plan_status=plan_status,
        created_at=timezone.now(),
        updated_at=timezone.now(),
    )


def identity_event(event_type="UserCreated", *, event_id=None, data=None):
    return build_event_envelope(
        event_type,
        data or {
            "user_id": str(uuid.uuid4()),
            "email": "user@example.com",
            "art_name": "artist",
            "role": "USER",
            "is_active": True,
        },
        source_service="identity-service",
        routing_key=f"identity.user.{event_type.lower().replace('user', '').strip('.') or 'created'}",
        event_id=str(event_id or uuid.uuid4()),
    )


def settlement_event(event_type, *, event_id=None, occurred_at=None, data=None):
    routing_map = {
        "SettlementPlanGenerated": "settlement.plan.generated",
        "SettlementPlanActivated": "settlement.plan.activated",
        "SettlementPlanCancelled": "settlement.plan.cancelled",
        "SettlementPlanExpired": "settlement.plan.expired",
        "SettlementPlanCompleted": "settlement.plan.completed",
        "SettlementPlanItemReported": "settlement.plan_item.reported",
        "SettlementPlanItemConfirmed": "settlement.plan_item.confirmed",
        "SettlementPlanItemRejected": "settlement.plan_item.rejected",
    }
    return build_event_envelope(
        event_type,
        data or {},
        source_service="settlement-service",
        routing_key=routing_map[event_type],
        event_id=str(event_id or uuid.uuid4()),
        occurred_at=occurred_at,
    )
