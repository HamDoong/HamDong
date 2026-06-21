from rest_framework.permissions import BasePermission
from apps.expenses.infrastructure.repositories import ProjectionRepository


class IsActiveGroupMember(BasePermission):
    """Permission that checks whether request.user is an active member of the group.

    Expects view kwargs to include `group_id` when used for group-scoped endpoints.
    """

    def has_permission(self, request, view):
        group_id = view.kwargs.get("group_id") or request.data.get("group_id")
        if not group_id:
            return False
        user = getattr(request, "user", None)
        if not user:
            return False
        return ProjectionRepository.is_active_member(group_id, getattr(user, "sub", getattr(user, "id", None)))
