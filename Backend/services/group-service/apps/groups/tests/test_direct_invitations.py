from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import exceptions, status
from rest_framework.test import APIClient

from apps.groups.domain.models import GroupInvite, GroupInviteTypeChoices, GroupMember, OutboxMessage, UserProjection
from apps.groups.infrastructure.jwt_authentication import JWTAuthentication


class FakeUser:
    def __init__(self, *, sub=None, email="user@example.com", art_name="artist", role="USER"):
        self.sub = str(sub or uuid.uuid4())
        self.id = self.sub
        self.email = email
        self.art_name = art_name
        self.role = role
        self.payload = {
            "sub": self.sub,
            "email": self.email,
            "role": self.role,
        }

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False


@pytest.fixture
def auth_registry(monkeypatch):
    registry = {}

    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION")
        if not header:
            raise exceptions.NotAuthenticated()
        if header == "Bearer invalid":
            raise exceptions.AuthenticationFailed("invalid")
        user = registry.get(header)
        if not user:
            raise exceptions.AuthenticationFailed("invalid")
        return user, None

    monkeypatch.setattr(JWTAuthentication, "authenticate", authenticate)
    return registry


def make_client(registry, user: FakeUser | None = None, token: str | None = None):
    client = APIClient()
    if user is not None:
        registry[token or f"Bearer {user.sub}"] = user
        client.credentials(HTTP_AUTHORIZATION=token or f"Bearer {user.sub}")
    return client


def create_projection(user: FakeUser, *, is_active=True):
    return UserProjection.objects.create(
        identity_user_id=user.sub,
        email=user.email,
        art_name=user.art_name,
        is_active=is_active,
    )


@pytest.mark.django_db
def test_owner_and_admin_can_create_direct_invites(auth_registry):
    owner = FakeUser(email="owner@example.com", art_name="owner_artist")
    admin = FakeUser(email="admin@example.com", art_name="admin_artist")
    recipient = FakeUser(email="recipient@example.com", art_name="recipient_artist")
    create_projection(owner)
    create_projection(admin)
    create_projection(recipient)

    owner_client = make_client(auth_registry, owner)
    create_response = owner_client.post("/api/v1/groups/", {"title": "سفر شمال", "group_type": "TRIP"}, format="json")
    assert create_response.status_code == 201
    group_id = create_response.json()["id"]

    GroupMember.objects.create(
        group_id=group_id,
        user_id=admin.sub,
        email=admin.email,
        art_name_snapshot=admin.art_name,
        role="ADMIN",
        status="ACTIVE",
    )

    owner_invite = owner_client.post(
        f"/api/v1/groups/{group_id}/invites/direct/",
        {"recipient_user_id": recipient.sub, "expires_in_hours": 48},
        format="json",
    )
    assert owner_invite.status_code == 201
    invite_id = owner_invite.json()["id"]
    invite = GroupInvite.objects.get(id=invite_id)
    assert invite.invite_type == GroupInviteTypeChoices.DIRECT
    assert invite.status == "PENDING"

    admin_client = make_client(auth_registry, admin)
    second_recipient = FakeUser(email="recipient2@example.com", art_name="recipient2")
    create_projection(second_recipient)
    admin_invite = admin_client.post(
        f"/api/v1/groups/{group_id}/invites/direct/",
        {"recipient_user_id": second_recipient.sub, "expires_in_hours": 72},
        format="json",
    )
    assert admin_invite.status_code == 201
    assert OutboxMessage.objects.filter(event_type="GroupDirectInvitationCreated").count() == 2


