from __future__ import annotations

import re
import uuid

from django.contrib.auth.hashers import check_password as django_check_password
from django.contrib.auth.hashers import is_password_usable, make_password
from django.db import models
from django.utils import timezone


class User(models.Model):
    """Custom user model for identity service."""

    class RoleChoices(models.TextChoices):
        USER = "USER", "User"
        ADMIN = "ADMIN", "Admin"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(max_length=254, unique=True)
    legacy_phone_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    legacy_display_name = models.CharField(max_length=255, null=True, blank=True)
    display_name = models.CharField(max_length=150, null=True, blank=True)
    phone_number = models.CharField(max_length=16, unique=True, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    city = models.CharField(max_length=150, null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    art_name = models.CharField(max_length=32, unique=True)
    first_name = models.CharField(max_length=150, null=True, blank=True)
    last_name = models.CharField(max_length=150, null=True, blank=True)
    avatar_url = models.URLField(null=True, blank=True)
    avatar_file_id = models.UUIDField(null=True, blank=True)
    password_hash = models.CharField(max_length=128, null=True, blank=True)
    password_changed_at = models.DateTimeField(null=True, blank=True)
    is_email_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    role = models.CharField(
        max_length=10,
        choices=RoleChoices.choices,
        default=RoleChoices.USER,
    )
    last_login_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    version = models.IntegerField(default=1)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = models.Manager()

    class Meta:
        db_table = "users"
        ordering = ["-created_at"]

    def _generate_art_name(self) -> str:
        base_source = (self.email or "user").split("@", 1)[0]
        candidate = re.sub(r"\s+", "-", base_source.strip())
        candidate = re.sub(r"[^\w\-\u0600-\u06FF]", "-", candidate, flags=re.UNICODE)
        candidate = re.sub(r"-{2,}", "-", candidate).strip("-_")
        candidate = candidate[:32] if candidate else ""
        if not candidate or len(candidate) < 3:
            candidate = f"user-{str(self.id or uuid.uuid4()).replace('-', '')[:8]}".lower()[:32]
        unique_candidate = candidate
        suffix = 1
        while User.objects.exclude(pk=self.pk).filter(art_name=unique_candidate).exists():
            suffix_token = f"-{suffix}"
            unique_candidate = f"{candidate[: max(3, 32 - len(suffix_token))]}{suffix_token}"
            suffix += 1
        return unique_candidate

    def save(self, *args, **kwargs):
        if not self.art_name:
            if not self.id:
                self.id = uuid.uuid4()
            self.art_name = self._generate_art_name()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"User({self.email})"

    @property
    def last_login(self):
        return self.last_login_at

    @last_login.setter
    def last_login(self, value):
        self.last_login_at = value

    @property
    def is_anonymous(self):
        return False

    @property
    def is_authenticated(self):
        return True

    def set_password(self, raw_password: str) -> None:
        self.password_hash = make_password(raw_password)
        self.password_changed_at = timezone.now()

    def check_password(self, raw_password: str) -> bool:
        if not self.password_hash:
            return False
        return django_check_password(raw_password, self.password_hash)

    def has_usable_password(self) -> bool:
        return bool(self.password_hash and is_password_usable(self.password_hash))


class UserBankCard(models.Model):
    """User-owned bank cards stored encrypted at rest."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="bank_cards")
    holder_name = models.CharField(max_length=150)
    bank_name = models.CharField(max_length=100, null=True, blank=True)
    card_number_last4 = models.CharField(max_length=4)
    masked_card_number = models.CharField(max_length=24)
    card_number_hash = models.CharField(max_length=64)
    encrypted_card_number = models.TextField()
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_bank_cards"
        ordering = ["-is_default", "-updated_at", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "card_number_hash"], name="uniq_user_bank_card_hash"),
        ]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["user", "is_default"]),
        ]

    def __str__(self):
        return f"UserBankCard({self.user_id}, ****{self.card_number_last4})"



class RefreshToken(models.Model):
    """Refresh token model for token rotation, session listing, and revocation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="refresh_tokens"
    )
    token_hash = models.CharField(max_length=255, unique=True)
    jti = models.UUIDField(unique=True, default=uuid.uuid4)
    remember_me = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    last_used_at = models.DateTimeField(default=timezone.now)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user_agent = models.TextField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = "refresh_tokens"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "revoked_at", "expires_at"]),
        ]

    def __str__(self):
        return f"RefreshToken({self.user.email})"

    @property
    def is_revoked(self):
        return self.revoked_at is not None


class PasswordResetChallenge(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = "PENDING", "Pending"
        VERIFIED = "VERIFIED", "Verified"
        USED = "USED", "Used"
        EXPIRED = "EXPIRED", "Expired"
        LOCKED = "LOCKED", "Locked"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="password_reset_challenges",
        null=True,
        blank=True,
    )
    email = models.EmailField(max_length=254, db_index=True)
    otp_hash = models.CharField(max_length=128)
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING)
    attempt_count = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=5)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "password_reset_challenges"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email", "status", "created_at"]),
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self):
        return f"PasswordResetChallenge({self.email}, {self.status})"


class PasswordResetToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    challenge = models.ForeignKey(
        PasswordResetChallenge,
        on_delete=models.CASCADE,
        related_name="reset_tokens",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
    )
    token_hash = models.CharField(max_length=128, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "password_reset_tokens"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "expires_at", "used_at"]),
        ]

    def __str__(self):
        return f"PasswordResetToken({self.user.email})"


class OutboxMessageStatusChoices(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PUBLISHED = "PUBLISHED", "Published"
    FAILED = "FAILED", "Failed"


class OutboxMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_id = models.UUIDField(unique=True, db_index=True)
    event_type = models.CharField(max_length=128)
    event_version = models.PositiveIntegerField(default=1)
    source_service = models.CharField(max_length=128)
    exchange = models.CharField(max_length=128)
    routing_key = models.CharField(max_length=128)
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=OutboxMessageStatusChoices.choices, default=OutboxMessageStatusChoices.PENDING)
    retry_count = models.PositiveIntegerField(default=0)
    last_error = models.TextField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    available_at = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "identity_outbox_messages"
        indexes = [models.Index(fields=["status", "available_at"]), models.Index(fields=["routing_key"])]
