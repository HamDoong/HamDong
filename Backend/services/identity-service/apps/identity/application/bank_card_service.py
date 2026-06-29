from __future__ import annotations

import base64
import hashlib
import hmac
import re
from dataclasses import dataclass
from typing import Any, Iterable
from uuid import UUID

from cryptography.fernet import Fernet
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.identity.domain.models import User, UserBankCard
from apps.identity.infrastructure.repositories import RefreshTokenRepository


MAX_ACTIVE_BANK_CARDS = 10
_TEXT_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


@dataclass
class BankCardError(ValueError):
    code: str
    message: str
    fields: dict[str, list[str]] | None = None

    def __str__(self) -> str:
        return self.code


def derive_fernet_key() -> bytes:
    secret = str(
        getattr(settings, "BANK_CARD_ENCRYPTION_KEY", "")
        or getattr(settings, "SECRET_KEY", "")
    ).encode("utf-8")
    digest = hashlib.sha256(secret).digest()
    return base64.urlsafe_b64encode(digest)


def get_fernet() -> Fernet:
    return Fernet(derive_fernet_key())


def normalize_card_number(value: Any) -> str:
    if value is None:
        raise BankCardError("INVALID_CARD_NUMBER", "Card number is required.")
    raw_value = str(value)
    if not re.fullmatch(r"[0-9]{16}", raw_value):
        raise BankCardError("INVALID_CARD_NUMBER", "Card number must be 16 digits.")
    if len(set(raw_value)) == 1:
        raise BankCardError("INVALID_CARD_NUMBER", "Card number must be 16 digits.")
    return raw_value


def normalize_holder_name(value: Any) -> str:
    normalized = " ".join(str(value or "").split())
    if not normalized:
        raise BankCardError("INVALID_HOLDER_NAME", "Holder name is required.")
    if len(normalized) > 150:
        raise BankCardError("INVALID_HOLDER_NAME", "Holder name is too long.")
    if _TEXT_CONTROL_RE.search(normalized):
        raise BankCardError("INVALID_HOLDER_NAME", "Holder name contains invalid characters.")
    return normalized


def resolve_holder_name(input_holder_name: Any, user: User) -> str:
    provided_value = " ".join(str(input_holder_name or "").split())
    if provided_value:
        return normalize_holder_name(provided_value)

    fallback_parts = [
        " ".join(str(user.first_name or "").split()),
        " ".join(str(user.last_name or "").split()),
    ]
    fallback_value = " ".join(part for part in fallback_parts if part)
    if not fallback_value:
        raise BankCardError(
            "INVALID_HOLDER_NAME",
            "Holder name is required when user first name and last name are empty.",
        )
    return normalize_holder_name(fallback_value)


