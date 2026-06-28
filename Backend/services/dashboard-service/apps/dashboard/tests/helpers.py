from __future__ import annotations

import uuid
from types import SimpleNamespace

from django.utils import timezone
from rest_framework.test import APIClient

from apps.dashboard.domain.models import (
    DashboardActivity,
    GroupMemberProjection,
    GroupProjection,
    UserProjection,
)


def auth_user(sub=None, email="user@example.com", role="USER"):
    return SimpleNamespace(
        sub=str(sub or uuid.uuid4()),
        id=str(sub or uuid.uuid4()),
        email=email,
        role=role,
        token_jti="test-jti",
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


def create_group(group_id=None, title="Group A", status="ACTIVE", created_by_user_id=None):
    return GroupProjection.objects.create(
        group_id=group_id or uuid.uuid4(),
        title=title,
        description="",
        group_type="GENERAL",
        status=status,
        created_by_user_id=created_by_user_id,
        member_count=1,
    )


def create_member(group_id, user_id, role="MEMBER", status="ACTIVE", art_name_snapshot="artist", email="user@example.com"):
    return GroupMemberProjection.objects.create(
        group_id=group_id,
        user_id=user_id,
        role=role,
        status=status,
        art_name_snapshot=art_name_snapshot,
        email=email,
    )


def create_activity(
    *,
    event_id=None,
    event_type="EXPENSE_CREATED",
    group_id,
    actor_user_id=None,
    source_object_id=None,
    summary=None,
    occurred_at=None,
):
    return DashboardActivity.objects.create(
        id=event_id or uuid.uuid4(),
        event_type=event_type,
        source_service="expense-service",
        routing_key="expense.created",
        group_id=group_id,
        actor_user_id=actor_user_id,
        source_object_id=source_object_id,
        summary=summary or {},
        occurred_at=occurred_at or timezone.now(),
    )
