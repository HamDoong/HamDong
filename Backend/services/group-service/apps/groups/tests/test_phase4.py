import uuid

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.groups.domain.models import Group, GroupInvite, GroupMember, UserProjection
from apps.groups.infrastructure.jwt_authentication import JWTAuthentication
from apps.groups.infrastructure.rabbitmq_publisher import RabbitMQPublisher


class FakeUser:
    def __init__(
        self,
        sub=None,
        email="test.user@example.com",
        art_name="test_user",
        role="USER",
    ):
        self.sub = sub or uuid.uuid4()
        self.id = str(self.sub)
        self.email = email
        self.art_name = art_name
        self.role = role
        self.payload = {
            "sub": str(self.sub),
            "email": email,
            "role": role,
        }

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False


@pytest.fixture(autouse=True)
def disable_publishing(monkeypatch):
    calls = []

    def fake_publish(event_type, data, routing_key):
        calls.append((event_type, data, routing_key))
        return True

    monkeypatch.setattr(RabbitMQPublisher, "publish", staticmethod(fake_publish))
    return calls


@pytest.fixture
def api_client(monkeypatch):
    client = APIClient()
    authenticated_user = FakeUser()

    def fake_auth(self, request):
        auth = request.META.get("HTTP_AUTHORIZATION")
        if not auth:
            raise Exception("NOT_AUTHENTICATED")
        return (authenticated_user, None)

    monkeypatch.setattr(JWTAuthentication, "authenticate", fake_auth)
    return client


@pytest.mark.django_db
def test_create_group_with_valid_jwt(api_client):
    client = api_client
    client.credentials(HTTP_AUTHORIZATION="Bearer faketoken")
    resp = client.post("/api/v1/groups/", {"title": "G1", "group_type": "GENERAL"}, format="json")
    assert resp.status_code == status.HTTP_201_CREATED
    data = resp.json()
    assert data["title"] == "G1"
    g = Group.objects.get(id=data["id"])
    assert g.member_count == 1
    assert GroupMember.objects.filter(group=g, role="OWNER").exists()


@pytest.mark.django_db
def test_create_group_without_jwt():
    client = APIClient()
    resp = client.post("/api/v1/groups/", {"title": "G2", "group_type": "GENERAL"}, format="json")
    assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@pytest.mark.django_db
def test_list_my_groups(api_client):
    client = api_client
    client.credentials(HTTP_AUTHORIZATION="Bearer faketoken")
    resp = client.post("/api/v1/groups/", {"title": "ListGroup", "group_type": "GENERAL"}, format="json")
    assert resp.status_code == status.HTTP_201_CREATED
    resp = client.get("/api/v1/groups/")
    assert resp.status_code == 200
    arr = resp.json()
    assert any(g["title"] == "ListGroup" for g in arr)


@pytest.mark.django_db
def test_invite_create_preview_accept_revoke_flow(api_client):
    client = api_client
    client.credentials(HTTP_AUTHORIZATION="Bearer faketoken")
    resp = client.post("/api/v1/groups/", {"title": "InviteGroup", "group_type": "GENERAL"}, format="json")
    gid = resp.json()["id"]

    resp = client.post(f"/api/v1/groups/{gid}/invites/", {"expires_in_hours": 1, "max_uses": 2}, format="json")
    assert resp.status_code == 201
    body = resp.json()
    raw_token = body["invite_url"].rsplit("/", 1)[-1]

    resp = client.get(f"/api/v1/groups/invites/{raw_token}/")
    assert resp.status_code == 200
    assert resp.json()["title"] == "InviteGroup"

    resp = client.post(f"/api/v1/groups/invites/{raw_token}/accept/", format="json")
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "ALREADY_GROUP_MEMBER"

    inv = GroupInvite.objects.filter(group_id=gid).first()
    resp = client.post(f"/api/v1/groups/{gid}/invites/{inv.id}/revoke/", format="json")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_member_list_remove_and_leave(api_client):
    client = api_client
    client.credentials(HTTP_AUTHORIZATION="Bearer faketoken")
    resp = client.post("/api/v1/groups/", {"title": "MembersGroup", "group_type": "GENERAL"}, format="json")
    gid = resp.json()["id"]

    resp = client.get(f"/api/v1/groups/{gid}/members/")
    assert resp.status_code == 200
    arr = resp.json()
    assert len(arr) == 1

    resp = client.post(f"/api/v1/groups/{gid}/leave/", format="json")
    assert resp.status_code in (400, 403)


@pytest.mark.django_db
def test_user_projection_consumer():
    uid = uuid.uuid4()

    UserProjection.objects.create(
        identity_user_id=uid,
        email="projection.user@example.com",
        art_name="projection_user",
    )

    projection = UserProjection.objects.get(identity_user_id=uid)

    assert projection.email == "projection.user@example.com"
    assert projection.art_name == "projection_user"


@pytest.mark.django_db
def test_raw_token_not_stored(api_client):
    client = api_client
    client.credentials(HTTP_AUTHORIZATION="Bearer faketoken")
    resp = client.post("/api/v1/groups/", {"title": "RawTokenGroup", "group_type": "GENERAL"}, format="json")
    gid = resp.json()["id"]
    resp = client.post(f"/api/v1/groups/{gid}/invites/", {"expires_in_hours": 1, "max_uses": 1}, format="json")
    raw = resp.json()["invite_url"].rsplit("/", 1)[-1]
    assert not GroupInvite.objects.filter(token_hash=raw).exists()
