import json
import re
from pathlib import Path

import jsonschema


REPO_ROOT = Path(__file__).resolve().parents[1]


def read(*parts: str) -> str:
    return (REPO_ROOT.joinpath(*parts)).read_text(encoding="utf-8")


def load_json(*parts: str) -> dict:
    return json.loads(read(*parts))


def test_event_envelope_schema_accepts_valid_payload():
    schema = load_json("shared", "contracts", "schemas", "event_envelope.schema.json")
    payload = {
        "event_id": "91efe947-ca4e-4520-8db0-71fcc2854fcd",
        "event_type": "ExpenseCreated",
        "event_version": 1,
        "occurred_at": "2026-06-03T10:00:00Z",
        "source_service": "expense-service",
        "correlation_id": "91efe947-ca4e-4520-8db0-71fcc2854fce",
        "causation_id": "91efe947-ca4e-4520-8db0-71fcc2854fcf",
        "routing_key": "expense.created",
        "data": {"expense_id": "abc"},
    }
    jsonschema.validate(payload, schema)


def test_event_envelope_schema_rejects_invalid_payloads():
    schema = load_json("shared", "contracts", "schemas", "event_envelope.schema.json")
    invalid_payloads = [
        {
            "event_type": "ExpenseCreated",
            "event_version": 1,
            "occurred_at": "2026-06-03T10:00:00Z",
            "source_service": "expense-service",
            "correlation_id": "91efe947-ca4e-4520-8db0-71fcc2854fce",
            "causation_id": "91efe947-ca4e-4520-8db0-71fcc2854fcf",
            "routing_key": "expense.created",
            "data": {},
        },
        {
            "event_id": "91efe947-ca4e-4520-8db0-71fcc2854fcd",
            "event_type": "ExpenseCreated",
            "event_version": 0,
            "occurred_at": "2026-06-03T10:00:00Z",
            "source_service": "expense-service",
            "correlation_id": "91efe947-ca4e-4520-8db0-71fcc2854fce",
            "causation_id": "91efe947-ca4e-4520-8db0-71fcc2854fcf",
            "routing_key": "expense.created",
            "data": {},
        },
        {
            "event_id": "91efe947-ca4e-4520-8db0-71fcc2854fcd",
            "event_type": "ExpenseCreated",
            "event_version": 1,
            "occurred_at": "2026-06-03T10:00:00Z",
            "source_service": "expense-service",
            "correlation_id": "91efe947-ca4e-4520-8db0-71fcc2854fce",
            "causation_id": "91efe947-ca4e-4520-8db0-71fcc2854fcf",
            "routing_key": "expense.created",
        },
    ]
    for payload in invalid_payloads:
        try:
            jsonschema.validate(payload, schema)
        except jsonschema.ValidationError:
            pass
        else:
            raise AssertionError(f"Payload should be invalid: {payload}")


def test_contract_files_exist_and_are_not_decorative():
    contracts_dir = REPO_ROOT / "shared" / "contracts" / "events"
    expected = {
        "identity.events.json",
        "group.events.json",
        "expense.events.json",
        "media.events.json",
        "settlement.events.json",
        "notification.events.json",
    }
    actual = {path.name for path in contracts_dir.glob("*.json")}
    assert expected <= actual
    for name in expected:
        payload = json.loads((contracts_dir / name).read_text(encoding="utf-8"))
        assert payload["events"], f"{name} has no events"
        for event in payload["events"]:
            assert event["event_type"]
            assert event["routing_key"]
            assert event["payload_keys"]