@pytest.mark.django_db
def test_member_and_non_member_cannot_create_direct_invites(auth_registry):
    owner = FakeUser(email="owner@example.com")
    member = FakeUser(email="member@example.com")
    outsider = FakeUser(email="outsider@example.com")
    recipient = FakeUser(email="recipient@example.com")
    for user in (owner, member, outsider, recipient):
        create_projection(user)

    owner_client = make_client(auth_registry, owner)
    group_id = owner_client.post("/api/v1/groups/", {"title": "g", "group_type": "GENERAL"}, format="json").json()["id"]
    GroupMember.objects.create(
        group_id=group_id,
        user_id=member.sub,
        email=member.email,
        art_name_snapshot=member.art_name,
        role="MEMBER",
        status="ACTIVE",
    )

    member_client = make_client(auth_registry, member)
    outsider_client = make_client(auth_registry, outsider)

    member_resp = member_client.post(f"/api/v1/groups/{group_id}/invites/direct/", {"recipient_user_id": recipient.sub}, format="json")
    outsider_resp = outsider_client.post(f"/api/v1/groups/{group_id}/invites/direct/", {"recipient_user_id": recipient.sub}, format="json")
    assert member_resp.status_code == 403
    assert outsider_resp.status_code == 403


@pytest.mark.django_db
def test_direct_invite_auth_errors(auth_registry):
    client = APIClient()
    missing = client.post(f"/api/v1/groups/{uuid.uuid4()}/invites/direct/", {"recipient_user_id": str(uuid.uuid4())}, format="json")
    assert missing.status_code == 401

    client.credentials(HTTP_AUTHORIZATION="Bearer invalid")
    invalid = client.post(f"/api/v1/groups/{uuid.uuid4()}/invites/direct/", {"recipient_user_id": str(uuid.uuid4())}, format="json")
    assert invalid.status_code == 401


@pytest.mark.django_db
def test_direct_invite_validation_rules(auth_registry):
    owner = FakeUser(email="owner@example.com")
    inactive = FakeUser(email="inactive@example.com")
    active = FakeUser(email="active@example.com")
    create_projection(owner)
    create_projection(inactive, is_active=False)
    create_projection(active)

    owner_client = make_client(auth_registry, owner)
    group_id = owner_client.post("/api/v1/groups/", {"title": "g", "group_type": "GENERAL"}, format="json").json()["id"]

    not_found = owner_client.post(f"/api/v1/groups/{group_id}/invites/direct/", {"recipient_user_id": str(uuid.uuid4())}, format="json")
    inactive_resp = owner_client.post(f"/api/v1/groups/{group_id}/invites/direct/", {"recipient_user_id": inactive.sub}, format="json")
    first = owner_client.post(f"/api/v1/groups/{group_id}/invites/direct/", {"recipient_user_id": active.sub}, format="json")
    duplicate = owner_client.post(f"/api/v1/groups/{group_id}/invites/direct/", {"recipient_user_id": active.sub}, format="json")

    GroupMember.objects.create(group_id=group_id, user_id=active.sub, email=active.email, art_name_snapshot=active.art_name, role="MEMBER", status="ACTIVE")
    already_member = owner_client.post(f"/api/v1/groups/{group_id}/invites/direct/", {"recipient_user_id": active.sub}, format="json")

    assert not_found.status_code == 400
    assert inactive_resp.status_code == 400
    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert already_member.status_code == 409


@pytest.mark.django_db
def test_recipient_can_list_and_view_only_own_invitations(auth_registry):
    owner = FakeUser(email="owner@example.com", art_name="owner_artist")
    recipient = FakeUser(email="recipient@example.com", art_name="reza_artist")
    other = FakeUser(email="other@example.com", art_name="other_artist")
    for user in (owner, recipient, other):
        create_projection(user)

    owner_client = make_client(auth_registry, owner)
    group_id = owner_client.post("/api/v1/groups/", {"title": "سفر شمال", "group_type": "TRIP"}, format="json").json()["id"]
    invite_id = owner_client.post(f"/api/v1/groups/{group_id}/invites/direct/", {"recipient_user_id": recipient.sub}, format="json").json()["id"]

    recipient_client = make_client(auth_registry, recipient)
    other_client = make_client(auth_registry, other)

    listing = recipient_client.get("/api/v1/users/me/group-invitations/")
    assert listing.status_code == 200
    assert listing.json()["results"][0]["id"] == invite_id
    assert listing.json()["results"][0]["invited_by"]["art_name"] == "owner_artist"

    detail = recipient_client.get(f"/api/v1/group-invitations/{invite_id}/")
    assert detail.status_code == 200
    assert detail.json()["group"]["title"] == "سفر شمال"

    other_detail = other_client.get(f"/api/v1/group-invitations/{invite_id}/")
    assert other_detail.status_code == 404


