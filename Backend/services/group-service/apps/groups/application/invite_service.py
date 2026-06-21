"""Compatibility wrapper exposing invite service."""

from apps.groups.application.use_cases import InviteService


def create_invite(*args, **kwargs):
    return InviteService().create_invite(*args, **kwargs)


def preview_invite(*args, **kwargs):
    return InviteService().preview_invite(*args, **kwargs)


def accept_invite(*args, **kwargs):
    return InviteService().accept_invite(*args, **kwargs)


def revoke_invite(*args, **kwargs):
    return InviteService().revoke_invite(*args, **kwargs)
