"""Compatibility wrapper exposing member service functions."""

from apps.groups.application.use_cases import ListMembersUseCase, RemoveMemberUseCase, LeaveGroupUseCase


def list_members(*args, **kwargs):
    return ListMembersUseCase().execute(*args, **kwargs)


def remove_member(*args, **kwargs):
    return RemoveMemberUseCase().execute(*args, **kwargs)


def leave_group(*args, **kwargs):
    return LeaveGroupUseCase().execute(*args, **kwargs)
