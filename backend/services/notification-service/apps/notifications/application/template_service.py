"""Template rendering for notification-service."""

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

    def render_otp_message(self, code: str, expires_in: int) -> tuple[str, str]:
        template = self.ensure_default_otp_template()
        return template.code, template.body.format(code=code, expires_in=expires_in)

    def ensure_default_reminder_template(self):
        return self.repository.ensure_template(
            code=settings.SMS_TEMPLATE_SETTLEMENT_REMINDER,
            title="Settlement reminder",
            body="یادآوری تسویه برای گروه {group_title}: {message}",
        )

    def render_reminder_message(self, context: dict) -> tuple[str, str]:
        template = self.ensure_default_reminder_template()
        return template.code, template.body.format(**context)