def test_settlement_and_group_contracts_match_real_routing_keys():
    settlement_contract = load_json("shared", "contracts", "events", "settlement.events.json")
    group_contract = load_json("shared", "contracts", "events", "group.events.json")
    settlement_keys = {entry["routing_key"] for entry in settlement_contract["events"]}
    group_keys = {entry["routing_key"] for entry in group_contract["events"]}

    settlement_code = "\n".join(
        [
            read("services", "settlement-service", "apps", "settlements", "application", "debt_service.py"),
            read("services", "settlement-service", "apps", "settlements", "application", "settlement_service.py"),
            read("services", "settlement-service", "apps", "settlements", "application", "settlement_plan_service.py"),
            read("services", "settlement-service", "apps", "settlements", "infrastructure", "reminder_scheduler.py"),
        ]
    )
    group_code = read("services", "group-service", "apps", "groups", "application", "use_cases.py")

    for routing_key in [
        "settlement.created",
        "settlement.confirmed",
        "settlement.rejected",
        "settlement.cancelled",
        "settlement.balance_recalculated",
        "settlement.debt_ledger_updated",
        "settlement.plan.generated",
        "settlement.plan.activated",
        "settlement.plan.cancelled",
        "settlement.plan.expired",
        "settlement.plan.completed",
        "settlement.plan_item.reported",
        "settlement.plan_item.confirmed",
        "settlement.plan_item.rejected",
        "settlement.payment_reminder.requested",
        "settlement.confirmation_reminder.requested",
        "settlement.plan_item_reminder.requested",
    ]:
        assert routing_key in settlement_keys
        assert routing_key in settlement_code

    for routing_key in [
        "group.created",
        "group.updated",
        "group.archived",
        "group.invite.created",
        "group.invite.accepted",
        "group.invite.revoked",
        "group.member.joined",
        "group.member.removed",
        "group.member.left",
    ]:
        assert routing_key in group_keys
        assert routing_key in group_code


def test_outbox_dispatchers_and_inbox_models_exist_for_phase9_services():
    producer_services = {
        "identity-service": ("identity", False),
        "group-service": ("groups", True),
        "expense-service": ("expenses", True),
        "media-service": ("media_files", True),
        "settlement-service": ("settlements", True),
        "notification-service": ("notifications", True),
    }
    for service, (app_name, has_inbox) in producer_services.items():
        service_root = REPO_ROOT / "services" / service / "apps" / app_name
        model_text = (service_root / "domain" / "models.py").read_text(encoding="utf-8")
        assert "class OutboxMessage" in model_text
        command_text = (service_root / "management" / "commands" / "dispatch_outbox.py").read_text(encoding="utf-8")
        assert "OutboxDispatcher" in command_text
        assert "dispatch()" in command_text
        dispatcher_text = (service_root / "infrastructure" / "outbox_dispatcher.py").read_text(encoding="utf-8")
        assert "mark_published" in dispatcher_text
        assert "mark_failed" in dispatcher_text
        if has_inbox:
            assert ("class InboxMessage" in model_text) or ("class ProcessedEvent" in model_text)


def test_notification_consumer_and_scheduler_are_wired_for_reminders():
    scheduler = read("services", "settlement-service", "apps", "settlements", "infrastructure", "reminder_scheduler.py")
    consumer = read("services", "notification-service", "apps", "notifications", "infrastructure", "reminder_consumer.py")
    assert "PaymentReminderRequested" in scheduler
    assert "SettlementConfirmationReminderRequested" in scheduler
    assert "SettlementPlanItemReminderRequested" in scheduler
    assert "create_notification_job" in consumer
    assert "SmsService" in consumer
    assert "InboxRepository" in consumer


def test_docker_compose_contains_phase9_workers():
    docker_compose = read("docker-compose.yml")
    for service_name in [
        "identity-outbox-dispatcher:",
        "group-outbox-dispatcher:",
        "expense-outbox-dispatcher:",
        "media-outbox-dispatcher:",
        "settlement-outbox-dispatcher:",
        "notification-outbox-dispatcher:",
        "settlement-reminder-scheduler:",
        "notification-reminder-consumer:",
    ]:
        assert service_name in docker_compose


def test_no_build_helper_file_was_added():
    assert not (REPO_ROOT / ("Make" + "file")).exists()


