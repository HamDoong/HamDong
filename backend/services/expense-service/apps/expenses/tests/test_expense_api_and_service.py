from dataclasses import dataclass
from types import SimpleNamespace
from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.expenses.application.use_cases import ExpenseService
from apps.expenses.domain.models import Expense, GroupMemberProjection, GroupProjection


pytestmark = pytest.mark.django_db


@dataclass
class AuthUser:
    sub: str

    @property
    def is_authenticated(self):
        return True


class FakePublisher:
    def __init__(self):
        self.events = []

    def publish_event(self, event):
        self.events.append(event)
        return True

    def publish(self, *args):
        if len(args) == 1:
            event = args[0]
        else:
            event_type, data, routing_key = args
            event = {
                "event_type": event_type,
                "data": data,
                "routing_key": routing_key,
            }
        self.events.append(event)
        return True


@pytest.fixture(autouse=True)
def disable_rabbitmq(monkeypatch):
    monkeypatch.setattr(
        "apps.expenses.infrastructure.rabbitmq_publisher.RabbitMQPublisher.publish",
        lambda self, event: True,
    )


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def expense_context():
    group_id = uuid4()
    owner_id = uuid4()
    admin_id = uuid4()
    member_id = uuid4()

    GroupProjection.objects.create(
        group_id=group_id,
        title="Trip group",
        group_type=GroupProjection.TYPE_TRIP,
        status=GroupProjection.STATUS_ACTIVE,
        created_by_user_id=owner_id,
        member_count=3,
    )
    GroupMemberProjection.objects.bulk_create(
        [
            GroupMemberProjection(
                group_id=group_id,
                user_id=owner_id,
                phone_number="+10000000001",
                display_name_snapshot="Owner",
                role=GroupMemberProjection.ROLE_OWNER,
                status=GroupMemberProjection.STATUS_ACTIVE,
            ),
            GroupMemberProjection(
                group_id=group_id,
                user_id=admin_id,
                phone_number="+10000000002",
                display_name_snapshot="Admin",
                role=GroupMemberProjection.ROLE_ADMIN,
                status=GroupMemberProjection.STATUS_ACTIVE,
            ),
            GroupMemberProjection(
                group_id=group_id,
                user_id=member_id,
                phone_number="+10000000003",
                display_name_snapshot="Member",
                role=GroupMemberProjection.ROLE_MEMBER,
                status=GroupMemberProjection.STATUS_ACTIVE,
            ),
        ]
    )
    return {
        "group_id": group_id,
        "owner_id": owner_id,
        "admin_id": admin_id,
        "member_id": member_id,
    }


def build_equal_payload(context):
    return {
        "title": "Lunch",
        "description": "Shared lunch",
        "payer_user_id": str(context["owner_id"]),
        "base_amount_minor": 1000,
        "currency": "IRR",
        "split_method": "EQUAL",
        "participant_user_ids": [str(context["owner_id"]), str(context["member_id"])],
        "tax_type": "PERCENTAGE",
        "tax_percentage": "10.0000",
        "service_fee_type": "FIXED",
        "service_fee_amount_minor": 50,
        "expense_date": timezone.now().isoformat(),
    }


def build_custom_payload(context):
    return {
        "title": "Shopping",
        "description": "Shared shopping",
        "payer_user_id": str(context["owner_id"]),
        "base_amount_minor": 1000,
        "currency": "IRR",
        "split_method": "CUSTOM_AMOUNT",
        "participants": [
            {"user_id": str(context["owner_id"]), "base_share_minor": 700},
            {"user_id": str(context["member_id"]), "base_share_minor": 300},
        ],
        "tax_type": "FIXED",
        "tax_amount_minor": 100,
        "service_fee_type": "PERCENTAGE",
        "service_fee_percentage": "10.0000",
        "expense_date": timezone.now().isoformat(),
    }


def authenticate(client, user_id):
    client.force_authenticate(user=AuthUser(str(user_id)))
    return client


