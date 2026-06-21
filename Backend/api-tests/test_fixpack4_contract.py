from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_gateway_nested_routes_come_before_groups_route():
    content = (ROOT / "api-gateway" / "nginx.conf").read_text()
    groups_index = content.index("location /api/v1/groups/")
    for needle in [
        "location ~ ^/api/v1/groups/[^/]+/expenses(/|$)",
        "location ~ ^/api/v1/groups/[^/]+/media(/|$)",
        "location ~ ^/api/v1/groups/[^/]+/(balances|debts|settlements|settlement-plan)(/|$)",
    ]:
        assert content.index(needle) < groups_index


def test_gateway_broad_routes_exist():
    content = (ROOT / "api-gateway" / "nginx.conf").read_text()
    for needle in [
        "location /api/v1/auth/",
        "location /api/v1/users/",
        "location /api/v1/groups/",
        "location /api/v1/notifications/",
    ]:
        assert needle in content


def test_identity_http_contains_password_flow():
    content = (ROOT / "api-tests" / "identity.http").read_text()
    for needle in [
        "/api/v1/auth/password/login/",
        "/api/v1/auth/password/set/",
        "/api/v1/auth/password/change/",
        '"art_name": "{{artName}}"',
    ]:
        assert needle in content


def test_group_http_contains_restore_delete_and_title_parts():
    content = (ROOT / "api-tests" / "group.http").read_text()
    for needle in [
        "/restore/",
        "DELETE {{baseUrl}}/api/v1/groups/{{groupId}}/",
        '"title_parts": ["سفر", "شمال", "تابستان"]',
    ]:
        assert needle in content


def test_notification_http_contains_crud_flow():
    content = (ROOT / "api-tests" / "notification.http").read_text()
    for needle in [
        "POST {{baseUrl}}/api/v1/notifications/",
        "GET {{baseUrl}}/api/v1/notifications/{{notificationId}}/",
        "PATCH {{baseUrl}}/api/v1/notifications/{{notificationId}}/",
        "DELETE {{baseUrl}}/api/v1/notifications/{{notificationId}}/",
    ]:
        assert needle in content


def test_new_end_to_end_http_file_exists_and_updates_second_invite_token():
    content = (ROOT / "api-tests" / "new-auth-group-notification.http").read_text()
    for needle in [
        "Request OTP for Ali",
        "Password login for Ali",
        "Restore group",
        "Create notification",
        "inviteUrl2",
        'client.global.set("inviteToken", inviteUrl2.split("/").pop())',
    ]:
        assert needle in content


def test_no_makefile_or_shell_entrypoint_introduced():
    project_root = ROOT.parent
    assert not (project_root / "Makefile").exists()
    compose = (project_root / "docker-compose.yml").read_text()
    assert '["sh", "-c",' not in compose
    assert "entrypoint.sh" not in compose
