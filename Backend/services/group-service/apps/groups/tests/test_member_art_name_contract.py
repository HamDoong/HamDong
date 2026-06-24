import uuid

import pytest
from datetime import timedelta

from django.utils import timezone
from rest_framework import exceptions, status
from rest_framework.test import APIClient

from apps.groups.application.member_display import SAFE_MEMBER_ART_NAME_FALLBACK
from apps.groups.domain.models import Group, GroupInvite, GroupMember, UserProjection
from apps.groups.infrastructure.jwt_authentication import JWTAuthentication
from apps.groups.infrastructure.rabbitmq_publisher import RabbitMQPublisher


class AuthUser:
    def __init__(self, sub=None, email="member@example.com", role="USER", art_name=None):
        self.sub = sub or uuid.uuid4()
        self.id = str(self.sub)
        self.email = email
        self.role = role
        if art_name is not None:
            self.art_name = art_name

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False


@pytest.fixture(autouse=True)
def disable_publishing(monkeypatch):
    monkeypatch.setattr(RabbitMQPublisher, "publish", staticmethod(lambda *args, **kwargs: True))


def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def create_group(owner: AuthUser, *, title="Art Name Group") -> Group:
    return Group.objects.create(
        title=title,
        title_parts=[],
        description="",
        group_type="GENERAL",
        status="ACTIVE",
        created_by_user_id=owner.sub,
        created_by_email=owner.email,
        member_count=1,
    )


def add_member(group: Group, user, *, role="MEMBER", status_value="ACTIVE", art_name_snapshot=None, email=None) -> GroupMember:
    return GroupMember.objects.create(
        group=group,
        user_id=user.sub,
        email=email or user.email,
        art_name_snapshot=art_name_snapshot,
        role=role,
        status=status_value,
    )


def member_by_user_id(payload, user_id):
    return next(item for item in payload if item["user_id"] == str(user_id))


@pytest.mark.django_db
def test_members_list_returns_art_name_contract_from_snapshot():
    owner = AuthUser(email="owner@example.com", art_name="owner_artist")
    target = AuthUser(email="amir@example.com")

    group = create_group(owner)
    add_member(group, owner, role="OWNER", art_name_snapshot="owner_artist")
    add_member(group, target, art_name_snapshot="amir_artist")

    response = auth_client(owner).get(f"/api/v1/groups/{group.id}/members/")

    assert response.status_code == status.HTTP_200_OK
    member = member_by_user_id(response.json(), target.sub)
    assert member["art_name"] == "amir_artist"
    assert member["username"] == "amir_artist"
    assert member["art_name_snapshot"] == "amir_artist"
    assert member["email"] == "am***@example.com"
    assert "display_name" not in member
    assert {"id", "user_id", "role", "joined_at", "art_name", "username", "art_name_snapshot", "email"} <= set(member)


@pytest.mark.django_db
def test_members_list_prefers_projection_over_null_snapshot():
    owner = AuthUser(email="owner@example.com", art_name="owner_artist")
    target = AuthUser(email="amir@example.com")

    group = create_group(owner)
    add_member(group, owner, role="OWNER", art_name_snapshot="owner_artist")
    add_member(group, target, art_name_snapshot=None)
    UserProjection.objects.create(
        identity_user_id=target.sub,
        email=target.email,
        art_name="amir_artist",
    )

    response = auth_client(owner).get(f"/api/v1/groups/{group.id}/members/")

    assert response.status_code == status.HTTP_200_OK
    member = member_by_user_id(response.json(), target.sub)
    assert member["art_name"] == "amir_artist"
    assert member["username"] == "amir_artist"
    assert member["art_name_snapshot"] is None
    assert member["email"] == "am***@example.com"