def create_expense_via_service(context, *, publisher=None, creator_id=None):
    service = ExpenseService(publisher=publisher)
    creator_user_id = creator_id or context["owner_id"]
    return service.create_expense(
        context["group_id"],
        AuthUser(str(creator_user_id)),
        {
            "title": "Dinner",
            "description": "Shared dinner",
            "payer_user_id": context["owner_id"],
            "base_amount_minor": 1000,
            "currency": "IRR",
            "split_method": "EQUAL",
            "participant_user_ids": [context["owner_id"], context["member_id"]],
            "tax_type": "PERCENTAGE",
            "tax_percentage": "10.0000",
            "service_fee_type": "FIXED",
            "service_fee_amount_minor": 50,
            "expense_date": timezone.now(),
        },
    )


def test_create_equal_expense_successfully(api_client, expense_context):
    response = authenticate(api_client, expense_context["owner_id"]).post(
        f"/api/v1/groups/{expense_context['group_id']}/expenses/",
        data=build_equal_payload(expense_context),
        format="json",
    )

    assert response.status_code == 201
    assert response.data["base_amount_minor"] == 1000
    assert response.data["tax_amount_minor"] == 100
    assert response.data["service_fee_amount_minor"] == 50
    assert response.data["total_amount_minor"] == 1150
    assert len(response.data["participants"]) == 2


def test_create_custom_amount_expense_successfully(api_client, expense_context):
    response = authenticate(api_client, expense_context["owner_id"]).post(
        f"/api/v1/groups/{expense_context['group_id']}/expenses/",
        data=build_custom_payload(expense_context),
        format="json",
    )

    assert response.status_code == 201
    assert response.data["base_amount_minor"] == 1000
    assert response.data["tax_amount_minor"] == 100
    assert response.data["service_fee_amount_minor"] == 100
    assert response.data["total_amount_minor"] == 1200


def test_create_expense_without_jwt_should_fail(api_client, expense_context):
    response = api_client.post(
        f"/api/v1/groups/{expense_context['group_id']}/expenses/",
        data=build_equal_payload(expense_context),
        format="json",
    )

    assert response.status_code == 401


def test_create_expense_by_non_member_should_fail(api_client, expense_context):
    response = authenticate(api_client, uuid4()).post(
        f"/api/v1/groups/{expense_context['group_id']}/expenses/",
        data=build_equal_payload(expense_context),
        format="json",
    )

    assert response.status_code == 403
    assert response.data["error"]["code"] == "NOT_GROUP_MEMBER"


def test_create_expense_in_archived_group_should_fail(api_client, expense_context):
    group = GroupProjection.objects.get(group_id=expense_context["group_id"])
    group.status = GroupProjection.STATUS_ARCHIVED
    group.save(update_fields=["status"])

    response = authenticate(api_client, expense_context["owner_id"]).post(
        f"/api/v1/groups/{expense_context['group_id']}/expenses/",
        data=build_equal_payload(expense_context),
        format="json",
    )

    assert response.status_code == 400
    assert response.data["error"]["code"] == "GROUP_NOT_ACTIVE"


def test_create_expense_with_payer_not_in_group_should_fail(api_client, expense_context):
    payload = build_equal_payload(expense_context)
    payload["payer_user_id"] = str(uuid4())

    response = authenticate(api_client, expense_context["owner_id"]).post(
        f"/api/v1/groups/{expense_context['group_id']}/expenses/",
        data=payload,
        format="json",
    )

    assert response.status_code == 400
    assert response.data["error"]["code"] == "PAYER_NOT_GROUP_MEMBER"


def test_create_expense_with_participant_not_in_group_should_fail(api_client, expense_context):
    payload = build_equal_payload(expense_context)
    payload["participant_user_ids"] = [str(expense_context["owner_id"]), str(uuid4())]

    response = authenticate(api_client, expense_context["owner_id"]).post(
        f"/api/v1/groups/{expense_context['group_id']}/expenses/",
        data=payload,
        format="json",
    )

    assert response.status_code == 400
    assert response.data["error"]["code"] == "PARTICIPANT_NOT_GROUP_MEMBER"


def test_sum_participant_total_shares_equals_expense_total_amount(expense_context):
    expense = create_expense_via_service(expense_context)
    assert sum(participant.total_share_minor for participant in expense.participants.all()) == expense.total_amount_minor


