from types import SimpleNamespace
from uuid import uuid4

import pytest

from apps.expenses.application.use_cases import ExpensePermissionError, ExpenseService, ExpenseServiceError
from apps.expenses.domain.models import Expense, GroupMemberProjection, GroupProjection


class FakePublisher:
    def __init__(self):
        self.events = []

    def publish_event(self, event):
        self.events.append(event)
        return True


@pytest.fixture
def group_context(db):
    group_id = uuid4()
    creator_id = uuid4()
    owner_id = uuid4()
    payer_id = uuid4()
    participant_ids = [payer_id, uuid4(), uuid4()]
    group = GroupProjection.objects.create(
        group_id=group_id,
        title="Trip",
        group_type=GroupProjection.TYPE_TRIP,
        status=GroupProjection.STATUS_ACTIVE,
        created_by_user_id=creator_id,
        member_count=4,
    )

    members = {}
    for index, user_id in enumerate([creator_id, owner_id, *participant_ids], start=1):
        members[str(user_id)] = GroupMemberProjection.objects.create(
            group_id=group_id,
            user_id=user_id,
            phone_number=f"+98912000000{index}",
            display_name_snapshot=f"User {index}",
            role=GroupMemberProjection.ROLE_OWNER if user_id == owner_id else GroupMemberProjection.ROLE_MEMBER,
            status=GroupMemberProjection.STATUS_ACTIVE,
        )

    return {
        "group": group,
        "group_id": group_id,
        "creator_id": creator_id,
        "owner_id": owner_id,
        "payer_id": payer_id,
        "participant_ids": participant_ids,
        "members": members,
    }


def user(user_id):
    return SimpleNamespace(sub=str(user_id), is_authenticated=True)


@pytest.mark.django_db
def test_create_equal_expense_successfully(group_context):
    publisher = FakePublisher()
    service = ExpenseService(publisher=publisher)

    expense = service.create_expense(
        group_context["group_id"],
        user(group_context["creator_id"]),
        {
            "title": "شام رستوران",
            "description": "شام جمعه",
            "payer_user_id": group_context["payer_id"],
            "base_amount_minor": 1200000,
            "currency": "IRR",
            "split_method": Expense.SPLIT_EQUAL,
            "participant_user_ids": group_context["participant_ids"],
            "tax_type": Expense.TAX_PERCENTAGE,
            "tax_percentage": "10.00",
            "service_fee_type": Expense.SERVICE_FIXED,
            "service_fee_amount_minor": 50000,
        },
    )

    assert expense.total_amount_minor == 1370000
    assert expense.participants.count() == 3
    assert sum(p.total_share_minor for p in expense.participants.all()) == expense.total_amount_minor
    assert publisher.events[0]["event_type"] == "ExpenseCreated"
    assert publisher.events[0]["routing_key"] == "expense.created"
    assert publisher.events[0]["data"]["base_amount_minor"] == 1200000


@pytest.mark.django_db
def test_create_custom_amount_expense_successfully(group_context):
    publisher = FakePublisher()
    service = ExpenseService(publisher=publisher)
    participant_ids = group_context["participant_ids"]

    expense = service.create_expense(
        group_context["group_id"],
        user(group_context["creator_id"]),
        {
            "title": "خرید مشترک",
            "payer_user_id": group_context["payer_id"],
            "base_amount_minor": 1000000,
            "currency": "IRR",
            "split_method": Expense.SPLIT_CUSTOM,
            "participants": [
                {"user_id": participant_ids[0], "base_share_minor": 400000},
                {"user_id": participant_ids[1], "base_share_minor": 300000},
                {"user_id": participant_ids[2], "base_share_minor": 300000},
            ],
            "tax_type": Expense.TAX_FIXED,
            "tax_amount_minor": 100000,
            "service_fee_type": Expense.SERVICE_NONE,
        },
    )

    assert expense.base_amount_minor == 1000000
    assert expense.tax_amount_minor == 100000
    assert expense.service_fee_amount_minor == 0
    assert sum(p.total_share_minor for p in expense.participants.all()) == 1100000


@pytest.mark.django_db
def test_create_expense_by_non_member_should_fail(group_context):
    service = ExpenseService(publisher=FakePublisher())

    with pytest.raises(ExpensePermissionError, match="NOT_GROUP_MEMBER"):
        service.create_expense(
            group_context["group_id"],
            user(uuid4()),
            {
                "title": "Dinner",
                "payer_user_id": group_context["payer_id"],
                "base_amount_minor": 100000,
                "currency": "IRR",
                "split_method": Expense.SPLIT_EQUAL,
                "participant_user_ids": group_context["participant_ids"],
            },
        )


