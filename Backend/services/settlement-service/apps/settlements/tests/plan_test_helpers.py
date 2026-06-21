import uuid
from types import SimpleNamespace

from rest_framework.test import APIClient

from apps.settlements.domain.models import (
    CurrencyChoices,
    GroupMemberProjection,
    GroupMemberStatusChoices,
    GroupMemberRoleChoices,
    GroupProjection,
    GroupStatusChoices,
    GroupBalanceSnapshot,
    UserProjection,
)


def create_group(title="Group A", owner_user_id=None, status=GroupStatusChoices.ACTIVE):
    owner_user_id = owner_user_id or uuid.uuid4()
    return GroupProjection.objects.create(
        group_id=uuid.uuid4(),
        title=title,
        group_type="GENERAL",
        status=status,
        created_by_user_id=owner_user_id,
        member_count=0,
    )


def create_user_projection(
    identity_user_id=None, art_name=None, email="+989100000000"
):
    identity_user_id = identity_user_id or uuid.uuid4()
    return UserProjection.objects.create(
        identity_user_id=identity_user_id,
        email=email,
        art_name=art_name,
        is_active=True,
    )


def create_member(
    group_id,
    user_id=None,
    status=GroupMemberStatusChoices.ACTIVE,
    role=GroupMemberRoleChoices.MEMBER,
    email="+989121234567",
    art_name_snapshot="Member",
):
    user_id = user_id or uuid.uuid4()
    return GroupMemberProjection.objects.create(
        group_id=group_id,
        user_id=user_id,
        email=email,
        art_name_snapshot=art_name_snapshot,
        role=role,
        status=status,
    )


def seed_snapshot(
    group_id,
    user_id,
    net_balance_minor,
    calculated_at=None,
    currency=CurrencyChoices.IRR,
):
    calculated_at = calculated_at
    return GroupBalanceSnapshot.objects.create(
        group_id=group_id,
        user_id=user_id,
        currency=currency,
        total_paid_minor=max(net_balance_minor, 0),
        total_share_minor=max(-net_balance_minor, 0),
        total_settled_paid_minor=0,
        total_settled_received_minor=0,
        net_balance_minor=net_balance_minor,
        calculated_at=calculated_at
        or GroupBalanceSnapshot._meta.get_field("calculated_at").default(),
    )


def auth_user(sub=None):
    return SimpleNamespace(sub=sub or uuid.uuid4(), is_authenticated=True)


def api_client(user=None):
    client = APIClient()
    if user is not None:
        client.force_authenticate(user=user)
    return client