def test_list_group_expenses_only_for_active_member(api_client, expense_context):
    create_expense_via_service(expense_context)

    allowed = authenticate(api_client, expense_context["member_id"]).get(
        f"/api/v1/groups/{expense_context['group_id']}/expenses/"
    )
    denied = authenticate(APIClient(), uuid4()).get(
        f"/api/v1/groups/{expense_context['group_id']}/expenses/"
    )

    assert allowed.status_code == 200
    assert len(allowed.data) == 1
    assert denied.status_code == 403


def test_expense_detail_only_for_active_member(api_client, expense_context):
    expense = create_expense_via_service(expense_context)

    allowed = authenticate(api_client, expense_context["member_id"]).get(
        f"/api/v1/expenses/{expense.id}/"
    )
    denied = authenticate(APIClient(), uuid4()).get(f"/api/v1/expenses/{expense.id}/")

    assert allowed.status_code == 200
    assert allowed.data["id"] == str(expense.id)
    assert denied.status_code == 403


def test_update_expense_by_creator(api_client, expense_context):
    expense = create_expense_via_service(expense_context)

    response = authenticate(api_client, expense_context["owner_id"]).patch(
        f"/api/v1/expenses/{expense.id}/",
        data={"title": "Dinner updated"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["title"] == "Dinner updated"
    assert response.data["status"] == Expense.STATUS_UPDATED


def test_update_expense_by_group_owner_should_pass(api_client, expense_context):
    expense = create_expense_via_service(expense_context, creator_id=expense_context["member_id"])

    response = authenticate(api_client, expense_context["owner_id"]).patch(
        f"/api/v1/expenses/{expense.id}/",
        data={"title": "Owner updated title"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["title"] == "Owner updated title"


def test_delete_expense_by_creator(api_client, expense_context):
    expense = create_expense_via_service(expense_context)

    response = authenticate(api_client, expense_context["owner_id"]).delete(
        f"/api/v1/expenses/{expense.id}/"
    )

    assert response.status_code == 200
    assert response.data["status"] == Expense.STATUS_DELETED
    assert Expense.objects.get(id=expense.id).status == Expense.STATUS_DELETED


def test_deleted_expense_not_shown_in_active_list(api_client, expense_context):
    expense = create_expense_via_service(expense_context)
    authenticate(api_client, expense_context["owner_id"]).delete(f"/api/v1/expenses/{expense.id}/")

    response = authenticate(APIClient(), expense_context["owner_id"]).get(
        f"/api/v1/groups/{expense_context['group_id']}/expenses/"
    )

    assert response.status_code == 200
    assert response.data == []


def test_expense_created_event_is_created_published(expense_context):
    publisher = FakePublisher()
    expense = create_expense_via_service(expense_context, publisher=publisher)

    assert expense is not None
    assert len(publisher.events) == 1
    event = publisher.events[0]
    assert event["event_type"] == "ExpenseCreated"
    assert event["routing_key"] == "expense.created"


def test_expense_updated_event_is_created_published(expense_context):
    publisher = FakePublisher()
    expense = create_expense_via_service(expense_context, publisher=publisher)
    publisher.events.clear()

    updated = ExpenseService(publisher=publisher).update_expense(
        expense.id,
        AuthUser(str(expense_context["owner_id"])),
        {"title": "Updated from service"},
    )

    assert updated.title == "Updated from service"
    assert len(publisher.events) == 1
    assert publisher.events[0]["event_type"] == "ExpenseUpdated"
    assert publisher.events[0]["routing_key"] == "expense.updated"


def test_expense_deleted_event_is_created_published(expense_context):
    publisher = FakePublisher()
    expense = create_expense_via_service(expense_context, publisher=publisher)
    publisher.events.clear()

    deleted = ExpenseService(publisher=publisher).delete_expense(
        expense.id,
        AuthUser(str(expense_context["owner_id"])),
    )

    assert deleted.status == Expense.STATUS_DELETED
    assert len(publisher.events) == 1
    assert publisher.events[0]["event_type"] == "ExpenseDeleted"
    assert publisher.events[0]["routing_key"] == "expense.deleted"