@pytest.mark.django_db
def test_create_expense_in_archived_group_should_fail(group_context):
    group_context["group"].status = GroupProjection.STATUS_ARCHIVED
    group_context["group"].save(update_fields=["status"])
    service = ExpenseService(publisher=FakePublisher())

    with pytest.raises(ExpenseServiceError, match="GROUP_NOT_ACTIVE"):
        service.create_expense(
            group_context["group_id"],
            user(group_context["creator_id"]),
            {
                "title": "Dinner",
                "payer_user_id": group_context["payer_id"],
                "base_amount_minor": 100000,
                "currency": "IRR",
                "split_method": Expense.SPLIT_EQUAL,
                "participant_user_ids": group_context["participant_ids"],
            },
        )


@pytest.mark.django_db
def test_create_expense_with_payer_not_in_group_should_fail(group_context):
    service = ExpenseService(publisher=FakePublisher())

    with pytest.raises(ExpenseServiceError, match="PAYER_NOT_GROUP_MEMBER"):
        service.create_expense(
            group_context["group_id"],
            user(group_context["creator_id"]),
            {
                "title": "Dinner",
                "payer_user_id": uuid4(),
                "base_amount_minor": 100000,
                "currency": "IRR",
                "split_method": Expense.SPLIT_EQUAL,
                "participant_user_ids": group_context["participant_ids"],
            },
        )


@pytest.mark.django_db
def test_create_expense_with_participant_not_in_group_should_fail(group_context):
    service = ExpenseService(publisher=FakePublisher())

    with pytest.raises(ExpenseServiceError, match="PARTICIPANT_NOT_GROUP_MEMBER"):
        service.create_expense(
            group_context["group_id"],
            user(group_context["creator_id"]),
            {
                "title": "Dinner",
                "payer_user_id": group_context["payer_id"],
                "base_amount_minor": 100000,
                "currency": "IRR",
                "split_method": Expense.SPLIT_EQUAL,
                "participant_user_ids": [group_context["payer_id"], uuid4()],
            },
        )


@pytest.mark.django_db
def test_custom_split_sum_mismatch_should_fail(group_context):
    service = ExpenseService(publisher=FakePublisher())
    participant_ids = group_context["participant_ids"]

    with pytest.raises(ExpenseServiceError, match="INVALID_SPLIT_AMOUNT"):
        service.create_expense(
            group_context["group_id"],
            user(group_context["creator_id"]),
            {
                "title": "Groceries",
                "payer_user_id": group_context["payer_id"],
                "base_amount_minor": 1000000,
                "currency": "IRR",
                "split_method": Expense.SPLIT_CUSTOM,
                "participants": [
                    {"user_id": participant_ids[0], "base_share_minor": 400000},
                    {"user_id": participant_ids[1], "base_share_minor": 300000},
                ],
            },
        )


@pytest.mark.django_db
def test_list_detail_update_delete_authorization_and_events(group_context):
    publisher = FakePublisher()
    service = ExpenseService(publisher=publisher)
    expense = service.create_expense(
        group_context["group_id"],
        user(group_context["creator_id"]),
        {
            "title": "Dinner",
            "payer_user_id": group_context["payer_id"],
            "base_amount_minor": 900000,
            "currency": "IRR",
            "split_method": Expense.SPLIT_EQUAL,
            "participant_user_ids": group_context["participant_ids"],
        },
    )

    assert service.list_expenses(group_context["group_id"], user(group_context["creator_id"]))
    assert service.get_expense(expense.id, user(group_context["creator_id"])).id == expense.id

    updated = service.update_expense(expense.id, user(group_context["owner_id"]), {"title": "Updated dinner"})
    assert updated.title == "Updated dinner"
    assert publisher.events[-1]["event_type"] == "ExpenseUpdated"

    deleted = service.delete_expense(expense.id, user(group_context["creator_id"]))
    assert deleted.status == Expense.STATUS_DELETED
    assert publisher.events[-1]["event_type"] == "ExpenseDeleted"
    assert service.list_expenses(group_context["group_id"], user(group_context["creator_id"])) == []