@pytest.mark.django_db
def test_recipient_can_accept_direct_invite_and_second_accept_is_idempotent(auth_registry):
    owner = FakeUser(email="owner@example.com")
    recipient = FakeUser(email="recipient@example.com", art_name="recipient_artist")
    create_projection(owner)
    create_projection(recipient)

    owner_client = make_client(auth_registry, owner)
    group_id = owner_client.post("/api/v1/groups/", {"title": "g", "group_type": "GENERAL"}, format="json").json()["id"]
    invite_id = owner_client.post(f"/api/v1/groups/{group_id}/invites/direct/", {"recipient_user_id": recipient.sub}, format="json").json()["id"]

    recipient_client = make_client(auth_registry, recipient)
    first = recipient_client.post(f"/api/v1/group-invitations/{invite_id}/accept/", {}, format="json")
    second = recipient_client.post(f"/api/v1/group-invitations/{invite_id}/accept/", {}, format="json")

    assert first.status_code == 200
    assert second.status_code == 200
    assert GroupMember.objects.filter(group_id=group_id, user_id=recipient.sub, status="ACTIVE").count() == 1
    invite = GroupInvite.objects.get(id=invite_id)
    assert invite.status == "ACCEPTED"
    assert OutboxMessage.objects.filter(event_type="GroupDirectInvitationAccepted").count() == 1


@pytest.mark.django_db
def test_other_user_cannot_accept_direct_invite(auth_registry):
    owner = FakeUser(email="owner@example.com")
    recipient = FakeUser(email="recipient@example.com")
    other = FakeUser(email="other@example.com")
    for user in (owner, recipient, other):
        create_projection(user)

    owner_client = make_client(auth_registry, owner)
    group_id = owner_client.post("/api/v1/groups/", {"title": "g", "group_type": "GENERAL"}, format="json").json()["id"]
    invite_id = owner_client.post(f"/api/v1/groups/{group_id}/invites/direct/", {"recipient_user_id": recipient.sub}, format="json").json()["id"]

    other_client = make_client(auth_registry, other)
    response = other_client.post(f"/api/v1/group-invitations/{invite_id}/accept/", {}, format="json")
    assert response.status_code == 404


@pytest.mark.django_db
def test_expired_direct_invitation_cannot_be_accepted(auth_registry):
    owner = FakeUser(email="owner@example.com")
    recipient = FakeUser(email="recipient@example.com")
    create_projection(owner)
    create_projection(recipient)
    owner_client = make_client(auth_registry, owner)
    group_id = owner_client.post("/api/v1/groups/", {"title": "g", "group_type": "GENERAL"}, format="json").json()["id"]
    invite_id = owner_client.post(f"/api/v1/groups/{group_id}/invites/direct/", {"recipient_user_id": recipient.sub, "expires_in_hours": 1}, format="json").json()["id"]

    invite = GroupInvite.objects.get(id=invite_id)
    invite.expires_at = timezone.now() - timedelta(minutes=1)
    invite.save(update_fields=["expires_at", "updated_at"])

    recipient_client = make_client(auth_registry, recipient)
    response = recipient_client.post(f"/api/v1/group-invitations/{invite_id}/accept/", {}, format="json")
    assert response.status_code == 409
    invite.refresh_from_db()
    assert invite.status == "EXPIRED"


