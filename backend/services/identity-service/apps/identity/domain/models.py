import uuid
from django.db import models
from django.utils import timezone


class User(models.Model):
    """Custom user model for identity service."""

    class RoleChoices(models.TextChoices):
        USER = "USER", "User"
        ADMIN = "ADMIN", "Admin"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField(max_length=20, unique=True)
    display_name = models.CharField(max_length=255, null=True, blank=True)
    first_name = models.CharField(max_length=150, null=True, blank=True)
    last_name = models.CharField(max_length=150, null=True, blank=True)
    avatar_url = models.URLField(null=True, blank=True)
    is_phone_verified = models.BooleanField(default=False)
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

    # Django auth compatibility (minimal): identify by phone_number
    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = []
    objects = models.Manager()

    class Meta:
        db_table = "users"
        ordering = ["-created_at"]

    def __str__(self):
        return f"User({self.phone_number})"

    @property
    def last_login(self):
        return self.last_login_at

    @last_login.setter
    def last_login(self, value):
        self.last_login_at = value

    # Minimal Django auth compatibility helpers
    @property
    def is_anonymous(self):
        return False

    @property
    def is_authenticated(self):
        return True


class RefreshToken(models.Model):
    """Refresh token model for token rotation and revocation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="refresh_tokens"
    )
    token_hash = models.CharField(max_length=255, unique=True)
    jti = models.UUIDField(unique=True, default=uuid.uuid4)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user_agent = models.TextField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = "refresh_tokens"
        ordering = ["-created_at"]

    def __str__(self):
        return f"RefreshToken({self.user.phone_number})"

    @property
    def is_revoked(self):
        return self.revoked_at is not None


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