def test_notification_templates_and_retry_env_are_configured():
    env_example = read(".env.example")
    for key in [
        "SMS_TEMPLATE_PAYMENT_REMINDER",
        "SMS_TEMPLATE_SETTLEMENT_CONFIRMATION_REMINDER",
        "SMS_TEMPLATE_PLAN_ITEM_REMINDER",
        "EVENT_MAX_RETRY_COUNT",
        "EVENT_RETRY_DELAY_SECONDS",
        "REMINDER_SCHEDULER_INTERVAL_SECONDS",
    ]:
        assert f"{key}=" in env_example

    template_service = read(
        "services",
        "notification-service",
        "apps",
        "notifications",
        "application",
        "template_service.py",
    )
    assert "PAYMENT_REMINDER" in template_service
    assert "SETTLEMENT_CONFIRMATION_REMINDER" in template_service
    assert "PLAN_ITEM_REMINDER" in template_service

    consumer = read(
        "services",
        "notification-service",
        "apps",
        "notifications",
        "infrastructure",
        "reminder_consumer.py",
    )
    assert "render_reminder_message(reminder_type, context)" in consumer

    settlement_settings = read(
        "services",
        "settlement-service",
        "config",
        "settings",
        "base.py",
    )
    assert "REMINDER_SCHEDULER_INTERVAL_SECONDS" in settlement_settings

    docker_compose = read("docker-compose.yml")
    assert "${EVENT_OUTBOX_POLL_INTERVAL_SECONDS:-5}" in docker_compose
    assert "${REMINDER_SCHEDULER_INTERVAL_SECONDS:-3600}" in docker_compose


def test_outbox_repositories_use_configurable_retry_policy():
    for rel in [
        ("services", "identity-service", "apps", "identity", "infrastructure", "repositories.py"),
        ("services", "group-service", "apps", "groups", "infrastructure", "repositories.py"),
        ("services", "expense-service", "apps", "expenses", "infrastructure", "repositories.py"),
        ("services", "media-service", "apps", "media_files", "infrastructure", "repositories.py"),
        ("services", "notification-service", "apps", "notifications", "infrastructure", "repositories.py"),
    ]:
        text = read(*rel)
        assert "EVENT_MAX_RETRY_COUNT" in text
        assert "EVENT_RETRY_DELAY_SECONDS" in text
        assert "available_at" in text


def test_phase9_env_defaults_match_fix_pack_requirements():
    for rel in [".env.example", "backend/.env.example"]:
        text = (REPO_ROOT.parent / rel).read_text(encoding="utf-8")
        assert "EVENT_OUTBOX_BATCH_SIZE=50" in text
        assert "EVENT_OUTBOX_POLL_INTERVAL_SECONDS=5" in text
        assert "EVENT_MAX_RETRY_COUNT=5" in text
        assert "EVENT_RETRY_DELAY_SECONDS=10,30,60" in text
        assert "EVENT_DLQ_SUFFIX=.dlq" in text
        assert "REMINDER_ENABLED=true" in text
        assert "REMINDER_MIN_INTERVAL_HOURS=24" in text
        assert "REMINDER_SCHEDULER_INTERVAL_SECONDS=3600" in text
        assert "PAYMENT_REMINDER_MIN_AMOUNT_MINOR=1000" in text
        assert "PENDING_SETTLEMENT_REMINDER_AFTER_HOURS=24" in text
        assert "PLAN_ITEM_REMINDER_AFTER_HOURS=24" in text
        assert "NOTIFICATION_REMINDER_QUEUE=notification.reminders" in text
        assert "SETTLEMENT_REMINDER_EXCHANGE=hamdong.settlement" in text


def test_phase9_compose_defaults_match_fix_pack_requirements():
    backend_compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "${EVENT_OUTBOX_BATCH_SIZE:-50}" in backend_compose
    assert "${EVENT_OUTBOX_POLL_INTERVAL_SECONDS:-5}" in backend_compose
    assert "${EVENT_RETRY_DELAY_SECONDS:-10,30,60}" in backend_compose
    assert "NOTIFICATION_REMINDER_QUEUE: ${NOTIFICATION_REMINDER_QUEUE:-notification.reminders}" in backend_compose

    repo_compose = (REPO_ROOT.parent / "docker-compose.yml").read_text(encoding="utf-8")
    assert "${EVENT_OUTBOX_BATCH_SIZE:-50}" in repo_compose
    assert "${EVENT_RETRY_DELAY_SECONDS:-10,30,60}" in repo_compose
    assert "NOTIFICATION_REMINDER_QUEUE: ${NOTIFICATION_REMINDER_QUEUE:-notification.reminders}" in repo_compose
