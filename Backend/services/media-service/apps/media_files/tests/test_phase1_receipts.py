from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.media_files.domain.models import (
    ExpenseProjection,
    ExpenseStatusChoices,
    GroupMemberProjection,
    GroupMemberStatusChoices,
    GroupProjection,
    GroupStatusChoices,
    MediaAccessLog,
    MediaFile,
    MediaFileTypeChoices,
    MediaStatusChoices,
)
from apps.media_files.infrastructure.jwt_authentication import JWTAuthentication
from apps.media_files.infrastructure.rabbitmq_consumer import MediaEventConsumer
from apps.media_files.tests.test_phase6 import FakeUser, auth_client, envelope, seed_active_group


def seed_expense(*, group_id, created_by_user_id=None, payer_user_id=None, status=ExpenseStatusChoices.ACTIVE, version=1):
    return ExpenseProjection.objects.create(
        expense_id=uuid.uuid4(),
        group_id=group_id,
        status=status,
        created_by_user_id=created_by_user_id or uuid.uuid4(),
        payer_user_id=payer_user_id or uuid.uuid4(),
        version=version,
    )


def seed_receipt(
    *,
    group_id,
    uploaded_by_user_id,
    expense_id=None,
    name="receipt.jpg",
    created_at=None,
    status=MediaStatusChoices.ACTIVE,
):
    media = MediaFile.objects.create(
        uploaded_by_user_id=uploaded_by_user_id,
        group_id=group_id,
        related_expense_id=expense_id,
        file_type=MediaFileTypeChoices.RECEIPT,
        storage_provider="LOCAL",
        object_key=f"receipts/{group_id}/{uuid.uuid4()}.jpg",
        original_filename=name,
        stored_filename=f"{uuid.uuid4()}.jpg",
        content_type="image/jpeg",
        file_extension="jpg",
        size_bytes=12345,
        checksum_sha256="a" * 64,
        status=status,
        visibility="GROUP_MEMBERS",
    )
    if created_at is not None:
        MediaFile.objects.filter(id=media.id).update(created_at=created_at, updated_at=created_at)
        media.refresh_from_db()
    return media


