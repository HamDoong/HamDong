"""Event helpers for group-service."""

from __future__ import annotations

from apps.groups.infrastructure.event_envelope import build_event_envelope

EVENT_ROUTING_KEYS = {
    "GroupCreated": "group.created",
    "GroupUpdated": "group.updated",
    "GroupArchived": "group.archived",
    "GroupRestored": "group.restored",
    "GroupDeleted": "group.deleted",
    "GroupInviteCreated": "group.invite.created",
    "GroupInviteAccepted": "group.invite.accepted",
    "GroupInviteRevoked": "group.invite.revoked",
    "GroupDirectInvitationCreated": "group.direct_invitation.created",
    "GroupDirectInvitationAccepted": "group.direct_invitation.accepted",
    "GroupDirectInvitationRejected": "group.direct_invitation.rejected",
    "GroupDirectInvitationRevoked": "group.direct_invitation.revoked",
    "GroupMemberJoined": "group.member.joined",
    "GroupMemberRemoved": "group.member.removed",
    "GroupMemberLeft": "group.member.left",
}


def make_event(event_type: str, data: dict, routing_key: str | None = None) -> dict:
    return build_event_envelope(
        event_type,
        data,
        routing_key=routing_key or EVENT_ROUTING_KEYS[event_type],
        source_service="group-service",
    )