@pytest.mark.django_db
def test_members_list_uses_safe_fallback_when_projection_and_snapshot_are_missing():
    owner = AuthUser(email="owner@example.com", art_name="owner_artist")
    target = AuthUser(email="fallback@example.com")

    group = create_group(owner)
    add_member(group, owner, role="OWNER", art_name_snapshot="owner_artist")
    add_member(group, target, art_name_snapshot=None, email="fallback@example.com")

    response = auth_client(owner).get(f"/api/v1/groups/{group.id}/members/")

    assert response.status_code == status.HTTP_200_OK
    member = member_by_user_id(response.json(), target.sub)
    assert member["art_name"] == SAFE_MEMBER_ART_NAME_FALLBACK
    assert member["username"] == SAFE_MEMBER_ART_NAME_FALLBACK
    assert member["email"] == "fa***@example.com"


@pytest.mark.django_db
def test_group_creator_snapshot_and_member_response_use_projection_when_jwt_has_no_art_name():
    creator = AuthUser(email="creator@example.com")
    UserProjection.objects.create(
        identity_user_id=creator.sub,
        email=creator.email,
        art_name="creator_artist",
    )
    client = auth_client(creator)

    create_response = client.post("/api/v1/groups/", {"title": "Creator Group", "group_type": "GENERAL"}, format="json")

    assert create_response.status_code == status.HTTP_201_CREATED
    group_id = create_response.json()["id"]

    owner_member = GroupMember.objects.get(group_id=group_id, user_id=creator.sub)
    assert owner_member.role == "OWNER"
    assert owner_member.art_name_snapshot == "creator_artist"

    members_response = client.get(f"/api/v1/groups/{group_id}/members/")
    assert members_response.status_code == status.HTTP_200_OK
    creator_payload = member_by_user_id(members_response.json(), creator.sub)
    assert creator_payload["art_name"] == "creator_artist"
    assert creator_payload["username"] == "creator_artist"
    assert creator_payload["role"] == "OWNER"


@pytest.mark.django_db
def test_invite_accept_uses_projection_when_authenticated_user_has_no_art_name():
    owner = AuthUser(email="owner@example.com", art_name="owner_artist")
    owner_client = auth_client(owner)
    create_response = owner_client.post("/api/v1/groups/", {"title": "Invite Group", "group_type": "GENERAL"}, format="json")
    assert create_response.status_code == status.HTTP_201_CREATED
    group_id = create_response.json()["id"]

    invite_response = owner_client.post(f"/api/v1/groups/{group_id}/invites/", {"max_uses": 2}, format="json")
    assert invite_response.status_code == status.HTTP_201_CREATED
    raw_token = invite_response.json()["invite_url"].rstrip("/").split("/")[-1]

    invited = AuthUser(email="invited@example.com")
    UserProjection.objects.create(
        identity_user_id=invited.sub,
        email=invited.email,
        art_name="invited_artist",
    )
    invited_client = auth_client(invited)

    accept_response = invited_client.post(f"/api/v1/groups/invites/{raw_token}/accept/", format="json")
    assert accept_response.status_code == status.HTTP_200_OK

    invited_member = GroupMember.objects.get(group_id=group_id, user_id=invited.sub)
    assert invited_member.art_name_snapshot == "invited_artist"

    members_response = owner_client.get(f"/api/v1/groups/{group_id}/members/")
    invited_payload = member_by_user_id(members_response.json(), invited.sub)
    assert invited_payload["art_name"] == "invited_artist"
    assert invited_payload["username"] == "invited_artist"
    assert invited_payload["email"] == "in***@example.com"