@pytest.mark.django_db
def test_expense_receipts_requires_authentication():
    expense_id = uuid.uuid4()
    client = APIClient()
    response = client.get(f"/api/v1/expenses/{expense_id}/receipts/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_expense_receipts_rejects_invalid_token():
    expense_id = uuid.uuid4()
    client = APIClient()
    response = client.get(
        f"/api/v1/expenses/{expense_id}/receipts/",
        HTTP_AUTHORIZATION="Bearer definitely-invalid",
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_my_receipts_requires_authentication():
    client = APIClient()
    response = client.get("/api/v1/users/me/receipts/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_my_receipts_rejects_invalid_token():
    client = APIClient()
    response = client.get(
        "/api/v1/users/me/receipts/",
        HTTP_AUTHORIZATION="Bearer definitely-invalid",
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_expense_receipts_member_can_see_receipts(monkeypatch):
    user = FakeUser()
    client = auth_client(monkeypatch, user=user)
    group_id = seed_active_group(member_user_id=user.sub, uploaded_by=user.sub)
    expense = seed_expense(group_id=group_id, created_by_user_id=user.sub, payer_user_id=user.sub)
    receipt = seed_receipt(group_id=group_id, uploaded_by_user_id=user.sub, expense_id=expense.expense_id)

    response = client.get(f"/api/v1/expenses/{expense.expense_id}/receipts/")

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["next_cursor"] is None
    assert payload["results"][0]["id"] == str(receipt.id)
    assert payload["results"][0]["expense_id"] == str(expense.expense_id)
    assert payload["results"][0]["group_id"] == str(group_id)
    assert payload["results"][0]["download_url"] == f"/api/v1/media/files/{receipt.id}/download/"
    assert "object_key" not in payload["results"][0]
    assert MediaAccessLog.objects.filter(media_file=receipt, user_id=user.sub, action="VIEW").count() == 1


@pytest.mark.django_db
def test_expense_receipts_non_member_cannot_see_receipts(monkeypatch):
    user = FakeUser()
    client = auth_client(monkeypatch, user=user)
    member_id = uuid.uuid4()
    group_id = seed_active_group(member_user_id=member_id, uploaded_by=member_id)
    expense = seed_expense(group_id=group_id, created_by_user_id=member_id, payer_user_id=member_id)
    seed_receipt(group_id=group_id, uploaded_by_user_id=member_id, expense_id=expense.expense_id)

    response = client.get(f"/api/v1/expenses/{expense.expense_id}/receipts/")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_expense_receipts_deleted_receipts_are_hidden(monkeypatch):
    user = FakeUser()
    client = auth_client(monkeypatch, user=user)
    group_id = seed_active_group(member_user_id=user.sub, uploaded_by=user.sub)
    expense = seed_expense(group_id=group_id, created_by_user_id=user.sub, payer_user_id=user.sub)
    seed_receipt(group_id=group_id, uploaded_by_user_id=user.sub, expense_id=expense.expense_id, status=MediaStatusChoices.DELETED)
    seed_receipt(group_id=group_id, uploaded_by_user_id=user.sub, expense_id=expense.expense_id)

    response = client.get(f"/api/v1/expenses/{expense.expense_id}/receipts/")

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()["results"]) == 1


@pytest.mark.django_db
def test_my_receipts_only_shows_active_group_memberships(monkeypatch):
    user = FakeUser()
    client = auth_client(monkeypatch, user=user)
    active_group_id = seed_active_group(member_user_id=user.sub, uploaded_by=user.sub)
    hidden_group_id = seed_active_group(member_user_id=uuid.uuid4(), uploaded_by=uuid.uuid4())
    visible_receipt = seed_receipt(group_id=active_group_id, uploaded_by_user_id=user.sub)
    seed_receipt(group_id=hidden_group_id, uploaded_by_user_id=uuid.uuid4())

    response = client.get("/api/v1/users/me/receipts/")

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert [item["id"] for item in payload["results"]] == [str(visible_receipt.id)]


@pytest.mark.django_db
def test_my_receipts_hides_left_group_memberships(monkeypatch):
    user = FakeUser()
    client = auth_client(monkeypatch, user=user)
    group_id = seed_active_group(member_user_id=user.sub, uploaded_by=user.sub)
    GroupMemberProjection.objects.filter(group_id=group_id, user_id=user.sub).update(status=GroupMemberStatusChoices.LEFT)
    seed_receipt(group_id=group_id, uploaded_by_user_id=user.sub)

    response = client.get("/api/v1/users/me/receipts/")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["results"] == []


@pytest.mark.django_db
def test_my_receipts_filters_work_together(monkeypatch):
    user = FakeUser()
    other_user_id = uuid.uuid4()
    client = auth_client(monkeypatch, user=user)
    group_id = seed_active_group(member_user_id=user.sub, uploaded_by=user.sub)
    GroupMemberProjection.objects.create(
        group_id=group_id,
        user_id=other_user_id,
        email="+9892",
        art_name_snapshot="Other",
        role="MEMBER",
        status="ACTIVE",
    )
    expense = seed_expense(group_id=group_id, created_by_user_id=user.sub, payer_user_id=user.sub)
    now = timezone.now()
    too_old = seed_receipt(
        group_id=group_id,
        uploaded_by_user_id=user.sub,
        expense_id=expense.expense_id,
        created_at=now - timedelta(days=5),
    )
    wrong_uploader = seed_receipt(
        group_id=group_id,
        uploaded_by_user_id=other_user_id,
        expense_id=expense.expense_id,
        created_at=now - timedelta(days=1),
    )
    wanted = seed_receipt(
        group_id=group_id,
        uploaded_by_user_id=user.sub,
        expense_id=expense.expense_id,
        created_at=now,
    )

    response = client.get(
        "/api/v1/users/me/receipts/",
        {
            "group_id": str(group_id),
            "expense_id": str(expense.expense_id),
            "uploaded_by_me": "true",
            "from": (now - timedelta(days=2)).date().isoformat(),
            "to": now.date().isoformat(),
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["results"][0]["id"] == str(wanted.id)
    all_ids = {item["id"] for item in response.json()["results"]}
    assert str(too_old.id) not in all_ids
    assert str(wrong_uploader.id) not in all_ids


@pytest.mark.django_db
def test_my_receipts_group_filter_enforces_membership(monkeypatch):
    user = FakeUser()
    client = auth_client(monkeypatch, user=user)
    group_id = seed_active_group(member_user_id=uuid.uuid4(), uploaded_by=uuid.uuid4())

    response = client.get("/api/v1/users/me/receipts/", {"group_id": str(group_id)})

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_my_receipts_expense_filter_enforces_membership(monkeypatch):
    user = FakeUser()
    client = auth_client(monkeypatch, user=user)
    member_id = uuid.uuid4()
    group_id = seed_active_group(member_user_id=member_id, uploaded_by=member_id)
    expense = seed_expense(group_id=group_id, created_by_user_id=member_id, payer_user_id=member_id)

    response = client.get("/api/v1/users/me/receipts/", {"expense_id": str(expense.expense_id)})

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_my_receipts_invalid_query_params_return_400(monkeypatch):
    user = FakeUser()
    client = auth_client(monkeypatch, user=user)

    response = client.get(
        "/api/v1/users/me/receipts/",
        {
            "group_id": "bad-uuid",
            "expense_id": "bad-uuid",
            "uploaded_by_me": "maybe",
            "from": "not-a-date",
            "cursor": "###",
            "page_size": 999,
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


@pytest.mark.django_db
def test_expense_receipts_invalid_cursor_returns_400(monkeypatch):
    user = FakeUser()
    client = auth_client(monkeypatch, user=user)
    group_id = seed_active_group(member_user_id=user.sub, uploaded_by=user.sub)
    expense = seed_expense(group_id=group_id, created_by_user_id=user.sub, payer_user_id=user.sub)

    response = client.get(f"/api/v1/expenses/{expense.expense_id}/receipts/?cursor=bad-cursor")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"]["code"] == "INVALID_CURSOR"


@pytest.mark.django_db
def test_receipt_list_cursor_pagination(monkeypatch):
    user = FakeUser()
    client = auth_client(monkeypatch, user=user)
    group_id = seed_active_group(member_user_id=user.sub, uploaded_by=user.sub)
    expense = seed_expense(group_id=group_id, created_by_user_id=user.sub, payer_user_id=user.sub)
    first = seed_receipt(group_id=group_id, uploaded_by_user_id=user.sub, expense_id=expense.expense_id, created_at=timezone.now())
    second = seed_receipt(group_id=group_id, uploaded_by_user_id=user.sub, expense_id=expense.expense_id, created_at=timezone.now() - timedelta(minutes=1))
    third = seed_receipt(group_id=group_id, uploaded_by_user_id=user.sub, expense_id=expense.expense_id, created_at=timezone.now() - timedelta(minutes=2))

    page_one = client.get(f"/api/v1/expenses/{expense.expense_id}/receipts/", {"page_size": 2})
    assert page_one.status_code == status.HTTP_200_OK
    page_one_payload = page_one.json()
    assert [item["id"] for item in page_one_payload["results"]] == [str(first.id), str(second.id)]
    assert page_one_payload["next_cursor"]

    page_two = client.get(
        f"/api/v1/expenses/{expense.expense_id}/receipts/",
        {"page_size": 2, "cursor": page_one_payload["next_cursor"]},
    )
    assert page_two.status_code == status.HTTP_200_OK
    assert [item["id"] for item in page_two.json()["results"]] == [str(third.id)]


@pytest.mark.django_db
def test_expense_event_consumer_creates_updates_and_deletes_projection():
    consumer = MediaEventConsumer()
    group_id = str(uuid.uuid4())
    expense_id = str(uuid.uuid4())

    created = envelope(
        "ExpenseCreated",
        {
            "expense_id": expense_id,
            "group_id": group_id,
            "created_by_user_id": str(uuid.uuid4()),
            "payer_user_id": str(uuid.uuid4()),
        },
        "expense.created",
    )
    consumer.process_expense_payload(created)

    updated = envelope(
        "ExpenseUpdated",
        {
            "expense_id": expense_id,
            "group_id": group_id,
            "created_by_user_id": str(uuid.uuid4()),
            "payer_user_id": str(uuid.uuid4()),
            "status": "UPDATED",
            "version": 2,
        },
        "expense.updated",
    )
    consumer.process_expense_payload(updated)

    stale = envelope(
        "ExpenseUpdated",
        {
            "expense_id": expense_id,
            "group_id": group_id,
            "created_by_user_id": str(uuid.uuid4()),
            "payer_user_id": str(uuid.uuid4()),
            "status": "ACTIVE",
            "version": 1,
        },
        "expense.updated",
    )
    consumer.process_expense_payload(stale)

    deleted = envelope(
        "ExpenseDeleted",
        {
            "expense_id": expense_id,
            "group_id": group_id,
            "status": "DELETED",
        },
        "expense.deleted",
    )
    consumer.process_expense_payload(deleted)

    projection = ExpenseProjection.objects.get(expense_id=expense_id)
    assert projection.version == 2
    assert projection.status == ExpenseStatusChoices.DELETED


@pytest.mark.django_db
def test_expense_event_consumer_is_idempotent_for_same_event():
    consumer = MediaEventConsumer()
    payload = envelope(
        "ExpenseCreated",
        {
            "expense_id": str(uuid.uuid4()),
            "group_id": str(uuid.uuid4()),
            "created_by_user_id": str(uuid.uuid4()),
            "payer_user_id": str(uuid.uuid4()),
        },
        "expense.created",
    )

    consumer.process_expense_payload(payload)
    consumer.process_expense_payload(payload)

    assert ExpenseProjection.objects.count() == 1


@pytest.mark.django_db
def test_receipt_listing_schema_contains_new_paths(monkeypatch):
    user = FakeUser()
    client = auth_client(monkeypatch, user=user)
    response = client.get("/api/schema/?format=json")

    assert response.status_code == status.HTTP_200_OK
    schema = response.json()
    assert "/api/v1/expenses/{expense_id}/receipts/" in schema["paths"]
    assert "/api/v1/users/me/receipts/" in schema["paths"]


@pytest.mark.django_db
def test_receipt_listing_response_contract(monkeypatch):
    user = FakeUser()
    client = auth_client(monkeypatch, user=user)
    group_id = seed_active_group(member_user_id=user.sub, uploaded_by=user.sub)
    expense = seed_expense(group_id=group_id, created_by_user_id=user.sub, payer_user_id=user.sub)
    receipt = seed_receipt(group_id=group_id, uploaded_by_user_id=user.sub, expense_id=expense.expense_id)

    response = client.get("/api/v1/users/me/receipts/", {"expense_id": str(expense.expense_id)})
    assert response.status_code == status.HTTP_200_OK
    item = response.json()["results"][0]
    assert item["id"] == str(receipt.id)
    assert item["expense_id"] == str(expense.expense_id)
    assert item["group"]["id"] == str(group_id)
    assert item["group"]["title"] == "Trip"
    assert item["download_url"].endswith("/download/")
    assert "object_key" not in item
    uuid.UUID(item["id"])
    uuid.UUID(item["expense_id"])
    uuid.UUID(item["group"]["id"])
    uuid.UUID(item["uploaded_by_user_id"])
    assert item["created_at"].endswith("Z") or "+" in item["created_at"]


@pytest.mark.django_db
def test_expense_receipts_unknown_expense_returns_404(monkeypatch):
    user = FakeUser()
    client = auth_client(monkeypatch, user=user)
    response = client.get(f"/api/v1/expenses/{uuid.uuid4()}/receipts/")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_jwt_auth_monkeypatch_still_returns_valid_token_for_new_endpoints(monkeypatch):
    user = FakeUser()
    client = APIClient()

    def fake_auth(self, request):
        return user, "token"

    monkeypatch.setattr(JWTAuthentication, "authenticate", fake_auth)
    group_id = seed_active_group(member_user_id=user.sub, uploaded_by=user.sub)
    expense = seed_expense(group_id=group_id, created_by_user_id=user.sub, payer_user_id=user.sub)
    seed_receipt(group_id=group_id, uploaded_by_user_id=user.sub, expense_id=expense.expense_id)

    expense_response = client.get(f"/api/v1/expenses/{expense.expense_id}/receipts/")
    my_response = client.get(reverse("my_receipt_list"))

    assert expense_response.status_code == status.HTTP_200_OK
    assert my_response.status_code == status.HTTP_200_OK
