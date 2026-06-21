import uuid

import pytest
from rest_framework.test import APIClient

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


@pytest.fixture(autouse=True)
def disable_publishing(monkeypatch):
    calls = []

    def fake_publish(event_type, data, routing_key):
        calls.append((event_type, data, routing_key))
        return True

    monkeypatch.setattr(RabbitMQPublisher, "publish", staticmethod(fake_publish))
    return calls


def auth_client(monkeypatch, user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
def test_restore_and_delete_group(monkeypatch, disable_publishing):
    owner = FakeUser()
    client = auth_client(monkeypatch, owner)
    response = client.post("/api/v1/groups/", {"title": "شام جمعه", "group_type": "EVENT"}, format="json")
    group_id = response.json()["id"]

    archive = client.post(f"/api/v1/groups/{group_id}/archive/", format="json")
    assert archive.status_code == 200

    restore = client.post(f"/api/v1/groups/{group_id}/restore/", format="json")
    assert restore.status_code == 200
    assert restore.json()["status"] == "ACTIVE"

    delete = client.delete(f"/api/v1/groups/{group_id}/")
    assert delete.status_code == 200

    listing = client.get("/api/v1/groups/")
    assert all(item["id"] != group_id for item in listing.json())
    assert any(call[0] == "GroupRestored" for call in disable_publishing)
    assert any(call[0] == "GroupDeleted" for call in disable_publishing)


@pytest.mark.django_db
def test_title_parts_and_removed_member_requires_new_invite(monkeypatch):
    owner = FakeUser()
    owner_client = auth_client(monkeypatch, owner)
    response = owner_client.post("/api/v1/groups/", {"title_parts": ["سفر", "شمال", "تابستان"], "group_type": "TRIP"}, format="json")
    assert response.status_code == 201
    group_id = response.json()["id"]
    assert response.json()["display_title"] == "سفر شمال تابستان"

    patch = owner_client.patch(f"/api/v1/groups/{group_id}/", {"title_parts": ["شام", "جمعه", "دوستان"]}, format="json")
    assert patch.status_code == 200
    assert patch.json()["title"] == "شام جمعه دوستان"
    assert patch.json()["display_title"] == "شام جمعه دوستان"

    invite = owner_client.post(f"/api/v1/groups/{group_id}/invites/", {"max_uses": 3}, format="json")
    token = invite.json()["invite_url"].rstrip("/").split("/")[-1]

    removed_user = FakeUser(sub=uuid.uuid4(), email="removed.user@example.com", art_name="removed_user")
    removed_client = auth_client(monkeypatch, removed_user)
    first_accept = removed_client.post(f"/api/v1/groups/invites/{token}/accept/", format="json")
    assert first_accept.status_code == 200

    member_id = first_accept.json()["member_id"]
    remove = owner_client.post(f"/api/v1/groups/{group_id}/members/{member_id}/remove/", format="json")
    assert remove.status_code == 200

    second_accept_same = removed_client.post(f"/api/v1/groups/invites/{token}/accept/", format="json")
    assert second_accept_same.status_code == 409
    assert second_accept_same.json()["error"]["code"] == "NEW_INVITE_REQUIRED"

    invite2 = owner_client.post(f"/api/v1/groups/{group_id}/invites/", {"max_uses": 3}, format="json")
    token2 = invite2.json()["invite_url"].rstrip("/").split("/")[-1]
    second_accept = removed_client.post(f"/api/v1/groups/invites/{token2}/accept/", format="json")
    assert second_accept.status_code == 200
    assert second_accept.json()["status"] == "ACTIVE"
