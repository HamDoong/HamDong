"""Template rendering for notification-service."""

from __future__ import annotations

from django.conf import settings

from apps.notifications.infrastructure.repositories import NotificationRepository


class TemplateService:
    def __init__(self):
        self.repository = NotificationRepository()

    def ensure_default_otp_template(self):
        return self.repository.ensure_template(
            code=settings.EMAIL_TEMPLATE_OTP_LOGIN,
            title="HamDong login code",
            body=(
                "HamDong login verification\n\n"
                "Your one-time code is: {code}\n"
                "This code is valid for {expires_in} seconds.\n"
                "Do not share this code with anyone."
            ),
        )

    def ensure_default_reminder_templates(self) -> dict[str, object]:
        templates = {
            "PAYMENT_REMINDER": self.repository.ensure_template(
                code=settings.EMAIL_TEMPLATE_PAYMENT_REMINDER,
                title="HamDong payment reminder",
                body=(
                    "HamDong payment reminder\n\n"
                    "Group: {group_title}\n"
                    "Amount due: {amount} {currency}\n"
                    "Please settle your balance when possible."
                ),
            ),
            "SETTLEMENT_CONFIRMATION_REMINDER": self.repository.ensure_template(
                code=settings.EMAIL_TEMPLATE_SETTLEMENT_CONFIRMATION_REMINDER,
                title="HamDong settlement confirmation reminder",
                body=(
                    "HamDong settlement confirmation reminder\n\n"
                    "{payer_name} reported a payment of {amount} {currency}.\n"
                    "Please confirm or reject the settlement."
                ),
            ),
            "PLAN_ITEM_REMINDER": self.repository.ensure_template(
                code=settings.EMAIL_TEMPLATE_PLAN_ITEM_REMINDER,
                title="HamDong settlement plan reminder",
                body=(
                    "HamDong settlement plan reminder\n\n"
                    "Group: {group_title}\n"
                    "Amount: {amount} {currency}\n"
                    "Please pay {receiver_name} to complete this settlement step."
                ),
            ),
        }
        self.repository.ensure_template(
            code=settings.EMAIL_TEMPLATE_SETTLEMENT_REMINDER,
            title="HamDong settlement reminder",
            body="HamDong settlement reminder\n\nGroup: {group_title}\n{message}",
        )
        return templates

    def render_otp_message(self, code: str, expires_in: int) -> tuple[str, str, str]:
        template = self.ensure_default_otp_template()
        return template.code, template.title, template.body.format(code=code, expires_in=expires_in)

    def render_reminder_message(self, reminder_type: str, context: dict) -> tuple[str, str, str]:
        templates = self.ensure_default_reminder_templates()
        template = templates.get(reminder_type)
        if template is None:
            template = self.repository.ensure_template(
                code=settings.EMAIL_TEMPLATE_SETTLEMENT_REMINDER,
                title="HamDong settlement reminder",
                body="HamDong settlement reminder\n\nGroup: {group_title}\n{message}",
            )
        return template.code, template.title, template.body.format(**context)
