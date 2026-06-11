"""Template rendering for notification-service."""

from __future__ import annotations

from django.conf import settings

from apps.notifications.infrastructure.repositories import NotificationRepository


class TemplateService:
    def __init__(self):
        self.repository = NotificationRepository()

    def ensure_default_otp_template(self):
        return self.repository.ensure_template(
            code=settings.SMS_TEMPLATE_OTP_LOGIN,
            title="Login OTP",
            body="کد ورود شما به هم‌دنگ: {code}\nاعتبار: {expires_in} ثانیه",
        )

    def ensure_default_reminder_templates(self) -> dict[str, object]:
        templates = {
            "PAYMENT_REMINDER": self.repository.ensure_template(
                code=settings.SMS_TEMPLATE_PAYMENT_REMINDER,
                title="Payment reminder",
                body=(
                    "یادآوری هم‌دنگ:\n"
                    "شما در گروه {group_title} مبلغ {amount} {currency} بدهکار هستید.\n"
                    "لطفاً در زمان مناسب تسویه را انجام دهید."
                ),
            ),
            "SETTLEMENT_CONFIRMATION_REMINDER": self.repository.ensure_template(
                code=settings.SMS_TEMPLATE_SETTLEMENT_CONFIRMATION_REMINDER,
                title="Settlement confirmation reminder",
                body=(
                    "یادآوری هم‌دنگ:\n"
                    "{payer_name} اعلام کرده مبلغ {amount} {currency} را پرداخت کرده است.\n"
                    "لطفاً دریافت مبلغ را تأیید یا رد کنید."
                ),
            ),
            "PLAN_ITEM_REMINDER": self.repository.ensure_template(
                code=settings.SMS_TEMPLATE_PLAN_ITEM_REMINDER,
                title="Settlement plan item reminder",
                body=(
                    "یادآوری هم‌دنگ:\n"
                    "برای تسویه گروه {group_title} لطفاً مبلغ {amount} {currency} را به {receiver_name} پرداخت کنید."
                ),
            ),
        }
        # Legacy compatibility for older code paths that still expect a generic reminder template.
        self.repository.ensure_template(
            code=settings.SMS_TEMPLATE_SETTLEMENT_REMINDER,
            title="Settlement reminder",
            body="یادآوری تسویه برای گروه {group_title}: {message}",
        )
        return templates

    def render_otp_message(self, code: str, expires_in: int) -> tuple[str, str]:
        template = self.ensure_default_otp_template()
        return template.code, template.body.format(code=code, expires_in=expires_in)

    def render_reminder_message(self, reminder_type: str, context: dict) -> tuple[str, str]:
        templates = self.ensure_default_reminder_templates()
        template = templates.get(reminder_type)
        if template is None:
            template = self.repository.ensure_template(
                code=settings.SMS_TEMPLATE_SETTLEMENT_REMINDER,
                title="Settlement reminder",
                body="یادآوری تسویه برای گروه {group_title}: {message}",
            )
        return template.code, template.body.format(**context)
