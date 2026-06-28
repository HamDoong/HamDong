from __future__ import annotations

import uuid
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.identity.application.token_service import TokenService
from apps.identity.domain.models import User


class UserSearchApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.token_service = TokenService()
        self.url = "/api/v1/users/search/"
        self.current_user = User.objects.create(
            email="current@example.com",
            art_name="amir_current",
            avatar_url="https://example.com/current.png",
        )

    def auth(self, user: User | None = None) -> None:
        access_token, _, _ = self.token_service.generate_tokens(
            user or self.current_user
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

    def test_search_requires_authentication(self):
        response = self.client.get(self.url, {"art_name": "amir"})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.json()["error"]["code"], "NOT_AUTHENTICATED")

    def test_search_matches_case_insensitive_contains_and_excludes_current_user_by_default(
        self,
    ):
        matched_user = User.objects.create(
            email="artist@example.com",
            art_name="Amir_Art",
            avatar_url="https://example.com/avatar.png",
        )
        User.objects.create(email="other@example.com", art_name="navid_music")

        self.auth()
        response = self.client.get(self.url, {"art_name": "amir"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["query"], "amir")
        self.assertEqual(payload["items"][0]["user_id"], str(matched_user.id))
        self.assertEqual(payload["items"][0]["art_name"], "Amir_Art")
        self.assertEqual(
            payload["items"][0]["avatar_url"], "https://example.com/avatar.png"
        )
        returned_ids = {item["user_id"] for item in payload["items"]}
        self.assertNotIn(str(self.current_user.id), returned_ids)

    def test_search_can_include_current_user_when_exclude_me_is_false(self):
        self.auth()
        response = self.client.get(
            self.url, {"art_name": "amir", "exclude_me": "false"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item["user_id"] for item in response.json()["items"]}
        self.assertIn(str(self.current_user.id), returned_ids)

    def test_search_orders_exact_match_before_prefix_and_contains(self):
        contains_user = User.objects.create(
            email="contains@example.com", art_name="the_amir_artist"
        )
        prefix_user = User.objects.create(
            email="prefix@example.com", art_name="amir_art"
        )
        exact_user = User.objects.create(email="exact@example.com", art_name="amir")

        now = timezone.now()
        User.objects.filter(id=contains_user.id).update(
            created_at=now - timedelta(days=1)
        )
        User.objects.filter(id=prefix_user.id).update(
            created_at=now - timedelta(days=2)
        )
        User.objects.filter(id=exact_user.id).update(created_at=now - timedelta(days=3))

        self.auth()
        response = self.client.get(self.url, {"art_name": "amir", "exclude_me": "true"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ordered_ids = [item["user_id"] for item in response.json()["items"][:3]]
        self.assertEqual(
            ordered_ids,
            [str(exact_user.id), str(prefix_user.id), str(contains_user.id)],
        )

    def test_search_excludes_inactive_and_deleted_users(self):
        active_user = User.objects.create(
            email="active@example.com", art_name="amir_active"
        )
        User.objects.create(
            email="inactive@example.com", art_name="amir_inactive", is_active=False
        )
        User.objects.create(
            email="deleted@example.com",
            art_name="amir_deleted",
            deleted_at=timezone.now(),
        )

        self.auth()
        response = self.client.get(self.url, {"art_name": "amir", "exclude_me": "true"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        returned_ids = {item["user_id"] for item in payload["items"]}
        self.assertIn(str(active_user.id), returned_ids)
        self.assertEqual(len(returned_ids), 1)

    def test_search_returns_empty_collection_when_no_results(self):
        self.auth()
        response = self.client.get(self.url, {"art_name": "notfound"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(), {"items": [], "count": 0, "query": "notfound"}
        )

    def test_search_enforces_limit(self):
        for index in range(3):
            User.objects.create(
                email=f"match-{index}@example.com", art_name=f"amir_result_{index}"
            )

        self.auth()
        response = self.client.get(
            self.url, {"art_name": "amir", "limit": 2, "exclude_me": "true"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["items"]), 2)

    def test_search_validates_required_query_length_and_limit(self):
        self.auth()

        missing_query = self.client.get(self.url)
        self.assertEqual(missing_query.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            missing_query.json()["error"]["code"], "ART_NAME_QUERY_REQUIRED"
        )

        short_query = self.client.get(self.url, {"art_name": "a"})
        self.assertEqual(short_query.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            short_query.json()["error"]["code"], "ART_NAME_QUERY_TOO_SHORT"
        )

        long_query = self.client.get(self.url, {"art_name": "a" * 51})
        self.assertEqual(long_query.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(long_query.json()["error"]["code"], "ART_NAME_QUERY_TOO_LONG")

        invalid_limit = self.client.get(self.url, {"art_name": "amir", "limit": 500})
        self.assertEqual(invalid_limit.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(invalid_limit.json()["error"]["code"], "INVALID_LIMIT")

    def test_search_response_hides_sensitive_fields(self):
        User.objects.create(
            email="private@example.com",
            art_name="amir_private",
            phone_number="+989123456789",
            city="Tehran",
            bio="Hidden bio",
        )

        self.auth()
        response = self.client.get(self.url, {"art_name": "amir", "exclude_me": "true"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = response.json()["items"][0]
        for forbidden_field in {
            "email",
            "phone_number",
            "password_hash",
            "date_of_birth",
            "city",
            "bio",
            "bank_cards",
            "roles",
            "refresh_tokens",
            "security_events",
            "display_name",
        }:
            self.assertNotIn(forbidden_field, item)


class PublicUserLookupApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.token_service = TokenService()
        self.viewer = User.objects.create(
            email="viewer@example.com", art_name="viewer_user"
        )

    def auth(self) -> None:
        access_token, _, _ = self.token_service.generate_tokens(self.viewer)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

    def test_public_lookup_requires_authentication(self):
        target = User.objects.create(
            email="artist@example.com", art_name="navid_artist"
        )

        response = self.client.get(f"/api/v1/users/{target.id}/public/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.json()["error"]["code"], "NOT_AUTHENTICATED")

    def test_public_lookup_returns_public_safe_fields_for_active_user(self):
        target = User.objects.create(
            email="artist@example.com",
            art_name="navid_artist",
            avatar_url="https://example.com/avatar.png",
            phone_number="+989123456789",
            city="Tehran",
            bio="Private bio",
        )

        self.auth()
        response = self.client.get(f"/api/v1/users/{target.id}/public/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertEqual(payload["user_id"], str(target.id))
        self.assertEqual(payload["art_name"], "navid_artist")
        self.assertEqual(payload["avatar_url"], "https://example.com/avatar.png")
        self.assertIs(payload["is_active"], True)
        for forbidden_field in {
            "email",
            "phone_number",
            "date_of_birth",
            "city",
            "bio",
            "password_hash",
            "bank_cards",
            "roles",
            "refresh_tokens",
            "security_events",
            "display_name",
        }:
            self.assertNotIn(forbidden_field, payload)

    def test_public_lookup_rejects_invalid_uuid(self):
        self.auth()
        response = self.client.get("/api/v1/users/not-a-uuid/public/")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"]["code"], "INVALID_USER_ID")

    def test_public_lookup_returns_not_found_for_missing_inactive_or_deleted_users(
        self,
    ):
        inactive_user = User.objects.create(
            email="inactive@example.com", art_name="inactive_artist", is_active=False
        )
        deleted_user = User.objects.create(
            email="deleted@example.com",
            art_name="deleted_artist",
            deleted_at=timezone.now(),
        )

        self.auth()

        missing_response = self.client.get(f"/api/v1/users/{uuid.uuid4()}/public/")
        self.assertEqual(missing_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(missing_response.json()["error"]["code"], "USER_NOT_FOUND")

        inactive_response = self.client.get(f"/api/v1/users/{inactive_user.id}/public/")
        self.assertEqual(inactive_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(inactive_response.json()["error"]["code"], "USER_NOT_FOUND")

        deleted_response = self.client.get(f"/api/v1/users/{deleted_user.id}/public/")
        self.assertEqual(deleted_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(deleted_response.json()["error"]["code"], "USER_NOT_FOUND")


class UserSearchAndLookupSwaggerTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_schema_includes_user_search_and_public_lookup_paths(self):
        response = self.client.get("/api/schema/?format=json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        paths = payload["paths"]

        self.assertIn("/api/v1/users/search/", paths)
        self.assertIn("/api/v1/users/{user_id}/public/", paths)

        search_get = paths["/api/v1/users/search/"]["get"]
        public_get = paths["/api/v1/users/{user_id}/public/"]["get"]

        search_params = {parameter["name"] for parameter in search_get["parameters"]}
        self.assertTrue({"art_name", "limit", "exclude_me"}.issubset(search_params))
        self.assertTrue(search_get.get("security"))
        self.assertTrue(public_get.get("security"))

        public_params = {parameter["name"] for parameter in public_get["parameters"]}
        self.assertIn("user_id", public_params)

        schemas = payload["components"]["schemas"]
        self.assertEqual(
            set(schemas["UserSearchResult"]["properties"].keys()),
            {"user_id", "art_name", "avatar_url"},
        )
        self.assertEqual(
            set(schemas["PublicUser"]["properties"].keys()),
            {"user_id", "art_name", "avatar_url", "is_active"},
        )