@pytest.mark.django_db
def test_recipient_can_reject_and_cannot_accept_after_reject(auth_registry):
    owner = FakeUser(email="owner@example.com")
    recipient = FakeUser(email="recipient@example.com")
    create_projection(owner)
    create_projection(recipient)

    owner_client = make_client(auth_registry, owner)
    group_id = owner_client.post("/api/v1/groups/", {"title": "g", "group_type": "GENERAL"}, format="json").json()["id"]
    invite_id = owner_client.post(f"/api/v1/groups/{group_id}/invites/direct/", {"recipient_user_id": recipient.sub}, format="json").json()["id"]

    recipient_client = make_client(auth_registry, recipient)
    reject = recipient_client.post(f"/api/v1/group-invitations/{invite_id}/reject/", {}, format="json")
    accept_after_reject = recipient_client.post(f"/api/v1/group-invitations/{invite_id}/accept/", {}, format="json")

    assert reject.status_code == 200
    assert accept_after_reject.status_code == 409
    assert GroupMember.objects.filter(group_id=group_id, user_id=recipient.sub).count() == 0
    invite = GroupInvite.objects.get(id=invite_id)
    assert invite.status == "REJECTED"
    assert OutboxMessage.objects.filter(event_type="GroupDirectInvitationRejected").count() == 1


@pytest.mark.django_db
def test_reject_after_accept_is_rejected(auth_registry):
    owner = FakeUser(email="owner@example.com")
    recipient = FakeUser(email="recipient@example.com")
    create_projection(owner)
    create_projection(recipient)
    owner_client = make_client(auth_registry, owner)
    group_id = owner_client.post("/api/v1/groups/", {"title": "g", "group_type": "GENERAL"}, format="json").json()["id"]
    invite_id = owner_client.post(f"/api/v1/groups/{group_id}/invites/direct/", {"recipient_user_id": recipient.sub}, format="json").json()["id"]

    recipient_client = make_client(auth_registry, recipient)
    assert recipient_client.post(f"/api/v1/group-invitations/{invite_id}/accept/", {}, format="json").status_code == 200
    reject_after_accept = recipient_client.post(f"/api/v1/group-invitations/{invite_id}/reject/", {}, format="json")
    assert reject_after_accept.status_code == 409


@pytest.mark.django_db
def test_my_invitation_pagination_and_swagger(auth_registry):
    owner = FakeUser(email="owner@example.com")
    recipient = FakeUser(email="recipient@example.com")
    create_projection(owner)
    create_projection(recipient)
    owner_client = make_client(auth_registry, owner)
    group_id = owner_client.post("/api/v1/groups/", {"title": "g", "group_type": "GENERAL"}, format="json").json()["id"]
    for _ in range(3):
        invite = owner_client.post(f"/api/v1/groups/{group_id}/invites/direct/", {"recipient_user_id": recipient.sub}, format="json")
        if invite.status_code == 409:
            existing = GroupInvite.objects.filter(group_id=group_id, recipient_user_id=recipient.sub, status="PENDING").order_by("-created_at").first()
            existing.status = "REJECTED"
            existing.save(update_fields=["status", "updated_at"])
            invite = owner_client.post(f"/api/v1/groups/{group_id}/invites/direct/", {"recipient_user_id": recipient.sub}, format="json")
        assert invite.status_code == 201

    recipient_client = make_client(auth_registry, recipient)
    page = recipient_client.get("/api/v1/users/me/group-invitations/", {"page_size": 2})
    assert page.status_code == 200
    assert len(page.json()["results"]) == 2
    assert page.json()["next_cursor"]

    page2 = recipient_client.get("/api/v1/users/me/group-invitations/", {"page_size": 2, "cursor": page.json()["next_cursor"]})
    assert page2.status_code == 200

    schema = recipient_client.get("/api/schema/", {"format": "json"})
    assert schema.status_code == 200
    paths = schema.json()["paths"]
    assert "/api/v1/groups/{group_id}/invites/direct/" in paths
    assert "/api/v1/users/me/group-invitations/" in paths
    assert "/api/v1/group-invitations/{invite_id}/accept/" in paths
