"""Compatibility wrapper exposing group service functions."""

from apps.groups.application.use_cases import CreateGroupUseCase, ListMyGroupsUseCase


def create_group(*args, **kwargs):
    return CreateGroupUseCase().execute(*args, **kwargs)


def list_my_groups(*args, **kwargs):
    return ListMyGroupsUseCase().execute(*args, **kwargs)