@pytest.mark.django_db
def test_rejoin_does_not_overwrite_valid_snapshot_with_null():
    import hashlib

    owner = AuthUser(email="owner@example.com", art_name="owner_artist")
    returning_user = AuthUser(email="returning@example.com")

    group = create_group(owner)
    add_member(group, owner, role="OWNER", art_name_snapshot="owner_artist")
    existing_member = add_member(
        group,
        returning_user,
        status_value="LEFT",
        art_name_snapshot="stable_artist",
        email="returning@example.com",
    )
    GroupInvite.objects.create(
        group=group,
        created_by_user_id=owner.sub,
        token_hash=hashlib.sha256(b"token").hexdigest(),
        status="ACTIVE",
        max_uses=2,
        used_count=0,
        expires_at=timezone.now() + timedelta(hours=1),
    )

    response = auth_client(returning_user).post("/api/v1/groups/invites/token/accept/", format="json")

    assert response.status_code == status.HTTP_200_OK
    existing_member.refresh_from_db()
    assert existing_member.art_name_snapshot == "stable_artist"


@pytest.mark.django_db
def test_members_schema_documents_art_name_and_omits_display_name():
    response = APIClient().get("/api/schema/?format=json")

    assert response.status_code == status.HTTP_200_OK
    schema = response.json()
    member_schema = schema["components"]["schemas"]["Member"]
    properties = member_schema["properties"]

    assert "art_name" in properties
    assert "username" in properties
    assert "art_name_snapshot" in properties
    assert "display_name" not in properties


@pytest.mark.django_db
def test_member_listing_permissions_and_authentication_errors(monkeypatch):
    owner = AuthUser(email="owner@example.com", art_name="owner_artist")
    member = AuthUser(email="member@example.com", art_name="member_artist")
    outsider = AuthUser(email="outsider@example.com", art_name="outsider_artist")
    other_group_user = AuthUser(email="other@example.com", art_name="other_artist")

    group = create_group(owner)
    other_group = create_group(other_group_user, title="Other Group")
    add_member(group, owner, role="OWNER", art_name_snapshot="owner_artist")
    add_member(group, member, art_name_snapshot="member_artist")
    add_member(other_group, other_group_user, role="OWNER", art_name_snapshot="other_artist")

    owner_response = auth_client(owner).get(f"/api/v1/groups/{group.id}/members/")
    assert owner_response.status_code == status.HTTP_200_OK

    member_response = auth_client(member).get(f"/api/v1/groups/{group.id}/members/")
    assert member_response.status_code == status.HTTP_200_OK

    outsider_client = auth_client(outsider)
    outsider_response = outsider_client.get(f"/api/v1/groups/{group.id}/members/?user_id={owner.sub}")
    assert outsider_response.status_code == status.HTTP_403_FORBIDDEN
    assert outsider_response.json()["error"]["code"] == "NOT_GROUP_MEMBER"

    other_group_response = auth_client(other_group_user).get(f"/api/v1/groups/{group.id}/members/")
    assert other_group_response.status_code == status.HTTP_403_FORBIDDEN
    assert other_group_response.json()["error"]["code"] == "NOT_GROUP_MEMBER"

    missing_token_response = APIClient().get(f"/api/v1/groups/{group.id}/members/")
    assert missing_token_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert missing_token_response.json()["error"]["code"] == "NOT_AUTHENTICATED"

    def invalid_auth(self, request):
        raise exceptions.AuthenticationFailed({"code": "INVALID_TOKEN", "message": "The provided token is invalid."})

    monkeypatch.setattr(JWTAuthentication, "authenticate", invalid_auth)
    invalid_token_response = APIClient().get(
        f"/api/v1/groups/{group.id}/members/",
        HTTP_AUTHORIZATION="Bearer invalid-token",
    )
    assert invalid_token_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert invalid_token_response.json()["error"]["code"] == "INVALID_TOKEN"

    def expired_auth(self, request):
        raise exceptions.AuthenticationFailed({"code": "TOKEN_EXPIRED", "message": "The provided token has expired."})

    monkeypatch.setattr(JWTAuthentication, "authenticate", expired_auth)
    expired_token_response = APIClient().get(
        f"/api/v1/groups/{group.id}/members/",
        HTTP_AUTHORIZATION="Bearer expired-token",
    )
    assert expired_token_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert expired_token_response.json()["error"]["code"] == "TOKEN_EXPIRED"