def serialize_bank_card_owner(user: User) -> dict[str, Any]:
    return {
        "user_id": str(user.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "art_name": user.art_name,
        "avatar_url": user.avatar_url,
    }


def normalize_bank_name(value: Any) -> str | None:
    if value is None:
        return None
    normalized = " ".join(str(value).split())
    if not normalized:
        return None
    if len(normalized) > 100:
        raise BankCardError("INVALID_BANK_NAME", "Bank name is too long.")
    if _TEXT_CONTROL_RE.search(normalized):
        raise BankCardError("INVALID_BANK_NAME", "Bank name contains invalid characters.")
    return normalized


def mask_card_number(card_number: str) -> str:
    return f"{card_number[:4]} **** **** {card_number[-4:]}"


def hash_card_number(user_id: UUID | str, card_number: str) -> str:
    secret = str(getattr(settings, "SECRET_KEY", "change-me")).encode("utf-8")
    payload = f"{user_id}:{card_number}".encode("utf-8")
    return hmac.new(secret, payload, hashlib.sha256).hexdigest()


def encrypt_card_number(card_number: str) -> str:
    return get_fernet().encrypt(card_number.encode("utf-8")).decode("utf-8")


def decrypt_card_number(value: str) -> str:
    return get_fernet().decrypt(value.encode("utf-8")).decode("utf-8")


def serialize_bank_card(card: UserBankCard, *, include_full_number: bool = False, client_id: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": str(card.id),
        "masked_card_number": card.masked_card_number,
        "card_number_last4": card.card_number_last4,
        "holder_name": card.holder_name,
        "bank_name": card.bank_name,
        "is_default": bool(card.is_default),
        "is_active": bool(card.is_active),
        "created_at": card.created_at,
        "updated_at": card.updated_at,
    }
    if client_id is not None:
        payload["client_id"] = client_id
    if include_full_number:
        payload["card_number"] = decrypt_card_number(card.encrypted_card_number)
        payload["type"] = "BANK_CARD"
    return payload


def _ensure_active_limit(user: User, *, extra_active: int = 0, exclude_ids: Iterable[UUID] | None = None) -> None:
    queryset = UserBankCard.objects.filter(user=user, is_active=True)
    if exclude_ids:
        queryset = queryset.exclude(id__in=list(exclude_ids))
    if queryset.count() + extra_active > MAX_ACTIVE_BANK_CARDS:
        raise BankCardError(
            "BANK_CARD_LIMIT_EXCEEDED",
            "You can save up to 10 active bank cards.",
        )


def _unset_other_defaults(user: User, current_id: UUID | None = None) -> None:
    queryset = UserBankCard.objects.filter(user=user, is_active=True, is_default=True)
    if current_id is not None:
        queryset = queryset.exclude(id=current_id)
    queryset.update(is_default=False, updated_at=timezone.now())


def _assign_default_if_missing(user: User) -> None:
    active_cards = list(UserBankCard.objects.filter(user=user, is_active=True).order_by("created_at", "id"))
    if not active_cards:
        return
    default_cards = [card for card in active_cards if card.is_default]
    if len(default_cards) == 1:
        return
    chosen = default_cards[0] if default_cards else active_cards[0]
    _unset_other_defaults(user, chosen.id)
    if not chosen.is_default:
        chosen.is_default = True
        chosen.save(update_fields=["is_default", "updated_at"])


class BankCardService:
    def _publish_event(self, event_type: str, card: UserBankCard) -> None:
        from apps.identity.domain.events import (
            UserBankCardCreated,
            UserBankCardDeactivated,
            UserBankCardUpdated,
        )
        from apps.identity.infrastructure.rabbitmq_publisher import RabbitMqPublisher

        event_map = {
            "created": UserBankCardCreated,
            "updated": UserBankCardUpdated,
            "deactivated": UserBankCardDeactivated,
        }
        event_cls = event_map[event_type]
        event = event_cls(
            card_id=card.id,
            user_id=card.user_id,
            holder_name=card.holder_name,
            bank_name=card.bank_name,
            card_number_last4=card.card_number_last4,
            masked_card_number=card.masked_card_number,
            is_default=card.is_default,
            is_active=card.is_active,
            updated_at=card.updated_at,
        )
        RabbitMqPublisher().publish(event.to_dict(), event.to_dict()["routing_key"])

    def list_cards(self, user: User, *, include_inactive: bool = False) -> list[UserBankCard]:
        queryset = UserBankCard.objects.filter(user=user)
        if not include_inactive:
            queryset = queryset.filter(is_active=True)
        return list(queryset.order_by("-is_default", "-updated_at", "-created_at"))

    @transaction.atomic
    def create_card(
        self,
        user: User,
        *,
        card_number: Any,
        holder_name: Any = None,
        bank_name: Any = None,
        is_default: bool | None = None,
    ) -> tuple[UserBankCard, bool]:
        normalized_card_number = normalize_card_number(card_number)
        normalized_holder_name = resolve_holder_name(holder_name, user)
        normalized_bank_name = normalize_bank_name(bank_name)
        card_hash = hash_card_number(user.id, normalized_card_number)
        existing = UserBankCard.objects.filter(user=user, card_number_hash=card_hash).first()
        if existing and existing.is_active:
            raise BankCardError("CARD_ALREADY_EXISTS", "This card is already registered for your account.")
        if not existing:
            _ensure_active_limit(user, extra_active=1)
        first_active = not UserBankCard.objects.filter(user=user, is_active=True).exists()
        should_default = bool(is_default) or first_active

        if existing:
            existing.holder_name = normalized_holder_name
            existing.bank_name = normalized_bank_name
            existing.card_number_last4 = normalized_card_number[-4:]
            existing.encrypted_card_number = encrypt_card_number(normalized_card_number)
            existing.masked_card_number = mask_card_number(normalized_card_number)
            existing.is_active = True
            existing.is_default = should_default
            existing.save()
            card = existing
            created = False
            event_type = "updated"
        else:
            card = UserBankCard.objects.create(
                user=user,
                holder_name=normalized_holder_name,
                bank_name=normalized_bank_name,
                card_number_last4=normalized_card_number[-4:],
                card_number_hash=card_hash,
                encrypted_card_number=encrypt_card_number(normalized_card_number),
                masked_card_number=mask_card_number(normalized_card_number),
                is_default=should_default,
                is_active=True,
            )
            created = True
            event_type = "created"

        if should_default:
            _unset_other_defaults(user, card.id)
        _assign_default_if_missing(user)
        card.refresh_from_db()
        self._publish_event(event_type, card)
        return card, created

    @transaction.atomic
    def update_card(self, user: User, card_id: UUID | str, payload: dict[str, Any]) -> UserBankCard:
        card = UserBankCard.objects.filter(user=user, id=card_id).first()
        if not card:
            raise BankCardError("NOT_FOUND", "Bank card not found.")
        if "card_number" in payload:
            raise BankCardError("CARD_NUMBER_IMMUTABLE", "Card number cannot be changed. Remove the card and add a new one.")

        fields_to_update: list[str] = []
        if "holder_name" in payload:
            card.holder_name = normalize_holder_name(payload.get("holder_name"))
            fields_to_update.append("holder_name")
        if "bank_name" in payload:
            card.bank_name = normalize_bank_name(payload.get("bank_name"))
            fields_to_update.append("bank_name")
        if "is_active" in payload:
            new_is_active = bool(payload.get("is_active"))
            if new_is_active and not card.is_active:
                _ensure_active_limit(user, extra_active=1)
            card.is_active = new_is_active
            if not new_is_active:
                card.is_default = False
            fields_to_update.extend(["is_active", "is_default"])
        if "is_default" in payload and bool(payload.get("is_default")) and card.is_active:
            card.is_default = True
            fields_to_update.append("is_default")

        if fields_to_update:
            card.save()
        if card.is_active and card.is_default:
            _unset_other_defaults(user, card.id)
        _assign_default_if_missing(user)
        card.refresh_from_db()
        self._publish_event("deactivated" if not card.is_active else "updated", card)
        return card

    @transaction.atomic
    def delete_card(self, user: User, card_id: UUID | str) -> None:
        card = UserBankCard.objects.filter(user=user, id=card_id).first()
        if not card:
            raise BankCardError("NOT_FOUND", "Bank card not found.")
        if not card.is_active:
            return
        card.is_active = False
        card.is_default = False
        card.save(update_fields=["is_active", "is_default", "updated_at"])
        _assign_default_if_missing(user)
        self._publish_event("deactivated", card)

    @transaction.atomic
    def bulk_save(self, user: User, cards: list[dict[str, Any]], deleted_card_ids: list[Any] | None = None) -> list[dict[str, Any]]:
        if not isinstance(cards, list):
            raise BankCardError("VALIDATION_ERROR", "cards must be an array.")
        if deleted_card_ids is None:
            deleted_card_ids = []
        if not isinstance(deleted_card_ids, list):
            raise BankCardError("VALIDATION_ERROR", "deleted_card_ids must be an array.")
        deleted_ids = [str(value) for value in deleted_card_ids]
        existing_cards = {
            str(card.id): card
            for card in UserBankCard.objects.filter(user=user)
        }
        unknown_deleted = [card_id for card_id in deleted_ids if card_id not in existing_cards]
        if unknown_deleted:
            raise BankCardError("NOT_FOUND", "Bank card not found.")

        field_errors: dict[str, list[str]] = {}
        normalized_new_hashes: dict[str, int] = {}
        final_active_ids: set[str] = {card_id for card_id, card in existing_cards.items() if card.is_active and card_id not in deleted_ids}
        final_default_ids: list[str] = []
        cards_to_create: list[tuple[dict[str, Any], str, str, str | None, str]] = []

        for index, item in enumerate(cards):
            if not isinstance(item, dict):
                field_errors[f"cards[{index}]"] = ["Each item must be an object."]
                continue
            card_id = str(item.get("id")) if item.get("id") else None
            if card_id:
                existing = existing_cards.get(card_id)
                if not existing:
                    field_errors[f"cards[{index}].id"] = ["Bank card not found."]
                    continue
                if "card_number" in item:
                    field_errors[f"cards[{index}].card_number"] = ["Card number cannot be changed. Remove the card and add a new one."]
                if card_id in deleted_ids:
                    continue
                if item.get("holder_name") is not None:
                    try:
                        resolve_holder_name(item.get("holder_name"), user)
                    except BankCardError as exc:
                        field_errors[f"cards[{index}].holder_name"] = [exc.message]
                if item.get("bank_name") is not None:
                    try:
                        normalize_bank_name(item.get("bank_name"))
                    except BankCardError as exc:
                        field_errors[f"cards[{index}].bank_name"] = [exc.message]
                if item.get("is_active", existing.is_active):
                    final_active_ids.add(card_id)
                    if item.get("is_default", existing.is_default):
                        final_default_ids.append(card_id)
                elif card_id in final_active_ids:
                    final_active_ids.remove(card_id)
            else:
                if "card_number" not in item:
                    field_errors[f"cards[{index}].card_number"] = ["This field is required."]
                    continue
                try:
                    normalized_card_number = normalize_card_number(item.get("card_number"))
                    normalized_holder_name = resolve_holder_name(item.get("holder_name"), user)
                    normalized_bank_name = normalize_bank_name(item.get("bank_name"))
                except BankCardError as exc:
                    target = {
                        "INVALID_CARD_NUMBER": "card_number",
                        "INVALID_HOLDER_NAME": "holder_name",
                        "INVALID_BANK_NAME": "bank_name",
                    }.get(exc.code, "card_number")
                    field_errors[f"cards[{index}].{target}"] = [exc.message]
                    continue
                card_hash = hash_card_number(user.id, normalized_card_number)
                if card_hash in normalized_new_hashes:
                    field_errors[f"cards[{index}].card_number"] = ["Duplicate card number in request."]
                    continue
                normalized_new_hashes[card_hash] = index
                existing = UserBankCard.objects.filter(user=user, card_number_hash=card_hash).first()
                if existing and existing.is_active and str(existing.id) not in deleted_ids:
                    field_errors[f"cards[{index}].card_number"] = ["This card is already registered for your account."]
                    continue
                future_id = str(existing.id) if existing else f"new-{index}"
                final_active_ids.add(future_id)
                if item.get("is_default"):
                    final_default_ids.append(future_id)
                cards_to_create.append((item, normalized_card_number, normalized_holder_name, normalized_bank_name, card_hash))

        if len(final_active_ids) > MAX_ACTIVE_BANK_CARDS:
            raise BankCardError("BANK_CARD_LIMIT_EXCEEDED", "You can save up to 10 active bank cards.")
        if len(final_default_ids) > 1:
            raise BankCardError("MULTIPLE_DEFAULT_CARDS", "Only one active card can be default.")
        if field_errors:
            raise BankCardError("VALIDATION_ERROR", "Validation failed.", fields=field_errors)

        results: list[dict[str, Any]] = []
        for card_id in deleted_ids:
            self.delete_card(user, card_id)

        for item in cards:
            client_id = item.get("client_id")
            card_id = item.get("id")
            if card_id:
                if str(card_id) in deleted_ids:
                    continue
                card = existing_cards[str(card_id)]
                update_payload = {
                    key: item[key]
                    for key in ("holder_name", "bank_name", "is_default", "is_active")
                    if key in item
                }
                if "holder_name" in update_payload:
                    update_payload["holder_name"] = resolve_holder_name(update_payload.get("holder_name"), user)
                card = self.update_card(user, card.id, update_payload)
                results.append(serialize_bank_card(card, client_id=client_id))
                continue

            normalized_card_number = normalize_card_number(item.get("card_number"))
            card, _ = self.create_card(
                user,
                card_number=normalized_card_number,
                holder_name=item.get("holder_name"),
                bank_name=item.get("bank_name"),
                is_default=item.get("is_default"),
            )
            results.append(serialize_bank_card(card, client_id=client_id))

        _assign_default_if_missing(user)
        refreshed = []
        for item in results:
            card = UserBankCard.objects.get(id=item["id"])
            refreshed.append(serialize_bank_card(card, client_id=item.get("client_id")))
        return refreshed

    @transaction.atomic
    def deactivate_account(self, user: User, *, current_password: str | None = None, reason: str | None = None) -> tuple[str, User]:
        if not user.is_active:
            return "ALREADY_DEACTIVATED", user
        if user.has_usable_password():
            if not current_password:
                raise BankCardError("CURRENT_PASSWORD_REQUIRED", "Current password is required.")
            if not user.check_password(current_password):
                raise BankCardError("INVALID_CURRENT_PASSWORD", "Current password is incorrect.")
        user.is_active = False
        if hasattr(user, "deleted_at"):
            user.deleted_at = timezone.now()
        user.save(update_fields=["is_active", "deleted_at", "updated_at"])
        RefreshTokenRepository.revoke_active_for_user(user)
        return "DEACTIVATED", user

    def resolve_payment_context_cards(self, owner_user_id: UUID | str, *, card_ids: list[Any] | None = None) -> list[dict[str, Any]]:
        queryset = UserBankCard.objects.filter(user_id=owner_user_id, is_active=True)
        if card_ids:
            queryset = queryset.filter(id__in=card_ids)
        cards = list(queryset.order_by("-is_default", "created_at"))
        return [serialize_bank_card(card, include_full_number=True) for card in cards]
